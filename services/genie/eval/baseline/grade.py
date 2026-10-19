"""Grade a captured Genie turn against one baseline100 row (ticket #336).

The口径 is the Knocket trial's (docs/research/2026-10-17-knocket/TRIAL.md §1-2,
kept by docs/specs/13-genie.md "对照题集") turned into code:

- a product is hit when a cards/compare block shows it, or a text block cites
  its product id (the model writes no model codes into the text);
- every number in the hydrated answer must be traceable: to the row's expected
  values (unit conversions count, as the judge rubric words it), or to a
  catalogue model/SKU token the answer names;
- every answer carries a next step (goal 9);
- the map's hard rows (#329: trials 1, 8, 10, 14) never fall back and never
  deflect to the team mailbox;
- EN and DE rows share one structure (same slots, same assertion kinds).

Everything here is pure: the runner feeds it parsed turns, the tests feed it
hand-made ones. The rows live in baseline100.jsonl beside this module.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

# AGENTS.md §3: these words are not this shop's vocabulary, in either language.
FORBIDDEN_WORDS = (
    "catalogue",
    "catalog",
    "cart",
    "basket",
    "artikel",
    "katalog",
    "warenkorb",
)

# What counts as a next step (docs/specs/13-genie.md 目标 9: "每条回答后两到
# 三个可点的下一步"). A handoff is one too: the mailbox sentence is the step.
NEXT_STEP_BLOCKS = (
    "ask",
    "cards",
    "compare",
    "action",
    "document",
    "parts",
    "contact",
    "handoff",
)

# The mailbox the one-sentence referrals name; a hard row that mentions it has
# deflected (the map's gate: 不兜底不转 sales@).
MAILBOX = "sales@de-linker.com"

# A word with a digit in it (model codes like H2-10K-T3, GW15K-ETA-G20, values).
_CODE_WORD = re.compile(r"[^\s]*\d[^\s]*")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


@dataclass
class Turn:
    """One captured turn: the SSE stream's meta event, blocks and done flag."""

    meta: dict[str, Any] = field(default_factory=dict)
    blocks: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False


def parse_stream(stream: str) -> Turn:
    """Read the service's SSE text (`event:`/`data:` pairs) into a Turn."""

    turn = Turn()
    for chunk in stream.split("\n\n"):
        lines = chunk.strip().splitlines()
        name = next(
            (line[7:].strip() for line in lines if line.startswith("event: ")), None
        )
        payload = next(
            (line[6:].strip() for line in lines if line.startswith("data: ")), None
        )
        if name is None or payload is None:
            continue
        data: Any = json.loads(payload)
        if name == "meta" and isinstance(data, dict):
            turn.meta = data
        elif name == "block" and isinstance(data, dict):
            turn.blocks.append(data)
        elif name == "done":
            turn.done = True
    return turn


def answer_text(blocks: list[dict[str, Any]]) -> str:
    """The words the customer reads: text blocks plus a handoff's summary."""

    parts = []
    for block in blocks:
        if block.get("type") == "text":
            parts.append(str(block.get("text", "")))
        elif block.get("type") == "handoff":
            parts.append(str(block.get("summary", "")))
    return "\n".join(parts)


def block_types(blocks: list[dict[str, Any]]) -> set[str]:
    return {str(block.get("type")) for block in blocks}


def shown_ids(blocks: list[dict[str, Any]]) -> set[int]:
    """Product ids the turn shows: cards, comparisons and text citations.

    A text block's `refs` carry product ids and fact ids (docs/specs/13-genie.md
    "结构保证": 卡片 ⊆ 正文引用), so a cited id counts as shown.
    """

    ids: set[int] = set()
    for block in blocks:
        kind = block.get("type")
        if kind in {"cards", "compare"}:
            ids.update(int(pid) for pid in block.get("product_ids") or [])
        elif kind == "text":
            for ref in block.get("refs") or []:
                if str(ref).isdigit():
                    ids.add(int(ref))
    return ids


