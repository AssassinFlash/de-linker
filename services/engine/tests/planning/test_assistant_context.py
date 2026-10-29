"""The assistant reads owned history; it does not execute or rewrite a design."""

from __future__ import annotations

from copy import deepcopy
from typing import cast

import pytest

from linker_engine.planning.assistant_context import assistant_context
from linker_engine.planning.canonical import Json, Object
from linker_engine.planning.errors import InvalidInput, NotFound
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.report_copy import text
from linker_engine.planning.report_model import build_report
from linker_engine.planning.report_pvlib import pvlib_sections
from linker_engine.planning.workspace import Workspace

from .test_pv_generation import parameter_document


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
