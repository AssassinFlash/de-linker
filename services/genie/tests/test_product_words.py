"""Brand/model conflicts, unknown models, and several models in one sentence.

The fixtures are the live store snapshot (tests/fixtures/storeapi.json,
2026-10-15). #363 and #367 are the SAJ/EcoFlow readings of GoodWe models.
#364 is a sentence that names three SAJ HS3 models.

The #339 cases for these tickets are executed from
services/genie/eval/regression/339-product-words.jsonl
(tests/test_regression_339.py). docs/acceptance/2026-10-19/379/339-cases.md
points at that file.
"""

from dataclasses import replace

import pytest

from linker_genie.cycle import run
from linker_genie.facts import Fact, TurnFacts
from linker_genie.ground import check
from linker_genie.jev import Reading
from linker_genie.lexicon import Match, Vocabulary
from linker_genie.route import (
    DOCUMENTS_SPARE,
    Call,
    NamedModel,
    Route,
    Subject,
    plan,
    with_page,
)
from linker_genie.schema import (
    CardsBlock,
    HandoffBlock,
    PageContext,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import (
    DEGRADED,
    NO_MATCH_DE,
    NO_MATCH_EN,
    fallback,
    german_is_clean,
)
from linker_genie.tools import MAX_TOOL_CALLS, READ_PAGE

SAJ_GOODWE = "Is the SAJ GW10K-ETA-G20 in stock?"
SAJ_GOODWE_DE = "Haben Sie den SAJ GW10K-ETA-G20?"
ECOFLOW_GOODWE = "EcoFlow GW5K-ETA-G20 availability?"
ECOFLOW_GOODWE_DE = "EcoFlow GW5K-ETA-G20 - lieferbar?"
UNKNOWN = "Do you have the GW50K-ETA-G20 in stock?"
UNKNOWN_DE = "Haben Sie den GW50K-ETA-G20 auf Lager?"
THREE = "Do you have HS3-5K-T2-W/G-PX, HS3-8K-T2-W/G-PX and HS3-12K-T2-W/G-PX in stock?"
THREE_DE = (
    "Haben Sie HS3-5K-T2-W/G-PX, HS3-8K-T2-W/G-PX und HS3-12K-T2-W/G-PX auf Lager?"
)
HS3 = ("HS3-5K-T2-W/G-PX", "HS3-8K-T2-W/G-PX", "HS3-12K-T2-W/G-PX")
# Kept family searches (#363 G2/G3/G4): a code the catalog does not list beside a
# real brand or series stays on that search.
FAMILY = (
    "Is the SAJ H2-35K-T3 available?",
    "I need the SAJ R5-8K-T3 hybrid inverter, 8 kW.",
    "Can you quote 20 pieces of DLK-SAJ-CHS2-75K-T8-X?",
)


def _reading(intent: str, confidence: float = 0.95) -> Reading:
    return Reading(intent, confidence, 0.1, 0.05, 0.2, 2.6, 0.0)  # type: ignore[arg-type]


_FIND_PRODUCTS = _reading("find_products")


def _catalog(vocabulary: Vocabulary) -> Subject:
    return Subject(
        (),
        vocabulary.device_class,
        vocabulary.labels,
        vocabulary.phase,
        vocabulary.series_members,
        brand_of={key: set(value) for key, value in vocabulary.brand_of.items()},
        brand_names=dict(vocabulary.brand_names),
        names=dict(vocabulary.names),
        catalog_models=vocabulary.model_codes(),
    )


def _route(
    vocabulary: Vocabulary,
    message: str,
    lang: str,
    reading: Reading | None = _FIND_PRODUCTS,
) -> Route:
    return plan(
        message,
        vocabulary.match(message),
        reading,
        _catalog(vocabulary),
        lang,
    )


def _texts(route: Route) -> list[str]:
    return [
        str(call.arguments.get("text"))
        for call in route.calls
        if call.ability == "linker/search-products"
    ]


def _sentence(output: TurnOutput) -> str:
    return " ".join(
        block.text for block in output.blocks if isinstance(block, TextBlock)
    )


def _facts(*ids: int, searched: bool = True) -> TurnFacts:
    facts = TurnFacts()
    facts.product_ids = set(ids)
    facts.qualified_ids = set(ids)
    if searched:
        facts.tool_calls.append(
            {
                "name": "linker/search-products",
                "arguments": {},
                "ok": True,
                "result": {},
            }
        )
    return facts


def test_a_conflicting_brand_searches_the_catalog_brand(
    vocabulary: Vocabulary,
) -> None:
    for message, lang in ((SAJ_GOODWE, "en"), (SAJ_GOODWE_DE, "de")):
        route = _route(vocabulary, message, lang)
        assert route.name == "products"
        assert route.show_products and route.no_handoff
        assert _texts(route) == ["GW10K-ETA-G20"]
        assert "brand" not in route.calls[0].arguments
        (note,) = route.named_models
        assert note.written_brand == "SAJ"
        assert note.catalog_brand == "GoodWe"
        assert 3556 in note.product_ids
        assert note.searched and not note.unknown
        assert "brand and model disagree" in route.reasons


def test_the_goodwe_model_without_a_stored_brand_is_still_named(
    vocabulary: Vocabulary,
) -> None:
    """Product 6512's store attributes carry no pa_brand; the title names GoodWe."""
    assert not vocabulary.brand_of.get(6512)
    for message, lang in ((ECOFLOW_GOODWE, "en"), (ECOFLOW_GOODWE_DE, "de")):
        route = _route(vocabulary, message, lang)
        assert _texts(route) == ["GW5K-ETA-G20"]
        assert "brand" not in route.calls[0].arguments
        (note,) = route.named_models
        assert note.written_brand == "EcoFlow"
        assert note.catalog_brand == "GoodWe"
        assert 6512 in note.product_ids
        assert route.show_products and route.no_handoff


def test_a_brand_conflict_is_not_swallowed_by_an_extreme(
    vocabulary: Vocabulary,
) -> None:
    message = "Is the SAJ GW10K-ETA-G20 your smallest inverter?"
    route = _route(vocabulary, message, "en")
    assert _texts(route) == ["GW10K-ETA-G20"]
    assert "extreme" not in route.calls[0].arguments
    assert "brand" not in route.calls[0].arguments
    (note,) = route.named_models
    assert note.written_brand == "SAJ"
    assert note.catalog_brand == "GoodWe"
    assert "brand and model disagree" in route.reasons


def test_an_extreme_over_a_brand_stays_one_aggregate(vocabulary: Vocabulary) -> None:
    route = _route(vocabulary, "What is your smallest GoodWe inverter?", "en")
    (call,) = route.calls
    assert call.arguments["extreme"] == "smallest"
    assert call.arguments["brand"] == "goodwe"
    assert call.arguments["device_class"] == "inverters"
    assert "text" not in call.arguments
    assert route.named_models == ()
    assert "brand and model disagree" not in route.reasons


def test_an_extreme_over_a_series_stays_one_aggregate(vocabulary: Vocabulary) -> None:
    route = _route(vocabulary, "What is your largest SAJ H2 inverter?", "en")
    (call,) = route.calls
    assert call.arguments["extreme"] == "largest"
    assert call.arguments.get("series") == "saj-h2"
    assert "text" not in call.arguments
    assert route.named_models == ()
    assert "brand and model disagree" not in route.reasons


SMALLEST_CLASS = "What is your smallest inverter with at least 30 kW?"
SMALLEST_CLASS_DE = "Was ist Ihr kleinster Wechselrichter mit mindestens 30 kW?"
SMALLEST_UNKNOWN = (
    "What is your smallest inverter with at least 30 kW, the GW50K-ETA-G20?"
)
SMALLEST_UNKNOWN_DE = (
    "Was ist Ihr kleinster Wechselrichter mit mindestens 30 kW, der GW50K-ETA-G20?"
)


@pytest.mark.parametrize(
    ("composite", "alone", "lang"),
    [
        (SMALLEST_UNKNOWN, SMALLEST_CLASS, "en"),
        (SMALLEST_UNKNOWN_DE, SMALLEST_CLASS_DE, "de"),
    ],
)
def test_a_class_extreme_also_searches_an_unknown_code(
    vocabulary: Vocabulary, composite: str, alone: str, lang: str
) -> None:
    # #339 registration (#384). The class aggregate used to be the only call,
    # so the unknown code was never searched and the answer never named it.
    route = _route(vocabulary, composite, lang)
    alone_route = _route(vocabulary, alone, lang)
    assert route.name == "products"
    assert route.show_products and route.no_handoff
    aggregate, *rest = route.calls
    (class_call,) = alone_route.calls
    assert aggregate.arguments == class_call.arguments
    assert aggregate.arguments["extreme"] == "smallest"
    assert aggregate.arguments["ac_power_min"] == 30.0
    assert "text" not in aggregate.arguments
    assert [call.arguments.get("text") for call in rest] == ["GW50K-ETA-G20", "ETA-G20"]
    assert all(call.arguments["lang"] == lang for call in route.calls)
    assert all("extreme" not in call.arguments for call in rest)
    assert all("price" not in call.arguments for call in route.calls)
    (note,) = route.named_models
    assert note.code == "GW50K-ETA-G20"
    assert note.unknown and note.searched
    assert "extreme: smallest" in route.reasons
    assert "model code not in the product data" in route.reasons
    assert "GW50K-ETA-G20" in route.hint


def test_the_unknown_code_extreme_answer_names_the_winner_and_the_code(
    vocabulary: Vocabulary,
) -> None:
    # Same block shape in both languages: the winner sentence, the code, one card.
    expected = {
        "en": (
            SMALLEST_UNKNOWN,
            "The GW30K-ETA-G20 meets the limit you named.",
            "GW50K-ETA-G20 is not in our product range.",
        ),
        "de": (
            SMALLEST_UNKNOWN_DE,
            "Das Modell GW30K-ETA-G20 erfüllt die genannte Grenze.",
            "Für GW50K-ETA-G20 haben wir kein Produkt.",
        ),
    }
    shapes: list[list[str]] = []
    for lang, (message, winner_sentence, range_sentence) in expected.items():
        route = _route(vocabulary, message, lang)
        facts = TurnFacts()
        facts.product_ids = {6518}
        facts.qualified_ids = {6518}
        facts.add(
            Fact(
                id="search.extreme_product_id",
                value="6518",
                source="search-products",
            )
        )
        facts.add(
            Fact(
                id="search.extreme_model",
                value="GW30K-ETA-G20",
                source="search-products",
            )
        )
        facts.tool_calls.append(
            {
                "name": "linker/search-products",
                "arguments": {"text": "GW50K-ETA-G20", "lang": lang, "limit": 6},
                "ok": True,
                "result": {"qualified": []},
            }
        )
        output = fallback(facts, lang, route)
        text = _sentence(output)
        assert winner_sentence in text
        assert range_sentence in text
        assert "€" not in text and "$" not in text and "{fact:" not in text
        cards = [block for block in output.blocks if isinstance(block, CardsBlock)]
        assert len(cards) == 1 and cards[0].product_ids == [6518]
        assert check(output, facts, route).ok
        if lang == "de":
            assert german_is_clean(text)
        shapes.append([type(block).__name__ for block in output.blocks])
        omitted = TurnOutput(
            language=lang,  # type: ignore[arg-type]
            blocks=[
                TextBlock(text=winner_sentence, refs=["6518"]),
                CardsBlock(product_ids=[6518]),
            ],
        )
        refused = check(omitted, facts, route)
        assert any("GW50K-ETA-G20" in failure for failure in refused.failures)
    assert shapes[0] == shapes[1]


def test_one_known_and_one_unknown_code_are_both_searched_beside_an_extreme(
    vocabulary: Vocabulary,
) -> None:
    # The prompt says every written code in an extreme question is searched.
    # One catalog code plus one unknown code used to search only the unknown.
    messages = (
        (
            "en",
            "What is your smallest inverter with at least 30 kW, "
            "the HS3-5K-T2-W/G-PX or the GW50K-ETA-G20?",
        ),
        (
            "de",
            "Was ist Ihr kleinster Wechselrichter mit mindestens 30 kW, "
            "der HS3-5K-T2-W/G-PX oder der GW50K-ETA-G20?",
        ),
    )
    for lang, message in messages:
        route = _route(vocabulary, message, lang)
        aggregate, *rest = route.calls
        assert aggregate.arguments["extreme"] == "smallest"
        assert aggregate.arguments["ac_power_min"] == 30.0
        assert "text" not in aggregate.arguments
        assert [call.arguments.get("text") for call in rest] == [
            "HS3-5K-T2-W/G-PX",
            "GW50K-ETA-G20",
            "ETA-G20",
        ]
        assert all("extreme" not in call.arguments for call in rest)
        known, unknown = route.named_models
        assert known.code == "HS3-5K-T2-W/G-PX"
        assert known.searched and not known.unknown
        assert 2198 in known.product_ids
        assert unknown.code == "GW50K-ETA-G20"
        assert unknown.searched and unknown.unknown
        assert "extreme: smallest" in route.reasons
        assert "model code not in the product data" in route.reasons


def test_several_models_and_an_extreme_search_each_model(
    vocabulary: Vocabulary,
) -> None:
    message = (
        "Which is the smallest inverter, HS3-5K-T2-W/G-PX or "
        "HS3-12K-T2-W/G-PX, with at least 5 kW?"
    )
    route = _route(vocabulary, message, "en")
    assert _texts(route)[:2] == [HS3[0], HS3[2]]
    assert all("extreme" not in call.arguments for call in route.calls)
    assert "several models" in route.reasons


def test_an_agreeing_brand_stays_on_the_search(vocabulary: Vocabulary) -> None:
    message = "Is the SAJ HS3-5K-T2-W/G-PX in stock?"
    route = _route(vocabulary, message, "en")
    assert route.calls[0].arguments["brand"] == "saj"
    assert route.calls[0].arguments["text"] == HS3[0]
    assert route.named_models[0].written_brand == ""


def test_three_models_are_each_searched(vocabulary: Vocabulary) -> None:
    for message, lang in ((THREE, "en"), (THREE_DE, "de")):
        route = _route(vocabulary, message, lang)
        assert _texts(route) == list(HS3)
        assert all("brand" not in call.arguments for call in route.calls)
        assert [note.code for note in route.named_models] == list(HS3)
        assert all(note.searched and not note.unknown for note in route.named_models)
        assert 2198 in route.named_models[0].product_ids
        assert 1187 in route.named_models[1].product_ids
        assert 1185 in route.named_models[2].product_ids
        assert route.show_products and route.no_handoff
        assert "several models" in route.reasons


def test_a_model_past_the_tool_budget_is_not_searched() -> None:
    codes = [f"M{i}-10K-T2" for i in range(MAX_TOOL_CALLS + 1)]
    matches = [
        Match("model", code, code, frozenset({index + 1}), code)
        for index, code in enumerate(codes)
    ]
    route = plan(
        " ".join(codes), matches, _reading("find_products"), Subject((), {}, {}), "en"
    )
    assert _texts(route) == codes[:MAX_TOOL_CALLS]
    assert [note.searched for note in route.named_models] == [True] * MAX_TOOL_CALLS + [
        False
    ]
    assert route.named_models[-1].code == codes[-1]


def test_an_unknown_model_is_searched_with_its_family(
    vocabulary: Vocabulary,
) -> None:
    for message, lang in ((UNKNOWN, "en"), (UNKNOWN_DE, "de")):
        for reading in (_reading("find_products"), _reading("other", 0.4), None):
            route = _route(vocabulary, message, lang, reading)
            assert route.name == "products"
            assert route.show_products and route.no_handoff
            assert _texts(route) == ["GW50K-ETA-G20", "ETA-G20"]
            (note,) = route.named_models
            assert note.unknown and note.searched
            assert note.code == "GW50K-ETA-G20"
            assert "model code not in the product data" in route.reasons


@pytest.mark.parametrize("message", FAMILY)
def test_a_family_search_is_not_replaced_by_an_unknown_code(
    vocabulary: Vocabulary, message: str
) -> None:
    route = _route(vocabulary, message, "en")
    assert route.calls
    assert not any(note.unknown for note in route.named_models)
    assert "GW50K-ETA-G20" not in _texts(route)


def test_a_phase_word_is_not_an_unknown_model(vocabulary: Vocabulary) -> None:
    route = _route(vocabulary, "Is 3-phase available?", "en", _reading("other", 0.4))
    assert route.calls == ()
    assert route.named_models == ()


def test_one_known_model_on_an_unplaced_question_does_not_force_cards() -> None:
    route = plan(
        "how does the H2-10K-T3 export limit work?",
        [Match("model", "H2-10K-T3", "H2-10K-T3", frozenset({4107}), "H2-10K-T3")],
        _reading("compare", 0.6),
        Subject((), {}, {}),
        "en",
    )
    assert route.name == "products"
    assert not route.show_products
    assert route.calls[0].arguments["text"] == "H2-10K-T3"


def test_a_dropped_page_search_marks_the_model_unsearched() -> None:
    notes = tuple(
        NamedModel(code=code)
        for code in ("A-10K-T2", "B-10K-T2", "C-10K-T2", "D-10K-T2")
    )
    calls = tuple(
        Call("linker/search-products", {"text": note.code, "lang": "en", "limit": 6})
        for note in notes
    )
    route = Route("documents", calls, no_handoff=True, named_models=notes)
    page = PageContext(type="product", url="https://de-linker.com/p", product_id=1)
    result = with_page(route, page, True, False, Subject((), {}, {}), "the page")
    assert [note.searched for note in result.named_models] == [True, True, True, False]
    assert "D-10K-T2" in result.hint
    assert "not searched" in result.hint.casefold()


def test_dropping_only_the_family_suffix_keeps_the_code_searched() -> None:
    note = NamedModel(code="GW50K-ETA-G20", unknown=True)
    calls = (
        Call(
            "linker/search-products",
            {"text": "GW50K-ETA-G20", "lang": "en", "limit": 6},
        ),
        Call("linker/search-products", {"text": "other", "lang": "en", "limit": 6}),
        Call("linker/search-products", {"text": "again", "lang": "en", "limit": 6}),
        Call("linker/search-products", {"text": "ETA-G20", "lang": "en", "limit": 6}),
    )
    route = Route("documents", calls, no_handoff=True, named_models=(note,))
    page = PageContext(type="faq", url="https://de-linker.com/faq")
    result = with_page(route, page, True, False, Subject((), {}, {}), "the page")
    assert result.named_models[0].searched is True
    assert "ETA-G20" not in _texts(result)


def test_conflict_fallback_names_both_brands_in_both_languages(
    vocabulary: Vocabulary,
) -> None:
    shapes = []
    for message, lang in ((SAJ_GOODWE, "en"), (SAJ_GOODWE_DE, "de")):
        route = _route(vocabulary, message, lang)
        output = fallback(_facts(3556), lang, route)
        text = _sentence(output)
        shapes.append([block.type for block in output.blocks])
        assert "GoodWe" in text and "SAJ" in text
        assert "GW10K-ETA-G20" in text
        assert not any(isinstance(block, HandoffBlock) for block in output.blocks)
        cards = [block for block in output.blocks if isinstance(block, CardsBlock)]
        assert cards and 3556 in cards[0].product_ids
        if lang == "de":
            assert german_is_clean(text)
            assert "angegeben" in text and "Karte" in text
    assert shapes[0] == shapes[1]


def test_unknown_model_fallback_offers_the_closest_products(
    vocabulary: Vocabulary,
) -> None:
    for message, lang, missing, closest in (
        (UNKNOWN, "en", "not in our product range", "closest products"),
        (UNKNOWN_DE, "de", "haben wir kein Produkt", "nächsten Produkte"),
    ):
        route = _route(vocabulary, message, lang)
        found = fallback(_facts(3556), lang, route)
        text = _sentence(found)
        assert "GW50K-ETA-G20" in text and missing in text and closest in text
        assert any(isinstance(block, CardsBlock) for block in found.blocks)
        assert not any(isinstance(block, HandoffBlock) for block in found.blocks)
        if lang == "de":
            assert german_is_clean(text)
        # A search that ran and returned nothing may say the code is absent.
        empty = fallback(_facts(searched=True), lang, route)
        assert missing in _sentence(empty)
        assert any(block.type == "ask" for block in empty.blocks)
        assert not any(isinstance(block, HandoffBlock) for block in empty.blocks)
        # No tool result is an outage, not an empty catalog.
        outage = fallback(TurnFacts(), lang, route)
        assert isinstance(outage.blocks[0], HandoffBlock)
        assert outage.blocks[0].summary == DEGRADED[lang]
        assert missing not in outage.blocks[0].summary


def test_an_empty_product_search_clarifies_and_an_outage_does_not() -> None:
    route = Route("products", no_handoff=True, show_products=True)
    found = fallback(_facts(searched=True), "en", route)
    assert _sentence(found) == NO_MATCH_EN
    assert [block.type for block in found.blocks] == ["text", "ask"]
    german = fallback(_facts(searched=True), "de", route)
    assert _sentence(german) == NO_MATCH_DE
    assert german_is_clean(_sentence(german))
    assert [block.type for block in german.blocks] == ["text", "ask"]
    outage = fallback(TurnFacts(), "en", route)
    assert isinstance(outage.blocks[0], HandoffBlock)


def test_an_unsearched_model_is_not_called_absent() -> None:
    codes = [f"M{index}-10K-T2" for index in range(MAX_TOOL_CALLS + 1)]
    notes = tuple(
        NamedModel(code=code, product_ids=(index + 1,), searched=index < MAX_TOOL_CALLS)
        for index, code in enumerate(codes)
    )
    route = Route("products", show_products=True, no_handoff=True, named_models=notes)
    ids = list(range(1, MAX_TOOL_CALLS + 1))
    for lang, missed in (
        ("en", "was not searched in this turn"),
        ("de", "nicht gesucht"),
    ):
        output = fallback(_facts(*ids), lang, route)
        text = _sentence(output)
        assert codes[-1] in text and missed in text
        assert "no entry" not in text.casefold()
        assert "nicht in unserem Sortiment" not in text
        if lang == "de":
            assert german_is_clean(text)


def test_grounding_refuses_an_absence_claim_for_a_model_that_was_searched() -> None:
    notes = tuple(
        NamedModel(code=code, product_ids=(pid,), searched=True)
        for code, pid in zip(HS3, (2198, 1187, 1185), strict=True)
    )
    route = Route("products", show_products=True, no_handoff=True, named_models=notes)
    facts = _facts(2198, 1187, 1185)
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "HS3-5K-T2-W/G-PX is in our product data. "
                    "These two model codes return no entry in our product data: "
                    "HS3-8K-T2-W/G-PX and HS3-12K-T2-W/G-PX."
                ),
                refs=["2198"],
            ),
            CardsBlock(product_ids=[2198]),
        ],
    )
    result = check(output, facts, route)
    assert not result.ok
    assert any("HS3-8K-T2-W/G-PX" in failure for failure in result.failures)
    assert any("HS3-12K-T2-W/G-PX" in failure for failure in result.failures)
    assert not any(
        "do not say HS3-5K-T2-W/G-PX" in failure for failure in result.failures
    )


