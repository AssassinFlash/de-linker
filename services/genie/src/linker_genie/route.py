"""Code decides which tools a turn runs (docs/specs/13-genie.md, goal 2).

`plan()` reads the product words the lexicon found and Jev's answers, and returns a
`Route`: the ability calls the service makes before the model runs, and what the
answer must then show. deepseek-flash only writes the answer from those results.
When Jev is unsure (confidence below `CONFIDENT`) or did not answer, the route makes
no call of its own and the model decides — except that a brand, series or model word
always runs the product search: a product word is never a greeting. A short body
that more than one product holds, or a shared trailing suffix with no other product
word, is a fixed question: the service writes it and the model does not run.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from linker_genie import page as page_tool
from linker_genie.jev import Reading
from linker_genie.lexicon import MAX_WORDS, MIN_CODE, Match, _words, normalize
from linker_genie.nameplate import Identified
from linker_genie.prefill import stated_size_hint
from linker_genie.schema import PageContext
from linker_genie.tools import MAX_TOOL_CALLS, READ_PAGE

# Jev's intent confidence from which code acts on it: the starting threshold measured
# 2026-10-17 — 57 of 60 messages reached it and 56 of those 57 were right
# (docs/research/2026-10-17-jev-intent/RESULTS.md); tuned later on live turns.
CONFIDENT = 0.8
# A yes/no answer of Jev counts from the same threshold.
LIKELY = 0.8
# Products a code-made search shows: search-products' own ceiling is 12
# (SearchProducts::MAX_LIMIT), and twelve cards for a family question was the
# failure of trial question 8 (docs/research/2026-10-17-knocket/TRIAL.md §2). Six
# fill two rows of the card grid; the answer asks one question to narrow the rest.
SEARCH_LIMIT = 6
# Products a document search is narrowed to: search-knowledge takes product_ids, and
# a question names one or two models in practice; four keeps a family question
# (OCEAN 2) inside the documents of the cards it shows.
KNOWLEDGE_PRODUCTS = 4

# Pairings of a solution draft checked at most: two of the four calls, so a draft of
# an inverter and two battery types is checked whole beside the page read.
DRAFT_PAIRS = 2
# A draft's inverters and its batteries, by device class (SelectionFacts.php).
_INVERTERS = ("inverters", "all-in-one-systems")
_BATTERIES = ("home-storage", "battery-systems")
# Calls a documents route leaves to the model: one, for a follow-up search when the
# first chunks miss the product (trial question 10, 2026-10-17: the model searched
# again with the product IDs get-product returned).
DOCUMENTS_SPARE = 1
# A delivery, shipping or freight question is the team's (owner 2026-10-05), also when
# it is asked about a page and Jev reads it otherwise: these words, EN and DE.
_LOGISTICS = re.compile(
    r"\b(?:deliver(?:y|ies)|shipping|shipment|freight|lieferung(?:en)?|lieferzeit(?:en)?|"
    r"lieferkosten|versand(?:kosten)?|fracht(?:kosten)?)\b",
    re.IGNORECASE,
)

PAGE_HINT = (
    " The customer asks about the page they are on; its text is here: the page's "
    "opening and the passages nearest the question, with its outline. "
    + page_tool.RULE
    + " A product, document or pairing question about the page's product is still "
    "answered from the product data and the documents. When the page's text is not "
    "available this turn, say that the page could not be read just now; never "
    "guess what it says. Speak to the customer about the page; never mention a "
    "service, a reading, a tool or an id in the text."
)
DRAFT_HINT = (
    " The customer asks about their solution draft: its products are here, and "
    "the pairings of its inverters and batteries have been checked. Name the "
    "products, say which pairs are released, with conditions, and which are not "
    "or unknown; cite the product IDs in refs. An empty draft has no products: "
    "say so and offer to find products. Speak to the customer about their draft; "
    "never mention a service, a reading, a tool or an id in the text."
)
ACCOUNT_HINT = (
    " The customer asks about their account page: it shows their inquiries, which "
    "are here; answer from them. Never mention a service, a reading, a tool or an "
    "id in the text."
)
SERVICE_HINT = (
    "This is a company, delivery or service question: answer with the "
    "handoff block from the handoff-team result."
)
# Smallest, largest and cheapest questions aggregate the qualified catalogue
# in search-products (#368). Dossier §1.1 has only a directional note on
# parameter correction, and §1.11 has no precedent for near-value
# disambiguation, so the floor and the extreme are decided here and in the
# ability, then the model names that one product.
EXTREME_HINT = (
    "The customer asks for an extreme of the product range (smallest, largest "
    "or cheapest) under the floor the message states. search-products already "
    "aggregated the published products. When extreme.applied is true, "
    "qualified holds that one product: name the model code extreme.model "
    "gives, exactly as written, cite that product id in refs, show only that "
    "card, and state the figure extreme.field names as a placeholder. When "
    "extreme.applied is false and extreme.reason is price_hidden, this "
    "account does not see prices: do not rank by price and do not name a "
    "cheapest product; say that approved partner accounts see net prices. "
    "English and German use this same shape."
)

DOCUMENTS_HINT = (
    "This is a question about documents or technical values. Answer from the "
    "search-knowledge chunks (cite them) and the product facts; show the "
    "documents as document blocks. It is not a question for the team."
)

RouteName = Literal[
    "nameplate",
    "parts",
    "products",
    "documents",
    "pairing",
    "compare",
    "sizing",
    "inquiry",
    "person",
    "service",
    "model",
    # A fixed question: an unmatched short body, or a shared suffix alone.
    # The service writes `Route.answer`. No tool call, no model.
    "clarify",
]

# Words of a sizing question, read in code so the configurator opens prefilled.
_KWP = re.compile(r"(\d+(?:[.,]\d+)?)\s*kwp\b", re.IGNORECASE)
_ANNUAL = re.compile(
    r"(\d{1,3}(?:[.,]\d{3})+|\d{3,6})\s*kwh\s*(?:/\s*(?:a|yr|year|jahr)\b|per\s+year|a\s+year|"
    r"pro\s+jahr|im\s+jahr|jährlich|yearly|annual)",
    re.IGNORECASE,
)
_THREE_PHASE = re.compile(
    r"\b(?:3|three|drei)[\s-]*(?:phase|phasen|phasig)", re.IGNORECASE
)
_ONE_PHASE = re.compile(
    r"\b(?:1|single|one|ein)[\s-]*(?:phase|phasen|phasig)", re.IGNORECASE
)
_BACKUP = re.compile(r"backup|back-up|notstrom|ersatzstrom", re.IGNORECASE)
# Extreme words, EN and DE. Comparatives (kleiner, größer, günstiger) are not
# extremes. ß and ss both occur.
_SMALLEST = re.compile(
    r"\b(?:smallest|lowest(?:[-\s]+power)?|"
    r"kleinst(?:e(?:r|n|m|s)?|er|es|em)?|"
    r"geringst(?:e(?:r|n|m|s)?|er|es|em)?|"
    r"niedrigst(?:e(?:r|n|m|s)?|er|es|em)?)\b",
    re.IGNORECASE,
)
_LARGEST = re.compile(
    r"\b(?:largest|biggest|"
    r"gr(?:ö|oe|o)(?:ß|ss)t(?:e(?:r|n|m|s)?|er|es|em)?|"
    r"h(?:ö|oe)chst(?:e(?:r|n|m|s)?|er|es|em)?|"
    r"st(?:ä|ae)rkst(?:e(?:r|n|m|s)?|er|es|em)?)\b",
    re.IGNORECASE,
)
_CHEAPEST = re.compile(
    r"\b(?:cheapest|lowest[-\s]+pric(?:e|ed)|"
    r"g(?:ü|ue)nstigst(?:e(?:r|n|m|s)?|er|es|em)?|"
    r"preiswertest(?:e(?:r|n|m|s)?|er|es|em)?|"
    r"billigst(?:e(?:r|n|m|s)?|er|es|em)?)\b",
    re.IGNORECASE,
)
_EXTREME_KINDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (_CHEAPEST, "cheapest"),
    (_LARGEST, "largest"),
    (_SMALLEST, "smallest"),
)
_INVERTER_WORD = re.compile(r"\b(?:inverters?|wechselrichter(?:n|s)?)\b", re.IGNORECASE)
_BATTERY_WORD = re.compile(
    r"\b(?:batter(?:y|ies)|batterie(?:n)?|speicher)\b", re.IGNORECASE
)
_NUMBER = r"(\d+(?:[.,]\d+)?)"
_FLOOR_MARK = (
    r"(?:at\s+least|minimum|min\.?|>=|≥|over|above|more\s+than|"
    r"mindestens|wenigstens|ab|über|ueber|mehr\s+als)"
)
_MARKED_KW = re.compile(rf"{_FLOOR_MARK}\s*{_NUMBER}\s*k\s*w(?!h)\b", re.IGNORECASE)
_MARKED_KWH = re.compile(rf"{_FLOOR_MARK}\s*{_NUMBER}\s*k\s*wh\b", re.IGNORECASE)
_ANY_KW = re.compile(rf"{_NUMBER}\s*k\s*w(?!h)\b", re.IGNORECASE)
_ANY_KWH = re.compile(rf"{_NUMBER}\s*k\s*wh\b", re.IGNORECASE)


@dataclass(frozen=True)
class Call:
    ability: str
    arguments: dict[str, Any]
    # The attachment reading whose text made these arguments (the nameplate
    # search): the turn log purges the call with its reading when the
    # conversation is deleted (log.TurnLog.forget, review round 1 of PR #309,
    # item 6).
    from_reading: str | None = None


def _call_log(call: Call) -> dict[str, Any]:
    """A call for the route log, naming the reading it came from when it did."""
    entry: dict[str, Any] = {"name": call.ability, "arguments": call.arguments}
    if call.from_reading:
        entry["from_reading"] = call.from_reading
    return entry


@dataclass(frozen=True)
class NamedModel:
    """One model code the customer wrote, and what the catalog says about it.

    `searched` is false when the turn's tool budget left the code out: the answer
    says it was not searched, and never that the product data lacks it (#364).
    `unknown` is a code the catalog does not list. `written_brand` and
    `catalog_brand` are set when the written brand and the catalog brand disagree
    (#363, #367).
    """

    code: str
    product_ids: tuple[int, ...] = ()
    searched: bool = True
    written_brand: str = ""
    catalog_brand: str = ""
    unknown: bool = False


@dataclass(frozen=True)
class Route:
    """What code runs before the model, and what the answer must contain."""

    name: RouteName
    calls: tuple[Call, ...] = ()
    # The answer must show cards of the products the code-made search returned.
    show_products: bool = False
    # The answer must carry this action (the configurator for sizing).
    action: str | None = None
    # Cards are not this answer's shape (sizing goes to the configurator).
    no_cards: bool = False
    # The answer may not be the team handoff (a product or document question).
    no_handoff: bool = False
    # A sentence for the model about what the code did and what is expected.
    hint: str = ""
    reasons: tuple[str, ...] = field(default=())
    # Calls the turn's budget left out (with_page), kept for the turn log.
    dropped: tuple[Call, ...] = ()
    # Models the customer named, in the order of the message (#363, #364, #367).
    named_models: tuple[NamedModel, ...] = ()
    # The service's own sentence for a `clarify` route. Empty on every other route.
    answer: str = ""

    def as_log(self) -> dict[str, Any]:
        log: dict[str, Any] = {
            "route": self.name,
            "calls": [_call_log(c) for c in self.calls],
            "show_products": self.show_products,
            "action": self.action,
            "no_cards": self.no_cards,
            "no_handoff": self.no_handoff,
            "reasons": list(self.reasons),
        }
        if self.dropped:
            log["dropped_calls"] = [_call_log(c) for c in self.dropped]
        if self.named_models:
            log["named_models"] = [
                {
                    "code": note.code,
                    "searched": note.searched,
                    "unknown": note.unknown,
                    "written_brand": note.written_brand,
                    "catalog_brand": note.catalog_brand,
                    "product_ids": list(note.product_ids),
                }
                for note in self.named_models
            ]
        return log


@dataclass(frozen=True)
class Subject:
    """The products a message is about: matched models, else the page's product."""

    ids: tuple[int, ...]
    device_class: dict[int, str]
    # The model of each product as the titles write it (search-products' text filter).
    labels: dict[int, str] = field(default_factory=dict)
    # The phase of each product, and the products of each series (lexicon.py).
    phase: dict[int, int] = field(default_factory=dict)
    series_members: dict[str, set[int]] = field(default_factory=dict)
    # Product → brand slugs, brand slug → the published name, product → title,
    # and the catalog's model codes. Empty on a subject built without a catalog,
    # which keeps a brand filter (the unit fixtures). route.py reads them to tell
    # a brand/model conflict from a model the catalog does not list.
    brand_of: dict[int, set[str]] = field(default_factory=dict)
    brand_names: dict[str, str] = field(default_factory=dict)
    names: dict[int, str] = field(default_factory=dict)
    catalog_models: tuple[str, ...] = ()
    # Short bodies that named more than one product, and trailing suffixes shared
    # by two or more products (lexicon.py). Empty when the subject has no catalog.
    unresolved_bodies: frozenset[str] = frozenset()
    shared_suffixes: frozenset[str] = frozenset()


def plan(
    message: str,
    matches: list[Match],
    reading: Reading | None,
    subject: Subject,
    lang: str,
    bare: bool = False,
    earlier: Sequence[str] = (),
) -> Route:
    """The route of one turn (module docstring).

    `bare` is true when the message is nothing but product words: then a category
    word ("EMS", "Zubehör") searches its products as a brand or model word does.
    `earlier` is the conversation's previous user messages: a sizing prefill may
    carry figures the customer already stated, and this message wins on a field
    both name (#365, dossier §1.12).
    """
    intent = reading.intent if reading and reading.confidence >= CONFIDENT else None
    named = [m for m in matches if m.kind in ("brand", "series", "model")]
    reasons: list[str] = []
    if reading is None:
        reasons.append("jev unavailable")
    elif intent is None:
        reasons.append(f"jev unsure: {reading.intent} {reading.confidence:.2f}")
    if named or bare:
        shown = named or matches
        reasons.append("product words: " + ", ".join(m.words for m in shown))

    if intent == "talk_to_person":
        # Frustration on another intent is answered as routed, with the contact
        # offer beside it (contact.decide).
        return person(reasons)
    if intent == "company_logistics_service":
        return service(message, reasons)
    if intent == "inquiry_status":
        return Route(
            "inquiry",
            (Call("linker/inquiry-status", {}),),
            no_handoff=True,
            hint="The inquiry-status result is fetched; answer from it.",
            reasons=tuple(reasons),
        )
    # A brand or series extreme is one aggregate (#368), not a brand/model
    # conflict. Two model codes in the message, or one code whose products
    # belong to another brand, stay on the per-model searches (#363, #364):
    # one class aggregate would hide those codes, and the two grounding rules
    # would require different cards.
    extreme = _catalogue_extreme(message, matches, subject, lang)
    if extreme is not None:
        reasons.append(f"extreme: {extreme['extreme']}")
        return Route(
            "products",
            (Call("linker/search-products", extreme),),
            show_products=True,
            no_handoff=True,
            hint=EXTREME_HINT,
            reasons=tuple(reasons),
        )
    if intent == "sizing":
        return Route(
            "sizing",
            (
                # This dict is the only size-hint derivation. The route log
                # stores it, and understand sends the same object (#365).
                Call(
                    "linker/size-hint",
                    stated_size_hint((*earlier, message)),
                ),
            ),
            action="open_configurator",
            no_cards=True,
            no_handoff=True,
            hint=(
                "This is a sizing question. The Solution Configurator sizes the "
                "system from the customer's PV and consumption: say so in one or "
                "two sentences and add the open_configurator action (the service "
                "fills its URL from pv_kwp, annual_load_kwh, phase, backup and "
                "plz the customer stated in the conversation, and leaves out "
                "every field they did not state). No product cards. Call "
                "size-hint with an empty object."
            ),
            reasons=tuple(reasons),
        )
    # An unmatched short body, or a suffix with no product word, is a question.
    # It does not search the family the other words name, and it does not hand
    # the model a generic hint. A named model still searches.
    clarify = _clarify(message, matches, subject, lang, reasons)
    if clarify is not None:
        return clarify
    family = _family_hint(matches)
    calls, notes = _search_plan(matches, lang, subject, message)
    hint_extra = _model_hint(notes)
    reasons.extend(_note_reasons(notes))
    if intent == "documents_specs":
        doc_calls = [
            Call(
                "linker/search-knowledge",
                _knowledge_input(message, matches, subject, lang),
            )
        ]
        if subject.ids:
            doc_calls.extend(
                Call("linker/get-product", {"product_id": pid, "lang": lang})
                for pid in subject.ids[:2]
            )
        elif calls:
            doc_calls.extend(calls)
        return Route(
            "documents",
            tuple(doc_calls),
            no_handoff=True,
            hint=DOCUMENTS_HINT + family + hint_extra,
            reasons=tuple(reasons),
            named_models=notes,
        )
    if intent == "pairing_compatibility":
        pairing = _pairing(subject, lang)
        if pairing is not None:
            return Route(
                "pairing",
                (pairing,),
                no_handoff=True,
                hint="The pairing result is fetched; answer from it.",
                reasons=tuple(reasons),
            )
    if intent == "compare" and len(subject.ids) >= 2:
        return Route(
            "compare",
            (
                Call(
                    "linker/compare-products",
                    {"product_ids": list(subject.ids[:4]), "lang": lang},
                ),
            ),
            no_handoff=True,
            hint="The comparison is fetched; answer with a compare block.",
            reasons=tuple(reasons),
        )
    unknown = any(note.unknown for note in notes)
    if (calls or notes) and (bare or intent == "find_products" or unknown):
        return Route(
            "products",
            calls,
            show_products=True,
            no_handoff=True,
            hint=(
                "The customer named products; the search result is fetched. Show "
                "its products as cards, cited in the text refs. A product word is "
                "never a name or a greeting." + family + hint_extra
            ),
            reasons=tuple(reasons),
            named_models=notes,
        )
    if calls and named and reading is not None and reading.intent == "documents_specs":
        # Product words in a question Jev reads as a document question, however
        # sure it is: code runs both searches, the model does not decide whether
        # to look (trial question 9, "How do I set the export limit on an SAJ H2
        # inverter?", Jev documents_specs 0.67 — the model did not look and
        # answered that the documents had nothing; review of PR #279).
        return Route(
            "documents",
            (
                *calls,
                Call(
                    "linker/search-knowledge",
                    _knowledge_input(message, matches, subject, lang),
                ),
            ),
            no_handoff=True,
            hint=DOCUMENTS_HINT + family + hint_extra,
            reasons=tuple(reasons),
            named_models=notes,
        )
    if (calls or notes) and named:
        # Product words inside a longer question that Jev could not place: code
        # still searches the named products (they are never small talk), and the
        # model decides the shape — cards are not forced on a how-to question
        # (trial question 9, Jev documents_specs 0.67, 2026-10-17). A brand/model
        # conflict, or two or more models, still shows cards.
        leaning = (
            f" Jev leans to {reading.intent} ({reading.confidence:.2f}): call "
            "search-knowledge if this is a document or technical question."
            if reading is not None
            else ""
        )
        return Route(
            "products",
            calls,
            show_products=_must_show(notes),
            no_handoff=True,
            hint=(
                "The customer named products; the search result is fetched. A "
                "product word is never a name or a greeting."
                + leaning
                + family
                + hint_extra
            ),
            reasons=tuple(reasons),
            named_models=notes,
        )
    if intent == "find_products":
        return Route(
            "model",
            no_handoff=True,
            hint=(
                "The customer is looking for products: call search-products with "
                "the filters the message gives."
            ),
            reasons=tuple(reasons),
        )
    if intent in ("pairing_compatibility", "compare"):
        return Route(
            "model",
            no_handoff=True,
            hint=f"Jev reads this as {intent}; identify the products with the tools.",
            reasons=tuple(reasons),
        )
    return Route("model", reasons=tuple(reasons))


def _searches(
    search: dict[str, Any], matches: list[Match], subject: Subject
) -> tuple[Call, ...]:
    """One search, or one per phase for a family named without a model that has both.

    Six cards of one search showed only the single-phase half of EcoFlow OCEAN 2
    (trial question 8, 2026-10-17): the family has single- and three-phase models,
    and the cheapest six were all single-phase. The phases come from pa_phase.
    """
    if any(m.kind == "model" for m in matches) or "phase" in search:
        return (Call("linker/search-products", search),)
    members: set[int] = set()
    for match in matches:
        if match.kind == "series":
            members |= subject.series_members.get(match.value, set())
    phases = sorted({subject.phase[pid] for pid in members if pid in subject.phase})
    if len(phases) < 2:
        return (Call("linker/search-products", search),)
    per_phase = max(1, SEARCH_LIMIT // len(phases))
    return tuple(
        Call("linker/search-products", {**search, "phase": phase, "limit": per_phase})
        for phase in phases
    )


def _family_hint(matches: list[Match]) -> str:
    """For a family named without a model: the search shows only part of it."""
    if any(m.kind == "model" for m in matches):
        return ""
    if not any(m.kind == "series" for m in matches):
        return ""
    return (
        " The customer named a product family, and the search shows only part "
        "of it: say what differs across the family (for example single-phase "
        "and three-phase models), answer the question for the products shown "
        "by naming each shown model with its figure as a placeholder (for "
        "example its ac_power_kw), never a lowest or highest value of the "
        "whole family, and ask which model or phase is wanted."
    )


# What the model is told about a nameplate turn. No internal wording: "the service
# read it" came back in a German answer as "der Dienst" (review round 1 of PR #309,
# item 10), so the hints speak of the photo and the customer only, and say not to
# describe how it was read.
_PLATE_VOICE = (
    " Write to the customer about their photo; never mention a service, a reading, "
    "a tool or an id in the text."
)
NAMEPLATE_HINTS = {
    "exact": (
        "The customer sent a photo of a nameplate ({id}); the model printed on it is "
        "one of our products, fetched by search. Show that product as a card, say in "
        "one sentence what the nameplate shows (put {id} in refs; brand and model are "
        "names, a rating only as {{fact:{id}.nK}}), and ask the customer to confirm "
        "that this is their device. The confirmation buttons are shown with the "
        "answer: add no ask block." + _PLATE_VOICE
    ),
    "partial": (
        "The customer sent a photo of a nameplate ({id}); the model printed on it "
        "matches none of our models exactly, and the products of the same family are "
        "fetched. Say what the nameplate shows (put {id} in refs), show the family's "
        "products as cards and ask which one it is, or that the customer types the "
        "model. Never claim that one of them is the device." + _PLATE_VOICE
    ),
    "none": (
        "The customer sent a photo of a nameplate ({id}); the device is not in our "
        "product range. Say what the nameplate shows (put {id} in refs) and that we "
        "do not carry this model; when the search found products of the same brand, "
        "you may offer them, never as the same device. Ask what the customer needs "
        "for it (a battery, a replacement)." + _PLATE_VOICE
    ),
    "unreadable": (
        "The customer sent a photo of a nameplate ({id}); its model cannot be made "
        "out, so it is not known whether we carry the device. Say so plainly, naming "
        "what can be made out, and ask for a sharp, straight photo of the whole label "
        "in good light, or for the model typed in. No cards." + _PLATE_VOICE
    ),
}


def nameplate(
    identified: Identified, lang: str, subject: Subject, reasons: list[str]
) -> Route:
    """A nameplate photo: the product it names, for the customer to confirm (#236).

    The grade is code's (nameplate.identify); the route fetches what the card and the
    answer show: the exact model, the family of a partial match, or the brand's
    products for a model we do not carry. An unreadable photo fetches nothing.
    """
    hint = NAMEPLATE_HINTS[identified.grade].format(id=identified.reading_id)
    reason = (*reasons, f"nameplate {identified.reading_id}: {identified.grade}")
    if identified.grade == "unreadable":
        return Route(
            "nameplate", no_cards=True, no_handoff=True, hint=hint, reasons=reason
        )
    matches = list(identified.matches)
    search = _search_input(matches, lang)
    if identified.grade == "none":
        # Only the brand (and its device class) is ours: the model may offer them.
        brands = [m for m in matches if m.kind in ("brand", "category")]
        search = (
            _search_input(brands, lang)
            if any(m.kind == "brand" for m in brands)
            else None
        )
    calls = _searches(search, matches, subject) if search is not None else ()
    # Every search word of a nameplate route is the reading's (the model or the
    # brand it printed), so the calls are marked as its: purged with it (#236).
    calls = tuple(replace(c, from_reading=identified.reading_id) for c in calls)
    return Route(
        "nameplate",
        calls,
        show_products=identified.grade in ("exact", "partial") and bool(calls),
        no_handoff=True,
        hint=hint,
        reasons=reason,
    )


def person(reasons: list[str]) -> Route:
    """The customer asks for a person: "Let Linker contact me" (#243).

    The route makes no call and the model does not run: the turn is the service's own
    sentence and the contact card (contact.answer, app.assistant_turn).
    """
    return Route("person", reasons=tuple(reasons))


# Words that may stand beside a suffix or a short body without naming a product.
# "the S2 one", "die S2", "das G20". A brand or a question word is not in here.
_DEICTIC = frozenset(
    {
        "the",
        "a",
        "an",
        "one",
        "this",
        "that",
        "please",
        "der",
        "die",
        "das",
        "den",
        "dem",
        "des",
        "ein",
        "eine",
        "einen",
        "einem",
        "einer",
        "bitte",
        "modell",
        "model",
        "variante",
        "version",
    }
)
# A hyphenated token as the customer wrote it ("BD-8"), so the question can
# repeat their word. The matcher's own cut drops the hyphen.
_HYPHENATED = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


def _clarify(
    message: str,
    matches: list[Match],
    subject: Subject,
    lang: str,
    reasons: list[str],
) -> Route | None:
    """A fixed question when a short body or a lone suffix cannot be matched.

    A model word wins: the customer named something the catalog lists. An
    unresolved body asks even when a brand or a series also matches, so the
    turn does not search that family. A suffix asks only when the message has
    no product word and the other words are pointers ("the S2 one").
    """
    if any(match.kind == "model" for match in matches):
        return None
    body = _customer_phrase(message, subject.unresolved_bodies)
    if body is not None:
        return _clarify_route(body, lang, "body", reasons)
    if matches:
        return None
    suffix = _suffix_only(message, subject.shared_suffixes)
    if suffix is None:
        return None
    return _clarify_route(suffix, lang, "suffix", reasons)


def _clarify_route(phrase: str, lang: str, kind: str, reasons: list[str]) -> Route:
    """The service's sentence. German is Sie and carries no English fragment."""
    if lang.startswith("de"):
        if kind == "suffix":
            text = (
                f"{phrase} ist eine Endung mehrerer Modelle. Welches Modell meinen Sie?"
            )
        else:
            text = (
                f"{phrase} passt zu mehr als einem Produkt. Welches Modell meinen Sie?"
            )
    elif kind == "suffix":
        text = f"{phrase} is a suffix on more than one model. Which model do you mean?"
    else:
        text = f"{phrase} matches more than one product. Which model do you mean?"
    reasons.append(f"clarify: {kind} {phrase}")
    return Route(
        "clarify",
        no_cards=True,
        no_handoff=True,
        answer=text,
        reasons=tuple(reasons),
    )


def _suffix_only(message: str, suffixes: frozenset[str]) -> str | None:
    """The one shared suffix, when every other word is a pointer."""
    words = _words(message)
    hits = [word for word in words if normalize(word) in suffixes]
    if len(hits) != 1:
        return None
    rest = [word for word in words if normalize(word) not in suffixes]
    if any(normalize(word) not in _DEICTIC for word in rest):
        return None
    return hits[0]


def _customer_phrase(message: str, keys: frozenset[str]) -> str | None:
    """The customer's own token for one of `keys`, hyphen kept when they wrote one."""
    if not keys:
        return None
    for token in _HYPHENATED.findall(message):
        written = str(token)
        if normalize(written) in keys:
            return written
    words = _words(message)
    limit = min(MAX_WORDS, len(words))
    for size in range(limit, 0, -1):
        for start in range(len(words) - size + 1):
            piece = words[start : start + size]
            if "".join(normalize(word) for word in piece) in keys:
                return " ".join(piece)
    return None


def _extreme_kind(message: str) -> str | None:
    """The extreme word that occurs first, or None."""
    found: list[tuple[int, str]] = []
    for pattern, kind in _EXTREME_KINDS:
        match = pattern.search(message)
        if match:
            found.append((match.start(), kind))
    if not found:
        return None
    found.sort()
    return found[0][1]


def _floor_number(
    marked: re.Pattern[str], plain: re.Pattern[str], message: str
) -> float | None:
    """The marked floor when the message states one, else the smaller plain figure."""
    hit = marked.search(message)
    if hit:
        return float(hit.group(1).replace(",", "."))
    numbers = [
        float(item.group(1).replace(",", ".")) for item in plain.finditer(message)
    ]
    if not numbers:
        return None
    return min(numbers)


def _catalogue_extreme(
    message: str, matches: list[Match], subject: Subject, lang: str
) -> dict[str, Any] | None:
    """The class aggregate, or None when the named models have to be searched.

    `extreme_input` builds the aggregate. This decides whether that aggregate
    is the turn: a brand or series narrows it and is not a conflict; two codes
    written in the message are searched one by one; one code that conflicts
    with the written brand is that conflict, not the class extreme.
    """
    written = _written_models(matches, message)
    if len(written) >= 2 or _conflicts_with_written_brand(written, matches, subject):
        return None
    return extreme_input(message, matches, lang)


def extreme_input(
    message: str, matches: list[Match], lang: str
) -> dict[str, Any] | None:
    """search-products arguments for a smallest, largest or cheapest question.

    A kWp or annual-consumption figure stays a sizing question. The floor is
    AC power for an inverter (or a kW figure) and energy for a battery (or a
    kWh figure). A named model is not a filter: the extreme is taken over the
    class, narrowed by a single brand or series when the message names one.
    `plan` does not use this when `_catalogue_extreme` returns None.
    """
    if _KWP.search(message) or _ANNUAL.search(message):
        return None
    kind = _extreme_kind(message)
    if kind is None:
        return None
    inverter = _INVERTER_WORD.search(message) is not None
    battery = _BATTERY_WORD.search(message) is not None
    kw = _floor_number(_MARKED_KW, _ANY_KW, message)
    kwh = _floor_number(_MARKED_KWH, _ANY_KWH, message)
    if not inverter and not battery and kw is None and kwh is None:
        return None
    if inverter and not battery:
        kwh = None
    elif battery and not inverter:
        kw = None
    elif kw is not None and kwh is not None:
        # Both figures and no single class word: the question is an AC floor.
        kwh = None
    found: dict[str, Any] = {
        "lang": lang,
        "extreme": kind,
        "limit": SEARCH_LIMIT if kind == "cheapest" else 1,
    }
    if kw is not None:
        found["ac_power_min"] = kw
    if kwh is not None:
        found["kwh_min"] = kwh
    if (battery and not inverter) or (kwh is not None and kw is None):
        found["device_classes"] = ["home-storage", "battery-systems"]
    elif inverter or kw is not None:
        found["device_class"] = "inverters"
    brands = [item for item in matches if item.kind == "brand"]
    if len({item.value for item in brands}) == 1:
        found["brand"] = brands[0].value
    series = [item for item in matches if item.kind == "series"]
    if len({item.value for item in series}) == 1 and not any(
        item.kind == "model" for item in matches
    ):
        found["series"] = series[0].value
    return found


def _search_input(matches: list[Match], lang: str) -> dict[str, Any] | None:
    """search-products filters for the product words, most specific first."""
    models = [m for m in matches if m.kind == "model"]
    series = [m for m in matches if m.kind == "series"]
    brands = [m for m in matches if m.kind == "brand"]
    categories = [m for m in matches if m.kind == "category"]
    found: dict[str, Any] = {}
    if models:
        found["text"] = models[0].value
    elif series:
        slugs = {m.value for m in series}
        if len(slugs) == 1:
            found["series"] = series[0].value
        else:
            # One alias names several series ("ESA", "OCEAN 2"): the titles carry
            # the alias as written, so the text filter finds the whole family.
            found["text"] = series[0].words
    if brands and len({m.value for m in brands}) == 1:
        found["brand"] = brands[0].value
    if categories and len({m.value for m in categories}) == 1:
        found["device_class"] = categories[0].value
    if not found:
        return None
    found["lang"] = lang
    found["limit"] = SEARCH_LIMIT
    return found


# A code in the raw message: a letter, a digit, and at least two "-" or "/" joins.
# One join is a phase or a rating ("3-phase", "10-20"); the unknown-model case in
# #363 is GW50K-ETA-G20. MIN_CODE (lexicon.py) is the shortest real code, four
# characters ("L260", snapshot 2026-10-15).
_ASKED_CODE = re.compile(
    r"(?<![\w.])(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]+(?:[./][A-Za-z0-9]+)*"
    r"(?:[-/][A-Za-z0-9]+(?:[./][A-Za-z0-9]+)*){2,}(?![\w])"
)


def _search_plan(
    matches: list[Match], lang: str, subject: Subject, message: str = ""
) -> tuple[tuple[Call, ...], tuple[NamedModel, ...]]:
    """The product searches for this message, and a note for every model code.

    A sentence that names several models searches each one (search-products takes
    one `text`). A model the catalog lists under another brand is searched without
    the written brand: ANDing them returns no product (campaign #330, F1/F4). The
    wording of that clarification is fixed in template.py; dossier 2026-10-19 §1.1,
    §1.11 and §2 item 10 mark the resolution as having no competitor precedent.
    Nameplate keeps `_search_input` (nameplate.py).
    """
    models = [match for match in matches if match.kind == "model"]
    if models:
        return _model_calls(models, matches, lang, subject, message)
    found = _search_input(matches, lang)
    if found is not None:
        return _searches(found, matches, subject), ()
    return _unknown_calls(_unknown_codes(message, subject), lang, subject)


def _model_calls(
    models: list[Match],
    matches: list[Match],
    lang: str,
    subject: Subject,
    message: str,
) -> tuple[tuple[Call, ...], tuple[NamedModel, ...]]:
    brands = [match for match in matches if match.kind == "brand"]
    brand = brands[0] if len({match.value for match in brands}) == 1 else None
    categories = [match for match in matches if match.kind == "category"]
    category = (
        categories[0].value if len({match.value for match in categories}) == 1 else None
    )
    calls: list[Call] = []
    notes: list[NamedModel] = []
    for model in _ordered_models(models, message):
        arguments: dict[str, Any] = {
            "text": model.value,
            "lang": lang,
            "limit": SEARCH_LIMIT,
        }
        written = ""
        catalog = ""
        if brand is not None and _conflicts(model, brand.value, subject):
            # The catalog brand wins the filter. The answer names both (template.py).
            written = brand.label
            catalog = _catalog_label(model.product_ids, subject)
        elif brand is not None:
            arguments["brand"] = brand.value
        if category is not None and _category_fits(
            model.product_ids, category, subject
        ):
            arguments["device_class"] = category
        # The turn's tool budget (tools.MAX_TOOL_CALLS, spec 13: at most four
        # ability calls). A model past it is named as not searched.
        searched = len(calls) < MAX_TOOL_CALLS
        if searched:
            calls.append(Call("linker/search-products", arguments))
        notes.append(
            NamedModel(
                code=model.value,
                product_ids=tuple(sorted(model.product_ids)),
                searched=searched,
                written_brand=written,
                catalog_brand=catalog,
            )
        )
    return tuple(calls), tuple(notes)


def _ordered_models(models: list[Match], message: str) -> list[Match]:
    """One match per model code, product ids joined, in message order."""
    grouped: dict[str, Match] = {}
    order: list[str] = []
    for model in models:
        previous = grouped.get(model.value)
        if previous is None:
            grouped[model.value] = model
            order.append(model.value)
        else:
            grouped[model.value] = Match(
                previous.kind,
                previous.label,
                previous.value,
                previous.product_ids | model.product_ids,
                previous.words,
            )
    folded = message.casefold()

    def position(value: str) -> tuple[int, int]:
        model = grouped[value]
        at = folded.find(model.value.casefold())
        if at < 0:
            at = folded.find(model.words.casefold())
        if at < 0:
            at = len(message)
        return (at, order.index(value))

    return [grouped[value] for value in sorted(order, key=position)]


def _written_models(matches: list[Match], message: str) -> list[Match]:
    """Model codes that stand in the message, one per code, in message order.

    A match attached without its code in the text is not written. The catalogue
    extreme ignores that match as a filter (#368) and does not treat it as one
    of several models (#364).
    """
    models = [match for match in matches if match.kind == "model"]
    if not models:
        return []
    folded = message.casefold()
    return [
        model
        for model in _ordered_models(models, message)
        if model.value.casefold() in folded or model.words.casefold() in folded
    ]


def _conflicts_with_written_brand(
    written: list[Match], matches: list[Match], subject: Subject
) -> bool:
    """Whether the one written model belongs to a brand other than the one named."""
    if len(written) != 1:
        return False
    brands = [match for match in matches if match.kind == "brand"]
    if len({match.value for match in brands}) != 1:
        return False
    return _conflicts(written[0], brands[0].value, subject)


def _conflicts(model: Match, brand_slug: str, subject: Subject) -> bool:
    """Whether every known product of `model` belongs to some other brand.

    An empty brand map keeps the brand filter: the unit fixtures build a subject
    without a catalog. A product whose brand cannot be read is not treated as a
    conflict.
    """
    if not model.product_ids:
        return False
    if not subject.brand_of and not subject.brand_names:
        return False
    found = [_brands_of(pid, subject) for pid in model.product_ids]
    if any(not brands for brands in found):
        return False
    return all(brand_slug not in brands for brands in found)


def _brands_of(product_id: int, subject: Subject) -> set[str]:
    """Brand slugs recorded for the product, else a brand name standing in its title.

    The store snapshot of 2026-10-15 has GW5K-ETA-G20 (product 6512) with no
    pa_brand; its title begins with GoodWe, and other GoodWe products publish
    that brand name. The lexicon's own brand map is left unchanged.
    """
    recorded = subject.brand_of.get(product_id)
    if recorded:
        return set(recorded)
    words = {
        normalize(word)
        for word in re.split(r"[^\w]+", subject.names.get(product_id, ""))
        if word
    }
    found: set[str] = set()
    for slug, label in subject.brand_names.items():
        if normalize(label) in words or normalize(slug) in words:
            found.add(slug)
    return found


def _catalog_label(product_ids: frozenset[int], subject: Subject) -> str:
    slugs: set[str] = set()
    for product_id in product_ids:
        slugs |= _brands_of(product_id, subject)
    if not slugs:
        return ""
    slug = next(iter(slugs)) if len(slugs) == 1 else sorted(slugs)[0]
    return subject.brand_names.get(slug) or slug


def _category_fits(
    product_ids: frozenset[int], device_class: str, subject: Subject
) -> bool:
    """Keep a category filter unless every known product is a different class.

    An empty device-class map, or a product with no class, keeps the filter.
    """
    if not product_ids or not subject.device_class:
        return True
    classes: list[str] = []
    for product_id in product_ids:
        device = subject.device_class.get(product_id)
        if not device:
            return True
        classes.append(device)
    return any(device == device_class for device in classes)


def _unknown_codes(message: str, subject: Subject) -> tuple[str, ...]:
    """Model-like codes in `message` that the catalog does not list.

    Without a catalog (the unit fixtures) nothing here is searched. A code the
    catalog already lists is a lexicon match and is handled with the other models.
    """
    if not subject.catalog_models:
        return ()
    known = {normalize(code) for code in subject.catalog_models}
    found: list[str] = []
    seen: set[str] = set()
    for match in _ASKED_CODE.finditer(message):
        code = match.group(0)
        key = normalize(code)
        if key in seen or key in known or len(key) < MIN_CODE:
            continue
        if not any(ch.isalpha() for ch in key) or not any(ch.isdigit() for ch in key):
            continue
        seen.add(key)
        found.append(code)
    return tuple(found)


def _unknown_calls(
    codes: tuple[str, ...], lang: str, subject: Subject
) -> tuple[tuple[Call, ...], tuple[NamedModel, ...]]:
    """Search each unknown code, then the closest family suffix that the budget allows.

    The suffix is a tail of the code that already occurs inside a catalog model
    (`ETA-G20` inside `GW10K-ETA-G20`). It is not an edit-distance guess: dossier
    2026-10-19 §1.1 leaves typos out of scope.
    """
    if not codes:
        return (), ()
    calls: list[Call] = []
    searched: list[str] = []
    for code in codes:
        if len(calls) >= MAX_TOOL_CALLS:
            break
        calls.append(
            Call(
                "linker/search-products",
                {"text": code, "lang": lang, "limit": SEARCH_LIMIT},
            )
        )
        searched.append(code)
    for code in searched:
        stem = _family_stem(code, subject.catalog_models)
        if stem is None or len(calls) >= MAX_TOOL_CALLS:
            continue
        calls.append(
            Call(
                "linker/search-products",
                {"text": stem, "lang": lang, "limit": SEARCH_LIMIT},
            )
        )
    notes = tuple(
        NamedModel(code=code, searched=code in searched, unknown=True) for code in codes
    )
    return tuple(calls), notes


def _family_stem(code: str, catalog: tuple[str, ...]) -> str | None:
    """The longest '-'/'/' tail of `code` that a catalog model already contains."""
    cuts = [index for index, ch in enumerate(code) if ch in "-/"]
    folded = [model.casefold() for model in catalog]
    for index in cuts:
        tail = code[index + 1 :]
        key = normalize(tail)
        if len(key) < MIN_CODE or tail.casefold() == code.casefold():
            continue
        if any(tail.casefold() in model for model in folded):
            return tail
    return None


def _must_show(notes: tuple[NamedModel, ...]) -> bool:
    """Cards for a conflict, an unknown code, or two or more named models."""
    if any(note.written_brand or note.unknown for note in notes):
        return True
    return len([note for note in notes if not note.unknown]) >= 2


def _note_reasons(notes: tuple[NamedModel, ...]) -> list[str]:
    reasons: list[str] = []
    if any(note.written_brand for note in notes):
        reasons.append("brand and model disagree")
    if any(note.unknown for note in notes):
        reasons.append("model code not in the product data")
    if len([note for note in notes if not note.unknown]) >= 2:
        reasons.append("several models")
    return reasons


def _model_hint(notes: tuple[NamedModel, ...]) -> str:
    """What the model is told about each named code. English, both locales."""
    parts: list[str] = []
    conflicts = [note for note in notes if note.written_brand and note.catalog_brand]
    if conflicts:
        named = "; ".join(
            f"{note.code} is {note.catalog_brand} in the product data; "
            f"the customer wrote {note.written_brand}"
            for note in conflicts
        )
        parts.append(
            named + ". Name the brand from the product data, show that product as a "
            "card, and do not say the model is missing. This is not a question for "
            "the team."
        )
    unknown = [note.code for note in notes if note.unknown and note.searched]
    if unknown:
        parts.append(
            "These model codes are not in the product data: "
            + ", ".join(unknown)
            + ". Say that plainly and offer the closest products the search returned. "
            "Do not hand the question to the team."
        )
    known = [note.code for note in notes if note.searched and not note.unknown]
    if len(known) >= 2:
        parts.append(
            "Every named model was searched on its own: "
            + ", ".join(known)
            + ". Report each one from its own result and show each found product. "
            "Never say a model has no entry unless that model's search returned nothing."
        )
    missed = [note.code for note in notes if not note.searched]
    if missed:
        parts.append(
            "Not searched this turn: "
            + ", ".join(missed)
            + ". Say they were not searched. Never say they are absent from the "
            "product data."
        )
    if not parts:
        return ""
    return " " + " ".join(parts)


def _knowledge_input(
    message: str, matches: list[Match], subject: Subject, lang: str
) -> dict[str, Any]:
    """search-knowledge for the message, narrowed to the products it names.

    The matched models (or the page's product) first; a series named without a
    model ("SAJ H2") narrows to the series' products instead — the family shares
    its datasheet and manual, so a few of its members carry its documents.
    """
    found: dict[str, Any] = {"query": message, "lang": lang}
    ids = list(subject.ids)
    if not ids:
        for match in matches:
            if match.kind == "series":
                for pid in sorted(subject.series_members.get(match.value, set())):
                    if pid not in ids:
                        ids.append(pid)
    if ids:
        found["product_ids"] = ids[:KNOWLEDGE_PRODUCTS]
    return found


def _pairing(subject: Subject, lang: str) -> Call | None:
    """check-compatibility for two products, the inverter's pairings for one."""
    if len(subject.ids) >= 2:
        return Call(
            "linker/check-compatibility", {"product_ids": list(subject.ids[:2])}
        )
    if len(subject.ids) == 1:
        product_id = subject.ids[0]
        device = subject.device_class.get(product_id)
        label = subject.labels.get(product_id)
        if device in ("inverters", "all-in-one-systems") and label:
            # The pairing search of the system prompt: the inverter by its model,
            # with the documented batteries and their verdicts.
            return Call(
                "linker/search-products",
                {
                    "device_class": device,
                    "with_pairings": True,
                    "text": label,
                    "lang": lang,
                    "limit": 1,
                },
            )
    return None


def service(message: str, reasons: list[str]) -> Route:
    """A company, delivery or service question: the team sentence (owner 2026-10-05)."""
    return Route(
        "service",
        (Call("linker/handoff-team", {"summary": message}),),
        hint=SERVICE_HINT,
        reasons=tuple(reasons),
    )


def with_page(
    route: Route,
    page: PageContext,
    about_page: bool,
    logged_in: bool,
    subject: Subject,
    message: str = "",
) -> Route:
    """The route with the page's content added when the message is about the page.

    Jev's `about_this_page` decides (#234). A signed-in customer's account page is
    their inquiries (inquiry-status); a solution draft is its products and the
    pairings among them; any other page is read (read-page). A request for a person,
    a company question, an inquiry status or a clarifying question reads nothing,
    and a delivery question about a page goes to the team whatever Jev says
    (`_LOGISTICS`).

    The calls fit the turn's budget in a fixed priority: the route's own calls (the
    subject's get-product among them) first, then the page, then the draft's pairs; a
    documents route leaves one call to the model (`DOCUMENTS_SPARE`). What does not
    fit is dropped, named in the turn log and, for a pair, in the hint.
    """
    if not about_page or route.name in ("person", "service", "inquiry", "clarify"):
        return route
    if _LOGISTICS.search(message):
        return service(message, [*route.reasons, "about this page: delivery"])
    added: list[Call] = []
    beyond: list[Call] = []
    hint = PAGE_HINT
    if page.type == "account" and logged_in:
        added.append(Call("linker/inquiry-status", {}))
        hint = ACCOUNT_HINT
    elif page.type == "draft":
        added.append(Call(READ_PAGE, {}))
        if not any(c.ability == "linker/check-compatibility" for c in route.calls):
            pairs = _draft_pairs(page.draft_ids or [], subject)
            added.extend(pairs[:DRAFT_PAIRS])
            beyond = pairs[DRAFT_PAIRS:]
        hint = DRAFT_HINT
    elif page.url:
        added.append(Call(READ_PAGE, {}))
    else:
        return route
    room = MAX_TOOL_CALLS - (DOCUMENTS_SPARE if route.name == "documents" else 0)
    ordered = [*route.calls, *(call for call in added if call not in route.calls)]
    calls, dropped = tuple(ordered[:room]), (*ordered[room:], *beyond)
    unchecked = [
        f"{c.arguments['inverter_id']}+{c.arguments['battery_id']}"
        for c in dropped
        if c.ability == "linker/check-compatibility"
    ]
    if unchecked:
        hint += (
            " Pairs of the draft not checked in this turn (inverter ID + battery ID): "
            + ", ".join(unchecked)
            + "; say that they were not checked yet and offer to check them."
        )
    kept_texts = {
        call.arguments.get("text")
        for call in calls
        if call.ability == "linker/search-products"
    }
    # A dropped search whose text is the model code was not searched. A family
    # suffix (ETA-G20) is not the code, so dropping only that search leaves the
    # code searched.
    named = tuple(
        replace(note, searched=False)
        if note.searched and note.code not in kept_texts
        else note
        for note in route.named_models
    )
    flipped = [
        note.code
        for previous, note in zip(route.named_models, named, strict=True)
        if previous.searched and not note.searched
    ]
    if flipped:
        hint += (
            " Not searched this turn: "
            + ", ".join(flipped)
            + ". Say they were not searched. Never say they are absent from the "
            "product data."
        )
    return Route(
        route.name,
        calls,
        show_products=route.show_products,
        action=route.action,
        no_cards=route.no_cards,
        no_handoff=route.no_handoff,
        hint=(route.hint + hint).strip(),
        reasons=(*route.reasons, f"about this page: {page.type}"),
        dropped=dropped,
        named_models=named,
        answer=route.answer,
    )


def _draft_pairs(ids: list[int], subject: Subject) -> list[Call]:
    """check-compatibility for each inverter and battery of the draft, in draft order.

    All pairs are returned; `with_page` checks `DRAFT_PAIRS` of them and names the rest.
    """
    inverters = [pid for pid in ids if subject.device_class.get(pid) in _INVERTERS]
    batteries = [pid for pid in ids if subject.device_class.get(pid) in _BATTERIES]
    pairs = [
        Call("linker/check-compatibility", {"inverter_id": inv, "battery_id": bat})
        for inv in inverters
        for bat in batteries
    ]
    return pairs
