"""The routing table: Jev's intent and the product words decide the tools (route.py)."""

import pytest

from linker_genie.jev import Reading
from linker_genie.lexicon import Match
from linker_genie.route import CONFIDENT, Subject, plan, sizing_input

NONE = Subject((), {}, {})
H2 = Subject((4107,), {4107: "inverters", 1832: "home-storage"}, {4107: "H2-10K-T3"})


def _reading(intent: str, confidence: float = 0.95, person: float = 0.05) -> Reading:
    return Reading(intent, confidence, 0.1, person, 0.2, 2.6, 0.0)  # type: ignore[arg-type]


def _model(value: str, *ids: int) -> Match:
    return Match("model", value, value, frozenset(ids), value)


def test_sizing_opens_the_configurator_with_the_stated_figures() -> None:
    message = "What size battery for 8 kWp PV and 6000 kWh per year?"
    route = plan(message, [], _reading("sizing", 1.0), NONE, "en")
    assert route.name == "sizing"
    (call,) = route.calls
    assert call.ability == "linker/size-hint"
    assert call.arguments == {"pv_kwp": 8.0, "annual_load_kwh": 6000.0}
    assert route.action == "open_configurator"
    assert route.no_cards and route.no_handoff


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Wie groß sollte der Speicher bei 10 kWp sein?", {"pv_kwp": 10.0}),
        (
            "12,5 kWp, 4.500 kWh pro Jahr, dreiphasig mit Notstrom",
            {"pv_kwp": 12.5, "annual_load_kwh": 4500.0, "phase": 3, "backup": "needed"},
        ),
        ("single-phase, 5 kWp", {"pv_kwp": 5.0, "phase": 1}),
        ("help me design a system for a farm", {}),
    ],
)
def test_sizing_figures_are_read_in_code(
    message: str, expected: dict[str, object]
) -> None:
    assert sizing_input(message) == expected


def test_a_document_question_searches_the_documents_of_its_product() -> None:
    message = "Wie wird der SAJ CB2-100.3-HV5 installiert? Welcher Mindestabstand?"
    subject = Subject((2101,), {2101: "battery-systems"}, {2101: "CB2-100.3-HV5"})
    route = plan(
        message,
        [_model("CB2-100.3-HV5", 2101)],
        _reading("documents_specs", 0.93),
        subject,
        "de",
    )
    assert route.name == "documents"
    assert [c.ability for c in route.calls] == [
        "linker/search-knowledge",
        "linker/get-product",
    ]
    assert route.calls[0].arguments == {
        "query": message,
        "lang": "de",
        "product_ids": [2101],
    }
    assert route.no_handoff


def test_a_family_document_question_brings_the_family_facts() -> None:
    message = "Is the EcoFlow OCEAN 2 single-phase or three-phase?"
    matches = [
        Match("series", "a", "ecoflow-ocean2-hd-p3-s2", frozenset(), "OCEAN 2"),
        Match("series", "b", "ecoflow-ocean-2-battery", frozenset(), "OCEAN 2"),
        Match("brand", "EcoFlow", "ecoflow", frozenset(), "EcoFlow"),
    ]
    route = plan(message, matches, _reading("documents_specs"), NONE, "en")
    assert [c.ability for c in route.calls] == [
        "linker/search-knowledge",
        "linker/search-products",
    ]
    assert route.calls[1].arguments == {
        "text": "OCEAN 2",
        "brand": "ecoflow",
        "lang": "en",
        "limit": 6,
    }


def test_pairing_of_one_inverter_reads_its_documented_batteries() -> None:
    route = plan(
        "Which battery works with the SAJ H2-10K-T3?",
        [_model("H2-10K-T3", 4107)],
        _reading("pairing_compatibility"),
        H2,
        "en",
    )
    assert route.name == "pairing"
    (call,) = route.calls
    assert call.ability == "linker/search-products"
    assert call.arguments["with_pairings"] is True
    assert call.arguments["text"] == "H2-10K-T3"


def test_pairing_of_two_products_checks_the_pair() -> None:
    subject = Subject((4107, 1832), H2.device_class, H2.labels)
    route = plan("does it fit?", [], _reading("pairing_compatibility"), subject, "en")
    assert route.calls[0].ability == "linker/check-compatibility"
    assert route.calls[0].arguments == {"product_ids": [4107, 1832]}


def test_compare_of_two_models_compares_them() -> None:
    subject = Subject((4107, 3555), {}, {})
    route = plan("compare", [], _reading("compare"), subject, "de")
    assert route.calls[0].ability == "linker/compare-products"
    assert route.calls[0].arguments == {"product_ids": [4107, 3555], "lang": "de"}


def test_a_brand_comparison_without_models_is_left_to_the_model() -> None:
    matches = [
        Match("brand", "SAJ", "saj", frozenset(), "SAJ"),
        Match("brand", "GoodWe", "goodwe", frozenset(), "GoodWe"),
    ]
    route = plan(
        "SAJ vs GoodWe for commercial storage", matches, _reading("compare"), NONE, "en"
    )
    assert route.name == "model"
    assert route.calls == ()
    assert route.no_handoff


def test_inquiry_status_is_fetched_by_code() -> None:
    route = plan("where is my proforma?", [], _reading("inquiry_status"), NONE, "en")
    assert [c.ability for c in route.calls] == ["linker/inquiry-status"]


@pytest.mark.parametrize("message", ["can I talk to someone?", "this bot is useless"])
def test_a_person_goes_through_the_person_seam(message: str) -> None:
    route = plan(message, [], _reading("talk_to_person"), NONE, "en")
    assert route.name == "person"
    assert route.calls[0].ability == "linker/handoff-team"


def test_frustration_reaches_a_person_even_when_the_intent_is_unsure() -> None:
    route = plan("das hilft nicht", [], _reading("other", 0.5, person=0.9), NONE, "de")
    assert route.name == "person"


def test_company_questions_hand_off_to_the_team() -> None:
    route = plan(
        "Liefern Sie nach Österreich?",
        [],
        _reading("company_logistics_service"),
        NONE,
        "de",
    )
    assert route.name == "service"
    assert route.calls[0].arguments == {"summary": "Liefern Sie nach Österreich?"}


def test_an_unsure_reading_lets_the_model_decide() -> None:
    reading = _reading("inquiry_status", CONFIDENT - 0.22)
    route = plan("what happens after I send the inquiry?", [], reading, NONE, "en")
    assert route.name == "model"
    assert route.calls == ()
    assert "jev unsure: inquiry_status 0.58" in route.reasons


def test_without_jev_the_model_decides_and_the_reason_is_recorded() -> None:
    route = plan("Danke schön", [], None, NONE, "de")
    assert (route.name, route.calls, route.reasons) == (
        "model",
        (),
        ("jev unavailable",),
    )


def test_small_talk_without_product_words_runs_no_tool() -> None:
    route = plan("hi", [], _reading("small_talk"), NONE, "en")
    assert (route.name, route.calls) == ("model", ())


def test_product_words_in_an_unplaced_question_search_without_forcing_cards() -> None:
    matches = [Match("series", "saj-h2", "saj-h2", frozenset(), "SAJ H2")]
    reading = _reading("documents_specs", 0.67)
    route = plan(
        "How do I set the export limit on an SAJ H2 inverter?",
        matches,
        reading,
        NONE,
        "en",
    )
    assert route.name == "products"
    assert route.calls[0].ability == "linker/search-products"
    assert not route.show_products
    assert "Jev leans to documents_specs (0.67)" in route.hint
