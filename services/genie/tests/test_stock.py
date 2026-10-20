"""Stock-status questions (#415).

The nine-case matrix lives in eval/regression/339-product-words.jsonl
(kind "stock") and runs from test_regression_339.py. These tests are the
edges around that matrix: what is not a stock question, a missing product,
mixed flags, compound questions, and the grounding net.
"""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import Request

from linker_genie.app import _answer
from linker_genie.facts import Fact, TurnFacts, collect, merge, stock_rows
from linker_genie.ground import check
from linker_genie.jev import Reading
from linker_genie.lexicon import Vocabulary
from linker_genie.prices import Lookup
from linker_genie.route import (
    Route,
    Subject,
    plan,
    simple_stock,
    with_page,
)
from linker_genie.schema import (
    CardsBlock,
    HandoffBlock,
    Locale,
    PageContext,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.stock import asks, phrase
from linker_genie.template import DEGRADED, fallback, german_is_clean, stock_answer
from linker_genie.understand import Prepared


def _reading(intent: str, confidence: float = 0.95) -> Reading:
    return Reading(intent, confidence, 0.1, 0.05, 0.2, 2.6, 0.0)  # type: ignore[arg-type]


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


def _commerce(in_stock: bool, lang: str = "en") -> dict[str, object]:
    line = (
        "Nettopreis nach Partner-Anmeldung"
        if lang.startswith("de")
        else "Net price after partner sign-in"
    )
    return {
        "price_visible": False,
        "in_stock": in_stock,
        "price_line": line,
        "price_reason": "login",
    }


def _row(product_id: int, in_stock: bool, lang: str = "en") -> dict[str, object]:
    """A published product row: title, URL and SKU, not the price line."""
    return {
        "product_id": product_id,
        "title": f"Product {product_id}",
        "url": f"https://de-linker.com/product/{product_id}/",
        "sku": f"SKU-{product_id}",
        "facts": {},
        "commerce": _commerce(in_stock, lang),
    }


@pytest.mark.parametrize("confidence", [0.95, 0.4])
def test_a_stock_question_is_not_handed_to_the_team(
    vocabulary: Vocabulary, confidence: float
) -> None:
    for message, lang in (
        ("Is the SAJ H2-10K-T3 in stock right now?", "en"),
        ("Ist der SAJ H2-10K-T3 gerade auf Lager?", "de"),
        # A full stop inside a model code is not a sentence boundary: the
        # whole question is still only about stock.
        ("Is the GoodWe GW99.99K-ET-G10 in stock?", "en"),
        ("Ist der GoodWe GW99.99K-ET-G10 auf Lager?", "de"),
    ):
        route = plan(
            message,
            vocabulary.match(message),
            _reading("company_logistics_service", confidence),
            _catalog(vocabulary),
            lang,
        )
        assert route.name == "products"
        assert route.stock is True
        assert route.no_handoff is True
        assert route.show_products is True
        assert simple_stock(route) is True
        assert any(call.ability == "linker/search-products" for call in route.calls)
        assert all(call.ability != "linker/handoff-team" for call in route.calls)
        assert "stock status" in route.reasons


def test_a_delivery_question_stays_with_the_team() -> None:
    route = plan(
        "Liefern Sie nach Österreich?",
        [],
        _reading("company_logistics_service"),
        Subject((), {}, {}),
        "de",
    )
    assert route.name == "service"
    assert route.stock is False
    assert route.calls[0].ability == "linker/handoff-team"


@pytest.mark.parametrize(
    ("message", "lang"),
    [
        ("Is the SAJ H2-35K-T3 available?", "en"),
        ("Ist der SAJ H2-35K-T3 verfügbar?", "de"),
        ("Ist der SAJ H2-35K-T3 nicht verfügbar?", "de"),
    ],
)
def test_available_names_a_product_and_is_a_stock_question(
    vocabulary: Vocabulary, message: str, lang: str
) -> None:
    route = plan(
        message,
        vocabulary.match(message),
        _reading("company_logistics_service"),
        _catalog(vocabulary),
        lang,
    )
    assert route.name == "products"
    assert route.stock is True
    assert route.no_handoff is True
    assert route.delivery is False
    assert any(call.ability == "linker/search-products" for call in route.calls)
    assert all(call.ability != "linker/handoff-team" for call in route.calls)


def test_available_without_a_product_stays_off_the_stock_route(
    vocabulary: Vocabulary,
) -> None:
    for message, reading in (
        ("Is 3-phase available?", _reading("company_logistics_service")),
        ("Is 3-phase available?", _reading("find_products")),
        ("Is 3-phase unavailable?", _reading("company_logistics_service")),
    ):
        route = plan(
            message,
            vocabulary.match(message),
            reading,
            _catalog(vocabulary),
            "en",
        )
        assert route.stock is False
    handed = plan(
        "Is 3-phase available?",
        vocabulary.match("Is 3-phase available?"),
        _reading("company_logistics_service"),
        _catalog(vocabulary),
        "en",
    )
    assert handed.name == "service"
    assert handed.calls[0].ability == "linker/handoff-team"
    # The page's product id alone does not make this a stock question: a
    # specification is not a status (#415 review round 3). A pointer at the
    # page's product is.
    page_product = replace(_catalog(vocabulary), ids=(4107,))
    paged = plan(
        "Is 3-phase available?",
        vocabulary.match("Is 3-phase available?"),
        _reading("company_logistics_service"),
        page_product,
        "en",
    )
    assert paged.stock is False
    assert paged.stock_beside is False
    pointer = plan(
        "Is it available?",
        vocabulary.match("Is it available?"),
        _reading("company_logistics_service"),
        page_product,
        "en",
    )
    assert pointer.stock is True
    assert pointer.stock_beside is False


@pytest.mark.parametrize(
    ("message", "lang"),
    [
        ("What is the stock status of the SAJ H2-10K-T3?", "en"),
        ("Wie ist der Lagerstatus des SAJ H2-10K-T3?", "de"),
        ("Is the SAJ H2-10K-T3 unavailable?", "en"),
        ("Ist der SAJ H2-10K-T3 ausverkauft?", "de"),
        ("Für welches Produkt soll ich den Lagerstatus prüfen?", "de"),
    ],
)
def test_status_synonyms_are_not_handed_to_the_team(
    vocabulary: Vocabulary, message: str, lang: str
) -> None:
    """Jev files these as company logistics. They stay a stock question.

    "Lagerstatus" is the deciding sentence's own word. A customer who
    answers with it must not fall through to service().
    """
    assert asks(message) is True
    route = plan(
        message,
        vocabulary.match(message),
        _reading("company_logistics_service"),
        _catalog(vocabulary),
        lang,
    )
    assert route.name == "products"
    assert route.stock is True
    assert all(call.ability != "linker/handoff-team" for call in route.calls)


def test_delivery_words_are_not_stock_asks() -> None:
    for message in (
        "Ist der GoodWe ET lieferbar?",
        "Liefern Sie nach Österreich?",
        "What is the delivery cost?",
        "What is the shipping status?",
    ):
        assert asks(message) is False


def test_ausverkauft_without_a_product_stays_with_the_team(
    vocabulary: Vocabulary,
) -> None:
    message = "Ist das ausverkauft?"
    route = plan(
        message,
        vocabulary.match(message),
        _reading("company_logistics_service"),
        _catalog(vocabulary),
        "de",
    )
    assert route.stock is False
    assert route.name == "service"
    assert route.calls[0].ability == "linker/handoff-team"


def test_a_document_question_that_says_in_stock_stays_a_document_question(
    vocabulary: Vocabulary,
) -> None:
    message = "Do you have the GW50K-ETA-G20 in stock?"
    route = plan(
        message,
        vocabulary.match(message),
        _reading("documents_specs"),
        _catalog(vocabulary),
        "en",
    )
    assert route.name == "documents"
    assert route.stock is False


def test_a_stock_question_on_a_page_is_not_rewritten_into_delivery(
    vocabulary: Vocabulary,
) -> None:
    message = "Is the SAJ H2-10K-T3 in stock right now?"
    catalog = _catalog(vocabulary)
    route = plan(
        message,
        vocabulary.match(message),
        _reading("company_logistics_service"),
        catalog,
        "en",
    )
    assert route.stock is True
    paged = with_page(
        route,
        PageContext(
            type="product",
            url="https://de-linker.com/product/saj-h2-10k-t3/",
            product_id=4107,
        ),
        True,
        False,
        catalog,
        message,
    )
    assert paged.name == "products"
    assert paged.stock is True
    assert paged.delivery is False
    assert all(call.ability != "linker/handoff-team" for call in paged.calls)


def test_a_missing_product_is_not_reported_out_of_stock() -> None:
    facts = collect(
        "linker/get-product",
        {
            "product_id": 4107,
            "commerce": {
                "price_visible": False,
                "in_stock": False,
                "rfq_only": False,
            },
        },
        "en",
    )
    assert "p4107.stock" not in facts.facts
    assert stock_rows(facts) is None
    output = fallback(
        facts,
        "en",
        Route("products", stock=True, no_handoff=True, show_products=True),
    )
    assert isinstance(output.blocks[0], HandoffBlock)
    assert output.blocks[0].summary == DEGRADED["en"]
    assert not any(isinstance(block, CardsBlock) for block in output.blocks)


def test_stock_follows_the_product_not_the_price_line() -> None:
    """A title, URL or SKU marks a product. A price line does not."""
    real = collect(
        "linker/get-product",
        {
            "product_id": 4107,
            "title": "SAJ H2-10K-T3",
            "url": "https://de-linker.com/product/saj-h2-10k-t3/",
            "sku": "DLK-SAJ-H210KT3",
            "commerce": {
                "price_visible": False,
                "in_stock": False,
                "rfq_only": False,
            },
        },
        "en",
    )
    assert stock_rows(real) == [(4107, False)]
    assert real.facts["p4107.stock"].value == phrase("en", False)
    priced_only = collect(
        "linker/get-product",
        {
            "product_id": 4107,
            "title": "",
            "url": "",
            "sku": "",
            "commerce": {
                "price_visible": False,
                "in_stock": False,
                "rfq_only": False,
                "price_line": "Net price after partner sign-in",
            },
        },
        "en",
    )
    assert "p4107.stock" not in priced_only.facts
    assert stock_rows(priced_only) is None


def test_mixed_statuses_name_each_status() -> None:
    facts = collect(
        "linker/search-products",
        {
            "qualified": [
                _row(4107, True),
                _row(3556, False),
            ]
        },
        "en",
    )
    output = stock_answer(facts, "en")
    assert output is not None
    text = " ".join(
        block.text for block in output.blocks if isinstance(block, TextBlock)
    )
    assert phrase("en", True).casefold() in text.casefold()
    assert phrase("en", False).casefold() in text.casefold()
    cards = [block for block in output.blocks if isinstance(block, CardsBlock)]
    assert [card.product_ids for card in cards] == [[3556, 4107]]
    rendered = fallback(
        facts,
        "en",
        Route("products", stock=True, no_handoff=True, show_products=True),
    )
    rendered_text = " ".join(
        block.text for block in rendered.blocks if isinstance(block, TextBlock)
    )
    assert "matching products" not in rendered_text.casefold()
    assert phrase("en", True).casefold() in rendered_text.casefold()
    assert phrase("en", False).casefold() in rendered_text.casefold()
    german = stock_answer(facts, "de")
    assert german is not None
    german_text = german.blocks[0]
    assert isinstance(german_text, TextBlock)
    assert german_is_clean(german_text.text)


def test_grounding_accepts_the_status_and_refuses_a_quantity(
    vocabulary: Vocabulary,
) -> None:
    message = "Is the SAJ H2-10K-T3 in stock right now?"
    route = plan(
        message,
        vocabulary.match(message),
        _reading("company_logistics_service"),
        _catalog(vocabulary),
        "de",
    )
    facts = collect(
        "linker/search-products",
        {"qualified": [_row(4107, False)]},
        "de",
    )
    facts.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {"text": "H2-10K-T3", "lang": "de", "limit": 6},
            "ok": True,
            "result": {},
        }
    )
    answered = stock_answer(facts, "de")
    assert answered is not None
    assert check(answered, facts, route).ok
    counted = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="12 units in stock", refs=["p4107.stock"]),
            CardsBlock(product_ids=[4107]),
        ],
    )
    refused = check(counted, facts, route)
    assert refused.ok is False
    assert any("quantity" in failure for failure in refused.failures)


