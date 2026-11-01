"""Recorded material declarations remain revision-bound and unqualified."""

from __future__ import annotations

import copy
import io
from typing import cast

import pytest
from pypdf import PdfReader

from linker_engine import pdf
from linker_engine.planning.assistant_context import _report_source_projection
from linker_engine.planning.canonical import Object
from linker_engine.planning.errors import InvalidInput, ProjectInputContractRequired
from linker_engine.planning.installation_inputs import InstallationInputs
from linker_engine.planning.installation_takeoff import route_takeoff
from linker_engine.planning.project_input_contracts import (
    MATERIALS_INPUT_CONTRACT,
    SUPPORTED_INPUT_CONTRACTS,
    require_input_contract,
)
from linker_engine.planning.project_materials import materials_csv, project_materials
from linker_engine.planning.report_model import build_report

from .conftest import FixtureObject, json_object
from .test_installation_electrical import circuit_fixture
from .test_installation_terminals import sample
from .test_project_materials import _source_data


def declared() -> list[dict[str, object]]:
    return [
        {
            "id": f"material-{index}",
            "name": f"Private item {index}",
            "kind": kind,
            "circuit_id": circuit,
            "quantity": quantity,
            "unit": unit,
            "specification": "Private specification",
            "source_note": "Private source note",
        }
        for index, (kind, circuit, quantity, unit) in enumerate(
            [
                ("connector", "circuit", 2, "piece"),
                ("protection", "removed-circuit", 1, "piece"),
                ("earthing", None, 10.5, "m"),
                ("mounting", None, None, "piece"),
            ],
            1,
        )
    ]


def test_complete_writer_protects_declarations_and_legacy_bytes() -> None:
    inputs, _ = circuit_fixture()
    legacy = copy.deepcopy(inputs)
    assert (
        "materials"
        not in InstallationInputs.read(legacy["installation"]).project_document()
    )
    inputs["installation"]["materials"] = declared()
    for writer in (None, *SUPPORTED_INPUT_CONTRACTS[:-1]):
        for before, after in ((legacy, inputs), (inputs, inputs), (inputs, legacy)):
            with pytest.raises(ProjectInputContractRequired):
                require_input_contract(before, after, writer)
    require_input_contract(legacy, inputs, MATERIALS_INPUT_CONTRACT)
    invalid = copy.deepcopy(inputs["installation"])
    invalid["materials"][0]["quantity"] = 1.5
    with pytest.raises(InvalidInput):
        InstallationInputs.read(invalid)


def test_materials_flow_to_reports_csv_and_private_projection() -> None:
    inputs, basis = circuit_fixture()
    inputs["installation"]["materials"] = declared()
    installation = json_object(route_takeoff(inputs, basis))
    review = installation["material_review"]
    assert review["qualified"] is False and review["complete_bos"] is False
    assert [r["circuit_status"] for r in review["rows"]] == [
        "linked",
        "circuit_unavailable",
        "not_linked",
        "not_linked",
    ]
    assert all(row["verification"] == "not_assessed" for row in review["rows"])
    source = _source_data()
    source.update(installation=installation, title="Installation fixture", locale="en")
    materials = project_materials(cast(Object, source))
    source["materials"] = materials
    lines = [
        row
        for row in cast(list[FixtureObject], materials["lines"])
        if row["id"].startswith("installation-material:")
    ]
    assert [row["quantity"] for row in lines] == [2, 1, 10.5, None]
    assert all(
        "sku" not in row and row["source"]["qualified"] is False for row in lines
    )
    for locale in ("en", "de"):
        source["locale"] = locale
        document = pdf.render(build_report(cast(Object, source)))
        rendered = " ".join(
            " ".join(p.extract_text().split())
            for p in PdfReader(io.BytesIO(document)).pages
        )
        csv_text = materials_csv(materials, "0" * 64, locale).decode("utf-8-sig")
        assert "Private item 1" in rendered and "Private specification" in rendered
        assert "Private item 1" in csv_text and "Private source note" in csv_text
        projected = str(_report_source_projection(cast(Object, source), locale))
        assert (
            "Private item" not in projected and "Private source note" not in projected
        )
        assert (
            "Private specification" not in projected
            and "removed-circuit" not in projected
        )


