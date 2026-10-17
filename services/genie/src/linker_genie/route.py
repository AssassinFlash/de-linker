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
from dataclasses import dataclass, field
from typing import Any, Literal

from linker_genie.jev import Reading
from linker_genie.lexicon import Match

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

DOCUMENTS_HINT = (
    "This is a question about documents or technical values. Answer from the "
    "search-knowledge chunks (cite them) and the product facts; show the "
    "documents as document blocks. It is not a question for the team."
)

RouteName = Literal[
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


@dataclass(frozen=True)
class Call:
    ability: str
    arguments: dict[str, Any]


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

    def as_log(self) -> dict[str, Any]:
        return {
            "route": self.name,
            "calls": [
                {"name": c.ability, "arguments": c.arguments} for c in self.calls
            ],
            "show_products": self.show_products,
            "action": self.action,
            "no_cards": self.no_cards,
            "no_handoff": self.no_handoff,
            "reasons": list(self.reasons),
        }


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


def plan(
    message: str,
    matches: list[Match],
    reading: Reading | None,
    subject: Subject,
    lang: str,
    bare: bool = False,
) -> Route:
    """The route of one turn (module docstring).

    `bare` is true when the message is nothing but product words: then a category
    word ("EMS", "Zubehör") searches its products as a brand or model word does.
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

    if intent == "talk_to_person" or (
        intent is None and reading is not None and reading.wants_person >= LIKELY
    ):
        return person(message, reasons)
    if intent == "company_logistics_service":
        return Route(
            "service",
            (Call("linker/handoff-team", {"summary": message}),),
            hint=(
                "This is a company, delivery or service question: answer with the "
                "handoff block from the handoff-team result."
            ),
            reasons=tuple(reasons),
        )
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
            (Call("linker/size-hint", sizing_input(message)),),
            action="open_configurator",
            no_cards=True,
            no_handoff=True,
            hint=(
                "This is a sizing question. The Solution Configurator sizes the "
                "system from the customer's PV and consumption: say so in one or "
                "two sentences and add the open_configurator action (the "
                "service fills its URL). No product cards."
            ),
            reasons=tuple(reasons),
        )
    family = _family_hint(matches)
    if intent == "documents_specs":
        calls = [
            Call(
                "linker/search-knowledge",
                _knowledge_input(message, matches, subject, lang),
            )
        ]
        search = _search_input(matches, lang)
        if subject.ids:
            calls.extend(
                Call("linker/get-product", {"product_id": pid, "lang": lang})
                for pid in subject.ids[:2]
            )
        elif search is not None:
            calls.extend(_searches(search, matches, subject))
        return Route(
            "documents",
            tuple(calls),
            no_handoff=True,
            hint=DOCUMENTS_HINT + family,
            reasons=tuple(reasons),
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
    search = _search_input(matches, lang)
    if search is not None and (bare or intent == "find_products"):
        return Route(
            "products",
            _searches(search, matches, subject),
            show_products=True,
            no_handoff=True,
            hint=(
                "The customer named products; the search result is fetched. Show "
                "its products as cards, cited in the text refs. A product word is "
                "never a name or a greeting." + family
            ),
            reasons=tuple(reasons),
        )
    if (
        search is not None
        and named
        and reading is not None
        and reading.intent == "documents_specs"
    ):
        # Product words in a question Jev reads as a document question, however
        # sure it is: code runs both searches, the model does not decide whether
        # to look (trial question 9, "How do I set the export limit on an SAJ H2
        # inverter?", Jev documents_specs 0.67 — the model did not look and
        # answered that the documents had nothing; review of PR #279).
        return Route(
            "documents",
            (
                *_searches(search, matches, subject),
                Call(
                    "linker/search-knowledge",
                    _knowledge_input(message, matches, subject, lang),
                ),
            ),
            no_handoff=True,
            hint=DOCUMENTS_HINT + family,
            reasons=tuple(reasons),
        )
    if search is not None and named:
        # Product words inside a longer question that Jev could not place: code
        # still searches the named products (they are never small talk), and the
        # model decides the shape — cards are not forced on a how-to question
        # (trial question 9, Jev documents_specs 0.67, 2026-10-17).
        leaning = (
            f" Jev leans to {reading.intent} ({reading.confidence:.2f}): call "
            "search-knowledge if this is a document or technical question."
            if reading is not None
            else ""
        )
        return Route(
            "products",
            _searches(search, matches, subject),
            no_handoff=True,
            hint=(
                "The customer named products; the search result is fetched. A "
                "product word is never a name or a greeting." + leaning + family
            ),
            reasons=tuple(reasons),
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


def person(message: str, reasons: list[str]) -> Route:
    """The customer asks for a person.

    The seam for "Let Linker contact me" (#243): today the route hands the turn to the
    team mailbox through handoff-team, as before; #243 replaces this function's calls
    and hint with its contact request, and the router needs no other change.
    """
    return Route(
        "person",
        (Call("linker/handoff-team", {"summary": message}),),
        hint="The customer asks for a person: answer with the handoff block.",
        reasons=tuple(reasons),
    )


def sizing_input(message: str) -> dict[str, Any]:
    """The size-hint input the message states in figures (kWp, kWh a year, phase, backup)."""
    found: dict[str, Any] = {}
    kwp = _KWP.search(message)
    if kwp:
        found["pv_kwp"] = float(kwp.group(1).replace(",", "."))
    annual = _ANNUAL.search(message)
    if annual:
        found["annual_load_kwh"] = float(re.sub(r"[.,]", "", annual.group(1)))
    if _THREE_PHASE.search(message):
        found["phase"] = 3
    elif _ONE_PHASE.search(message):
        found["phase"] = 1
    if _BACKUP.search(message):
        found["backup"] = "needed"
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
