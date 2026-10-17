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
- A sizing turn (route.py): one sentence and the configurator action, never a
  stack of cards; the configurator does the sizing (trial question 14,
  docs/research/2026-10-17-knocket/TRIAL.md).
- A document turn with documents found: one sentence and the documents as links,
  before any cards.
- With nothing citable (every ability call failed - an outage or a storm -
  or the model produced no product structure twice): the mailbox sentence
  when handoff-team ran this turn, and the degraded declaration only when
  it did not. The degraded sentence says the failure plainly and offers
  the retry and the team; a German line carries no English fragment. The
  turn's meta carries `fallback: true` with the failures for anything that
  reads the stream programmatically; the schema has no separate
  degradation block.
"""

from __future__ import annotations

from linker_genie.facts import TurnFacts
from linker_genie.hydrate import hydrate
from linker_genie.route import SEARCH_LIMIT, Route
from linker_genie.schema import (
    ASK_FIELDS,
    ActionBlock,
    AskBlock,
    AskField,
    Block,
    CardsBlock,
    DocumentBlock,
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

# R7 unsigned-out (docs/acceptance/protocol.md §5): a guest who asks where
# the Proforma stands is asked to log in. The sentence is the service's,
# not the model's, so a German turn cannot drift into the team mailbox
# sentence (PR #96 pending-main, measured 2026-10-11). Functional UI text.
# Wording: docs/acceptance/2026-10-13/genie-facts-protocol/copy-review.md.
# The same two sentences are quoted in prompts/en/system.md,
# prompts/de/system.md and the per-turn reminder in agent.py — those three
# copies have to stay byte-identical to this dict, because grounding
# accepts only this text.
LOGIN_REQUIRED = {
    "en": "Please log in to your account to view this inquiry.",
    "de": "Bitte melden Sie sich in Ihrem Konto an, um diese Anfrage anzuzeigen.",
}

# The sizing and document shapes' sentences (#233). Functional UI text; wording:
# docs/acceptance/2026-10-17/233/copy-review.md.
SIZING = {
    "en": (
        "The Solution Configurator sizes the battery from your annual "
        "consumption and your PV system."
    ),
    "de": (
        "Der Lösungskonfigurator ermittelt die passende Speichergröße anhand "
        "Ihres Jahresverbrauchs und Ihrer PV-Leistung."
    ),
}
DOCUMENTS = {
    "en": "Here is what I found for your question.",
    "de": "Zu Ihrer Frage habe ich Folgendes gefunden.",
}
# Document links the document shape shows: search-knowledge ranks its hits, and three
# keep the answer short (the trial's failures were answers that listed too much).
FALLBACK_DOCUMENTS = 3

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


def fallback(facts: TurnFacts, locale: str, route: Route | None = None) -> TurnOutput:
    """A protocol-set answer for a turn grounding refused twice, in `locale`."""
    language = language_of(locale)
    # The login fact outranks every other shape. A guest Proforma question
    # that also called handoff-team must still ask for a login (R7), not
    # ship the mailbox sentence the handoff tool returned.
    if "inquiry.login_required" in facts.facts:
        return login_required(language)
    url = facts.facts.get("size.configurator_url")
    if route is not None and route.name == "sizing" and url is not None:
        return TurnOutput(
            language=language,
            blocks=[
                TextBlock(text=SIZING[language]),
                ActionBlock(name="open_configurator", args={"url": url.value}),
            ],
        )
    if route is not None and route.name == "documents" and facts.documents:
        refs = [ref for ref in facts.documents if ref in facts.chunk_ids] or list(
            facts.documents
        )
        document_blocks: list[Block] = [
            TextBlock(text=DOCUMENTS[language], refs=refs[:FALLBACK_DOCUMENTS])
        ]
        document_blocks.extend(
            DocumentBlock(ref=ref) for ref in refs[:FALLBACK_DOCUMENTS]
        )
        return hydrate(TurnOutput(language=language, blocks=document_blocks), facts)
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
        # The route's six (route.SEARCH_LIMIT): a fallback that dumped twelve
        # cards was trial question 11's failure (2026-10-17); one ask follows to
        # narrow the rest.
        CardsBlock(product_ids=ids[:SEARCH_LIMIT]),
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