@pytest.mark.parametrize(
    ("kind", "circuit_kind", "fact_id", "values", "expected", "page"),
    [
        (
            "earthing",
            "protective_earth",
            "protective-earth-conductor",
            (25, None, None),
            "within_recommendation",
            153,
        ),
        (
            "earthing",
            "protective_earth",
            "protective-earth-conductor",
            (24, None, None),
            "outside_recommendation",
            153,
        ),
        (
            "protection",
            "ac",
            "ac-output-breaker",
            (None, 160, 400),
            "meets_minimum_values",
            152,
        ),
        (
            "protection",
            "ac",
            "ac-output-breaker",
            (None, 159, 400),
            "below_minimum_values",
            152,
        ),
    ],
)
def test_exact_instance_and_current_document_comparison(
    kind: str,
    circuit_kind: str,
    fact_id: str,
    values: tuple[int | None, int | None, int | None],
    expected: str,
    page: int,
) -> None:
    inputs, basis = sample(1946)
    plan = inputs["installation"]
    plan["circuits"][0]["kind"] = circuit_kind
    plan["circuits"][0].pop("communication_use")
    fact = next(
        x
        for x in basis["products"][0]["installation_facts"]["items"]
        if x["id"] == fact_id
    )
    item = declared()[0]
    item["kind"] = kind
    item["circuit_id"] = plan["circuits"][0]["id"]
    comparison: FixtureObject = {
        "instance_id": plan["instances"][0]["id"],
        "product_id": 1946,
        "product_revision": basis["products"][0]["product_revision"],
        "fact_id": fact_id,
        "document_id": fact["source"]["document_id"],
        "document_revision": fact["source"]["document_revision"],
        "cross_section_mm2": values[0],
        "rated_current_a": values[1],
        "rated_voltage_v": values[2],
        "conditions_confirmed": True,
        "circuit_context": {
            key: plan["circuits"][0][key] for key in ("id", "kind", "start", "end")
        },
    }
    item["comparison"] = comparison
    plan["materials"] = [item]
    compare = json_object(route_takeoff(inputs, basis))["material_review"]["rows"][0][
        "comparison_result"
    ]
    assert compare["status"] == expected and compare["qualified"] is False
    assert compare["fact"]["source"]["page"] == page
    comparison["conditions_confirmed"] = False
    assert (
        json_object(route_takeoff(inputs, basis))["material_review"]["rows"][0][
            "comparison_result"
        ]["status"]
        == "conditions_not_confirmed"
    )
    comparison["conditions_confirmed"] = True
    comparison["circuit_context"]["kind"] = "other"
    assert (
        json_object(route_takeoff(inputs, basis))["material_review"]["rows"][0][
            "comparison_result"
        ]["status"]
        == "conditions_changed"
    )
    comparison["circuit_context"]["kind"] = circuit_kind
    if expected == "within_recommendation":
        installation = json_object(route_takeoff(inputs, basis))
        source = _source_data()
        source.update(
            installation=installation, title="Comparison fixture", locale="en"
        )
        materials = project_materials(cast(Object, source))
        source["materials"] = materials
        report = build_report(cast(Object, source))
        section = next(
            section
            for section in report.sections
            if section.id == "installation-declared-materials"
        )
        assert "25 mm²" in section.rows[0].value and "p. 153" in section.rows[0].value
        pdf_text = " ".join(
            page.extract_text()
            for page in PdfReader(io.BytesIO(pdf.render(report))).pages
        )
        assert "25" in pdf_text and "153" in pdf_text
        csv_text = materials_csv(materials, "0" * 64, "en").decode("utf-8-sig")
        assert "within_recommendation" in csv_text and "document_revision" in csv_text
        for language, word in (("en", "within"), ("de", "Zahlenbereich")):
            projected = _report_source_projection(cast(Object, source), language)
            projected_section = next(
                section
                for section in build_report(projected).sections
                if section.id == "installation-declared-materials"
            )
            shown = projected_section.rows[0].value
            assert word in shown and "25 mm²" in shown and "p. 153" in shown
            assert projected_section.rows[0].href == fact["source"]["url"]
            assert "Private specification" not in str(projected)
            assert "Private source note" not in str(projected)
            assert "circuit_context" not in str(projected)
    comparison["document_revision"] = "a" * 64
    assert (
        json_object(route_takeoff(inputs, basis))["material_review"]["rows"][0][
            "comparison_result"
        ]["status"]
        == "document_unavailable"
    )
    comparison["document_revision"] = fact["source"]["document_revision"]
    comparison["instance_id"] = "missing"
    assert (
        json_object(route_takeoff(inputs, basis))["material_review"]["rows"][0][
            "comparison_result"
        ]["status"]
        == "circuit_or_instance_unavailable"
    )
