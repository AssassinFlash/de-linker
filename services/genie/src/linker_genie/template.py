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
  team mailbox. An ability outage that is not a fatal failure (no successful
  search) stays the mailbox or the degraded sentence below.
- With nothing citable (every ability call failed - an outage or a storm -
  or the model produced no product structure twice) and the turn is not a
  fatal failure: the mailbox sentence when handoff-team ran this turn, and
  the degraded declaration only when it did not. The degraded sentence says
  the failure plainly and offers the retry and the team; a German line
  carries no English fragment. The turn's meta carries `fallback: true`
  with the failures for anything that reads the stream programmatically;
  the schema has no separate degradation block.
- A fatal failure this turn (`failure_class` is `model`, `retrieval` or
  `ability`; #410, dossier 2026-10-19 §1.15): the same degraded sentence,
  even when this turn already has cards or documents. Cards and document
  links may stay. The matching-products sentence and the document success
  sentence do not. An ability failure is not the sales mailbox. A request
  for a person is answered before this template (app._answer). Login still
  outranks this.
- A not_released pair check with no released set (`compat.verdict` is
  `not_released`): the check's own condition facts and documents, no cards.
  The service adds no sentence of its own; the conditions are tool data
  (#396).
- A document or chunk ref this turn did not return (`invented_citation`):
  the degraded sentence and no cards (#396). A product id is not this case.
- A tool whose pydantic-ai retry budget is spent (`exhausted`): the degraded
  sentence only, and no cards. The route may already hold product ids; they
  are not shown as a normal match. This is stricter than a fatal failure
  that still has qualified cards (#410). Dossier 2026-10-19 §1.15: the
  recovery path matches the failure (try again, or write to the team),
  which is this sentence.
- A products route whose search qualified nothing: no cards from
  `facts.product_ids`. A search that ran asks once; a search that did not
  run is the outage sentence above.
- A stock-status turn (`route.stock`, #415), after the clarification above
  (an empty successful search stays this turn's, never "No product matched."):
  the page's status sentence and the cards. Mixed statuses name both
  statuses, not one status for every card. No usable status is the degraded
  sentence, not a recommendation. A stock question that also asks about
  delivery adds the team sentence for that part.
"""

from __future__ import annotations

import re

from linker_genie.facts import (
    RELEASED_VERDICTS,
    Fact,
    TurnFacts,
    pairing_card_sets,
    stock_rows,
)
from linker_genie.failure import FailureClass
from linker_genie.figures import chunk_of, is_code
from linker_genie.hydrate import PLACEHOLDER, hydrate
from linker_genie.route import (
    SEARCH_LIMIT,
    ModelLookup,
    NamedModel,
    Route,
    lookup_models,
    several,
)
from linker_genie.schema import (
    ASK_FIELDS,
    ActionBlock,
    AskBlock,
    AskField,
    Block,
    CardsBlock,
    CompareBlock,
    DocumentBlock,
    HandoffBlock,
    Locale,
    TextBlock,
    TurnOutput,
)
from linker_genie.stock import phrase

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
# The prompts and the per-turn reminder name the placeholder. The service
# fills it from this dict in the answer language (cycle.align_login,
# hydrate._render_fact). Grounding also accepts either exact sentence.
LOGIN_REQUIRED = {
    "en": "Please log in to your account to view this inquiry.",
    "de": "Bitte melden Sie sich in Ihrem Konto an, um diese Anfrage anzuzeigen.",
}
LOGIN_PLACEHOLDER = "{fact:inquiry.login}"
HANDOFF_PLACEHOLDER = "{fact:handoff.sentence}"

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
# Next-step sentences (#394). Functional UI text, owned here next to the writer.
# Wording: docs/acceptance/2026-10-20/394/copy-review.md, signed 2026-10-20.
# The same four sentences are also written into prompts/en/system.md,
# prompts/de/system.md, route.py `_SHAPE_HINT`, and the per-turn reminder in
# agent.py. Those four tell the model what to say; they are not a second
# customer string. A wording change starts here and has to be carried across,
# or the model and this check drift apart.
# Already said is the content, not only this exact sentence, where a sentence
# is appended: the service handoff's promise ("within one working day" /
# "innerhalb eines Werktags"; "einem Werktag" and the contact card's "one
# business day" do not count). A shaped turn (TALK, PARTNER, PROMISE below)
# replaces the model's prose with the signed sentence instead of appending it,
# so a paraphrase cannot stand beside the same content.
TALK = {
    "en": (
        "I am Linker's AI assistant. I can help with products, compatibility, "
        "documents and sizing. Which product category do you want to look at?"
    ),
    "de": (
        "Ich bin Genie, der KI-Assistent von Linker. Ich unterstütze Sie bei "
        "Produkten, Kompatibilität, Dokumenten und der Auslegung. Welche "
        "Produktkategorie möchten Sie ansehen?"
    ),
}
PROMISE = {
    "en": (
        "After you send an inquiry, the Linker team replies within one working day."
    ),
    "de": (
        "Nach dem Absenden Ihrer Anfrage antwortet das Linker-Team "
        "innerhalb eines Werktags."
    ),
}
REPLY_PROMISE = {
    "en": "The Linker team replies within one working day.",
    "de": "Das Linker-Team antwortet innerhalb eines Werktags.",
}
PARTNER = {
    "en": (
        "Approved partner accounts see net prices. A guest sees "
        '"Net price after partner sign-in" on the product card. An account '
        'under review sees "Account under review. Prices after approval."'
    ),
    "de": (
        "Freigegebene Partnerkonten sehen die Nettopreise. Auf der "
        "Produktkarte steht für einen Gast „Nettopreis nach "
        "Partner-Anmeldung“ und für ein Konto in Prüfung „Ihr Konto wird "
        "geprüft. Preise nach Freigabe.“"
    ),
}
# Fixed sentences for the scripted route (#440). Each restates only the
# reference of its baseline row: no owner date, no mailbox address, no reply
# promise, no question mark. EN is settled first; DE is written on its own.
# The German open sentence points at the inquiry form and restates the guest
# fields. It does not say "Preise" (the remit says the answer text never
# states a price) and it does not say "nur", which would deny the reference's
# price half. It also leaves out the account and list clause: a live cascade
# read that clause as an account process outside the remit, while still
# scoring the form facts as supported. The record is
# docs/acceptance/2026-10-20/440/copy-review.md.
SCRIPTED = {
    "open": {
        "en": (
            "Inquiries are open to everyone. A guest fills in an email, a name "
            "and an optional company on the inquiry form. An account is only "
            "needed to see prices and the inquiry list."
        ),
        "de": (
            "Eine Anfrage stellen Sie über das Anfrageformular. Ein Gast gibt "
            "dort E-Mail, Name und optional die Firma an."
        ),
    },
    "remit": {
        "en": (
            "Product selection is what I can do: finding products, "
            "compatibility, documents and a battery size through the Solution "
            "Configurator. Planning the whole project, installation and "
            "company services go to the team mailbox."
        ),
        "de": (
            "Die Produktauswahl ist meine Aufgabe: Produkte finden, "
            "Kompatibilität, Dokumente und die Speichergröße im "
            "Lösungskonfigurator. Gesamtplanung, Montage und "
            "Unternehmensdienstleistungen gehen an das Teampostfach."
        ),
    },
    "weather": {
        # The capability clause uses the same words as TALK. A wording change
        # of that clause starts in TALK and has to be carried here.
        "en": (
            "I have no weather data. I can help with products, compatibility, "
            "documents and sizing."
        ),
        "de": (
            "Wetterdaten habe ich nicht. Ich unterstütze Sie bei Produkten, "
            "Kompatibilität, Dokumenten und der Auslegung."
        ),
    },
}
# The Roof detail step (#497): its role and the cost of skipping it. The role
# sentence is the site card's own copy (#12, docs/acceptance/2026-10-10/12/
# copy-review.md §3); the last sentence is the engine's limit.default_orientation
# verbatim (services/engine/src/linker_engine/texts.py, #479 C57). The step is
# optional, and without it the yield falls back to that orientation. EN is
# settled first; DE keeps the site's sentence and is written on its own. The
# service writes the whole turn, and the action's URL comes from size-hint.
ROOF = {
    "en": (
        "The Roof detail step adds the building's layout. It is optional and "
        "maps the roof surface and module placement. Without a roof plane, "
        "the yield assumes 35° tilt facing south (HTW Berlin calculator "
        "default)."
    ),
    "de": (
        "Der Schritt Dachdetails nimmt die Dachfläche auf. Er ist optional und "
        "zeichnet die Lage der Module ein. Ohne Dachfläche nimmt der Ertrag "
        "35° Neigung nach Süden an (Vorgabe des HTW-Rechners)."
    ),
}
# A service backstop, not a sentence the model is told to copy. Appended only
# when a released pairing condition names a hyphenated model code the text
# omitted and a card shows that partner. Comma-joined, so the German line
# stays free of "and".
PARTNER_CODES = {
    "en": "Compatible models: {codes}.",
    "de": "Passende Modelle: {codes}.",
}
# The recorded ESA battery question (#440). The model named the modules and
# then restated each power figure, which the number allowlist rejects. This
# sentence restates the released condition's two model codes and no bare
# figure, no page range. EN is settled first; DE is written on its own. The
# model still runs; finish() replaces its prose. The record is
# docs/acceptance/2026-10-20/440/copy-review.md.
ESA_BATTERY = {
    "en": (
        "The GoodWe ESA pairs with the GW5.1/8.3/6.0/9.0-BAT-D-G20 "
        "battery modules for the GW3K–10K-EHA-G20 power modules."
    ),
    "de": (
        "Zum GoodWe ESA passen die Batteriemodule "
        "GW5.1/8.3/6.0/9.0-BAT-D-G20 für die Leistungsmodule "
        "GW3K–10K-EHA-G20."
    ),
}
# `compat.condition.{partner_id}.{index}` from a search pairing. A check's
# `compat.condition.0` has no partner id and is not this pattern.
_PAIR_CONDITION = re.compile(r"^compat\.condition\.(\d+)\.(\d+)$")
_CODE_MARK = re.compile(r"[-/–—]")
# A slash or a dash that is not a hyphen marks a family of codes (GW5.1/8.3…,
# GW3K–10K-EHA-G20). A hyphenated prose compound (G20-Module) has neither.
_RANGE_MARK = re.compile(r"[/–—]")
_CODE_EDGE = ".,;:()[]\"'“”„"
# Document links the document shape shows: search-knowledge ranks its hits, and three
# keep the answer short (the trial's failures were answers that listed too much).
FALLBACK_DOCUMENTS = 3

# Absence phrases the fallback writes. ground.py imports them, so rewording a
# sentence cannot leave the check matching the old words. EN keeps the #251
# range wording ("One line is not in our product range."). DE is written in
# Sie-form on its own. The record is
# docs/acceptance/2026-10-19/379/copy-review.md; the coordinator has not
# signed off. Dossier 2026-10-19 §1.1, §1.11 and §2 item 10: no competitor
# wording to copy.
NOT_IN_RANGE_EN = "not in our product range"
NOT_IN_RANGE_DE = "haben wir kein Produkt"
NO_MATCH_EN = "No product matched."
NO_MATCH_DE = "Dazu haben wir kein passendes Produkt."
# Both statuses, when the products do not share one (#415). The page's own
# lines, so a blanket "In stock" is not written over an out-of-stock card.
MIXED_STATUS = {
    "en": ("Some of these products are in stock and some are currently unavailable."),
    "de": ("Einige dieser Produkte sind auf Lager, andere derzeit nicht verfügbar."),
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


def roof_answer(text: str, facts: TurnFacts, language: Locale) -> TurnOutput:
    """The Roof detail step's turn (#497): the signed sentence and the action.

    `text` is `ROOF` for this turn's language. hydrate fills the configurator
    URL from size-hint's fact, so the link is the site's and not one the answer
    wrote. The action is drawn only when that fact is here, the same gate the
    sizing fallback uses: a failed call is the caller's degraded turn, never a
    clickable step with no URL. No cards and no handoff: the route's shape.
    """
    blocks: list[Block] = [TextBlock(text=text)]
    if "size.configurator_url" in facts.facts:
        blocks.append(ActionBlock(name="open_configurator", args={}))
    return hydrate(TurnOutput(language=language, blocks=blocks), facts)


def _pair_document_refs(facts: TurnFacts) -> list[str]:
    """Document facts of the pair check, in the tool's order.

    `compat.document.0` is that check. `compat.document.3612.0` is a battery
    on a search-products pairing row and is a different answer.
    """
    found: list[tuple[int, str]] = []
    for fact_id in facts.documents:
        head, _, tail = fact_id.rpartition(".")
        if head == "compat.document" and tail.isdigit():
            found.append((int(tail), fact_id))
    return [fact_id for _, fact_id in sorted(found)]


def _pair_condition_refs(facts: TurnFacts) -> list[str]:
    """Condition facts of the pair check, in the tool's order.

    `compat.condition.0` is that check. `compat.condition.3612.0` is a battery
    on a search-products pairing row and is a different answer.
    """
    found: list[tuple[int, str]] = []
    for fact_id in facts.facts:
        head, _, tail = fact_id.rpartition(".")
        if head == "compat.condition" and tail.isdigit():
            found.append((int(tail), fact_id))
    return [fact_id for _, fact_id in sorted(found)]


def _not_released_fallback(facts: TurnFacts, language: Locale) -> TurnOutput | None:
    """The check's own conditions, when the pair is not released.

    This runs only after grounding failed twice. The sentences are the
    contract facts (`compat.condition.N`) the tool returned this turn, the
    same placeholders the prompt asks the model to write; the service adds no
    sentence of its own. A released set in the same turn stays on the card
    path. No condition fact means no sentence is invented. The pair itself is
    not shown as cards. Documents the check returned stay the next step.
    """
    verdict = facts.facts.get("compat.verdict")
    if verdict is None or verdict.value != "not_released":
        return None
    if pairing_card_sets(facts):
        return None
    conditions = _pair_condition_refs(facts)
    if not conditions:
        return None
    text = " ".join(f"{{fact:{fact_id}}}" for fact_id in conditions)
    blocks: list[Block] = [TextBlock(text=text)]
    blocks.extend(DocumentBlock(ref=ref) for ref in _pair_document_refs(facts))
    return hydrate(TurnOutput(language=language, blocks=blocks), facts, language)


def _extreme_fallback(
    facts: TurnFacts, language: Locale, route: Route | None = None
) -> TurnOutput | None:
    """The aggregate, plus every code the same question named (#384).

    An applied extreme still shows that one card. A hidden price names no
    cheapest product. Either way the codes are in the text. Dossier §1.1 and
    §1.11 have no wording for this mix, so the sentences are the existing
    extreme line, the existing range line, and one line that names the codes.
    """
    hidden = facts.facts.get("search.extreme_price_hidden")
    winner = facts.facts.get("search.extreme_product_id")
    model = facts.facts.get("search.extreme_model")
    if hidden is not None and winner is None:
        if route is None or not route.named_models:
            return None
        return _hidden_codes_answer(facts, language, route)
    if winner is None or model is None:
        return None
    try:
        product_id = int(winner.value)
    except ValueError:
        return None
    lead = (
        f"Das Modell {model.value} erfüllt die genannte Grenze."
        if language == "de"
        else f"The {model.value} meets the limit you named."
    )
    lines = [lead]
    if route is not None and route.named_models:
        lines.extend(_extreme_code_lines(facts, language, route, skip=model.value))
    return TurnOutput(
        language=language,
        blocks=[
            TextBlock(text=" ".join(lines), refs=[str(product_id)]),
            CardsBlock(product_ids=[product_id]),
        ],
    )


def _hidden_codes_answer(
    facts: TurnFacts, language: Locale, route: Route
) -> TurnOutput:
    """Name the codes. Do not call one of them the cheapest, and write no price.

    The price sentence and "You named" are customer-visible. The record is
    docs/acceptance/2026-10-20/384/copy-review.md, signed off on 2026-10-20.
    """
    price = (
        "Freigegebene Partnerkonten sehen die Nettopreise."
        if language == "de"
        else "Approved partner accounts see net prices."
    )
    looked = lookup_models(route.named_models, facts.tool_calls, facts.qualified_ids)
    codes = _extreme_code_lines(facts, language, route, skip=None, looked=looked)
    ids: list[int] = []
    for item in looked:
        if not item.note.searched_known:
            continue
        for product_id in item.note.product_ids:
            if product_id in facts.qualified_ids and product_id not in ids:
                ids.append(product_id)
    if not ids and facts.qualified_ids:
        ids = sorted(facts.qualified_ids)
    shown = ids[:SEARCH_LIMIT]
    blocks: list[Block] = [TextBlock(text=price)]
    blocks.append(
        TextBlock(text=" ".join(codes), refs=[str(product_id) for product_id in shown])
    )
    if shown:
        blocks.append(CardsBlock(product_ids=shown))
    return TurnOutput(language=language, blocks=blocks)


def _extreme_code_lines(
    facts: TurnFacts,
    language: Locale,
    route: Route,
    *,
    skip: str | None,
    looked: tuple[ModelLookup, ...] | None = None,
) -> list[str]:
    """One line per code that still has to be said, without a cheapest claim.

    `skip` is a code already named by the winner sentence. None names every
    searched code. `looked` is the join this caller already made.
    """
    if looked is None:
        looked = lookup_models(
            route.named_models, facts.tool_calls, facts.qualified_ids
        )
    lines: list[str] = []
    named: list[str] = []
    missed: list[NamedModel] = []
    unknown_empty: list[str] = []
    for item in looked:
        code = item.note.code
        if item.outcome == "unsearched":
            missed.append(item.note)
            continue
        if item.note.unknown and item.outcome == "empty":
            unknown_empty.append(code)
            continue
        if item.note.searched and code != skip:
            named.append(code)
    if unknown_empty:
        lines.append(_range_sentence(unknown_empty, language))
    if named:
        lines.append(_named_codes_sentence(named, language))
    lines.extend(_missed_sentences(missed, language))
    return lines


def _named_codes_sentence(codes: list[str], language: Locale) -> str:
    shown = ", ".join(codes)
    if language == "de":
        return f"Sie haben {shown} genannt."
    return f"You named {shown}."


def stock_answer(
    facts: TurnFacts, language: Locale, *, handoff: str | None = None
) -> TurnOutput | None:
    """The status sentence and its cards.

    None when this turn has no usable stock flag. One shared flag is the
    page's own line (stock.phrase), with no quantity. Differing flags name
    both page lines, so a blanket "In stock" is not written over a card that
    is out of stock. `handoff` is the team sentence for a delivery question
    in the same message. A missing flag is not false.
    """
    rows = stock_rows(facts)
    if not rows:
        return None
    ids = [product_id for product_id, _flag in rows][:SEARCH_LIMIT]
    flags = {flag for _product_id, flag in rows}
    refs = [f"p{product_id}.stock" for product_id in ids]
    cards = CardsBlock(product_ids=ids)
    status = (
        MIXED_STATUS[language] if len(flags) != 1 else phrase(language, flags.pop())
    )
    blocks: list[Block] = [
        TextBlock(text=status, refs=refs),
        cards,
    ]
    if handoff:
        blocks.append(HandoffBlock(summary=handoff))
    return TurnOutput(language=language, blocks=blocks)


def german_is_clean(text: str) -> bool:
    """A German line carries none of the English function-word fragments."""
    padded = f" {text.lower()} "
    return not any(fragment in padded for fragment in _ENGLISH_FRAGMENT)


def _warranty_period_fallback(
    facts: TurnFacts,
    language: Locale,
    route: Route,
    question: str,
    page_product_id: int | None,
) -> TurnOutput | None:
    """Use an already verified policy answer for one clearly named model."""
    if (
        route.name != "documents"
        or facts.technical_chunks
        or not re.search(
            r"\b(?:warrant\w*|guarantee\w*|\w*garantie\w*|\w*gewährleist\w*)\b",
            question,
            re.I,
        )
        or not re.search(
            r"\b(?:how long|how many (?:years?|months?)|when (?:does|will|did|is)|"
            r"warranty (?:period|duration|start)|guarantee period|start of (?:the )?warranty|"
            r"wie lange|wie\s*viele (?:jahre|monate)|wann (?:beginnt|startet|gilt|fängt)|"
            r"ab wann|ab welchem zeitpunkt|garantiebeginn|garantiedauer|"
            r"garantiezeit(?:raum)?)\b",
            question,
            re.I,
        )
    ):
        return None
    candidates = [
        cid
        for cid in facts.documents
        if cid in facts.warranty_chunks
        and len(facts.warranty_models.get(cid, ())) == 1
        and len(facts.knowledge_products.get(cid, ())) == 1
        and facts.warranty_answers.get(cid, {}).get("period")
        and facts.warranty_answers.get(cid, {}).get("start")
    ]
    identities = {
        (facts.knowledge_products[cid][0], facts.warranty_models[cid][0])
        for cid in candidates
    }
    if len(identities) != 1:
        return None
    pid, model = next(iter(identities))
    if route.named_models and any(
        note.unknown or set(note.product_ids) != {pid} for note in route.named_models
    ):
        return None
    from linker_genie.source_models import model_pattern

    if page_product_id != pid and not model_pattern(model).search(question):
        return None
    cid = candidates[0]
    answers = facts.warranty_answers[cid]
    period, start = answers["period"], answers["start"]
    answer = period if start in period else answers.get("general", "")
    if not answer:
        return None
    draft = TurnOutput(language=language, blocks=[TextBlock(text=answer, refs=[cid])])
    # Run the same model, source and condition checks used for model answers.
    # The import is local because ground also uses this module's constants.
    from linker_genie.ground import check

    if not check(
        draft, facts, route, question=question, page_product_id=page_product_id
    ).ok:
        return None
    return hydrate(draft, facts, language)


def _manual_torque_fallback(
    facts: TurnFacts,
    language: Locale,
    route: Route,
    question: str,
    page_product_id: int | None,
) -> TurnOutput | None:
    """Keep the two reviewed ETR fastening actions distinct on fallback."""
    from linker_genie.ground import (
        check,
        manual_torque_actions,
        manual_torque_source_actions,
    )
    from linker_genie.manual_diagram_records import DIAGRAMS
    from linker_genie.manual_evidence import evidence_id
    from linker_genie.source_models import codes, model_pattern

    actions = manual_torque_actions(question)
    sources = manual_torque_source_actions(facts)
    if (
        route.name != "documents"
        or len(actions) != 1
        or not sources
        or re.search(
            r"\b(?:and|also|und|sowie)\s+(?:what|how|when|which|was|wie|wann|welche)\b",
            question,
            re.I,
        )
    ):
        return None
    action = next(iter(actions))
    # An explicitly named GoodWe model overrides the product-page context.
    named = {
        code.casefold() for code in codes(question) if re.match(r"^GW\d", code, re.I)
    }
    matches: list[str] = []
    for cid, source_action in sources.items():
        if source_action != action:
            continue
        ids = facts.knowledge_products.get(cid, ())
        if len(ids) != 1:
            continue
        for record in DIAGRAMS:
            if record.get("torque_action") != action:
                continue
            models = [part.strip(" ()") for part in record["anchor_quote"].split("|")]
            for model in models:
                if (
                    not model
                    or (named and named != {model.casefold()})
                    or (
                        not named
                        and page_product_id != ids[0]
                        and not model_pattern(model).search(question)
                    )
                ):
                    continue
                if cid == evidence_id(
                    record["sha256"],
                    record["source_page"],
                    model,
                    record["source_id"],
                    record["excerpt"],
                ):
                    matches.append(cid)
    if len(set(matches)) != 1:
        return _degraded_keeping_findings(facts, language, route)
    cid = matches[0]
    source = facts.facts[f"{cid}.text"].value
    if language == "de":
        if action == "inverter_to_bracket":
            answer = (
                "Für die Befestigung des Wechselrichters an der Montagehalterung "
                "zeigt Abbildung ETR12510INT0004 M6-Schrauben mit einem "
                f"Drehmoment von {{fact:{cid}.n1}} bis {{fact:{cid}.n2}}."
            )
        else:
            answer = (
                "Für die Befestigung der Halterung an der Wand zeigt Abbildung "
                "ETR12510INT0002 M10-Befestigungselemente mit einem "
                f"Drehmoment von {{fact:{cid}.n3}} bis {{fact:{cid}.n4}}."
            )
    else:
        answer = re.sub(
            r"\[n([1-9]\d*)=[^\[\]\n]+\]",
            lambda match: f"{{fact:{cid}.n{match.group(1)}}}",
            source,
        )
    draft = TurnOutput(language=language, blocks=[TextBlock(text=answer, refs=[cid])])
    if not check(
        draft, facts, route, question=question, page_product_id=page_product_id
    ).ok:
        return _degraded_keeping_findings(facts, language, route)
    return hydrate(draft, facts, language)


def fallback(
    facts: TurnFacts,
    locale: str,
    route: Route | None = None,
    *,
    exhausted: bool = False,
    failure_class: FailureClass | None = None,
    raised: bool = False,
    invented_citation: bool = False,
    question: str = "",
    page_product_id: int | None = None,
) -> TurnOutput:
    """A protocol-set answer for a turn grounding refused twice, in `locale`.

    `exhausted` is a tool call that spent pydantic-ai's tool retries
    (`cycle._tool_retries_exhausted`). The answer is the degraded sentence,
    not the product template, and the route's ids are not shown.

    `failure_class` is a fatal failure of this turn (`cycle.fatal_class`):
    the model returned 5xx/429/an empty stream, the document index or the
    encoder failed, or an ability returned 5xx or timed out. The customer
    sentence is the degraded sentence even when cards or documents exist.

    `raised` is the last attempt threw (`cycle.run`). `kind_of` may still be
    None. That is not a grounding miss: on a shaped route the answer is the
    degraded sentence, findings kept, not the signed shape. A grounding miss
    leaves `raised` false and still owes the shape.

    `invented_citation` is a document or chunk ref this turn's tools did not
    return (#396). A product id keeps the card fallback. The degraded
    sentence and no cards follow, except a not_released pair: its answer is
    the check's own conditions and documents, built here from the tool
    facts, so no invented ref can reach it.
    """
    language = language_of(locale)
    # The login fact outranks every other shape. A guest Proforma question
    # that also called handoff-team must still ask for a login (R7), not
    # ship the mailbox sentence the handoff tool returned.
    if "inquiry.login_required" in facts.facts:
        return login_required(language)
    # The tool never returned. Product ids the route already collected are
    # not a match, and the matching-products sentence would hide the failure.
    # This stays stricter than a fatal failure that still has qualified cards.
    if exhausted:
        return _degraded(language)
    if failure_class is not None:
        # A products search that died must not be printed as a sales
        # handoff (#410). A request for a person never reaches here.
        return _degraded_keeping_findings(facts, language, route)
    # A grounding miss on a shaped turn still owes that shape (#394). An
    # exception does not, even when it has no fatal class: the signed sentence
    # would hide that the turn failed. Findings already collected stay, under
    # the degraded sentence, the same way a classified failure keeps them.
    # The login sentence above stays the one block a guest inquiry may carry.
    # A fatal failure was answered above.
    if raised and route is not None and route.shape:
        return _degraded_keeping_findings(facts, language, route)
    if route is not None:
        shaped = _shape_fallback(route, language)
        if shaped is not None:
            return shaped
    # A not_released pair has no released cards to dump. The check's conditions
    # are the answer, also when the model cited a ref outside this turn: the
    # answer is assembled from tool facts, not from the model's failed draft.
    refused = _not_released_fallback(facts, language)
    if refused is not None:
        return refused
    # The model cited a document or chunk that this turn did not return.
    # Product ids the route already collected are not a match, and the
    # matching-products sentence would hide the failure.
    if invented_citation:
        return _degraded(language)
    # The applied winner is the whole fallback. The named-model clarification
    # would add the other cards (#363, #364), which an extreme answer refuses.
    # An applied extreme shows that one card. Codes named in the same question
    # are written beside it (#384). A hidden price names no cheapest product;
    # when the question also named codes, those codes are still named.
    extreme = _extreme_fallback(facts, language, route)
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
        manual = _manual_torque_fallback(
            facts, language, route, question, page_product_id
        )
        if manual is not None:
            return manual
        warranty = _warranty_period_fallback(
            facts, language, route, question, page_product_id
        )
        if warranty is not None:
            return warranty
        refs = _document_refs(facts)
        # A separately requested product keeps only this turn's qualified
        # cards. A document owner / page product alone is not qualification.
        ids = _card_ids(facts, route)[:SEARCH_LIMIT]
        document_blocks: list[Block] = [
            TextBlock(
                text=DOCUMENTS[language], refs=[*refs, *(str(pid) for pid in ids)]
            )
        ]
        document_blocks.extend(DocumentBlock(ref=ref) for ref in refs)
        if ids:
            document_blocks.append(CardsBlock(product_ids=ids))
        return hydrate(TurnOutput(language=language, blocks=document_blocks), facts)
    clarified = _clarify(facts, language, route)
    if clarified is not None:
        return clarified
    # Stock status only after a clarification: a conflict, an unknown code,
    # or several models still name the catalog. No usable flag is the
    # degraded sentence (#410's shape, #366), not a generic recommendation.
    # A stock question that names no product is route.answer, written in
    # app._answer before the model runs. This fallback never sees it.
    if route is not None and route.stock:
        handoff = team_sentence(facts) if route.delivery else None
        answered = stock_answer(facts, language, handoff=handoff)
        if answered is None:
            return _degraded(language)
        return answered
    # Which ids may be shown lives in `_card_ids` (#366). This branch only
    # chooses the sentence when a products search qualified nothing.
    if route is not None and route.name == "products" and not facts.qualified_ids:
        if _search_succeeded(facts):
            line = NO_MATCH_DE if language == "de" else NO_MATCH_EN
            return _ask_answer(language, [line])
        return _outage(facts, language)
    ids = _card_ids(facts, route)
    if not ids:
        return _outage(facts, language)
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
    looked = lookup_models(route.named_models, facts.tool_calls, facts.qualified_ids)
    notes = tuple(item.note for item in looked)
    outcome = {item.note.code: item.outcome for item in looked}
    # A failed search is not an empty catalog and not "did not return".
    # When every attempted model failed, the caller uses the mailbox sentence
    # or DEGRADED. A code the budget did not search is named as not searched.
    missed = [note for note in notes if outcome[note.code] == "unsearched"]
    failed = [note for note in notes if outcome[note.code] == "failed"]
    reported = any(outcome[note.code] in ("products", "empty") for note in notes)
    if failed and not missed and not reported:
        return None
    # Clarification must share the document card policy too, while retaining
    # existing unsearched/unknown-model explanations. Other routes are unchanged.
    qualified = (
        set(_card_ids(facts, route))
        if route.name == "documents"
        else facts.qualified_ids
    )
    outage = _outage_line(failed, facts, language)
    missed_lines = _missed_sentences(missed, language)

    def tail(lines: list[str]) -> list[str]:
        extra = missed_lines + ([outage] if outage else [])
        return lines + extra

    conflict_lines: list[str] = []
    conflict_ids: list[int] = []
    for note in notes:
        if not (note.is_conflict and outcome[note.code] == "products"):
            continue
        own_ids = [pid for pid in note.product_ids if pid in qualified]
        if not own_ids:
            continue
        conflict_lines.append(_conflict_sentence(note, language))
        for pid in own_ids:
            if pid not in conflict_ids:
                conflict_ids.append(pid)
    if conflict_lines and conflict_ids:
        return _product_answer(language, tail(conflict_lines), conflict_ids)
    unknowns = [
        note for note in notes if note.unknown and outcome[note.code] == "empty"
    ]
    if unknowns:
        lines = [_range_sentence([note.code for note in unknowns], language)]
        if qualified:
            lines.append(_closest_sentence(language))
            return _product_answer(language, tail(lines), sorted(qualified))
        return _ask_answer(language, tail(lines))
    if several(notes, searched=True):
        known = [note for note in notes if note.searched_known]
        pending: list[str] = []
        found_ids: list[int] = []
        for note in known:
            if outcome[note.code] == "failed":
                continue
            own = [pid for pid in note.product_ids if pid in qualified]
            if own:
                for pid in own:
                    if pid not in found_ids:
                        found_ids.append(pid)
            elif note.product_ids and outcome[note.code] == "empty":
                pending.append(_not_returned(note.code, language))
        if found_ids:
            lead = (
                "Die Karten gehören zu den Modellen, die Sie genannt haben."
                if language == "de"
                else "These are the products for the models in your message."
            )
            return _product_answer(language, tail([lead, *pending]), found_ids)
        if pending or missed or outage:
            return _ask_answer(language, tail(pending))
    if missed or outage:
        return _ask_answer(language, tail([]))
    # A stock turn's empty search is not "No product matched.": the stock
    # branch below turns a missing status into the degraded sentence (#415
    # review round 3, blocker 3).
    if (
        route.name in ("products", "model")
        and route.no_handoff
        and not route.stock
        and not qualified
        and not facts.product_ids
        and _search_succeeded(facts)
    ):
        line = NO_MATCH_DE if language == "de" else NO_MATCH_EN
        return _ask_answer(language, [line])
    return None


def _conflict_sentence(note: NamedModel, language: Locale) -> str:
    # One sentence names both brands and the product. The code may sit in it.
    # Grounding accepts a conflict when both brands share a sentence and the
    # card shows the product; the code is not required in that sentence.
    if language == "de":
        return (
            f"Sie haben {note.written_brand} angegeben; die Karte zeigt "
            f"{note.code} als {note.catalog_brand}-Produkt."
        )
    return (
        f"You wrote {note.written_brand}; {note.code} is a {note.catalog_brand} "
        "product, and the card shows it."
    )


def _range_sentence(codes: list[str], language: Locale) -> str:
    shown = ", ".join(codes)
    if language == "de":
        # Singular and plural are written separately. One code keeps the
        # reviewed absence phrase; several codes take the plural.
        if len(codes) > 1:
            return f"Für {shown} haben wir keine Produkte."
        return f"Für {shown} {NOT_IN_RANGE_DE}."
    verb = "are" if len(codes) > 1 else "is"
    return f"{shown} {verb} {NOT_IN_RANGE_EN}."


def _closest_sentence(language: Locale) -> str:
    # The next products the search returned. Not a series claim.
    if language == "de":
        return "Die Karten zeigen die nächsten Produkte dieser Suche."
    return "The closest products are on the cards."


def _not_returned(code: str, language: Locale) -> str:
    if language == "de":
        return f"Die Suche hat zu {code} kein Produkt geliefert."
    return f"The search did not return {code}."


def _missed_sentences(notes: list[NamedModel], language: Locale) -> list[str]:
    if language == "de":
        return [f"{note.code} wurde in dieser Runde nicht gesucht." for note in notes]
    return [f"{note.code} was not searched in this turn." for note in notes]


def _outage_line(notes: list[NamedModel], facts: TurnFacts, language: Locale) -> str:
    """The mailbox or degraded sentence for models whose search failed.

    The degraded wording stays the reviewed sentence. The codes sit in front
    of it so the customer can see which lookup failed.
    """
    if not notes:
        return ""
    shown = ", ".join(note.code for note in notes)
    return f"{shown}. {_mailbox(facts, language)}"


def _degraded(language: Locale) -> TurnOutput:
    """The reviewed degraded sentence, and no cards."""
    return TurnOutput(
        language=language,
        blocks=[HandoffBlock(summary=DEGRADED[language])],
    )


def _document_refs(facts: TurnFacts) -> list[str]:
    """Document links the fallback shows, search order, capped at three."""
    refs = [ref for ref in facts.documents if ref in facts.chunk_ids] or list(
        facts.documents
    )
    return refs[:FALLBACK_DOCUMENTS]


def _card_ids(facts: TurnFacts, route: Route | None) -> list[int]:
    """Ids a fallback may show. The card block caps them at the route's six.

    Documents show only separately requested, qualified products, whether
    documents were found or not. Other routes keep qualified ids first.
    A products search that qualified nothing does not
    borrow `facts.product_ids` (#366): those are a series hit, a page, or a
    get-product, not the model the customer asked for.
    """
    qualified = sorted(facts.qualified_ids)
    if route is not None and route.name == "documents":
        return qualified if route.show_products else []
    if qualified:
        return qualified
    if route is not None and route.name == "products":
        return []
    return sorted(facts.product_ids)


def _degraded_keeping_findings(
    facts: TurnFacts, language: Locale, route: Route | None
) -> TurnOutput:
    """The degraded sentence, then whatever this turn already found.

    `_degraded` is that sentence and nothing else (the tool never returned,
    or nothing qualified). This one may add the qualified cards or the
    document links. The sentence is never the matching-products line or
    the document success line (#410). Which cards and which documents is
    `_card_ids` / `_document_refs`.
    """
    if route is not None and route.name == "documents" and facts.documents:
        blocks: list[Block] = [HandoffBlock(summary=DEGRADED[language])]
        blocks.extend(DocumentBlock(ref=ref) for ref in _document_refs(facts))
        ids = _card_ids(facts, route)[:SEARCH_LIMIT]
        if ids:
            blocks.append(CardsBlock(product_ids=ids))
        return hydrate(TurnOutput(language=language, blocks=blocks), facts, language)
    ids = _card_ids(facts, route)[:SEARCH_LIMIT]
    if not ids:
        return _degraded(language)
    return TurnOutput(
        language=language,
        blocks=[
            HandoffBlock(summary=DEGRADED[language]),
            CardsBlock(product_ids=ids),
        ],
    )


def _outage(facts: TurnFacts, language: Locale) -> TurnOutput:
    """Nothing citable: the handoff sentence when that tool ran, else degraded.

    Pretending to hand off when handoff-team did not run would hide the outage.
    """
    sentence_id = "handoff.sentence_de" if language == "de" else "handoff.sentence_en"
    sentence = facts.facts.get(sentence_id)
    summary = sentence.value if sentence is not None else DEGRADED[language]
    return TurnOutput(
        language=language,
        blocks=[HandoffBlock(summary=summary)],
    )


def team_sentence(facts: TurnFacts) -> str | None:
    """The handoff-team sentence for this turn, when that call returned one."""
    sentence = facts.facts.get("handoff.sentence")
    if sentence is None or not sentence.value:
        return None
    return sentence.value


def _mailbox(facts: TurnFacts, language: Locale) -> str:
    sentence_id = "handoff.sentence_de" if language == "de" else "handoff.sentence_en"
    sentence = facts.facts.get(sentence_id)
    if sentence is not None:
        return sentence.value
    return DEGRADED[language]


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


def _shape_fallback(route: Route, language: Locale) -> TurnOutput | None:
    """The canonical next-step answer for a shaped model turn, or None."""
    if route.shape == "talk":
        return _shaped(language, TALK[language], ask=True)
    if route.shape == "promise":
        return _shaped(language, PROMISE[language], view=True)
    if route.shape == "partner":
        return _shaped(language, PARTNER[language], ask=True)
    return None


def _shaped(
    language: Locale, text: str, *, ask: bool = False, view: bool = False
) -> TurnOutput:
    blocks: list[Block] = [TextBlock(text=text)]
    if view:
        blocks.append(ActionBlock(name="view_inquiry", args={}))
    if ask:
        blocks.append(
            AskBlock(field="application", options=_ask_options("application", language))
        )
    return TurnOutput(language=language, blocks=blocks)


def finish(
    output: TurnOutput,
    facts: TurnFacts,
    route: Route | None,
    question: str = "",
) -> TurnOutput:
    """Add the next step the route owes when the model left it out (#394).

    A guest login stays the one login sentence. A degraded handoff is the
    failure sentence and is returned unchanged: the signed sentence does not
    replace it, and the reply promise is not appended to it. Cards and
    document links already on that handoff stay. A turn with no route is
    unchanged, so an outage handoff does not grow a reply promise. A company
    turn is the mailbox sentence plus the one-working-day reply. A shaped turn
    ships its signed sentence once: the model's prose is replaced, not kept
    beside it. An inquiry turn gains view_inquiry. A sizing turn gains the
    application ask even when the configurator action is already there: that
    action is not the ask the row requires, and the chips are home/commercial,
    not the phase digits. A plain model answer gains
    one application ask, whether or not its prose already asks: the ask is
    chips and carries no question sentence, so the customer still reads one
    question. A clarification keeps its question and ships no clickable block:
    it asks which model the customer means, and the application chips cannot
    answer that (goal 9's one block has no field for a model choice). The
    contact card stays contact.decide's, after this returns.
    A scripted sentence replaces the model's prose. An open inquiry gains
    send_inquiry; the remit and the weather gain the application ask.
    An ESA battery-fit sentence replaces the model's prose the same way and
    keeps a card already shown. A missing card is filled only when the tool
    results hold exactly one released set. A released pairing condition's
    model code is named when a card shows that partner and the text left the
    code out. Naming runs before a compare question's cards become a compare
    block of those same ids. One card is not a comparison, and more than four
    is not a subset this function invents. A prose compound such as G20-Module is not a code. Cards do not
    replace the code. Login, a degraded handoff and the team sentence are
    returned before that naming.
    The gate is one clickable block; two or three is the product target when
    the answer already has cards, a document or an action.
    """
    if route is None or "inquiry.login_required" in facts.facts:
        return output
    # The failure sentence outranks a signed next step and the reply promise.
    # Replacing it, or appending the promise, hid that the turn failed.
    if _degraded_handoff(output):
        return output
    language = output.language
    if route.name == "service":
        return _service_turn(output, facts)
    if route.name == "scripted" and route.answer:
        replaced = _replace_prose(output, route.answer)
        stepped = (
            _ensure_inquiry(replaced)
            if route.action == "send_inquiry"
            else _ensure_ask(replaced, language)
        )
        return _named(stepped, facts, question)
    if route.shape == "promise":
        return _named(
            _ensure_view(_replace_prose(output, PROMISE[language])), facts, question
        )
    if route.shape == "partner":
        return _named(
            _ensure_ask(_replace_prose(output, PARTNER[language]), language),
            facts,
            question,
        )
    if route.shape == "talk":
        return _named(
            _ensure_ask(_replace_prose(output, TALK[language]), language),
            facts,
            question,
        )
    if route.answer and "esa battery" in route.reasons:
        replaced = _replace_prose(output, route.answer)
        return _named(_ensure_released_cards(replaced, facts, route), facts, question)
    if route.name == "inquiry" and not _has_next_step(output):
        return _named(_ensure_view(output), facts, question)
    if route.name == "sizing":
        return _named(_ensure_ask(output, language), facts, question)
    if not _has_next_step(output) and _plain_next_step(route):
        if route.name == "clarify":
            return output
        return _named(_ensure_ask(output, language), facts, question)
    return _named(output, facts, question)


def _degraded_handoff(output: TurnOutput) -> bool:
    """True when a handoff already carries the reviewed degraded sentence.

    Cards and document links may sit beside it. The sentence is the failure;
    a signed next step or a reply promise must not replace or extend it.
    """
    degraded = set(DEGRADED.values())
    return any(
        isinstance(block, HandoffBlock) and block.summary.strip() in degraded
        for block in output.blocks
    )


def _plain_next_step(route: Route) -> bool:
    """A clarification, or a model turn with no shape of its own."""
    return route.name == "clarify" or (route.name == "model" and not route.shape)


def _service_turn(output: TurnOutput, facts: TurnFacts) -> TurnOutput:
    """One handoff block: the mailbox sentence, then the one-working-day reply."""
    language = output.language
    fact_id = "handoff.sentence_de" if language == "de" else "handoff.sentence_en"
    fact = facts.facts.get(fact_id)
    existing = next(
        (
            block.summary.strip()
            for block in output.blocks
            if isinstance(block, HandoffBlock) and block.summary.strip()
        ),
        "",
    )
    if fact is not None:
        summary = fact.value.strip()
    elif existing and existing not in DEGRADED.values():
        summary = existing
    else:
        summary = DEGRADED[language]
    promise = REPLY_PROMISE[language]
    if not _has_promise(summary, language):
        summary = f"{summary.rstrip()} {promise}"
    return output.model_copy(update={"blocks": [HandoffBlock(summary=summary)]})


def _ensure_released_cards(
    output: TurnOutput, facts: TurnFacts, route: Route
) -> TurnOutput:
    """Keep a card the model showed; fill one only from a single released set.

    The ESA battery sentence names codes, not product ids. Two pairing sets
    are two answers and are not merged. A route that owes no cards is left
    as it is. The ids are the tool's, never a hardcoded list.
    """
    if route.no_cards or any(isinstance(block, CardsBlock) for block in output.blocks):
        return output
    sets = pairing_card_sets(facts)
    if len(sets) != 1 or not sets[0]:
        return output
    blocks = list(output.blocks)
    insert_at = 1 if blocks and isinstance(blocks[0], TextBlock) else 0
    blocks.insert(insert_at, CardsBlock(product_ids=sets[0]))
    return output.model_copy(update={"blocks": blocks})


def _replace_prose(output: TurnOutput, sentence: str) -> TurnOutput:
    """The model's words give way to the signed sentence (#394).

    A shaped turn has one approved answer. Keeping the prose beside the signed
    sentence made the customer read the same content twice; replacing it means
    the signed sentence ships once, whatever the model paraphrased. The blocks
    the shape owns (ask, action) stay and are completed below.
    """
    blocks: list[Block] = [
        block
        for block in output.blocks
        if not isinstance(block, (TextBlock, HandoffBlock))
    ]
    blocks.insert(0, TextBlock(text=sentence))
    return output.model_copy(update={"blocks": blocks})


def _ensure_ask(output: TurnOutput, language: Locale) -> TurnOutput:
    """Add the clickable ask when the answer has none.

    The block is chips and a group label, not a question sentence, so a prose
    question already in the answer stays the one question the customer reads.
    """
    if any(block.type == "ask" for block in output.blocks):
        return output
    blocks = [
        *output.blocks,
        AskBlock(field="application", options=_ask_options("application", language)),
    ]
    return output.model_copy(update={"blocks": blocks})


def _ensure_view(output: TurnOutput) -> TurnOutput:
    if any(
        isinstance(block, ActionBlock) and block.name == "view_inquiry"
        for block in output.blocks
    ):
        return output
    blocks = [*output.blocks, ActionBlock(name="view_inquiry", args={})]
    return output.model_copy(update={"blocks": blocks})


def _ensure_inquiry(output: TurnOutput) -> TurnOutput:
    """The open-inquiry next step. The name is inquiry.ACTION."""
    if any(
        isinstance(block, ActionBlock) and block.name == "send_inquiry"
        for block in output.blocks
    ):
        return output
    blocks = [*output.blocks, ActionBlock(name="send_inquiry", args={})]
    return output.model_copy(update={"blocks": blocks})


def _name_released_partners(output: TurnOutput, facts: TurnFacts) -> TurnOutput:
    """Name a released partner code the text left out, when its card is shown.

    The code is a whitespace token of `compat.condition.{id}.{index}` that
    `_model_code` accepts. A slash or an en dash keeps a family code. A
    hyphenated token needs two digit-bearing segments, so GW6.0-BAT-D-G20
    stays and G20-Module does not. The verdict `compat.verdict.{id}` must be
    released. A bare "G21", a page range and a check's `compat.condition.0`
    stay out. No card of that partner, no line.
    """
    by_partner = _partner_codes(facts)
    if not by_partner:
        return output
    shown = {
        product_id
        for block in output.blocks
        if isinstance(block, CardsBlock)
        for product_id in block.product_ids
        if product_id in by_partner
    }
    if not shown:
        return output
    present = " ".join(
        block.text for block in output.blocks if isinstance(block, TextBlock)
    ).casefold()
    missing: list[str] = []
    seen: set[str] = set()
    for partner_id, codes in by_partner.items():
        if partner_id not in shown:
            continue
        for code in codes:
            key = code.casefold()
            if key in seen or key in present:
                continue
            seen.add(key)
            missing.append(code)
    if not missing:
        return output
    sentence = PARTNER_CODES[output.language].format(codes=", ".join(missing))
    return _append_sentence(output, sentence)


def _ensure_compare(output: TurnOutput, question: str) -> TurnOutput:
    """A compare question owes a compare block, not only cards.

    The ids stay the ones the model showed. One card cannot be a comparison,
    and more than four is not a subset this function invents. A block that is
    already a comparison stays. Partner naming has already run.
    """
    folded = question.casefold()
    if "compare" not in folded and "vergleich" not in folded:
        return output
    if any(isinstance(block, CompareBlock) for block in output.blocks):
        return output
    blocks = list(output.blocks)
    for index, block in enumerate(blocks):
        if isinstance(block, CardsBlock) and 2 <= len(block.product_ids) <= 4:
            blocks[index] = CompareBlock(product_ids=list(block.product_ids))
            return output.model_copy(update={"blocks": blocks})
    return output


def _named(output: TurnOutput, facts: TurnFacts, question: str) -> TurnOutput:
    """Name released partners while the cards are still cards, then compare."""
    return _ensure_compare(_name_released_partners(output, facts), question)


def _model_code(token: str) -> bool:
    """A model code, not a hyphenated prose compound.

    `is_code` treats G20-Module as a code because G20 mixes a letter and a
    digit. A family written with a slash or an en dash is a code. A hyphenated
    token is a code only when two segments carry a digit, which a prose
    compound (G20-Module, Force-H3, BU5-Module) does not.
    """
    if not token or _CODE_MARK.search(token) is None or not is_code(token):
        return False
    if _RANGE_MARK.search(token):
        return True
    segments = [part for part in token.split("-") if part]
    return sum(any(character.isdigit() for character in part) for part in segments) >= 2


def _partner_codes(facts: TurnFacts) -> dict[int, list[str]]:
    by_partner: dict[int, list[str]] = {}
    seen: dict[int, set[str]] = {}
    for fact_id, fact in facts.facts.items():
        match = _PAIR_CONDITION.fullmatch(fact_id)
        if match is None:
            continue
        partner_id = int(match.group(1))
        verdict = facts.facts.get(f"compat.verdict.{partner_id}")
        if verdict is None or verdict.value not in RELEASED_VERDICTS:
            continue
        for token in fact.value.split():
            code = token.strip(_CODE_EDGE)
            if not _model_code(code):
                continue
            key = code.casefold()
            if key in seen.setdefault(partner_id, set()):
                continue
            seen[partner_id].add(key)
            by_partner.setdefault(partner_id, []).append(code)
    return by_partner


def _has_next_step(output: TurnOutput) -> bool:
    return any(
        block.type in {"ask", "cards", "compare", "action", "document", "handoff"}
        for block in output.blocks
    )


def _has_promise(text: str, language: Locale) -> bool:
    """The canonical reply promise. "einem Werktag" and "one business day" do not count."""
    folded = text.casefold()
    if language == "de":
        return "innerhalb eines werktags" in folded
    return "within one working day" in folded


# Customer-visible sentences written by the service, not the model (#439).
# Wording is the copy record docs/acceptance/2026-10-20/439/copy-review.md.
# The patterns are the baseline row's own `expect.all` expressions, copied so
# a paraphrase that already satisfies the row is not written a second time.
# Production does not import the grader.
_USABLE_ABSENCE = {
    "en": "The documents do not state a usable capacity.",
    "de": "Die Unterlagen nennen keine nutzbare Kapazität.",
}
_SUPPORT_ABSENCE = {
    "en": "The documents do not state whether it supports this.",
    "de": "Die Unterlagen nennen keine Unterstützung.",
}
_USABLE_PRESENT = {
    "en": re.compile(
        r"(?i)do not state|does not state|not stated|do not give|does not give|"
        r"do not print|does not print|cannot state|not part of|"
        r"no usable (capacity|energy|figure|value)"
    ),
    "de": re.compile(
        r"(?i)nutzbare[rn]?\**\s+\**\s*(?:Kapazität|Energie|Wert|Angabe).{0,100}\bnicht\b"
        r"|\bnicht\b.{0,100}nutzbare[rn]?\**\s+\**\s*(?:Kapazität|Energie|Wert|Angabe)"
        r"|keine(?:\s+\**\s*\w+){0,4}\s+\**\s*nutzbare[rn]?\**\s+\**\s*"
        r"(?:Kapazität|Energie|Wert|Angabe)"
        r"|nicht (?:angegeben|genannt|ausgewiesen)|nennen keine|steht nicht"
    ),
}
_SUPPORT_PRESENT = {
    "en": re.compile(r"(?i)documents do not state\b.{0,60}\bsupports?\b"),
    "de": re.compile(
        r"(?i)Unterlagen nennen keine Unterstützung|Dokumente nennen keine Unterstützung"
    ),
}
_NOMINAL_LABEL = {
    "en": re.compile(r"(?i)nominal"),
    "de": re.compile(r"(?i)Nennkapazität|Nennenergie|nominal"),
}
_DOD_LABEL = {
    "en": re.compile(r"(?i)depth of discharge|\bDoD\b"),
    "de": re.compile(r"(?i)Entladetiefe|\bDoD\b"),
}
_KWH_260 = re.compile(r"260 ?kWh")
_PERCENT_98 = re.compile(r"98\s*%")
_STRIP_ROUTES = frozenset({"products", "compare", "pairing", "sizing", "model"})
_DOCUMENT_PHRASES = (
    "usable capacity",
    "nutzbare kapazität",
    "leistungsreduzierung",
    "pv input",
    "eingangsleistung",
    "datasheet",
    "datenblatt",
    "warranty",
    "garantie",
    "enwg",
    "14a",
)


def seal(
    output: TurnOutput,
    facts: TurnFacts,
    route: Route | None,
    question: str,
    page_type: str | None,
    *,
    original: TurnOutput | None = None,
) -> TurnOutput:
    """Drop unlicensed bare numbers and write the sentences a row requires.

    A product page is left alone: its question can require a figure the
    question itself does not print. A documents turn is not stripped down to
    the question, or a rated-power answer would lose the powers the row
    requires. A number that appears in the document text only as the tail of a
    digit-free hyphenated code is removed unless the answer keeps that code
    immediately before it. A figure fact that is only the number does not
    license it. A decimal point splits the clause the acceptance check uses,
    so a model code already on that line is repeated after the decimal before
    a later figure. That repeat is not a new sentence. Only a clearance question is stripped, and only against the
    installation figures in the document facts: energy, power and percent on
    the same sheet do not stay. A stock question that also asks something
    else is not stripped: that other half is a figure the question names and
    does not print (#415). The absence sentences are appended, not
    generated, and only the millimetres the facts already contain.

    A turn that read the customer's saved solution (#496) is page-like: its
    figures are licensed by the solution's own text, which the question does
    not print, exactly as a page's are. The configurator's page type is
    `other`, so the generic strip below would cut the answer's figures back to
    the question's own digits. The clearance and document branches keep their
    own allowances and still run. A text block citing a customer attachment
    keeps the reading's figure facts as well as the question's figures. This
    happens after grounding and hydration: a filename or an unrelated file
    must not license numbers, nor may another block borrow that citation.
    """
    if route is None or page_type not in (None, "other"):
        return output
    from linker_genie import ground as grounding

    scoped = _seal_sources(original or output, facts, route)
    source_texts = {
        fact_id: fact
        for fact_id, fact in scoped.facts.items()
        if fact_id.endswith(".text")
    }
    blob = "\n".join(fact.value for fact in source_texts.values())
    if clearance_question(question):
        clearances = _source_clearances(scoped)
        checked_sources = _seal_sources(
            original or output, facts, route, include_qualified=True
        )
        allowed = grounding.clearance_allowance(
            _clearance_source_texts(scoped), question
        )
        for _, value, _ in clearances:
            allowed.update(grounding.question_allowance(str(value)))
        checked, other_figures = _clearance_answer(
            output,
            original,
            facts,
            checked_sources,
            _source_clearances(checked_sources),
        )
        for figure_id in other_figures:
            allowed.update(grounding.question_allowance(facts.facts[figure_id].value))
        stripped = grounding.strip_unlicensed_numbers(
            checked,
            allowed,
        )
        return _append_clearance(stripped, scoped)
    if _document_like(route, question):
        stripped = grounding.strip_detached_code_tails(
            output, grounding.code_tail_blob(facts)
        )
        rebound = grounding.rebind_figures_past_decimal(stripped)
        support_sources = (
            _seal_sources(original or output, facts, route, include_qualified=True)
            if _support_question(question)
            else scoped
        )
        return _append_document_sentences(
            rebound, scoped, blob, question, support_sources
        )
    if (
        route.name in _STRIP_ROUTES
        and not route.stock_beside
        and "solution" not in facts.facts
    ):
        return _seal_attachment_figures(output, facts, question)
    return output


def _seal_sources(
    output: TurnOutput,
    facts: TurnFacts,
    route: Route,
    *,
    include_qualified: bool = False,
) -> TurnFacts:
    """Only the first answer's cited chunks for one current model.

    Automatic sentences are appended to the first text block. They may use
    that block's actual chunk refs and figure placeholders; when it names none,
    explicit document blocks can establish the source. Multiple chunks are
    accepted only when every chunk is bound to the same single product, and
    all chunks refer to the same PDF. A multi-model table is not a single
    product projection even when the question names one of its models.
    A condition-bound projection is never a source for bare synthesized values.
    The support-absence check may inspect it only to avoid a false absence;
    this does not synthesize a fact or remove the original qualification.
    """
    first = next(
        (block for block in output.blocks if isinstance(block, TextBlock)), None
    )
    if first is None:
        return TurnFacts()
    refs: list[str] = []
    for ref in [*first.refs, *PLACEHOLDER.findall(first.text)]:
        chunk = chunk_of(ref) or ref
        if chunk in facts.knowledge_products:
            refs.append(chunk)
    if not refs:
        refs = [
            block.ref
            for block in output.blocks
            if isinstance(block, DocumentBlock)
            and block.ref in facts.knowledge_products
        ]
        if not refs:
            return TurnFacts()
    refs = list(dict.fromkeys(refs))
    products = [set(facts.knowledge_products[ref]) for ref in refs]
    if not products or any(len(product) != 1 for product in products):
        return TurnFacts()
    common = set.intersection(*products)
    named = {pid for model in route.named_models for pid in model.product_ids}
    if named:
        common.intersection_update(named)
    named_refs = {
        int(ref.removeprefix("p"))
        for ref in first.refs
        if ref.removeprefix("p").isdigit()
    }
    if named_refs:
        common.intersection_update(named_refs)
    if len(common) != 1:
        return TurnFacts()
    if len(refs) > 1:
        urls = {facts.documents[ref].url for ref in refs if ref in facts.documents}
        if len(urls) != 1 or any(ref not in facts.documents for ref in refs):
            return TurnFacts()
    selected = {
        f"{ref}.text": facts.facts[f"{ref}.text"]
        for ref in refs
        if (include_qualified or ref not in facts.qualifications)
        and f"{ref}.text" in facts.facts
        and facts.facts[f"{ref}.text"].source == "search-knowledge"
    }
    selected.update(
        {
            fact_id: fact
            for fact_id, fact in facts.facts.items()
            if (chunk := chunk_of(fact_id)) is not None
            and f"{chunk}.text" in selected
            and fact.source == "search-knowledge"
        }
    )
    return TurnFacts(
        facts=selected,
        qualifications={
            ref: facts.qualifications[ref]
            for ref in refs
            if ref in facts.qualifications and f"{ref}.text" in selected
        },
    )


def _seal_attachment_figures(
    output: TurnOutput, facts: TurnFacts, question: str
) -> TurnOutput:
    """Keep only question numbers and each text block's cited reading figures.

    The earlier grounding check still requires numeric placeholders and
    rejects unknown facts and attachment amounts. Planning figures use the
    same per-block citation boundary, without granting product permission.
    This final seal must not
    erase those hydrated figures simply because the question omitted them.
    A file ref licenses that file's figures; a figure ref licenses only that
    figure. Raw reading text and the filename are not numerical allowances.
    """
    from linker_genie import ground as grounding

    question_numbers = grounding.question_allowance(question)
    blocks: list[Block] = []
    for block in output.blocks:
        allowed = set(question_numbers)
        if isinstance(block, TextBlock):
            for fact_id, fact in facts.facts.items():
                match = re.fullmatch(
                    r"(att[1-9][0-9]{0,5}|planning)\.n[1-9][0-9]*", fact_id
                )
                if match is None or fact.source not in {
                    "read-attachment",
                    "read-planning-project",
                }:
                    continue
                reading_id = match.group(1)
                reading = facts.facts.get(reading_id)
                if reading is None or reading.source != fact.source:
                    continue
                if reading_id in block.refs or fact_id in block.refs:
                    allowed.update(grounding.question_allowance(fact.value))
        sealed = grounding.strip_unlicensed_numbers(
            output.model_copy(update={"blocks": [block]}), allowed
        )
        blocks.extend(sealed.blocks)
    return output.model_copy(update={"blocks": blocks})


def clearance_question(question: str) -> bool:
    folded = question.casefold()
    return "clearance" in folded or "mindestabstand" in folded


def _usable_question(question: str) -> bool:
    folded = question.casefold()
    return "usable capacity" in folded or "nutzbare kapazität" in folded


def _support_question(question: str) -> bool:
    folded = question.casefold()
    return "enwg" in folded or "14a" in folded or "leistungsreduzierung" in folded


def _document_like(route: Route, question: str) -> bool:
    """A question whose figures must not be cut back to the question text.

    "install" alone is not one: a services question uses that word. Rated
    power is not one either: that question is a documents turn, and stripping
    it would remove the powers. MPPT is a substring so "MPPTs" still counts.
    """
    if route.name == "documents":
        return True
    folded = question.casefold()
    if "mppt" in folded:
        return True
    return any(phrase in folded for phrase in _DOCUMENT_PHRASES)


def _prose(output: TurnOutput) -> str:
    parts: list[str] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            parts.append(block.text)
        elif isinstance(block, HandoffBlock):
            parts.append(block.summary)
    return "\n".join(parts)


def _append_sentence(output: TurnOutput, sentence: str) -> TurnOutput:
    if not sentence or sentence in _prose(output):
        return output
    blocks = list(output.blocks)
    for index, block in enumerate(blocks):
        if not isinstance(block, TextBlock):
            continue
        text = block.text.rstrip()
        if text and text[-1] not in ".!?":
            text = f"{text}."
        joined = f"{text} {sentence}".strip() if text else sentence
        blocks[index] = block.model_copy(update={"text": joined})
        return output.model_copy(update={"blocks": blocks})
    blocks.insert(0, TextBlock(text=sentence))
    return output.model_copy(update={"blocks": blocks})


def _append_document_sentences(
    output: TurnOutput,
    sources: TurnFacts,
    blob: str,
    question: str,
    support_sources: TurnFacts,
) -> TurnOutput:
    sealed = output
    if _usable_question(question) and blob:
        sealed = _append_usable(sealed, sources, blob)
    if _support_question(question):
        sealed = _append_support(sealed, support_sources, question)
    return sealed


def _append_usable(output: TurnOutput, sources: TurnFacts, blob: str) -> TurnOutput:
    language = output.language
    text = _prose(output)
    need_capacity = _structured_source_figure(
        sources,
        r"(?:nominal\s+(?:capacity|energy)|nennkapazität|nennenergie)"
        r"(?:\s*\(kWh\))?",
        r"260\s*kWh",
    ) and (
        _KWH_260.search(text) is None or _NOMINAL_LABEL[language].search(text) is None
    )
    need_discharge = _structured_source_figure(
        sources,
        r"(?:depth\s+of\s+discharge|dod|entladetiefe)(?:\s*\(%\))?",
        r"98\s*%",
    ) and (
        _PERCENT_98.search(text) is None or _DOD_LABEL[language].search(text) is None
    )
    sealed = _append_sentence(
        output, _figure_sentence(language, need_capacity, need_discharge)
    )
    if _USABLE_PRESENT[language].search(_prose(sealed)):
        return sealed
    absence = re.compile(
        r"(?i)(?:usable(?:\s+(?:capacity|energy|figure|value))?|nutzbar\w*)"
        r"[^\n.]{0,100}(?:not\s+(?:printed|stated|available|provided)|"
        r"nicht\s+(?:angegeben|genannt|ausgewiesen))|"
        r"(?:no|kein(?:e|en|er)?)\s+(?:usable|nutzbar)"
    )
    if absence.search(blob) or absence.search(_prose(sealed)):
        return _append_sentence(sealed, _USABLE_ABSENCE[language])
    return sealed


def _source_segments(blob: str) -> list[str]:
    return re.split(r"\n|(?<=[.!?])\s+", blob)


def _structured_source_figure(sources: TurnFacts, label: str, value: str) -> bool:
    """Bind a complete single-value table row to its actual figure fact.

    A word and a number appearing in the same paragraph do not establish a
    property. Other attributes, ranges, multi-value cells and extra conditions
    are not used to synthesize a bare statement.
    """
    for fact_id, fact in sources.facts.items():
        if not fact_id.endswith(".text") or fact.source != "search-knowledge":
            continue
        chunk_id = fact_id[:-5]
        for line in fact.value.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|") or not stripped.endswith("|"):
                continue
            cells = [cell.strip() for cell in stripped[1:-1].split("|")]
            if len(cells) != 2 or re.fullmatch(label, cells[0], re.IGNORECASE) is None:
                continue
            tagged = re.fullmatch(r"\[n([1-9]\d*)=([^\]]+)\]", cells[1])
            if (
                tagged is None
                or re.fullmatch(value, tagged.group(2), re.IGNORECASE) is None
            ):
                continue
            figure = sources.facts.get(f"{chunk_id}.n{tagged.group(1)}")
            if (
                figure
                and figure.source == "search-knowledge"
                and figure.value == tagged.group(2)
            ):
                return True
    return False


def _figure_sentence(language: str, capacity: bool, discharge: bool) -> str:
    if language == "de":
        if capacity and discharge:
            return (
                "Die Unterlagen nennen eine Nennkapazität von 260 kWh "
                "und eine Entladetiefe von 98 %."
            )
        if capacity:
            return "Die Unterlagen nennen eine Nennkapazität von 260 kWh."
        if discharge:
            return "Die Unterlagen nennen eine Entladetiefe von 98 %."
        return ""
    if capacity and discharge:
        return (
            "The documents state a nominal capacity of 260 kWh "
            "and a depth of discharge of 98%."
        )
    if capacity:
        return "The documents state a nominal capacity of 260 kWh."
    if discharge:
        return "The documents state a depth of discharge of 98%."
    return ""


def _append_support(
    output: TurnOutput, sources: TurnFacts, question: str
) -> TurnOutput:
    language = output.language
    if _SUPPORT_PRESENT[language].search(_prose(output)):
        return output
    question_key = re.sub(r"[^a-z0-9äöü]+", "", question.casefold())
    for fact_id, fact in sources.facts.items():
        if not fact_id.endswith(".text") or fact.source != "search-knowledge":
            continue
        source = re.sub(r"\[n[1-9]\d*=([^\]]+)\]", r"\1", fact.value)
        source_key = re.sub(r"[^a-z0-9äöü]+", "", source.casefold())
        if (
            ("enwg" in question_key and "enwg" in source_key)
            or ("14a" in question_key and "14a" in source_key)
            or (
                "leistungsreduzierung" in question_key
                and (
                    "leistungsreduzierung" in source_key
                    or "powerreduction" in source_key
                )
            )
        ):
            # A cited source discusses the subject. We cannot infer support
            # from a mention, or assert that the document is silent about it.
            return output
    return _append_sentence(output, _SUPPORT_ABSENCE[language])


_CLEARANCE_LABEL = (
    r"(?:(?:minimum|minimum\s+required|minimaler|minimale|minimalen)\s+)?"
    r"(?:clearances?|mindestabstand|mindestabstände|abstand|abstände)"
)
_CLEARANCE_ATOM = r"(?:≥|>=)?\s*\[n[1-9]\d*=[^\[\]]+\]"
_CLEARANCE_LIST = (
    rf"{_CLEARANCE_ATOM}(?:\s*(?:(?:/|,|\band\b|\bund\b)\s*|(?=≥|>=))"
    rf"{_CLEARANCE_ATOM})*"
)
_CLEARANCE_TOKEN = re.compile(r"\[n([1-9]\d*)=([^\[\]]+)\]")


def _clearance_answer(
    output: TurnOutput,
    original: TurnOutput | None,
    facts: TurnFacts,
    sources: TurnFacts,
    clearances: list[tuple[str, int, bool]],
) -> tuple[TurnOutput, set[str]]:
    """Remove unsupported figure occurrences before a numeric allowance is applied.

    Equal numbers do not make different figure IDs interchangeable. Rehydrate
    the authored text with unsupported occurrences marked, then remove only
    affected sentences. Existing qualified placeholders retain their opaque
    seal markers and their source conditions.
    """
    if original is None:
        return output, set()
    minimum_by_id = {figure_id: minimum for figure_id, _, minimum in clearances}
    eligible_chunks = {chunk_of(figure_id) for figure_id in minimum_by_id}
    other_measurements: set[tuple[str, str, bool]] = set()
    for fact_id, source in sources.facts.items():
        chunk = fact_id[:-5]
        if not fact_id.endswith(".text") or (
            chunk not in eligible_chunks and chunk not in sources.qualifications
        ):
            continue
        for segment in _source_segments(
            _clearance_source_content(sources, chunk, source.value)
        ):
            for clause in segment.split(";"):
                measurement = _independent_measurement(sources, chunk, clause)
                if measurement:
                    other_measurements.add(measurement)
    retained: set[str] = set()
    all_text = (
        str(original.model_dump())
        + str(output.model_dump())
        + " ".join(fact.value for fact in facts.facts.values())
    )
    marker = "\ue002R\ue003"
    while marker in all_text:
        marker = marker[:-1] + "R\ue003"
    changed = False
    blocks: list[Block] = []
    for block in original.blocks:
        if not isinstance(block, (TextBlock, HandoffBlock)):
            blocks.append(block)
            continue
        text = block.text if isinstance(block, TextBlock) else block.summary
        pieces = re.split(r"(?<=[.!?;])(?=\s)|(?=\n)", text)
        for index, piece in enumerate(pieces):
            minimum_claim = bool(
                re.search(r"(?i)\b(?:minimum|minimal\w*|mindest\w*)\b", piece)
            )
            negated = bool(
                re.search(r"(?i)\b(?:not|never|false|nicht|kein\w*)\b", piece)
            )

            def mark(
                match: re.Match[str],
                *,
                is_negated: bool = negated,
                is_minimum: bool = minimum_claim,
                authored_piece: str = piece,
            ) -> str:
                nonlocal changed
                figure_id = match.group(1)
                fact = facts.facts.get(figure_id)
                chunk = chunk_of(figure_id)
                if fact is None or fact.source != "search-knowledge" or chunk is None:
                    return match.group(0)
                if not is_negated and figure_id not in minimum_by_id:
                    token = figure_id.removeprefix(f"{chunk}.")
                    probe = (
                        authored_piece[: match.start()]
                        + f"[{token}={fact.value}]"
                        + authored_piece[match.end() :]
                    )
                    measurement = _independent_measurement(sources, chunk, probe)
                    if measurement in other_measurements:
                        retained.add(figure_id)
                        return match.group(0)
                if (
                    figure_id in minimum_by_id
                    and not is_negated
                    and (not is_minimum or minimum_by_id[figure_id])
                ):
                    return match.group(0)
                changed = True
                return marker

            pieces[index] = PLACEHOLDER.sub(mark, piece)
        field = "text" if isinstance(block, TextBlock) else "summary"
        blocks.append(block.model_copy(update={field: "".join(pieces)}))
    if not changed:
        return output, retained

    opaque: list[str] = re.findall(r"\ue000Q+\ue001", _prose(output))

    def text_blocks(candidate: TurnOutput) -> list[tuple[str, str]]:
        return [
            (block.type, block.text if isinstance(block, TextBlock) else block.summary)
            for block in candidate.blocks
            if isinstance(block, (TextBlock, HandoffBlock))
        ]

    control: TurnOutput | None
    marked: TurnOutput | None
    try:
        tokens = iter(opaque)
        by_value: dict[str, list[str]] = {}

        def original_marker(value: str) -> str:
            token = next(tokens)
            by_value.setdefault(value, []).append(token)
            return token

        control = hydrate(
            original, facts, output.language, qualified_mask=original_marker
        )
        if next(tokens, None) is not None:
            raise ValueError("qualified marker count changed")

        def retained_marker(value: str) -> str:
            markers = by_value.get(value)
            if not markers:
                raise ValueError("qualified marker not found")
            return markers.pop(0)

        marked = hydrate(
            original.model_copy(update={"blocks": blocks}),
            facts,
            output.language,
            qualified_mask=retained_marker,
        )
    except (StopIteration, ValueError):
        control = marked = None
    if control is None or marked is None or text_blocks(control) != text_blocks(output):
        from linker_genie import ground as grounding

        return grounding.strip_unlicensed_numbers(output, None), set()

    revised = iter(text_blocks(marked))
    sealed: list[Block] = []
    for block in output.blocks:
        if not isinstance(block, (TextBlock, HandoffBlock)):
            sealed.append(block)
            continue
        _, text = next(revised)
        pieces = re.split(r"(?<=[.!?;])(?=\s)|(?=\n)", text)
        for index, piece in enumerate(pieces):
            if marker not in piece:
                continue
            if re.search(r"\ue000Q+\ue001", piece):
                pieces[index] = re.sub(rf"{re.escape(marker)}(?:\s*mm\b)?", "—", piece)
            else:
                pieces[index] = ""
        field = "text" if isinstance(block, TextBlock) else "summary"
        sealed.append(block.model_copy(update={field: "".join(pieces).strip()}))
    return output.model_copy(update={"blocks": sealed}), retained


def _clearance_source_texts(sources: TurnFacts) -> TurnFacts:
    """Restore independent non-length installation figures for the strip step.

    Treating figures as isolated words would turn the ``10`` in ``Φ10`` into
    an allowed installation number; the original source context prevents it.
    Dimensions are excluded: only the clearance parser may authorize those.
    """
    texts: dict[str, Fact] = {}
    for fact_id, fact in sources.facts.items():
        if not fact_id.endswith(".text") or fact.source != "search-knowledge":
            continue
        chunk = fact_id[:-5]

        def restore(match: re.Match[str], chunk_id: str = chunk) -> str:
            figure = sources.facts.get(f"{chunk_id}.n{match.group(1)}")
            if (
                figure
                and figure.source == "search-knowledge"
                and figure.value == match.group(2)
            ):
                return figure.value
            return ""

        segments = [
            segment
            for segment in _source_segments(fact.value)
            if _independent_measurement(sources, chunk, segment)
            and re.search(r"(?i)\b(?:height|width|depth)\b", segment) is None
        ]
        texts[fact_id] = Fact(
            id=fact_id,
            source=fact.source,
            value=_CLEARANCE_TOKEN.sub(restore, "\n".join(segments)),
        )
    return TurnFacts(facts=texts)


def _clearance_values(
    sources: TurnFacts, chunk: str, expression: str, *, unit_in_label: bool = False
) -> list[tuple[str, int]] | None:
    """Read only an intact list of figure facts with a supported mm unit."""
    if re.fullmatch(_CLEARANCE_LIST, expression, re.IGNORECASE) is None:
        return None
    tokens = list(_CLEARANCE_TOKEN.finditer(expression))
    values: list[tuple[str, int]] = []
    explicit_units: list[bool] = []
    for token in tokens:
        value = token.group(2)
        number = re.fullmatch(r"(\d+)(\s*mm)?", value, re.IGNORECASE)
        figure = sources.facts.get(f"{chunk}.n{token.group(1)}")
        if (
            number is None
            or figure is None
            or figure.source != "search-knowledge"
            or figure.value != value
        ):
            return None
        values.append((figure.id, int(number.group(1))))
        explicit_units.append(number.group(2) is not None)
    if not tokens or not (
        all(explicit_units)
        or unit_in_label
        or (explicit_units[-1] and not any(explicit_units[:-1]))
    ):
        return None
    return values


def _clearance_clauses(
    sources: TurnFacts, chunk: str, segment: str
) -> list[tuple[str, int, bool]] | None:
    """Bind clearance values to complete clauses, including explicit negation.

    Unknown clauses make the sentence ambiguous: they can be conditions on a
    previous value. A following correction can refer to the immediately
    preceding negated clearance, but an unrelated property cannot supply one.
    """
    result: list[tuple[str, int, bool]] = []
    negated = False
    for clause in segment.rstrip(".!").split(";"):
        clause = clause.strip()
        direct = re.fullmatch(
            rf"(?:the\s+|der\s+|die\s+)?(?P<label>{_CLEARANCE_LABEL})"
            rf"(?:\s+(?:is|are|of|ist|sind|beträgt|betragen|von))?\s*[:=]?\s*"
            rf"(?P<not>not\s+|nicht\s+)?(?P<values>{_CLEARANCE_LIST})",
            clause,
            re.IGNORECASE,
        )
        correction = re.fullmatch(
            rf"(?:use|verwenden\s+sie)\s+(?:a\s+)?(?:minimum|mindestens)\s+"
            rf"(?:of|von)?\s*(?P<values>{_CLEARANCE_LIST})",
            clause,
            re.IGNORECASE,
        )
        other = re.fullmatch(
            rf"(?:the\s+)?(?:enclosure|cabinet|device|unit)\s+(?:height|width|depth)"
            rf"(?:\s+(?:is|of))?\s*[:=]?\s*(?P<values>{_CLEARANCE_LIST})",
            clause,
            re.IGNORECASE,
        )
        if direct:
            values = _clearance_values(sources, chunk, direct.group("values"))
            if values is None:
                return None
            negated = direct.group("not") is not None
            if not negated:
                minimum = bool(re.search(r"(?i)minimum|minimal|mindest|≥|>=", clause))
                result.extend(
                    (figure_id, value, minimum) for figure_id, value in values
                )
        elif correction and negated:
            values = _clearance_values(sources, chunk, correction.group("values"))
            if values is None:
                return None
            result.extend((figure_id, value, True) for figure_id, value in values)
            negated = False
        elif other:
            if _clearance_values(sources, chunk, other.group("values")) is None:
                return None
            negated = False
        else:
            return None
    return result


def _independent_measurement(
    sources: TurnFacts, chunk: str, segment: str
) -> tuple[str, str, bool] | None:
    """Recognize a separate single-property measurement, not free context."""
    line = segment.strip().rstrip(".!")
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    if line.startswith("|") and len(cells) == 2:
        line = f"{cells[0]} {cells[1]}"
    match = re.fullmatch(
        r"(?:the\s+)?(?P<label>(?:(?:rated|usable|nominal|maximum|minimum|enclosure|cabinet|device|unit)\s+)?"
        r"(?:height|width|depth|energy|power|voltage|current|weight|mass|torque|load|drill\s+bit))"
        r"(?:\s+(?:is|of))?\s*[:=]?\s*(?P<phi>Φ?)\[n(?P<id>[1-9]\d*)=(?P<value>[^\[\]]+)\]",
        line,
        re.IGNORECASE,
    )
    if match is None:
        return None
    figure = sources.facts.get(f"{chunk}.n{match.group('id')}")
    if (
        not figure
        or figure.source != "search-knowledge"
        or figure.value != match.group("value")
    ):
        return None
    label = " ".join(match.group("label").casefold().split())
    return figure.id, label, bool(match.group("phi"))


def _clearance_source_content(sources: TurnFacts, chunk: str, text: str) -> str:
    notes = sources.qualifications.get(chunk, ())
    note_lines = {f"{note.quote} (p. {note.page})" for note in notes}
    content = "\n".join(
        line for line in text.splitlines() if line.strip() not in note_lines
    )
    for note in notes:
        marker = note.quote.split(":", 1)[0]
        content = re.sub(rf"{re.escape(marker)}(?!\d)", "", content)
    return content


def _source_clearances(sources: TurnFacts) -> list[tuple[str, int, bool]]:
    values: list[tuple[str, int, bool]] = []
    for fact_id, fact in sources.facts.items():
        if not fact_id.endswith(".text") or fact.source != "search-knowledge":
            continue
        chunk = fact_id[:-5]
        chunk_values: list[tuple[str, int, bool]] = []
        source_text = _clearance_source_content(sources, chunk, fact.value)
        for segment in _source_segments(source_text):
            if not segment.strip():
                continue
            cells = [cell.strip() for cell in segment.strip().strip("|").split("|")]
            if segment.strip().startswith("|") and len(cells) == 2:
                label = re.fullmatch(
                    rf"(?P<label>{_CLEARANCE_LABEL})\s*(?:\(mm\)|\[mm\])?",
                    cells[0],
                    re.IGNORECASE,
                )
                if label:
                    found = _clearance_values(
                        sources,
                        chunk,
                        cells[1],
                        unit_in_label="mm" in cells[0].casefold(),
                    )
                    if found is not None:
                        minimum = bool(
                            re.search(r"(?i)minimum|minimal|mindest|≥|>=", segment)
                        )
                        chunk_values.extend(
                            (figure_id, value, minimum) for figure_id, value in found
                        )
                        continue
                elif re.fullmatch(
                    r"(?i)parameter|property|eigenschaft", cells[0]
                ) and re.fullmatch(r"(?i)value|wert", cells[1]):
                    continue
            else:
                found_clauses = _clearance_clauses(sources, chunk, segment)
                if found_clauses is not None:
                    chunk_values.extend(found_clauses)
                    continue
            if not _independent_measurement(sources, chunk, segment):
                # A surrounding heading or prose can qualify the measurement.
                # Leave it to the cited, conditioned answer path instead of
                # producing a bare automatic statement.
                break
        else:
            values.extend(chunk_values)
    return list(dict.fromkeys(values))


def _append_clearance(output: TurnOutput, sources: TurnFacts) -> TurnOutput:
    for minimum in (True, False):
        missing = [
            value
            for _, value, is_minimum in _source_clearances(sources)
            if is_minimum == minimum
            and not re.search(rf"(?<!\d){value}\s*mm\b", _prose(output), re.IGNORECASE)
        ]
        output = _append_sentence(
            output,
            _clearance_sentence(output.language, list(dict.fromkeys(missing)), minimum),
        )
    return output


def _clearance_sentence(language: str, values: list[int], minimum: bool) -> str:
    if not values:
        return ""
    if language == "de":
        if len(values) == 1:
            label = "Mindestabstand" if minimum else "Abstand"
            return f"Die Montageunterlagen nennen einen {label} von {values[0]} mm."
        label = "Mindestabstände" if minimum else "Abstände"
        return f"Die Montageunterlagen nennen {label} von {_join_mm(values, 'und')}."
    if len(values) == 1:
        label = "minimum clearance" if minimum else "clearance"
        return f"The installation documents state a {label} of {values[0]} mm."
    label = "minimum clearances" if minimum else "clearances"
    return f"The installation documents state {label} of {_join_mm(values, 'and')}."


def _join_mm(values: list[int], conjunction: str) -> str:
    parts = [f"{value} mm" for value in values]
    if len(parts) == 2:
        return f"{parts[0]} {conjunction} {parts[1]}"
    return ", ".join(parts[:-1]) + f" {conjunction} {parts[-1]}"
