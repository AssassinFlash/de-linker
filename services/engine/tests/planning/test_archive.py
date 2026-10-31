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


def test_offline_collection_preserves_history_recursive_json_and_independent_backup(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    from linker_engine.planning.errors import LeaseLost
    from linker_engine.planning.retention import collect

    raw = workspace.blobs.put(b"\x00raw-weather-source")
    middle = workspace.blobs.put_object({"nested": [{"raw": raw}]})
    parent = workspace.blobs.put_object(
        {"references": [middle], "large": "x" * (2 * 1024 * 1024)}
    )
    runtime = workspace.blobs.put_object(
        {
            "schema": 1,
            "dependencies": {"numpy": "2.4.1", "pandas": "3.0.0"},
            "files": [],
        }
    )
    pinned = replace(
        context,
        assets={**context.assets, "source": parent, "runtime_snapshot": runtime},
    )
    project = workspace.create(owner, "History", {"retained": parent}, key="new")
    run = workspace.evaluate(
        owner, project.id, 1, pinned, key="old-run", max_attempts=2
    )
    jobs = Jobs(workspace)
    lease = jobs.claim("worker", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(lease, {"result": [parent]})
    workspace.revise(owner, project.id, 1, {"latest": True}, key="edit")
    cancelled = workspace.evaluate(
        owner, project.id, 2, pinned, key="cancelled", max_attempts=2
    )
    lost = jobs.claim("worker", kinds=("evaluate",), lease_seconds=30)
    assert lost is not None
    workspace.cancel(owner, cancelled.id)
    before = {p.name for p in workspace.blobs.directory.glob("*/*")}
    with pytest.raises(LeaseLost):
        jobs.complete(lost, {"unpublished_after_cancel": True})
    after = {p.name for p in workspace.blobs.directory.glob("*/*")}
    assert len(after - before) == 1
    orphan = (after - before).pop()
    interrupted = workspace.blobs.directory / orphan[:2] / (".incoming-" + "a" * 32)
    interrupted.write_bytes(b"interrupted")
    unknown = interrupted.with_name("unowned-file")
    unknown.write_bytes(b"preserve")
    lock = workspace.database.path.parent / ".cas.lock"
    assert not lock.exists()
    plan = collect(workspace.database.path.parent)
    assert plan["candidate_sha256"] == [orphan] and plan["advisory"] is True
    assert not lock.exists() and interrupted.exists()
    destination = tmp_path / "recovery"
    original = Blobs.put
    lock_checked = False

    def copy_with_gc_attempt(blobs: Blobs, content: bytes) -> str:
        nonlocal lock_checked
        if blobs.directory != workspace.blobs.directory and not lock_checked:
            lock_checked = True
            with pytest.raises(VersionUnavailable, match="already active"):
                collect(
                    workspace.database.path.parent,
                    apply=True,
                    offline=True,
                    recovery=destination,
                )
        return original(blobs, content)

    with monkeypatch.context() as patch:
        patch.setattr(Blobs, "put", copy_with_gc_attempt)
        archive.backup(workspace, destination)
    assert lock_checked
    verified = archive.verify(destination)
    with pytest.raises(VersionUnavailable, match="stopped"):
        collect(workspace.database.path.parent, apply=True, recovery=destination)
    applied = collect(
        workspace.database.path.parent,
        apply=True,
        offline=True,
        recovery=destination,
        snapshots=(destination,),
    )
    assert applied["deleted_count"] == 1 and applied["temporary_deleted_count"] == 1
    assert not interrupted.exists() and unknown.read_bytes() == b"preserve"
    assert workspace.get(owner, project.id, revision=1).inputs == {"retained": parent}
    assert workspace.run(owner, run.id).result == {"result": [parent]}
    for sha in (parent, middle, raw, runtime):
        workspace.blobs.read(sha)
    assert collect(workspace.database.path.parent)["candidate_count"] == 0
    # A complete snapshot retains its own orphan, never pinning the source CAS.
    assert archive.verify(destination) == verified
    assert Blobs(destination / "blobs").read(orphan)


def test_collection_refuses_incomplete_graph_recovery_and_external_snapshots_before_deletion(
    workspace: Workspace,
    owner: Actor,
    tmp_path: Path,
) -> None:
    from linker_engine.planning.retention import collect

    project = workspace.create(owner, "Project", {}, key="new")
    recovery = tmp_path / "recovery"
    archive.backup(workspace, recovery)
    orphan = workspace.blobs.put(b"not-covered-by-older-recovery")
    directory = workspace.database.path.parent
    with pytest.raises(VersionUnavailable, match="does not cover"):
        collect(directory, apply=True, offline=True, recovery=recovery)
    database_only = tmp_path / "database-only"
    database_only.mkdir()
    (database_only / "workspace.sqlite").write_bytes(
        (recovery / "workspace.sqlite").read_bytes()
    )
    with pytest.raises(VersionUnavailable):
        collect(
            directory,
            apply=True,
            offline=True,
            recovery=recovery,
            snapshots=(database_only,),
        )
    shared = tmp_path / "shared-cas"
    shared.mkdir()
    (shared / "blobs").symlink_to(workspace.blobs.directory)
    with pytest.raises(VersionUnavailable, match="independent"):
        collect(
            directory, apply=True, offline=True, recovery=recovery, snapshots=(shared,)
        )
    broken = workspace.blobs.put(b'{"broken":')
    workspace.revise(owner, project.id, 1, {"nested": [broken]}, key="broken")
    with pytest.raises(VersionUnavailable, match="JSON"):
        collect(directory, apply=True, offline=True, recovery=recovery)
    assert workspace.blobs.read(orphan) == b"not-covered-by-older-recovery"
    (workspace.blobs.directory / broken[:2] / broken).unlink()
    # An explicit dependency is strict even when its hash no longer exists.
    with workspace.database.transaction() as connection:
        content = workspace.blobs.put_object({"dependencies": {"raw": broken}})
        connection.execute("UPDATE idempotency SET receipt_sha256=?", (content,))
    with pytest.raises(VersionUnavailable, match="unavailable"):
        collect(directory, apply=True, offline=True, recovery=recovery)
    assert workspace.blobs.read(orphan)


@pytest.mark.parametrize("name", ["workspace.sqlite", "backup.json"])
def test_recovery_rejects_external_database_and_manifest_aliases(
    workspace: Workspace,
    owner: Actor,
    tmp_path: Path,
    name: str,
) -> None:
    from linker_engine.planning.retention import collect

    workspace.create(owner, "Project", {}, key="new")
    orphan = workspace.blobs.put(b"unique-unreferenced-result")
    recovery = tmp_path / "recovery"
    archive.backup(workspace, recovery)
    outside = tmp_path / ("external-" + name)
    (recovery / name).rename(outside)
    (recovery / name).symlink_to(outside)
    # All bytes still hash correctly; dependence on this external mutable file
    # is what disqualifies the recovery point before the first CAS unlink.
    with pytest.raises(VersionUnavailable, match="independent"):
        collect(
            workspace.database.path.parent, apply=True, offline=True, recovery=recovery
        )
    assert workspace.blobs.read(orphan) == b"unique-unreferenced-result"


def test_collection_refuses_source_database_alias_before_any_write(
    workspace: Workspace,
    owner: Actor,
    tmp_path: Path,
) -> None:
    from linker_engine.planning.retention import collect

    workspace.create(owner, "Project", {}, key="new")
    outside = tmp_path / "external.sqlite"
    workspace.database.path.rename(outside)
    workspace.database.path.symlink_to(outside)
    before = set(workspace.database.path.parent.rglob("*"))
    with pytest.raises(VersionUnavailable, match="symbolic links"):
        collect(workspace.database.path.parent)
    assert set(workspace.database.path.parent.rglob("*")) == before
    assert not (workspace.database.path.parent / ".cas.lock").exists()


def test_plan_never_creates_sqlite_sidecars_or_changes_existing_wal_state(
    workspace: Workspace,
    owner: Actor,
) -> None:
    from linker_engine.planning.retention import collect

    workspace.create(owner, "Project", {}, key="new")
    directory = workspace.database.path.parent
    before = {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in directory.rglob("*")
        if p.is_file()
    }
    assert collect(directory)["mode"] == "plan"
    assert {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in directory.rglob("*")
        if p.is_file()
    } == before
    connection = workspace.database.connect()
    try:
        connection.execute("PRAGMA wal_autocheckpoint=0")
        workspace.revise(
            owner, workspace.projects(owner)[0].id, 1, {"pending": True}, key="wal"
        )
        before = {
            p: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in directory.rglob("*")
            if p.is_file()
        }
        with pytest.raises(VersionUnavailable, match="WAL state"):
            collect(directory)
        assert {
            p: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in directory.rglob("*")
            if p.is_file()
        } == before
    finally:
        connection.close()


def test_transitive_explicit_cas_dependency_is_required_even_when_absent(
    workspace: Workspace,
    owner: Actor,
) -> None:
    from linker_engine.planning.retention import collect

    missing = "a" * 64
    child = workspace.blobs.put_object({"dependencies": {"raw_source": missing}})
    workspace.create(owner, "Project", {"nested": [{"child": child}]}, key="new")
    with pytest.raises(VersionUnavailable, match="unavailable"):
        collect(workspace.database.path.parent)