class _Model:
    """A generator that fails the test if a service-written stock turn calls it."""

    def __call__(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("the model ran on a stock-status question")


class _Request:
    class app:
        class state:
            generate = _Model()


def _turn(message: str, lang: Locale) -> TurnRequest:
    return TurnRequest(
        conversation_id="415",
        messages=[TurnMessage(role="user", content=message)],
        locale=lang,
    )


def _http() -> Request[Any]:
    return cast(Request[Any], _Request())


def _search(product_id: int, in_stock: bool, lang: str) -> TurnFacts:
    return collect(
        "linker/search-products",
        {"qualified": [_row(product_id, in_stock)]},
        lang,
    )


def _team(lang: str) -> TurnFacts:
    return collect(
        "linker/handoff-team",
        {
            "sentence_en": "Our team will answer that at sales@de-linker.com.",
            "sentence_de": "Unser Team beantwortet das unter sales@de-linker.com.",
            "mailto": "mailto:sales@de-linker.com",
        },
        lang,
    )


@pytest.mark.parametrize(
    ("message", "lang", "question"),
    [
        (
            "What do you have in stock?",
            "en",
            "Which product should I check the stock for?",
        ),
        (
            "Welche Produkte sind auf Lager?",
            "de",
            "Für welches Produkt soll ich den Lagerstatus prüfen?",
        ),
    ],
)
def test_a_stock_question_with_no_product_asks_which_one(
    vocabulary: Vocabulary, message: str, lang: Locale, question: str
) -> None:
    route = plan(
        message,
        vocabulary.match(message),
        _reading("company_logistics_service"),
        _catalog(vocabulary),
        lang,
    )
    assert route.name == "products"
    assert route.stock is True
    assert route.calls == ()
    assert route.answer == question
    assert route.no_cards is True
    assert simple_stock(route) is True
    result, block = _answer(
        _turn(message, lang),
        Prepared(route=route),
        _http(),
        cast(Lookup, None),
    )
    assert block is None
    assert result.attempts == 0
    assert result.grounded is True
    assert result.fallback is False
    assert result.failures == ()
    assert isinstance(result.output.blocks[0], TextBlock)
    assert result.output.blocks[0].text == question
    assert result.output.blocks[0].text != DEGRADED[lang]
    if lang == "de":
        assert german_is_clean(question)


def test_lieferbar_stays_a_delivery_question(vocabulary: Vocabulary) -> None:
    message = "Ist der GoodWe ET lieferbar?"
    route = plan(
        message,
        vocabulary.match(message),
        _reading("company_logistics_service"),
        _catalog(vocabulary),
        "de",
    )
    assert route.name == "service"
    assert route.stock is False
    assert route.calls[0].ability == "linker/handoff-team"
    paged = with_page(
        plan(
            message,
            vocabulary.match(message),
            _reading("find_products"),
            _catalog(vocabulary),
            "de",
        ),
        PageContext(
            type="product",
            url="https://de-linker.com/product/goodwe-et/",
            product_id=3556,
        ),
        True,
        False,
        _catalog(vocabulary),
        message,
    )
    assert paged.name == "service"
    assert paged.stock is False
    assert paged.calls[0].ability == "linker/handoff-team"


@pytest.mark.parametrize(
    ("message", "lang"),
    [
        (
            "Is the SAJ H2-10K-T3 in stock right now? What is the delivery cost?",
            "en",
        ),
        (
            "Ist der SAJ H2-10K-T3 auf Lager, und was kostet die Lieferung?",
            "de",
        ),
    ],
)
def test_stock_and_delivery_answers_stock_and_hands_delivery_to_the_team(
    vocabulary: Vocabulary, message: str, lang: Locale
) -> None:
    catalog = _catalog(vocabulary)
    route = plan(
        message,
        vocabulary.match(message),
        _reading("company_logistics_service"),
        catalog,
        lang,
    )
    assert route.name == "products"
    assert route.stock is True
    assert route.delivery is True
    assert route.no_handoff is False
    assert any(call.ability == "linker/search-products" for call in route.calls)
    assert any(call.ability == "linker/handoff-team" for call in route.calls)
    paged = with_page(
        route,
        PageContext(
            type="product",
            url="https://de-linker.com/product/saj-h2-10k-t3/",
            product_id=4107,
        ),
        True,
        False,
        catalog,
        message,
    )
    assert paged.name == "products"
    assert paged.stock is True
    assert paged.delivery is True
    assert any(call.ability == "linker/handoff-team" for call in paged.calls)
    facts = merge([_search(4107, True, lang), _team(lang)])
    facts.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {"text": "H2-10K-T3", "lang": lang, "limit": 6},
            "ok": True,
            "result": {},
        }
    )
    result, block = _answer(
        _turn(message, lang),
        Prepared(route=route, facts=facts),
        _http(),
        cast(Lookup, None),
    )
    assert block is None
    assert result.attempts == 0
    assert result.grounded is True
    assert result.fallback is False
    assert result.failures == ()
    text = " ".join(
        item.text for item in result.output.blocks if isinstance(item, TextBlock)
    )
    assert text == phrase(lang, True)
    assert any(isinstance(item, CardsBlock) for item in result.output.blocks)
    handed = [item for item in result.output.blocks if isinstance(item, HandoffBlock)]
    assert len(handed) == 1
    assert "sales@de-linker.com" in handed[0].summary
    assert check(result.output, result.facts, route).ok
    bare = check(
        result.output,
        result.facts,
        Route("service", no_handoff=False),
    )
    assert bare.ok is False
    assert any("handoff" in failure for failure in bare.failures)


