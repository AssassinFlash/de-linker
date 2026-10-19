"""Code decides which tools a turn runs (docs/specs/13-genie.md, goal 2).

`plan()` reads the product words the lexicon found and Jev's answers, and returns a
`Route`: the ability calls the service makes before the model runs, and what the
answer must then show. deepseek-flash only writes the answer from those results.
When Jev is unsure (confidence below `CONFIDENT`) or did not answer, the route makes
no call of its own and the model decides — except that a brand, series or model word
always runs the product search: a product word is never a greeting.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from linker_genie import page as page_tool
from linker_genie.jev import Reading
from linker_genie.lexicon import MIN_CODE, Match, normalize
from linker_genie.nameplate import Identified
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
]


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
    if intent == "sizing":
        return Route(
            "sizing",
            (
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


# A stated size outside this band is not a residential prefill (#365 round 2).
# The configurator URL this reader fills is the residential form (spec 14:
# a commercial site brings a load profile, not these fields). Zero is a parse
# miss — a thousands group read on its own — not a size the customer stated.
# The ceilings are the round-2 review's bounds: above 1 000 kWp or
# 100 000 kWh/year the figure is dropped rather than written into the URL.
_MAX_KWP = 1000
_MAX_KWH = 100_000
# A quantity, including a thousands group. A group is three digits
# (German "4.500", English "12,000", spaced "12 000"; #365 round 2).
# Space, dot and comma are grouping; the last separator is the decimal
# when both appear. Grouped forms are tried first so "12 000" is one
# token and never the trailing "000". One or two digits after a single
# separator stay a decimal ("12,5", "12.5").
_NUM = (
    r"(?<!\d)(?P<num>"
    r"\d{1,3}(?:[ \u00a0]\d{3})+(?:[.,]\d+)?"
    r"|\d{1,3}(?:\.\d{3})+(?:,\d+)?"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?"
    r"|\d+(?:[.,]\d+)?"
    r")(?!\d)"
)
_KWP = re.compile(
    _NUM + r"\s*(?:kwp|kilo?watt[\s-]*peak|kw[\s-]*peak)\b",
    re.IGNORECASE,
)
# The year word may sit before the number ("annual consumption 6000 kWh") or
# after it ("6000 kWh Jahresverbrauch", "pro Jahr"). Longer phrases come first.
_YEAR_BEFORE = (
    r"(?:annual\s+consumption|annual\s+load|yearly\s+consumption|yearly\s+load|"
    r"consumption\s+per\s+year|jahresverbrauch|verbrauch\s+pro\s+jahr|"
    r"pro\s+jahr|im\s+jahr|jährlich|jaehrlich|yearly|annual)"
)
_YEAR_AFTER = (
    r"(?:/\s*(?:year|yr|jahr|a)\b|per\s+year|a\s+year|pro\s+jahr|im\s+jahr|"
    r"jährlich|jaehrlich|yearly|annual|jahresverbrauch)"
)
_GAP = r"(?:\s*[:\-]\s*|\s+)(?:(?:of|von|ca\.?|about|circa|rund|etwa|ungefähr|ungefaehr)\s+)?"
_ANNUAL_BEFORE = re.compile(
    _YEAR_BEFORE + _GAP + _NUM + r"\s*kwh\b",
    re.IGNORECASE,
)
_ANNUAL_AFTER = re.compile(
    _NUM + r"\s*kwh\b\s*,?\s*" + _YEAR_AFTER,
    re.IGNORECASE,
)
# "phasig" is not a prefix of "phase", so both stems are listed. A trailing
# inflection ("dreiphasigen", "Drehstromanschluss") stays the same word.
_THREE_PHASE = re.compile(
    r"\b(?:(?:3|three|drei)[\s-]*phas(?:e|ig)\w*|drehstrom\w*)\b",
    re.IGNORECASE,
)
_ONE_PHASE = re.compile(
    r"\b(?:(?:1|single|one|ein)[\s-]*phas(?:e|ig)\w*|wechselstrom\w*)\b",
    re.IGNORECASE,
)
_BACKUP = re.compile(
    r"\b(?:back-up|backup|notstrom|ersatzstrom)\w*\b",
    re.IGNORECASE,
)
# A German postcode is five digits (SizeHint.php `/^[0-9]{5}$/`, spec 13).
_PLZ_WORD = r"\b(?:plz|postleitzahl|postcode|zip(?:\s+code)?)\b"
_PLZ = re.compile(
    rf"{_PLZ_WORD}\s*[:\-]?\s*(?P<after>\d{{5}})(?!\d)"
    rf"|(?<!\d)(?P<before>\d{{5}})(?!\d)\s*[:\-]?\s*{_PLZ_WORD}",
    re.IGNORECASE,
)
# A negation applies to the keyword it stands next to, not to the whole
# message (#365 round 2: "kein Notstrom", "no backup needed", "Notstrom ist
# nicht nötig", "backup is not required"). Those sentences leave at most
# two words between the keyword and the negation. Three words is that gap
# plus one, so a short copula counts and a negation elsewhere does not.
# The 48-character slice in `_negated` holds those three words in either
# language.
_NEG_WORD = (
    r"(?:ohne|kein(?:e[mnrs]?)?|nicht|nie|niemals|without|no|not|"
    r"don'?t|do not|doesn'?t|does not|never)"
)
_NEG_BEFORE = re.compile(
    rf"\b{_NEG_WORD}\b(?:\s+\w+){{0,3}}\s*$",
    re.IGNORECASE,
)
_NEG_AFTER = re.compile(
    rf"^(?:\s+\w+){{0,3}}\s+\b{_NEG_WORD}\b",
    re.IGNORECASE,
)
# Verb-first (DE) and auxiliary / wh-first (EN) clauses are questions. A finite
# verb later in the clause is ordinary German word order ("Mein Haus ist
# einphasig") and is not a question by itself.
_LEADING_QUESTION = re.compile(
    r"""^[\s"'“”«»(\[]*(?:"""
    r"can|could|does|do|did|is|are|was|were|will|would|should|has|have|may|might|"
    r"what|which|how|why|when|where|who|"
    r"ist|sind|hat|haben|kann|können|koennen|wird|werden|"
    r"unterstützt|unterstuetzt|gibt|braucht|soll|sollen|darf|dürfen|duerfen|"
    r"wie|was|welche[rsnm]?|warum|wann|wo|wer|wieso|weshalb"
    r""")\b""",
    re.IGNORECASE,
)


