"""The price line of each product card, filled by the service (#242).

Prices follow the account (docs/specs/13-genie.md 目标 8): the product abilities
answer as the customer (the shell's short-lived token, abilities.py), so their
commerce object is what the customer's own product page shows — an approved
partner account reads the price as the page prints it (`price_text`), everybody
else reads why there is none (`price_reason`: sign in, waiting for approval,
restricted, quoted per project, on request). The model never writes a price
(ground.py refuses a price placeholder); the card carries it, filled here from
the turn's own tool results, the way hydration fills the text's numbers.

A card whose product no tool of the turn priced (a battery a pairing released,
a product of the solution draft, a comparison) is read with get-product, as the
customer, after the run. Those calls are the turn's tool calls like any other:
logged with their results, so the quality check finds the price it judges.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from linker_genie.abilities import AbilityClient, AbilityError
from linker_genie.facts import TurnFacts, merge
from linker_genie.schema import CardPrice, CardsBlock, TurnOutput, TurnRequest

logger = logging.getLogger("linker_genie")

# Reads the commerce objects of products no tool of the turn priced; the facts it
# returns carry them (TurnFacts.commerce) and the calls that read them.
Lookup = Callable[[list[int]], tuple[TurnFacts, list[str]]]
REASONS = ("login", "pending", "restricted", "project", "unpriced")


def commerce_lookup(client: AbilityClient, request: TurnRequest) -> Lookup:
    """get-product for each product, as the customer of this turn, side by side."""

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

        with ThreadPoolExecutor(max_workers=len(product_ids)) as pool:
            futures = [pool.submit(one, product_id) for product_id in product_ids]
        parts: list[TurnFacts] = []
        failures: list[str] = []
        for product_id, future in zip(product_ids, futures, strict=True):
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
    the lookups that failed (their cards carry no price line)."""
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
    blocks = [
        block.model_copy(update={"prices": _prices(block, facts)})
        if isinstance(block, CardsBlock)
        else block
        for block in output.blocks
    ]
    return output.model_copy(update={"blocks": blocks}), facts, failures


def _prices(block: CardsBlock, facts: TurnFacts) -> list[CardPrice]:
    return [
        price
        for pid in block.product_ids
        if (price := line(pid, facts.commerce.get(pid))) is not None
    ]


def line(product_id: int, commerce: dict[str, Any] | None) -> CardPrice | None:
    """One card's price line from the ability's commerce object, or None when the
    turn has none for it."""
    if not isinstance(commerce, dict):
        return None
    text = commerce.get("price_text")
    if isinstance(text, str) and text:
        return CardPrice(product_id=product_id, text=text)
    reason = commerce.get("price_reason")
    if reason in REASONS:
        return CardPrice(product_id=product_id, reason=reason)
    return None