def test_grounding_allows_an_absent_code_the_route_did_not_carry() -> None:
    route = Route("products", show_products=True, no_handoff=True)
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="H2-35K-T3 is not in our product range.",
                refs=["4107"],
            ),
            CardsBlock(product_ids=[4107]),
        ],
    )
    assert check(output, _facts(4107), route).ok


def test_grounding_requires_the_catalog_brand_and_accepts_it_with_the_card(
    vocabulary: Vocabulary,
) -> None:
    route = _route(vocabulary, SAJ_GOODWE, "en")
    facts = _facts(3556)
    missing = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="GW10K-ETA-G20 is not in our product range.", refs=["3556"]),
            CardsBlock(product_ids=[3556]),
        ],
    )
    refused = check(missing, facts, route)
    assert any("GoodWe" in failure for failure in refused.failures)
    split = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "The SAJ reading of GW10K-ETA-G20 is not in our product range. "
                    "The card shows the GoodWe product."
                ),
                refs=["3556"],
            ),
            CardsBlock(product_ids=[3556]),
        ],
    )
    assert not check(split, facts, route).ok
    catalog_only = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="GW10K-ETA-G20 is a GoodWe product.", refs=["3556"]),
            CardsBlock(product_ids=[3556]),
        ],
    )
    catalog_refused = check(catalog_only, facts, route)
    assert not catalog_refused.ok
    assert any("SAJ" in failure for failure in catalog_refused.failures)
    pointed = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="You wrote SAJ; GW10K-ETA-G20 is a GoodWe product.",
                refs=["3556"],
            ),
            CardsBlock(product_ids=[3556]),
        ],
    )
    assert check(pointed, facts, route).ok
    # The code may sit outside the sentence that names both brands.
    brands_only = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="You wrote SAJ; it is a GoodWe product.", refs=["3556"]),
            CardsBlock(product_ids=[3556]),
        ],
    )
    assert check(brands_only, facts, route).ok


