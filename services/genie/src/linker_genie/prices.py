"""The price line of each product card, filled by the service (#242).

Prices follow the account (docs/specs/13-genie.md 目标 8): the product abilities
answer as the customer (the shell's short-lived token, abilities.py), so their
commerce object is what the customer's own product page shows: `price_line` is
the page's line where the price stands (the price for an approved partner
account, the page's own sentence for everybody else, already in the turn's
language), `price_reason` why there is no price. The model never writes a price
(ground.py refuses a price placeholder); the card carries the line, filled here
from the turn's own tool results, the way hydration fills the text's numbers.

A card whose product no tool of the turn priced (a battery a pairing released, a
product of the solution draft, a comparison) is read with get-product, as the
customer, after the run: side by side, and only until `LOOKUP_DEADLINE` seconds
after the turn began, so the whole turn stays inside the shell's timeout. The
calls that answered are the turn's tool calls like any other (logged with their
results, so the quality check finds the price it judges); one that missed the
deadline is reported in `price_failures`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Any, get_args

from linker_genie.abilities import AbilityClient, AbilityError
from linker_genie.facts import TurnFacts, merge
from linker_genie.schema import (
    CardPrice,
    CardsBlock,
    PriceReason,
    TurnOutput,
    TurnRequest,
)

logger = logging.getLogger("linker_genie")

# Reads the commerce objects of products no tool of the turn priced; the facts it
# returns carry them (TurnFacts.commerce) and the calls that read them, the list
# the lookups that failed or missed the deadline.
Lookup = Callable[[list[int]], tuple[TurnFacts, list[str]]]
REASONS: tuple[PriceReason, ...] = get_args(PriceReason)
# The reasons that belong to the account, not the product: the product page names
# them first (CommerceState::reason on its PAGE surface), so every product page
# of a guest, a pending or a restricted account prints the same line.
ACCOUNT_REASONS: frozenset[str] = frozenset({"login", "pending", "restricted"})

# The shell waits 60 s for a turn (plugins/linker-tools Proxy::post, 'timeout' =>
# 60.0). The lookups must be done 50 s after the turn began: the 10 s left cover
# the turn log, the SSE hand-over and the shell storing the thread (all three
# together took under 0.1 s on g242, 2026-10-18), with the slack of a slow host.
SHELL_TIMEOUT = 60.0
LOOKUP_DEADLINE = 50.0


def commerce_lookup(
    client: AbilityClient, request: TurnRequest, deadline: float
) -> Lookup:
    """get-product for each product, as the customer of this turn, side by side,
    until `deadline` (a `time.monotonic()` instant)."""

    def lookup(product_ids: list[int]) -> tuple[TurnFacts, list[str]]:
        if not product_ids:
            return TurnFacts(), []

        def one(product_id: int) -> TurnFacts:
            _payload, gathered = client.record(
                "linker/get-product",
                {"product_id": product_id, "lang": request.locale},
                request.user.context,
                request.locale,
            )
            return gathered

        pool = ThreadPoolExecutor(max_workers=len(product_ids))
        futures = {
            pool.submit(one, product_id): product_id for product_id in product_ids
        }
        wait(futures, timeout=max(0.0, deadline - time.monotonic()))
        # A call still running is left behind: it ends on its own HTTP timeout and
        # nothing waits for it.
        pool.shutdown(wait=False, cancel_futures=True)
        parts: list[TurnFacts] = []
        failures: list[str] = []
        for future, product_id in futures.items():
            if not future.done():
                failures.append(
                    f"linker/get-product {product_id}: no answer before the turn's deadline"
                )
                logger.warning(
                    "genie card price for %s missed the turn's deadline", product_id
                )
                continue
            try:
                parts.append(future.result())
            except AbilityError as error:
                failures.append(f"linker/get-product {product_id}: {error}")
                logger.warning("genie card price unavailable: %s", error)
        return merge(parts), failures

    return lookup


def fill(
    output: TurnOutput, facts: TurnFacts, lookup: Lookup | None = None
) -> tuple[TurnOutput, TurnFacts, list[str]]:
    """The output with every card's price line, the facts with any lookups, and
    the lookups that failed."""
    shown = [
        pid
        for block in output.blocks
        if isinstance(block, CardsBlock)
        for pid in block.product_ids
    ]
    missing = [pid for pid in dict.fromkeys(shown) if pid not in facts.commerce]
    failures: list[str] = []
    if missing and lookup is not None:
        found, failures = lookup(missing)
        facts = merge([facts, found])
    account = _account_line(facts)
    blocks = [
        block.model_copy(update={"prices": _prices(block, facts, account)})
        if isinstance(block, CardsBlock)
        else block
        for block in output.blocks
    ]
    return output.model_copy(update={"blocks": blocks}), facts, failures


def _prices(
    block: CardsBlock, facts: TurnFacts, account: CardPrice | None
) -> list[CardPrice]:
    lines: list[CardPrice] = []
    for pid in block.product_ids:
        price = line(pid, facts.commerce.get(pid))
        if price is None and account is not None:
            price = account.model_copy(update={"product_id": pid})
        if price is not None:
            lines.append(price)
    return lines


def _account_line(facts: TurnFacts) -> CardPrice | None:
    """The line every product page prints for this account, when the account
    decides it (a guest, a pending or a restricted account), read from any
    commerce object of the turn; None for an approved account."""
    for pid, commerce in facts.commerce.items():
        price = line(pid, commerce)
        if price is not None and price.reason in ACCOUNT_REASONS:
            return price
    return None


def line(product_id: int, commerce: dict[str, Any] | None) -> CardPrice | None:
    """One card's price line from the ability's commerce object, or None when the
    turn has none for it."""
    if not isinstance(commerce, dict):
        return None
    text = commerce.get("price_line")
    if not isinstance(text, str) or not text:
        return None
    reason = commerce.get("price_reason")
    return CardPrice(
        product_id=product_id,
        text=text,
        reason=reason if reason in REASONS else None,
    )
