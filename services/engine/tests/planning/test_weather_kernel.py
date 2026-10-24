"""Actual queued acquisition/publication and HTTP ownership, simulated provider."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from linker_engine.planning import runtime_snapshot
from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import InvalidInput, LeaseLost, NotFound
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.pv_preparation import (
    PvPreparationService,
    PvReferenceKernel,
    check_pv_preparation,
)
from linker_engine.planning.records import Actor
from linker_engine.planning.weather_journal import WeatherJournal
from linker_engine.planning.weather_kernel import WeatherKernel
from linker_engine.planning.weather_service import WeatherService
from linker_engine.planning.weather_status import weather_status
from linker_engine.planning.worker import Control, Worker
from linker_engine.planning.workspace import Workspace

from .conftest import Clock
from .test_energy_kernel import TOLERANCE, create_scenario
from .test_official_weather import Reply, SequenceAdapter, plan
from .test_private_http import TOKEN, headers
from .test_pv_profile import LIMITS, project_with_roof
from .test_pvgis_tmy import raw
from .test_worker_host import (
    completed,
    configuration,
    launch,
    ready_generation,
    stop,
    wait_for,
)


def source_inputs() -> Object:
    p = plan()
    return {
        "weather_acquisition": {
            "schema_version": 1,
            "request": p.request.model_dump(mode="json"),
            "interpretation": p.interpretation.model_dump(mode="json"),
        }
    }


def valid_adapter() -> SequenceAdapter:
    return SequenceAdapter(Reply(200, raw()))


def services(workspace: Workspace, adapter: SequenceAdapter):
    weather = WeatherService(
        workspace,
        WeatherKernel(
            workspace,
            plan().limits,
            adapter_factory=lambda: adapter,
        ),
        max_attempts=2,
    )
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000),
        max_attempts=2,
    )
    return weather, energy


def worker(workspace: Workspace, registry):
    return Worker(
        Jobs(workspace),
        "weather-integration",
        {"evaluate": registry},
        lease_seconds=300,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )


def asset_count(workspace: Workspace) -> int:
    with workspace.database.read() as connection:
        return int(
            connection.execute("SELECT COUNT(*) FROM project_assets").fetchone()[0]
        )


def test_shared_registry_acquires_source_then_explicit_saved_selection_prepares_full_pv(
    workspace: Workspace, owner: Actor
) -> None:
    roof = project_with_roof(workspace, owner)
    roof = workspace.revise(
        owner,
        roof.id,
        roof.revision,
        {**roof.inputs, **source_inputs()},
        key="weather-inputs",
    )
    adapter = valid_adapter()
    weather, energy = services(workspace, adapter)
    pv = PvPreparationService(
        workspace, PvReferenceKernel(workspace, LIMITS), max_attempts=2
    )
    registry = service_registry(energy, pv, weather)
    run = weather.evaluate(owner, roof.id, roof.revision, key="acquire")
    assert adapter.calls == [] and asset_count(workspace) == 0
    assert (
        weather_status(workspace, owner, run.id)["acquisition_state"] == "not_started"
    )
    assert worker(workspace, registry).run_once()
    completed = workspace.run(owner, run.id)
    assert completed.state == "succeeded" and completed.result is not None
    source_id = completed.result["prepared_asset"]["id"]
    source = Assets(workspace).get(owner, roof.id, source_id)
    assert Assets(workspace).content(owner, roof.id, source_id) == raw()
    assert source.metadata["weather"]["interval_count"] == 8760
    assert workspace.get(owner, roof.id).revision == roof.revision
    assert "pv_preparation" not in workspace.get(owner, roof.id).inputs
    selected = {
        **roof.inputs,
        "pv_preparation": {"schema_version": 1, "weather_asset_id": source_id},
    }
    check_pv_preparation(Assets(workspace), owner, roof.id, selected)
    saved = workspace.revise(
        owner, roof.id, roof.revision, selected, key="select-weather"
    )
    pv_run = pv.evaluate(owner, roof.id, saved.revision, key="prepare")
    assert worker(workspace, registry).run_once()
    result = workspace.run(owner, pv_run.id)
    assert (
        result.state == "succeeded"
        and result.result["profile_summary"]["interval_count"] == 8760
    )
    assert len(adapter.calls) == 1 and all(
        call.method == "GET" for call in adapter.calls
    )


def test_atomic_source_publication_rolls_back_then_reuses_prepared_bytes_without_another_download(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    adapter = valid_adapter()
    weather, _ = services(workspace, adapter)
    run = weather.evaluate(owner, project.id, project.revision, key="acquire")
    jobs = Jobs(workspace)
    lease = jobs.claim("prepare", kinds=("evaluate",), lease_seconds=300)
    assert lease
    prepared = weather.kernel(lease, Control())
    assert asset_count(workspace) == 0
    with workspace.database.transaction() as connection:
        connection.execute(
            "CREATE TRIGGER reject_source BEFORE INSERT ON project_assets BEGIN SELECT RAISE(ABORT,'fixture'); END"
        )
    with pytest.raises(sqlite3.DatabaseError):
        jobs.complete(lease, prepared.result, asset=prepared.asset)
    assert asset_count(workspace) == 0 and workspace.run(owner, run.id).result is None
    with workspace.database.transaction() as connection:
        connection.execute("DROP TRIGGER reject_source")
    jobs.complete(lease, prepared.result, asset=prepared.asset)
    assert (
        asset_count(workspace) == 1
        and workspace.run(owner, run.id).state == "succeeded"
    )
    assert len(adapter.calls) == 1


def test_replacement_reuses_completed_capture_after_original_network_deadline(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    adapter = valid_adapter()
    weather, _ = services(workspace, adapter)
    run = weather.evaluate(owner, project.id, project.revision, key="acquire")
    jobs = Jobs(workspace)
    first = jobs.claim("old", kinds=("evaluate",), lease_seconds=10)
    assert first
    prepared = weather.kernel(first, Control())
    clock.advance(61)
    second = jobs.claim("new", kinds=("evaluate",), lease_seconds=300)
    assert second
    with pytest.raises(LeaseLost):
        jobs.complete(first, prepared.result, asset=prepared.asset)
    restored = weather.kernel(second, Control())
    jobs.complete(second, restored.result, asset=restored.asset)
    assert (
        workspace.run(owner, run.id).state == "succeeded"
        and asset_count(workspace) == 1
    )
    assert len(adapter.calls) == 1


def test_cancel_after_capture_before_commit_cannot_publish_source(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    adapter = valid_adapter()
    weather, _ = services(workspace, adapter)
    run = weather.evaluate(owner, project.id, project.revision, key="acquire")
    jobs = Jobs(workspace)
    lease = jobs.claim("weather", kinds=("evaluate",), lease_seconds=300)
    assert lease
    output = weather.kernel(lease, Control())
    workspace.cancel(owner, run.id)
    with pytest.raises(LeaseLost):
        jobs.complete(lease, output.result, asset=output.asset)
    assert (
        asset_count(workspace) == 0
        and workspace.run(owner, run.id).state == "cancelled"
    )


def test_new_request_cannot_silently_use_an_old_selected_weather_source(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    adapter = valid_adapter()
    weather, energy = services(workspace, adapter)
    run = weather.evaluate(owner, project.id, 1, key="acquire")
    worker(workspace, service_registry(energy, None, weather)).run_once()
    source_id = workspace.run(owner, run.id).result["prepared_asset"]["id"]
    changed = json.loads(encode(source_inputs()))
    changed["weather_acquisition"]["request"]["latitude_deg"] = 53
    changed["pv_preparation"] = {"schema_version": 1, "weather_asset_id": source_id}
    with pytest.raises(InvalidInput, match="saved source request"):
        check_pv_preparation(Assets(workspace), owner, project.id, changed)


def test_private_queue_receipt_status_and_disabled_history_use_no_provider_on_http(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    adapter = valid_adapter()
    weather, energy = services(workspace, adapter)
    command = {
        "schema_version": 1,
        "project_id": project.id,
        "expected_revision": 1,
        "key": "http-weather",
    }
    limits = HttpLimits(2_000_000, 1_000_000, 20, 32)
    with TestClient(
        create_private_app(
            workspace, energy, credential=lambda: TOKEN, limits=limits, weather=weather
        )
    ) as client:
        assert client.post("/runs/weather", json=command).status_code == 401
        assert (
            client.post(
                "/runs/weather",
                json={**command, "actor_id": "override"},
                headers=headers(owner),
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/runs/weather", json=command, headers=headers(Actor("user", "foreign"))
            ).status_code
            == 404
        )
        reply = client.post("/runs/weather", json=command, headers=headers(owner))
        assert reply.status_code == 200
        run_id = reply.json()["id"]
        assert adapter.calls == [] and reply.json()["state"] == "queued"
        state = client.post(
            "/runs/weather/status",
            json={"schema_version": 1, "run_id": run_id},
            headers=headers(owner),
        )
        assert (
            state.status_code == 200
            and state.json()["acquisition_state"] == "not_started"
        )
        assert worker(workspace, service_registry(energy, None, weather)).run_once()
        assert (
            client.post(
                "/runs/weather/status",
                json={"schema_version": 1, "run_id": run_id},
                headers=headers(Actor("user", "foreign")),
            ).status_code
            == 404
        )
    with TestClient(
        create_private_app(workspace, energy, credential=lambda: TOKEN, limits=limits)
    ) as client:
        replay = client.post(
            "/operations/replay/runs/weather", json=command, headers=headers(owner)
        )
        assert (
            replay.status_code == 200
            and replay.json()["status"] == "replayed"
            and replay.json()["result"]["id"] == run_id
        )
        assert (
            client.post(
                "/runs/weather", json={**command, "key": "new"}, headers=headers(owner)
            ).status_code
            == 503
        )
        assert (
            client.post(
                "/runs/weather/status",
                json={"schema_version": 1, "run_id": run_id},
                headers=headers(owner),
            ).json()["acquisition_state"]
            == "captured"
        )
    assert len(adapter.calls) == 1


def test_one_registry_executes_energy_and_weather_without_claiming_other_runtime(
    workspace: Workspace,
    owner: Actor,
    context,
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    adapter = valid_adapter()
    weather, energy = services(workspace, adapter)
    weather_run = weather.evaluate(owner, project.id, 1, key="weather")
    scenario = create_scenario(workspace, owner)
    energy_run = energy.evaluate(owner, scenario.id, scenario.revision, key="energy")
    other = workspace.evaluate(
        owner, project.id, 1, context, key="different-runtime", max_attempts=1
    )
    registry = service_registry(energy, None, weather)
    host = worker(workspace, registry)
    assert host.run_once() and host.run_once() and not host.run_once()
    assert (
        workspace.run(owner, weather_run.id).state
        == workspace.run(owner, energy_run.id).state
        == "succeeded"
    )
    assert workspace.run(owner, other.id).state == "queued"


def test_guest_transfer_keeps_pending_source_and_completed_asset_with_project(
    workspace: Workspace,
) -> None:
    guest, user = Actor("guest", "weather-session"), Actor("user", "weather-account")
    project = workspace.create(guest, "Guest weather", source_inputs(), key="project")
    adapter = valid_adapter()
    weather, energy = services(workspace, adapter)
    run = weather.evaluate(guest, project.id, 1, key="weather")
    workspace.claim_guest(guest, user, project.id, key="claim")
    assert worker(workspace, service_registry(energy, None, weather)).run_once()
    result = workspace.run(user, run.id)
    source_id = result.result["prepared_asset"]["id"]
    assert Assets(workspace).content(user, project.id, source_id) == raw()
    assert (
        WeatherJournal(workspace).view(user, run.id)["acquisition_state"] == "captured"
    )
    with pytest.raises(NotFound):
        weather_status(workspace, guest, run.id)


def test_new_saved_request_does_not_replace_frozen_historical_weather_or_select_it(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Weather", source_inputs(), key="project")
    adapter = valid_adapter()
    weather, energy = services(workspace, adapter)
    run = weather.evaluate(owner, project.id, 1, key="weather")
    changed = json.loads(encode(project.inputs))
    changed["weather_acquisition"]["request"]["latitude_deg"] = 53
    workspace.revise(owner, project.id, 1, changed, key="changed-location")
    assert worker(workspace, service_registry(energy, None, weather)).run_once()
    historical = workspace.run(owner, run.id)
    assert historical.state == "succeeded" and not historical.is_current
    source = historical.result["prepared_asset"]["metadata"]
    assert source["weather_request"]["latitude_deg"] == 52.52
    latest = workspace.get(owner, project.id)
    assert latest.revision == 2 and "pv_preparation" not in latest.inputs


def test_independent_managed_process_resumes_weather_capture_then_runs_energy_and_pv(
    tmp_path: Path,
) -> None:
    settings = configuration(tmp_path, rows=9000).model_copy(
        update={
            "weather_acquisition": plan().limits,
            "pv_preparation": LIMITS,
        }
    )
    workspace, energy = settings.open()
    owner = Actor("user", "independent-weather-owner")
    roof = project_with_roof(workspace, owner)
    roof = workspace.revise(
        owner,
        roof.id,
        roof.revision,
        {**roof.inputs, **source_inputs()},
        key="weather-inputs",
    )
    adapter = valid_adapter()
    weather = WeatherService(
        workspace,
        WeatherKernel(
            workspace,
            plan().limits,
            adapter_factory=lambda: adapter,
        ),
        max_attempts=2,
    )
    source_run = weather.evaluate(owner, roof.id, roof.revision, key="weather")
    jobs = Jobs(workspace)
    lease = jobs.claim("interrupted-producer", kinds=("evaluate",), lease_seconds=300)
    assert lease
    weather.kernel(lease, Control())
    assert asset_count(workspace) == 0
    jobs.fail(
        lease,
        {"code": "fixture_interrupted_after_retained_capture", "retryable": True},
        retry_after=0,
    )
    scenario = create_scenario(workspace, owner)
    energy_run = energy.evaluate(owner, scenario.id, scenario.revision, key="energy")
    # The independent process has no research/provider credentials and must
    # reuse the captured source without another download.
    process, ready, generation = launch(tmp_path / "worker-process", settings)
    try:
        wait_for(lambda: ready_generation(ready), lambda value: value == generation)
        finished = completed(workspace, owner, source_run)
        assert finished.state == "succeeded"
        assert completed(workspace, owner, energy_run).state == "succeeded"
        source_id = finished.result["prepared_asset"]["id"]
        assert Assets(workspace).content(owner, roof.id, source_id) == raw()
        saved = workspace.revise(
            owner,
            roof.id,
            roof.revision,
            {
                **roof.inputs,
                "pv_preparation": {"schema_version": 1, "weather_asset_id": source_id},
            },
            key="select",
        )
        pv = settings.pv_service(workspace)
        assert pv is not None
        pv_run = pv.evaluate(owner, roof.id, saved.revision, key="pv")
        assert completed(workspace, owner, pv_run).state == "succeeded"
        with workspace.database.read() as connection:
            assert (
                connection.execute(
                    "SELECT attempt FROM jobs WHERE run_id=? AND kind='evaluate'",
                    (source_run.id,),
                ).fetchone()[0]
                == 2
            )
        assert len(adapter.calls) == 1
    finally:
        stop(process)


def test_installed_transport_version_changes_execution_identity_and_leaves_old_work_unclaimed(
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = workspace.create(
        owner, "Version-pinned source", source_inputs(), key="project"
    )
    adapter = valid_adapter()
    original, energy = services(workspace, adapter)
    run = original.evaluate(owner, project.id, 1, key="weather")
    version = runtime_snapshot.version
    monkeypatch.setattr(
        runtime_snapshot,
        "version",
        lambda name: (
            version(name) + "-different-fixture" if name == "urllib3" else version(name)
        ),
    )
    replacement, changed_energy = services(workspace, adapter)
    assert replacement.kernel.execution_key() != original.kernel.execution_key()
    assert not worker(
        workspace, service_registry(changed_energy, None, replacement)
    ).run_once()
    assert workspace.run(owner, run.id).state == "queued" and adapter.calls == []


def test_status_does_not_turn_ownership_denial_during_guest_transfer_into_not_started(
    workspace: Workspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guest, user = Actor("guest", "status-race"), Actor("user", "status-account")
    project = workspace.create(
        guest, "Status ownership race", source_inputs(), key="project"
    )
    adapter = valid_adapter()
    weather, energy = services(workspace, adapter)
    run = weather.evaluate(guest, project.id, 1, key="weather")
    original = workspace.run
    calls = 0

    def transfer_before_second_owned_read(actor: Actor, run_id: str):
        nonlocal calls
        calls += 1
        if calls == 2:
            workspace.claim_guest(guest, user, project.id, key="claim-during-status")
        return original(actor, run_id)

    monkeypatch.setattr(workspace, "run", transfer_before_second_owned_read)
    with TestClient(
        create_private_app(
            workspace,
            energy,
            credential=lambda: TOKEN,
            limits=HttpLimits(2_000_000, 1_000_000, 20, 32),
            weather=weather,
        )
    ) as client:
        response = client.post(
            "/runs/weather/status",
            json={"schema_version": 1, "run_id": run.id},
            headers=headers(guest),
        )
        assert (
            response.status_code == 404
            and response.json()["error"]["code"] == "not_found"
        )
    assert calls == 2 and not adapter.calls