def stated_size_hint(message: str | Sequence[str]) -> dict[str, Any]:
    """The size-hint object a configurator URL may be built from (#365).

    `sizing_input` is the only source. A string is one message. A sequence is
    the conversation's user messages in order: a later message overrides the
    same field and leaves the others, so a follow-up question keeps a size the
    customer already stated. Callers pass this dict on and drop whatever
    object they were given — the model's, when the route did not call the
    tool and the model calls it itself. A catalogue fact is not a source
    either: no rule copies a named product's phase into this prefill
    (docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md §1.12; the read
    stays deterministic, §1.1).

    A negated backup word is the stated value ``none`` (the configurator's
    own enum, SizeHint.php). Omitting it would drop a decision the customer
    already made. A negated phase word sets nothing and does not flip to the
    other phase. An interrogative clause does not set phase or backup.
    """
    texts = (message,) if isinstance(message, str) else tuple(message)
    found: dict[str, Any] = {}
    for text in texts:
        found.update(sizing_input(text))
    return found


def sizing_input(message: str) -> dict[str, Any]:
    """The five size-hint fields this message states (spec 13 §A).

    pv_kwp, annual_load_kwh, phase, backup and plz. A question clause still
    contributes a figure or a postcode — "what size for 8 kWp and 6000 kWh a
    year?" is how a customer states those — and contributes neither phase nor
    backup, because "can it do backup?" is not the customer's installation.
    """
    found: dict[str, Any] = {}
    for clause, interrogative in _clauses(message):
        if not interrogative:
            _read_phase(clause, found)
            _read_backup(clause, found)
        _read_kwp(clause, found)
        _read_annual(clause, found)
        _read_plz(clause, found)
    return found


