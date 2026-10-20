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

from linker_genie.facts import TurnFacts, stock_rows
from linker_genie.failure import FailureClass
from linker_genie.hydrate import hydrate
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


def fallback(
    facts: TurnFacts,
    locale: str,
    route: Route | None = None,
    *,
    exhausted: bool = False,
    failure_class: FailureClass | None = None,
    raised: bool = False,
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
        refs = _document_refs(facts)
        document_blocks: list[Block] = [TextBlock(text=DOCUMENTS[language], refs=refs)]
        document_blocks.extend(DocumentBlock(ref=ref) for ref in refs)
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
    qualified = facts.qualified_ids
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

    Qualified ids first. A products search that qualified nothing does not
    borrow `facts.product_ids` (#366): those are a series hit, a page, or a
    get-product, not the model the customer asked for.
    """
    qualified = sorted(facts.qualified_ids)
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


def finish(output: TurnOutput, facts: TurnFacts, route: Route | None) -> TurnOutput:
    """Add the next step the route owes when the model left it out (#394).

    A guest login stays the one login sentence. A degraded handoff is the
    failure sentence and is returned unchanged: the signed sentence does not
    replace it, and the reply promise is not appended to it. Cards and
    document links already on that handoff stay. A turn with no route is
    unchanged, so an outage handoff does not grow a reply promise. A company
    turn is the mailbox sentence plus the one-working-day reply. A shaped turn
    ships its signed sentence once: the model's prose is replaced, not kept
    beside it. An inquiry turn gains view_inquiry. A plain model answer gains
    one application ask, whether or not its prose already asks: the ask is
    chips and carries no question sentence, so the customer still reads one
    question. A clarification keeps its question and ships no clickable block:
    it asks which model the customer means, and the application chips cannot
    answer that (goal 9's one block has no field for a model choice). The
    contact card stays contact.decide's, after this returns.
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
    if route.shape == "promise":
        return _ensure_view(_replace_prose(output, PROMISE[language]))
    if route.shape == "partner":
        return _ensure_ask(_replace_prose(output, PARTNER[language]), language)
    if route.shape == "talk":
        return _ensure_ask(_replace_prose(output, TALK[language]), language)
    if route.name == "inquiry" and not _has_next_step(output):
        return _ensure_view(output)
    if not _has_next_step(output) and _plain_next_step(route):
        if route.name == "clarify":
            return output
        return _ensure_ask(output, language)
    return output


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
