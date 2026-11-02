"""Recorded material declarations remain revision-bound and unqualified."""

from __future__ import annotations

import copy
import io
from dataclasses import replace
from typing import cast

import pytest
from pypdf import PdfReader

from linker_engine import pdf
from linker_engine.planning import installation_materials
from linker_engine.planning.assets import Assets
from linker_engine.planning.assistant_calculation_sources import calculation_sources
from linker_engine.planning.assistant_context import (
    _report_source_projection,
    assistant_context,
)
from linker_engine.planning.canonical import Object
from linker_engine.planning.errors import (
    InvalidInput,
    ProjectInputContractRequired,
    ReportSourceExportRequired,
)
from linker_engine.planning.execution_registry import ExecutionRegistry
from linker_engine.planning.geometry_documents import PanelArray
from linker_engine.planning.installation_inputs import InstallationInputs
from linker_engine.planning.installation_takeoff import route_takeoff
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_input_contracts import (
    MATERIALS_INPUT_CONTRACT,
    MOUNTING_QUANTITIES_INPUT_CONTRACT,
    SUPPORTED_INPUT_CONTRACTS,
    require_input_contract,
)
from linker_engine.planning.project_materials import materials_csv, project_materials
from linker_engine.planning.records import Actor
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_model import build_report
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object
from .test_geometry import fixture as roof_fixture
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


