"""Brand/model conflicts, unknown models, and several models in one sentence.

The fixtures are the live store snapshot (tests/fixtures/storeapi.json,
2026-10-15). #363 and #367 are the SAJ/EcoFlow readings of GoodWe models.
#364 is a sentence that names three SAJ HS3 models.
"""

import pytest

from linker_genie.cycle import run
from linker_genie.facts import TurnFacts
from linker_genie.ground import check
from linker_genie.jev import Reading
from linker_genie.lexicon import Match, Vocabulary
from linker_genie.route import Call, NamedModel, Route, Subject, plan, with_page
from linker_genie.schema import (
    CardsBlock,
    HandoffBlock,
    PageContext,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import fallback, german_is_clean
from linker_genie.tools import MAX_TOOL_CALLS

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
            assert "geführt" in text
    assert shapes[0] == shapes[1]


def test_unknown_model_fallback_offers_the_closest_products(
    vocabulary: Vocabulary,
) -> None:
    for message, lang, missing, closest in (
        (UNKNOWN, "en", "not in our product range", "closest products"),
        (UNKNOWN_DE, "de", "nicht in unserem Sortiment", "nächsten Produkte"),
    ):
        route = _route(vocabulary, message, lang)
        found = fallback(_facts(3556), lang, route)
        text = _sentence(found)
        assert "GW50K-ETA-G20" in text and missing in text and closest in text
        assert any(isinstance(block, CardsBlock) for block in found.blocks)
        assert not any(isinstance(block, HandoffBlock) for block in found.blocks)
        if lang == "de":
            assert german_is_clean(text)
        empty = fallback(TurnFacts(), lang, route)
        assert missing in _sentence(empty)
        assert any(block.type == "ask" for block in empty.blocks)
        assert not any(isinstance(block, HandoffBlock) for block in empty.blocks)


def test_an_empty_product_search_clarifies_and_an_outage_does_not() -> None:
    route = Route("products", no_handoff=True, show_products=True)
    found = fallback(_facts(searched=True), "en", route)
    assert _sentence(found) == "No product matched that search."
    assert [block.type for block in found.blocks] == ["text", "ask"]
    german = fallback(_facts(searched=True), "de", route)
    assert _sentence(german) == "Zu dieser Suche gibt es kein Produkt."
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
    named = TurnOutput(
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
    assert check(named, facts, route).ok


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
