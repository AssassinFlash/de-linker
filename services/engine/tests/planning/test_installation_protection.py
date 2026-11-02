"""One project circuit: breaking, worst-case clearing and thermal evidence."""

from __future__ import annotations

import copy
import io
from typing import cast

import pytest
from pypdf import PdfReader

from linker_engine.planning.assets import Assets
from linker_engine.planning.assistant_context import assistant_context
from linker_engine.planning.errors import ProjectInputContractRequired
from linker_engine.planning.execution_registry import ExecutionRegistry
from linker_engine.planning.installation_inputs import InstallationInputs
from linker_engine.planning.installation_protection import protection_review
from linker_engine.planning.installation_takeoff import route_takeoff
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_input_contracts import (
    MOUNTING_QUANTITIES_INPUT_CONTRACT,
    PROTECTION_EVIDENCE_INPUT_CONTRACT,
    require_input_contract,
)
from linker_engine.planning.records import Actor
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object
from .test_installation_electrical import circuit_fixture


def fixture() -> tuple[FixtureObject, FixtureObject]:
    inputs, basis = circuit_fixture(ac=True)
    plan = inputs["installation"]
    plan["materials"] = [
        {
            "id": "breaker",
            "name": "Synthetic breaker",
            "kind": "protection",
            "circuit_id": "circuit",
            "quantity": 1,
            "unit": "piece",
            "specification": "Synthetic device and trip setting",
            "source_note": "Project device declaration",
        }
    ]
    plan["protection_assessments"] = [
        {
            "id": "case_1",
            "circuit_id": "circuit",
            "protection_material_id": "breaker",
            "operating_condition_id": "steady",
            "scenario": "Synthetic grid case",
            "fault_range": {
                "minimum_fault_a": 500,
                "maximum_fault_a": 6000,
                "source_note": "Project fault study",
            },
            "breaking": {
                "capacity_a": 10000,
                "rated_voltage_v": 230,
                "current_kind": "ac",
                "source_note": "Synthetic breaker data",
            },
            "disconnection": {
                "device_worst_case_clear_s": 0.2,
                "required_clear_s": 0.4,
                "device_source_note": "Synthetic worst-case trip curve",
                "limit_source_note": "Project selected time limit",
            },
            "thermal": [
                {
                    "run_id": "run_0",
                    "core_role": "line",
                    "maximum_let_through_a2s": 100000,
                    "coverage_min_fault_a": 500,
                    "coverage_max_fault_a": 6000,
                    "maximum_clear_s": 0.3,
                    "k_a_sqrt_s_per_mm2": 115,
                    "k_source_note": "Synthetic conductor thermal basis",
                    "let_through_source_note": "Synthetic range-bound let-through data",
                }
            ],
            "confirmed_context_sha256": None,
        }
    ]
    return inputs, basis


def result(inputs: FixtureObject, basis: FixtureObject) -> FixtureObject:
    return cast(
        FixtureObject,
        json_object(route_takeoff(inputs, basis))["protection_review"]["assessments"][
            0
        ],
    )


def confirmed() -> tuple[FixtureObject, FixtureObject]:
    inputs, basis = fixture()
    review = result(inputs, basis)
    assert review["confirmation_status"] == "confirmation_required"
    inputs["installation"]["protection_assessments"][0]["confirmed_context_sha256"] = (
        review["confirmation_context_sha256"]
    )
    return inputs, basis


def test_three_checks_and_physical_context_are_independent() -> None:
    inputs, basis = confirmed()
    item = result(inputs, basis)
    assert item["qualified"] is False
    assert item["breaking"]["measured"] == 6000 and item["breaking"]["maximum"] == 10000
    assert (
        item["disconnection"]["measured"] == 0.2
        and item["disconnection"]["maximum"] == 0.4
    )
    assert item["thermal"][0]["measured"] == 100000
    assert item["thermal"][0]["maximum"] == (115 * 4) ** 2
    assert all(
        item[key]["status"] == "within_declared_values"
        for key in ("breaking", "disconnection")
    )
    assert item["thermal"][0]["status"] == "within_declared_values"
    renamed = copy.deepcopy(inputs)
    renamed["installation"]["circuits"][0]["name"] = "Unrelated label"
    assert result(renamed, basis)["confirmation_status"] == "confirmed"
    changed = copy.deepcopy(inputs)
    changed["installation"]["cable_runs"][0]["conductor"]["cross_section_mm2"] = 6
    assert result(changed, basis)["confirmation_status"] == "context_changed"
    plan = InstallationInputs.read(inputs["installation"])
    stale = json_object(protection_review(plan, {"source"}))["assessments"][0]
    assert stale["confirmation_status"] == "context_unavailable"


