"""Frozen report exposes numerical basis and the source behind each conductor."""

import csv
import io
import json
from typing import Literal, cast

import pytest
from pypdf import PdfReader

from linker_engine.models import Report
from linker_engine.pdf import render
from linker_engine.planning.canonical import Object
from linker_engine.planning.grid_connection import country_assessment
from linker_engine.planning.grid_connection_report import grid_connection_sections
from linker_engine.planning.installation_report import installation_sections
from linker_engine.planning.installation_takeoff import route_takeoff
from linker_engine.planning.project_materials import materials_csv, project_materials
from linker_engine.planning.report_copy import text

from .conftest import json_object
from .test_grid_connection import declared
from .test_installation_electrical import circuit_fixture
from .test_installation_terminals import bind, sample


@pytest.mark.parametrize("locale", ["en", "de"])
def test_electrical_report_localizes_and_retains_declared_basis(locale: str) -> None:
    inputs, basis = circuit_fixture()
    inputs["installation"]["circuits"][0]["operating_conditions"][0][
        "voltage_limit"
    ] = {"maximum_percent": 1, "source_note": "Project designer requirement"}
    source: Object = {"installation": json_object(route_takeoff(inputs, basis))}
    sections = installation_sections(source, locale)
    summary = next(s for s in sections if s.id == "installation-electrical")
    assert summary.table is not None
    assert "5.088 / 0.848" in summary.table.rows[0]
    detail = next(s for s in sections if s.id.startswith("installation-electrical-"))
    rendered = " ".join(row.value for row in detail.rows)
    assert "Project designer requirement" in rendered
    assert "-5.088" in rendered
    assert "20 A / 600 V" in rendered
    assert "dc_20" in rendered
    assert sum(row.href is not None for row in detail.rows) == 2
    summary_text = " ".join(summary.table.rows[0])
    assert ("Berechnet" if locale == "de" else "Calculated") in summary_text
    assert "resistance_upper_bound" not in summary_text
    assert "within_declared_limit" not in rendered


def test_missing_cable_source_is_actionable_in_german_report() -> None:
    inputs, basis = circuit_fixture()
    basis["cable_references"] = []
    sections = installation_sections(
        {"installation": json_object(route_takeoff(inputs, basis))}, "de"
    )
    detail = next(s for s in sections if s.id.startswith("installation-electrical-"))
    assert "Die gewählte Kabelquelle ist nicht verfügbar." in detail.paragraphs
    assert all("cable_reference_unavailable" not in p for p in detail.paragraphs)
    assert not any(row.href for row in detail.rows)


def test_long_valid_condition_name_survives_pdf_page_boundary() -> None:
    inputs, basis = circuit_fixture()
    name = "Betriebsfall " * 310 + "Namensende"
    inputs["installation"]["circuits"][0]["operating_conditions"][0]["name"] = name
    sections = installation_sections(
        {"installation": json_object(route_takeoff(inputs, basis))}, "de"
    )
    data = render(
        Report(
            title="Test",
            subtitle="",
            generated_at="2026-11-01",
            locale="de",
            sections=sections,
        )
    )
    contents = " ".join(
        page.extract_text() for page in PdfReader(io.BytesIO(data)).pages
    )
    assert "Namensende" in contents
    assert "5.088" in contents


@pytest.mark.parametrize("locale", ["en", "de"])
def test_country_evidence_pdf_distinguishes_project_entries_from_permission(
    locale: str,
) -> None:
    assessment = country_assessment(declared(complete=True))
    sections = grid_connection_sections(assessment, locale)
    report = Report(
        title="Grid",
        subtitle="",
        generated_at="2026-11-01",
        locale=cast(Literal["en", "de"], locale),
        sections=sections,
    )
    contents = " ".join(
        page.extract_text() for page in PdfReader(io.BytesIO(render(report))).pages
    )
    assert text("grid_all_entered", locale) in contents
    assert text("grid_no_permission", locale) in contents
    assert "2023-09" in contents
    assert "2026-10-28" in contents
    unknown = grid_connection_sections(
        country_assessment(declared(country=None)), locale
    )
    assert text("grid_missing_country_code", locale) in unknown[1].rows[0].value
    assert "VDE-AR-N 4110" not in str(unknown)
    assert grid_connection_sections(country_assessment({}), locale) == []