def _clauses(message: str) -> list[tuple[str, bool]]:
    """Clauses split on ! ? ; newlines and a sentence stop.

    A dot followed by a digit stays inside the number ("4.500", "12.5",
    "12.000"). A comma is not a boundary either, so "12,5" stays one token.
    The terminator stays on the clause so a question mark still marks it.
    """
    pieces = re.split(r"([?!;\n]|\.(?!\d))", message)
    clauses: list[tuple[str, bool]] = []
    pending = ""
    for index, piece in enumerate(pieces):
        pending += piece
        if index % 2 == 0 and index + 1 < len(pieces):
            continue
        text = pending.strip()
        pending = ""
        if text:
            clauses.append(
                (text, "?" in text or _LEADING_QUESTION.search(text) is not None)
            )
    return clauses


def _parse_number(token: str) -> float | None:
    """A stated number. Grouping separators are not decimals of exactly three digits."""
    text = token.replace("\u00a0", "").replace(" ", "")
    if not text:
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif _grouped(text, ","):
        text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    elif _grouped(text, "."):
        text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


def _grouped(text: str, separator: str) -> bool:
    """True when `separator` groups thousands, not a decimal.

    A thousands group is three digits and the head group is one to three
    ("4.500", "12,000"; #365 round 2, route test "4.500 kWh pro Jahr" = 4500).
    One or two digits after the separator are a decimal ("12,5", "12.5").
    """
    parts = text.split(separator)
    if len(parts) > 2:
        return True
    return len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3


def _negated(text: str, start: int, end: int) -> bool:
    """Whether a negation word stands next to the keyword at [start, end)."""
    # 48 characters: the three-word window documented on `_NEG_WORD` (#365).
    before = _flat(text[max(0, start - 48) : start])
    after = _flat(text[end : end + 48])
    return (
        _NEG_BEFORE.search(before) is not None or _NEG_AFTER.search(after) is not None
    )


def _flat(text: str) -> str:
    """Curly apostrophes as `'`, so "don't" and "don’t" are the same word."""
    return text.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")


def _read_kwp(text: str, found: dict[str, Any]) -> None:
    for match in _KWP.finditer(text):
        value = _parse_number(match.group("num"))
        if value is not None and 0 < value <= _MAX_KWP:
            found["pv_kwp"] = value


def _read_annual(text: str, found: dict[str, Any]) -> None:
    hits: list[tuple[int, str]] = []
    for pattern in (_ANNUAL_BEFORE, _ANNUAL_AFTER):
        hits.extend(
            (match.start(), match.group("num")) for match in pattern.finditer(text)
        )
    for _start, token in sorted(hits):
        value = _parse_number(token)
        if value is not None and 0 < value <= _MAX_KWH:
            found["annual_load_kwh"] = value


def _read_phase(text: str, found: dict[str, Any]) -> None:
    mentions: list[tuple[int, int, int]] = []
    for match in _THREE_PHASE.finditer(text):
        mentions.append((match.start(), 3, match.end()))
    for match in _ONE_PHASE.finditer(text):
        mentions.append((match.start(), 1, match.end()))
    for start, phase, end in sorted(mentions):
        if _negated(text, start, end):
            if found.get("phase") == phase:
                del found["phase"]
            continue
        found["phase"] = phase


def _read_backup(text: str, found: dict[str, Any]) -> None:
    for match in _BACKUP.finditer(text):
        # `none` is a value the customer stated, not an empty field: the
        # configurator form's backup enum is none / needed / needed_accessory_ok
        # (SizeHint.php). A negated keyword must not become "needed".
        found["backup"] = (
            "none" if _negated(text, match.start(), match.end()) else "needed"
        )


def _read_plz(text: str, found: dict[str, Any]) -> None:
    for match in _PLZ.finditer(text):
        code = match.group("after") or match.group("before")
        if code:
            found["plz"] = code


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
    a company question or an inquiry status reads nothing, and a delivery question
    about a page goes to the team whatever Jev says (`_LOGISTICS`).

    The calls fit the turn's budget in a fixed priority: the route's own calls (the
    subject's get-product among them) first, then the page, then the draft's pairs; a
    documents route leaves one call to the model (`DOCUMENTS_SPARE`). What does not
    fit is dropped, named in the turn log and, for a pair, in the hint.
    """
    if not about_page or route.name in ("person", "service", "inquiry"):
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
