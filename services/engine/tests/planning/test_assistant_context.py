"""The assistant reads owned history; it does not execute or rewrite a design."""

from __future__ import annotations

from typing import cast

import pytest

from linker_engine.planning.assistant_context import assistant_context
from linker_engine.planning.canonical import Object
from linker_engine.planning.errors import InvalidInput, NotFound
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.report_copy import text
from linker_engine.planning.workspace import Workspace


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
                ],
            },
        },
    )
    result = assistant_context(workspace, owner, project.id, 1, [run.id], locale)
    assert "PRIVATE" not in str(result["runs"])
    assert "6.000 kWh" in str(result["runs"]) and "DE" in str(result["runs"])
    assert "010101" in str(result["runs"])
