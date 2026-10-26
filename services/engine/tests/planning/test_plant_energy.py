"""Joint-connection counterexamples that a summed battery cannot reproduce."""

from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from linker_engine.planning.dispatch_frame import Command
from linker_engine.planning.energy_origins import EnergyOrigins
from linker_engine.planning.interval import Interval
from linker_engine.planning.plant_energy_checks import verify
from linker_engine.planning.plant_energy_dispatch import replay, self_consumption, step
from linker_engine.planning.plant_energy_model import PlantFrame, StorageUnit

from .test_dispatch import TOLERANCE, battery, frame
from .test_equipment import feed as feed
from .test_equipment import plant_inputs, prepared_dc_fixture_source


def test_native_joint_parameters_run_trace_and_report_share_one_owned_plant(
    feed, engine, workspace, owner, monkeypatch
) -> None:
    from linker_engine.planning.energy_kernel import EnergyKernel
    from linker_engine.planning.energy_service import EnergyService
    from linker_engine.planning.execution_registry import service_registry
    from linker_engine.planning.http_app import HttpLimits, create_private_app
    from linker_engine.planning.jobs import Jobs
    from linker_engine.planning.plant_energy_kernel import PlantEnergyKernel
    from linker_engine.planning.report_kernel import ReportKernel, ReportService
    from linker_engine.planning.worker import Worker

    from .test_energy_kernel import create_scenario
    from .test_private_http import TOKEN, headers

    feed, source, loaded, _, _, _ = prepared_dc_fixture_source(
        feed, engine, monkeypatch, reverse_ac_kw=5
    )
    project = create_scenario(workspace, owner)
    previous = project.inputs["energy_replay"]
    plant = plant_inputs(feed, coordinated=False)
    plant["requirements"]["pv_dc_kw"] = 0
    for unit in plant["units"]:
        unit["selection"]["pv_dc_kw"] = 0
    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        {"equipment_plant": plant},
        key="joint-plant",
    )
    single = EnergyKernel(workspace, TOLERANCE, max_intervals=20, products=source)
    joint = PlantEnergyKernel(workspace, TOLERANCE, max_intervals=20, products=source)
    energy = EnergyService(workspace, single, max_attempts=1, plant_kernel=joint)
    reports = ReportService(workspace, ReportKernel(workspace, source), max_attempts=1)
    registry = service_registry(energy, None, reports=reports)
    executor = Worker(
        Jobs(workspace),
        "native-joint-fixture",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 10_000, 10, 32),
        product_provider=lambda: loaded,
        reports=reports,
    )
    assumptions = {
        "schema_version": 1,
        "model": "constant_window_shared_dc_bus_v1",
        "parameter_basis": "explicit_loss_scenario_with_woo_equipment",
        "battery_port_id": "BAT1",
        "battery_temperature_c": 20,
        "eta_bus_to_battery": 1,
        "eta_battery_to_bus": 1,
        "eta_store_charge": 0.9,
        "eta_store_discharge": 0.9,
        "eta_inverter_forward": 1,
        "eta_inverter_reverse": 1,
        "internal_aux_kw": 0,
        "standing_loss_rate_per_hour": 0,
        "source_note": "Synthetic native loss scenario; reverse figures use a fixture-only source, not manufacturer specifications.",
    }
    with TestClient(app) as client:
        unprepared = client.post(
            "/runs/energy",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": project.revision,
                "key": "no-single-battery-fallback",
            },
            headers=headers(owner),
        )
        assert unprepared.status_code == 422
        assets = {}
        for unit in plant["units"]:
            response = client.post(
                "/battery/scenario",
                json={
                    "schema_version": 1,
                    "project_id": project.id,
                    "expected_revision": project.revision,
                    "equipment_unit_id": unit["id"],
                    "parameters": assumptions,
                    "source_note": "Owned joint unit fixture",
                    "key": "joint-parameters-" + unit["id"],
                },
                headers=headers(owner),
            )
            assert response.status_code == 200, response.text
            assets[unit["id"]] = response.json()
        scenario = {
            "schema_version": 1,
            "coupling": "plant_ac",
            "gross_load_asset_id": previous["gross_load_asset_id"],
            "critical_load_asset_id": None,
            "pv_available_asset_id": previous["pv_available_asset_id"],
            "aux_ac_asset_id": previous["aux_ac_asset_id"],
            "schedule": previous["schedule"],
            "controller": "proportional_available_power_self_consumption_v1",
            "units": [
                {
                    "unit_id": unit["id"],
                    "battery_parameters_asset_id": assets[unit["id"]]["id"],
                    "initial_inventory": {
                        "pv_kwh": 0,
                        "grid_kwh": 0,
                        "initial_unknown_kwh": 0,
                        "basis": "synthetic_fixture",
                        "source_note": "Empty distinct unit fixture",
                    },
                    "reserve_kwh": 0,
                    "terminal_min_kwh": None,
                    "pv_dc_input_unused": True,
                }
                for unit in plant["units"]
            ],
        }
        project = workspace.revise(
            owner,
            project.id,
            project.revision,
            {**project.inputs, "energy_plant": scenario},
            key="joint-scenario",
        )
        response = client.post(
            "/runs/energy",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": project.revision,
                "key": "native-joint-run",
            },
            headers=headers(owner),
        )
        assert response.status_code == 200, response.text
        rid = response.json()["id"]
        assert executor.run_once()
        run = workspace.run(owner, rid)
        assert run.state == "succeeded", run.error
        result = run.result
        assert result["kind"] == joint.kind
        assert result["verification"]["physical_passed"]
        assert result["metrics"]["grid_import_kwh"] == pytest.approx(0.38)
        assert {row["unit_id"] for row in result["metrics"]["units"]} == {"a", "b"}
        trace = client.post(
            "/runs/trace",
            json={
                "schema_version": 1,
                "run_id": rid,
                "offset": 0,
                "page_size": 2,
                "unit_id": "a",
            },
            headers=headers(owner),
        )
        assert trace.status_code == 200, trace.text
        assert trace.json()["rows"][0]["unit"]["unit_id"] == "a"
        assert trace.json()["rows"][1]["unit"]["after"]["pv_kwh"] == pytest.approx(0)
        response = client.post(
            "/runs/report",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": project.revision,
                "key": "native-joint-report",
                "options": {
                    "locale": "de",
                    "energy_run_id": rid,
                    "pv_run_id": None,
                    "equipment_run_id": None,
                    "logo": None,
                },
            },
            headers=headers(owner),
        )
        assert response.status_code == 200, response.text
        report_id = response.json()["id"]
        assert executor.run_once()
        report = workspace.run(owner, report_id)
        assert report.state == "succeeded", report.error
        assert report.result["prepared_asset"]["content_sha256"]

        # The new model must be admitted by the existing comparison consumer;
        # no new physical replay is needed to read its frozen state keys.
        from linker_engine.planning.energy_comparison import comparison_side
        from linker_engine.planning.errors import EvidenceMissing, InvalidInput
        from linker_engine.planning.plant_energy_inputs import PlantEnergyInputs

        side = comparison_side(workspace, owner, project.id, rid)
        assert set(side.inventory_key()) == {"a", "b"}
        assert side.reference()["coupling"] == "plant_ac"
        assert side.reference()["usable_window_kwh"] > 0
        wrong_unit = {
            **scenario,
            "units": [
                {
                    **u,
                    "battery_parameters_asset_id": scenario["units"][0][
                        "battery_parameters_asset_id"
                    ],
                }
                for u in scenario["units"]
            ],
        }
        with pytest.raises(InvalidInput):
            joint.context(
                owner, project.id, {**project.inputs, "energy_plant": wrong_unit}
            )
        with pytest.raises(EvidenceMissing) as unsupported:
            PlantEnergyInputs.from_project(
                {
                    **project.inputs,
                    "energy_plant": {
                        **scenario,
                        "schedule": [
                            {
                                **scenario["schedule"][0],
                                "mode": "outage",
                                "allow_grid_charge": False,
                            }
                        ],
                    },
                }
            )
        assert (
            unsupported.value.public_details["constraint_id"]
            == "joint_outage_ac_pv_topology"
        )

        # Opt-in capture reuses this native worker output for the distinct
        # browser consumer. Synthetic source rows never enter product runtime.
        import os
        from pathlib import Path

        from linker_engine.planning.canonical import encode
        from linker_engine.planning.http_views import project_view, run_view

        capture = os.environ.get("PLANNER_CLIENT_FIXTURE")
        if capture:
            Path(capture).write_bytes(
                encode(
                    {
                        "run": run_view(run),
                        "project": project_view(project),
                        "trace": trace.json(),
                        "report": run_view(report),
                    }
                )
            )


