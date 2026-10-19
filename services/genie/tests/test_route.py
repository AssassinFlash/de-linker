"""The routing table: Jev's intent and the product words decide the tools (route.py)."""

import pytest

from linker_genie.jev import Reading
from linker_genie.lexicon import Match
from linker_genie.prefill import sizing_input
from linker_genie.route import CONFIDENT, Subject, plan

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
    # Round-2 regressions (negation, questions, postcode, cross-turn) are
    # registered for #339 in test_prefill.py.
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


@pytest.mark.parametrize(
    "message", ["can I talk to someone?", "kann mich jemand anrufen"]
)
def test_a_person_is_the_person_route_with_no_call(message: str) -> None:
    # The turn is the service's sentence and the contact card (#243): no ability,
    # no model.
    route = plan(message, [], _reading("talk_to_person"), NONE, "en")
    assert route.name == "person"
    assert route.calls == ()


def test_frustration_on_an_unsure_intent_is_answered_as_routed() -> None:
    # The contact offer goes beside the answer (contact.decide), the answer stays.
    route = plan("das hilft nicht", [], _reading("other", 0.5, person=0.9), NONE, "de")
    assert route.name == "model"


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


def test_a_how_to_question_with_product_words_searches_the_documents_in_code() -> None:
    # Trial question 9: Jev reads documents_specs at 0.67, below CONFIDENT.
    h2 = Subject((), {}, {}, {}, {"saj-h2": {3557, 3556, 4107, 4108, 3558}})
    matches = [Match("series", "saj-h2", "saj-h2", frozenset(), "SAJ H2")]
    message = "How do I set the export limit on an SAJ H2 inverter?"
    route = plan(message, matches, _reading("documents_specs", 0.67), h2, "en")
    assert route.name == "documents"
    assert [c.ability for c in route.calls] == [
        "linker/search-products",
        "linker/search-knowledge",
    ]
    assert route.calls[0].arguments["series"] == "saj-h2"
    assert route.calls[1].arguments == {
        "query": message,
        "lang": "en",
        "product_ids": [3556, 3557, 3558, 4107],
    }
    assert route.no_handoff and not route.show_products


def test_a_document_reading_uses_the_matched_models_for_the_documents() -> None:
    matches = [_model("H2-10K-T3", 4107)]
    route = plan(
        "export limit H2-10K-T3?", matches, _reading("documents_specs", 0.5), H2, "en"
    )
    assert route.calls[-1].arguments["product_ids"] == [4107]


def test_product_words_in_an_unplaced_question_search_without_forcing_cards() -> None:
    matches = [Match("series", "saj-h2", "saj-h2", frozenset(), "SAJ H2")]
    reading = _reading("compare", 0.6)
    route = plan("SAJ H2 or something else?", matches, reading, NONE, "en")
    assert route.name == "products"
    assert [c.ability for c in route.calls] == ["linker/search-products"]
    assert not route.show_products
    assert "Jev leans to compare (0.60)" in route.hint


INVERTERS = Match("category", "inverters", "inverters", frozenset(), "inverter")
EN_30 = "What is your smallest inverter with at least 30 kW?"
DE_30 = "Was ist Ihr kleinster Wechselrichter mit mindestens 30 kW?"
SMALLEST_30 = {
    "device_class": "inverters",
    "ac_power_min": 30.0,
    "extreme": "smallest",
    "limit": 1,
}
CHEAPEST_10 = {
    "device_classes": ["home-storage", "battery-systems"],
    "kwh_min": 10.0,
    "extreme": "cheapest",
    "limit": 6,
}


def _search_args(
    message: str,
    lang: str,
    reading: Reading | None,
    matches: list[Match] | None = None,
) -> dict[str, object]:
    route = plan(
        message,
        [INVERTERS] if matches is None else matches,
        reading,
        NONE,
        lang,
    )
    assert route.name == "products"
    assert route.show_products and route.no_handoff
    (call,) = route.calls
    assert call.ability == "linker/search-products"
    assert f"extreme: {call.arguments['extreme']}" in route.reasons
    return call.arguments


@pytest.mark.parametrize(
    "reading",
    [_reading("find_products"), _reading("find_products", 0.5), None],
)
def test_smallest_inverter_at_least_30_kw_aggregates(reading: Reading | None) -> None:
    # J5-EN: relevance order named GW75K. The route filters ac_power_kw >= 30
    # and asks for the minimum, including when Jev is sure, unsure, or down.
    assert _search_args(EN_30, "en", reading) == {**SMALLEST_30, "lang": "en"}


def test_the_german_smallest_inverter_uses_the_same_aggregate() -> None:
    english = _search_args(EN_30, "en", _reading("find_products"))
    german = _search_args(DE_30, "de", _reading("find_products"))
    assert german == {**english, "lang": "de"}


def test_a_matched_model_does_not_narrow_the_extreme() -> None:
    matches = [_model("GW75K-ET-G10", 6506), INVERTERS]
    args = _search_args(EN_30, "en", _reading("find_products"), matches)
    assert "text" not in args
    assert args["device_class"] == "inverters"
    assert args["ac_power_min"] == 30.0


