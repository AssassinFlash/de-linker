"""Direct download keeps its original plan/deadline and validates before retention."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from linker_engine.planning import archive
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.errors import LeaseLost, NotFound
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Lease
from linker_engine.planning.weather_fetch_errors import WeatherResponseInvalid
from linker_engine.planning.weather_intent import WeatherIntent
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


def test_invalid_source_keeps_private_original_and_safe_reason_without_weather_asset(
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Existing official response fixture; the one observed provider failure
    # pattern is a negative 10-m total wind speed, never a modelled correction.
    body = json.loads(raw())
    row = body["outputs"]["tmy_hourly"][751]
    row["WS10m"] = -0.29
    content = json.dumps(body).encode()
    source_timestamp = (
        datetime.strptime(row["time(UTC)"], "%Y%m%d:%H%M")
        .replace(tzinfo=UTC)
        .isoformat()
    )
    adapter = SequenceAdapter(Reply(200, content))
    weather, energy = services(workspace, adapter)
    project = workspace.create(
        owner, "Invalid weather fixture", source_inputs(), key="project"
    )
    run = weather.evaluate(owner, project.id, 1, key="invalid-weather")
    original_fail = Jobs.fail

    def observe_retained_diagnostic_before_failure(
        jobs: Jobs, lease: Lease, error: Object, *, retry_after: float | None
    ) -> None:
        with workspace.database.read() as connection:
            pending = connection.execute(
                "SELECT * FROM weather_downloads WHERE run_id=?", (run.id,)
            ).fetchone()
            output = connection.execute(
                "SELECT output_sha256 FROM jobs WHERE run_id=?", (run.id,)
            ).fetchone()[0]
            assert pending is not None and pending["capture_sha256"] is None
            assert isinstance(output, str)
        phase = json_object(weather_status(workspace, owner, run.id))
        assert (
            phase["task_state"] == "running"
            and phase["acquisition_state"] == "fetching"
        )
        assert phase["capture_sha256"] is None
        assert "validation_failure" not in phase and "diagnostic_retained" not in phase
        pending_intent = WeatherIntent(
            run.id,
            run.manifest_sha256,
            pending["plan_sha256"],
            pending["deadline_at"],
            None,
        )
        with pytest.raises(WeatherResponseInvalid):
            WeatherJournal(workspace).captured_source(pending_intent)
        original_fail(jobs, lease, error, retry_after=retry_after)

    monkeypatch.setattr(Jobs, "fail", observe_retained_diagnostic_before_failure)
    host = worker(workspace, service_registry(energy, None, weather))
    assert host.run_once()
    completed = workspace.run(owner, run.id)
    details = {
        "reason": "negative_wind",
        "field": "WS10m",
        "row_index": 751,
        "source_timestamp_utc": source_timestamp,
        "value": -0.29,
    }
    assert completed.state == "failed" and completed.result is None
    assert completed.error == {
        "code": "weather_source_quality_invalid",
        "retryable": False,
        "details": details,
    }
    status = json_object(weather_status(workspace, owner, run.id))
    assert (
        status["acquisition_state"] == "rejected"
        and status["capture_sha256"] is None
        and status["diagnostic_retained"] is True
    )
    assert status["validation_failure"] == {
        "code": "weather_source_quality_invalid",
        **details,
    }
    assert all(
        field not in encode(status).decode()
        for field in (
            "requested_url",
            "loaded_url",
            "latitude",
            "longitude",
            "provenance",
        )
    )
    with workspace.database.read() as connection:
        row = connection.execute(
            "SELECT * FROM weather_downloads WHERE run_id=?", (run.id,)
        ).fetchone()
        assert row is not None and row["capture_sha256"] is None
        assert (
            connection.execute("SELECT count(*) FROM project_assets").fetchone()[0] == 0
        )
        intent = WeatherIntent(
            run.id,
            run.manifest_sha256,
            row["plan_sha256"],
            row["deadline_at"],
            row["capture_sha256"],
        )
        output = connection.execute(
            "SELECT output_sha256 FROM jobs WHERE run_id=?", (run.id,)
        ).fetchone()[0]
        assert isinstance(output, str)
    diagnostic = json_object(workspace.blobs.object(output))
    assert (
        diagnostic["kind"] == "unvalidated_official_jrc_tmy_diagnostic_v1"
        and diagnostic["usable_weather_source"] is False
    )
    assert diagnostic["dependencies"]["weather_unvalidated_original"] == digest(content)
    assert (
        workspace.blobs.read(diagnostic["dependencies"]["weather_unvalidated_original"])
        == content
    )
    transport = json_object(
        workspace.blobs.object(diagnostic["dependencies"]["capture.transport_receipt"])
    )
    assert (
        transport["status"] == 200 and transport["requested_url"] == plan().request.url
    )
    with pytest.raises(WeatherResponseInvalid):
        WeatherJournal(workspace).captured_source(intent)
    with pytest.raises(NotFound):
        weather_status(workspace, Actor("guest", "unrelated"), run.id)
    assert not host.run_once() and len(adapter.calls) == 1
