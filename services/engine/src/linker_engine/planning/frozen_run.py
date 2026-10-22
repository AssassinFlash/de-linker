"""Bind worker dependencies to this durable run, revision and owned asset IDs."""

from __future__ import annotations

from .canonical import Object
from .energy_inputs import EnergyInputs
from .errors import VersionUnavailable
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
            or manifest.get("schema") != 1
        ):
            raise VersionUnavailable("manifest does not belong to this frozen run")
    return manifest


def bind_energy_assets(
    workspace: Workspace, manifest: Object, scenario: EnergyInputs, pinned: Object
) -> None:
    expected = {"runtime_bundle", "battery.raw", "battery.metadata"}
    expected.update(
        f"{role}.{part}"
        for role in scenario.profiles()
        for part in ("raw", "metadata", "timezone")
    )
    if set(pinned) != expected:
        raise VersionUnavailable(
            "energy dependency roles differ from the frozen inputs"
        )
    references = {
        **scenario.profiles(),
        "battery": scenario.battery_parameters_asset_id,
    }
    with workspace.database.read() as connection:
        for role, asset_id in references.items():
            row = connection.execute(
                "SELECT content_sha256, metadata_sha256, purpose FROM project_assets WHERE project_id=? AND id=?",
                (manifest["project_id"], asset_id),
            ).fetchone()
            purpose = "battery_parameters_v1" if role == "battery" else "csv_profile_v1"
            if (
                row is None
                or row["purpose"] != purpose
                or pinned[f"{role}.raw"] != row["content_sha256"]
                or pinned[f"{role}.metadata"] != row["metadata_sha256"]
            ):
                raise VersionUnavailable(
                    "dependency does not match the frozen project asset"
                )