def test_a_products_handoff_is_still_refused(vocabulary: Vocabulary) -> None:
    route = _route(vocabulary, SAJ_GOODWE, "en")
    output = TurnOutput(
        language="en",
        blocks=[
            HandoffBlock(summary="Our team will answer that at sales@de-linker.com.")
        ],
    )
    result = check(output, _facts(3556), route)
    assert any("not a question for the team" in failure for failure in result.failures)


def test_an_unsearched_code_must_be_named_as_not_searched() -> None:
    note = NamedModel(code="M4-10K-T2", product_ids=(4,), searched=False)
    carried = NamedModel(code="M0-10K-T2", product_ids=(1,), searched=True)
    route = Route(
        "products", show_products=True, no_handoff=True, named_models=(carried, note)
    )
    facts = _facts(1)
    omitted = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="M0-10K-T2 is listed.", refs=["1"]),
            CardsBlock(product_ids=[1]),
        ],
    )
    absent = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="M0-10K-T2 is listed. M4-10K-T2 is not in our product range.",
                refs=["1"],
            ),
            CardsBlock(product_ids=[1]),
        ],
    )
    said = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="M0-10K-T2 is listed. M4-10K-T2 was not searched in this turn.",
                refs=["1"],
            ),
            CardsBlock(product_ids=[1]),
        ],
    )
    assert any(
        "not searched" in failure for failure in check(omitted, facts, route).failures
    )
    assert any(
        "not that it is absent" in failure
        for failure in check(absent, facts, route).failures
    )
    assert check(said, facts, route).ok