def test_declared_mounting_rule_uses_the_saved_array_and_reopens_after_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, basis = circuit_fixture()
    geometry = roof_fixture()
    # Six slots, one excluded: two separate row segments and three neighbours.
    inputs["geometry"] = geometry
    item = declared()[-1]
    item["mounting_quantity_basis"] = {
        "array": copy.deepcopy(geometry["arrays"][0]),
        "module": copy.deepcopy(geometry["module_specs"][0]),
        "roof": copy.deepcopy(geometry["roofs"][0]),
        "per_module": 0,
        "per_segment": 4,
        "per_adjacency": 2,
        "conditions_confirmed": True,
    }
    inputs["installation"]["materials"] = [item]
    for confirmation in (False, 1, None):
        invalid = copy.deepcopy(inputs["installation"])
        rule = invalid["materials"][0]["mounting_quantity_basis"]
        if confirmation is None:
            rule.pop("conditions_confirmed")
        else:
            rule["conditions_confirmed"] = confirmation
        with pytest.raises(InvalidInput):
            InstallationInputs.read(invalid)
    assert (
        InstallationInputs.read(inputs["installation"]).project_document()
        == inputs["installation"]
    )
    floor = SUPPORTED_INPUT_CONTRACTS.index(MOUNTING_QUANTITIES_INPUT_CONTRACT)
    for writer in (None, *SUPPORTED_INPUT_CONTRACTS[:floor]):
        with pytest.raises(ProjectInputContractRequired):
            require_input_contract(inputs, inputs, writer)
    for writer in SUPPORTED_INPUT_CONTRACTS[floor:]:
        require_input_contract(inputs, inputs, writer)
    installation = json_object(route_takeoff(inputs, basis))
    result = installation["material_review"]["rows"][0]["mounting_quantity_result"]
    assert result == {
        "status": "calculated",
        "quantity": 14,
        "modules": 5,
        "segments": 2,
        "adjacencies": 3,
        "per_module": 0,
        "per_segment": 4,
        "per_adjacency": 2,
    }
    renamed = copy.deepcopy(inputs)
    renamed["geometry"]["roofs"][0]["name"] = "Changed roof label"
    renamed["geometry"]["arrays"][0]["name"] = "Changed array label"
    renamed["geometry"]["arrays"][0]["mounting_note"] = "Changed note"
    renamed["geometry"]["module_specs"][0]["stc_power_w"] += 1
    renamed["geometry"]["module_specs"][0]["source"]["note"] = "Changed note"
    assert (
        json_object(route_takeoff(renamed, basis))["material_review"]["rows"][0][
            "mounting_quantity_result"
        ]
        == result
    )
    second = copy.deepcopy(item)
    second["id"] = "another-mounting-item"
    renamed["installation"]["materials"].append(second)
    count_calls = 0
    original_counts = installation_materials._array_counts

    def count_once(array: PanelArray) -> tuple[int, int]:
        nonlocal count_calls
        count_calls += 1
        return original_counts(array)

    with monkeypatch.context() as patch:
        patch.setattr(installation_materials, "_array_counts", count_once)
        reviewed = json_object(route_takeoff(renamed, basis))
    assert len(reviewed["material_review"]["rows"]) == 2 and count_calls == 1
    changed_module = copy.deepcopy(inputs)
    changed_module["geometry"]["module_specs"][0]["model"] = "Different module"
    assert (
        json_object(route_takeoff(changed_module, basis))["material_review"]["rows"][0][
            "mounting_quantity_result"
        ]["status"]
        == "layout_changed"
    )
    source = _source_data()
    source.update(installation=installation, title="Mounting fixture", locale="en")
    materials = project_materials(cast(Object, source))
    source["materials"] = materials
    line = next(
        row
        for row in cast(list[FixtureObject], materials["lines"])
        if row["id"].startswith("installation-material:")
    )
    assert line["quantity"] == 14 and line["source"]["qualified"] is False
    for locale in ("en", "de"):
        source["locale"] = locale
        csv_text = materials_csv(materials, "0" * 64, locale).decode("utf-8-sig")
        assert (
            "14" in csv_text
            and ("row segments" if locale == "en" else "Reihenabschnitte") in csv_text
        )
        rendered = " ".join(
            " ".join(p.extract_text().split())
            for p in PdfReader(
                io.BytesIO(pdf.render(build_report(cast(Object, source))))
            ).pages
        )
        assert (
            "14" in rendered
            and ("row segments" if locale == "en" else "Reihenabschnitte") in rendered
        )
        projection = _report_source_projection(cast(Object, source), locale)
        rows = json_object(projection)["installation"]["material_review"]["rows"]
        assert "mounting_quantity_basis" not in rows[0]
        assert rows[0]["mounting_quantity_result"]["quantity"] == 14
    inputs["geometry"]["arrays"][0]["excluded_slots"].append("0:1")
    stale = json_object(route_takeoff(inputs, basis))["material_review"]["rows"][0][
        "mounting_quantity_result"
    ]
    assert stale == {"status": "layout_changed", "quantity": None}
    source["installation"] = json_object(route_takeoff(inputs, basis))
    stale_lines = cast(
        list[FixtureObject], project_materials(cast(Object, source))["lines"]
    )
    stale_material = next(
        row for row in stale_lines if row["id"].startswith("installation-material:")
    )
    assert stale_material["quantity"] is None
    oversized = copy.deepcopy(inputs)
    oversized["geometry"]["arrays"][0]["rows"] = 10_000_000
    oversized["installation"]["materials"][0]["mounting_quantity_basis"]["array"] = (
        copy.deepcopy(oversized["geometry"]["arrays"][0])
    )
    with pytest.raises(InvalidInput):
        route_takeoff(oversized, basis)