def test_failed_values_and_mismatched_device_rating_remain_separate() -> None:
    inputs, basis = fixture()
    item = inputs["installation"]["protection_assessments"][0]
    item["breaking"]["capacity_a"] = 5999
    item["disconnection"]["device_worst_case_clear_s"] = 0.5
    item["thermal"][0]["maximum_let_through_a2s"] = 211601
    item["thermal"][0]["maximum_clear_s"] = 0.5
    item["confirmed_context_sha256"] = result(inputs, basis)[
        "confirmation_context_sha256"
    ]
    review = result(inputs, basis)
    assert review["breaking"]["status"] == "outside_declared_values"
    assert review["disconnection"]["status"] == "outside_declared_values"
    assert review["thermal"][0]["status"] == "outside_declared_values"
    item["breaking"]["rated_voltage_v"] = 400
    item["confirmed_context_sha256"] = None
    item["confirmed_context_sha256"] = result(inputs, basis)[
        "confirmation_context_sha256"
    ]
    review = result(inputs, basis)
    assert review["breaking"] == {
        "status": "not_assessed",
        "reason": "rating_conditions_differ",
    }
    assert review["disconnection"]["status"] == "outside_declared_values"


def test_zero_minimum_fault_is_saved_but_clearing_is_not_inferred() -> None:
    inputs, basis = fixture()
    item = inputs["installation"]["protection_assessments"][0]
    item["fault_range"]["minimum_fault_a"] = 0
    item["thermal"][0]["coverage_min_fault_a"] = 0
    item["confirmed_context_sha256"] = result(inputs, basis)[
        "confirmation_context_sha256"
    ]
    review = result(inputs, basis)
    assert review["disconnection"] == {
        "status": "not_assessed",
        "reason": "zero_minimum_fault_current",
    }
    assert review["breaking"]["status"] == "within_declared_values"


@pytest.mark.parametrize(
    "change, reason",
    [
        ("coverage", "fault_range_not_covered"),
        ("duration", "adiabatic_duration_exceeds_five_seconds"),
        ("time", "clearing_time_evidence_inconsistent"),
    ],
)
def test_thermal_limit_does_not_bypass_actual_evidence(
    change: str, reason: str
) -> None:
    inputs, basis = fixture()
    item = inputs["installation"]["protection_assessments"][0]
    if change == "coverage":
        item["thermal"][0]["coverage_max_fault_a"] = 5999
    if change == "duration":
        item["thermal"][0]["maximum_clear_s"] = 5.01
    if change == "time":
        item["thermal"][0]["maximum_clear_s"] = 0.1
    item["confirmed_context_sha256"] = result(inputs, basis)[
        "confirmation_context_sha256"
    ]
    thermal = result(inputs, basis)["thermal"][0]
    assert thermal["status"] == "not_assessed" and thermal["reason"] == reason


def test_old_writers_cannot_erase_evidence() -> None:
    inputs, _ = fixture()
    plain = copy.deepcopy(inputs)
    del plain["installation"]["protection_assessments"]
    for previous, incoming in ((plain, inputs), (inputs, inputs), (inputs, plain)):
        with pytest.raises(ProjectInputContractRequired):
            require_input_contract(
                previous, incoming, MOUNTING_QUANTITIES_INPUT_CONTRACT
            )
        require_input_contract(previous, incoming, PROTECTION_EVIDENCE_INPUT_CONTRACT)


