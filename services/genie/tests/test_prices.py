"""Prices follow the account (#242, docs/specs/13-genie.md 目标 8).

The fixture is what the product abilities of a local instance answered four kinds
of account on the live snapshot of 2026-10-17 (`eval/prices/capture_prices.py`): an
approved partner, a pending and a restricted account (each through the shell's own
customer token), and a guest. The model never writes a price; the service fills
each product card's price line from the turn's own tool results, and a card whose
product no tool of the turn priced is read with get-product, as the customer.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from linker_genie.abilities import USER_CONTEXT_HEADER, AbilityClient
from linker_genie.cycle import run
from linker_genie.facts import TurnFacts, collect
from linker_genie.ground import check
from linker_genie.prices import commerce_lookup
from linker_genie.quality import citations
from linker_genie.quality.turns import LoggedTurn
from linker_genie.schema import (
    CardPrice,
    CardsBlock,
    PriceReason,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
    UserContext,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "prices.json").read_text(encoding="utf-8")
)
STATES = ("approved", "pending", "restricted", "guest")
# The product page's price line for each account, read from the same instance
# (ProductView::price_html: the price, or the page's sentence in its place).
EXPECTED = {
    "approved": CardPrice(product_id=4107, text="€1,680.00"),
    "pending": CardPrice(
        product_id=4107, text="Prices after approval", reason="pending"
    ),
    "restricted": CardPrice(
        product_id=4107, text="Not available for your account", reason="restricted"
    ),
    "guest": CardPrice(
        product_id=4107, text="Net price after partner sign-in", reason="login"
    ),
}


def _request(locale: str = "en", state: str = "guest") -> TurnRequest:
    signed_in = state != "guest"
    return TurnRequest(
        conversation_id="c242",
        messages=[TurnMessage(role="user", content="What does the H2-10K-T3 cost?")],
        locale=locale,  # type: ignore[arg-type]
        user=UserContext(
            logged_in=signed_in,
            partner=state == "approved",
            context=f"token-{state}" if signed_in else None,
        ),
    )


def _answer(*ids: int) -> TurnOutput:
    return TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Here is the product.", refs=[str(i) for i in ids]),
            CardsBlock(product_ids=list(ids)),
        ],
    )


def _cards(output: TurnOutput) -> CardsBlock:
    return next(block for block in output.blocks if isinstance(block, CardsBlock))


@pytest.mark.parametrize("state", STATES)
def test_a_search_card_shows_what_the_product_page_shows(state: str) -> None:
    facts = collect("linker/search-products", FIXTURE[state]["search_h2_en"])

    result = run(_request(state=state), lambda _r, _x: (_answer(4107), facts))

    assert result.grounded
    assert _cards(result.output).prices == [EXPECTED[state]]


def test_a_german_card_shows_the_german_price_line() -> None:
    facts = collect("linker/get-product", FIXTURE["approved"]["product_4107_de"], "de")

    result = run(_request("de", "approved"), lambda _r, _x: (_answer(4107), facts))

    assert _cards(result.output).prices == [
        CardPrice(product_id=4107, text="1.680,00 €")
    ]


@pytest.mark.parametrize(
    ("state", "reason", "line"),
    [
        ("approved", "project", "Angebot pro Projekt"),
        ("pending", "pending", "Preise nach Freigabe"),
        ("restricted", "restricted", "Für Ihr Konto nicht verfügbar"),
        ("guest", "login", "Nettopreis nach Partner-Anmeldung"),
    ],
)
def test_a_product_quoted_per_project_has_no_price_for_anybody(
    state: str, reason: PriceReason, line: str
) -> None:
    """In German too: the line is the German product page's sentence."""
    facts = collect("linker/get-product", FIXTURE[state]["product_1957_de"], "de")

    result = run(_request("de", state), lambda _r, _x: (_answer(1957), facts))

    assert _cards(result.output).prices == [
        CardPrice(product_id=1957, text=line, reason=reason)
    ]