def test_owned_mounting_rule_report_worker_and_export_permission(
    workspace: Workspace, owner: Actor, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs, basis = circuit_fixture()
    geometry = roof_fixture()
    inputs["geometry"] = geometry
    item = declared()[-1]
    item["name"] = "Synthetic project end clamp"
    item["mounting_quantity_basis"] = {
        "array": copy.deepcopy(geometry["arrays"][0]),
        "module": copy.deepcopy(geometry["module_specs"][0]),
        "roof": copy.deepcopy(geometry["roofs"][0]),
        "per_module": 0,
        "per_segment": 4,
        "per_adjacency": 0,
        "conditions_confirmed": True,
    }
    inputs["installation"]["materials"] = [item]
    products = ProductSources(lambda: pytest.fail("unexpected live source"))
    monkeypatch.setattr(products, "equipment_basis", lambda **kwargs: basis)
    monkeypatch.setattr(products, "confirm_basis", lambda *args, **kwargs: None)
    kernel = ReportKernel(workspace, products)
    service = ReportService(workspace, kernel, max_attempts=1)
    registry = ExecutionRegistry(kernel)
    worker = Worker(
        Jobs(workspace),
        "mounting-report",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    options = ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=None,
        equipment_run_id=None,
        logo=None,
        include_installation=True,
    )
    project = workspace.create(
        owner,
        "Synthetic mounting project",
        inputs,
        key="mounting-project",
        input_contract=MOUNTING_QUANTITIES_INPUT_CONTRACT,
    )
    run = service.evaluate(
        owner, project.id, project.revision, options, key="mounting-report"
    )
    assert worker.run_once()
    complete = workspace.run(owner, run.id)
    assert complete.state == "succeeded", complete.error
    result = json_object(complete.result)
    pdf_bytes = Assets(workspace).content(
        owner, project.id, result["prepared_asset"]["id"]
    )
    csv_bytes = Assets(workspace).content(
        owner, project.id, result["prepared_attachments"]["bill_of_materials_csv"]["id"]
    )
    pdf_text = " ".join(
        " ".join(page.extract_text().split())
        for page in PdfReader(io.BytesIO(pdf_bytes)).pages
    )
    assert (
        "Synthetic project end clamp" in pdf_text
        and "8 pieces" in pdf_text
        and "row segments" in pdf_text
    )
    assert "Synthetic project end clamp" in csv_bytes.decode(
        "utf-8-sig"
    ) and "row segments" in csv_bytes.decode("utf-8-sig")
    projection = assistant_context(
        workspace, owner, project.id, project.revision, [run.id], "en"
    )
    selected = json_object(projection)["runs"][0]
    assert selected["calculation_sources"] == {"schema_version": 1, "groups": []}
    assert "Synthetic project end clamp" not in str(selected["rows"])
    assert "Installation material 1" in str(selected["rows"])
    legacy_source = workspace.blobs.object(result["dependencies"]["report_source"])
    del legacy_source["energy"]
    legacy_sha = workspace.blobs.put_object(legacy_source)
    legacy_result = {**result, "dependencies": {"report_source": legacy_sha}}
    assert (
        calculation_sources(workspace, replace(complete, result=legacy_result)) is None
    )
    for permission in ("unknown", "prohibited"):
        denied = copy.deepcopy(inputs)
        denied["geometry"]["sources"][0]["permissions"]["export"] = permission
        unexportable = workspace.create(
            owner,
            "Synthetic restricted roof",
            denied,
            key=f"restricted-roof-{permission}",
            input_contract=MOUNTING_QUANTITIES_INPUT_CONTRACT,
        )
        with pytest.raises(ReportSourceExportRequired, match="mounting layout"):
            service.evaluate(
                owner,
                unexportable.id,
                unexportable.revision,
                options,
                key=f"restricted-report-{permission}",
            )


def test_complete_writer_protects_declarations_and_legacy_bytes() -> None:
    inputs, _ = circuit_fixture()
    legacy = copy.deepcopy(inputs)
    assert (
        "materials"
        not in InstallationInputs.read(legacy["installation"]).project_document()
    )
    inputs["installation"]["materials"] = declared()
    floor = SUPPORTED_INPUT_CONTRACTS.index(MATERIALS_INPUT_CONTRACT)
    for writer in (None, *SUPPORTED_INPUT_CONTRACTS[:floor]):
        for before, after in ((legacy, inputs), (inputs, inputs), (inputs, legacy)):
            with pytest.raises(ProjectInputContractRequired):
                require_input_contract(before, after, writer)
    for writer in SUPPORTED_INPUT_CONTRACTS[floor:]:
        for before, after in ((legacy, inputs), (inputs, inputs), (inputs, legacy)):
            require_input_contract(before, after, writer)
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
