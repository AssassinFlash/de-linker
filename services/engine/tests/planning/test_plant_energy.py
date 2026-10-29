"""Joint-connection counterexamples that a summed battery cannot reproduce."""

from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from linker_engine.engine import Engine
from linker_engine.planning.dispatch_frame import Command
from linker_engine.planning.energy_origins import EnergyOrigins
from linker_engine.planning.interval import Interval
from linker_engine.planning.plant_energy_checks import verify
from linker_engine.planning.plant_energy_dispatch import replay, self_consumption, step
from linker_engine.planning.plant_energy_model import PlantFrame, StorageUnit
from linker_engine.planning.records import Actor
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object, mapping_role
from .test_dispatch import TOLERANCE, battery, frame
from .test_equipment import feed as feed
from .test_equipment import plant_inputs, prepared_dc_fixture_source


def test_native_joint_parameters_run_trace_and_report_share_one_owned_plant(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
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
    previous = json_object(project.inputs)["energy_replay"]
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
        result = json_object(run.result)
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
        assert json_object(report.result)["prepared_asset"]["content_sha256"]

        # The new model must be admitted by the existing comparison consumer;
        # no new physical replay is needed to read its frozen state keys.
        from linker_engine.planning.energy_comparison import comparison_side
        from linker_engine.planning.errors import EvidenceMissing, InvalidInput
        from linker_engine.planning.plant_energy_inputs import PlantEnergyInputs

        side = comparison_side(workspace, owner, project.id, rid)
        assert set(json_object(side.inventory_key())) == {"a", "b"}
        assert json_object(side.reference())["coupling"] == "plant_ac"
        assert json_object(side.reference())["usable_window_kwh"] > 0
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
                        "run": json_object(run_view(run)),
                        "project": json_object(project_view(project)),
                        "trace": trace.json(),
                        "report": json_object(run_view(report)),
                    }
                )
            )


