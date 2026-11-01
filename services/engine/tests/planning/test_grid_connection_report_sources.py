"""The normal report pin path cannot re-label another revision's grid review."""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Literal, cast

import pytest

from linker_engine.planning.canonical import Object
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.equipment_assessment import assess_equipment
from linker_engine.planning.equipment_candidate_store import EquipmentCandidateStore
from linker_engine.planning.equipment_kernel import EquipmentKernel
from linker_engine.planning.equipment_search import candidate_record
from linker_engine.planning.equipment_search_kernel import EquipmentSearchKernel
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_input_contracts import (
    ENGINEERING_V10_INPUT_CONTRACT,
    GRID_CONNECTION_INPUT_CONTRACT,
)
from linker_engine.planning.records import Actor, Context, Project, Run
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_sources import ReportInputsChanged
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object
from .test_country_rules import rule_input
from .test_energy_kernel import TOLERANCE, create_scenario, worker
from .test_equipment import feed as feed
from .test_equipment import inputs
from .test_grid_connection import declared

type SourceKind = Literal["assessment", "search"]


def completed_equipment_source(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    feed: FixtureObject,
    values: Object,
    kind: SourceKind,
) -> tuple[Project, Run]:
    contract = (
        ENGINEERING_V10_INPUT_CONTRACT
        if "country_rule_inputs" in values
        else GRID_CONNECTION_INPUT_CONTRACT
    )
    project = workspace.create(
        owner,
        "Grid source binding",
        values,
        key="create",
        input_contract=contract,
    )
    proof = workspace.blobs.put_object(feed)
    context = replace(context, assets={**context.assets, "woo.equipment_inputs": proof})
    run = workspace.evaluate(owner, project.id, 1, context, key="check", max_attempts=1)
    assessment = assess_equipment(values, feed)
    if kind == "search":
        candidate = candidate_record(
            "selection",
            cast(Object, values["equipment_selection"]),
            assessment,
            EquipmentCandidateStore(workspace),
        )
        payload: Object = {
            "kind": EquipmentSearchKernel.kind,
            "search": {"candidates": [candidate]},
        }
    else:
        payload = {"kind": EquipmentKernel.kind, "assessment": assessment}
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(
        lease,
        {
            **payload,
            "pinned_assets": {key: sha for key, sha in context.assets.items()},
            "runtime_sha256": context.code_sha256,
        },
    )
    if kind == "search":
        project = workspace.revise(
            owner,
            project.id,
            project.revision,
            {
                **project.inputs,
                "equipment_candidate": {
                    "run_id": run.id,
                    "candidate_id": candidate["id"],
                    "assessment_sha256": candidate["assessment_sha256"],
                },
            },
            key="adopt",
            input_contract=contract,
        )
    return project, workspace.run(owner, run.id)


@pytest.mark.parametrize("kind", ["assessment", "search"])
@pytest.mark.parametrize("change", ["add", "change", "remove"])
def test_report_pin_rejects_changed_rule_inputs(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    feed: FixtureObject,
    monkeypatch: pytest.MonkeyPatch,
    kind: SourceKind,
    change: str,
) -> None:
    values = cast(Object, {**inputs(feed, 3), **declared(complete=True)})
    rules = rule_input("de_pv_installed", power_kw=30, de_before_control_test=True)
    if change != "add":
        values["country_rule_inputs"] = rules
    project, source = completed_equipment_source(
        workspace, owner, context, feed, values, kind
    )
    changed = copy.deepcopy(project.inputs)
    if change == "add":
        changed["country_rule_inputs"] = rules
    elif change == "remove":
        changed.pop("country_rule_inputs")
    else:
        cast(Object, changed["country_rule_inputs"])["power_kw"] = 10
    revised = workspace.revise(
        owner,
        project.id,
        project.revision,
        changed,
        key="edit-rules",
        input_contract=ENGINEERING_V10_INPUT_CONTRACT,
    )
    with pytest.raises(ReportInputsChanged):
        report_service(workspace, monkeypatch).evaluate(
            owner,
            revised.id,
            revised.revision,
            options(source, kind),
            key="report-rules",
        )


def report_service(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> ReportService:
    sources = ProductSources(lambda: pytest.fail("uses the retained Woo proof"))
    monkeypatch.setattr(sources, "confirm_basis", lambda *args, **kwargs: None)
    return ReportService(workspace, ReportKernel(workspace, sources), max_attempts=1)


def options(run: Run, kind: SourceKind) -> ReportOptions:
    return ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=None,
        equipment_run_id=run.id if kind == "assessment" else None,
        logo=None,
    )


