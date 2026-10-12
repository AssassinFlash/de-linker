"""Deterministic fallback when structured output or grounding fails twice.

Three shapes, each inside the protocol set by construction
(`docs/acceptance/protocol.md` §5):

- A guest inquiry turn (`inquiry.login_required` is a fact of this turn):
  the login sentence only. R7's unsigned-out half is "要求登录", not the
  team mailbox, so the template must not hand that turn to the handoff
  sentence even when `handoff-team` also ran.
- With this turn's tool results (products survived the failed attempts):
  the qualified cards plus one ask, cards cited by the text's refs. A
  German turn's text and ask options are German; an English turn's are
  English. The handoff mailbox sentence is not this shape.
- With nothing citable (every ability call failed - an outage or a storm -
  or the model produced no product structure twice): one handoff that says
  so plainly instead of reading as a normal answer, and offers the retry
  and the team. That sentence is the degraded declaration, not the
  mailbox sentence: a German line carries no English fragment. The turn's
  meta carries `fallback: true` with the failures for anything that reads
  the stream programmatically; the schema has no separate degradation block.
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

# R7 unsigned-out (docs/acceptance/protocol.md §5, panel B7): a guest who
# asks where the Proforma stands is asked to log in. The sentence is the
# service's, not the model's, so a German turn cannot drift into the team
# mailbox sentence (PR #96 pending-main, measured 2026-10-11). Functional
# UI text, EN and DE written independently.
LOGIN_REQUIRED = {
    "en": "Please log in to see where your Proforma stands.",
    "de": "Bitte melden Sie sich an, um zu sehen, wo Ihre Proforma steht.",
}

# English function words that only appear in an English sentence. The e2e
# suite uses the same test (tests/e2e/specs/genie.spec.ts ENGLISH_ONLY) to
# refuse a German answer that mixes in an English fragment.
_ENGLISH_FRAGMENT = (
    " the ",
    " and ",
    " with ",
    " your ",
    " this ",
    " our ",
)


def language_of(locale: str) -> Locale:
    """`de` for a German locale, otherwise `en`."""
    return "de" if locale.startswith("de") else "en"


def login_required(locale: str) -> TurnOutput:
    """The R7 guest sentence: ask for a login, name no mailbox, leak nothing."""
    language = language_of(locale)
    return TurnOutput(
        language=language,
        blocks=[TextBlock(text=LOGIN_REQUIRED[language])],
    )


def german_is_clean(text: str) -> bool:
    """A German line carries none of the English function-word fragments."""
    padded = f" {text.lower()} "
    return not any(fragment in padded for fragment in _ENGLISH_FRAGMENT)


def fallback(facts: TurnFacts, locale: str) -> TurnOutput:
    """A protocol-set answer for a turn grounding refused twice, in `locale`."""
    language = language_of(locale)
    # The login fact outranks every other shape. A guest Proforma question
    # that also called handoff-team must still ask for a login (R7), not
    # ship the mailbox sentence the handoff tool returned.
    if "inquiry.login_required" in facts.facts:
        return login_required(language)
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