def test_native_dc_plant_projects_owned_pv_groups_and_keeps_report_stages(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One two-hour producer/command/worker/trace/report path, reused by the UI."""
    import os
    from pathlib import Path

    from linker_engine.planning.assets import Assets
    from linker_engine.planning.canonical import digest, encode
    from linker_engine.planning.csv_mapping import CsvMapping
    from linker_engine.planning.dc_plant_kernel import DcPlantEnergyKernel
    from linker_engine.planning.energy_kernel import EnergyKernel
    from linker_engine.planning.energy_service import EnergyService
    from linker_engine.planning.execution_registry import service_registry
    from linker_engine.planning.http_app import HttpLimits, create_private_app
    from linker_engine.planning.http_views import project_view, run_view
    from linker_engine.planning.jobs import Jobs
    from linker_engine.planning.profile_import import ProfileImport
    from linker_engine.planning.profile_selections import check_profile_selections
    from linker_engine.planning.pv_generation import generate_pv
    from linker_engine.planning.pv_parameters import PvGenerationParameters
    from linker_engine.planning.pv_profile_preparation import PROFILE_PURPOSE
    from linker_engine.planning.report_kernel import ReportKernel, ReportService
    from linker_engine.planning.series_source import SeriesSource
    from linker_engine.planning.worker import Worker

    from .test_energy_kernel import PROVENANCE
    from .test_private_http import TOKEN, headers
    from .test_pv_generation import geometry, parameter_document, weather

    feed, source, loaded, _, _, _ = prepared_dc_fixture_source(
        feed, engine, monkeypatch
    )
    layout, parameters = geometry(), parameter_document()
    module_id = layout["module_specs"][0]["id"]
    layout["module_specs"] = [
        {
            **json_object(source.module_basis())["module"]["specification"],
            "id": module_id,
        }
    ]
    for identifier, position in (("dc-b", 10), ("ac-pv", 14)):
        layout["arrays"].append(
            {
                **layout["arrays"][0],
                "id": identifier,
                "name": identifier,
                "origin_uv": [position, 10],
                "rows": 1,
                "columns": 1,
                "excluded_slots": [],
            }
        )
        parameters["arrays"].append({**parameters["arrays"][0], "array_id": identifier})
        parameters["converters"].append(
            {**parameters["converters"][0], "id": identifier, "array_ids": [identifier]}
        )
    declared = PvGenerationParameters.read(parameters)
    raw = encode({"fixture": "owned synthetic two-hour multi-converter weather"})
    raw_hash = workspace.blobs.put(raw)
    meteo = weather()
    first = meteo.points[0]
    second = replace(
        first,
        interval=Interval(first.interval.end, first.interval.end + timedelta(hours=1)),
        irradiance_at_utc=first.irradiance_at_utc + timedelta(hours=1),
        source_label_utc=first.source_label_utc + timedelta(hours=1),
        ghi_w_m2=0,
        dni_w_m2=0,
        dhi_w_m2=0,
    )
    meteo = replace(
        meteo,
        points=(first, second),
        source=SeriesSource(raw_hash, "synthetic", "UTC", 3600, encode(PROVENANCE)),
    )
    generated = generate_pv(layout, meteo, declared, max_array_steps=10)
    witness = json_object(generated.witness())
    array_power = {row["id"]: row["stc_power_w"] / 1000 for row in witness["arrays"]}
    plant = plant_inputs(feed, coordinated=False)
    groups = {"a": declared.converters[0].id, "b": "dc-b"}
    powers = {"a": array_power[layout["arrays"][0]["id"]], "b": array_power["dc-b"]}
    plant["requirements"]["pv_dc_kw"] = sum(powers.values())
    for unit in plant["units"]:
        unit["selection"]["pv_dc_kw"] = powers[unit["id"]]
    project = workspace.create(
        owner,
        "Synthetic multi-hybrid retained-DC integration",
        {
            "geometry": layout,
            "pv_generation": declared.model_dump(mode="json"),
            "equipment_plant": plant,
        },
        key="dc-plant",
    )
    assets = Assets(workspace)
    pv = assets.add(
        owner,
        project.id,
        raw,
        "application/json",
        PROFILE_PURPOSE,
        {
            "schema": 1,
            "profile_type": PROFILE_PURPOSE,
            "retention": "permanent",
            "provenance": PROVENANCE,
            "geometry_sha256": digest(encode(layout)),
            "parameters_sha256": digest(
                encode(json_object(project.inputs)["pv_generation"])
            ),
            "woo_module_inputs": json_object(source.module_basis()),
            "dependencies": {
                "pv_model_inputs": workspace.blobs.put(generated.inputs_json),
                "pv_model_witness": workspace.blobs.put(generated.witness_json),
            },
        },
        key="dc-plant-pv",
    )
    profiles = {}
    for role, values in (("gross_load", (0, 1)), ("aux_ac", (0, 0))):
        content = (
            "time,power\n"
            + "".join(
                f"{point.interval.start.isoformat()},{power}\n"
                for point, power in zip(meteo.points, values, strict=True)
            )
        ).encode()
        profiles[role] = (
            ProfileImport(assets)
            .csv(
                owner,
                project.id,
                content,
                CsvMapping(
                    "time",
                    "power",
                    mapping_role(role),
                    "interval_average_kw",
                    "start",
                    "UTC",
                    "synthetic",
                    3600,
                    ",",
                    ".",
                ),
                PROVENANCE,
                key="dc-plant-" + role,
            )
            .id
        )
    single = EnergyKernel(workspace, TOLERANCE, max_intervals=20, products=source)
    joint = DcPlantEnergyKernel(workspace, TOLERANCE, max_intervals=20, products=source)
    energy = EnergyService(workspace, single, max_attempts=1, plant_dc_kernel=joint)
    reports = ReportService(workspace, ReportKernel(workspace, source), max_attempts=1)
    registry = service_registry(energy, None, reports=reports)
    executor = Worker(
        Jobs(workspace),
        "native-dc-plant",
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
        "eta_store_charge": 1,
        "eta_store_discharge": 1,
        "eta_inverter_forward": 1,
        "eta_inverter_reverse": None,
        "internal_aux_kw": 0,
        "standing_loss_rate_per_hour": 0,
        "source_note": "Synthetic loss scenario, no inferred reverse conversion or equipment release",
    }
    with TestClient(app) as client:
        prepared = {}
        for uid in groups:
            response = client.post(
                "/battery/scenario",
                json={
                    "schema_version": 1,
                    "project_id": project.id,
                    "expected_revision": project.revision,
                    "equipment_unit_id": uid,
                    "parameters": assumptions,
                    "source_note": "Owned synthetic DC plant port",
                    "key": "dc-plant-parameters-" + uid,
                },
                headers=headers(owner),
            )
            assert response.status_code == 200, response.text
            prepared[uid] = response.json()["id"]
        scenario = {
            "schema_version": 1,
            "coupling": "plant_shared_dc",
            "gross_load_asset_id": profiles["gross_load"],
            "critical_load_asset_id": None,
            "pv_available_asset_id": None,
            "pv_reference_asset_id": pv.id,
            "ac_pv_converter_ids": ["ac-pv"],
            "aux_ac_asset_id": profiles["aux_ac"],
            "schedule": [
                {
                    "start_utc": first.interval.start.isoformat(),
                    "end_utc": second.interval.end.isoformat(),
                    "mode": "connected",
                    "reserve_kwh": 0,
                    "import_cap_kw": None,
                    "export_cap_kw": 0,
                    "pv_enabled": True,
                    "allow_grid_charge": False,
                }
            ],
            "units": [
                {
                    "unit_id": uid,
                    "battery_parameters_asset_id": prepared[uid],
                    "initial_inventory": {
                        "pv_kwh": 0,
                        "grid_kwh": 0,
                        "initial_unknown_kwh": 0,
                        "basis": "synthetic_fixture",
                        "source_note": "Empty distinct DC fixture",
                    },
                    "reserve_kwh": 0,
                    "terminal_min_kwh": 0,
                    "pv_converter_id": group,
                    "aux_dc_kw": 0,
                    "allow_ac_charge": False,
                }
                for uid, group in groups.items()
            ],
            "controller": "local_dc_then_proportional_ac_self_consumption_v1",
        }
        inputs: FixtureObject = {
            **project.inputs,
            "energy_plant": scenario,
            "profile_selections": {
                "schema_version": 1,
                "selected": {**profiles, "pv_reference": pv.id},
            },
        }
        from linker_engine.planning.dc_plant_inputs import DcPlantEnergyInputs
        from linker_engine.planning.errors import EvidenceMissing
        from linker_engine.planning.plant_energy_kernel import (
            check_plant_profile_boundary,
        )

        frozen_scenario = DcPlantEnergyInputs.read(json_object(scenario))
        for purpose in (
            "pvlib_reference_profile_v1",
            "pvgis_roof_ac_reference_profile_v1",
            "geometric_pv_reference_profile_v1",
        ):
            with pytest.raises(EvidenceMissing, match="plant_dc_duplicate_pv_source"):
                check_plant_profile_boundary(
                    frozen_scenario, "pv_available_ac", {"profile_type": purpose}
                )
        # A distinct external AC profile remains admissible alongside roof DC.
        check_plant_profile_boundary(
            frozen_scenario,
            "pv_available_ac",
            {"profile_type": "pvgis_system_profile_v1"},
        )
        check_profile_selections(assets, owner, project.id, inputs)
        project = workspace.revise(
            owner, project.id, project.revision, inputs, key="dc-plant-inputs"
        )
        response = client.post(
            "/runs/energy",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": project.revision,
                "key": "dc-plant-run",
            },
            headers=headers(owner),
        )
        assert response.status_code == 200, response.text
        assert executor.run_once()
        run = workspace.run(owner, response.json()["id"])
        assert run.state == "succeeded", run.error
        assert json_object(run.result)["metrics"]["solar_load_kwh"] > 0
        assert json_object(run.result)["metrics"]["pv_generated_dc_kwh"] > 0
        assert json_object(run.result)["metrics"]["pv_input_self_use"] == {
            "value": None,
            "undefined_reason": "mixed_pv_measurement_stages",
        }
        trace = client.post(
            "/runs/trace",
            json={
                "schema_version": 1,
                "run_id": run.id,
                "offset": 0,
                "page_size": 2,
                "unit_id": "a",
            },
            headers=headers(owner),
        )
        assert trace.status_code == 200, trace.text
        assert (
            trace.json()["measurement_boundaries"]["pv"]
            == "common_AC_PV_after_curtailment"
        )
        assert trace.json()["rows"][0]["unit"]["after"]["pv_kwh"] > 0
        assert trace.json()["rows"][0]["unit"]["pv_dc_kw"] > 0
        response = client.post(
            "/runs/report",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": project.revision,
                "key": "dc-plant-report",
                "options": {
                    "locale": "de",
                    "energy_run_id": run.id,
                    "pv_run_id": None,
                    "equipment_run_id": None,
                    "logo": None,
                },
            },
            headers=headers(owner),
        )
        assert response.status_code == 200, response.text
        assert executor.run_once()
        report = workspace.run(owner, response.json()["id"])
        assert report.state == "succeeded", report.error
        from linker_engine.planning.energy_comparison import comparison_side

        side = comparison_side(workspace, owner, project.id, run.id)
        assert side.joint and set(json_object(side.inventory_key())) == {"a", "b"}
        capture = os.environ.get("PLANNER_DC_CLIENT_FIXTURE")
        if capture:
            Path(capture).write_bytes(
                encode(
                    {
                        "project": json_object(project_view(project)),
                        "run": json_object(run_view(run)),
                        "trace": trace.json(),
                        "report": json_object(run_view(report)),
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


def test_duplicate_roof_ac_rejects_geometric_and_abnormal_inputs() -> None:
    from types import SimpleNamespace

    from linker_engine.planning.errors import EvidenceMissing
    from linker_engine.planning.plant_energy_kernel import check_plant_profile_boundary

    reference = {"pv_reference_asset_id": "a" * 32}
    geometric = "geometric_pv_reference_profile_v1"

    def rejected(scenario: object, role: str, metadata: object) -> None:
        with pytest.raises(EvidenceMissing, match="plant_dc_duplicate_pv_source"):
            check_plant_profile_boundary(scenario, role, metadata)

    rejected(reference, "pv_available_ac", {"profile_type": geometric})
    rejected(reference, "pv_available_ac", {"purpose": geometric})
    rejected(reference, "other", {"purpose": f"  {geometric}  "})
    rejected(reference, "pv_available_ac", {"profile_type": [geometric]})
    rejected(
        reference,
        "pv_available_ac",
        {"metadata": {"purpose": geometric}},
    )
    rejected(reference, "pv_available_ac", None)
    rejected(reference, "pv_available_ac", ["not", "a", "mapping"])
    rejected(
        SimpleNamespace(pv_reference_asset_id="b" * 32),
        "pv_available_ac",
        {"profile_type": geometric},
    )
    rejected(reference, "pv_available_ac", {})
    rejected(reference, "pv_available_ac", {"profile_type": "unknown_profile"})
    # The retained DC reference may itself be a pvlib roof profile.
    check_plant_profile_boundary(
        reference,
        "pv_reference",
        {"profile_type": "pvlib_reference_profile_v1"},
    )
    check_plant_profile_boundary(
        reference,
        "pv_available_ac",
        {"profile_type": "pvgis_system_profile_v1"},
    )
    check_plant_profile_boundary(
        reference,
        "pv_available_ac",
        {"csv_mapping": {"measurement": "pv_available_ac"}},
    )
    check_plant_profile_boundary(
        {"pv_reference_asset_id": None},
        "pv_available_ac",
        {"profile_type": geometric},
    )
    check_plant_profile_boundary(
        {},
        "pv_available_ac",
        {"profile_type": geometric},
    )