@pytest.mark.parametrize("locale", ["en", "de"])
def test_saved_terminal_checks_reach_pdf_and_materials_csv(
    locale: Literal["en", "de"],
) -> None:
    inputs, basis = sample(1958)
    bind(inputs, basis, 0, "external-communication-terminal", "COM1")
    bind(inputs, basis, 1, "internal-communication-terminals", "COM2")
    inputs["installation"]["cable_runs"] = []
    source: Object = {
        "project_id": "project",
        "revision": 2,
        "input_sha256": "a" * 64,
        "installation": json_object(route_takeoff(inputs, basis)),
    }
    sections = installation_sections(source, locale)
    assert "installation-routing" not in {section.id for section in sections}
    section = next(s for s in sections if s.id == "installation-terminals")
    pdf = render(
        Report(
            title="Test",
            subtitle="",
            generated_at="2026-11-01",
            locale=locale,
            sections=[section],
        )
    )
    output = " ".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "COM1" in output and "COM2" in output
    assert ("weicht ab" if locale == "de" else "Declared use differs") in output
    assert ("S. 23" if locale == "de" else "p. 23") in output
    materials = project_materials(source)
    rows = csv.reader(
        io.StringIO(materials_csv(materials, "a" * 64, locale).decode("utf-8-sig"))
    )
    review = next(
        row for row in rows if row[3].startswith(("Terminal check", "Klemmenprüfung"))
    )
    assert review[2] == ""
    evidence = json.loads(review[6])["source"]
    assert evidence["qualified"] is False
    assert [e["use_status"] for e in evidence["circuit"]["endpoints"]] == [
        "matches",
        "mismatch",
    ]


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("status", ["product_unavailable", "product_revision_changed"])
def test_terminal_report_explains_stale_instances_without_replacing_saved_product(
    locale: str, status: str
) -> None:
    inputs, basis = sample()
    # The instance has no terminal binding; its identity can still go stale.
    if status == "product_unavailable":
        basis["products"] = []
    else:
        basis["products"][0]["product_revision"] = "f" * 64
        basis["products"][0]["brand"] = "NEW VERSION BRAND"
        basis["products"][0]["model"] = "NEW VERSION MODEL"
    takeoff = json_object(route_takeoff(inputs, basis))
    device = takeoff["instances"][0]
    assert device["product_status"] == status
    assert device["brand"] is None and device["model"] is None
    assert (
        takeoff["terminal_assessment"]["circuits"][0]["endpoints"][0]["status"]
        == "not_bound"
    )
    section = next(
        item
        for item in installation_sections({"installation": takeoff}, locale)
        if item.id == "installation-instances"
    )
    assert section.table is not None
    assert section.table.rows[0][1] == text(f"installation_{status}", locale)
    assert "None" not in str(section.table.rows)
    assert "NEW VERSION" not in str(section.table.rows)
    # Retained sources predating the new state remain presentable without a
    # guessed product identity or an invented reason for its absence.
    for item in takeoff["instances"]:
        item.pop("product_status", None)
    historical = installation_sections({"installation": takeoff}, locale)[0]
    assert historical.table is not None
    assert historical.table.rows[0][1] == text(
        "installation_product_details_unavailable", locale
    )


def test_current_legacy_installation_product_shape_and_label_are_unchanged() -> None:
    inputs, basis = sample()
    inputs["installation"]["circuits"][0].pop("communication_use")
    takeoff = json_object(route_takeoff(inputs, basis))
    device = takeoff["instances"][0]
    assert "product_status" not in device
    section = installation_sections({"installation": takeoff}, "en")[0]
    assert section.table is not None
    assert section.table.rows[0][1] == f"{device['brand']} {device['model']}"
