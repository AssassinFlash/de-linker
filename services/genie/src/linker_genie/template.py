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
- A product clarification (#363, #367, #364): a brand the catalog does not list
  for that model, a model code the catalog does not list, several models in one
  sentence, or a product search that ran and matched nothing. The answer names
  what the catalog says and offers the products or one question. It is not the
  team mailbox. An ability outage (no successful search) stays the mailbox or
  the degraded sentence below.
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
from linker_genie.route import SEARCH_LIMIT, NamedModel, Route
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


def _extreme_fallback(facts: TurnFacts, language: Locale) -> TurnOutput | None:
    """The one product search-products aggregated, named by its model code."""
    winner = facts.facts.get("search.extreme_product_id")
    model = facts.facts.get("search.extreme_model")
    if winner is None or model is None:
        return None
    try:
        product_id = int(winner.value)
    except ValueError:
        return None
    text = (
        f"Das Modell {model.value} erfüllt die genannte Grenze."
        if language == "de"
        else f"The {model.value} meets the limit you named."
    )
    return TurnOutput(
        language=language,
        blocks=[
            TextBlock(text=text, refs=[str(product_id)]),
            CardsBlock(product_ids=[product_id]),
        ],
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
    # The applied winner is the whole fallback. The named-model clarification
    # would add the other cards (#363, #364), which an extreme answer refuses.
    extreme = _extreme_fallback(facts, language)
    if extreme is not None:
        return extreme
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
    clarified = _clarify(facts, language, route)
    if clarified is not None:
        return clarified
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


# Clarification sentences (#363, #367, #364). Functional UI text, owned here next
# to the only writer. EN and DE use the same blocks. Dossier 2026-10-19 §1.1,
# §1.11 and §2 item 10: this wording has no competitor precedent.
def _clarify(
    facts: TurnFacts, language: Locale, route: Route | None
) -> TurnOutput | None:
    """A product answer that names the catalog, or None to keep the older shapes."""
    if route is None:
        return None
    notes = route.named_models
    qualified = facts.qualified_ids
    missed = [note for note in notes if not note.searched]
    conflict_lines: list[str] = []
    conflict_ids: list[int] = []
    for note in notes:
        if not (note.searched and note.written_brand and note.catalog_brand):
            continue
        own_ids = [pid for pid in note.product_ids if pid in qualified]
        if not own_ids:
            continue
        conflict_lines.append(_conflict_sentence(note, language))
        for pid in own_ids:
            if pid not in conflict_ids:
                conflict_ids.append(pid)
    if conflict_lines and conflict_ids:
        return _product_answer(
            language,
            conflict_lines + _missed_sentences(missed, language),
            conflict_ids,
        )
    unknowns = [note for note in notes if note.unknown and note.searched]
    if unknowns:
        lines = [_range_sentence([note.code for note in unknowns], language)]
        if qualified:
            lines.append(_closest_sentence(language))
            lines.extend(_missed_sentences(missed, language))
            return _product_answer(language, lines, sorted(qualified))
        lines.extend(_missed_sentences(missed, language))
        return _ask_answer(language, lines)
    known = [note for note in notes if note.searched and not note.unknown]
    if len(known) >= 2:
        pending: list[str] = []
        found_ids: list[int] = []
        for note in known:
            own = [pid for pid in note.product_ids if pid in qualified]
            if own:
                for pid in own:
                    if pid not in found_ids:
                        found_ids.append(pid)
            elif note.product_ids:
                pending.append(_not_returned(note.code, language))
        if found_ids:
            lead = (
                "Das sind die Produkte zu den Modellen in Ihrer Nachricht."
                if language == "de"
                else "These are the products for the models in your message."
            )
            return _product_answer(
                language,
                [lead, *pending, *_missed_sentences(missed, language)],
                found_ids,
            )
        if pending or missed:
            return _ask_answer(language, pending + _missed_sentences(missed, language))
    if missed:
        return _ask_answer(language, _missed_sentences(missed, language))
    if (
        route.name in ("products", "model")
        and route.no_handoff
        and not qualified
        and not facts.product_ids
        and _search_succeeded(facts)
    ):
        line = (
            "Zu dieser Suche gibt es kein Produkt."
            if language == "de"
            else "No product matched that search."
        )
        return _ask_answer(language, [line])
    return None


def _conflict_sentence(note: NamedModel, language: Locale) -> str:
    if language == "de":
        return (
            f"{note.code} ist unter {note.catalog_brand} geführt. "
            f"Ihre Nachricht nennt {note.written_brand}. "
            f"Die Karte zeigt das {note.catalog_brand}-Produkt."
        )
    return (
        f"{note.code} is listed under {note.catalog_brand}. "
        f"Your message names {note.written_brand}. "
        f"The card shows the {note.catalog_brand} product."
    )


def _range_sentence(codes: list[str], language: Locale) -> str:
    shown = ", ".join(codes)
    if language == "de":
        verb = "sind" if len(codes) > 1 else "ist"
        return f"{shown} {verb} nicht in unserem Sortiment."
    verb = "are" if len(codes) > 1 else "is"
    return f"{shown} {verb} not in our product range."


def _closest_sentence(language: Locale) -> str:
    if language == "de":
        return "Die nächsten Produkte in unseren Produktdaten stehen auf den Karten."
    return "The closest products in our product data are on the cards."


def _not_returned(code: str, language: Locale) -> str:
    if language == "de":
        return f"Die Suche hat {code} nicht ergeben."
    return f"The search did not return {code}."


def _missed_sentences(notes: list[NamedModel], language: Locale) -> list[str]:
    if language == "de":
        return [f"{note.code} wurde in dieser Runde nicht gesucht." for note in notes]
    return [f"{note.code} was not searched in this turn." for note in notes]


def _product_answer(language: Locale, lines: list[str], ids: list[int]) -> TurnOutput:
    shown = ids[:SEARCH_LIMIT]
    return TurnOutput(
        language=language,
        blocks=[
            TextBlock(text=" ".join(lines), refs=[f"p{pid}" for pid in shown]),
            CardsBlock(product_ids=shown),
        ],
    )


def _ask_answer(language: Locale, lines: list[str]) -> TurnOutput:
    return TurnOutput(
        language=language,
        blocks=[
            TextBlock(text=" ".join(lines)),
            AskBlock(field="brand", options=_ask_options("brand", language)),
        ],
    )


def _search_succeeded(facts: TurnFacts) -> bool:
    return any(
        str(call.get("name", "")).endswith("search-products") and call.get("ok") is True
        for call in facts.tool_calls
    )


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
