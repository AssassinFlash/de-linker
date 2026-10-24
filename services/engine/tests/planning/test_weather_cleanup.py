"""Cancellation while no producer runs still has durable leased remote cleanup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import requests

from linker_engine.planning import archive
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor
from linker_engine.planning.weather_cleanup import WeatherCleanup
from linker_engine.planning.weather_journal import WeatherJournal
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

from .test_apify_weather_client import Reply, SequenceAdapter, provider
from .test_weather_kernel import (
    WeatherAdapter,
    asset_count,
    services,
    source_inputs,
    worker,
)


def pending(workspace: Workspace, owner: Actor, *cleanup_replies: Reply):
    project = workspace.create(
        owner, "Cancelled source", source_inputs(), key="project"
    )
    producer = WeatherAdapter(
        Reply(201, provider("READY")),
        Reply(0, b"", error=requests.ConnectionError("fixture")),
    )
    weather, energy = services(workspace, producer)
    cleanup_adapter = SequenceAdapter(*cleanup_replies)
    adapters = [producer, cleanup_adapter]
    weather.kernel.adapter_factory = lambda: adapters.pop(0)
    run = weather.evaluate(owner, project.id, 1, key="weather")
    assert worker(workspace, service_registry(energy, None, weather)).run_once()
    assert workspace.run(owner, run.id).state == "retry_wait"
    cleanup = Worker(
        Jobs(workspace),
        "cleanup",
        {"abort_weather": WeatherCleanup(weather.kernel)},
        lease_seconds=300,
        heartbeat_seconds=1,
        retry_seconds=1,
    )
    return run, weather, cleanup, producer, cleanup_adapter


def test_inactive_retry_cancel_enqueues_once_and_confirms_remote_terminal_without_publishing(
    workspace: Workspace, owner: Actor
) -> None:
    run, weather, cleanup, producer, adapter = pending(
        workspace,
        owner,
        Reply(200, provider("RUNNING")),
        Reply(200, provider("ABORTING")),
        Reply(200, provider("ABORTED")),
    )
    workspace.cancel(owner, run.id)
    workspace.cancel(owner, run.id)
    queued = weather.journal.view(owner, run.id)
    assert (
        queued["task_state"] == "cancelled" and queued["cleanup"]["state"] == "queued"
    )
    assert cleanup.run_once() and not cleanup.run_once()
    final = weather.journal.view(owner, run.id)
    assert (
        final["task_state"] == "cancelled" and final["cleanup"]["state"] == "succeeded"
    )
    assert final["acquisition_state"] == "ABORTED"
    assert [call.method for call in adapter.calls] == ["GET", "POST", "GET"]
    assert len(producer.calls) == 2 and asset_count(workspace) == 0
    assert workspace.run(owner, run.id).result is None
    with workspace.database.read() as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE kind='abort_weather'"
            ).fetchone()[0]
            == 1
        )


def test_already_finished_actor_is_read_without_repeating_abort(
    workspace: Workspace, owner: Actor
) -> None:
    run, weather, cleanup, _, adapter = pending(
        workspace, owner, Reply(200, provider())
    )
    workspace.cancel(owner, run.id)
    assert cleanup.run_once()
    assert [call.method for call in adapter.calls] == ["GET"]
    status = weather.journal.view(owner, run.id)
    assert (
        status["acquisition_state"] == "SUCCEEDED"
        and status["task_state"] == "cancelled"
    )
    assert status["abort_sha256"] is None and asset_count(workspace) == 0


def test_actor_finishing_between_read_and_abort_is_observed_without_fake_aborted_state(
    workspace: Workspace, owner: Actor
) -> None:
    run, weather, cleanup, _, adapter = pending(
        workspace,
        owner,
        Reply(200, provider("RUNNING")),
        Reply(400, b"{}"),
        Reply(200, provider()),
    )
    workspace.cancel(owner, run.id)
    assert cleanup.run_once()
    status = weather.journal.view(owner, run.id)
    assert (
        status["acquisition_state"] == "SUCCEEDED"
        and status["cleanup"]["state"] == "succeeded"
    )
    assert status["abort_sha256"] is None and len(adapter.calls) == 3


def test_existing_abort_reply_polls_without_another_post(
    workspace: Workspace, owner: Actor
) -> None:
    run, weather, cleanup, _, adapter = pending(
        workspace,
        owner,
        Reply(200, provider("ABORTING")),
        Reply(200, provider("ABORTED")),
    )
    intent = weather.journal.for_run(run.id)
    from .test_weather_journal import remote

    weather.journal.abort_reply(intent, remote("ABORTING"))
    workspace.cancel(owner, run.id)
    assert cleanup.run_once()
    assert all(call.method == "GET" for call in adapter.calls)
    assert weather.journal.view(owner, run.id)["acquisition_state"] == "ABORTED"


def test_cancel_and_cleanup_admission_rollback_together_on_queue_failure(
    workspace: Workspace, owner: Actor
) -> None:
    run, weather, _, _, _ = pending(workspace, owner)
    with workspace.database.transaction() as connection:
        connection.execute(
            "CREATE TRIGGER reject_cleanup BEFORE INSERT ON jobs WHEN NEW.kind='abort_weather' BEGIN SELECT RAISE(ABORT,'fixture'); END"
        )
    with pytest.raises(sqlite3.DatabaseError):
        workspace.cancel(owner, run.id)
    assert workspace.run(owner, run.id).state == "retry_wait"
    assert weather.journal.view(owner, run.id)["cleanup"] is None
    with workspace.database.transaction() as connection:
        connection.execute("DROP TRIGGER reject_cleanup")
    workspace.cancel(owner, run.id)
    assert weather.journal.view(owner, run.id)["cleanup"]["state"] == "queued"


def test_unknown_start_cleanup_fails_visibly_without_actor_post_or_local_success(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(
        owner, "Unknown cancelled start", source_inputs(), key="project"
    )
    adapter = SequenceAdapter()
    weather, _ = services(workspace, adapter)
    run = weather.evaluate(owner, project.id, 1, key="weather")
    lease = Jobs(workspace).claim("producer", kinds=("evaluate",), lease_seconds=300)
    assert lease
    from .test_weather_journal import plan

    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    journal.authorize_post(lease, intent)
    workspace.cancel(owner, run.id)
    cleanup = Worker(
        Jobs(workspace),
        "cleanup",
        {"abort_weather": WeatherCleanup(weather.kernel)},
        lease_seconds=300,
        heartbeat_seconds=1,
        retry_seconds=1,
    )
    assert cleanup.run_once()
    status = journal.view(owner, run.id)
    assert (
        status["acquisition_state"] == "start_outcome_unknown"
        and status["task_state"] == "cancelled"
    )
    assert (
        status["cleanup"]["state"] == "failed"
        and status["cleanup"]["error"]["code"] == "weather_start_unknown"
    )
    assert not adapter.calls and asset_count(workspace) == 0


def test_backup_restore_keeps_cancelled_task_and_confirmed_cleanup_dependencies(
    workspace: Workspace,
    owner: Actor,
    tmp_path: Path,
) -> None:
    run, weather, cleanup, _, _ = pending(
        workspace,
        owner,
        Reply(200, provider("RUNNING")),
        Reply(200, provider("ABORTED")),
    )
    workspace.cancel(owner, run.id)
    assert cleanup.run_once()
    snapshot = tmp_path / "cleanup-backup"
    archive.backup(workspace, snapshot)
    archive.verify(snapshot)
    restored = archive.restore(snapshot, tmp_path / "cleanup-restored")
    before = weather.journal.view(owner, run.id)
    after = WeatherJournal(restored).view(owner, run.id)
    assert after == before
    assert (
        after["task_state"] == "cancelled" and after["acquisition_state"] == "ABORTED"
    )
    assert after["cleanup"]["state"] == "succeeded"
    assert restored.run(owner, run.id).result is None and asset_count(restored) == 0