@pytest.mark.parametrize("kind", ["assessment", "search"])
@pytest.mark.parametrize(
    "change", ["add", "change", "remove", "de_to_fr", "de_to_null"]
)
def test_report_pin_rejects_grid_or_country_changed_since_equipment_source(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    feed: FixtureObject,
    monkeypatch: pytest.MonkeyPatch,
    kind: SourceKind,
    change: str,
) -> None:
    values = cast(Object, {**inputs(feed, 3), **declared(complete=True)})
    if change == "add":
        values.pop("grid_connection")
    project, source = completed_equipment_source(
        workspace, owner, context, feed, values, kind
    )
    service = report_service(workspace, monkeypatch)
    original = service.evaluate(
        owner, project.id, project.revision, options(source, kind), key="report-old"
    )
    pinned = cast(Object, cast(Object, original.manifest["context"])["assets"])
    original_bytes = workspace.blobs.read(cast(str, pinned["report.source"]))
    changed = copy.deepcopy(project.inputs)
    if change == "add":
        changed["grid_connection"] = declared(complete=True)["grid_connection"]
    elif change == "remove":
        changed.pop("grid_connection")
    elif change == "change":
        cast(Object, changed["grid_connection"])["dso_name"] = "Another declared DSO"
    else:
        site = cast(Object, cast(Object, changed["brief"])["site"])
        site["country_code"] = "FR" if change == "de_to_fr" else None
    revised = workspace.revise(
        owner,
        project.id,
        project.revision,
        changed,
        key="edit-grid",
        input_contract=GRID_CONNECTION_INPUT_CONTRACT,
    )
    with pytest.raises(ReportInputsChanged):
        service.evaluate(
            owner, revised.id, revised.revision, options(source, kind), key="report-new"
        )
    assert workspace.blobs.read(cast(str, pinned["report.source"])) == original_bytes
    assert workspace.run(owner, original.id).manifest == original.manifest


@pytest.mark.parametrize("kind", ["assessment", "search"])
def test_unchanged_grid_allows_unrelated_revision_and_keeps_frozen_source(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    feed: FixtureObject,
    monkeypatch: pytest.MonkeyPatch,
    kind: SourceKind,
) -> None:
    values = cast(Object, {**inputs(feed, 3), **declared(complete=True)})
    project, source = completed_equipment_source(
        workspace, owner, context, feed, values, kind
    )
    changed = copy.deepcopy(project.inputs)
    cast(Object, changed["brief"])["project_note"] = "Unrelated saved note"
    revised = workspace.revise(
        owner,
        project.id,
        project.revision,
        changed,
        key="note",
        input_contract=GRID_CONNECTION_INPUT_CONTRACT,
    )
    run = report_service(workspace, monkeypatch).evaluate(
        owner, revised.id, revised.revision, options(source, kind), key="report"
    )
    pinned = cast(Object, cast(Object, run.manifest["context"])["assets"])
    saved = workspace.blobs.object(cast(str, pinned["report.source"]))
    assert saved["revision"] == revised.revision
    equipment = json_object(saved["equipment"])
    assert (
        json_object(equipment["country_assessment"])["project_facts"]
        == values["grid_connection"]
    )


def test_absent_new_contract_preserves_legacy_country_projection(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    feed: FixtureObject,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = cast(Object, {**inputs(feed, 3), **declared(complete=True)})
    values.pop("grid_connection")
    project, source = completed_equipment_source(
        workspace, owner, context, feed, values, "assessment"
    )
    changed = copy.deepcopy(project.inputs)
    cast(Object, cast(Object, changed["brief"])["site"])["country_code"] = "FR"
    revised = workspace.revise(owner, project.id, 1, changed, key="legacy-country")
    run = report_service(workspace, monkeypatch).evaluate(
        owner, revised.id, revised.revision, options(source, "assessment"), key="report"
    )
    pinned = cast(Object, cast(Object, run.manifest["context"])["assets"])
    saved = workspace.blobs.object(cast(str, pinned["report.source"]))
    assert json_object(json_object(saved["equipment"])["country_assessment"]) == {
        "country_code": "DE",
        "status": "unresolved",
        "reason": "versioned_country_rules_required",
    }


def test_energy_bound_equipment_fallback_cannot_relabel_grid_country(
    workspace: Workspace,
    owner: Actor,
    feed: FixtureObject,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = create_scenario(workspace, owner)
    values = cast(
        Object, {**scenario.inputs, **inputs(feed, 3), **declared(complete=True)}
    )
    project = workspace.revise(
        owner,
        scenario.id,
        scenario.revision,
        values,
        key="attach-grid-equipment",
        input_contract=GRID_CONNECTION_INPUT_CONTRACT,
    )
    sources = ProductSources(lambda: pytest.fail("uses the frozen source fixture"))
    monkeypatch.setattr(sources, "equipment_basis", lambda: feed)
    monkeypatch.setattr(sources, "confirm_basis", lambda *args, **kwargs: None)
    monkeypatch.setattr(sources, "check_profile", lambda *args, **kwargs: None)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=sources)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, project.revision, key="energy"
    )
    assert worker(workspace, kernel).run_once()
    completed = workspace.run(owner, run.id)
    assert completed.state == "succeeded", completed.error
    opts = ReportOptions(
        locale="en",
        energy_run_id=run.id,
        pv_run_id=None,
        equipment_run_id=None,
        logo=None,
    )
    service = report_service(workspace, monkeypatch)
    original = service.evaluate(
        owner, project.id, project.revision, opts, key="old-energy-report"
    )
    pinned = cast(Object, cast(Object, original.manifest["context"])["assets"])
    saved = workspace.blobs.object(cast(str, pinned["report.source"]))
    assert (
        json_object(json_object(saved["equipment"])["country_assessment"])[
            "country_code"
        ]
        == "DE"
    )
    changed = copy.deepcopy(project.inputs)
    cast(Object, cast(Object, changed["brief"])["site"])["country_code"] = "FR"
    revised = workspace.revise(
        owner,
        project.id,
        project.revision,
        changed,
        key="change-energy-country",
        input_contract=GRID_CONNECTION_INPUT_CONTRACT,
    )
    with pytest.raises(ReportInputsChanged):
        service.evaluate(
            owner, revised.id, revised.revision, opts, key="new-energy-report"
        )
