"""Bind worker dependencies to this durable run, revision and owned asset IDs."""

from __future__ import annotations

from .assets import Asset
from .canonical import Object
from .energy_inputs import EnergyInputs
from .errors import VersionUnavailable
from .profile_assets import profile_dependencies
from .records import Lease
from .workspace import Workspace


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