def test_a_document_gap_is_not_an_absence_claim() -> None:
    note = NamedModel(code="HS3-5K-T2-W/G-PX", product_ids=(2198,))
    route = Route("documents", no_handoff=True, named_models=(note,))
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="Our documents do not state the export limit for HS3-5K-T2-W/G-PX."
            )
        ],
    )
    assert check(output, TurnFacts(), route).ok


@pytest.mark.parametrize("locale", ["en", "de"])
def test_a_conflict_handoff_falls_back_to_the_catalog_brand(
    vocabulary: Vocabulary, locale: str
) -> None:
    message = SAJ_GOODWE_DE if locale == "de" else SAJ_GOODWE
    route = _route(vocabulary, message, locale)
    facts = _facts(3556)

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language=locale,  # type: ignore[arg-type]
                blocks=[HandoffBlock(summary="Our team will answer that.")],
            ),
            facts,
        )

    request = TurnRequest(
        conversation_id="c1",
        messages=[TurnMessage(role="user", content=message)],
        locale=locale,  # type: ignore[arg-type]
    )
    result = run(request, generate, route, facts)
    assert result.fallback is True
    text = _sentence(result.output)
    assert "GoodWe" in text and "SAJ" in text
    assert not any(isinstance(block, HandoffBlock) for block in result.output.blocks)
    cards = [block for block in result.output.blocks if isinstance(block, CardsBlock)]
    assert cards and 3556 in cards[0].product_ids
    if locale == "de":
        assert german_is_clean(text)
    reported = TurnOutput(
        language=locale,  # type: ignore[arg-type]
        blocks=[
            TextBlock(text=text, refs=["3556"]),
            CardsBlock(product_ids=[3556]),
        ],
    )
    assert check(reported, facts, route).ok


