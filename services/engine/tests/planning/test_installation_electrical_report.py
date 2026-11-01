"""Frozen report exposes numerical basis and the source behind each conductor."""

import io

import pytest
from pypdf import PdfReader

from linker_engine.models import Report
from linker_engine.pdf import render
from linker_engine.planning.canonical import Object
from linker_engine.planning.installation_report import installation_sections
from linker_engine.planning.installation_takeoff import route_takeoff

from .conftest import json_object
from .test_installation_electrical import circuit_fixture


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
