"""Native product/document language recovery fixtures; no customer traces (#563)."""

import pytest

from linker_genie.cycle import run
from linker_genie.facts import TurnFacts, collect, merge
from linker_genie.jev import Reading
from linker_genie.lexicon import Match
from linker_genie.route import Subject, plan
from linker_genie.schema import (
    CardsBlock,
    DocumentBlock,
    Locale,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
    UserContext,
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
