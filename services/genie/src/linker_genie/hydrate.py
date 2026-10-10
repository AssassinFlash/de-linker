"""Server-side hydration: replace `{fact:ID}` with values from this turn's tools.

The model must not write numbers. Placeholders are filled here (Rufus). There
is no rewriting of the rest of the text. Handoff summaries hydrate too: the
prompt routes out-of-scope turns through handoff-team and puts the team
mailbox sentence into the summary as `{fact:handoff.sentence_*}` — the
customer must see the real sentence, not a model paraphrase (review
2026-10-10, must-fix 1).
"""

from __future__ import annotations

import re

from linker_genie.facts import Fact, TurnFacts
from linker_genie.schema import Block, HandoffBlock, TextBlock, TurnOutput

PLACEHOLDER = re.compile(r"\{fact:([^}]+)\}")


def hydrate(output: TurnOutput, facts: TurnFacts) -> TurnOutput:
    """Return a copy whose text blocks and handoff summaries are filled."""
    blocks: list[Block] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            blocks.append(block.model_copy(update={"text": fill(block.text, facts)}))
        elif isinstance(block, HandoffBlock):
            blocks.append(
                block.model_copy(update={"summary": fill(block.summary, facts)})
            )
        else:
            blocks.append(block)
    return output.model_copy(update={"blocks": blocks})


def fill(text: str, facts: TurnFacts) -> str:
    """Replace each `{fact:ID}` with the stored value; unknown IDs stay as-is
    so a later check can still see them."""

    def replace(match: re.Match[str]) -> str:
        fact = _lookup(facts, match.group(1))
        return fact.value if fact is not None else match.group(0)

    return PLACEHOLDER.sub(replace, text)


def _lookup(facts: TurnFacts, fact_id: str) -> Fact | None:
    """The fact for an ID, tolerating a missing leading 'p' on a product fact."""
    fact = facts.facts.get(fact_id)
    if fact is None and not fact_id.startswith("p"):
        fact = facts.facts.get(f"p{fact_id}")
    return fact


def leftover_placeholders(text: str) -> list[str]:
    """Fact IDs still present as `{fact:ID}` after a fill attempt."""
    return PLACEHOLDER.findall(text)