def compare_ids(blocks: list[dict[str, Any]]) -> list[set[int]]:
    """Every compare block's product ids, one set per block."""

    return [
        {int(pid) for pid in block.get("product_ids") or []}
        for block in blocks
        if block.get("type") == "compare"
    ]


def cited_refs(blocks: list[dict[str, Any]]) -> set[str]:
    """The refs of text blocks (a `page` ref means the answer cites the page)."""

    return {
        str(ref)
        for block in blocks
        if block.get("type") == "text"
        for ref in block.get("refs") or []
    }


def action_names(blocks: list[dict[str, Any]]) -> set[str]:
    return {str(block.get("name")) for block in blocks if block.get("type") == "action"}


def contact_reasons(blocks: list[dict[str, Any]]) -> set[str]:
    return {
        str(block.get("reason")) for block in blocks if block.get("type") == "contact"
    }


def price_lines(blocks: list[dict[str, Any]]) -> list[str]:
    """The card price lines the service filled (#242): the only price surface."""

    lines = []
    for block in blocks:
        if block.get("type") != "cards":
            continue
        for price in block.get("prices") or []:
            if isinstance(price, dict) and price.get("text"):
                lines.append(str(price["text"]))
    return lines


def number_variants(token: str) -> set[float]:
    """The numbers a printed token can mean: `20.000` is 20000 (EN thousands)
    or 20.0 (a decimal), `20,000` the same pair the other way round."""

    values: list[float] = []
    for separator in (".", ","):
        if separator in token:
            whole, _, fraction = token.partition(separator)
            if whole.isdigit() and fraction.isdigit():
                values.append(float(f"{whole}.{fraction}"))
                if len(fraction) == 3:  # a thousands group, EN or DE print
                    values.append(float(whole + fraction))
    if token.isdigit():
        values.append(float(token))
    return set(values)


def _catalog_tokens(catalog: Mapping[str, str]) -> set[str]:
    """A word is a catalogue code when its letters-and-digits form is one.

    Catalogue tokens arrive as the Store API prints them - the model attribute
    ("EF HD-P1-3K68-S2") and the product name - so a token is split on
    whitespace first: the answer names the model without the brand prefix
    ("HD-P1-3K68-S2")."""

    codes: set[str] = set()
    for token in catalog:
        for part in str(token).split():
            stripped = re.sub(r"[^a-z0-9]", "", part.lower())
            if stripped:
                codes.add(stripped)
    return codes


def untraceable_numbers(
    text: str, allowed: list[str], catalog: Mapping[str, str] | None = None
) -> list[str]:
    """Numbers in the answer that no expected fact and no catalogue code backs.

    `allowed` is the row's `expect.numbers` (strings, e.g. "20000", "6.6",
    "2026"): a token passes when any of its readings equals an allowed value or
    its 1000-fold (15000 Wp = 15 kWp = 15.000 Wp, as the judge rubric words
    it). A number inside a catalogue model/SKU (H2-10K-T3) is traceable by
    being that product's name.
    """

    permitted: set[float] = set()
    for value in allowed:
        for variant in number_variants(str(value)):
            permitted.update({variant, variant * 1000.0, variant / 1000.0})
    codes = _catalog_tokens(catalog or {})
    untraceable = []
    for word in _CODE_WORD.findall(text):
        stripped = re.sub(r"[^a-z0-9]", "", word.lower())
        if stripped in codes:
            continue
        # A series prefix as printed on its own ("CB2" for CB2-100.3-HV5) is
        # still the product's own code.
        if any(letter.isalpha() for letter in stripped) and any(
            code.startswith(stripped) for code in codes
        ):
            continue
        # A designation the manual uses for equipment we do not sell (CH2, the
        # inverter a CB2 cabinet connects to): letters first, then digits, no
        # unit - unlike a measurement ("1500mm", digits first).
        if re.match(r"[a-z]{1,4}\d", stripped):
            continue
        for token in _NUMBER.findall(word):
            readings = number_variants(token)
            if readings and not readings & permitted:
                untraceable.append(token)
    return untraceable


