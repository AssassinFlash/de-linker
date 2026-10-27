"""Bind worker dependencies to this durable run, revision and owned asset IDs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .assets import Asset
from .canonical import Object
from .energy_inputs import EnergyInputs
from .errors import VersionUnavailable
from .profile_assets import profile_dependencies
from .records import Lease
from .workspace import Workspace


@dataclass(frozen=True)
class FrozenEnergyExecution:
    workspace: Workspace
    manifest_hash: str
    manifest: Object
    inputs: Object
    pinned: Object
    runtime_sha256: str

    def dependency(self, name: str) -> str:
        value = self.pinned.get(name)
        if not isinstance(value, str):
            raise VersionUnavailable(f"pinned dependency missing: {name}")
        self.workspace.blobs.read(value)
        return value

    def result(self, kind: str, physical: Object) -> Object:
        return {
            "schema": 1,
            "kind": kind,
            "project_id": self.manifest.get("project_id"),
            "revision": self.manifest.get("revision"),
            "input_sha256": self.manifest.get("input_sha256"),
            "manifest_sha256": self.manifest_hash,
            "runtime_sha256": self.runtime_sha256,
            **physical,
            "pinned_assets": self.pinned,
            "equipment_release": {
                "status": "not_assessed",
                "reason": "explicit_scenario_replay_is_not_equipment_release",
            },
            "country_assessment": {
                "status": "not_assessed",
                "reason": "country_rules_are_a_separate_assessment",
            },
        }


def frozen_energy_execution(
    workspace: Workspace,
    lease: Lease,
    *,
    runtime_sha256: str,
    models: Mapping[str, str],
    parameters: Object,
) -> FrozenEnergyExecution:
    manifest_hash = lease.request.get("manifest_sha256")
    if not isinstance(manifest_hash, str):
        raise VersionUnavailable("evaluation has no pinned manifest")
    manifest = frozen_manifest(workspace, lease, manifest_hash)
    context = manifest.get("context")
    if (
        not isinstance(context, dict)
        or context.get("code_sha256") != runtime_sha256
        or context.get("models") != models
    ):
        raise VersionUnavailable("this worker cannot execute the pinned runtime/models")
    if context.get("parameters") != parameters:
        raise VersionUnavailable(
            "this worker cannot execute the pinned numerical settings"
        )
    pinned = context.get("assets")
    if not isinstance(pinned, dict) or any(
        not isinstance(value, str) for value in pinned.values()
    ):
        raise VersionUnavailable("pinned dependency hashes required")
    execution = FrozenEnergyExecution(
        workspace,
        manifest_hash,
        manifest,
        workspace.pinned_inputs(manifest),
        pinned,
        runtime_sha256,
    )
    if execution.dependency("runtime_bundle") != runtime_sha256:
        raise VersionUnavailable("runtime bundle and code identity differ")
    return execution


def frozen_manifest(workspace: Workspace, lease: Lease, manifest_hash: str) -> Object:
    manifest = workspace.blobs.object(manifest_hash)
    with workspace.database.read() as connection:
        row = connection.execute(
            "SELECT runs.*, revisions.input_sha256 FROM runs JOIN revisions "
            "ON revisions.project_id=runs.project_id AND revisions.number=runs.revision "
            "WHERE runs.id=?",
            (lease.run_id,),
        ).fetchone()
        if (
            row is None
            or any(
                manifest.get(name) != row[name]
                for name in ("project_id", "revision", "input_sha256")
            )
            or row["manifest_sha256"] != manifest_hash
            or type(manifest.get("schema")) is not int
            or manifest.get("schema") != 1
        ):
            raise VersionUnavailable("manifest does not belong to this frozen run")
    return manifest


def bind_energy_assets(
    workspace: Workspace,
    manifest: Object,
    scenario: EnergyInputs,
    inputs: Object,
    pinned: Object,
) -> None:
    expected = {"runtime_bundle", "battery.raw", "battery.metadata"}
    if "equipment_selection" in inputs:
        expected.update({"woo.equipment_inputs", "equipment.selection"})
        selection = pinned.get("equipment.selection")
        if (
            not isinstance(selection, str)
            or workspace.blobs.object(selection) != inputs["equipment_selection"]
        ):
            raise VersionUnavailable(
                "energy equipment differs from its frozen selection"
            )
    references = {
        **scenario.profiles(),
        "battery": scenario.battery_parameters_asset_id,
    }
    with workspace.database.read() as connection:
        for role, asset_id in references.items():
            row = connection.execute(
                "SELECT content_sha256, metadata_sha256, purpose, media_type FROM project_assets WHERE project_id=? AND id=?",
                (manifest["project_id"], asset_id),
            ).fetchone()
            if (
                row is None
                or pinned.get(f"{role}.raw") != row["content_sha256"]
                or pinned.get(f"{role}.metadata") != row["metadata_sha256"]
                or (role == "battery" and row["purpose"] != "battery_parameters_v1")
            ):
                raise VersionUnavailable(
                    "dependency does not match the frozen project asset"
                )
            if role != "battery":
                # The durable manifest is already bound to the run and project.
                # Use only the owned rows selected above, with no latest lookup.
                asset = Asset(
                    asset_id,
                    str(manifest["project_id"]),
                    row["content_sha256"],
                    row["media_type"],
                    row["purpose"],
                    row["metadata_sha256"],
                    workspace.blobs.object(row["metadata_sha256"]),
                )
                dependencies = profile_dependencies(
                    asset, role, inputs, workspace.blobs
                )
                if any(
                    pinned.get(name) != value for name, value in dependencies.items()
                ):
                    raise VersionUnavailable(
                        "profile dependency differs from its frozen asset"
                    )
                expected.update(dependencies)
            elif scenario.coupling == "shared_dc":
                metadata = workspace.blobs.object(row["metadata_sha256"])
                children = metadata.get("dependencies")
                if not isinstance(children, dict) or set(children) != {
                    "dc_prepared_parameters",
                    "dc_woo_inputs",
                }:
                    raise VersionUnavailable(
                        "frozen DC parameters have no server-prepared source dependencies"
                    )
                for name, sha in children.items():
                    if not isinstance(sha, str) or pinned.get(f"battery.{name}") != sha:
                        raise VersionUnavailable(
                            "DC parameter dependency differs from the frozen owned asset"
                        )
                    workspace.blobs.read(sha)
                    expected.add(f"battery.{name}")
    if set(pinned) != expected:
        raise VersionUnavailable(
            "energy dependency roles differ from the frozen inputs"
        )
