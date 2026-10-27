"""Direct download keeps its original plan/deadline and validates before retention."""

from __future__ import annotations

from pathlib import Path

import pytest

from linker_engine.planning import archive
from linker_engine.planning.errors import LeaseLost
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor
from linker_engine.planning.weather_journal import (
    WeatherDeadlineExceeded,
    WeatherJournal,
)
from linker_engine.planning.weather_status import weather_status
from linker_engine.planning.worker import Control
from linker_engine.planning.workspace import Workspace

from .conftest import Clock, json_object
from .test_official_weather import Reply, SequenceAdapter, plan
from .test_pvgis_tmy import raw
from .test_weather_kernel import services, source_inputs, valid_adapter, worker


def test_begin_replays_the_same_original_deadline(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    weather, _ = services(workspace, valid_adapter())
    run = weather.evaluate(owner, project.id, 1, key="weather")
    lease = Jobs(workspace).claim("weather", kinds=("evaluate",), lease_seconds=300)
    assert lease is not None
    journal = WeatherJournal(workspace)
    first = journal.begin(lease, plan())
    clock.advance(3)
    assert journal.begin(lease, plan()) == first
    assert (
        json_object(weather_status(workspace, owner, run.id))["acquisition_state"]
        == "fetching"
    )


def test_elapsed_original_deadline_cannot_be_reset_by_retry(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    adapter = valid_adapter()
    weather, _ = services(workspace, adapter)
    weather.evaluate(owner, project.id, 1, key="weather")
    lease = Jobs(workspace).claim("weather", kinds=("evaluate",), lease_seconds=300)
    assert lease is not None
    intent = WeatherJournal(workspace).begin(lease, plan())
    clock.advance(61)
    with pytest.raises(WeatherDeadlineExceeded):
        weather.kernel(lease, Control())
    assert not adapter.calls
    assert (
        WeatherJournal(workspace).begin(lease, plan()).deadline_at == intent.deadline_at
    )


def test_cancellation_during_get_fences_capture_and_source(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    adapter = valid_adapter()
    weather, _ = services(workspace, adapter)
    run = weather.evaluate(owner, project.id, 1, key="weather")

    def cancel_source_run() -> None:
        workspace.cancel(owner, run.id)

    adapter.on_send = cancel_source_run
    lease = Jobs(workspace).claim("weather", kinds=("evaluate",), lease_seconds=300)
    assert lease is not None
    with pytest.raises(LeaseLost):
        weather.kernel(lease, Control())
    with workspace.database.read() as connection:
        assert (
            connection.execute(
                "SELECT capture_sha256 FROM weather_downloads WHERE run_id=?", (run.id,)
            ).fetchone()[0]
            is None
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM project_assets").fetchone()[0] == 0
        )


def test_transient_get_retries_without_remote_job_or_credentials(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    adapter = SequenceAdapter(Reply(503, b"unavailable"), Reply(200, raw()))
    weather, energy = services(workspace, adapter)
    run = weather.evaluate(owner, project.id, 1, key="weather")
    host = worker(workspace, service_registry(energy, None, weather))
    assert host.run_once()
    assert workspace.run(owner, run.id).state == "retry_wait"
    clock.advance(2)
    assert host.run_once()
    assert workspace.run(owner, run.id).state == "succeeded"
    assert len(adapter.calls) == 2 and all(
        call.method == "GET" for call in adapter.calls
    )


def test_download_capture_survives_verified_archive_restore(
    workspace: Workspace, owner: Actor, tmp_path: Path
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    weather, energy = services(workspace, valid_adapter())
    run = weather.evaluate(owner, project.id, 1, key="weather")
    assert worker(workspace, service_registry(energy, None, weather)).run_once()
    destination = tmp_path / "backup"
    archive.backup(workspace, destination)
    archive.verify(destination)
    restored = archive.restore(destination, tmp_path / "restored")
    assert (
        json_object(weather_status(restored, owner, run.id))["acquisition_state"]
        == "captured"
    )
    assert restored.run(owner, run.id).result == workspace.run(owner, run.id).result