def _search_result(text: str, *ids: int, ok: bool = True) -> dict[str, object]:
    """The shape abilities.record writes: real arguments, ok when the call returns.

    A route call that raises is omitted from tool_calls (understand.py). Tests
    for that failure leave the call out; they do not invent ok:false with empty
    arguments.
    """
    return {
        "name": "linker/search-products",
        "arguments": {"text": text, "lang": "en", "limit": 6},
        "ok": ok,
        "result": {"qualified": [{"product_id": pid} for pid in ids]} if ok else {},
    }


def _facts_for(calls: list[dict[str, object]], *ids: int) -> TurnFacts:
    facts = TurnFacts()
    facts.product_ids = set(ids)
    facts.qualified_ids = set(ids)
    facts.tool_calls.extend(calls)
    return facts


def test_an_unknown_code_on_a_product_page_is_not_called_absent(
    vocabulary: Vocabulary,
) -> None:
    """A documents route that cannot fit the code's search must not call it absent."""
    crowded = (3556, 1187, 2198)
    for message, lang, missed, absent in (
        (UNKNOWN, "en", "was not searched", "not in our product range"),
        (UNKNOWN_DE, "de", "nicht gesucht", "haben wir kein Produkt"),
    ):
        subject = replace(_catalog(vocabulary), ids=crowded)
        route = plan(
            message,
            vocabulary.match(message),
            _reading("documents_specs"),
            subject,
            lang,
        )
        assert len(route.calls) <= MAX_TOOL_CALLS - DOCUMENTS_SPARE
        (note,) = route.named_models
        assert note.code == "GW50K-ETA-G20"
        assert note.searched is False
        assert note.code not in _texts(route)
        # A successful search is in the facts, so an outage cannot hide a
        # note that was wrongly left searched.
        output = fallback(_facts(3556), lang, route)
        text = _sentence(output)
        assert missed in text
        assert absent not in text
        assert "no entry" not in text.casefold()
        assert not any(isinstance(block, HandoffBlock) for block in output.blocks)
        if lang == "de":
            assert german_is_clean(text)
    room = replace(_catalog(vocabulary), ids=(3556,))
    route = plan(
        UNKNOWN,
        vocabulary.match(UNKNOWN),
        _reading("documents_specs"),
        room,
        "en",
    )
    assert len(route.calls) <= MAX_TOOL_CALLS - DOCUMENTS_SPARE
    assert route.named_models[0].searched is True
    assert "GW50K-ETA-G20" in _texts(route)


