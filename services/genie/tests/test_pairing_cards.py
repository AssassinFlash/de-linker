"""A repeated pairing question keeps the tool's released card set (#376).

The campaign run and the c376 replay asked the same German question four times.
The route and the search stayed `pairing` / H2-10K-T3 with the same seven
released batteries. The model sometimes left the inverter out of the cards
block. English kept the full set. The service fills that set from the tool.
"""

from typing import Any

from linker_genie.cycle import run
from linker_genie.facts import TurnFacts, collect
from linker_genie.hydrate import complete_pairing_cards
from linker_genie.route import Route
from linker_genie.schema import (
    CardsBlock,
    DocumentBlock,
    Locale,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)

INVERTER = 4107
BATTERIES = [1832, 2067, 2068, 2069, 2070, 2090, 2092]
RELEASED = [INVERTER, *BATTERIES]


def _payload() -> dict[str, Any]:
    pairings = [
        {"product_id": battery, "verdict": "released_with_accessory", "conditions": []}
        for battery in BATTERIES
    ]
    pairings.append({"product_id": 9999, "verdict": "not_released", "conditions": []})
    return {
        "qualified": [
            {
                "product_id": INVERTER,
                "facts": {},
                "commerce": {"price_visible": False},
                "pairings": pairings,
            }
        ]
    }


def _facts(locale: Locale = "de") -> TurnFacts:
    payload = _payload()
    gathered = collect("linker/search-products", payload, locale)
    gathered.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {
                "device_class": "inverters",
                "with_pairings": True,
                "text": "H2-10K-T3",
                "lang": locale,
                "limit": 1,
            },
            "ok": True,
            "result": payload,
        }
    )
    return gathered


def _request(locale: Locale) -> TurnRequest:
    question = (
        "Welche Batterien passen zum SAJ H2-10K-T3?"
        if locale == "de"
        else "Which batteries work with the SAJ H2-10K-T3?"
    )
    return TurnRequest(
        conversation_id="c376",
        messages=[TurnMessage(role="user", content=question)],
        locale=locale,
    )


def _answer(
    language: Locale, text: str, cards: list[int], refs: list[str]
) -> TurnOutput:
    return TurnOutput(
        language=language,
        blocks=[
            TextBlock(text=text, refs=refs),
            CardsBlock(product_ids=cards),
        ],
    )


def test_a_german_retry_that_drops_the_inverter_ships_the_released_set() -> None:
    """Campaign turns 62–65: the first draft quoted "Artikel" and the retry
    kept only the batteries. The tool result still had the inverter."""
    facts = _facts()
    seen: list[str | None] = []

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        seen.append(retry)
        if retry is None:
            return (
                _answer(
                    "de",
                    "Das Steuermodul ist ein eigener Artikel.",
                    RELEASED,
                    [str(pid) for pid in RELEASED],
                ),
                facts,
            )
        return (
            _answer(
                "de",
                "Das Steuermodul ist ein eigenes Produkt.",
                BATTERIES,
                [str(pid) for pid in BATTERIES],
            ),
            facts,
        )

    result = run(_request("de"), generate, Route("pairing", no_handoff=True))
    cards = result.output.blocks[1]
    text = result.output.blocks[0]
    assert result.grounded is True
    assert result.fallback is False
    assert result.attempts == 2
    assert seen[1] is not None and "artikel" in seen[1]
    assert isinstance(cards, CardsBlock)
    assert cards.product_ids == RELEASED
    assert isinstance(text, TextBlock)
    assert text.text == "Das Steuermodul ist ein eigenes Produkt."
    assert "4107" in text.refs
    assert 9999 not in cards.product_ids


def test_a_first_attempt_that_omits_the_inverter_card_still_shows_it() -> None:
    """c376 replay, rounds 1 and 3: one attempt, refs named 4107, cards did not."""
    facts = _facts()

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (
            _answer(
                "de",
                "Diese Batterien haben ein dokumentiertes Pairing.",
                BATTERIES,
                ["4107", *[str(pid) for pid in BATTERIES]],
            ),
            facts,
        )

    first = run(_request("de"), generate, Route("pairing", no_handoff=True))
    second = run(_request("de"), generate, Route("pairing", no_handoff=True))
    assert first.attempts == 1
    assert isinstance(first.output.blocks[1], CardsBlock)
    assert isinstance(second.output.blocks[1], CardsBlock)
    assert first.output.blocks[1].product_ids == RELEASED
    assert second.output.blocks[1].product_ids == first.output.blocks[1].product_ids


def test_an_english_answer_that_already_shows_the_set_keeps_its_order() -> None:
    facts = _facts("en")
    output = _answer(
        "en",
        "These batteries have a documented pairing.",
        RELEASED,
        [str(pid) for pid in RELEASED],
    )
    filled = complete_pairing_cards(output, facts, Route("pairing"))
    cards = filled.blocks[1]
    assert isinstance(cards, CardsBlock)
    assert cards.product_ids == RELEASED
    assert filled.blocks[0] == output.blocks[0]


def test_a_product_route_does_not_gain_the_inverter_card() -> None:
    facts = _facts()
    output = _answer(
        "de",
        "Diese Batterien haben ein dokumentiertes Pairing.",
        BATTERIES,
        [str(pid) for pid in BATTERIES],
    )
    filled = complete_pairing_cards(output, facts, Route("products"))
    cards = filled.blocks[1]
    assert isinstance(cards, CardsBlock)
    assert cards.product_ids == BATTERIES


def test_a_document_block_stays_when_the_inverter_card_is_restored() -> None:
    facts = _facts()
    document = DocumentBlock(ref="compat.document.1832.0")
    output = TurnOutput(
        language="de",
        blocks=[
            TextBlock(text="Diese Batterien haben ein dokumentiertes Pairing."),
            CardsBlock(product_ids=BATTERIES),
            document,
        ],
    )
    filled = complete_pairing_cards(output, facts, Route("pairing"))
    assert isinstance(filled.blocks[1], CardsBlock)
    assert filled.blocks[1].product_ids == RELEASED
    assert filled.blocks[2] == document
    text = filled.blocks[0]
    assert isinstance(text, TextBlock)
    assert text.refs == [str(pid) for pid in RELEASED]


def test_a_pairing_fallback_shows_every_released_product() -> None:
    """Both drafts fail the number check. The template's six-card cap is the
    search sample, not this pairing: the shipped cards are the released set."""
    facts = _facts()

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request, retry
        return (
            _answer(
                "de",
                "Die Spannung liegt bei 180 V.",
                BATTERIES,
                [str(pid) for pid in BATTERIES],
            ),
            facts,
        )

    result = run(_request("de"), generate, Route("pairing", no_handoff=True))
    cards = next(
        block for block in result.output.blocks if isinstance(block, CardsBlock)
    )
    assert result.fallback is True
    assert cards.product_ids == RELEASED
    assert 9999 not in cards.product_ids
