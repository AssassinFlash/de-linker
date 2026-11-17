"""Real CSV/assets/durable-worker/replay/result paths with analytic fixtures."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from linker_engine.planning import archive, timezone_rules
from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import Json, Object, encode
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.energy_inputs import BatteryParameters, EnergyInputs
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
from linker_engine.planning.project_input_contracts import SUPPORTED_INPUT_CONTRACTS
from linker_engine.planning.records import Actor, Project
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object

TOLERANCE = Tolerance(1e-7, 1e-7, 1e-9)
PROVENANCE: FixtureObject = {
    "label": "Analytic two-hour fixture; no real customer, weather or SKU",
    "basis": "synthetic_fixture",
    "rights_basis": "created by this test; permanent private retention allowed",
}
BATTERY: FixtureObject = {
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


def authored_from_execution(
    inputs: FixtureObject, losses: FixtureObject | None = None
) -> FixtureObject:
    """Reuse the established physical fixture as current editor declarations."""
    result = deepcopy(inputs)
    joint = "energy_plant" in result
    scenario = result.pop("energy_plant" if joint else "energy_replay")
    periods = [
        {
            **p,
            "id": "a" * 32,
            "import_policy": "unlimited" if p["import_cap_kw"] is None else "limited",
            "export_policy": "unlimited" if p["export_cap_kw"] is None else "limited",
        }
        for p in scenario["schedule"]
    ]
    profiles = {
        role: scenario[field]
        for role, field in (
            ("gross_load", "gross_load_asset_id"),
            ("critical_load", "critical_load_asset_id"),
            ("pv_available_ac", "pv_available_asset_id"),
            ("aux_ac", "aux_ac_asset_id"),
            ("pv_reference", "pv_reference_asset_id"),
        )
        if scenario.get(field) is not None
    }
    result["profile_selections"] = {"schema_version": 1, "selected": profiles}

    def settings(state: FixtureObject) -> FixtureObject:
        inventory = {
            k: v for k, v in state["initial_inventory"].items() if k != "basis"
        }
        draft: FixtureObject = {
            "schema_version": 1,
            "battery": {
                k: v
                for k, v in BATTERY.items()
                if k not in ("schema_version", "model", "parameter_basis")
            },
            "source_note": "Explicit analytic fixture",
            "initial_inventory": inventory,
            "schedule": periods,
            "terminal_policy": "none"
            if state["terminal_min_kwh"] is None
            else "minimum",
            "terminal_min_kwh": state["terminal_min_kwh"],
        }
        if losses is not None:
            draft["dc"] = {
                "source_note": losses["source_note"],
                "battery_port_id": losses["battery_port_id"],
                "pv_converter_id": state.get("pv_converter_id", ""),
                "aux_dc_kw": state.get("aux_dc_kw", 0),
                "losses": {
                    k: v
                    for k, v in losses.items()
                    if k.startswith("eta_")
                    or k in ("internal_aux_kw", "standing_loss_rate_per_hour")
                },
                **{
                    k: losses[k]
                    for k in ("battery_temperature_c", "capacity_window_basis")
                    if k in losses
                },
            }
        return draft

    if joint:
        result["energy_plant_setup"] = {
            "schema_version": 1,
            "coupling": scenario["coupling"],
            "schedule": periods,
            **(
                {"controller": scenario["controller"]}
                if scenario["coupling"] == "plant_ac"
                else {}
            ),
            "ac_pv_converter_ids": scenario.get("ac_pv_converter_ids", []),
            "units": [
                {
                    "unit_id": unit["unit_id"],
                    "settings": settings(unit),
                    "reserve_kwh": unit["reserve_kwh"],
                    "pv_dc_input_unused": unit.get("pv_converter_id") is None,
                    "allow_ac_charge": unit.get("allow_ac_charge"),
                }
                for unit in scenario["units"]
            ],
        }
    else:
        result["energy_scenario"] = {
            **settings(scenario),
            "coupling": scenario.get("coupling", "independent_ac"),
            "controller": scenario["controller"],
        }
    return result


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
    inputs: FixtureObject = {
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


def object_field(document: FixtureObject, name: str) -> FixtureObject:
    field = document[name]
    assert isinstance(field, dict)
    return field


def test_storage_only_replay_needs_no_pv_source_and_keeps_zero_solar_accounting(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    scenario = object_field(project.inputs, "energy_replay")
    pv_asset_id = scenario["pv_available_asset_id"]
    scenario["pv_available_asset_id"] = None
    scenario["initial_inventory"] = {
        "pv_kwh": 0,
        "grid_kwh": 5,
        "initial_unknown_kwh": 0,
        "basis": "user_declared",
        "source_note": "Declared starting charge",
    }
    for period in scenario["schedule"]:
        period["pv_enabled"] = False
    inputs: Object = {
        **project.inputs,
        "brief": {
            "schema_version": 1,
            "project_use": "commercial",
            "system_scope": "storage_only",
            "site": {
                "country_code": "FR",
                "location_label": "Test site",
                "latitude": None,
                "longitude": None,
                "coordinate_basis": "not_provided",
                "timezone": "Europe/Paris",
            },
            "annual_load": {"kwh": None, "basis": None, "source_note": ""},
            "project_note": "",
        },
        "energy_replay": scenario,
    }
    from linker_engine.planning.project_input_contracts import SUPPORTED_INPUT_CONTRACTS

    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        inputs,
        key="storage-only",
        input_contract=SUPPORTED_INPUT_CONTRACTS[-1],
    )
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    run = EnergyService(workspace, kernel, max_attempts=2).evaluate(
        owner, project.id, project.revision, key="storage-run"
    )
    assert worker(workspace, kernel).run_once()
    completed = workspace.run(owner, run.id)
    assert completed.state == "succeeded", completed.error
    result = json_object(completed.result)
    energy = object_field(result, "metrics")
    assert energy["gross_load_kwh"] == 4
    assert energy["grid_import_kwh"] == pytest.approx(0)
    assert energy["solar_load_kwh"] == 0
    assert energy["solar_autarky"]["value"] == 0
    pv = result["profile_interpretation"]["operating_periods"][0]["profiles"][
        "pv_available_ac"
    ]
    assert pv["source"]["details"]["basis"] == "pv_disabled_for_entire_schedule"
    for violation in ("asset", "generation", "initial"):
        invalid = deepcopy(inputs)
        changed = object_field(invalid, "energy_replay")
        if violation == "asset":
            changed["pv_available_asset_id"] = pv_asset_id
        elif violation == "generation":
            changed["schedule"][0]["pv_enabled"] = True
        else:
            changed["initial_inventory"]["pv_kwh"] = 1
        project = workspace.revise(
            owner,
            project.id,
            project.revision,
            invalid,
            key="forbidden-pv-" + violation,
            input_contract=SUPPORTED_INPUT_CONTRACTS[-1],
        )
        with pytest.raises(InvalidInput, match="storage-only"):
            EnergyService(workspace, kernel, max_attempts=1).evaluate(
                owner, project.id, project.revision, key="forbidden-" + violation
            )


@pytest.mark.parametrize("pv_enabled", [False, True])
def test_pv_backup_can_use_previous_solar_inventory_without_a_generation_source(
    workspace: Workspace, owner: Actor, pv_enabled: bool
) -> None:
    project = create_scenario(workspace, owner, outage=True)
    scenario = object_field(project.inputs, "energy_replay")
    scenario["pv_available_asset_id"] = None
    scenario["initial_inventory"]["pv_kwh"] = 3
    scenario["schedule"] = [
        {
            **scenario["schedule"][1],
            "start_utc": "2024-03-30T23:00:00Z",
            "pv_enabled": pv_enabled,
        }
    ]
    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        {**project.inputs, "energy_replay": scenario},
        key="pv-backup",
        input_contract=SUPPORTED_INPUT_CONTRACTS[-1],
    )
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    service = EnergyService(workspace, kernel, max_attempts=1)
    if pv_enabled:
        with pytest.raises(InvalidInput, match="PV source"):
            service.evaluate(owner, project.id, project.revision, key="backup")
        return
    run = service.evaluate(owner, project.id, project.revision, key="backup")
    assert worker(workspace, kernel).run_once()
    completed = workspace.run(owner, run.id)
    assert completed.state == "succeeded", completed.error
    result = json_object(completed.result)
    assert result["metrics"]["solar_load_kwh"] == pytest.approx(2)
    assert result["metrics"]["stored_initial"]["pv_kwh"] == 3
    assert result["metrics"]["pv_generated_ac_kwh"] == 0
    pv = result["profile_interpretation"]["operating_periods"][0]["profiles"][
        "pv_available_ac"
    ]
    assert pv["source"]["details"]["basis"] == "pv_disabled_for_entire_schedule"


@pytest.mark.parametrize("allow_grid_charge", [True, False])
def test_peak_shaving_recharges_below_the_grid_cap_before_serving_a_peak(
    workspace: Workspace, owner: Actor, allow_grid_charge: bool
) -> None:
    project = create_scenario(workspace, owner)
    scenario = object_field(project.inputs, "energy_replay")
    source = b"time,power\n2024-03-30T23:00:00Z,0\n2024-03-31T00:00:00Z,3\n"
    load = ProfileImport(Assets(workspace)).csv(
        owner, project.id, source, mapping("gross_load"), PROVENANCE, key="peak-load"
    )
    scenario["gross_load_asset_id"] = load.id
    scenario["controller"] = "peak_shaving_with_reserve_v1"
    for period in scenario["schedule"]:
        period.update(
            pv_enabled=False, allow_grid_charge=allow_grid_charge, import_cap_kw=2
        )
    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        {**project.inputs, "energy_replay": scenario},
        key="peak",
        input_contract=SUPPORTED_INPUT_CONTRACTS[-1],
    )
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    run = EnergyService(workspace, kernel, max_attempts=2).evaluate(
        owner, project.id, project.revision, key="peak-run"
    )
    assert worker(workspace, kernel).run_once()
    completed = workspace.run(owner, run.id)
    assert completed.state == "succeeded", completed.error
    result = json_object(completed.result)
    energy = object_field(result, "metrics")
    assert energy["grid_import_kwh"] == pytest.approx(4 if allow_grid_charge else 2)
    assert energy["solar_load_kwh"] == 0
    assert result["scenario_constraint_status"] == (
        "satisfied" if allow_grid_charge else "violated"
    )
    context = object_field(completed.manifest, "context")
    assert context["models"]["controller"] == "peak_shaving_with_reserve_v1"
    from linker_engine.planning.execution_identity import execution_key
    from linker_engine.planning.execution_registry import service_registry

    registry = service_registry(EnergyService(workspace, kernel, max_attempts=1), None)
    assert execution_key(context) in registry.execution_keys()
    flows = json_object(workspace.blobs.object(result["trace_sha256"]))["flows"]
    assert flows[0]["grid_charge_kw"] == pytest.approx(2 if allow_grid_charge else 0)
    assert flows[1]["discharge_kw"] == pytest.approx(1 if allow_grid_charge else 0)


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
    result = json_object(result_run.result)
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
    trace = json_object(workspace.blobs.object(trace_hash))
    assert trace["manifest_sha256"] == run.manifest_sha256
    assert isinstance(trace["flows"], list) and len(trace["flows"]) == 2
    reopened = Workspace(workspace.database.path.parent)
    assert reopened.run(owner, run.id).result == result
    assert json_object(reopened.get(owner, project.id).inputs)["site"] == {
        "country": "FR"
    }


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
    result = json_object(workspace.run(owner, run.id).result)
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
    context = kernel.context(owner, project.id, project.inputs)
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


@pytest.mark.parametrize("peak", [False, True])
def test_registered_worker_rejects_controller_evidence_that_disagrees_with_frozen_inputs(
    workspace: Workspace, owner: Actor, peak: bool
) -> None:
    from linker_engine.planning.execution_registry import service_registry

    project = create_scenario(workspace, owner)
    scenario = object_field(project.inputs, "energy_replay")
    scenario["controller"] = (
        "peak_shaving_with_reserve_v1" if peak else "self_consumption_with_reserve_v1"
    )
    scenario["schedule"][0]["import_cap_kw"] = 2
    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        {**project.inputs, "energy_replay": scenario},
        key="controller",
        input_contract=SUPPORTED_INPUT_CONTRACTS[-1],
    )
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    service = EnergyService(workspace, kernel, max_attempts=1)
    valid = service.evaluate(owner, project.id, project.revision, key="valid")
    context = kernel.context(owner, project.id, project.inputs)
    context = replace(
        context,
        models={
            **context.models,
            "controller": "self_consumption_with_reserve_v1"
            if peak
            else "peak_shaving_with_reserve_v1",
        },
    )
    forged = workspace.evaluate(
        owner,
        project.id,
        project.revision,
        context,
        key="wrong-controller",
        max_attempts=1,
    )
    registry = service_registry(service, None)
    executor = Worker(
        Jobs(workspace),
        "controller-binding-worker",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    assert executor.run_once()
    assert executor.run_once()
    completed = workspace.run(owner, valid.id)
    assert completed.state == "succeeded", completed.error
    assert completed.manifest == valid.manifest
    failed = workspace.run(owner, forged.id)
    assert failed.error == {"code": "version_unavailable", "retryable": False}
    assert failed.manifest == forged.manifest
    assert failed.result is None


def test_unknown_model_version_is_not_reinterpreted_by_the_current_worker(
    workspace: Workspace, owner: Actor
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    context = kernel.context(owner, project.id, project.inputs)
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
    metadata = json_object(Assets(workspace).get(owner, project.id, asset_id).metadata)
    child = metadata["timezone_rules_sha256"]
    assert isinstance(child, str)
    (workspace.blobs.directory / child[:2] / child).unlink()
    destination = tmp_path / "must-not-publish"
    with pytest.raises(VersionUnavailable):
        archive.backup(workspace, destination)
    assert not destination.exists()


@pytest.mark.parametrize("version", [True, 1.0, "1", None, 2])
def test_battery_schema_version_is_an_actual_supported_integer(version: Json) -> None:
    with pytest.raises(InvalidInput, match="schema_version"):
        BatteryParameters.read({**BATTERY, "schema_version": version})


@pytest.mark.parametrize("version", [True, 1.0, "1", None, 2])
def test_scenario_schema_version_wrong_type_is_rejected_before_queue(
    workspace: Workspace,
    owner: Actor,
    version: Json,
) -> None:
    project = create_scenario(workspace, owner)
    object_field(project.inputs, "energy_replay")["schema_version"] = version
    project = workspace.revise(owner, project.id, 2, project.inputs, key="bad-version")
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    with pytest.raises(InvalidInput, match="schema_version"):
        EnergyService(workspace, kernel, max_attempts=1).evaluate(
            owner, project.id, 3, key="run"
        )
    assert not workspace.runs(owner, project.id)


@pytest.mark.parametrize("version", [True, 1.0])
def test_real_worker_also_rejects_wrong_battery_schema_types(
    workspace: Workspace,
    owner: Actor,
    version: Json,
) -> None:
    project = create_scenario(workspace, owner)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100)
    context = kernel.context(owner, project.id, project.inputs)
    bad = Assets(workspace).add(
        owner,
        project.id,
        encode({**BATTERY, "schema_version": version}),
        "application/json",
        "battery_parameters_v1",
        {"retention": "permanent", "provenance": PROVENANCE},
        key="bad-battery",
    )
    object_field(project.inputs, "energy_replay")["battery_parameters_asset_id"] = (
        bad.id
    )
    project = workspace.revise(
        owner, project.id, 2, project.inputs, key="wrong-battery-schema"
    )
    context = replace(
        context,
        assets={
            **context.assets,
            "battery.raw": bad.content_sha256,
            "battery.metadata": bad.metadata_sha256,
        },
    )
    # Bypass only the trusted enqueue adapter to represent malformed durable
    # work: the actual production worker must independently reject its asset.
    run = workspace.evaluate(
        owner, project.id, 3, context, key="worker-validation", max_attempts=1
    )
    assert worker(workspace, kernel).run_once()
    failed = workspace.run(owner, run.id)
    assert failed.error == {"code": "invalid_input", "retryable": False}
    assert failed.result is None