def test_documents_intent_searches_named_models_and_leaves_a_spare(
    vocabulary: Vocabulary,
) -> None:
    subject = replace(_catalog(vocabulary), ids=(2198, 1187, 1185))
    route = plan(
        THREE,
        vocabulary.match(THREE),
        _reading("documents_specs"),
        subject,
        "en",
    )
    assert len(route.calls) <= MAX_TOOL_CALLS - DOCUMENTS_SPARE
    assert [call.ability for call in route.calls][0] == "linker/search-knowledge"
    assert sum(call.ability == "linker/get-product" for call in route.calls) == 2
    assert [note.code for note in route.named_models] == list(HS3)
    assert any(not note.searched for note in route.named_models)
    fetched = {
        call.arguments.get("product_id")
        for call in route.calls
        if call.ability == "linker/get-product"
    }
    for note in route.named_models:
        assert note.searched is bool(set(note.product_ids) & fetched)
    open_subject = _catalog(vocabulary)
    searched = plan(
        THREE,
        vocabulary.match(THREE),
        _reading("documents_specs"),
        open_subject,
        "en",
    )
    assert len(searched.calls) <= MAX_TOOL_CALLS - DOCUMENTS_SPARE
    assert _texts(searched) == list(HS3[:2])
    assert any(call.ability == "linker/search-knowledge" for call in searched.calls)
    assert any(not note.searched for note in searched.named_models)
    for note in searched.named_models:
        assert note.searched is (note.code in _texts(searched))


def test_documents_plan_leaves_a_spare_and_the_page_still_fits(
    vocabulary: Vocabulary,
) -> None:
    message = "Datasheet for the HS3-5K-T2-W/G-PX"
    subject = replace(_catalog(vocabulary), ids=(2198,))
    route = plan(
        message,
        vocabulary.match(message),
        _reading("documents_specs"),
        subject,
        "en",
    )
    assert len(route.calls) <= MAX_TOOL_CALLS - DOCUMENTS_SPARE
    page = PageContext(
        type="product", url="https://de-linker.com/p/hs3", product_id=2198
    )
    paged = with_page(route, page, True, False, subject, message)
    assert any(call.ability == READ_PAGE for call in paged.calls)
    assert len(paged.calls) <= MAX_TOOL_CALLS - DOCUMENTS_SPARE


def test_documents_plus_four_unknown_codes_stays_inside_four_calls(
    vocabulary: Vocabulary,
) -> None:
    codes = [f"GW5{index}K-ETA-G20" for index in range(1, 5)]
    message = "Datasheets for " + " ".join(codes)
    route = plan(
        message,
        vocabulary.match(message),
        _reading("documents_specs"),
        _catalog(vocabulary),
        "en",
    )
    assert len(route.calls) <= MAX_TOOL_CALLS - DOCUMENTS_SPARE
    assert [note.code for note in route.named_models] == codes
    assert any(not note.searched for note in route.named_models)
    for note in route.named_models:
        assert note.searched is (note.code in _texts(route))


@pytest.mark.parametrize(
    "message",
    ["Order ABC-123-456 status?", "DLK-2026-001 status?", "ORDER-2026-G20 status?"],
)
def test_an_order_or_shop_code_is_not_a_model(
    vocabulary: Vocabulary, message: str
) -> None:
    route = plan(
        message,
        vocabulary.match(message),
        _reading("other", 0.95),
        _catalog(vocabulary),
        "en",
    )
    assert route.named_models == ()
    assert route.calls == ()
    assert "not in our product range" not in route.hint