def test_joint_verifier_cannot_finance_microsecond_delivery_from_soft_stock_tolerance() -> (
    None
):
    site = frame(0, load=1, import_cap=0)
    site = replace(
        site,
        interval=Interval(
            site.interval.start, site.interval.start + timedelta(microseconds=1)
        ),
    )
    units = (StorageUnit("a", battery(10, 1)),)
    initial = {"a": EnergyOrigins(0, 0, 0)}
    original = step(
        PlantFrame(site, {"a": 0}),
        units,
        initial,
        {"a": Command(0, 1)},
        tolerance=TOLERANCE,
    )
    ghost = EnergyOrigins(0, site.interval.hours, 0)
    unit = replace(
        original.units[0], before=ghost, withdrawn_internal=ghost, delivered_ac=ghost
    )
    forged = replace(
        original,
        units=(unit,),
        load_sources=ghost,
        battery_to_load_ac=ghost,
        unserved_load_kwh=0,
    )
    result = verify(
        (forged,), units, TOLERANCE, initial=initial, terminal_min_kwh={"a": None}
    )
    assert not result.physical_passed
    assert any(
        c.code == "unit:a:inventory_discharge_power" and not c.passed
        for c in result.checks
    )
    # The same tiny stock cannot change source identity either. Its total
    # budget is valid, so only an independent origin binding rejects this.
    solar = EnergyOrigins(site.interval.hours, 0, 0)
    relabelled = replace(
        forged,
        units=(
            replace(unit, before=solar, withdrawn_internal=solar, delivered_ac=solar),
        ),
        load_sources=solar,
        battery_to_load_ac=solar,
    )
    source_check = verify(
        (relabelled,),
        units,
        TOLERANCE,
        initial={"a": ghost},
        terminal_min_kwh={"a": None},
    )
    assert not source_check.physical_passed
    assert any(
        c.code == "unit:a:continuity_pv_kwh" and not c.passed
        for c in source_check.checks
    )


