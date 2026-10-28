"""Planning figures keep their owned revision, scope and existing fact hydration."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from linker_genie import planning
from linker_genie.facts import Fact
from linker_genie.hydrate import fill, hydrate
from linker_genie.route import Route, Subject, with_page
from linker_genie.schema import (
    ActionBlock,
    PageContext,
    TextBlock,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import seal

PROJECT = "a" * 32
RUN = "b" * 32
URL = f"https://de-linker.test/solution-configurator/?project={PROJECT}&run={RUN}#lp-calculations"


def source() -> tuple[dict[str, Any], PageContext]:
    page = PageContext(
        planning_project_id=PROJECT, planning_revision=3, planning_run_ids=[RUN]
    )
    return {
        "schema_version": 1,
        "status": "available",
        "project": {
            "id": PROJECT,
            "title": "Owned project",
            "revision": 3,
            "current_revision": 4,
        },
        "rows": [{"label": "annual_load.kwh", "value": "6.000 kWh"}],
        "runs": [
            {
                "id": RUN,
                "revision": 2,
                "state": "succeeded",
                "kind": "single_ac_energy_replay_v1",
                "matches_view_revision": False,
                "is_current": False,
                "scope": {
                    "country_assessment": {"status": "not_assessed"},
                    "scenario_constraint_status": "violated",
                },
                "rows": [{"label": "solar_autarky", "value": "81,449 %"}],
                "details_available": True,
            }
        ],
        "workspace_url": URL,
        "truncated": False,
    }, page


def test_facts_hydrate_without_granting_product_or_document_permission() -> None:
    raw, page = source()
    raw["runs"][0].update(
        manifest_sha256="c" * 64,
        result_sha256="d" * 64,
        calculation_sources={
            "schema_version": 1,
            "groups": [
                {
                    "kind": "pv",
                    "role": "selected",
                    "input_quantity": "pv_available_ac",
                    "source_scope": "whole_reference",
                    "timezone": "Europe/Paris",
                    "radiation_database": "PVGIS-SARAH3",
                    "meteorological_database": "ERA5",
                    "weather_selection_period": {"start_year": 2014, "end_year": 2023},
                    "synthetic_calculation_year": 2023,
                    "periods_utc": [
                        {
                            "start_utc": "2023-01-01T00:00:00+00:00",
                            "end_utc": "2024-01-01T00:00:00+00:00",
                        }
                    ],
                },
                {
                    "kind": "energy",
                    "role": "selected",
                    "timezone": "Europe/Paris",
                    "periods_utc": [
                        {
                            "start_utc": "2023-06-16T09:00:00+00:00",
                            "end_utc": "2023-06-16T11:00:00+00:00",
                        }
                    ],
                },
            ],
        },
    )
    card = planning.source_card(raw, page)
    assert card is not None and card["results"][0]["revision"] == 2
    with pytest.raises(ValidationError):
        TurnOutput.model_validate({"language": "de", "blocks": [card]})
    assert (
        card["results"][0]["groups"][1]["periods_utc"][0]["start_utc"]
        == "2023-06-16T09:00:00+00:00"
    )
    assert planning.source_card({**raw, "status": "unsaved_changes"}, page) is None
    assert planning.source_card({**raw, "truncated": True}, page) is None
    assert (
        planning.source_card(
            raw, page.model_copy(update={"planning_project_id": "e" * 32})
        )
        is None
    )
    explanation: dict[str, Any] = {
        "blocks": [
            {"type": "text", "text": "Saved explanation"},
            {"type": "ask", "field": "backup", "options": ["needed", "none"]},
        ]
    }
    planning.add_source_card(
        explanation,
        raw,
        page,
        "Bitte erklären Sie mir die Ergebnisse dieses gespeicherten Projekts und des ausgewählten Berichts: Auf welchen Quellen und Zeiträumen beruhen PV-Erzeugung und Energiebilanz, wie sind die Kennzahlen zu verstehen, und welche Aussagen lassen sich daraus zur Geräteauswahl, Installation und zum Netzanschluss treffen?",
        "model",
    )
    assert [b["type"] for b in explanation["blocks"]] == ["text", "planning_sources"]
    sizing: dict[str, Any] = {
        "blocks": [{"type": "ask", "field": "backup", "options": ["needed", "none"]}]
    }
    planning.add_source_card(
        sizing, raw, page, "Explain the report and size a new battery", "model"
    )
    assert sizing["blocks"][0]["type"] == "ask"
    raw["runs"][0]["rows"].extend(
        [
            {
                "label": "Reference module",
                "value": {"model": "TSM-460NEG9R.28", "power": "460 W"},
            },
            {"label": "Plain reference power", "value": "460.0 W"},
        ]
    )
    payload, gathered = planning.record(raw, page)
    assert "not_assessed" in payload["text"] and "violated" in payload["text"]
    assert "matches_view_revision=False" in payload["text"]
    module_row = next(
        line.removeprefix("Reference module: ")
        for line in payload["text"].splitlines()
        if line.startswith("Reference module: ")
    )
    assert json.loads(module_row)["model"] == "TSM-460NEG9R.28"
    for value in ("460 W", "460.0 W"):
        power = next(key for key, item in payload["figures"].items() if item == value)
        assert fill("{fact:" + power + "}", gathered) == value
    figure = next(
        key for key, value in payload["figures"].items() if value == "81,449 %"
    )
    assert fill("Recorded: {fact:" + figure + "}", gathered) == "Recorded: 81,449 %"
    quoted = hydrate(
        TurnOutput(
            language="de",
            blocks=[
                TextBlock(text="Ergebnis: {fact:" + figure + "}", refs=["planning"])
            ],
        ),
        gathered,
    )
    sealed = seal(quoted, gathered, Route("model"), "Explain this project", "other")
    sealed_text = sealed.blocks[0]
    assert isinstance(sealed_text, TextBlock)
    assert "81,449 %" in sealed_text.text
    unrelated = quoted.model_copy(
        update={"blocks": [TextBlock(text="Ergebnis: 81,449 %", refs=[])]}
    )
    unrelated_text = seal(
        unrelated, gathered, Route("model"), "Explain this project", "other"
    ).blocks[0]
    assert isinstance(unrelated_text, TextBlock)
    assert "81,449" not in unrelated_text.text
    assert gathered.product_ids == set() and gathered.documents == {}
    gathered.add(
        Fact(
            id="size.configurator_url",
            value="https://de-linker.test/solution-configurator/",
            source="size",
        )
    )
    output = TurnOutput(language="en", blocks=[ActionBlock(name="open_configurator")])
    action = hydrate(output, gathered).blocks[0]
    assert isinstance(action, ActionBlock)
    assert action.args["url"] == URL
    request = TurnRequest(
        conversation_id="00000000-0000-4000-8000-000000000001",
        messages=[],
        page_context=page,
        planning_context=raw,
    )
    assert "planning_context" not in request.model_dump()


def test_unavailable_dirty_or_mismatched_context_never_reuses_figures() -> None:
    raw, page = source()
    for context, expected in (
        (None, "unavailable"),
        ({**raw, "status": "unsaved_changes"}, "unsaved_changes"),
        ({**raw, "project": {"id": "c" * 32, "revision": 3}}, "unavailable"),
        ({**raw, "runs": []}, "unavailable"),
    ):
        payload, gathered = planning.record(context, page)
        assert payload == {"error": expected}
        assert gathered.facts == {} and gathered.product_ids == set()


def test_active_project_sizing_reads_selected_history_instead_of_blank_tool() -> None:
    _, page = source()
    routed = with_page(
        Route("sizing"), page, False, True, Subject((), {}, {}), "Explain this project"
    )
    assert routed.name == "planning_project"
    assert [call.ability for call in routed.calls] == [planning.NAME]
    assert routed.no_cards