def test_absence_claims_fail_outside_the_code_clause() -> None:
    notes = tuple(
        NamedModel(code=code, product_ids=(pid,), searched=True)
        for code, pid in zip(HS3[:2], (2198, 1187), strict=True)
    )
    route = Route("products", show_products=True, no_handoff=True, named_models=notes)
    facts = _facts(2198, 1187)
    elsewhere = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "HS3-5K-T2-W/G-PX and HS3-8K-T2-W/G-PX are both listed. "
                    "These two model codes return no entry in our product data."
                ),
                refs=["2198", "1187"],
            ),
            CardsBlock(product_ids=[2198, 1187]),
        ],
    )
    refused = check(elsewhere, facts, route)
    assert not refused.ok
    assert any("HS3-5K-T2-W/G-PX" in failure for failure in refused.failures)
    assert any("HS3-8K-T2-W/G-PX" in failure for failure in refused.failures)
    unsearched = NamedModel(code="GW50K-ETA-G20", unknown=True, searched=False)
    pending = Route(
        "products", show_products=True, no_handoff=True, named_models=(unsearched,)
    )
    pronoun = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="GW50K-ETA-G20 is on the label. It is not in our product range."
            )
        ],
    )
    pronoun_de = TurnOutput(
        language="de",
        blocks=[
            TextBlock(
                text=(
                    "GW50K-ETA-G20 steht auf dem Typenschild. "
                    "Es ist nicht in unserem Sortiment."
                )
            )
        ],
    )
    for output in (pronoun, pronoun_de):
        result = check(output, _facts(searched=True), pending)
        assert any("not that it is absent" in failure for failure in result.failures)
    conflict = NamedModel(
        code="GW10K-ETA-G20",
        product_ids=(3556,),
        searched=True,
        written_brand="SAJ",
        catalog_brand="GoodWe",
    )
    branded = Route(
        "products", show_products=True, no_handoff=True, named_models=(conflict,)
    )
    exempted = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="GW10K-ETA-G20 is not in our product range. GoodWe may help.",
                refs=["3556"],
            ),
            CardsBlock(product_ids=[3556]),
        ],
    )
    brand_result = check(exempted, _facts(3556), branded)
    assert not brand_result.ok
    assert any("GoodWe" in failure for failure in brand_result.failures)


def test_an_ability_failure_is_not_an_empty_catalog() -> None:
    """AbilityError omits the route call. The note stays searched; the answer is degraded."""
    unknown = Route(
        "products",
        show_products=True,
        no_handoff=True,
        named_models=(NamedModel(code="GW50K-ETA-G20", unknown=True, searched=True),),
    )
    several_models = Route(
        "products",
        show_products=True,
        no_handoff=True,
        named_models=tuple(
            NamedModel(code=code, product_ids=(pid,), searched=True)
            for code, pid in zip(HS3, (2198, 1187, 1185), strict=True)
        ),
    )
    for route in (unknown, several_models):
        for lang in ("en", "de"):
            output = fallback(TurnFacts(), lang, route)
            assert isinstance(output.blocks[0], HandoffBlock)
            assert output.blocks[0].summary == DEGRADED[lang]
            summary = output.blocks[0].summary
            assert "not in our product range" not in summary
            assert "did not return" not in summary
            assert "kein Produkt" not in summary
            assert "nicht in unserem Sortiment" not in summary
    refused = check(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="GW50K-ETA-G20 is not in our product range."),
            ],
        ),
        TurnFacts(),
        unknown,
    )
    assert not refused.ok
    assert any("did not succeed" in failure for failure in refused.failures)


def test_the_page_hint_drops_a_model_from_the_searched_list() -> None:
    from linker_genie.route import _model_hint

    notes = tuple(
        NamedModel(code=code)
        for code in ("A-10K-T2", "B-10K-T2", "C-10K-T2", "D-10K-T2")
    )
    calls = tuple(
        Call("linker/search-products", {"text": note.code, "lang": "en", "limit": 6})
        for note in notes
    )
    route = Route(
        "documents",
        calls,
        no_handoff=True,
        named_models=notes,
        hint="Answer from the documents." + _model_hint(notes),
    )
    page = PageContext(type="product", url="https://de-linker.com/p", product_id=1)
    result = with_page(route, page, True, False, Subject((), {}, {}), "the page")
    assert result.named_models[-1].searched is False
    assert "Not searched this turn: D-10K-T2" in result.hint
    assert "D-10K-T2" not in result.hint.split("Not searched this turn")[0]


@pytest.mark.parametrize(
    "text",
    [
        "HS3-5K-T2-W/G-PX: keinen Eintrag.",
        "HS3-5K-T2-W/G-PX ist nicht in den Produktdaten.",
        "HS3-5K-T2-W/G-PX gibt es bei uns nicht.",
        "HS3-5K-T2-W/G-PX führen wir nicht.",
        "Für HS3-5K-T2-W/G-PX haben wir keine Produkte.",
        "HS3-5K-T2-W/G-PX ist nicht verfügbar.",
        "We don't carry HS3-5K-T2-W/G-PX.",
        "We don't stock HS3-5K-T2-W/G-PX.",
        "HS3-5K-T2-W/G-PX is not available.",
    ],
)
def test_absence_forms_fail_when_the_search_returned_the_product(text: str) -> None:
    note = NamedModel(code=HS3[0], product_ids=(2198,), searched=True)
    route = Route("products", show_products=True, no_handoff=True, named_models=(note,))
    facts = _facts_for([_search_result(HS3[0], 2198)], 2198)
    output = TurnOutput(
        language="de" if "HS3" in text and "We " not in text else "en",
        blocks=[
            TextBlock(text=text, refs=["2198"]),
            CardsBlock(product_ids=[2198]),
        ],
    )
    result = check(output, facts, route)
    assert not result.ok
    assert any(HS3[0] in failure for failure in result.failures)


