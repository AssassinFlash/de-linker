"""Whole-workspace recovery proves committed WAL and immutable bytes survive."""

from __future__ import annotations

from pathlib import Path

import pytest

from linker_engine.planning import archive
from linker_engine.planning.errors import Conflict, VersionUnavailable
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.storage import Blobs
from linker_engine.planning.workspace import Workspace


def test_snapshot_restores_committed_wal_and_frozen_dependencies(
    workspace: Workspace, owner: Actor, context: Context, tmp_path: Path
) -> None:
    project = workspace.create(owner, "Factory", {"annual_load_kwh": 20}, key="new")
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=2)
    lease = Jobs(workspace).claim("worker", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    Jobs(workspace).complete(lease, {"fixture_only": True, "served": 20})
    # Keep a connection open, so backup cannot rely on last-close checkpoint.
    connection = workspace.database.connect()
    try:
        connection.execute("PRAGMA wal_autocheckpoint=0")
        workspace.revise(owner, project.id, 1, {"annual_load_kwh": 35}, key="edit")
        assert (
            workspace.database.path.with_name("workspace.sqlite-wal").stat().st_size > 0
        )
        destination = tmp_path / "backup"
        manifest = archive.backup(workspace, destination)
    finally:
        connection.close()
    assert archive.verify(destination) == manifest
    reopened = archive.restore(destination, tmp_path / "restored")
    assert reopened.get(owner, project.id).inputs == {"annual_load_kwh": 35}
    assert reopened.get(owner, project.id, revision=1).inputs == {"annual_load_kwh": 20}
    assert reopened.run(owner, run.id).result == {"fixture_only": True, "served": 20}
    assert not reopened.run(owner, run.id).is_current
    assert reopened.blobs.read(context.assets["weather"]) == b"frozen-fixture-weather"
    assert (destination.stat().st_mode & 0o777) == 0o700
    assert (reopened.database.path.stat().st_mode & 0o777) == 0o600


def test_write_during_blob_copy_does_not_change_the_database_snapshot(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = workspace.create(owner, "Project", {"load": 1}, key="new")
    workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=2)
    original = Blobs.put
    wrote = False

    def concurrent_write(blobs: Blobs, content: bytes) -> str:
        nonlocal wrote
        if blobs.directory != workspace.blobs.directory and not wrote:
            wrote = True
            workspace.revise(owner, project.id, 1, {"load": 2}, key="during-backup")
        return original(blobs, content)

    with monkeypatch.context() as patch:
        patch.setattr(Blobs, "put", concurrent_write)
        archive.backup(workspace, tmp_path / "backup")
    assert wrote and workspace.get(owner, project.id).revision == 2
    restored = archive.restore(tmp_path / "backup", tmp_path / "restored")
    assert restored.get(owner, project.id).revision == 1
    assert restored.get(owner, project.id).inputs == {"load": 1}


def test_missing_blob_rejects_restore_without_publishing_a_workspace(
    workspace: Workspace, owner: Actor, context: Context, tmp_path: Path
) -> None:
    project = workspace.create(owner, "Project", {}, key="new")
    workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=2)
    destination = tmp_path / "backup"
    archive.backup(workspace, destination)
    sha256 = context.assets["weather"]
    (destination / "blobs" / sha256[:2] / sha256).unlink()
    with pytest.raises(VersionUnavailable):
        archive.restore(destination, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_existing_workspace_and_backup_are_never_overwritten(
    workspace: Workspace, owner: Actor, tmp_path: Path
) -> None:
    project = workspace.create(owner, "Project", {}, key="new")
    destination = tmp_path / "backup"
    archive.backup(workspace, destination)
    with pytest.raises(Conflict):
        archive.backup(workspace, destination)
    with pytest.raises(Conflict):
        archive.restore(destination, workspace.database.path.parent)
    assert workspace.get(owner, project.id).id == project.id
