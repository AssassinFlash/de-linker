"""Owned frozen-weather/roof preparation through the actual durable worker."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from .asset_publication import AssetPublication, AssetResult
from .assets import Asset, Assets
from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput, VersionUnavailable
from .execution_identity import execution_key, request_execution_key
from .frozen_run import frozen_manifest
from .pv_parameters import PvGenerationLimits, PvGenerationParameters
from .pv_profile_preparation import PROFILE_PURPOSE, prepare_profile
from .pv_source import PvSource
from .records import Actor, Context, Lease, Run
from .runtime_snapshot import RuntimeSnapshot
from .weather_import import WEATHER_PURPOSE
from .worker import Control
from .workspace import Workspace


class PvPreparationInputs(Document):
    schema_version: SchemaVersion
    weather_asset_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


def check_pv_preparation(
    assets: Assets, actor: Actor, project_id: str | None, inputs: Object
) -> None:
    if "pv_preparation" not in inputs:
        return
    if project_id is None:
        raise InvalidInput("a new project cannot reference another project's weather")
    selected_weather(assets, actor, project_id, inputs)


def selected_weather(
    assets: Assets, actor: Actor, project_id: str, inputs: Object
) -> Asset:
    selection = PvPreparationInputs.read(inputs.get("pv_preparation"))
    asset = assets.get(actor, project_id, selection.weather_asset_id)
    require_weather_source(asset.purpose, asset.metadata)
    return asset


def require_weather_source(purpose: str, metadata: Object) -> None:
    if (
        purpose != WEATHER_PURPOSE
        or metadata.get("source_type") != WEATHER_PURPOSE
        or type(metadata.get("schema")) is not int
        or metadata.get("schema") != 1
        or metadata.get("retention") != "permanent"
    ):
        raise InvalidInput("trusted original TMY weather source required")


class PvReferenceKernel:
    kind = "prepare_roof_pv_reference_v1"
    models = {
        "task": kind,
        "generation": "uniform_unshaded_pvlib_reference_v1",
        "weather": "pvgis_5_3_tmy_explicit_two_axes_v1",
        "pvlib": "0.16.1",
    }

    def __init__(self, workspace: Workspace, limits: PvGenerationLimits) -> None:
        self.workspace = workspace
        # Freeze deployment settings against later caller mutations.
        self.limits = PvGenerationLimits.read(limits.model_dump(mode="json"))
        self.runtime = RuntimeSnapshot.capture()
        self.workspace.blobs.put(self.runtime.content)

    def parameters(self) -> Object:
        return {"kind": self.kind, "limits": {**self.limits.model_dump(mode="json")}}

    def execution_key(self) -> str:
        return execution_key(
            {
                "code_sha256": self.runtime.sha256,
                "models": dict(self.models),
                "parameters": self.parameters(),
            }
        )

    def context(self, actor: Actor, project_id: str, inputs: Object) -> Context:
        PvGenerationParameters.read(inputs.get("pv_generation"))
        source = selected_weather(Assets(self.workspace), actor, project_id, inputs)
        return Context(
            self.runtime.sha256,
            dict(self.models),
            {
                "runtime_bundle": self.runtime.sha256,
                "weather.raw": source.content_sha256,
                "weather.metadata": source.metadata_sha256,
            },
            self.parameters(),
        )

    def __call__(self, lease: Lease, control: Control) -> AssetResult:
        control.checkpoint()
        manifest_hash = lease.request.get("manifest_sha256")
        if not isinstance(manifest_hash, str):
            raise VersionUnavailable("PV preparation has no pinned manifest")
        manifest = frozen_manifest(self.workspace, lease, manifest_hash)
        if (
            request_execution_key(lease.request, manifest, manifest_hash)
            != self.execution_key()
        ):
            raise VersionUnavailable(
                "this worker cannot prepare the pinned PV model/settings"
            )
        context = manifest.get("context")
        assert isinstance(context, dict)  # request_execution_key checked its shape.
        pinned = context.get("assets")
        if (
            not isinstance(pinned, dict)
            or set(pinned) != {"runtime_bundle", "weather.raw", "weather.metadata"}
            or any(not isinstance(x, str) for x in pinned.values())
        ):
            raise VersionUnavailable("exact PV preparation dependencies required")
        if pinned["runtime_bundle"] != self.runtime.sha256:
            raise VersionUnavailable("PV runtime bundle differs from the executor")
        for value in pinned.values():
            self.workspace.blobs.read(str(value))
        inputs = self.workspace.pinned_inputs(manifest)
        selection = PvPreparationInputs.read(inputs.get("pv_preparation"))
        with self.workspace.database.read() as connection:
            row = connection.execute(
                "SELECT * FROM project_assets WHERE project_id=? AND id=?",
                (manifest["project_id"], selection.weather_asset_id),
            ).fetchone()
        if (
            row is None
            or row["content_sha256"] != pinned["weather.raw"]
            or row["metadata_sha256"] != pinned["weather.metadata"]
        ):
            raise VersionUnavailable(
                "weather does not match the frozen project's owned source"
            )
        source_metadata = self.workspace.blobs.object(str(pinned["weather.metadata"]))
        require_weather_source(row["purpose"], source_metadata)
        source = PvSource.read(
            self.workspace.blobs, str(pinned["weather.raw"]), source_metadata
        )
        control.checkpoint()
        revision = manifest["revision"]
        if type(revision) is not int:
            raise VersionUnavailable("PV revision required")
        metadata = prepare_profile(
            self.workspace.blobs, inputs, revision, source, self.limits
        )
        control.checkpoint()
        publication = AssetPublication.prepare(
            self.workspace.blobs,
            str(manifest["project_id"]),
            source.content,
            "application/json",
            PROFILE_PURPOSE,
            metadata,
        )
        return AssetResult(
            {
                "schema": 1,
                "kind": self.kind,
                "project_id": manifest["project_id"],
                "revision": revision,
                "input_sha256": manifest["input_sha256"],
                "manifest_sha256": manifest_hash,
                "runtime_sha256": self.runtime.sha256,
                "pinned_assets": pinned,
                "profile_summary": metadata["interpretation"],
                "dependencies": metadata["dependencies"],
                "equipment_release": {"status": "not_assessed"},
                "country_assessment": {"status": "not_assessed"},
                "near_shading_assessment": {"status": "not_assessed"},
            },
            publication,
        )


class PvPreparationService:
    def __init__(
        self, workspace: Workspace, kernel: PvReferenceKernel, *, max_attempts: int
    ) -> None:
        if kernel.workspace is not workspace:
            raise InvalidInput("PV preparation must share project authority")
        self.workspace, self.kernel, self.max_attempts = workspace, kernel, max_attempts

    def evaluate(
        self, actor: Actor, project_id: str, expected_revision: int, *, key: str
    ) -> Run:
        project = self.workspace.get(actor, project_id, revision=expected_revision)
        return self.workspace.evaluate(
            actor,
            project_id,
            expected_revision,
            self.kernel.context(actor, project_id, project.inputs),
            key=key,
            max_attempts=self.max_attempts,
            intent={"kind": self.kernel.kind},
        )
