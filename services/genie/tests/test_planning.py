"""Planning figures keep their owned revision, scope and existing fact hydration."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from linker_genie import planning
from linker_genie.facts import Fact
from linker_genie.hydrate import fill, hydrate
from linker_genie.jev import Reading
from linker_genie.route import Route, Subject, plan, with_page
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


def test_private_material_label_and_report_without_pv_sources_are_not_denied() -> None:
    raw, page = source()
    raw["runs"][0].update(
        kind="planning_report_v1",
        manifest_sha256="c" * 64,
        result_sha256="d" * 64,
        calculation_sources={"schema_version": 1, "groups": []},
        rows=[{"label": "Installation material 1", "value": "8 pieces"}],
    )
    payload = planning.view(raw, page)
    assert "anonymized" in payload["text"].lower()
    assert "absence" in payload["text"].lower()
    assert "anonymized" in planning.RULE.lower()
    shipped: dict[str, Any] = {"blocks": [{"type": "text", "text": "8 pieces"}]}
    planning.add_source_card(shipped, raw, page, "Explain this saved report", "model")
    assert [block["type"] for block in shipped["blocks"]] == ["text"]

    raw["runs"][0]["calculation_sources"] = None
    planning.add_source_card(shipped, raw, page, "Explain this saved report", "model")
    assert shipped["blocks"][-1] == {
        "type": "planning_sources",
        "schema_version": 1,
        "status": "unavailable",
    }
    raw["runs"][0]["calculation_sources"] = {"schema_version": 1, "groups": "invalid"}
    shipped = {"blocks": []}
    planning.add_source_card(shipped, raw, page, "Explain this saved report", "model")
    assert shipped["blocks"][-1]["status"] == "unavailable"


def test_saved_material_answers_use_frozen_anonymous_items_in_both_languages() -> None:
    raw, page = source()
    raw["runs"][0].update(
        kind="planning_report_v1",
        declared_installation_materials=[
            {
                "quantity": {"en": "8 pc", "de": "8 Stk."},
                "explanation": {
                    "en": "5 × 0 + 2 × 4 + 3 × 0 = 8 pieces",
                    "de": "5 × 0 + 2 × 4 + 3 × 0 = 8 Stück",
                },
            },
            {"quantity": {"en": "Open", "de": "Offen"}, "explanation": None},
        ],
    )
    answer = planning.material_answer(raw, page, "en")
    assert answer and "5 × 0 + 2 × 4 + 3 × 0 = 8 pieces" in answer
    assert "Installation material 2" in answer and "Open" in answer
    assert "cannot verify" in answer and "not assessed" in answer
    answer = planning.material_answer(raw, page, "de")
    assert answer and "5 × 0 + 2 × 4 + 3 × 0 = 8 Stück" in answer
    assert "nicht bestätigen" in answer and "nicht geprüft" in answer
    raw["runs"][0]["declared_installation_materials"][0]["private_name"] = (
        "Private name"
    )
    refused = planning.material_answer(raw, page, "en")
    assert (
        refused and "could not be verified" in refused and "Private name" not in refused
    )


def protection_display() -> dict[str, Any]:
    return {
        "en": {
            "scope": "This does not approve selectivity or earthing.",
            "rows": [
                {
                    "label": "Protection case 1 · Breaking capacity",
                    "value": "Outside the declared values · Maximum prospective fault current 6,000 A > device breaking capacity 5,000 A · 230 V AC",
                },
                {
                    "label": "Protection case 1 · Clearing time",
                    "value": "Within the declared values · Worst-case device clearing time 0.2 s ≤ required maximum clearing time 0.4 s · Minimum fault current 500 A",
                },
                {
                    "label": "Protection case 1 · Thermal withstand · Conductor 1 / line",
                    "value": "Not assessed · Let-through evidence does not cover the fault range",
                },
            ],
        },
        "de": {
            "scope": "Selektivität und Erdungssystem sind damit nicht freigegeben.",
            "rows": [
                {
                    "label": "Schutzfall 1 · Ausschaltvermögen",
                    "value": "Außerhalb der angegebenen Werte · Maximaler Fehlerstrom 6.000 A > Ausschaltvermögen des Schutzgeräts 5.000 A · 230 V AC",
                },
                {
                    "label": "Schutzfall 1 · Abschaltzeit",
                    "value": "Innerhalb der angegebenen Werte · Längste Abschaltzeit 0,2 s ≤ zulässige Abschaltzeit 0,4 s",
                },
                {
                    "label": "Schutzfall 1 · Thermische Beanspruchung · Leiter 1 / line",
                    "value": "Nicht geprüft · Der Durchlassenergienachweis deckt den Fehlerstrombereich nicht ab",
                },
            ],
        },
    }


def test_saved_protection_comparisons_explain_all_three_statuses() -> None:
    raw, page = source()
    raw["runs"][0].update(
        kind="planning_report_v1", protection_comparisons=protection_display()
    )
    answer = planning.protection_answer(raw, page, "en")
    assert "fault current 6,000 A > device breaking capacity 5,000 A" in answer
    assert "clearing time 0.2 s ≤ required maximum clearing time 0.4 s" in answer
    assert "Not assessed · Let-through evidence" in answer
    assert "revision 2" in answer and "does not approve" in answer
    assert "viewed project: revision 3" in answer
    assert "latest saved project: revision 4" in answer
    assert "do not automatically apply to equipment in another revision" in answer
    de = planning.protection_answer(raw, page, "de")
    assert (
        "6.000 A > Ausschaltvermögen des Schutzgeräts 5.000 A" in de and "0,2 s ≤" in de
    )
    assert "angezeigter Projektstand: Revision 3" in de
    assert "neuester gespeicherter Projektstand: Revision 4" in de
    raw["runs"][0]["revision"] = 3
    raw["project"]["current_revision"] = 3
    current = planning.protection_answer(raw, page, "en")
    assert "Saved report, revision 3:" in current
    assert "viewed project:" not in current and "latest saved project:" not in current
    raw["project"]["current_revision"] = 4
    assert "latest saved project: revision 4" in planning.protection_answer(
        raw, page, "en"
    )
    raw["runs"][0]["protection_comparisons"]["en"]["rows"][0]["private_name"] = (
        "Private name"
    )
    assert "could not be verified" in planning.protection_answer(raw, page, "en")


def test_real_protection_question_uses_service_route() -> None:
    from types import SimpleNamespace

    from linker_genie.app import _answer
    from linker_genie.understand import Understander

    raw, page = source()
    raw["runs"][0].update(
        kind="planning_report_v1", protection_comparisons=protection_display()
    )
    question = "In this report, which protection check is outside the declared values and why? What do the other two comparisons show?"
    request = TurnRequest.model_validate(
        {
            "conversation_id": "test",
            "messages": [{"role": "user", "content": question}],
            "locale": "en",
            "page_context": page.model_dump(),
        }
    ).model_copy(update={"planning_context": raw})

    class RecordedJev:
        def read(
            self, message: str, page: dict[str, Any], history: Any = ()
        ) -> Reading:
            assert message == question and page["saved_protection_report"] is True
            return Reading(
                intent="documents_specs",
                confidence=0.73,
                about_this_page=0.66,
                wants_person=0.03,
                needs_followup=0.82,
                seconds=0,
                cost=0,
                saved_protection_question=0.94,
            )

    prepared = Understander(None, RecordedJev()).prepare(request, None)  # type: ignore[arg-type]
    assert prepared.route.reasons == ("verified saved protection explanation",)
    result, _ = _answer(request, prepared, SimpleNamespace(), None, abilities=None)  # type: ignore[arg-type]
    assert result.attempts == 0 and prepared.log["saved_protection_answer"] is True
    block = result.output.blocks[0]
    assert (
        isinstance(block, TextBlock)
        and "6,000 A > device breaking capacity 5,000 A" in block.text
    )
    assert "Not assessed" in block.text

    class OtherJev:
        def read(
            self, message: str, page: dict[str, Any], history: Any = ()
        ) -> Reading:
            return Reading(
                intent="find_products",
                confidence=0.39,
                about_this_page=0.7,
                wants_person=0,
                needs_followup=0,
                seconds=0,
                cost=0,
                saved_protection_question=0.1,
            )

    other = TurnRequest.model_validate(
        {
            "conversation_id": "test",
            "messages": [
                {
                    "role": "user",
                    "content": "Why did the actual fault occur and which breaker should replace this one?",
                }
            ],
            "locale": "en",
            "page_context": page.model_dump(),
        }
    ).model_copy(update={"planning_context": raw})
    other_prepared = Understander(None, OtherJev()).prepare(other, None)  # type: ignore[arg-type]
    assert "verified saved protection explanation" not in other_prepared.route.reasons

    raw["runs"][0]["kind"] = "single_ac_energy_replay_v1"
    assert not planning.is_protection_report(raw, page)


def test_actual_saved_report_question_takes_the_service_answer_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from linker_genie.app import _answer
    from linker_genie.understand import Understander

    raw, page = source()
    raw["runs"][0].update(
        kind="planning_report_v1",
        declared_installation_materials=[
            {
                "quantity": {"en": "8 pc", "de": "8 Stk."},
                "explanation": {
                    "en": "5 × 0 + 2 × 4 + 3 × 0 = 8 pieces",
                    "de": "5 × 0 + 2 × 4 + 3 × 0 = 8 Stück",
                },
            }
        ],
    )
    question = "How many end clamps does this saved report calculate, and what does that calculation establish? What is the name of the material in the report?"
    request = TurnRequest.model_validate(
        {
            "conversation_id": "test",
            "messages": [{"role": "user", "content": question}],
            "locale": "en",
            "page_context": page.model_dump(),
        }
    ).model_copy(update={"planning_context": raw})
    reading = Reading(
        intent="documents_specs",
        confidence=0.9,
        about_this_page=1,
        wants_person=0,
        needs_followup=0,
        seconds=0,
        cost=0,
        saved_material_question=0.85,
    )
    subject = Subject(ids=(), device_class={})
    route = plan(question, [], reading, subject, "en", False)
    assert route.name == "documents"

    class RecordedJev:
        def read(
            self, message: str, page: dict[str, Any], history: Any = ()
        ) -> Reading:
            assert message == question and page["saved_report"] is True
            return reading

    calls: list[int] = []
    original_answer = planning.material_answer

    def counted(raw: Any, page: PageContext, language: str) -> str:
        calls.append(1)
        return original_answer(raw, page, language)

    monkeypatch.setattr(planning, "material_answer", counted)
    prepared = Understander(None, RecordedJev()).prepare(request, None)  # type: ignore[arg-type]
    assert prepared.route.name == "planning_project" and prepared.route.calls == ()
    assert calls == []
    result, _ = _answer(request, prepared, SimpleNamespace(), None, abilities=None)  # type: ignore[arg-type]
    assert calls == [1]
    assert result.attempts == 0 and prepared.log["saved_material_answer"] is True
    block = result.output.blocks[0]
    assert isinstance(block, TextBlock)
    assert "5 × 0 + 2 × 4 + 3 × 0 = 8 pieces" in block.text
    assert "cannot verify" in block.text


def test_only_succeeded_report_with_declared_materials_gets_material_intent() -> None:
    from linker_genie.understand import Understander

    raw, page = source()
    raw["runs"][0]["declared_installation_materials"] = [
        {"quantity": {"en": "8 pc", "de": "8 St."}, "explanation": None}
    ]
    request = TurnRequest.model_validate(
        {
            "conversation_id": "test",
            "messages": [{"role": "user", "content": "How many hours?"}],
            "page_context": page.model_dump(),
        }
    ).model_copy(update={"planning_context": raw})

    class NonReportJev:
        def read(
            self, message: str, page: dict[str, Any], history: Any = ()
        ) -> Reading:
            assert "saved_report" not in page
            return Reading(
                intent="small_talk",
                confidence=0.9,
                about_this_page=0,
                wants_person=0,
                needs_followup=0,
                seconds=0,
                cost=0,
            )

    assert not planning.is_material_report(raw, page)
    prepared = Understander(None, NonReportJev()).prepare(request, None)  # type: ignore[arg-type]
    assert "verified saved material explanation" not in prepared.route.reasons


@pytest.mark.parametrize(
    ("question", "score"),
    [
        ("How many hours does this report cover?", 0.16),
        ("Which inverter is in my bill of materials?", 0.16),
        ("How many hours does this report cover?", None),
    ],
)
def test_unrelated_saved_report_questions_keep_their_normal_route(
    monkeypatch: pytest.MonkeyPatch, question: str, score: float | None
) -> None:
    from types import SimpleNamespace

    import linker_genie.app as app_module
    from linker_genie.cycle import TurnResult
    from linker_genie.facts import TurnFacts
    from linker_genie.understand import Prepared

    raw, page = source()
    raw["runs"][0].update(
        kind="planning_report_v1",
        declared_installation_materials=[
            {"quantity": {"en": "8 pc", "de": "8 St."}, "explanation": None}
        ],
    )
    request = TurnRequest.model_validate(
        {
            "conversation_id": "test",
            "messages": [{"role": "user", "content": question}],
            "locale": "en",
            "page_context": page.model_dump(),
        }
    ).model_copy(update={"planning_context": raw})
    reading = Reading(
        intent="other",
        confidence=0.9,
        about_this_page=1,
        wants_person=0,
        needs_followup=0,
        seconds=0,
        cost=0,
        saved_material_question=score,
    )
    prepared = Prepared(route=Route("model"), reading=reading)
    expected = TurnResult(
        output=TurnOutput(language="en", blocks=[TextBlock(text="normal route")]),
        facts=TurnFacts(),
        grounded=True,
        failures=(),
        fallback=False,
        attempts=1,
    )
    monkeypatch.setattr(app_module, "run", lambda *args, **kwargs: expected)
    native_request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(generate=object()))
    )
    result, _ = app_module._answer(
        request,
        prepared,
        native_request,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        abilities=None,  # type: ignore[arg-type]
    )
    assert result is expected and "saved_material_answer" not in prepared.log


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


def test_provisional_bom_keeps_verified_provenance_and_scope() -> None:
    raw, page = source()
    raw["runs"][0].update(
        kind="planning_report_v1",
        materials={
            "status": "verified",
            "sha256": "c" * 64,
            "model": "project_materials_v3",
            "line_count": 4,
            "unresolved_quantity_count": 2,
            "handling_counts": {
                "customer_supplied_required": 1,
                "site_engineering_required": 1,
                "woo_product": 1,
                "manufacturer_included": 1,
            },
            "scope": "provisional_not_complete_bos",
        },
        rows=[
            {
                "label": "Provisional bill of materials",
                "value": {"Product": "GoodWe GW61.4-BAT-AC-G10", "Quantity": "—"},
            }
        ],
    )

    payload, gathered = planning.record(raw, page)

    assert payload["status"] == "available" and payload["truncated"] is False
    assert "GoodWe GW61.4-BAT-AC-G10" in payload["text"]
    assert "Verified provisional bill of materials:" in payload["text"]
    assert (
        "quantities unresolved; not a complete balance-of-system take-off."
        in payload["text"]
    )
    assert {"4", "2"} <= set(payload["figures"].values())
    assert "provenance SHA-" in payload["text"]
    assert "c" * 64 in payload["text"]
    assert "site_engineering_required" in payload["text"]
    assert gathered.tool_calls[0]["name"] == planning.NAME
    assert len(payload["text"]) <= planning.MAX_TEXT_CHARS

    malformed = json.loads(json.dumps(raw))
    malformed["runs"][0]["materials"]["sha256"] = "not-a-hash"
    assert planning.record(malformed, page)[0] == {"error": "unavailable"}
    malformed = json.loads(json.dumps(raw))
    malformed["runs"][0]["materials"]["model"] = "x" * 30_000
    assert planning.record(malformed, page)[0] == {"error": "unavailable"}
    malformed = json.loads(json.dumps(raw))
    malformed["runs"][0]["materials"]["handling_counts"] = {"approval_granted": 4}
    assert planning.record(malformed, page)[0] == {"error": "unavailable"}


@pytest.mark.parametrize(
    ("locale", "question"),
    [
        ("en", "What is in the bill of materials for this plan?"),
        ("en", "Is the BOM a complete balance of system?"),
        ("en", "Are the BOMs complete?"),
        ("en", "Review the material lists"),
        ("de", "Was steht in der vorläufigen Stückliste?"),
        ("de", "Ist die Materialliste ein vollständiges BOS?"),
        ("de", "Was steht in den Stücklisten?"),
        ("de", "Sind die Materiallisten vollständig?"),
    ],
)
def test_bom_questions_read_the_exact_planning_project(
    locale: str, question: str
) -> None:
    _, page = source()
    routed = with_page(
        Route("model"),
        page,
        False,
        True,
        Subject((), {}, {}),
        question,
    )

    assert page.planning_project_id is not None
    assert [call.ability for call in routed.calls] == [planning.NAME]


def test_boss_does_not_trigger_the_bom_route() -> None:
    _, page = source()
    routed = with_page(
        Route("model"),
        page,
        False,
        True,
        Subject((), {}, {}),
        "Who is the boss?",
    )

    assert routed.calls == ()


def test_bom_planning_call_survives_a_full_documents_route() -> None:
    _, page = source()
    subject = Subject(
        (1, 2, 3, 4),
        {1: "home-storage", 2: "home-storage", 3: "home-storage", 4: "home-storage"},
        {1: "A", 2: "B", 3: "C", 4: "D"},
    )
    message = "What is in the BOM for this project?"
    route = plan(
        message,
        [],
        Reading("documents_specs", 0.95, 0.1, 0.05, 0.2, 2.6, 0.0),
        subject,
        "en",
    )
    assert route.name == "documents"

    routed = with_page(route, page, False, True, subject, message)

    assert planning.NAME in [call.ability for call in routed.calls]
    assert planning.NAME not in [call.ability for call in routed.dropped]


def test_active_project_sizing_reads_selected_history_instead_of_blank_tool() -> None:
    _, page = source()
    routed = with_page(
        Route("sizing"), page, False, True, Subject((), {}, {}), "Explain this project"
    )
    assert routed.name == "planning_project"
    assert [call.ability for call in routed.calls] == [planning.NAME]
    assert routed.no_cards
