from dataclasses import replace
from typing import Any

import pytest

from linker_engine.planning.assistant_context import assistant_context
from linker_engine.planning.equipment_kernel import EquipmentKernel
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_input_contracts import SUPPORTED_INPUT_CONTRACTS
from linker_engine.planning.project_materials import project_materials
from linker_engine.planning.pvgis_known_inputs import MODEL
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_sources import report_sources
from linker_engine.planning.workspace import Workspace

from .conftest import json_object
from .test_certificate_evidence import condition_project, evidence
from .test_pv_generation import geometry


@pytest.mark.parametrize(
    ("count", "power", "active", "old_layout"),
    [
        (16, 430, True, False),
        (16, 430, True, True),
        (16, None, True, False),
        (None, 430, True, False),
        (None, None, True, False),
        (16, 430, False, False),
    ],
)
def test_saved_report_keeps_only_the_active_known_panel_declaration(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    monkeypatch: pytest.MonkeyPatch,
    count: int | None,
    power: int | None,
    active: bool,
    old_layout: bool,
) -> None:
    inputs = json_object(condition_project())
    inputs.pop("equipment_condition_inputs")
    if old_layout:
        inputs["geometry"] = geometry()
    inputs.update(
        known_panel_details={"count": count, "power_w": power, "system_kwp": 11},
        pvgis_reference_setup={
            "model": MODEL if active else "pvgis_5_3_roof_ac_reference_v1"
        },
    )
    project = workspace.create(
        owner,
        "Customer declaration",
        inputs,
        key="project",
        input_contract=SUPPORTED_INPUT_CONTRACTS[-1],
    )
    proof, assessment = evidence()
    assessment["provisional_bill_of_materials"] = []
    ctx = replace(
        context,
        assets={
            **context.assets,
            "woo.equipment_inputs": workspace.blobs.put_object(proof),
        },
    )
    jobs = Jobs(workspace)

    def completed(ctx: Context, result: dict[str, Any], key: str) -> str:
        run = workspace.evaluate(owner, project.id, 1, ctx, key=key, max_attempts=1)
        lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
        assert lease is not None
        jobs.complete(lease, result)
        return run.id

    equip = completed(
        ctx,
        {
            "kind": EquipmentKernel.kind,
            "assessment": assessment,
            "pinned_assets": ctx.assets,
            "runtime_sha256": ctx.code_sha256,
        },
        "equipment",
    )
    product = ProductSources(
        lambda: pytest.fail("a saved panel assumption has no Woo product")
    )
    monkeypatch.setattr(product, "confirm_bases", lambda *args, **kwargs: None)
    source = report_sources(
        workspace,
        product,
        owner,
        project,
        ReportOptions(
            locale="en",
            energy_run_id=None,
            pv_run_id=None,
            equipment_run_id=equip,
            logo=None,
        ),
    )
    materials = json_object(project_materials(source))
    declared = [
        line for line in materials["lines"] if line["handling"] == "pv_declared"
    ]
    assert not any(line["handling"] == "pv_reference" for line in materials["lines"])
    if not active or (count is None and power is None):
        assert declared == [] and "declared_pv_panels" not in source
        return
    assert source["declared_pv_panels"] == {"count": count, "stc_power_w": power}
    [line] = declared
    assert (
        line["quantity"] == count
        and line["stc_power_w"] == power
        and line["product_id"] is None
    )
    assert line["source"] == {"kind": "user_declared"}
    sha = workspace.blobs.put_object(materials)
    source["materials"] = materials
    json_object(source["dependencies"])["materials_model"] = sha
    source_sha = workspace.blobs.put_object(source)
    report_context = replace(
        context,
        assets={**context.assets, "report.source": source_sha},
        models={**context.models, "materials": "project_materials_v3"},
    )
    saved = completed(
        report_context,
        {
            "kind": "planning_report_v1",
            "report": {"locale": "en", "sections": []},
            "materials_sha256": sha,
            "dependencies": {"report_source": source_sha, "materials_model": sha},
        },
        "report",
    )
    [selected] = json_object(
        assistant_context(workspace, owner, project.id, 1, [saved], "en")
    )["runs"]
    assert selected["saved_roof_panel_count"] is None
    assert (
        selected["declared_panel_count"] == count
        and selected["declared_panel_stc_power_w"] == power
    )
