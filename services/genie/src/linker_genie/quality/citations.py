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
"""

from __future__ import annotations

import re

from linker_genie.facts import collect, merge
from linker_genie.ground import bare_numbers
from linker_genie.quality.turns import LoggedTurn


def verify(turn: LoggedTurn) -> list[str]:
    """What the shipped answer states or cites beyond the turn's tool results."""
    facts = merge(
        [
            collect(str(call.get("name", "")), call.get("result"), turn.locale)
            for call in turn.tool_calls
        ]
    )
    known = facts.ids()
    sources = " ".join(fact.value for fact in facts.facts.values())
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
        if kind in ("text", "handoff"):
            text = str(block.get("text" if kind == "text" else "summary", ""))
            for number in bare_numbers(text):
                if not _occurs(number, sources):
                    failures.append(f"states {number}, which no tool result contains")
    return failures


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
