"""Full-source geometric PV preparation, published through the durable worker."""

from __future__ import annotations

from .asset_publication import AssetPublication, AssetResult
from .assets import Asset, Assets
from .canonical import Object, digest, encode
from .errors import InvalidInput, VersionUnavailable
from .execution_identity import execution_key, request_execution_key
from .frozen_run import frozen_manifest
from .geometric_pv_generation import generate_geometric_pv
from .geometric_pv_inputs import (
    KIND,
    MODEL,
    MODEL_ROLES,
    PROFILE_PURPOSE,
    SHADING_STATUS,
    GeometricPvInputs,
    GeometricPvLimits,
)
from .product_sources import ProductSources
from .pv_parameters import PvGenerationLimits
from .pv_preparation import require_weather_source, selected_weather
from .pv_source import PvSource
from .records import Actor, Context, Lease
from .runtime_snapshot import RuntimeSnapshot
from .worker import Control
from .workspace import Workspace


def selected_source(
    assets: Assets, actor: Actor, project_id: str, inputs: Object
) -> Asset:
    request = GeometricPvInputs.read(inputs.get("geometric_pv_preparation"))
    return selected_weather(
        assets,
        actor,
        project_id,
        {
            **inputs,
            "pv_preparation": {
                "schema_version": 1,
                "weather_asset_id": request.weather_asset_id,
            },
        },
    )


def check_geometric_pv(
    assets: Assets, actor: Actor, project_id: str | None, inputs: Object
) -> None:
    if "geometric_pv_preparation" not in inputs:
        return
    GeometricPvInputs.read(inputs["geometric_pv_preparation"])
    if project_id is None:
        raise InvalidInput("a new project cannot reference another project's weather")
    selected_source(assets, actor, project_id, inputs)


