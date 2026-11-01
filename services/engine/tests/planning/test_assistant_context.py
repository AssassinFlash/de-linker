"""The assistant reads owned history; it does not execute or rewrite a design."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import cast

import pytest

from linker_engine.planning.assistant_context import (
    _installation_report_projection,
    _report_materials,
    _report_source_projection,
    assistant_context,
)
from linker_engine.planning.canonical import Json, Object
from linker_engine.planning.errors import InvalidInput, NotFound
from linker_engine.planning.grid_connection import country_assessment
from linker_engine.planning.installation_takeoff import route_takeoff
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.project_materials import project_materials
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.report_copy import text
from linker_engine.planning.report_model import build_report
from linker_engine.planning.report_pvlib import pvlib_sections
from linker_engine.planning.workspace import Workspace

from .test_grid_connection import declared
from .test_installation_electrical import circuit_fixture
from .test_pv_generation import parameter_document


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("historical", [False, True])
def test_controller_report_keeps_owner_group_name_out_of_assistant(
    workspace: Workspace, owner: Actor, context: Context, locale: str, historical: bool
) -> None:
    project = workspace.create(
        owner,
        "Controller review",
        {
            "equipment_plant": {
                "units": [
                    {"id": "a", "name": "PRIVATE UNIT"},
                    {"id": "b", "name": "PRIVATE SECOND"},
                ]
            }
        },
        key="new",
    )
    checks: list[Json] = [
        {
            "id": f"group:synthetic:{semantic}",
            "semantic_id": semantic,
            "group_name": "PRIVATE CUSTOMER GROUP",
            "status": "satisfied",
            "reason": reason,
            "actual": 2,
            "required": 10,
            "control_network": "lan",
            "facts": [],
        }
        for semantic, reason in (
            ("plant_controller_network_count", "controller_network_limit_comparison"),
            (
                "plant_parallel_count",
                "parallel_count_uses_applicable_manufacturer_limit",
            ),
        )
    ]
    source: Object = {
        "title": project.title,
        "project_id": project.id,
        "revision": 1,
        "input_sha256": project.input_sha256,
        "generated_at": "2026-11-01T00:00:00Z",
        "source_runs": [],
        "locale": locale,
        "equipment": {
            "overall_status": "unresolved",
            "selected_products": [],
            "provisional_bill_of_materials": [],
            "checks": checks,
            "systems": [
                {"id": "a", "name": "PRIVATE UNIT"},
                {"id": "b", "name": "PRIVATE SECOND"},
            ],
            "installation_requirements": [
                {
                    "kind": "meter",
                    "included": False,
                    "group_name": "PRIVATE CUSTOMER GROUP",
                    "conditions": [
                        {"en": "Synthetic scope.", "de": "Synthetischer Umfang."}
                    ],
                    "documents": [
                        {"url": "https://example.invalid/fixture.pdf", "page": 2}
                    ],
                }
            ],
        },
        "brief": {
            "site": {
                "location_label": "PRIVATE LOCATION",
                "country_code": "DE",
                "timezone": "Europe/Berlin",
            },
            "project_note": "PRIVATE NOTE",
        },
    }
    if not historical:
        grid_inputs = declared(complete=True)
        cast(Object, grid_inputs["grid_connection"])["dso_name"] = (
            "PRIVATE GRID DECLARATION"
        )
        cast(Object, source["equipment"])["country_assessment"] = country_assessment(
            grid_inputs
        )
    report = cast(Object, build_report(source).model_dump(mode="json"))
    assert ("PRIVATE GRID DECLARATION" in str(report)) is not historical
    assert "PRIVATE CUSTOMER GROUP" in str(report)
    cast(list[Json], report["sections"]).append(
        {
            "id": "pv-strings",
            "title": text("pv_strings_title", locale),
            "rows": [{"label": "PRIVATE UNIT · Ambient", "value": "-10 °C"}],
            "table": {
                "columns": [text("plant_unit", locale), "Count"],
                "rows": [["PRIVATE UNIT", "2"]],
            },
        }
    )
    cast(list[Json], report["sections"]).append(
        {
            "id": "energy-capacity-reference-0",
            "title": "PRIVATE UNIT · PRIVATE SECOND · Frozen capacity basis",
            "rows": [{"label": "Capacity", "value": "2 kWh"}],
        }
    )
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=1)
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(
        lease,
        {
            "kind": "planning_report_v1",
            "report": report,
            "dependencies": {}
            if historical
            else {"report_source": workspace.blobs.put_object(source)},
        },
    )
    shown = assistant_context(workspace, owner, project.id, 1, [run.id], locale)
    assert "PRIVATE" not in str(shown)
    rows = cast(list[Object], cast(list[Object], shown["runs"])[0]["rows"])
    if not historical:
        assert text("grid_no_permission", locale) in str(rows)
        assert "VDE-AR-N 4110:2023-09" in str(rows)

    table_row = next(
        row
        for row in rows
        if row["label"] == text("pv_strings_title", locale)
        and isinstance(row["value"], dict)
    )
    assert cast(Object, table_row["value"])["Count"] == "2"
    assert any(row["value"] == "-10 °C" for row in rows)
    stored = workspace.run(owner, run.id).result
    assert stored is not None and stored["report"] == report
    if not historical:
        translated = assistant_context(
            workspace, owner, project.id, 1, [run.id], "de" if locale == "en" else "en"
        )
        assert "PRIVATE" not in str(translated)


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("missing_source", [False, True])
@pytest.mark.parametrize("pinned_materials", [False, True])
def test_electrical_report_projects_frozen_numbers_without_private_project_text(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    monkeypatch: pytest.MonkeyPatch,
    locale: str,
    missing_source: bool,
    pinned_materials: bool,
) -> None:
    inputs, basis = circuit_fixture()
    plan = inputs["installation"]
    circuit = plan["circuits"][0]
    circuit["name"] = "PRIVATE CIRCUIT NAME"
    condition = circuit["operating_conditions"][0]
    condition.update(
        name="PRIVATE CONDITION NAME",
        source_note="PRIVATE CONDITION SOURCE",
        voltage_limit={"maximum_percent": 1, "source_note": "PRIVATE LIMIT SOURCE"},
    )
    for index, cable in enumerate(plan["cable_runs"]):
        cable["id"] = f"PRIVATE-RUN-{index}"
        cable["name"] = f"PRIVATE CABLE {index}"
        cable["conductor"]["source_note"] = "PRIVATE CONDUCTOR SOURCE"
    for route in plan["routes"]:
        route.update(name="PRIVATE ROUTE", extra_length_note="PRIVATE LENGTH NOTE")
    for instance in plan["instances"]:
        instance["name"] = "PRIVATE INSTANCE"
        for port in instance["ports"]:
            port["name"] = "PRIVATE PORT"
    # Native v2 reconciliation carries editable unit and inverter identities
    # into derived BOM scopes as well as the owner's string-link table.
    inputs["pv_plant_string_plan"] = {
        "schema_version": 1,
        "units": [
            {
                "unit_id": "PRIVATE_CUSTOMER_UNIT",
                "inverter_instance_id": "PRIVATE_CUSTOMER_INVERTER",
                "plan": {
                    "schema_version": 1,
                    "inverter_product_id": 9103,
                    "minimum_ambient_c": None,
                    "temperature_source": None,
                    "strings": [
                        {
                            "id": "PRIVATE_STRING",
                            "mppt": 1,
                            "input": 1,
                            "module_ids": ["PRIVATE_MODULE"],
                        }
                    ],
                },
            }
        ],
    }
    plan["pv_string_links"] = [
        {"string_id": "PRIVATE_STRING", "circuit_id": circuit["id"]}
    ]
    if missing_source:
        basis["cable_references"] = []
    project = workspace.create(owner, "Conductor scenario", {}, key="new")
    source: Object = {
        "title": project.title,
        "project_id": project.id,
        "revision": 1,
        "input_sha256": project.input_sha256,
        "generated_at": "2026-11-01T00:00:00Z",
        "source_runs": [],
        "locale": locale,
        "installation": route_takeoff(cast(Object, inputs), cast(Object, basis)),
        "unrelated_hourly_profile": [{"value": 123.4}],
        "equipment": {
            "overall_status": "unresolved",
            "selected_products": [],
            "provisional_bill_of_materials": [],
            "checks": [],
            "installation_requirements": [
                {
                    "included": True,
                    "kind": "meter",
                    "unit_name": "PRIVATE INCLUDED COMPONENT UNIT NAME",
                }
            ],
        },
    }
    if pinned_materials:
        source["materials"] = project_materials(source)
    recorded = cast(Object, build_report(source).model_dump(mode="json"))
    unrelated_section: Object = {
        "id": "unrelated-stored-history",
        "title": "Stored history",
        "rows": [{"label": "Preserved section", "value": "UNCHANGED STORED SECTION"}],
    }
    cast(list[Json], recorded["sections"]).append(unrelated_section)
    original_source, original_report = deepcopy(source), deepcopy(recorded)
    saved_installation = cast(Object, source["installation"])
    reconciliation = cast(Object, saved_installation["pv_string_reconciliation"])
    assert reconciliation["schema_version"] == 2
    safe_source = _report_source_projection(source, locale)
    assert safe_source["unrelated_hourly_profile"] is source["unrelated_hourly_profile"]
    same_language_report = _installation_report_projection(recorded, source, locale)
    assert cast(list[Object], same_language_report["sections"])[-1] is unrelated_section
    safe_installation = cast(Object, safe_source["installation"])
    safe_reconciliation = cast(Object, safe_installation["pv_string_reconciliation"])
    safe_link = cast(list[Object], safe_reconciliation["rows"])[0]
    assert safe_link["unit_id"] is not None
    assert safe_link["inverter_instance_id"] is not None
    assert source == original_source and recorded == original_report
    assert "PRIVATE CONDITION SOURCE" in str(recorded)
    assert "PRIVATE LIMIT SOURCE" in str(recorded)
    assert "PRIVATE-RUN-0" in str(source)
    assert "PRIVATE_CUSTOMER_UNIT" in str(recorded)
    assert "PRIVATE INCLUDED COMPONENT UNIT NAME" in str(recorded)
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=1)
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    source_sha = workspace.blobs.put_object(source)
    jobs.complete(
        lease,
        {
            "kind": "planning_report_v1",
            "report": recorded,
            "dependencies": {"report_source": source_sha},
        },
    )
    workspace.revise(owner, project.id, 1, {"later": True}, key="edit")
    with workspace.database.read() as connection:
        before = list(connection.iterdump())
    blobs = sorted(p.name for p in workspace.blobs.directory.rglob("*") if p.is_file())
    for requested in (locale, "de" if locale == "en" else "en"):
        with monkeypatch.context() as scoped:
            if requested == locale:

                def no_full_report_rebuild(source: Object) -> None:
                    raise AssertionError(
                        "same-language reads must reuse unrelated saved sections"
                    )

                scoped.setattr(
                    "linker_engine.planning.assistant_context.build_report",
                    no_full_report_rebuild,
                )
            projection = assistant_context(
                workspace, owner, project.id, 1, [run.id], requested
            )
        shown = str(projection)
        if requested == locale:
            assert "UNCHANGED STORED SECTION" in shown
        assert "PRIVATE" not in shown
        selected = cast(list[Object], projection["runs"])[0]
        assert selected["revision"] == 1 and selected["is_current"] is False
        assert selected["matches_view_revision"] is True
        assert "20 A / 600 V" in shown
        assert "1%" in shown
        assert "30 m" in shown and "4 mm²" in shown and "6 mm²" in shown
        if missing_source:
            assert "5.088" not in shown and "101.76" not in shown
            assert (
                "Die gewählte Kabelquelle ist nicht verfügbar."
                if requested == "de"
                else "The selected cable source is unavailable."
            ) in shown
        else:
            assert "5.088 / 0.848" in shown and "101.76" in shown
            assert "dc_20" in shown
            assert (
                "Maximaler Leiterwiderstand"
                if requested == "de"
                else "Maximum conductor resistance"
            ) in shown
            assert (
                "Innerhalb des erfassten Projektgrenzwerts"
                if requested == "de"
                else "Within recorded project limit"
            ) in shown
        assert ("Strombelastbarkeit" if requested == "de" else "ampacity") in shown
        assert text("installation_string_link_material_scope", requested) in shown
        assert (
            text("installation_string_link_inverter_endpoint_unresolved", requested)
            in shown
        )
        assert text("material_meter", requested) in shown
        assert projection["current_product_permission"] == "not_granted_by_this_context"
    assert workspace.blobs.object(source_sha) == original_source
    saved = workspace.run(owner, run.id).result
    assert saved is not None and saved["report"] == original_report
    with workspace.database.read() as connection:
        assert list(connection.iterdump()) == before
    assert (
        sorted(p.name for p in workspace.blobs.directory.rglob("*") if p.is_file())
        == blobs
    )


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("retained_source", [False, True])
def test_historical_installation_report_without_electrical_remains_readable(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    locale: str,
    retained_source: bool,
) -> None:
    inputs, basis = circuit_fixture()
    installation = route_takeoff(cast(Object, inputs), cast(Object, basis))
    installation.pop("electrical")
    cast(list[Object], installation["cables"])[0]["name"] = "PRIVATE CABLE NAME"
    project = workspace.create(owner, "Historical installation", {}, key="new")
    source: Object = {
        "title": project.title,
        "project_id": project.id,
        "revision": 1,
        "input_sha256": project.input_sha256,
        "generated_at": "2026-11-01T00:00:00Z",
        "source_runs": [],
        "locale": locale,
        "installation": installation,
    }
    report = cast(Object, build_report(source).model_dump(mode="json"))
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=1)
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(
        lease,
        {
            "kind": "planning_report_v1",
            "report": report,
            "dependencies": {"report_source": workspace.blobs.put_object(source)}
            if retained_source
            else {},
        },
    )
    projection = assistant_context(workspace, owner, project.id, 1, [run.id], locale)
    shown = str(projection)
    assert "PRIVATE" not in shown
    assert text("installation_scope", locale) in shown
    assert "5.088" not in shown and "20 A" not in shown
    assert "Conductor calculation" not in shown
    if retained_source:
        assert "30 m" in shown and "4 mm²" in shown
    saved = workspace.run(owner, run.id).result
    assert saved is not None and saved["report"] == report


def test_owned_snapshot_preserves_scope_revision_units_and_store(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    project = workspace.create(owner, "Recorded scenario", {}, key="new")
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=1)
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(
        lease,
        {
            "kind": "single_ac_energy_replay_v1",
            "metrics": {
                "load_kwh": 6000,
                "solar_autarky": {"value": 0.8144940056690679},
                "pv_input_self_use": {"value": None, "undefined_reason": "zero_pv"},
            },
            "country_assessment": {"status": "not_assessed"},
            "equipment_release": {"status": "not_assessed"},
            "scenario_constraint_status": "violated",
            "profile_interpretation": {
                "operating_periods": [
                    {
                        "profiles": {
                            "pv_available_ac": {
                                "source": {
                                    "details": {
                                        "parameters": {
                                            "source_note": "PRIVATE ENERGY REFERENCE NOTE"
                                        }
                                    }
                                }
                            }
                        }
                    }
                ]
            },
        },
    )
    workspace.revise(owner, project.id, 1, {"changed": True}, key="edit")
    with workspace.database.read() as connection:
        before = list(connection.iterdump())
    blobs = sorted(p.name for p in workspace.blobs.directory.rglob("*") if p.is_file())
    result = assistant_context(workspace, owner, project.id, 1, [run.id], "de")
    assert cast(Object, result["project"])["current_revision"] == 2
    selected = cast(list[Object], result["runs"])[0]
    assert selected["matches_view_revision"] is True and selected["is_current"] is False
    assert cast(Object, selected["scope"])["scenario_constraint_status"] == "violated"
    rows = {r["label"]: r for r in cast(list[Object], selected["rows"])}
    assert rows["load_kwh"]["value"] == "6.000 kWh"
    assert rows["solar_autarky"]["value"] == "81,449 %"
    assert rows["pv_input_self_use"]["value"] is None
    assert rows["pv_input_self_use"]["undefined_reason"] == "zero_pv"
    assert result["current_product_permission"] == "not_granted_by_this_context"
    assert "PRIVATE ENERGY REFERENCE NOTE" not in str(result)
    with workspace.database.read() as connection:
        assert list(connection.iterdump()) == before
    assert (
        sorted(p.name for p in workspace.blobs.directory.rglob("*") if p.is_file())
        == blobs
    )


def test_unavailable_owner_and_cross_project_result_are_refused(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    first = workspace.create(owner, "First", {}, key="first")
    second = workspace.create(owner, "Second", {}, key="second")
    run = workspace.evaluate(owner, second.id, 1, context, key="run", max_attempts=1)
    with pytest.raises(NotFound):
        assistant_context(workspace, Actor("guest", "another"), first.id, 1, [], "en")
    with pytest.raises(InvalidInput, match="different project"):
        assistant_context(workspace, owner, first.id, 1, [run.id], "en")


def test_unsaved_and_pending_views_do_not_supply_numbers(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    project = workspace.create(owner, "Not calculated", {}, key="new")
    assert assistant_context(workspace, owner, project.id, 1, [], "en")["runs"] == []
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=1)
    pending = assistant_context(workspace, owner, project.id, 1, [run.id], "en")
    selected = cast(list[Object], pending["runs"])[0]
    assert selected["state"] == "queued" and selected["rows"] == []
    unsaved = assistant_context(
        workspace, owner, project.id, 1, [run.id], "en", unsaved_changes=True
    )
    assert unsaved["status"] == "unsaved_changes"
    assert unsaved["runs"] == unsaved["rows"] == []


@pytest.mark.parametrize("locale", ["en", "de"])
def test_report_omits_comparison_location_and_private_note(
    workspace: Workspace, owner: Actor, context: Context, locale: str
) -> None:
    project = workspace.create(owner, "Private source", {}, key="new")
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=1)
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(
        lease,
        {
            "kind": "planning_report_v1",
            "report": {
                "locale": locale,
                "sections": [
                    {
                        "id": "comparison-baseline",
                        "title": "Baseline",
                        "paragraphs": ["PRIVATE NOTE"],
                        "rows": [
                            {
                                "label": text("location", locale),
                                "value": "PRIVATE PRECISE LOCATION",
                            },
                            {"label": text("country", locale), "value": "DE"},
                            {"label": "Recorded energy", "value": "6.000 kWh"},
                        ],
                    },
                    {
                        "id": "certificate-device-0",
                        "title": "Inverter · Selected model",
                        "rows": [
                            {
                                "label": text(
                                    "certificate_condition_source_note", locale
                                ),
                                "value": "PRIVATE DEVICE SOURCE NOTE",
                            },
                            {
                                "label": text(
                                    "certificate_condition_declared_firmware", locale
                                ),
                                "value": "010101",
                            },
                        ],
                    },
                    {
                        "id": "pvgis-roof-reference-0",
                        "title": "PVGIS reference",
                        "rows": [
                            {
                                "label": text("pvgis_reference_note", locale),
                                "value": "PRIVATE PVGIS ASSUMPTION",
                            },
                            {
                                "label": text("pvgis_calendar_year", locale),
                                "value": "2020",
                            },
                        ],
                    },
                    {
                        "id": "pvlib-reference-0",
                        "title": "Weather-based PV reference",
                        "rows": cast(
                            list[Json],
                            [
                                {"label": text(key, locale), "value": "PRIVATE SOURCE"}
                                for key in (
                                    "pvlib_note",
                                    "pvlib_original_request",
                                    "pvlib_array",
                                    "pvlib_converter",
                                    "pvlib_selected_dc_group",
                                )
                            ]
                            + [
                                {
                                    "label": text("pvlib_model", locale),
                                    "value": "pvlib 0.16.1",
                                },
                                {
                                    "label": text("pvlib_weather_period", locale),
                                    "value": "2014–2023",
                                },
                                {
                                    "label": text("pvlib_offset", locale),
                                    "value": "0.1805 h",
                                },
                                {
                                    "label": text("pvlib_dc_energy", locale),
                                    "value": "1.5 kWh",
                                },
                            ],
                        ),
                    },
                ],
            },
        },
    )
    result = assistant_context(workspace, owner, project.id, 1, [run.id], locale)
    assert "PRIVATE" not in str(result["runs"])
    assert "6.000 kWh" in str(result["runs"]) and "DE" in str(result["runs"])
    assert "010101" in str(result["runs"])
    assert "2020" in str(result["runs"])
    assert "pvlib 0.16.1" in str(result["runs"]) and "0.1805 h" in str(result["runs"])
    assert "1.5 kWh" in str(result["runs"])

    # A report stored in the other language is rebuilt from the same frozen
    # source. Comparison reference notes are still private after relocalizing.
    other_locale = "de" if locale == "en" else "en"
    source: Object = {
        "title": project.title,
        "project_id": project.id,
        "revision": 1,
        "input_sha256": project.input_sha256,
        "generated_at": "2026-10-28T00:00:00Z",
        "source_runs": [],
        "locale": other_locale,
        "brief": {
            "site": {
                "timezone": "Europe/Paris",
                "country_code": "FR",
                "location_label": "PRIVATE LOCATION",
            },
            "project_note": "PRIVATE PROJECT NOTE",
        },
        "energy": {
            "kind": "single_ac_energy_replay_v1",
            "interval_count": 2,
            "metrics": {
                "solar_autarky": {"value": None},
                "pv_input_self_use": {"value": None},
            },
        },
        "energy_scenario": {
            "schedule": [
                {"start_utc": "2023-06-16T09:00:00Z", "end_utc": "2023-06-16T11:00:00Z"}
            ]
        },
        "pvgis_roof_ac_references": [
            {
                "parameters": {
                    "year": 2020,
                    "radiation_database": "PVGIS-ERA5",
                    "pv_technology": "crystSi",
                    "mounting_place": "free",
                    "system_loss_percent": 14,
                    "use_terrain_horizon": True,
                    "source_note": "PRIVATE COMPARISON REFERENCE NOTE",
                },
                "profile_summary": {
                    "energy_kwh": 1,
                    "start_utc": "2020-01-01T00:00:00Z",
                    "end_utc": "2021-01-01T00:00:00Z",
                    "interval_count": 8784,
                },
                "used_by": [
                    {
                        "run_id": run.id,
                        "revision": 1,
                        "binding": "pv_available_ac",
                        "comparison_role": "baseline",
                    },
                ],
                "arrays": [],
                "pv_components": {"components": [], "nameplate_kwp": 0},
            }
        ],
        "pvlib_references": [
            {
                "converter_id": "PRIVATE SELECTED DC GROUP",
                "parameters": {
                    "model": "uniform_unshaded_pvlib_reference_v1",
                    "pvlib_version": "0.16.1",
                    "temporal_policy": "representative_pv_output_over_declared_intervals_v1",
                    "source_note": "PRIVATE PVLIB RELOCALIZED NOTE",
                    "modules": [],
                    "arrays": [],
                    "converters": [],
                },
                "profile_summary": {
                    "energy_kwh": 1.5,
                    "measurement": "pv_available_dc",
                    "interval_count": 8760,
                    "start_utc": "2023-01-01T00:00:00Z",
                    "end_utc": "2024-01-01T00:00:00Z",
                },
                "weather": {
                    "request": {
                        "start_year": 2014,
                        "end_year": 2023,
                        "use_terrain_horizon": False,
                    },
                    "capture": {
                        "requested_url": "https://re.jrc.ec.europa.eu/api/v5_3/tmy?lat=48.8566&lon=2.3522&startyear=2014&endyear=2023&usehorizon=0&outputformat=json",
                        "received_at_utc": "2026-10-28T00:00:00Z",
                    },
                    "interpretation": {"synthetic_energy_year": 2023},
                    "radiation_database": "PVGIS-SARAH3",
                    "meteo_database": "ERA5",
                    "irradiance_time_offset_hours": 0.1805,
                    "irradiance_offset_microseconds": 649800000,
                    "months_selected": [{"month": 1, "year": 2014}],
                    "solar_date_basis": "original_selected_year_plus_reported_irradiance_offset",
                    "native_radiation_semantics": "sarah_instantaneous",
                },
                "pv_components": {"nameplate_kwp": 9.2, "components": []},
                "used_by": [
                    {"run_id": run.id, "revision": 1, "binding": "pv_available_dc"},
                    {"run_id": run.id, "revision": 1, "binding": "legacy_quantity"},
                ],
                "arrays": [],
                "converters": [],
                "dependencies": {"pv_model_inputs": "a" * 64},
            }
        ],
    }
    # A whole pvlib reference may feed AC and a plant's retained DC binding.
    # Keep this distinct from the selected DC converter and the AC-only JRC source.
    pvlib = cast(list[Object], source["pvlib_references"])
    whole = deepcopy(pvlib[0])
    del whole["converter_id"]
    cast(Object, whole["profile_summary"])["measurement"] = "pv_available_ac"
    whole["used_by"] = [
        {"run_id": run.id, "revision": 1, "binding": "pv_available_ac"},
        {"run_id": run.id, "revision": 1, "binding": "pv_reference"},
    ]
    pvlib.append(whole)
    geometric_parameters = parameter_document()
    geometric_parameters["source_note"] = "PRIVATE GEOMETRIC REFERENCE NOTE"
    geometric_parameters["modules"][0]["gamma_pdc_per_c"] = -0.0029
    geometric_parameters["arrays"][0].update(
        array_id="PRIVATE GEOMETRIC ARRAY",
        albedo=0.3,
        beam_iam_b=0.05,
        sky_diffuse_iam_factor=0.95,
        ground_diffuse_iam_factor=0.9,
        spectral_factor=0.99,
        soiling_factor=0.72,
        dc_wiring_factor=0.88,
        dc_mismatch_factor=0.91,
        source_note="PRIVATE GEOMETRIC ARRAY NOTE: Near shading is not modelled.",
    )
    geometric_parameters["arrays"][0]["thermal"].update(
        a=-3.47, b=-0.0594, delta_t_c=3, source_note="PRIVATE GEOMETRIC THERMAL NOTE"
    )
    geometric_parameters["converters"][0].update(
        id="PRIVATE GEOMETRIC CONVERTER",
        array_ids=["PRIVATE GEOMETRIC ARRAY"],
        reference_dc_power_w=10416.666666666666,
        source_note="PRIVATE GEOMETRIC CONVERTER NOTE",
    )
    geometric_weather = deepcopy(cast(Object, whole["weather"]))
    geometric_request = cast(Object, geometric_weather["request"])
    geometric_request.update(
        expected_radiation_database="PVGIS-SARAH3", expected_meteo_database="ERA5"
    )
    source["geometric_pv_references"] = [
        {
            "model": "opaque_direct_uniform_pvlib_reference_v1",
            "parameters": {"parameters": geometric_parameters},
            "profile_summary": deepcopy(whole["profile_summary"]),
            "weather_source": {"details": geometric_weather},
            "weather_metadata": {
                "weather_request": geometric_request,
                "weather_interpretation": geometric_weather["interpretation"],
            },
            "model_facts": {
                "sampling": {"coarse_cells_per_edge": 1, "fine_cells_per_edge": 2}
            },
            "arrays": [
                {
                    "id": "PRIVATE GEOMETRIC ARRAY",
                    "module_spec_id": "module",
                    "module_count": 2,
                    "stc_power_w": 1000,
                    "tilt_deg": 29.999999999999996,
                    "azimuth_north_clockwise_deg": 180,
                    "normal_enu": [0, -0.49999999999999994, 0.8660254037844386],
                    "mounting_note": "PRIVATE GEOMETRIC MOUNTING NOTE",
                    "lower_edge_clearance_m": 0.2,
                }
            ],
            "converters": [
                {
                    "id": "PRIVATE GEOMETRIC CONVERTER",
                    "model_ac_cap_w": 9999.999999999998,
                }
            ],
            "pv_components": {"nameplate_kwp": 1, "components": []},
            "used_by": [
                {"run_id": run.id, "revision": 1, "binding": "pv_available_ac"}
            ],
            "dependencies": {},
        }
    ]
    original_source = deepcopy(source)
    recorded = build_report(source).model_dump(mode="json")
    assert source == original_source
    assert "PRIVATE COMPARISON REFERENCE NOTE" in str(recorded)
    geometric_section = next(
        section
        for section in cast(list[Object], recorded["sections"])
        if section["id"] == "geometric-pv-reference-0"
    )
    assert "PRIVATE GEOMETRIC" in str(geometric_section)
    assert "opaque_direct_uniform_pvlib_reference_v1" in str(geometric_section)
    assert "uniform_unshaded_pvlib_reference_v1" not in str(geometric_section)
    assert "Near shading is not modelled." in str(geometric_section)
    assert text("geometric_pv_notes_scope", other_locale) in str(geometric_section)
    assert text("geometric_pv_original_note", other_locale) in str(geometric_section)
    for en, de in (
        ("isotropic / 0.3", "isotropic / 0,3"),
        ("ashrae / 0.05 / 0.95 / 0.9", "ashrae / 0,05 / 0,95 / 0,9"),
        ("0.99 / 0.72 / 0.88 / 0.91", "0,99 / 0,72 / 0,88 / 0,91"),
        (
            "a=-3.47; b=-0.0594 s/m; delta T=3 °C",
            "a=-3,47; b=-0,0594 s/m; delta T=3 °C",
        ),
        # Every section groups and marks its numbers the same way, so the
        # converter power reads identically wherever it appears.
        ("10,416.667 W / 10,000 W", "10.416,667 W / 10.000 W"),
        ("0.96 / 0.9637", "0,96 / 0,9637"),
        ("-0.0029 / °C", "-0,0029 / °C"),
        ("30° / 180° / [0; -0.5; 0.866025]", "30° / 180° / [0; -0,5; 0,866025]"),
        ("1: 2014", "1: 2014"),
        ("649,800,000 µs", "649.800.000 µs"),
    ):
        assert (de if other_locale == "de" else en) in str(geometric_section)
    # A report saved when this reference still called its period `summary` must
    # render in both languages from that saved object. The new name is not
    # required, and no electrical scope is invented for a bundle that has none.
    geometric_reference = cast(list[Object], source["geometric_pv_references"])[0]
    historical_reference = deepcopy(geometric_reference)
    historical_reference["summary"] = historical_reference.pop("profile_summary")
    for report_locale in ("en", "de"):
        historical_report = build_report(
            {
                **source,
                "locale": report_locale,
                "geometric_pv_references": [historical_reference],
            }
        )
        historical_section = next(
            section
            for section in historical_report.sections
            if section.id == "geometric-pv-reference-0"
        )
        assert any(
            row.label == text("geometric_pv_energy", report_locale)
            and row.value == ("1.5 kWh" if report_locale == "en" else "1,5 kWh")
            for row in historical_section.rows
        )
        assert any(
            row.label == text("geometric_pv_original_note", report_locale)
            for row in historical_section.rows
        )
        shown = str(historical_section.model_dump())
        assert "independent_per_module" not in shown
        assert "applied_per_module" not in shown
        assert "unit_required_not_applied" not in shown
    assert "profile_summary" not in historical_reference
    # One report, one display convention: the same unshaded reference rendered
    # through the plain saved shape now rounds its numbers the same way, so no
    # binary float repr reaches a reader from either section.
    legacy_projection: Object = {
        "parameters": geometric_parameters,
        "weather": geometric_weather,
        "profile_summary": geometric_reference["profile_summary"],
        **{
            key: geometric_reference[key]
            for key in (
                "pv_components",
                "arrays",
                "converters",
                "used_by",
                "dependencies",
            )
        },
    }
    legacy_rows = pvlib_sections({"pvlib_references": [legacy_projection]}, locale)[
        0
    ].rows
    legacy_shown = str(legacy_rows)
    assert "29.999999999999996°" not in legacy_shown
    assert "10416.666666666666 W" not in legacy_shown
    assert "30°" in legacy_shown
    assert ("10,416.667 W" if locale == "en" else "10.416,667 W") in legacy_shown
    # A reference saved before component identities were retained has no
    # `pv_components` key at all. It still renders its own rows, and no
    # capacity claim is invented for it from a layout that is not in the bundle.
    without_components = {
        key: value for key, value in legacy_projection.items() if key != "pv_components"
    }
    historical_rows = pvlib_sections(
        {"pvlib_references": [without_components]}, locale
    )[0].rows
    assert all(
        row.label != text("pv_components_capacity", locale) for row in historical_rows
    )
    assert any(row.label == text("pvlib_array", locale) for row in historical_rows)
    localized = workspace.evaluate(
        owner, project.id, 1, context, key="localized-report", max_attempts=1
    )
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(
        lease,
        {
            "kind": "planning_report_v1",
            "report": cast(Object, recorded),
            "dependencies": {"report_source": workspace.blobs.put_object(source)},
        },
    )
    for requested_locale in (locale, other_locale):
        projection = assistant_context(
            workspace, owner, project.id, 1, [localized.id], requested_locale
        )
        assert "PRIVATE" not in str(projection)
        assert "PVGIS-ERA5" in str(projection) and "2020" in str(projection)
        assert "48.8566" not in str(projection) and "https://re.jrc" not in str(
            projection
        )
        assert "pvlib 0.16.1" in str(projection)
        # The context reads the report rows, so it inherits that report's own
        # decimal mark instead of announcing the value in English digits.
        assert ("0.1805" if requested_locale == "en" else "0,1805") in str(projection)
        assert ("1.5 kWh" if requested_locale == "en" else "1,5 kWh") in str(projection)
        assert "opaque_direct_uniform_pvlib_reference_v1" in str(projection)
        for en, de in (
            ("0.99 / 0.72 / 0.88 / 0.91", "0,99 / 0,72 / 0,88 / 0,91"),
            (
                "a=-3.47; b=-0.0594 s/m; delta T=3 °C",
                "a=-3,47; b=-0,0594 s/m; delta T=3 °C",
            ),
            ("10,416.667 W / 10,000 W", "10.416,667 W / 10.000 W"),
            ("-0.0029 / °C", "-0,0029 / °C"),
        ):
            assert (de if requested_locale == "de" else en) in str(projection)
        assert "1: 2014" in str(projection)
        assert (
            "649,800,000 µs" if requested_locale == "en" else "649.800.000 µs"
        ) in str(projection)
        assert "Near shading is not modelled." not in str(projection)
        assert "29.999999999999996" not in str(projection)
        sources = cast(
            Object, cast(list[Object], projection["runs"])[0]["calculation_sources"]
        )
        groups = cast(list[Object], sources["groups"])
        assert len(groups) == 7
        annual = next(
            group for group in groups if group.get("radiation_database") == "PVGIS-ERA5"
        )
        tmy = next(
            group
            for group in groups
            if group.get("source_scope") == "selected_dc_group"
            and group.get("input_quantity") == "pv_available_dc"
        )
        energy = next(group for group in groups if group["kind"] == "energy")
        assert annual["periods_utc"] == [
            {
                "start_utc": "2020-01-01T00:00:00+00:00",
                "end_utc": "2021-01-01T00:00:00+00:00",
            }
        ]
        assert "synthetic_calculation_year" not in annual
        assert "weather_selection_period" not in annual
        assert annual["input_quantity"] == "pv_available_ac"
        assert annual["source_scope"] == "whole_reference"
        assert {
            group.get("input_quantity")
            for group in groups
            if group.get("source_scope") == "whole_reference"
            and group["role"] == "selected"
        } == {"pv_available_ac", "pv_available_dc"}
        assert tmy["weather_selection_period"] == {
            "start_year": 2014,
            "end_year": 2023,
        }
        assert tmy["synthetic_calculation_year"] == 2023
        assert tmy["input_quantity"] == "pv_available_dc"
        assert tmy["source_scope"] == "selected_dc_group"
        assert any(
            group.get("source_scope") == "selected_dc_group"
            and group.get("input_quantity") is None
            for group in groups
        )
        assert tmy["timezone"] == "Europe/Paris"
        assert tmy["periods_utc"] == [
            {
                "start_utc": "2023-01-01T00:00:00+00:00",
                "end_utc": "2024-01-01T00:00:00+00:00",
            }
        ]
        assert energy["periods_utc"] == [
            {
                "start_utc": "2023-06-16T09:00:00+00:00",
                "end_utc": "2023-06-16T11:00:00+00:00",
            }
        ]


def test_report_exposes_verified_materials_provenance(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    project = workspace.create(owner, "Materials provenance", {}, key="materials")
    materials: Object = {
        "schema_version": 3,
        "kind": "project_materials_v3",
        "project_id": project.id,
        "revision": 1,
        "input_sha256": project.input_sha256,
        "lines": [
            {
                "id": "product:0:1946",
                "handling": "woo_product",
                "quantity": 1,
            },
            {
                "id": "installation:0:ac-conductor",
                "handling": "customer_supplied_required",
                "quantity": None,
            },
            {
                "id": "installation:1:meter",
                "handling": "manufacturer_included",
                "quantity": 2,
            },
        ],
        "installation_status": "not_assessed",
        "equipment_status": "unresolved",
    }
    materials_sha = workspace.blobs.put_object(materials)
    source: Object = {
        "project_id": project.id,
        "revision": 1,
        "input_sha256": project.input_sha256,
        "materials": materials,
        "dependencies": {"materials_model": materials_sha},
    }
    source_sha = workspace.blobs.put_object(source)
    report_context = Context(
        context.code_sha256,
        {**context.models, "materials": "project_materials_v3"},
        {**context.assets, "report.source": source_sha},
        context.parameters,
    )
    run = workspace.evaluate(
        owner, project.id, 1, report_context, key="materials-report", max_attempts=1
    )
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(
        lease,
        {
            "kind": "planning_report_v1",
            "report": {"locale": "en", "sections": []},
            "materials_sha256": materials_sha,
            "dependencies": {
                "report_source": source_sha,
                "materials_model": materials_sha,
            },
        },
    )

    projection = assistant_context(workspace, owner, project.id, 1, [run.id], "en")
    selected = cast(list[Object], projection["runs"])[0]
    assert selected["materials"] == {
        "status": "verified",
        "sha256": materials_sha,
        "model": "project_materials_v3",
        "line_count": 3,
        "unresolved_quantity_count": 1,
        "handling_counts": {
            "customer_supplied_required": 1,
            "manufacturer_included": 1,
            "woo_product": 1,
        },
        "scope": "provisional_not_complete_bos",
    }

    mismatch = workspace.evaluate(
        owner, project.id, 1, report_context, key="materials-mismatch", max_attempts=1
    )
    other_materials_sha = workspace.blobs.put_object({"different": "materials"})
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(
        lease,
        {
            "kind": "planning_report_v1",
            "report": {"locale": "en", "sections": []},
            "materials_sha256": materials_sha,
            "dependencies": {
                "report_source": source_sha,
                "materials_model": other_materials_sha,
            },
        },
    )
    with pytest.raises(InvalidInput, match="materials dependency differs"):
        assistant_context(workspace, owner, project.id, 1, [mismatch.id], "en")

    recorded = workspace.run(owner, run.id)
    assert recorded.result is not None

    def invalid_materials(
        changed: Object, *, dependency_sha: str | None = None
    ) -> None:
        changed_sha = workspace.blobs.put_object(changed)
        changed_source: Object = {
            **source,
            "materials": changed,
            "dependencies": {"materials_model": dependency_sha or changed_sha},
        }
        changed_source_sha = workspace.blobs.put_object(changed_source)
        changed_result: Object = {
            **cast(Object, recorded.result),
            "materials_sha256": changed_sha,
            "dependencies": {
                "report_source": changed_source_sha,
                "materials_model": changed_sha,
            },
        }
        with pytest.raises(InvalidInput):
            _report_materials(
                workspace,
                replace(
                    recorded,
                    result=changed_result,
                    manifest={
                        **recorded.manifest,
                        "context": {
                            **cast(Object, recorded.manifest["context"]),
                            "assets": {
                                **context.assets,
                                "report.source": changed_source_sha,
                            },
                        },
                    },
                ),
                changed_result,
            )

    invalid_materials(materials, dependency_sha=other_materials_sha)
    invalid_materials(
        {
            **materials,
            "schema_version": 999,
        }
    )
    invalid_materials(
        {
            **materials,
            "lines": [
                *cast(list[Object], materials["lines"]),
                {"id": "invalid", "handling": "approval_granted", "quantity": 1},
            ],
        }
    )


def _historical_period(start: str, end: str) -> Object:
    return {"summary": {"start_utc": start, "end_utc": end}}


def test_historical_summary_period_survives_assistant_readback(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    """A saved object that still calls its period `summary` keeps that period.

    The assistant reads the same frozen object the report renderer does. The
    old name is not a missing period, and the instants are normalized to UTC.
    """
    project = workspace.create(owner, "Historical summary", {}, key="historical")
    references = workspace.evaluate(
        owner, project.id, 1, context, key="historical-references", max_attempts=1
    )
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    reference_source: Object = {
        "project_id": project.id,
        "revision": 1,
        "input_sha256": project.input_sha256,
        "geometric_pv_references": [
            _historical_period("2020-01-01T01:00:00+01:00", "2021-01-01T01:00:00+01:00")
        ],
        "pvlib_references": [
            _historical_period("2023-01-01T00:00:00Z", "2024-01-01T00:00:00Z")
        ],
        "pvgis_roof_ac_references": [
            _historical_period("2019-06-01T22:00:00-02:00", "2020-06-01T22:00:00-02:00")
        ],
    }
    assert "profile_summary" not in str(reference_source)
    jobs.complete(
        lease,
        {
            "kind": "planning_report_v1",
            "report": {"locale": "en", "sections": []},
            "dependencies": {
                "report_source": workspace.blobs.put_object(reference_source)
            },
        },
    )
    projection = assistant_context(
        workspace, owner, project.id, 1, [references.id], "en"
    )
    groups = cast(
        list[Object],
        cast(Object, cast(list[Object], projection["runs"])[0]["calculation_sources"])[
            "groups"
        ],
    )
    periods = [group["periods_utc"] for group in groups]
    assert [None] not in periods
    assert [
        {
            "start_utc": "2020-01-01T00:00:00+00:00",
            "end_utc": "2021-01-01T00:00:00+00:00",
        }
    ] in periods
    assert [
        {
            "start_utc": "2023-01-01T00:00:00+00:00",
            "end_utc": "2024-01-01T00:00:00+00:00",
        }
    ] in periods
    assert [
        {
            "start_utc": "2019-06-02T00:00:00+00:00",
            "end_utc": "2020-06-02T00:00:00+00:00",
        }
    ] in periods
    legacy = workspace.evaluate(
        owner, project.id, 1, context, key="historical-pv", max_attempts=1
    )
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    legacy_source: Object = {
        "project_id": project.id,
        "revision": 1,
        "input_sha256": project.input_sha256,
        "pv": _historical_period(
            "2022-06-01T02:00:00+02:00", "2022-06-01T04:00:00+02:00"
        ),
    }
    assert "profile_summary" not in cast(Object, legacy_source["pv"])
    jobs.complete(
        lease,
        {
            "kind": "planning_report_v1",
            "report": {"locale": "en", "sections": []},
            "dependencies": {
                "report_source": workspace.blobs.put_object(legacy_source)
            },
        },
    )
    legacy_projection = assistant_context(
        workspace, owner, project.id, 1, [legacy.id], "en"
    )
    legacy_groups = cast(
        list[Object],
        cast(
            Object,
            cast(list[Object], legacy_projection["runs"])[0]["calculation_sources"],
        )["groups"],
    )
    assert legacy_groups[0]["periods_utc"] == [
        {
            "start_utc": "2022-06-01T00:00:00+00:00",
            "end_utc": "2022-06-01T02:00:00+00:00",
        }
    ]


def test_materials_source_must_match_the_selected_runs_frozen_source(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    """Same-revision, self-consistent source B cannot impersonate pinned A."""
    project = workspace.create(owner, "Pinned materials", {}, key="pinned-materials")

    def source(quantity: int) -> tuple[str, str]:
        materials: Object = {
            "schema_version": 3,
            "kind": "project_materials_v3",
            "installation_status": "not_assessed",
            "project_id": project.id,
            "revision": 1,
            "input_sha256": project.input_sha256,
            "lines": [
                {
                    "id": "product:fixture",
                    "handling": "woo_product",
                    "quantity": quantity,
                }
            ],
        }
        materials_sha = workspace.blobs.put_object(materials)
        source_sha = workspace.blobs.put_object(
            {
                "project_id": project.id,
                "revision": 1,
                "input_sha256": project.input_sha256,
                "materials": materials,
                "dependencies": {"materials_model": materials_sha},
            }
        )
        return source_sha, materials_sha

    source_a, _ = source(1)
    source_b, materials_b = source(7)
    run = workspace.evaluate(
        owner,
        project.id,
        1,
        Context(
            context.code_sha256,
            {**context.models, "materials": "project_materials_v3"},
            {**context.assets, "report.source": source_a},
            context.parameters,
        ),
        key="pinned-source-a",
        max_attempts=1,
    )
    forged: Object = {
        "kind": "planning_report_v1",
        "materials_sha256": materials_b,
        "dependencies": {"report_source": source_b, "materials_model": materials_b},
    }
    with pytest.raises(InvalidInput, match="frozen report source"):
        _report_materials(workspace, run, forged)