class Site:
    """The abilities endpoint of the fixture: answers get-product as the account
    whose token the request carries, and records what it was sent. `delay`
    holds each answer back that many seconds (a slow ability)."""

    def __init__(self, delay: float = 0.0) -> None:
        self.requests: list[httpx.Request] = []
        self.delay = delay

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.delay:
            time.sleep(self.delay)
        token = request.headers.get(USER_CONTEXT_HEADER, "")
        state = token.removeprefix("token-") if token else "guest"
        product = request.url.params.get("input[product_id]")
        lang = request.url.params.get("input[lang]")
        body = FIXTURE[state][f"product_{product}_{lang}"]
        return httpx.Response(200, json=body, request=request)


@pytest.mark.parametrize("state", STATES)
def test_a_card_no_tool_priced_is_read_as_the_customer(state: str) -> None:
    """A battery a pairing released, a product of the solution draft: no tool of
    the turn returned its commerce object, so the service reads it with
    get-product, carrying the customer's token, and logs the call like any
    other (the quality check reads the price from the log)."""
    site = Site()
    client = AbilityClient(
        "http://wp.test", transport=httpx.MockTransport(site.handler)
    )
    known = TurnFacts(product_ids={4107})
    request = _request(state=state)

    result = run(
        request,
        lambda _r, _x: (_answer(4107), known),
        commerce=commerce_lookup(client, request, time.monotonic() + 30),
    )

    assert _cards(result.output).prices == [EXPECTED[state]]
    assert len(site.requests) == 1
    assert site.requests[0].headers.get(USER_CONTEXT_HEADER) == request.user.context
    assert [call["name"] for call in result.facts.tool_calls] == ["linker/get-product"]
    logged = json.dumps(result.facts.tool_calls)
    assert "token-" not in logged


def test_the_lookups_run_side_by_side() -> None:
    """Three cards no tool priced cost one ability's time, not three."""
    site = Site(delay=0.3)
    client = AbilityClient(
        "http://wp.test", transport=httpx.MockTransport(site.handler)
    )
    known = TurnFacts(product_ids={4107, 1957})
    request = _request(state="approved")
    started = time.monotonic()

    result = run(
        request,
        lambda _r, _x: (_answer(4107, 1957), known),
        commerce=commerce_lookup(client, request, started + 30),
    )

    assert time.monotonic() - started < 0.55
    assert len(site.requests) == 2
    assert [line.product_id for line in _cards(result.output).prices or []] == [
        4107,
        1957,
    ]


@pytest.mark.parametrize(
    ("state", "line"),
    [
        ("guest", EXPECTED["guest"]),
        ("approved", None),
    ],
)
def test_a_slow_ability_cannot_push_the_turn_past_the_deadline(
    state: str, line: CardPrice | None
) -> None:
    """The lookups end at the deadline whatever the ability does; the missed
    call is reported, not logged as a result. A card left without its own
    commerce object reads the account's line when the account decides it (a
    guest, a pending or a restricted account read the same line on every
    product page, here taken from the other card); an approved account's line
    depends on the product, so that card shows none."""
    site = Site(delay=2.0)
    client = AbilityClient(
        "http://wp.test", transport=httpx.MockTransport(site.handler)
    )
    known = collect("linker/search-products", FIXTURE[state]["search_h2_en"])
    # A battery the search's pairings released: a card without a commerce object.
    known.product_ids.add(1957)
    known.qualified_ids.add(1957)
    request = _request(state=state)
    started = time.monotonic()

    result = run(
        request,
        lambda _r, _x: (_answer(4107, 1957), known),
        commerce=commerce_lookup(client, request, started + 0.3),
    )

    assert time.monotonic() - started < 1.0
    assert result.grounded
    assert result.price_failures == (
        "linker/get-product 1957: no answer before the turn's deadline",
    )
    prices = _cards(result.output).prices or []
    assert prices[0] == EXPECTED[state]
    expected_1957 = (
        None if line is None else line.model_copy(update={"product_id": 1957})
    )
    assert (prices[1] if len(prices) > 1 else None) == expected_1957
    assert all(call["name"] != "linker/get-product" for call in result.facts.tool_calls)