class GeometricPvKernel:
    kind = KIND
    models = {
        "task": KIND,
        # Retained identity. New requests name MODEL_V2 on the result; changing
        # this map would rewrite frozen v1 manifests.
        "generation": MODEL,
        "geometry": "declared_opaque_ray_midpoint_uvn_v1",
        "weather": "pvgis_5_3_tmy_explicit_two_axes_v1",
        "pvlib": "0.16.1",
    }

    def __init__(
        self,
        workspace: Workspace,
        weather_limits: PvGenerationLimits,
        limits: GeometricPvLimits,
        *,
        products: ProductSources,
    ) -> None:
        self.workspace, self.products = workspace, products
        self.weather_limits = PvGenerationLimits.read(
            weather_limits.model_dump(mode="json")
        )
        self.limits = GeometricPvLimits.read(limits.model_dump(mode="json"))
        self.runtime = RuntimeSnapshot.capture()
        workspace.blobs.put(self.runtime.content)

    def parameters(self) -> Object:
        return {
            "kind": KIND,
            "weather_limits": self.weather_limits.model_dump(mode="json"),
            "limits": self.limits.model_dump(mode="json"),
            "product_policy": "current_woo_reference_v1",
        }

    def execution_key(self) -> str:
        return execution_key(
            {
                "code_sha256": self.runtime.sha256,
                "models": dict(self.models),
                "parameters": self.parameters(),
            }
        )

    def context(self, actor: Actor, project_id: str, inputs: Object) -> Context:
        request = GeometricPvInputs.read(inputs.get("geometric_pv_preparation"))
        source = selected_source(Assets(self.workspace), actor, project_id, inputs)
        self.workspace.blobs.read(source.content_sha256)
        basis = self.products.pv_basis(request.product_inputs(inputs))
        return Context(
            self.runtime.sha256,
            dict(self.models),
            {
                "runtime_bundle": self.runtime.sha256,
                "weather.raw": source.content_sha256,
                "weather.metadata": source.metadata_sha256,
                "woo.module_inputs": self.workspace.blobs.put_object(basis),
            },
            self.parameters(),
        )

    def _owned_source(self, project_id: str, asset_id: str, pinned: Object) -> Object:
        with self.workspace.database.read() as connection:
            row = connection.execute(
                "SELECT * FROM project_assets WHERE project_id=? AND id=?",
                (project_id, asset_id),
            ).fetchone()
        if (
            row is None
            or row["content_sha256"] != pinned["weather.raw"]
            or row["metadata_sha256"] != pinned["weather.metadata"]
            or row["media_type"] != "application/json"
        ):
            raise VersionUnavailable("geometric PV owned weather changed")
        metadata = self.workspace.blobs.object(str(pinned["weather.metadata"]))
        require_weather_source(row["purpose"], metadata)
        return metadata

    def __call__(self, lease: Lease, control: Control) -> AssetResult:
        control.checkpoint()
        manifest_sha = lease.request.get("manifest_sha256")
        if not isinstance(manifest_sha, str):
            raise VersionUnavailable("geometric PV requires a frozen manifest")
        manifest = frozen_manifest(self.workspace, lease, manifest_sha)
        if (
            request_execution_key(lease.request, manifest, manifest_sha)
            != self.execution_key()
        ):
            raise VersionUnavailable("worker differs from pinned geometric PV executor")
        context = manifest.get("context")
        assert isinstance(context, dict)
        pinned = context.get("assets")
        if (
            not isinstance(pinned, dict)
            or set(pinned)
            != {
                "runtime_bundle",
                "weather.raw",
                "weather.metadata",
                "woo.module_inputs",
            }
            or pinned["runtime_bundle"] != self.runtime.sha256
            or any(not isinstance(value, str) for value in pinned.values())
        ):
            raise VersionUnavailable("exact geometric PV source dependencies required")
        for sha in pinned.values():
            self.workspace.blobs.read(str(sha))
        inputs = self.workspace.pinned_inputs(manifest)
        request = GeometricPvInputs.read(inputs.get("geometric_pv_preparation"))
        project, revision = manifest.get("project_id"), manifest.get("revision")
        if not isinstance(project, str) or type(revision) is not int:
            raise VersionUnavailable("geometric PV saved project revision required")
        basis = self.workspace.blobs.object(str(pinned["woo.module_inputs"]))
        self.products.confirm_basis(basis)
        self.products.check_pv_inputs(request.product_inputs(inputs), basis)
        source_metadata = self._owned_source(project, request.weather_asset_id, pinned)
        source = PvSource.read(
            self.workspace.blobs, str(pinned["weather.raw"]), source_metadata
        )
        weather = source.weather(self.weather_limits)
        result = generate_geometric_pv(
            inputs.get("geometry"),
            weather,
            request,
            self.limits,
            max_weather_rows=self.weather_limits.max_weather_rows,
            checkpoint=control.checkpoint,
        )
        control.checkpoint()
        self._owned_source(project, request.weather_asset_id, pinned)
        self.products.confirm_basis(basis)
        dependencies: Object = {
            "model.inputs": self.workspace.blobs.put(result.inputs_json),
            "model.witness": self.workspace.blobs.put(result.witness_json),
            "weather.raw": pinned["weather.raw"],
            "weather.metadata": pinned["weather.metadata"],
            "woo.module_inputs": pinned["woo.module_inputs"],
        }
        # Bind the exact saved project JSON separately from normalized model
        # coefficients, preserving byte-level project invalidation semantics.
        raw_parameters = inputs["geometric_pv_preparation"]
        assert isinstance(raw_parameters, dict)
        dependencies["project.parameters"] = self.workspace.blobs.put_object(
            raw_parameters
        )
        summary: Object = {
            "start_utc": result.profile.intervals[0].start.isoformat(),
            "end_utc": result.profile.intervals[-1].end.isoformat(),
            "interval_count": len(result.profile.intervals),
            "energy_kwh": result.profile.total_kwh,
            "measurement": "pv_available_ac",
            "origin": "modelled",
            "native_max_interval_seconds": weather.source.native_max_interval_seconds,
            "reconstructed_means": True,
            "model_role": MODEL_ROLES[request.model],
        }
        metadata: Object = {
            **source.metadata(),
            "schema": 1,
            "profile_type": PROFILE_PURPOSE,
            "retention": "permanent",
            "derived_from_revision": revision,
            "geometry_sha256": digest(encode(inputs.get("geometry"))),
            "parameters_sha256": dependencies["project.parameters"],
            "dependencies": dependencies,
            "woo_module_inputs": basis,
            "interpretation": summary,
            "weather": {
                "interval_count": len(weather.points),
                "start_utc": weather.points[0].interval.start.isoformat(),
                "end_utc": weather.points[-1].interval.end.isoformat(),
                "weather_document_sha256": digest(encode(weather.document())),
            },
        }
        publication = AssetPublication.prepare(
            self.workspace.blobs,
            project,
            encode(
                {
                    "schema_version": 1,
                    "kind": request.model,
                    "dependencies": dependencies,
                }
            ),
            "application/json",
            PROFILE_PURPOSE,
            metadata,
        )
        control.checkpoint()
        return AssetResult(
            {
                "schema": 1,
                "kind": KIND,
                "model": request.model,
                "project_id": project,
                "revision": revision,
                "input_sha256": manifest["input_sha256"],
                "manifest_sha256": manifest_sha,
                "runtime_sha256": self.runtime.sha256,
                "pinned_assets": pinned,
                "profile_summary": summary,
                "dependencies": dependencies,
                "scope": {
                    "diffuse_policy": request.diffuse_policy,
                    "thermal_policy": request.thermal_policy,
                    "electrical_policy": request.electrical_policy,
                },
                "equipment_release": {"status": "not_assessed"},
                "country_assessment": {"status": "not_assessed"},
                "near_shading_assessment": {"status": SHADING_STATUS[request.model]},
            },
            publication,
        )