class _BothHalves:
    """A model that answers the other half and states the status (#415)."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        self.calls = 0

    def __call__(
        self, request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        self.calls += 1
        return (
            TurnOutput(
                language="de" if request.locale.startswith("de") else "en",
                blocks=[
                    TextBlock(
                        text=f"{{fact:{self.detail}}} {{fact:p4107.stock}}",
                        refs=["4107"],
                    ),
                    CardsBlock(product_ids=[4107]),
                ],
            ),
            TurnFacts(),
        )


def _request_with(generate: Any) -> Request[Any]:
    state = SimpleNamespace(generate=generate)
    return cast(Request[Any], SimpleNamespace(app=SimpleNamespace(state=state)))


@pytest.mark.parametrize(
    ("message", "lang", "detail_id", "detail_value"),
    [
        (
            "What is the efficiency of the SAJ H2-10K-T3 and is it in stock?",
            "en",
            "p4107.efficiency",
            "97.5 %",
        ),
        (
            "Wie hoch ist der Wirkungsgrad des SAJ H2-10K-T3 und ist er auf Lager?",
            "de",
            "p4107.efficiency",
            "97,5 %",
        ),
        (
            "Is the SAJ H2-10K-T3 in stock? Can you send me the datasheet?",
            "en",
            "p4107.document",
            "Datasheet",
        ),
        (
            "Is the SAJ H2-10K-T3 in stock. Can you send me the datasheet?",
            "en",
            "p4107.document",
            "Datasheet",
        ),
        (
            "Ist der SAJ H2-10K-T3 auf Lager? Können Sie mir das Datenblatt senden?",
            "de",
            "p4107.document",
            "Datenblatt",
        ),
    ],
)
def test_a_compound_question_keeps_its_other_half(
    vocabulary: Vocabulary,
    message: str,
    lang: Locale,
    detail_id: str,
    detail_value: str,
) -> None:
    """The stock status is one part of the answer, not the whole answer.

    The review's probes: "What is the efficiency of the SAJ H2-10K-T3 and is
    it in stock?" and "... in stock? Can you send me the datasheet?". The
    deterministic status sentence dropped the other half; the model now
    answers the whole message with the status beside it.
    """
    route = plan(
        message,
        vocabulary.match(message),
        _reading("company_logistics_service"),
        _catalog(vocabulary),
        lang,
    )
    assert route.name == "products"
    assert route.stock is True
    assert route.stock_beside is True
    assert simple_stock(route) is False
    assert route.answer == ""
    assert "asks something else" in route.hint
    facts = collect(
        "linker/search-products",
        {"qualified": [_row(4107, True, lang)]},
        lang,
    )
    facts.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {"text": "H2-10K-T3", "lang": lang, "limit": 6},
            "ok": True,
            "result": {},
        }
    )
    facts.add(Fact(id=detail_id, value=detail_value, source="search-products"))
    model = _BothHalves(detail_id)
    result, block = _answer(
        _turn(message, lang),
        Prepared(route=route, facts=facts),
        _request_with(model),
        cast(Lookup, None),
    )
    assert block is None
    assert model.calls == 1, result.retried
    assert result.attempts == 1
    assert result.grounded is True
    assert result.fallback is False
    text = " ".join(
        item.text for item in result.output.blocks if isinstance(item, TextBlock)
    )
    assert phrase(lang, True) in text
    assert detail_value in text
    assert any(isinstance(item, CardsBlock) for item in result.output.blocks)


def test_an_empty_stock_search_is_degraded_not_no_match(
    vocabulary: Vocabulary,
) -> None:
    """A stock search that succeeded and found nothing is the degraded sentence.

    "No product matched." is the product-search shape. A stock question has
    no status to state without a product, so the turn is DEGRADED (#415
    review round 3, blocker 3).
    """
    message = "Is the SAJ H2-10K-T3 available?"
    route = plan(
        message,
        vocabulary.match(message),
        _reading("company_logistics_service"),
        _catalog(vocabulary),
        "en",
    )
    assert route.stock is True
    assert simple_stock(route) is True
    facts = collect("linker/search-products", {"qualified": []}, "en")
    facts.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {"text": "H2-10K-T3", "lang": "en", "limit": 6},
            "ok": True,
            "result": {},
        }
    )
    result, block = _answer(
        _turn(message, "en"),
        Prepared(route=route, facts=facts),
        _http(),
        cast(Lookup, None),
    )
    assert block is None
    assert result.attempts == 0
    assert result.grounded is False
    assert result.fallback is True
    assert result.failures == ("stock status unavailable",)
    assert isinstance(result.output.blocks[0], HandoffBlock)
    assert result.output.blocks[0].summary == DEGRADED["en"]
    assert "No product matched." not in result.output.blocks[0].summary
    assert not any(isinstance(item, CardsBlock) for item in result.output.blocks)


def test_a_missing_delivery_sentence_is_a_recorded_failure() -> None:
    facts = _search(4107, False, "en")
    route = Route(
        "products",
        stock=True,
        delivery=True,
        no_handoff=False,
        show_products=True,
    )
    result, _block = _answer(
        _turn("Is the SAJ H2-10K-T3 in stock? What is the delivery cost?", "en"),
        Prepared(route=route, facts=facts),
        _http(),
        cast(Lookup, None),
    )
    assert result.attempts == 0
    assert result.grounded is False
    assert result.fallback is False
    assert result.failures == ("delivery not handed to the team",)
    text = " ".join(
        item.text for item in result.output.blocks if isinstance(item, TextBlock)
    )
    assert text == phrase("en", False)
    assert text != DEGRADED["en"]
    assert not any(isinstance(item, HandoffBlock) for item in result.output.blocks)


def test_mixed_status_is_grounded_only_when_each_status_is_stated() -> None:
    facts = collect(
        "linker/search-products",
        {
            "qualified": [
                _row(4107, True),
                _row(3556, False),
            ]
        },
        "en",
    )
    route = Route("products", stock=True, no_handoff=True, show_products=True)
    named = stock_answer(facts, "en")
    assert named is not None
    assert check(named, facts, route).ok
    blanket = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="In stock", refs=["p3556.stock", "p4107.stock"]),
            CardsBlock(product_ids=[3556, 4107]),
        ],
    )
    refused = check(blanket, facts, route)
    assert refused.ok is False
    assert any(
        failure == "products differ: state each product's status, or none"
        for failure in refused.failures
    )
    omitted = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="Here are the two products.",
                refs=["p3556.stock", "p4107.stock"],
            ),
            CardsBlock(product_ids=[3556, 4107]),
        ],
    )
    assert check(omitted, facts, route).ok


def test_the_route_log_always_names_stock() -> None:
    plain = Route("products").as_log()
    assert plain["stock"] is False
    assert "delivery" not in plain
    assert "stock_beside" not in plain
    assert "show_products" in plain and "no_handoff" in plain
    marked = Route("products", stock=True, delivery=True).as_log()
    assert marked["stock"] is True
    assert marked["delivery"] is True
    beside = Route("products", stock=True, stock_beside=True).as_log()
    assert beside["stock_beside"] is True