def test_the_deadline_keeps_the_turn_inside_the_shells_timeout() -> None:
    from linker_genie.prices import LOOKUP_DEADLINE, SHELL_TIMEOUT

    assert 0 < LOOKUP_DEADLINE < SHELL_TIMEOUT


def test_the_model_never_writes_a_price() -> None:
    """The price is the card's: a price placeholder in the text is refused, even
    for an approved account whose tool returned it."""
    facts = collect("linker/search-products", FIXTURE["approved"]["search_h2_en"])
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="It costs {fact:p4107.price}.", refs=["4107"]),
            CardsBlock(product_ids=[4107]),
        ],
    )

    result = check(output, facts)

    assert not result.ok
    assert any("price" in failure for failure in result.failures)


def test_prices_the_model_put_on_a_card_are_replaced() -> None:
    facts = collect("linker/search-products", FIXTURE["guest"]["search_h2_en"])
    forged = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Here is the product.", refs=["4107"]),
            CardsBlock(
                product_ids=[4107],
                prices=[CardPrice(product_id=4107, text="€1,680.00")],
            ),
        ],
    )

    result = run(_request(), lambda _r, _x: (forged, facts))

    assert _cards(result.output).prices == [EXPECTED["guest"]]


def test_the_model_does_not_see_the_price_field() -> None:
    """The structured output the model fills has no price on a card."""
    schema: dict[str, Any] = TurnOutput.model_json_schema()
    assert "prices" not in json.dumps(schema["$defs"]["CardsBlock"])


def test_the_fallback_cards_are_priced_too() -> None:
    facts = collect("linker/search-products", FIXTURE["approved"]["search_h2_en"])

    def failing(_r: TurnRequest, _x: str | None) -> tuple[TurnOutput, TurnFacts]:
        raise ValueError("the model wrote no valid turn")

    result = run(_request(state="approved"), failing, seed=facts)

    assert result.fallback
    assert _cards(result.output).prices == [EXPECTED["approved"]]


def test_the_model_reads_whether_the_account_is_a_partner() -> None:
    from linker_genie.agent import _user_prompt

    assert "partner=True" in _user_prompt(_request(state="approved"), None)
    assert "partner=False" in _user_prompt(_request(state="pending"), None)


# --- the quality check reads the card's price with the same two gates ------------


def _shipped(state: str, card: CardPrice, approved: bool) -> LoggedTurn:
    """A logged turn whose search ran as `state` and whose card shows `card`."""
    return LoggedTurn(
        id=1,
        conversation_id="c242",
        created_at="2026-10-18T00:00:00Z",
        locale="en",
        fallback=False,
        tool_calls=[
            {
                "name": "linker/search-products",
                "arguments": {"text": "H2-10K-T3", "lang": "en"},
                "ok": True,
                "result": FIXTURE[state]["search_h2_en"],
            }
        ],
        output={
            "language": "en",
            "blocks": [
                {"type": "text", "text": "Here is the product.", "refs": ["4107"]},
                {
                    "type": "cards",
                    "product_ids": [4107],
                    "prices": [card.model_dump()],
                },
            ],
        },
        question="What does the H2-10K-T3 cost?",
        page={},
        approved=approved,
    )


def test_an_approved_card_price_from_the_tool_passes_the_check() -> None:
    assert citations.verify(_shipped("approved", EXPECTED["approved"], True)) == []


@pytest.mark.parametrize("state", ["pending", "restricted", "guest"])
def test_a_card_without_a_price_passes_the_check(state: str) -> None:
    assert citations.verify(_shipped(state, EXPECTED[state], False)) == []


def test_a_card_price_for_an_account_not_approved_is_flagged() -> None:
    assert citations.verify(_shipped("approved", EXPECTED["approved"], False)) == [
        "shows the price of product 4107 on its card, and the account is not approved"
    ]


def test_a_card_price_no_tool_returned_is_flagged() -> None:
    assert citations.verify(_shipped("guest", EXPECTED["approved"], True)) == [
        "shows a price of product 4107 on its card that no tool returned"
    ]
