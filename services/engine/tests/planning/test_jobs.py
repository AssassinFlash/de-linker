"""Restart, cancellation, timeout, retry and concurrent worker ownership."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

import pytest

from linker_engine.planning.asset_publication import AssetPublication
from linker_engine.planning.errors import Conflict, LeaseLost
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context, Lease, Run
from linker_engine.planning.workspace import Workspace

from .conftest import Clock, FixtureObject


@pytest.fixture
def run(workspace: Workspace, owner: Actor, context: Context) -> Run:
    project = workspace.create(owner, "Project", {}, key="new")
    return workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=2)


def take(jobs: Jobs, worker: str = "worker-a") -> Lease:
    lease = jobs.claim(worker, kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    return lease


def test_two_workers_cannot_own_the_same_attempt(
    workspace: Workspace, run: Run
) -> None:
    barrier = Barrier(2)

    def claim(name: str) -> Lease | None:
        barrier.wait()
        return Jobs(workspace).claim(name, kinds=("evaluate",), lease_seconds=30)

    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = list(pool.map(claim, ["worker-a", "worker-b"]))
    assert len([item for item in attempts if item is not None]) == 1
    assert attempts.count(None) == 1


def test_expired_attempt_cannot_renew_or_publish_even_before_reassignment(
    workspace: Workspace, owner: Actor, run: Run, clock: Clock
) -> None:
    jobs = Jobs(workspace)
    first = take(jobs)
    clock.advance(30)
    with pytest.raises(LeaseLost):
        jobs.heartbeat(first, lease_seconds=30)
    with pytest.raises(LeaseLost):
        jobs.complete(first, {"value": "late"})
    second = take(jobs, "worker-b")
    assert second.attempt == 2 and second.token != first.token
    for old in (first, replace(second, token=first.token)):
        with pytest.raises(LeaseLost):
            jobs.complete(old, {"value": "stale"})
    output = jobs.complete(second, {"value": "current"})
    clock.advance(10_000)
    assert jobs.complete(second, {"value": "current"}) == output
    with pytest.raises(Conflict):
        jobs.complete(second, {"value": "changed after publication"})
    assert workspace.run(owner, run.id).result == {"value": "current"}


def test_heartbeat_extends_execution_but_not_another_attempt(
    workspace: Workspace, owner: Actor, run: Run, clock: Clock
) -> None:
    jobs = Jobs(workspace)
    first = take(jobs)
    clock.advance(20)
    assert jobs.heartbeat(first, lease_seconds=30) == clock() + 30
    clock.advance(11)
    assert jobs.claim("other", kinds=("evaluate",), lease_seconds=30) is None
    jobs.complete(first, {"value": "heartbeating"})
    assert workspace.run(owner, run.id).state == "succeeded"


def test_crash_after_last_attempt_becomes_a_named_failure(
    workspace: Workspace, owner: Actor, run: Run, clock: Clock
) -> None:
    first_process = Jobs(workspace)
    take(first_process)
    clock.advance(31)
    # A restarted process shares durable state, not an in-memory task queue.
    restarted = Jobs(Workspace(workspace.database.path.parent, clock=clock))
    assert take(restarted, "worker-restarted").attempt == 2
    clock.advance(31)
    assert restarted.claim("third", kinds=("evaluate",), lease_seconds=30) is None
    failed = workspace.run(owner, run.id)
    assert failed.state == "failed" and failed.result is None
    assert failed.error == {"code": "attempts_exhausted", "retryable": False}


def test_typed_failure_retries_only_after_its_delay(
    workspace: Workspace, owner: Actor, run: Run, clock: Clock
) -> None:
    jobs = Jobs(workspace)
    lease = take(jobs)
    jobs.fail(lease, {"code": "fixture_transient"}, retry_after=10)
    assert workspace.run(owner, run.id).state == "retry_wait"
    assert jobs.claim("early", kinds=("evaluate",), lease_seconds=30) is None
    clock.advance(10)
    retry = take(jobs)
    jobs.fail(retry, {"code": "fixture_transient"}, retry_after=10)
    assert workspace.run(owner, run.id).state == "failed"
    with pytest.raises(LeaseLost):
        jobs.complete(retry, {"value": "after failure"})


def test_cancelled_attempt_cannot_publish_or_retry(
    workspace: Workspace, owner: Actor, run: Run
) -> None:
    jobs = Jobs(workspace)
    lease = take(jobs)
    assert workspace.cancel(owner, run.id).state == "cancelled"
    with pytest.raises(LeaseLost):
        jobs.complete(lease, {"value": "finished after cancel"})
    with pytest.raises(LeaseLost):
        jobs.fail(lease, {"code": "fixture_transient"}, retry_after=1)
    assert workspace.run(owner, run.id).result is None
    assert jobs.claim("next", kinds=("evaluate",), lease_seconds=30) is None


def test_related_report_files_publish_and_replay_atomically(
    workspace: Workspace, owner: Actor, run: Run
) -> None:
    jobs, lease = Jobs(workspace), take(Jobs(workspace))
    metadata: FixtureObject = {
        "retention": "permanent",
        "provenance": {
            "label": "Owned report",
            "basis": "Synthetic publication fixture",
            "rights_basis": "Owned fixture",
        },
    }
    pdf, csv_asset = (
        AssetPublication.prepare(
            workspace.blobs, run.project_id, content, media, purpose, metadata
        )
        for content, media, purpose in (
            (b"%PDF-fixture", "application/pdf", "report"),
            (b"item,quantity\n", "text/csv", "materials"),
        )
    )
    with workspace.database.transaction() as connection:
        connection.execute(
            "CREATE TRIGGER reject_csv BEFORE INSERT ON project_assets WHEN NEW.purpose='materials' BEGIN SELECT RAISE(ABORT,'fixture'); END"
        )
    with pytest.raises(sqlite3.DatabaseError):
        jobs.complete(
            lease, {"value": "paired"}, asset=pdf, attachments={"materials": csv_asset}
        )
    with workspace.database.transaction() as connection:
        assert (
            connection.execute("SELECT count(*) FROM project_assets").fetchone()[0] == 0
        )
        connection.execute("DROP TRIGGER reject_csv")
    assert workspace.run(owner, run.id).result is None
    sha = jobs.complete(
        lease, {"value": "paired"}, asset=pdf, attachments={"materials": csv_asset}
    )
    assert (
        jobs.complete(
            lease, {"value": "paired"}, asset=pdf, attachments={"materials": csv_asset}
        )
        == sha
    )
    with workspace.database.read() as connection:
        assert (
            connection.execute("SELECT count(*) FROM project_assets").fetchone()[0] == 2
        )


@pytest.mark.parametrize("damage", ["missing", "invalid_hash"])
def test_corrupt_queue_request_fails_without_blocking_other_work(
    workspace: Workspace,
    owner: Actor,
    run: Run,
    context: Context,
    clock: Clock,
    damage: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with workspace.database.read() as connection:
        sha = connection.execute(
            "SELECT request_sha256 FROM jobs WHERE run_id=?", (run.id,)
        ).fetchone()[0]
    if damage == "missing":
        (workspace.blobs.directory / sha[:2] / sha).unlink()
    else:
        with workspace.database.transaction() as connection:
            connection.execute(
                "UPDATE jobs SET request_sha256='invalid-hash' WHERE run_id=?",
                (run.id,),
            )
    clock.advance(1)
    # Equal manifests share request bytes; a new revision has independent bytes.
    workspace.revise(owner, run.project_id, 1, {"load": 2}, key="edit")
    healthy = workspace.evaluate(
        owner, run.project_id, 2, context, key="healthy", max_attempts=2
    )
    claimed = take(Jobs(workspace))
    assert claimed.run_id == healthy.id
    broken = workspace.run(owner, run.id)
    assert broken.state == "failed"
    assert broken.error == {"code": "version_unavailable", "retryable": False}
    assert (
        "version_unavailable during claim at linker_engine.planning.storage."
        in caplog.text
    )
