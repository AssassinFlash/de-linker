"""Business history, isolation and retries through the project authority."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from linker_engine.planning import commands
from linker_engine.planning.canonical import Object
from linker_engine.planning.errors import (
    Conflict,
    InvalidInput,
    NotFound,
    VersionUnavailable,
)
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context, Project
from linker_engine.planning.workspace import Workspace


def test_refresh_reopens_the_same_project_and_frozen_run(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    project = workspace.create(owner, "Warehouse", {"load_kwh": 12}, key="new")
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=3)
    jobs = Jobs(workspace)
    lease = jobs.claim("worker-a", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    revision = workspace.revise(owner, project.id, 1, {"load_kwh": 28}, key="edit")
    # A current edit cannot mutate a run already queued or executing.
    assert workspace.pinned_inputs(run.manifest) == {"load_kwh": 12}
    published = jobs.complete(lease, {"fixture_only": True, "value": 12})
    reopened = Workspace(workspace.database.path.parent, clock=workspace.clock)
    assert reopened.get(owner, project.id).revision == revision.revision == 2
    assert reopened.get(owner, project.id, revision=1).inputs == {"load_kwh": 12}
    history = reopened.run(owner, run.id)
    assert history.result_sha256 == published
    assert history.result == {"fixture_only": True, "value": 12}
    assert history.state == "succeeded" and not history.is_current
    assert reopened.blobs.read(context.assets["weather"]) == b"frozen-fixture-weather"


def test_lost_acknowledgement_does_not_duplicate_or_roll_back_inputs(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    first = workspace.create(owner, "Home", {"load": 1}, key="new")
    second = workspace.revise(owner, first.id, 1, {"load": 2}, key="edit")
    run = workspace.evaluate(owner, first.id, 2, context, key="run", max_attempts=2)
    workspace.revise(owner, first.id, 2, {"load": 3}, key="later")
    assert workspace.create(owner, "Home", {"load": 1}, key="new").revision == 1
    assert workspace.revise(owner, first.id, 1, {"load": 2}, key="edit") == second
    repeated = workspace.evaluate(
        owner, first.id, 2, context, key="run", max_attempts=2
    )
    assert repeated.id == run.id and not repeated.is_current
    assert len(workspace.runs(owner, first.id)) == len(workspace.projects(owner)) == 1
    assert workspace.get(owner, first.id).inputs == {"load": 3}
    with pytest.raises(Conflict):
        workspace.revise(owner, first.id, 1, {"load": 5}, key="edit")
    with pytest.raises(Conflict):
        workspace.evaluate(owner, first.id, 2, context, key="run", max_attempts=3)


def test_old_tab_cannot_overwrite_a_newer_revision(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Project", {"load": 1}, key="new")
    barrier = Barrier(2)

    def edit(value: int) -> Project | str:
        separate_process = Workspace(
            workspace.database.path.parent, clock=workspace.clock
        )
        barrier.wait()
        try:
            return separate_process.revise(
                owner, project.id, 1, {"load": value}, key=f"tab-{value}"
            )
        except Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = list(pool.map(edit, [2, 3]))
    assert attempts.count("conflict") == 1
    successful = [item for item in attempts if isinstance(item, Project)]
    assert len(successful) == 1
    assert workspace.get(owner, project.id) == successful[0]
    with workspace.database.read() as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_parallel_retry_enqueues_one_run(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    project = workspace.create(owner, "Project", {}, key="new")
    barrier = Barrier(2)

    def enqueue(_: int) -> str:
        separate_process = Workspace(
            workspace.database.path.parent, clock=workspace.clock
        )
        barrier.wait()
        return separate_process.evaluate(
            owner, project.id, 1, context, key="same-request", max_attempts=3
        ).id

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(enqueue, [1, 2]))
    assert results[0] == results[1]
    with workspace.database.read() as connection:
        assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1


def test_foreign_owner_cannot_read_history_run_or_cancel(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    project = workspace.create(owner, "Private", {}, key="new")
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=2)
    stranger = Actor("user", "wordpress:18")
    assert workspace.projects(stranger) == []
    for operation in (
        lambda: workspace.get(stranger, project.id),
        lambda: workspace.get(stranger, project.id, revision=1),
        lambda: workspace.run(stranger, run.id),
        lambda: workspace.runs(stranger, project.id),
        lambda: workspace.cancel(stranger, run.id),
        lambda: workspace.revise(stranger, project.id, 1, {}, key="edit"),
        lambda: workspace.evaluate(
            stranger, project.id, 1, context, key="run", max_attempts=2
        ),
    ):
        with pytest.raises(NotFound):
            operation()
    # Team identities are server-verified; they are not browser-selectable.
    assert workspace.get(Actor("team", "operator:1"), project.id).id == project.id
    assert workspace.run(owner, run.id).state == "queued"


def test_verified_guest_transfer_revokes_guest_and_retains_history(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    guest = Actor("guest", "opaque-cookie")
    project = workspace.create(guest, "Guest project", {}, key="new")
    run = workspace.evaluate(guest, project.id, 1, context, key="run", max_attempts=2)
    claimed = workspace.claim_guest(guest, owner, project.id, key="sign-in")
    assert workspace.claim_guest(guest, owner, project.id, key="sign-in") == claimed
    assert workspace.run(owner, run.id).project_id == project.id
    assert workspace.projects(guest) == []
    with pytest.raises(NotFound):
        workspace.run(guest, run.id)
    with pytest.raises(NotFound):
        workspace.claim_guest(
            guest, Actor("user", "wordpress:99"), project.id, key="steal"
        )
    with pytest.raises(NotFound):
        workspace.create(guest, "Guest project", {}, key="new")


def test_team_read_permission_never_grants_customer_write_permission(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    project = workspace.create(owner, "Customer", {"load": 1}, key="new")
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=2)
    team = Actor("team", "operator:1")
    assert workspace.get(team, project.id, revision=1).inputs == {"load": 1}
    assert workspace.run(team, run.id).id == run.id
    assert workspace.runs(team, project.id)[0].id == run.id
    for operation in (
        lambda: workspace.revise(team, project.id, 1, {"load": 999}, key="edit"),
        lambda: workspace.evaluate(
            team, project.id, 1, context, key="run", max_attempts=2
        ),
        lambda: workspace.cancel(team, run.id),
    ):
        with pytest.raises(NotFound):
            operation()
    assert workspace.get(owner, project.id).inputs == {"load": 1}
    assert workspace.get(owner, project.id).revision == 1
    assert workspace.run(owner, run.id).state == "queued"
    assert len(workspace.runs(owner, project.id)) == 1


def test_failed_commit_has_no_acknowledged_project(
    workspace: Workspace, owner: Actor, monkeypatch: pytest.MonkeyPatch
) -> None:
    def disk_failure(*_: object) -> None:
        raise OSError("fixture: receipt cannot be written")

    with monkeypatch.context() as patch:
        patch.setattr(commands, "remember", disk_failure)
        with pytest.raises(OSError):
            workspace.create(owner, "Interrupted", {"load": 5}, key="new")
    assert workspace.projects(owner) == []
    project = workspace.create(owner, "Interrupted", {"load": 5}, key="new")
    assert project.revision == 1


def test_missing_pinned_data_cannot_create_a_run(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    project = workspace.create(owner, "Project", {}, key="new")
    pinned = context.assets["weather"]
    (workspace.blobs.directory / pinned[:2] / pinned).unlink()
    with pytest.raises(VersionUnavailable):
        workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=2)
    assert workspace.runs(owner, project.id) == []


def test_corrupt_pinned_input_is_visible_instead_of_recalculated(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Project", {"load": 5}, key="new")
    pinned = project.input_sha256
    (workspace.blobs.directory / pinned[:2] / pinned).write_bytes(b'{"load":999}')
    with pytest.raises(VersionUnavailable, match="hash mismatch"):
        workspace.get(owner, project.id)


@pytest.mark.parametrize("inputs", [{"load": float("nan")}, {"load": float("inf")}])
def test_nonfinite_input_does_not_enter_history(
    workspace: Workspace, owner: Actor, inputs: Object
) -> None:
    with pytest.raises(InvalidInput):
        workspace.create(owner, "Project", inputs, key="new")
    assert workspace.projects(owner) == []


def test_future_database_is_not_downgraded(tmp_path: Path) -> None:
    path = tmp_path / "workspace.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=999")
    with pytest.raises(VersionUnavailable):
        Workspace(tmp_path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 999