def test_one_written_model_does_not_replace_the_extreme() -> None:
    # The code is in the question and still is not a text filter. Two codes
    # would be searched on their own; one is not.
    message = "What is your smallest inverter with at least 30 kW, the GW75K-ET-G10?"
    matches = [_model("GW75K-ET-G10", 6506), INVERTERS]
    args = _search_args(message, "en", _reading("find_products"), matches)
    assert "text" not in args
    assert args["ac_power_min"] == 30.0
    assert args["extreme"] == "smallest"


def test_an_extreme_over_a_brand_or_series_is_not_a_model_conflict() -> None:
    brand = Match("brand", "GoodWe", "goodwe", frozenset(), "GoodWe")
    smallest = plan(
        "What is your smallest GoodWe inverter?",
        [brand, INVERTERS],
        _reading("find_products"),
        NONE,
        "en",
    )
    assert smallest.named_models == ()
    assert "brand and model disagree" not in smallest.reasons
    (call,) = smallest.calls
    assert call.arguments["brand"] == "goodwe"
    assert call.arguments["extreme"] == "smallest"
    assert call.arguments["device_class"] == "inverters"
    assert "text" not in call.arguments

    series = Match("series", "SAJ H2", "saj-h2", frozenset({1}), "SAJ H2")
    saj = Match("brand", "SAJ", "saj", frozenset(), "SAJ")
    largest = plan(
        "What is your largest SAJ H2 inverter?",
        [series, saj, INVERTERS],
        _reading("find_products"),
        NONE,
        "en",
    )
    assert largest.named_models == ()
    assert "brand and model disagree" not in largest.reasons
    (call,) = largest.calls
    assert call.arguments["series"] == "saj-h2"
    assert call.arguments["brand"] == "saj"
    assert call.arguments["extreme"] == "largest"
    assert "text" not in call.arguments


def test_several_written_models_keep_their_searches_beside_an_extreme() -> None:
    message = (
        "Which is the smallest inverter, HS3-5K-T2 or HS3-12K-T2, with at least 5 kW?"
    )
    matches = [_model("HS3-5K-T2", 2198), _model("HS3-12K-T2", 1185), INVERTERS]
    route = plan(message, matches, _reading("find_products"), NONE, "en")
    assert [call.arguments.get("text") for call in route.calls] == [
        "HS3-5K-T2",
        "HS3-12K-T2",
    ]
    assert all("extreme" not in call.arguments for call in route.calls)
    assert [note.code for note in route.named_models] == ["HS3-5K-T2", "HS3-12K-T2"]
    assert "several models" in route.reasons


def test_smallest_inverter_at_least_20_kw_uses_that_floor() -> None:
    args = _search_args(
        "What is your smallest inverter with at least 20 kW?",
        "en",
        None,
        [],
    )
    assert args == {
        "lang": "en",
        "device_class": "inverters",
        "ac_power_min": 20.0,
        "extreme": "smallest",
        "limit": 1,
    }


def test_largest_inverter_aggregates_the_class() -> None:
    args = _search_args(
        "What is your largest inverter?", "en", _reading("find_products")
    )
    assert args == {
        "lang": "en",
        "device_class": "inverters",
        "extreme": "largest",
        "limit": 1,
    }


def test_cheapest_battery_at_least_10_kwh_is_the_same_shape_in_both_languages() -> None:
    english = "What is your cheapest battery with at least 10 kWh?"
    german = "Was ist Ihre günstigste Batterie mit mindestens 10 kWh?"
    assert _search_args(english, "en", _reading("find_products"), []) == {
        **CHEAPEST_10,
        "lang": "en",
    }
    assert _search_args(german, "de", None, []) == {**CHEAPEST_10, "lang": "de"}


def test_a_kwp_sizing_question_is_not_an_extreme() -> None:
    message = "Wie groß sollte der Speicher bei 10 kWp sein?"
    route = plan(message, [], _reading("sizing"), NONE, "de")
    assert route.name == "sizing"
    assert route.calls[0].ability == "linker/size-hint"
    assert "extreme" not in route.calls[0].arguments


def test_a_how_to_about_an_inverter_is_not_an_extreme() -> None:
    h2 = Subject((), {}, {}, {}, {"saj-h2": {3557, 3556, 4107, 4108, 3558}})
    matches = [Match("series", "saj-h2", "saj-h2", frozenset(), "SAJ H2")]
    message = "How do I set the export limit on an SAJ H2 inverter?"
    route = plan(message, matches, _reading("documents_specs", 0.67), h2, "en")
    assert route.name == "documents"
    assert all("extreme" not in call.arguments for call in route.calls)


def test_a_person_or_inquiry_question_is_not_an_extreme_search() -> None:
    person = plan(EN_30, [INVERTERS], _reading("talk_to_person"), NONE, "en")
    inquiry = plan(EN_30, [INVERTERS], _reading("inquiry_status"), NONE, "en")
    assert person.name == "person" and person.calls == ()
    assert inquiry.name == "inquiry"
    assert inquiry.calls[0].ability == "linker/inquiry-status"