def test_joint_verifier_keeps_common_bus_mixing_in_load_and_destination_inventory() -> (
    None
):
    units = (StorageUnit("a", battery(1, 1)), StorageUnit("b", battery(1, 1)))
    initial = {"a": EnergyOrigins(0, 1, 0), "b": EnergyOrigins(0, 0, 0)}
    mixed = step(
        PlantFrame(frame(0, load=1, pv=1, import_cap=0), {"a": 0, "b": 0}),
        units,
        initial,
        {"a": Command(0, 1), "b": Command(1, 0)},
        tolerance=TOLERANCE,
    )
    assert mixed.load_sources.pv_kwh == mixed.load_sources.grid_kwh == 0.5
    assert mixed.units[1].after.pv_kwh == mixed.units[1].after.grid_kwh == 0.5
    assert verify(
        (mixed,),
        units,
        TOLERANCE,
        initial=initial,
        terminal_min_kwh={"a": None, "b": None},
    ).passed
    destination = replace(
        mixed.units[1], received_ac=EnergyOrigins(0, 1, 0), after=EnergyOrigins(0, 1, 0)
    )
    forged = replace(
        mixed,
        units=(mixed.units[0], destination),
        load_sources=EnergyOrigins(1, 0, 0),
        direct_pv_to_load_kwh=1,
        direct_pv_to_charge_kwh=0,
        battery_to_load_ac=EnergyOrigins(0, 0, 0),
    )
    result = verify(
        (forged,),
        units,
        TOLERANCE,
        initial=initial,
        terminal_min_kwh={"a": None, "b": None},
    )
    assert not result.physical_passed
    assert all(c.passed for c in result.checks if c.code.startswith("pcc_source_"))
    assert any(
        not c.passed and c.code.startswith("pcc_mixing_load:") for c in result.checks
    )


def test_joint_replay_keeps_named_power_inventory_grid_cap_and_cross_unit_origins() -> (
    None
):
    units = (
        StorageUnit("empty_fast", battery(10, 10)),
        StorageUnit("full_slow", battery(10, 1)),
    )
    initial = {
        "empty_fast": EnergyOrigins(0, 0, 0),
        "full_slow": EnergyOrigins(0, 10, 0),
    }
    demand = PlantFrame(
        frame(0, load=3, import_cap=1), {"empty_fast": 0, "full_slow": 0}
    )
    flows = replay(
        (demand,),
        units,
        initial,
        self_consumption,
        checkpoint=lambda: None,
        tolerance=TOLERANCE,
    )
    flow = flows[0]
    assert flow.grid_import_kwh == 1
    assert flow.unserved_load_kwh == 1
    assert flow.load_sources.grid_kwh == 2
    assert flow.units[0].after.total == 0
    assert flow.units[1].after.total == 9
    result = verify(
        flows,
        units,
        TOLERANCE,
        initial=initial,
        terminal_min_kwh={u.id: None for u in units},
    )
    assert not result.passed
    assert [check.code for check in result.checks if not check.passed] == [
        "unserved_load"
    ]

    # Different devices may transfer energy through the AC bus, including
    # conversion loss. This must not invent PV or move DC inventory directly.
    transfer_units = (
        StorageUnit("a", battery(5, 5, eta=0.9)),
        StorageUnit("b", battery(5, 5, eta=0.9)),
    )
    transfer_initial = {"a": EnergyOrigins(0, 5, 0), "b": EnergyOrigins(0, 0, 0)}
    transfer_frame = PlantFrame(frame(0, load=0, import_cap=0), {"a": 0, "b": 0})
    transfer = step(
        transfer_frame,
        transfer_units,
        transfer_initial,
        {"a": Command(0, 5), "b": Command(5, 0)},
        tolerance=TOLERANCE,
    )
    assert transfer.grid_import_kwh == transfer.export_sources.total == 0
    assert transfer.units[0].after.total == 0
    assert transfer.units[1].after.grid_kwh == pytest.approx(4.05)
    assert transfer.units[1].after.pv_kwh == 0
    assert verify(
        (transfer,),
        transfer_units,
        TOLERANCE,
        initial=transfer_initial,
        terminal_min_kwh={"a": None, "b": None},
    ).passed
    forged = replace(
        transfer,
        units=(
            transfer.units[0],
            replace(transfer.units[1], after=EnergyOrigins(4.05, 0, 0)),
        ),
    )
    assert not verify(
        (forged,),
        transfer_units,
        TOLERANCE,
        initial=transfer_initial,
        terminal_min_kwh={"a": None, "b": None},
    ).passed
