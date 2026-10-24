"""Actual durable PV/energy executors and atomic owned-source publication."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from linker_engine.planning import archive
from linker_engine.planning.asset_publication import AssetResult
from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import InvalidInput, LeaseLost, NotFound
from linker_engine.planning.execution_identity import EvaluationRouting
from linker_engine.planning.execution_registry import ExecutionRegistry
from linker_engine.planning.frozen_profiles import frozen_profile
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.pv_physics import PvModelDomainExceeded
from linker_engine.planning.pv_preparation import (
    PvPreparationService,
    PvReferenceKernel,
)
from linker_engine.planning.pv_source import PvSource
from linker_engine.planning.records import Actor, Context, Lease, Project, Run
from linker_engine.planning.weather_import import WeatherImport
from linker_engine.planning.worker import Control, Worker
from linker_engine.planning.workspace import Workspace

from .conftest import Clock
from .test_energy_kernel import TOLERANCE, create_scenario
from .test_private_http import TOKEN, headers
from .test_pv_profile import LIMITS, PROVENANCE, annual_scenario, project_with_roof
from .test_pvgis_tmy import capture, interpretation, raw, request
from .test_worker_host import (
    completed,
    configuration,
    launch,
    ready_generation,
    stop,
    wait_for,
)


def pv_task(
    workspace: Workspace, owner: Actor
) -> tuple[Project, PvReferenceKernel, Run]:
    project = project_with_roof(workspace, owner)
    source = WeatherImport(Assets(workspace), LIMITS).tmy(
        owner,
        project.id,
        PvSource(raw(), request(), capture(), interpretation(), encode(PROVENANCE)),
        key="weather",
    )
    project = workspace.revise(
        owner,
        project.id,
        1,
        {
            **project.inputs,
            "pv_preparation": {"schema_version": 1, "weather_asset_id": source.id},
        },
        key="pv-settings",
    )
    kernel = PvReferenceKernel(workspace, LIMITS)
    run = PvPreparationService(workspace, kernel, max_attempts=2).evaluate(
        owner, project.id, project.revision, key="prepare-pv"
    )
    return project, kernel, run


def asset_count(workspace: Workspace, project_id: str) -> int:
    with workspace.database.read() as connection:
        return int(
            connection.execute(
                "SELECT COUNT(*) FROM project_assets WHERE project_id=?", (project_id,)
            ).fetchone()[0]
        )


def test_actual_shared_worker_prepares_pv_then_uses_it_in_full_year_energy(
    workspace: Workspace,
    owner: Actor,
    context: Context,
) -> None:
    roof, pv, pv_run = pv_task(workspace, owner)
    energy_project = create_scenario(workspace, owner)
    energy = EnergyKernel(workspace, TOLERANCE, max_intervals=9000)
    energy_run = EnergyService(workspace, energy, max_attempts=2).evaluate(
        owner, energy_project.id, energy_project.revision, key="energy-run"
    )
    incompatible = workspace.evaluate(
        owner, roof.id, roof.revision, context, key="other-executable", max_attempts=1
    )
    registry = ExecutionRegistry(energy, pv)
    assert ExecutionRegistry(pv, energy).execution_key() == registry.execution_key()
    worker = Worker(
        Jobs(workspace),
        "mixed-actual-executors",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    assert worker.run_once() and worker.run_once() and not worker.run_once()
    assert workspace.run(owner, incompatible.id).state == "queued"
    with workspace.database.read() as connection:
        assert (
            connection.execute(
                "SELECT attempt FROM jobs WHERE run_id=?", (incompatible.id,)
            ).fetchone()[0]
            == 0
        )
    assert workspace.run(owner, energy_run.id).state == "succeeded"
    completed = workspace.run(owner, pv_run.id)
    assert completed.state == "succeeded" and completed.result is not None
    result = completed.result
    record = cast(Object, result["prepared_asset"])
    asset = Assets(workspace).get(owner, roof.id, str(record["id"]))
    assert asset_count(workspace, roof.id) == 2
    profile = frozen_profile(
        workspace.blobs, asset.content_sha256, asset.metadata_sha256, None
    )
    assert len(profile.intervals) == 8760
    assert cast(Object, result["profile_summary"])["energy_kwh"] == profile.total_kwh
    replay_project = annual_scenario(workspace, owner, roof, asset)
    replay = EnergyService(workspace, energy, max_attempts=1).evaluate(
        owner, roof.id, replay_project.revision, key="pv-to-energy"
    )
    assert worker.run_once()
    replay_result = workspace.run(owner, replay.id).result
    assert replay_result is not None and replay_result["interval_count"] == 8760
    metrics = cast(Object, replay_result["metrics"])
    assert metrics["gross_load_kwh"] == 87600
    assert metrics["solar_load_kwh"] == pytest.approx(
        profile.total_kwh, rel=0, abs=1e-7
    )
    assert metrics["grid_import_kwh"] == pytest.approx(
        87600 - profile.total_kwh, rel=0, abs=1e-7
    )
    assert cast(Object, result["country_assessment"])["status"] == "not_assessed"


def test_cancellation_after_actual_pv_computation_publishes_no_owned_asset(
    workspace: Workspace,
    owner: Actor,
) -> None:
    project, kernel, run = pv_task(workspace, owner)
    assert asset_count(workspace, project.id) == 1

    def cancel_after_compute(lease: Lease, control: Control) -> AssetResult:
        result = kernel(lease, control)
        workspace.cancel(owner, run.id)
        return result

    worker = Worker(
        Jobs(workspace),
        "cancelled-actual-pv",
        {"evaluate": cancel_after_compute},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    )
    assert worker.run_once()
    cancelled = workspace.run(owner, run.id)
    assert cancelled.state == "cancelled" and cancelled.result is None
    assert asset_count(workspace, project.id) == 1


def test_expired_attempt_cannot_publish_after_its_replacement(
    workspace: Workspace,
    owner: Actor,
    clock: Clock,
) -> None:
    project, kernel, run = pv_task(workspace, owner)
    jobs = Jobs(workspace)
    old = jobs.claim("old", kinds=("evaluate",), lease_seconds=30)
    assert old is not None
    old_output = kernel(old, Control())
    clock.advance(31)
    new = jobs.claim("replacement", kinds=("evaluate",), lease_seconds=30)
    assert new is not None
    new_output = kernel(new, Control())
    published = jobs.complete(new, new_output.result, asset=new_output.asset)
    assert jobs.complete(new, new_output.result, asset=new_output.asset) == published
    with pytest.raises(LeaseLost):
        jobs.complete(old, old_output.result, asset=old_output.asset)
    with pytest.raises(NotFound):
        Assets(workspace).get(owner, project.id, old_output.asset.id)
    assert asset_count(workspace, project.id) == 2
    assert workspace.run(owner, run.id).result_sha256 == published


def test_publication_and_run_success_roll_back_as_one_transaction(
    workspace: Workspace,
    owner: Actor,
) -> None:
    project, kernel, run = pv_task(workspace, owner)
    jobs = Jobs(workspace)
    lease = jobs.claim("real-pv", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    output = kernel(lease, Control())
    with workspace.database.transaction() as connection:
        connection.execute(
            "CREATE TRIGGER fail_success BEFORE UPDATE ON jobs WHEN NEW.state='succeeded' BEGIN SELECT RAISE(ABORT,'fixture publication fault'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="fixture publication fault"):
        jobs.complete(lease, output.result, asset=output.asset)
    assert asset_count(workspace, project.id) == 1
    assert workspace.run(owner, run.id).result is None
    with workspace.database.transaction() as connection:
        connection.execute("DROP TRIGGER fail_success")
    jobs.complete(lease, output.result, asset=output.asset)
    assert asset_count(workspace, project.id) == 2
    assert workspace.run(owner, run.id).state == "succeeded"


def test_foreign_project_publication_rolls_back_without_result(
    workspace: Workspace,
    owner: Actor,
) -> None:
    project, kernel, run = pv_task(workspace, owner)
    other = workspace.create(owner, "another owned project", {}, key="other-project")
    jobs = Jobs(workspace)
    lease = jobs.claim("real-pv", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    output = kernel(lease, Control())
    with pytest.raises(InvalidInput, match="task's project"):
        jobs.complete(
            lease, output.result, asset=replace(output.asset, project_id=other.id)
        )
    assert (
        asset_count(workspace, project.id) == 1
        and asset_count(workspace, other.id) == 0
    )
    assert workspace.run(owner, run.id).result is None


def test_actual_private_command_receipt_worker_result_and_disabled_receipt_read(
    workspace: Workspace,
    owner: Actor,
) -> None:
    project, kernel, initial = pv_task(workspace, owner)
    workspace.cancel(owner, initial.id)
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000),
        max_attempts=2,
    )
    pv = PvPreparationService(workspace, kernel, max_attempts=2)
    limits = HttpLimits(2_000_000, 1_000_000, 20, 32)
    command: Object = {
        "schema_version": 1,
        "project_id": project.id,
        "expected_revision": project.revision,
        "key": "private-pv",
    }
    registry = ExecutionRegistry(energy.kernel, kernel)
    with TestClient(
        create_private_app(
            workspace, energy, credential=lambda: TOKEN, limits=limits, pv=pv
        )
    ) as client:
        assert client.post("/runs/pv", json=command).status_code == 401
        assert (
            client.post(
                "/runs/pv", json={**command, "context": {}}, headers=headers(owner)
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/runs/pv", json=command, headers=headers(Actor("user", "foreign"))
            ).status_code
            == 404
        )
        response = client.post("/runs/pv", json=command, headers=headers(owner))
        assert (
            response.status_code == 200
            and response.headers["cache-control"] == "no-store, private"
        )
        run_id = response.json()["id"]
        assert (
            response.json()["state"] == "queued" and response.json()["result"] is None
        )
        version = client.post(
            "/version", json={"schema_version": 1}, headers=headers(owner)
        ).json()
        assert version["execution_key"] == registry.execution_key()
        assert Worker(
            Jobs(workspace),
            "private-pv",
            {"evaluate": registry},
            lease_seconds=30,
            heartbeat_seconds=1,
            retry_seconds=1,
            routing=registry.routing(8),
        ).run_once()
        read = client.post(
            "/runs/read",
            json={"schema_version": 1, "run_id": run_id},
            headers=headers(owner),
        )
        assert read.json()["state"] == "succeeded"
        prepared_id = read.json()["result"]["prepared_asset"]["id"]
        assert Assets(workspace).get(owner, project.id, prepared_id)
    # Acknowledged mutation reads survive a later capability/config change.
    with TestClient(
        create_private_app(workspace, energy, credential=lambda: TOKEN, limits=limits)
    ) as client:
        replay = client.post(
            "/operations/replay/runs/pv", json=command, headers=headers(owner)
        )
        assert replay.status_code == 200 and replay.json()["status"] == "replayed"
        assert replay.json()["result"]["id"] == run_id
        assert (
            client.post(
                "/runs/pv",
                json={**command, "key": "disabled-new"},
                headers=headers(owner),
            ).status_code
            == 503
        )


def test_managed_process_executes_both_registered_kinds_with_matching_readiness(
    tmp_path: Path,
) -> None:
    settings = configuration(tmp_path, rows=9000).model_copy(
        update={"pv_preparation": LIMITS}
    )
    workspace, energy = settings.open()
    owner = Actor("user", "synthetic-mixed-process-owner")
    project, _, pv_run = pv_task(workspace, owner)
    energy_project = create_scenario(workspace, owner)
    energy_run = energy.evaluate(
        owner, energy_project.id, energy_project.revision, key="process-energy"
    )
    process, ready, generation = launch(tmp_path / "processes", settings, label="mixed")
    try:
        wait_for(lambda: ready_generation(ready), lambda value: value == generation)
        prepared, replayed = (
            completed(workspace, owner, pv_run),
            completed(workspace, owner, energy_run),
        )
        assert prepared.state == replayed.state == "succeeded"
        assert prepared.result is not None
        asset_id = str(cast(Object, prepared.result["prepared_asset"])["id"])
        assert Assets(workspace).get(owner, project.id, asset_id)
        assert process.poll() is None
    finally:
        stop(process)
    assert not ready.exists()


def test_publication_follows_project_after_guest_transfer(
    workspace: Workspace,
    owner: Actor,
) -> None:
    guest = Actor("guest", "synthetic-pv-guest")
    project, kernel, run = pv_task(workspace, guest)
    workspace.claim_guest(guest, owner, project.id, key="verified-transfer")
    assert Worker(
        Jobs(workspace),
        "transferred-pv",
        {"evaluate": kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    ).run_once()
    completed_run = workspace.run(owner, run.id)
    assert completed_run.result is not None
    asset_id = str(cast(Object, completed_run.result["prepared_asset"])["id"])
    assert Assets(workspace).get(owner, project.id, asset_id)
    with pytest.raises(NotFound):
        Assets(workspace).get(guest, project.id, asset_id)


def test_routing_freezes_compatible_keys_and_rejects_invalid_sets() -> None:
    keys = ["a" * 64, "b" * 64]
    routing = EvaluationRouting("c" * 64, 8, keys)  # type: ignore[arg-type]
    keys.clear()
    assert routing.execution_keys == ("a" * 64, "b" * 64)
    for values in (("a" * 64, "a" * 64), (True,), ("bad",)):
        with pytest.raises(InvalidInput):
            EvaluationRouting("c" * 64, 8, values)  # type: ignore[arg-type]


def test_pv_task_retains_queued_roof_and_does_not_overwrite_new_design(
    workspace: Workspace,
    owner: Actor,
) -> None:
    project, kernel, run = pv_task(workspace, owner)
    original_hash = digest(encode(project.inputs["geometry"]))
    geo = cast(Object, project.inputs["geometry"])
    cast(list[Object], geo["arrays"])[0]["mount_tilt_deg"] = 31
    edited = workspace.revise(
        owner, project.id, project.revision, project.inputs, key="new-roof"
    )
    assert Worker(
        Jobs(workspace),
        "historical-pv",
        {"evaluate": kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    ).run_once()
    completed_run = workspace.run(owner, run.id)
    assert completed_run.state == "succeeded" and not completed_run.is_current
    assert completed_run.result is not None
    record = cast(Object, completed_run.result["prepared_asset"])
    assert cast(Object, record["metadata"])["geometry_sha256"] == original_hash
    assert workspace.get(owner, project.id).input_sha256 == edited.input_sha256
    assert "profile_selections" not in workspace.get(owner, project.id).inputs


def test_prepared_source_and_children_survive_real_backup_restore(
    workspace: Workspace,
    owner: Actor,
    tmp_path: Path,
) -> None:
    project, kernel, run = pv_task(workspace, owner)
    assert Worker(
        Jobs(workspace),
        "archive-pv",
        {"evaluate": kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    ).run_once()
    result = workspace.run(owner, run.id).result
    assert result is not None
    record, dependencies = (
        cast(Object, result["prepared_asset"]),
        cast(Object, result["dependencies"]),
    )
    assert dependencies["prepared_asset_content"] == record["content_sha256"]
    assert dependencies["prepared_asset_metadata"] == record["metadata_sha256"]
    archive.backup(workspace, tmp_path / "archive")
    restored = archive.restore(tmp_path / "archive", tmp_path / "restored")
    assert restored.run(owner, run.id).result == result
    asset = Assets(restored).get(owner, project.id, str(record["id"]))
    series = frozen_profile(
        restored.blobs, asset.content_sha256, asset.metadata_sha256, None
    )
    assert len(series.intervals) == 8760


def test_worker_publishes_named_failure_for_a_foreign_prepared_asset(
    workspace: Workspace,
    owner: Actor,
) -> None:
    project, kernel, run = pv_task(workspace, owner)
    other = workspace.create(owner, "another project", {}, key="other")

    def invalid_publication(lease: Lease, control: Control) -> AssetResult:
        output = kernel(lease, control)
        return AssetResult(output.result, replace(output.asset, project_id=other.id))

    assert Worker(
        Jobs(workspace),
        "invalid-publication",
        {"evaluate": invalid_publication},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    ).run_once()
    failed = workspace.run(owner, run.id)
    assert failed.state == "failed" and failed.result is None
    assert failed.error == {"code": "invalid_input", "retryable": False}
    assert (
        asset_count(workspace, project.id) == 1
        and asset_count(workspace, other.id) == 0
    )


def test_http_classifies_a_known_domain_subclass_without_internal_details(
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = workspace.create(owner, "error classification", {}, key="project")
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000),
        max_attempts=1,
    )

    def reject(*_args: object, **_kwargs: object) -> Run:
        raise PvModelDomainExceeded("private model/input details must stay private")

    monkeypatch.setattr(energy, "evaluate", reject)
    with TestClient(
        create_private_app(
            workspace,
            energy,
            credential=lambda: TOKEN,
            limits=HttpLimits(2_000_000, 1_000_000, 20, 32),
        )
    ) as client:
        response = client.post(
            "/runs/energy",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": 1,
                "key": "error",
            },
            headers=headers(owner),
        )
        assert response.status_code == 422
        assert response.json() == {"error": {"code": "method_domain_exceeded"}}
