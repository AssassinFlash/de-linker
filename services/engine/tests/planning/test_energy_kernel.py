"""Real CSV/assets/durable-worker/replay/result paths with analytic fixtures."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from linker_engine.planning import archive, timezone_rules
from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import Json, Object, encode
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.energy_inputs import EnergyInputs
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import (
    Conflict,
    InvalidInput,
    NotFound,
    VersionUnavailable,
)
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.numerical_tolerance import Tolerance
from linker_engine.planning.power_series import Measurement
from linker_engine.planning.profile_import import ProfileImport
from linker_engine.planning.records import Actor, Project
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

TOLERANCE = Tolerance(1e-7, 1e-7, 1e-9)
PROVENANCE: Object = {
    "label": "Analytic two-hour fixture; no real customer, weather or SKU",
    "basis": "synthetic_fixture",
    "rights_basis": "created by this test; permanent private retention allowed",
}
BATTERY: Object = {
    "schema_version": 1,
    "model": "constant_window_single_ac_bus_v1",
    "parameter_basis": "explicit_scenario",
    "usable_window_kwh": 5,
    "charge_ac_kw": 5,
    "discharge_ac_kw": 5,
    "eta_charge": 0.9,
    "eta_discharge": 0.9,
    "internal_aux_kw": 0,
    "standing_loss_rate_per_hour": 0,
}


def mapping(measurement: Measurement) -> CsvMapping:
    return CsvMapping(
        "time",
        "power",
        measurement,
        "interval_average_kw",
        "start",
        "Europe/Berlin",
        "synthetic",
        3600,
        ",",
        ".",
    )


def add_profile(
    workspace: Workspace,
    owner: Actor,
    project_id: str,
    role: Measurement,
    powers: tuple[float, float],
) -> str:
    raw = f"time,power\n2024-03-30T23:00:00Z,{powers[0]}\n2024-03-31T00:00:00Z,{powers[1]}\n".encode()
    return (
        ProfileImport(Assets(workspace))
        .csv(owner, project_id, raw, mapping(role), PROVENANCE, key=f"profile:{role}")
        .id
    )


def create_scenario(
    workspace: Workspace, owner: Actor, *, outage: bool = False
) -> Project:
    project = workspace.create(
        owner,
        "French project, English/German independent",
        {"site": {"country": "FR"}},
        key="create",
    )
    load = add_profile(workspace, owner, project.id, "gross_load", (2, 2))
    pv = add_profile(workspace, owner, project.id, "pv_available_ac", (4, 0))
    aux = add_profile(workspace, owner, project.id, "aux_ac", (0, 0))
    critical = (
        add_profile(workspace, owner, project.id, "critical_load", (1, 1))
        if outage
        else None
    )
    battery = Assets(workspace).add(
        owner,
        project.id,
        encode(BATTERY),
        "application/json",
        "battery_parameters_v1",
        {"retention": "permanent", "provenance": PROVENANCE},
        key="battery",
    )
    schedule: list[Json] = [
        {
            "start_utc": "2024-03-30T23:00:00Z",
            "end_utc": "2024-03-31T01:00:00Z",
            "mode": "connected",
            "reserve_kwh": 0,
            "import_cap_kw": None,
            "export_cap_kw": 0,
            "pv_enabled": True,
            "allow_grid_charge": False,
        }
    ]
    if outage:
        connected = cast(Object, schedule[0])
        connected["end_utc"] = "2024-03-30T23:30:00Z"
        schedule.append(
            {
                **connected,
                "start_utc": "2024-03-30T23:30:00Z",
                "end_utc": "2024-03-31T01:00:00Z",
                "mode": "outage",
                "import_cap_kw": 0,
                "export_cap_kw": 0,
            }
        )
    inputs: Object = {
        "site": {"country": "FR"},
        "energy_replay": {
            "schema_version": 1,
            "gross_load_asset_id": load,
            "critical_load_asset_id": critical,
            "pv_available_asset_id": pv,
            "aux_ac_asset_id": aux,
            "battery_parameters_asset_id": battery.id,
            "initial_inventory": {
                "pv_kwh": 0,
                "grid_kwh": 0,
                "initial_unknown_kwh": 0,
                "basis": "synthetic_fixture",
                "source_note": "explicit empty initial scenario",
            },
            "schedule": schedule,
            "controller": "self_consumption_with_reserve_v1",
            "terminal_min_kwh": 0,
        },
    }
    return workspace.revise(owner, project.id, 1, inputs, key="set-scenario")


def worker(workspace: Workspace, kernel: EnergyKernel) -> Worker:
    return Worker(
        Jobs(workspace),
        "real-energy-worker",
        {"evaluate": kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    )


def object_field(document: Object, name: str) -> Object:
    field = document[name]
    assert isinstance(field, dict)
    return field


def test_real_csv_to_durable_run_keeps_analytic_energy_and_frozen_history(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    run = EnergyService(workspace, kernel, max_attempts=2).evaluate(
        owner, project.id, 2, key="run"
    )
    assert run.state == "queued" and run.result is None
    workspace.revise(
        owner,
        project.id,
        2,
        {**project.inputs, "title_note": "edited after queue"},
        key="newer",
    )
    assert worker(workspace, kernel).run_once()
    result_run = workspace.run(owner, run.id)
    assert result_run.state == "succeeded" and not result_run.is_current
    result = result_run.result
    assert result is not None and result["scenario_constraint_status"] == "satisfied"
    assert result["revision"] == 2 and result["input_sha256"] == project.input_sha256
    energy = object_field(result, "metrics")
    assert energy["gross_load_kwh"] == 4
    assert energy["grid_import_kwh"] == pytest.approx(0.38)
    assert energy["solar_load_kwh"] == pytest.approx(3.62)
    assert object_field(energy, "solar_autarky")["value"] == pytest.approx(0.905)
    assert object_field(result, "equipment_release")["status"] == "not_assessed"
    assert object_field(result, "country_assessment")["status"] == "not_assessed"
    trace_hash = result["trace_sha256"]
    assert isinstance(trace_hash, str)
    trace = workspace.blobs.object(trace_hash)
    assert trace["manifest_sha256"] == run.manifest_sha256
    assert isinstance(trace["flows"], list) and len(trace["flows"]) == 2
    reopened = Workspace(workspace.database.path.parent)
    assert reopened.run(owner, run.id).result == result
    assert reopened.get(owner, project.id).inputs["site"] == {"country": "FR"}


def test_replay_uses_imported_tzif_without_installed_host_timezone(
    workspace: Workspace, owner: Actor, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 2, key="run"
    )
    monkeypatch.setattr(timezone_rules, "TZPATH", ())
    assert worker(workspace, kernel).run_once()
    assert workspace.run(owner, run.id).state == "succeeded"


def test_operating_boundary_splits_hourly_means_without_claiming_new_measurements(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner, outage=True)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 2, key="run"
    )
    assert worker(workspace, kernel).run_once()
    result = workspace.run(owner, run.id).result
    assert result is not None and result["interval_count"] == 3
    energy = object_field(result, "metrics")
    assert energy["load_measurement_scope"] == "mixed"
    assert energy["gross_load_kwh"] is None
    assert object_field(energy, "solar_autarky")["value"] is None
    periods = object_field(result, "profile_interpretation")["operating_periods"]
    assert isinstance(periods, list)
    first = periods[0]
    assert isinstance(first, dict)
    profile = object_field(object_field(first, "profiles"), "gross_load")
    assert profile["effective_max_interval_seconds"] == 3600
    assert profile["reconstructed_means"] is True


def test_wrong_runtime_fails_explicitly_and_never_relabels_latest(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 2, key="run"
    )
    kernel.runtime = replace(kernel.runtime, sha256="f" * 64)
    assert worker(workspace, kernel).run_once()
    failed = workspace.run(owner, run.id)
    assert failed.state == "failed" and failed.result is None
    assert failed.error == {"code": "version_unavailable", "retryable": False}


def test_missing_pinned_profile_fails_without_zero_filling(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 2, key="run"
    )
    context = object_field(run.manifest, "context")
    raw_hash = object_field(context, "assets")["gross_load.raw"]
    assert isinstance(raw_hash, str)
    (workspace.blobs.directory / raw_hash[:2] / raw_hash).unlink()
    assert worker(workspace, kernel).run_once()
    assert workspace.run(owner, run.id).error == {
        "code": "version_unavailable",
        "retryable": False,
    }


def test_same_client_intent_retries_after_runtime_settings_change(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    first = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 2, key="same"
    )
    later_kernel = EnergyKernel(
        workspace, Tolerance(1e-8, 1e-8, 1e-10), max_intervals=200
    )
    repeated = EnergyService(workspace, later_kernel, max_attempts=3).evaluate(
        owner, project.id, 2, key="same"
    )
    assert repeated.id == first.id and repeated.manifest == first.manifest
    assert len(workspace.runs(owner, project.id)) == 1


def test_foreign_asset_id_cannot_be_bound_to_an_owned_run(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    stranger = Actor("user", "stranger")
    other = workspace.create(stranger, "Other", {}, key="other")
    other_profile = add_profile(workspace, stranger, other.id, "gross_load", (100, 100))
    scenario = object_field(project.inputs, "energy_replay")
    scenario["gross_load_asset_id"] = other_profile
    changed = workspace.revise(owner, project.id, 2, project.inputs, key="foreign-ref")
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    with pytest.raises(NotFound):
        EnergyService(workspace, kernel, max_attempts=1).evaluate(
            owner, project.id, changed.revision, key="bad"
        )


def test_invalid_input_units_or_string_numbers_are_not_coerced(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    scenario = object_field(project.inputs, "energy_replay")
    object_field(scenario, "initial_inventory")["pv_kwh"] = "12"
    with pytest.raises(InvalidInput, match="initial_inventory.pv_kwh"):
        EnergyInputs.from_project(project.inputs)


def test_profile_retry_does_not_recapture_changed_timezone(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Import", {}, key="create")
    importer = ProfileImport(Assets(workspace))
    raw = b"time,power\n2024-03-30T23:00:00Z,2\n"
    first = importer.csv(
        owner, project.id, raw, mapping("gross_load"), PROVENANCE, key="same"
    )

    def unavailable(_: str) -> timezone_rules.TimezoneRules:
        raise AssertionError("retry must read its first receipt")

    importer.timezone_loader = unavailable
    assert (
        importer.csv(
            owner, project.id, raw, mapping("gross_load"), PROVENANCE, key="same"
        )
        == first
    )
    with pytest.raises(Conflict):
        importer.csv(
            owner,
            project.id,
            raw.replace(b",2", b",3"),
            mapping("gross_load"),
            PROVENANCE,
            key="same",
        )


def test_temporary_provider_content_cannot_enter_permanent_backup_cas(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(
        owner, "No permanent restricted content", {}, key="create"
    )
    with pytest.raises(InvalidInput, match="temporary asset store"):
        Assets(workspace).add(
            owner,
            project.id,
            b"provider raw response",
            "application/json",
            "provider",
            {"retention": "30_days", "provenance": PROVENANCE},
            key="restricted",
        )


def test_backup_restore_replays_real_pinned_energy_without_original_store(
    workspace: Workspace, owner: Actor, tmp_path: Path
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 2, key="run"
    )
    backup = tmp_path / "backup"
    archive.backup(workspace, backup)
    restored_path = tmp_path / "restored"
    restored = archive.restore(backup, restored_path)
    restored_kernel = EnergyKernel(restored, TOLERANCE, max_intervals=100)
    assert worker(restored, restored_kernel).run_once()
    result = restored.run(owner, run.id)
    assert result.state == "succeeded" and result.result is not None
    assert object_field(result.result, "metrics")["solar_load_kwh"] == pytest.approx(
        3.62
    )


def test_role_substitution_cannot_relabel_net_import_as_gross_load(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    net = add_profile(workspace, owner, project.id, "net_import", (1, 1))
    object_field(project.inputs, "energy_replay")["gross_load_asset_id"] = net
    changed = workspace.revise(owner, project.id, 2, project.inputs, key="net-as-load")
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, changed.revision, key="bad"
    )
    assert worker(workspace, kernel).run_once()
    result = workspace.run(owner, run.id)
    assert (
        result.error == {"code": "invalid_input", "retryable": False}
        and result.result is None
    )


def test_pinned_hash_substitution_cannot_override_the_input_asset_id(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    scenario = EnergyInputs.from_project(project.inputs)
    context = kernel.context(owner, project.id, scenario)
    alternative = ProfileImport(Assets(workspace)).csv(
        owner,
        project.id,
        b"time,power\n2024-03-30T23:00:00Z,100\n2024-03-31T00:00:00Z,100\n",
        mapping("gross_load"),
        PROVENANCE,
        key="alternative",
    )
    context = replace(
        context,
        assets={
            **context.assets,
            "gross_load.raw": alternative.content_sha256,
            "gross_load.metadata": alternative.metadata_sha256,
        },
    )
    run = workspace.evaluate(
        owner, project.id, 2, context, key="forged-context", max_attempts=1
    )
    assert worker(workspace, kernel).run_once()
    failed = workspace.run(owner, run.id)
    assert failed.error == {"code": "version_unavailable", "retryable": False}


def test_unknown_model_version_is_not_reinterpreted_by_the_current_worker(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    context = kernel.context(
        owner, project.id, EnergyInputs.from_project(project.inputs)
    )
    context = replace(context, models={**context.models, "battery": "unknown_v999"})
    run = workspace.evaluate(
        owner, project.id, 2, context, key="unknown-model", max_attempts=1
    )
    assert worker(workspace, kernel).run_once()
    assert workspace.run(owner, run.id).error == {
        "code": "version_unavailable",
        "retryable": False,
    }


def test_missing_critical_profile_is_an_error_not_gross_load_in_disguise(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner, outage=True)
    object_field(project.inputs, "energy_replay")["critical_load_asset_id"] = None
    workspace.revise(owner, project.id, 2, project.inputs, key="missing-critical")
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 3, key="run"
    )
    assert worker(workspace, kernel).run_once()
    assert workspace.run(owner, run.id).error == {
        "code": "invalid_input",
        "retryable": False,
    }


def test_interval_resource_limit_is_explicit_and_never_changes_the_data(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=1)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 2, key="too-many"
    )
    assert worker(workspace, kernel).run_once()
    failed = workspace.run(owner, run.id)
    assert (
        failed.error == {"code": "invalid_input", "retryable": False}
        and failed.result is None
    )
    assert failed.manifest == run.manifest


def test_parallel_csv_retries_register_one_immutable_asset(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Parallel import", {}, key="new")
    raw = b"time,power\n2024-03-30T23:00:00Z,2\n"

    def upload(_: int) -> str:
        own_connection = Workspace(workspace.database.path.parent)
        return (
            ProfileImport(Assets(own_connection))
            .csv(owner, project.id, raw, mapping("gross_load"), PROVENANCE, key="same")
            .id
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(upload, range(2)))
    assert ids[0] == ids[1]
    with workspace.database.read() as connection:
        assert (
            connection.execute("SELECT count(*) FROM project_assets").fetchone()[0] == 1
        )


def test_team_read_authority_does_not_grant_import_write_authority(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "Read only team", {}, key="new")
    team = Actor("team", "verified-team")
    assert workspace.get(team, project.id).id == project.id

    def forbidden_loader(_: str) -> timezone_rules.TimezoneRules:
        raise AssertionError("unauthorized importer must be rejected before parsing")

    with pytest.raises(NotFound):
        ProfileImport(Assets(workspace), timezone_loader=forbidden_loader).csv(
            team,
            project.id,
            b"time,power\n",
            mapping("gross_load"),
            PROVENANCE,
            key="not-authorized",
        )


def test_backup_detects_missing_profile_child_before_any_evaluation(
    workspace: Workspace, owner: Actor, tmp_path: Path
) -> None:
    project = workspace.create(owner, "Not yet evaluated", {}, key="new")
    asset_id = add_profile(workspace, owner, project.id, "gross_load", (2, 2))
    metadata = Assets(workspace).get(owner, project.id, asset_id).metadata
    child = metadata["timezone_rules_sha256"]
    assert isinstance(child, str)
    (workspace.blobs.directory / child[:2] / child).unlink()
    destination = tmp_path / "must-not-publish"
    with pytest.raises(VersionUnavailable):
        archive.backup(workspace, destination)
    assert not destination.exists()
