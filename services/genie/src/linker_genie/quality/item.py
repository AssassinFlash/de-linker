"""One logged turn as the judges read it.

The item is the shape `linker_judges.turns.turns_state` takes, built the way
the end-to-end suite builds its own (`eval/judges/score.py`), with one
difference: the reference is what the turn's abilities returned *then*, read
from the log, not a replay — the stock, the prices and a signed-in customer's
inquiries the model read may have changed since.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from linker_judges.turns import answer_with_offers

from linker_genie.facts import collect, merge
from linker_genie.quality.turns import LoggedTurn


@dataclass(frozen=True)
class Item:
    """The judges' state for one turn, and what the worker reports beside it."""

    state: dict[str, Any]
    answer: str
    """The answer as the customer read it (text, handoff, ask, actions)."""
    cards: list[int]
    page_product: int | None
    swap: tuple[int, int] | None
    """The wrong-pick variant's `(from, to)`; None when the turn offered no
    product with a sibling to swap in, so `better_pick` is not asked."""


class Skip(Exception):
    """A turn the judges cannot read: the reason is reported, not judged."""


def build(turn: LoggedTurn) -> Item:
    """The judged item for one logged turn; `Skip` when there is nothing to judge."""
    if not turn.output.get("blocks"):
        raise Skip("no answer was shipped (the turn failed inside the service)")
    if not turn.question:
        raise Skip("the turn was logged without its question")
    if any("result" not in call for call in turn.tool_calls):
        raise Skip("the turn was logged without its tool results")

    answer = rendered(turn.output)
    cards = offered(turn.output)
    page = page_product(turn.page)
    calls = [
        {
            "name": call.get("name"),
            "arguments": call.get("arguments"),
            "result": call["result"],
        }
        for call in turn.tool_calls
    ]
    state: dict[str, Any] = {
        "question": turn.question,
        "answer": answer_with_offers(answer, page, cards),
        # No calls: the judge must read "nothing backs this answer", not an
        # empty state it would call fine (score.py's build_item, same rule).
        "reference": {"calls": calls},
        "cards": cards,
    }
    swap = wrong_pick(turn, cards, page)
    if swap is not None:
        state["answer_a"] = answer_with_offers(answer, page, cards)
        state["answer_b"] = answer_with_offers(answer, page, cards, swap)
    return Item(state, answer, cards, page, swap)


def rendered(output: dict[str, Any]) -> str:
    """The shipped blocks as text, in order: what the customer read."""
    parts: list[str] = []
    for block in output.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            parts.append(str(block.get("text", "")))
        elif kind == "handoff":
            parts.append(str(block.get("summary", "")))
        elif kind == "ask":
            options = ", ".join(str(option) for option in block.get("options") or [])
            parts.append(
                f"[Asks for {block.get('field')}"
                + (f": {options}]" if options else "]")
            )
        elif kind == "action":
            parts.append(f"[Offers the action {block.get('name')}]")
    return "\n\n".join(part for part in parts if part)


def offered(output: dict[str, Any]) -> list[int]:
    """The product ids the answer showed as cards or in a comparison, in order."""
    ids: list[int] = []
    for block in output.get("blocks") or []:
        if isinstance(block, dict) and block.get("type") in ("cards", "compare"):
            for pid in block.get("product_ids") or []:
                if isinstance(pid, int) and pid not in ids:
                    ids.append(pid)
    return ids


def page_product(page: dict[str, Any]) -> int | None:
    product = page.get("product_id")
    if page.get("type") == "product" and isinstance(product, int) and product > 0:
        return product
    return None


def wrong_pick(
    turn: LoggedTurn, cards: list[int], page: int | None
) -> tuple[int, int] | None:
    """Swap the first recommendation for a product the turn's tools also
    returned but the answer did not offer — the "worse pick" the judges must
    not prefer. None when there is no recommendation or no such product."""
    recommended = [pid for pid in cards if pid != page]
    if not recommended:
        return None
    facts = merge(
        [
            collect(str(call.get("name", "")), call.get("result"), turn.locale)
            for call in turn.tool_calls
        ]
    )
    others = sorted(facts.product_ids - set(cards) - {page})
    if not others:
        return None
    return (recommended[0], others[0])
