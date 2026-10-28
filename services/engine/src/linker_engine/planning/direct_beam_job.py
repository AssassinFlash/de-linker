"""Owned-weather worker; publishes a geometric witness, never a PV asset."""

from __future__ import annotations

from .assets import Asset, Assets
from .canonical import Object, digest, encode
from .direct_beam_inputs import (
    DirectBeamBinding,
    DirectBeamLimits,
    DirectBeamTaskInputs,
    FrozenWeatherSelection,
)
from .direct_beam_preparation import prepare_direct_beam
from .errors import InvalidInput, VersionUnavailable
from .execution_identity import execution_key, request_execution_key
from .frozen_run import frozen_manifest
from .product_sources import ProductSources
from .pv_parameters import PvGenerationLimits
from .pv_preparation import require_weather_source, selected_weather
from .pv_source import PvSource
from .records import Actor, Context, Lease
from .runtime_snapshot import RuntimeSnapshot
from .worker import Control
from .workspace import Workspace


class DirectBeamKernel:
    kind = "prepare_direct_beam_visibility_v1"
    models = {
        "task": kind,
        "geometry": "declared_opaque_ray_midpoint_uvn_v1",
        "weather": "pvgis_5_3_tmy_explicit_two_axes_v1",
        "pvlib": "0.16.1",
    }

    def __init__(
        self,
        workspace: Workspace,
        weather_limits: PvGenerationLimits,
        limits: DirectBeamLimits,
        *,
        products: ProductSources,
    ) -> None:
        if not isinstance(products, ProductSources):
            raise InvalidInput("a current Woo product provider is required")
        self.workspace, self.products = workspace, products
        self.weather_limits = PvGenerationLimits.read(
            weather_limits.model_dump(mode="json")
        )
        self.limits = DirectBeamLimits.read(limits.model_dump(mode="json"))
        self.runtime = RuntimeSnapshot.capture()
        self.workspace.blobs.put(self.runtime.content)

    def parameters(self) -> Object:
        return {
            "kind": self.kind,
            "weather_limits": self.weather_limits.model_dump(mode="json"),
            "visibility_limits": self.limits.model_dump(mode="json"),
            "product_policy": "current_woo_roof_reference_v1",
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
        request = DirectBeamTaskInputs.read(inputs.get("direct_beam_visibility"))
        if len(request.row_indices) > self.limits.max_selected_rows:
            raise InvalidInput("direct-beam row selection exceeds resource policy")
        # Reuse the existing owned TMY source and saved acquisition-request
        # check, without changing the project or generating a PV profile.
        source = selected_weather(
            Assets(self.workspace),
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
        self.workspace.blobs.read(source.content_sha256)
        basis = self.products.roof_basis(inputs)
        geometry = inputs.get("geometry")
        if not isinstance(geometry, dict):
            raise InvalidInput("saved roof geometry required")
        return Context(
            self.runtime.sha256,
            dict(self.models),
            {
                "runtime_bundle": self.runtime.sha256,
                "weather.raw": source.content_sha256,
                "weather.metadata": source.metadata_sha256,
                "geometry": self.workspace.blobs.put_object(geometry),
                "woo.module_inputs": self.workspace.blobs.put_object(basis),
            },
            self.parameters(),
        )

    def _owned_source(self, project_id: str, asset_id: str, pinned: Object) -> Asset:
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
            raise VersionUnavailable(
                "weather differs from the frozen project's owned source"
            )
        metadata = self.workspace.blobs.object(row["metadata_sha256"])
        require_weather_source(row["purpose"], metadata)
        return Asset(
            asset_id,
            project_id,
            row["content_sha256"],
            row["media_type"],
            row["purpose"],
            row["metadata_sha256"],
            metadata,
        )

    def __call__(self, lease: Lease, control: Control) -> Object:
        control.checkpoint()
        manifest_sha = lease.request.get("manifest_sha256")
        if not isinstance(manifest_sha, str):
            raise VersionUnavailable("direct-beam job has no frozen manifest")
        manifest = frozen_manifest(self.workspace, lease, manifest_sha)
        if (
            request_execution_key(lease.request, manifest, manifest_sha)
            != self.execution_key()
        ):
            raise VersionUnavailable("worker differs from the pinned direct-beam task")
        context = manifest.get("context")
        assert isinstance(context, dict)  # request_execution_key checks its shape.
        pinned = context.get("assets")
        if (
            not isinstance(pinned, dict)
            or set(pinned)
            != {
                "runtime_bundle",
                "weather.raw",
                "weather.metadata",
                "geometry",
                "woo.module_inputs",
            }
            or any(not isinstance(sha, str) for sha in pinned.values())
            or pinned["runtime_bundle"] != self.runtime.sha256
        ):
            raise VersionUnavailable("exact direct-beam dependencies required")
        for sha in pinned.values():
            self.workspace.blobs.read(str(sha))
        inputs = self.workspace.pinned_inputs(manifest)
        request = DirectBeamTaskInputs.read(inputs.get("direct_beam_visibility"))
        geometry = self.workspace.blobs.object(str(pinned["geometry"]))
        if digest(encode(inputs.get("geometry"))) != pinned["geometry"]:
            raise VersionUnavailable("geometry differs from the frozen project inputs")
        project_id, revision = manifest.get("project_id"), manifest.get("revision")
        if not isinstance(project_id, str) or type(revision) is not int:
            raise VersionUnavailable("frozen direct-beam project revision required")
        basis = self.workspace.blobs.object(str(pinned["woo.module_inputs"]))
        self.products.confirm_basis(basis)
        self.products.check_roof_inputs(inputs, basis)
        asset = self._owned_source(project_id, request.weather_asset_id, pinned)
        source = PvSource.read(
            self.workspace.blobs, asset.content_sha256, asset.metadata
        )
        control.checkpoint()
        # The complete original is parsed/hash-bound only in the worker. Solar
        # position and visibility subsequently use the explicit selected rows.
        weather = source.weather(self.weather_limits)
        weather_document = weather.document()
        weather_sha = digest(encode(weather_document))
        selection = FrozenWeatherSelection(
            schema_version=1,
            project_id=project_id,
            project_revision=revision,
            asset_id=asset.id,
            asset_metadata_sha256=asset.metadata_sha256,
            weather_document_sha256=weather_sha,
            row_indices=request.row_indices,
        )
        selection_document = selection.model_dump(mode="json")
        binding = DirectBeamBinding(
            schema_version=1,
            project_id=project_id,
            project_revision=revision,
            geometry_sha256=str(pinned["geometry"]),
            woo_module_basis_sha256=str(pinned["woo.module_inputs"]),
            weather_document_sha256=weather_sha,
            weather_asset_metadata_sha256=asset.metadata_sha256,
            weather_selection_sha256=digest(encode(selection_document)),
        )
        control.checkpoint()
        witness = prepare_direct_beam(
            geometry,
            basis,
            weather,
            asset.metadata,
            selection,
            binding,
            request.sampling,
            self.limits,
        )
        control.checkpoint()
        self._owned_source(project_id, asset.id, pinned)
        self.products.confirm_basis(basis)
        control.checkpoint()
        dependencies: Object = {
            **pinned,
            "weather.document": self.workspace.blobs.put_object(weather_document),
            "weather.selection": self.workspace.blobs.put_object(selection_document),
        }
        return {
            "schema": 1,
            "kind": self.kind,
            "project_id": project_id,
            "revision": revision,
            "input_sha256": manifest["input_sha256"],
            "manifest_sha256": manifest_sha,
            "runtime_sha256": self.runtime.sha256,
            "pinned_assets": pinned,
            "dependencies": dependencies,
            "visibility": witness,
            "frozen_geometry": geometry,
            "result_scope": "geometric_witness_not_a_profile_or_power_loss",
            "native_source_checks": {
                "owner": "native_owned_asset_at_admission",
                "revision": "durable_run_manifest_and_input_hash",
                "weather": "owned_asset_row_rechecked_after_compute",
                "woo": "current_basis_confirmed_before_and_after_compute",
                "publication": "standard_worker_jobs_lease_fence_required",
            },
            "consumer_scope": "sampled_geometry_only_no_power_profile",
            "equipment_release": {"status": "not_assessed"},
            "country_assessment": {"status": "not_assessed"},
            "near_shading_assessment": {
                "status": "not_assessed",
                "reason": "direct_beam_samples_are_not_a_complete_shading_assessment",
            },
        }
