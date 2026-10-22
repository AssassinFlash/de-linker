"""Native product/document language recovery fixtures; no customer traces (#563)."""

import pytest

from linker_genie.cycle import run
from linker_genie.facts import TurnFacts, collect, merge
from linker_genie.jev import Reading
from linker_genie.knowledge import KnowledgeUnavailable
from linker_genie.lexicon import Match
from linker_genie.route import Subject, plan
from linker_genie.schema import (
    CardsBlock,
    DocumentBlock,
    HandoffBlock,
    Locale,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
    UserContext,
)
from linker_genie.template import DEGRADED, fallback


def test_empty_documents_do_not_add_cards_through_multi_model_clarification() -> None:
    route = plan(
        "Show me datasheets for the B2-10.0-HV1 and B2-15.0-HV1 products.",
        [
            Match("model", code, code, frozenset({pid}), code)
            for code, pid in [("B2-10.0-HV1", 2067), ("B2-15.0-HV1", 2068)]
        ],
        Reading("documents_specs", 0.52, 0.1, 0.05, 0.2, 0.0, 0.0),
        Subject(
            (2067, 2068),
            {2067: "home-storage", 2068: "home-storage"},
            {2067: "B2-10.0-HV1", 2068: "B2-15.0-HV1"},
        ),
        "en",
    )
    assert route.name == "documents" and not route.show_products
    facts = collect("linker/search-products", {"qualified": [{"product_id": 2067}]})
    output = fallback(facts, "en", route)
    assert not any(isinstance(block, CardsBlock) for block in output.blocks)


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("qualified", [False, True])
@pytest.mark.parametrize("fatal", [False, True])
@pytest.mark.parametrize(
    "kind", ["product-and-document", "document-only", "negated", "quoted"]
)
def test_empty_documents_fallback_keeps_only_requested_qualified_cards(
    locale: Locale, qualified: bool, fatal: bool, kind: str
) -> None:
    questions = {
        "en": {
            "product-and-document": "Show me the SAJ B2-10.0-HV1 product and its datasheet.",
            "document-only": "Show me the datasheet for this product B2-10.0-HV1.",
            "negated": "Do not show the B2-10.0-HV1 product, only its datasheet.",
            "quoted": 'Explain "show me the product and its datasheet" for B2-10.0-HV1.',
        },
        "de": {
            "product-and-document": "Zeigen Sie mir das Produkt SAJ B2-10.0-HV1 und sein Datenblatt.",
            "document-only": "Zeigen Sie mir das Datenblatt für das Produkt B2-10.0-HV1.",
            "negated": "Zeigen Sie mir nicht das Produkt B2-10.0-HV1, nur sein Datenblatt.",
            "quoted": 'Erklären Sie "Zeigen Sie mir das Produkt und sein Datenblatt" für B2-10.0-HV1.',
        },
    }
    route = plan(
        questions[locale][kind],
        [
            Match(
                "model", "B2-10.0-HV1", "B2-10.0-HV1", frozenset({2067}), "B2-10.0-HV1"
            )
        ],
        Reading("documents_specs", 0.52, 0.1, 0.05, 0.2, 0.0, 0.0),
        Subject((2067,), {2067: "home-storage"}, {2067: "B2-10.0-HV1"}),
        locale,
    )
    assert route.name == "documents"
    assert route.show_products is (kind == "product-and-document")
    facts = merge(
        [
            collect("linker/search-knowledge", {"hits": []}, locale),
            collect(
                "linker/search-products", {"qualified": [{"product_id": 2067}]}, locale
            )
            if qualified
            else collect("linker/get-product", {"product_id": 2067}, locale),
        ]
    )
    assert facts.product_ids == {2067}
    assert not facts.documents

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        if fatal:
            raise KnowledgeUnavailable("Synthetic empty-index failure")
        # Two rejected native attempts reach the ordinary fallback.
        return TurnOutput(
            language="en" if locale == "de" else "de",
            blocks=[TextBlock(text="Synthetic rejected draft.")],
        ), TurnFacts()

    result = run(
        TurnRequest(
            conversation_id="synthetic-563-empty",
            locale=locale,
            messages=[TurnMessage(role="user", content=questions[locale][kind])],
        ),
        generate,
        route,
        seed=facts,
    )
    assert result.fallback
    assert result.attempts == 2
    output = result.output
    expected = [[2067]] if qualified and kind == "product-and-document" else []
    assert [
        block.product_ids for block in output.blocks if isinstance(block, CardsBlock)
    ] == expected
    assert not any(isinstance(block, DocumentBlock) for block in output.blocks)
    lead = output.blocks[0]
    if fatal or not expected:
        assert isinstance(lead, HandoffBlock)
        assert lead.summary == DEGRADED[locale]
    else:
        assert isinstance(lead, TextBlock)
        assert lead.text == (
            "Hier sind passende Produkte aus unserem Sortiment."
            if locale == "de"
            else "Here are matching products from our range."
        )


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("state", ["approved", "guest", "pending", "restricted"])
@pytest.mark.parametrize("language_miss", [False, True])
def test_normal_documents_keep_qualified_card_documents_and_account_price(
    locale: Locale, state: str, language_miss: bool
) -> None:
    question = (
        "Zeigen Sie mir das Produkt SAJ B2-10.0-HV1 und sein Datenblatt."
        if locale == "de"
        else "Show me the SAJ B2-10.0-HV1 product and its datasheet."
    )
    route = plan(
        question,
        [
            Match(
                "model", "B2-10.0-HV1", "B2-10.0-HV1", frozenset({2067}), "B2-10.0-HV1"
            )
        ],
        Reading("documents_specs", 0.52, 0.1, 0.05, 0.2, 0.0, 0.0),
        Subject((2067,), {2067: "home-storage"}, {2067: "B2-10.0-HV1"}),
        locale,
    )
    reason = {
        "approved": None,
        "guest": "login",
        "pending": "pending",
        "restricted": "restricted",
    }[state]
    # The price is synthetic. Model prose never supplies a price.
    line = (
        ("123,00 €" if locale == "de" else "€123.00")
        if state == "approved"
        else ("Preise nach Freigabe" if locale == "de" else "Prices after approval")
    )
    facts = merge(
        [
            collect(
                "linker/search-products",
                {
                    "qualified": [
                        {
                            "product_id": 2067,
                            "commerce": {
                                "price_visible": state == "approved",
                                "price_line": line,
                                "price_reason": reason,
                            },
                        }
                    ]
                },
                locale,
            ),
            collect(
                "linker/search-knowledge",
                {
                    "hits": [
                        {
                            "chunk_id": "c1",
                            "title": "Datenblatt",
                            "page": 1,
                            "doc_url": "https://example.test/de.pdf",
                        },
                        {
                            "chunk_id": "c2",
                            "title": "Datasheet",
                            "page": 1,
                            "doc_url": "https://example.test/en.pdf",
                        },
                    ]
                },
                locale,
            ),
        ]
    )
    # A page / get-product ID is not another qualified recommendation.
    facts.product_ids.add(9999)
    request = TurnRequest(
        conversation_id="synthetic-563",
        messages=[TurnMessage(role="user", content=question)],
        locale=locale,
        user=UserContext(logged_in=state != "guest", partner=state == "approved"),
    )
    retries: list[str | None] = []

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        retries.append(retry)
        return TurnOutput(
            language=("en" if locale == "de" else "de") if language_miss else locale,
            blocks=[
                TextBlock(
                    text="Hier sind das Produkt und sein Datenblatt."
                    if locale == "de"
                    else "Here are the product and its datasheet.",
                    refs=["2067", "c1", "c2"],
                ),
                CardsBlock(product_ids=[2067]),
                DocumentBlock(ref="c1"),
                DocumentBlock(ref="c2"),
            ],
        ), TurnFacts()

    result = run(request, generate, route, seed=facts)
    assert result.fallback is language_miss
    assert result.grounded is not language_miss
    assert result.attempts == (2 if language_miss else 1)
    assert len(retries) == result.attempts
    if language_miss:
        assert retries[1] and retries[1].startswith("answer in ")
    cards = [block for block in result.output.blocks if isinstance(block, CardsBlock)]
    assert len(cards) == 1
    assert cards[0].product_ids == [2067]
    assert cards[0].prices and cards[0].prices[0].text == line
    assert cards[0].prices[0].reason == reason
    assert [
        block.url for block in result.output.blocks if isinstance(block, DocumentBlock)
    ] == ["https://example.test/de.pdf#page=1", "https://example.test/en.pdf#page=1"]