def _floors(row: dict[str, Any], turn: Turn) -> list[str]:
    """The checks every row of the set shares (TRIAL.md's zero-error lines)."""

    failures: list[str] = []
    if not turn.done:
        failures.append("stream did not finish (no done event)")
    if turn.meta.get("fallback"):
        failures.append("fell back to the template (no answer)")
    if not turn.meta.get("grounded"):
        failures.append(
            f"ungrounded: {'; '.join(map(str, turn.meta.get('failures') or []))}"
        )
    if str(turn.meta.get("language")) != row["lang"]:
        failures.append(
            f"answered in {turn.meta.get('language')!r}, the customer wrote {row['lang']}"
        )
    text = answer_text(turn.blocks).lower()
    for word in FORBIDDEN_WORDS:
        if re.search(rf"\b{word}\b", text):
            failures.append(f"forbidden word '{word}' (AGENTS.md §3)")
    return failures


def check(
    row: dict[str, Any],
    turn: Turn,
    catalog: Mapping[str, str] | None = None,
) -> list[str]:
    """Why the row fails; empty when it passes. Judge/human-review rows still
    run the floors and any `expect` they carry — the verdict beyond that is the
    judge's or a person's, not this function's."""

    failures = _floors(row, turn)
    expect = row.get("expect") or {}
    blocks = turn.blocks
    text = answer_text(blocks)
    types = block_types(blocks)
    shown = shown_ids(blocks)

    for product_id in expect.get("products", []):
        if int(product_id) not in shown:
            failures.append(f"product {product_id} is neither shown nor cited")
    any_of = expect.get("products_any")
    if any_of and not {int(pid) for pid in any_of} & shown:
        failures.append(f"none of products {any_of} is shown or cited")

    groups = expect.get("compare")
    if groups is not None:
        wanted = [{int(pid) for pid in group} for group in groups]
        comparisons = compare_ids(blocks)
        held = any(group <= block_ids for group in wanted for block_ids in comparisons)
        if not comparisons:
            failures.append("no compare block")
        elif not held:
            failures.append(f"no compare block holds one of {groups}")

    for kind in expect.get("blocks", []):
        if kind not in types:
            failures.append(f"no {kind} block")
    for kind in expect.get("not_blocks", []):
        if kind in types:
            failures.append(f"must not carry a {kind} block")

    if "action" in expect and expect["action"] not in action_names(blocks):
        failures.append(f"no {expect['action']} action")

    if expect.get("document") and "document" not in types:
        failures.append("no document link cited")

    contact = expect.get("contact")
    if contact is not None:
        reasons = contact_reasons(blocks)
        if not reasons:
            failures.append("no contact offer")
        elif isinstance(contact, str) and contact not in reasons:
            failures.append(f"contact offer is {sorted(reasons)}, expected '{contact}'")

    if expect.get("no_handoff"):
        if "handoff" in types:
            failures.append("deflected to the team (handoff block)")
        if MAILBOX in text:
            failures.append(f"sent the customer to {MAILBOX}")

    gate = expect.get("price_gate")
    if gate is not None:
        lines = price_lines(blocks)
        if not lines:
            failures.append("cards carry no price line")
        elif not any(re.search(gate, line) for line in lines):
            failures.append(f"card price line is {lines}, expected /{gate}/")

    for pattern in expect.get("all", []):
        if not re.search(pattern, text):
            failures.append(f"missing /{pattern}/")
    for pattern in expect.get("none", []):
        if re.search(pattern, text):
            failures.append(f"must not match /{pattern}/")

    if expect.get("next_step") and not types & set(NEXT_STEP_BLOCKS):
        failures.append("no next step after the answer (goal 9)")

    if expect.get("cites_page") and "page" not in cited_refs(blocks):
        failures.append("the answer does not cite the page")

    numbers = expect.get("numbers")
    if numbers is not None:
        for token in untraceable_numbers(text, numbers, catalog):
            failures.append(f"number {token} is in no expected fact")
    return failures
