"""Deterministic fallback when structured output or grounding fails twice.

Two shapes, both protocol-compliant by construction:

- With this turn's tool results (products survived the failed attempts):
  the qualified cards plus one ask, cards cited by the text's refs.
- With nothing citable (every ability call failed - an outage or a storm -
  or the model produced no product structure twice): one handoff that says
  so plainly instead of reading as a normal answer, and offers the retry
  and the team. The turn's meta carries `fallback: true` with the failures
  for anything that reads the stream programmatically; the schema has no
  separate degradation block.
"""

from __future__ import annotations

from linker_genie.facts import TurnFacts
from linker_genie.schema import (
    ASK_FIELDS,
    AskBlock,
    AskField,
    Block,
    CardsBlock,
    HandoffBlock,
    Locale,
    TextBlock,
    TurnOutput,
)

# The degraded sentence, EN and DE. Functional UI text (a state the turn can
# land in), owned here next to the only writer; its wording went through the
# copy review of docs/acceptance/2026-10-12/103/copy-review.md.
DEGRADED = {
    "en": (
        "I could not answer this time. Please try again in a moment, "
        "or write to our team."
    ),
    "de": (
        "Ich konnte Ihre Frage diesmal nicht beantworten. Bitte versuchen "
        "Sie es gleich noch einmal, oder wenden Sie sich an unser Team."
    ),
}


def fallback(facts: TurnFacts, locale: str) -> TurnOutput:
    """Cards of qualified products and at most one ask, in `locale`."""
    language: Locale = "de" if locale.startswith("de") else "en"
    qualified = sorted(facts.qualified_ids)
    if not qualified and not facts.product_ids:
        # The handoff-team sentence when the tool ran this turn; the degraded
        # declaration only when it did not - the turn has nothing citable, so
        # pretending to hand off normally would hide the outage.
        sentence_id = (
            "handoff.sentence_de" if language == "de" else "handoff.sentence_en"
        )
        sentence = facts.facts.get(sentence_id)
        summary = sentence.value if sentence is not None else DEGRADED[language]
        return TurnOutput(
            language=language,
            blocks=[HandoffBlock(summary=summary)],
        )
    ids = qualified or sorted(facts.product_ids)
    refs = [f"p{product_id}" for product_id in ids]
    text = (
        "Hier sind passende Produkte aus unserem Sortiment."
        if language == "de"
        else "Here are matching products from our range."
    )
    blocks: list[Block] = [
        TextBlock(text=text, refs=refs),
        # Twelve, because search-products' own limit is 12 (docs/specs/
        # 13-genie.md §A, `limit≤12`): the template can never show more cards
        # than the tool that qualified them may return.
        CardsBlock(product_ids=ids[:12]),
    ]
    ask_field = _ask_field(facts)
    if ask_field is not None:
        blocks.append(
            AskBlock(field=ask_field, options=_ask_options(ask_field, language))
        )
    return TurnOutput(language=language, blocks=blocks)


def _ask_field(facts: TurnFacts) -> AskField | None:
    # Priority subsets of ASK_FIELDS (schema.py is the one source of the
    # field names; only the asking order is policy here).
    order: tuple[AskField, ...] = ("phase", "application", "pv_kwp", "backup")
    unknown = set(facts.unknown_fields)
    if "pv_input" in unknown:
        unknown.add("pv_kwp")
    for field in order:
        if field in unknown:
            return field
    remaining = tuple(field for field in ASK_FIELDS if field not in order)
    for field in remaining:
        if field in unknown:
            return field
    return "backup" if facts.qualified_ids else None


def _ask_options(field: str, language: str) -> list[str]:
    en = {
        "phase": ["1", "3"],
        "application": ["home", "commercial"],
        "pv_kwp": [],
        "kwh": [],
        "backup": ["none", "needed", "needed_accessory_ok"],
        "brand": [],
        "voltage": ["48 V", "HV"],
    }
    de = {
        "phase": ["1", "3"],
        "application": ["Wohngebäude", "Gewerbe"],
        "pv_kwp": [],
        "kwh": [],
        "backup": ["ohne", "benötigt", "benötigt, Zubehör akzeptiert"],
        "brand": [],
        "voltage": ["48 V", "HV"],
    }
    table = de if language == "de" else en
    return list(table.get(field, []))