def test_separate_protective_earth_is_checked_only_for_the_same_endpoints() -> None:
    inputs, basis = fixture()
    plan = inputs["installation"]
    for instance in plan["instances"]:
        port = copy.deepcopy(instance["ports"][0])
        port["id"] = "pe_terminal"
        instance["ports"].append(port)
    plan["circuits"].append(
        {
            "id": "earth",
            "name": "PE",
            "kind": "protective_earth",
            "start": {"instance_id": "source", "port_id": "pe_terminal"},
            "end": {"instance_id": "load", "port_id": "pe_terminal"},
        }
    )
    run = copy.deepcopy(plan["cable_runs"][0])
    run.update(id="pe_run", circuit_id="earth", core_roles=["pe"])
    plan["cable_runs"].append(run)
    thermal = copy.deepcopy(plan["protection_assessments"][0]["thermal"][0])
    thermal.update(run_id="pe_run", core_role="pe")
    plan["protection_assessments"][0]["thermal"].append(thermal)
    plan["protection_assessments"][0]["confirmed_context_sha256"] = result(
        inputs, basis
    )["confirmation_context_sha256"]
    review = result(inputs, basis)
    assert review["thermal"][1]["core_role"] == "pe"
    assert review["thermal"][1]["status"] == "within_declared_values"
    assert review["qualified"] is False
    other = copy.deepcopy(plan["instances"][1])
    other["id"] = "other"
    plan["instances"].append(other)
    plan["circuits"][1]["end"]["instance_id"] = "other"
    assert result(inputs, basis)["confirmation_status"] == "context_unavailable"


def test_worker_freezes_protection_in_report_pdf_csv_and_private_projection(
    workspace: Workspace, owner: Actor, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs, basis = confirmed()
    products = ProductSources(lambda: pytest.fail("unexpected live source"))
    monkeypatch.setattr(products, "equipment_basis", lambda **kwargs: basis)
    monkeypatch.setattr(products, "confirm_basis", lambda *args, **kwargs: None)
    kernel = ReportKernel(workspace, products)
    service = ReportService(workspace, kernel, max_attempts=1)
    registry = ExecutionRegistry(kernel)
    worker = Worker(
        Jobs(workspace),
        "protection-report",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    project = workspace.create(
        owner,
        "Synthetic protection project",
        inputs,
        key="protection-project",
        input_contract=PROTECTION_EVIDENCE_INPUT_CONTRACT,
    )
    options = ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=None,
        equipment_run_id=None,
        logo=None,
        include_installation=True,
    )
    run = service.evaluate(
        owner, project.id, project.revision, options, key="protection-report"
    )
    assert worker.run_once()
    completed = workspace.run(owner, run.id)
    assert completed.state == "succeeded", completed.error
    saved = json_object(completed.result)
    report = str(saved["report"])
    assert (
        "Breaking capacity" in report
        and "Thermal withstand" in report
        and "100,000" in report
    )
    pdf = Assets(workspace).content(owner, project.id, saved["prepared_asset"]["id"])
    pdf_text = " ".join(
        " ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(pdf)).pages
    )
    assert "Breaking capacity" in pdf_text and "Thermal withstand" in pdf_text
    csv_bytes = Assets(workspace).content(
        owner, project.id, saved["prepared_attachments"]["bill_of_materials_csv"]["id"]
    )
    assert "Synthetic breaker" in csv_bytes.decode(
        "utf-8-sig"
    ) and "Breaking capacity" in csv_bytes.decode("utf-8-sig")
    projection = assistant_context(
        workspace, owner, project.id, project.revision, [run.id], "en"
    )
    text = str(projection)
    assert "Breaking capacity" in text and "Thermal withstand" in text
    assert (
        "Synthetic breaker" not in text
        and "Project fault study" not in text
        and "Synthetic grid case" not in text
    )
    de_options = options.model_copy(update={"locale": "de"})
    de_run = service.evaluate(
        owner, project.id, project.revision, de_options, key="protection-report-de"
    )
    assert worker.run_once()
    de_completed = workspace.run(owner, de_run.id)
    assert de_completed.state == "succeeded", de_completed.error
    de_saved = json_object(de_completed.result)
    de_pdf = Assets(workspace).content(
        owner, project.id, de_saved["prepared_asset"]["id"]
    )
    de_text = " ".join(
        " ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(de_pdf)).pages
    )
    assert "Ausschaltvermögen" in de_text and "Thermische Beanspruchung" in de_text
    de_csv = Assets(workspace).content(
        owner,
        project.id,
        de_saved["prepared_attachments"]["bill_of_materials_csv"]["id"],
    )
    assert "Ausschaltvermögen" in de_csv.decode("utf-8-sig")
    de_projection = str(
        assistant_context(
            workspace, owner, project.id, project.revision, [de_run.id], "de"
        )
    )
    assert (
        "Ausschaltvermögen" in de_projection
        and "Project fault study" not in de_projection
    )
