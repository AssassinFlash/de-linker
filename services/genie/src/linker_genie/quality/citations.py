"""The deterministic citation check of a shipped turn.

docs/specs/10-knowledge-index.md, "引用与核验": the answer cites only what the
turn's tools returned, and every number it states occurs in a cited source.
`ground.py` enforces this before the answer ships, on the placeholders; this
re-checks the shipped, filled answer against the tool results the log kept,
so a hydration or template defect that slipped past shows up per turn.

What counts as a number is ground.py's own rule (`ground.bare_numbers`): a
model code written whole (BU2-5.0-HV1, CB2-100.3-HV5, GW125/261-ESA-LCN-G10)
is a name, not the numbers inside it (#258: turn 27 on production was flagged
for the "5.0" of BU2-5.0-HV1), while a number written beside a code is checked.

A price is never in the text (#242, the remit's price rule): a number equal to a
price the turn's tools returned is flagged in any account's answer. The product
card carries the price, and the card's price passes two gates (`_card_prices`):
the tool returned it as visible, and the account is approved.
"""

from __future__ import annotations

import re
from typing import Any

from linker_genie.facts import TurnFacts, collect, merge
from linker_genie.ground import bare_numbers
from linker_genie.quality.turns import LoggedTurn


def verify(turn: LoggedTurn) -> list[str]:
    """What the shipped answer states or cites beyond the turn's tool results.

    A turn whose file readings were purged with their conversation
    (`log.TurnLog.forget`) is not judged: the reading text that vouched for the
    answer's figures is gone by design, so every citation would look unfounded
    (review round 1 of PR #309). New turns are judged before any deletion.
    """
    if any(
        isinstance(call.get("result"), dict) and call["result"].get("purged")
        for call in turn.tool_calls
    ):
        return []
    facts = merge(
        [
            collect(str(call.get("name", "")), call.get("result"), turn.locale)
            for call in turn.tool_calls
        ]
    )
    known = facts.ids()
    sources = " ".join(fact.value for fact in facts.facts.values())
    prices = _visible_prices(facts)
    failures: list[str] = []
    for block in turn.output.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            for ref in block.get("refs") or []:
                ref = str(ref)
                if ref not in known and f"p{ref}" not in known:
                    failures.append(f"cites {ref}, which no tool returned")
        if kind in ("cards", "compare"):
            for pid in block.get("product_ids") or []:
                if pid not in facts.product_ids:
                    failures.append(f"shows product {pid}, which no tool returned")
        if kind == "cards":
            failures.extend(_card_prices(block, facts, turn.approved))
        if kind in ("text", "handoff"):
            text = str(block.get("text" if kind == "text" else "summary", ""))
            for number in bare_numbers(text):
                if not _occurs(number, sources):
                    failures.append(f"states {number}, which no tool result contains")
                else:
                    failures.extend(
                        f"states the price of product {pid} in the text; prices "
                        "appear only on the product card"
                        for pid, price in prices.items()
                        if _same_amount(number, price)
                    )
    return failures


def _card_prices(block: dict[str, Any], facts: TurnFacts, approved: bool) -> list[str]:
    """A card's price passes the same two gates as a price in the text (#242): the
    turn's tool returned this line for this product as a visible price (a
    `price_line` with `price_visible` and no `price_reason`), and the account is an
    approved one. A line that carries a reason is the page's sentence, not a price.
    """
    failures: list[str] = []
    for line in block.get("prices") or []:
        if not isinstance(line, dict) or line.get("reason"):
            continue
        pid = line.get("product_id")
        returned = facts.commerce.get(pid) if isinstance(pid, int) else None
        if (
            not returned
            or not returned.get("price_visible")
            or returned.get("price_reason")
            or returned.get("price_line") != line.get("text")
        ):
            failures.append(
                f"shows a price of product {pid} on its card that no tool returned"
            )
        elif not approved:
            failures.append(
                f"shows the price of product {pid} on its card, and the account is "
                "not approved"
            )
    return failures


def _visible_prices(facts: TurnFacts) -> dict[str, str]:
    """Product id → price, for the prices the turn's tools returned as visible.

    `facts.collect` keeps a price only when the ability said `price_visible`, so
    these are exactly the prices the site let this turn see; none of them belongs
    in the text (`linker_judges.rubric.REMIT`, #242).
    """
    return {
        fact.id.removeprefix("p").removesuffix(".price"): fact.value
        for fact in facts.facts.values()
        if fact.id.startswith("p") and fact.id.endswith(".price")
    }


def _same_amount(number: str, price: str) -> bool:
    try:
        return float(number.replace(",", ".")) == float(price.replace(",", "."))
    except ValueError:
        return False


def _occurs(number: str, sources: str) -> bool:
    variants = {number, number.replace(",", "."), number.replace(".", ",")}
    return any(
        re.search(rf"(?<![\d.,]){re.escape(variant)}(?!\d|[.,]\d)", sources)
        for variant in variants
    )


def summary(failures: list[str], limit: int = 5) -> list[str]:
    """At most `limit` failures, the rest counted, for the report."""
    if len(failures) <= limit:
        return failures
    return [*failures[:limit], f"… and {len(failures) - limit} more"]