def test_an_empty_search_may_say_the_code_is_absent() -> None:
    note = NamedModel(code="GW50K-ETA-G20", unknown=True, searched=True)
    route = Route("products", show_products=True, no_handoff=True, named_models=(note,))
    facts = _facts_for([_search_result("GW50K-ETA-G20")])
    output = TurnOutput(
        language="de",
        blocks=[TextBlock(text="Für GW50K-ETA-G20 gibt es keinen Eintrag.")],
    )
    assert check(output, facts, route).ok


def test_a_mixed_turn_uses_the_degraded_sentence_for_the_failed_model() -> None:
    notes = tuple(
        NamedModel(code=code, product_ids=(pid,), searched=True)
        for code, pid in zip(HS3, (2198, 1187, 1185), strict=True)
    )
    route = Route("products", show_products=True, no_handoff=True, named_models=notes)
    # Two searches returned. The third call is absent: AbilityError does not record it.
    calls = [
        _search_result(HS3[0], 2198),
        _search_result(HS3[1], 1187),
    ]
    facts = _facts_for(calls, 2198, 1187)
    for lang in ("en", "de"):
        output = fallback(facts, lang, route)
        text = _sentence(output)
        assert HS3[2] in text
        assert DEGRADED[lang] in text
        assert "did not return" not in text
        assert "not in our product range" not in text
        assert "kein Produkt" not in text
        cards = [block for block in output.blocks if isinstance(block, CardsBlock)]
        assert cards and cards[0].product_ids == [2198, 1187]
        if lang == "de":
            assert german_is_clean(text)
    claim = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    f"{HS3[0]} and {HS3[1]} are listed. "
                    f"{HS3[2]} is not in our product range."
                ),
                refs=["2198", "1187"],
            ),
            CardsBlock(product_ids=[2198, 1187]),
        ],
    )
    refused = check(claim, facts, route)
    assert not refused.ok
    assert any(
        HS3[2] in failure and "did not succeed" in failure
        for failure in refused.failures
    )


def test_a_successful_empty_search_still_says_the_search_did_not_return_it() -> None:
    notes = tuple(
        NamedModel(code=code, product_ids=(pid,), searched=True)
        for code, pid in zip(HS3, (2198, 1187, 1185), strict=True)
    )
    route = Route("products", show_products=True, no_handoff=True, named_models=notes)
    calls = [
        _search_result(HS3[0], 2198),
        _search_result(HS3[1], 1187),
        _search_result(HS3[2]),
    ]
    facts = _facts_for(calls, 2198, 1187)
    output = fallback(facts, "en", route)
    text = _sentence(output)
    assert f"The search did not return {HS3[2]}" in text
    assert DEGRADED["en"] not in text
    assert "not in our product range" not in text


def test_a_later_search_clears_a_page_dropped_model() -> None:
    note = NamedModel(code="GW50K-ETA-G20", unknown=True, searched=False)
    route = Route("documents", no_handoff=True, named_models=(note,))
    facts = _facts_for([_search_result("GW50K-ETA-G20", 3556)], 3556)
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "GW50K-ETA-G20 is not in our product range. "
                    "The closest products are on the cards."
                ),
                refs=["3556"],
            ),
            CardsBlock(product_ids=[3556]),
        ],
    )
    result = check(output, facts, route)
    assert result.ok
    assert not any("not searched" in failure for failure in result.failures)
    rendered = fallback(facts, "en", route)
    assert "was not searched" not in _sentence(rendered)
    assert "not in our product range" in _sentence(rendered)


def test_a_later_get_product_clears_a_budget_block() -> None:
    carried = NamedModel(code=HS3[0], product_ids=(2198,), searched=True)
    blocked = NamedModel(code=HS3[2], product_ids=(1185,), searched=False)
    route = Route(
        "products",
        show_products=True,
        no_handoff=True,
        named_models=(carried, blocked),
    )
    facts = TurnFacts()
    facts.tool_calls.append(_search_result(HS3[0], 2198))
    facts.tool_calls.append(
        {
            "name": "linker/get-product",
            "arguments": {"product_id": 1185, "lang": "en"},
            "ok": True,
            "result": {"product_id": 1185},
        }
    )
    facts.qualified_ids = {2198, 1185}
    facts.product_ids = {2198, 1185}
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=f"{HS3[0]} is listed. {HS3[2]} is listed.",
                refs=["2198", "1185"],
            ),
            CardsBlock(product_ids=[2198, 1185]),
        ],
    )
    result = check(output, facts, route)
    assert result.ok
    assert not any("not searched" in failure for failure in result.failures)
    rendered = fallback(facts, "en", route)
    assert "was not searched" not in _sentence(rendered)


def test_extreme_prompts_search_every_written_code_and_keep_the_winner_card() -> None:
    from linker_genie.agent import instructions

    english = instructions("en")
    german = instructions("de")
    assert "each of those written codes is searched on its own" in english
    assert "is not a separate search" in english
    assert "does not add a card" in english
    assert "für sich gesucht" in german
    assert "keine eigene Suche" in german
    assert "keine weitere Karte" in german


def test_en_and_de_prompts_carry_the_same_three_obligations() -> None:
    from linker_genie.agent import _user_prompt, instructions
    from linker_genie.route import NAMED_MODEL_RULE

    assert NAMED_MODEL_RULE in instructions("en")
    german = instructions("de")
    assert "nicht gesucht" in german and "fehlend" in german
    assert "geschriebene Marke" in german and "Marke aus den Produktdaten" in german
    assert "demselben Satz" in german
    assert "jedes für sich" in german
    request = TurnRequest(
        conversation_id="c-models",
        messages=[TurnMessage(role="user", content=THREE)],
    )
    reminder = _user_prompt(request, None)
    assert NAMED_MODEL_RULE in reminder
    assert "was not searched: say that" not in reminder
