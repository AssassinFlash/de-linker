"""Code decides which tools a turn runs (docs/specs/13-genie.md, goal 2).

`plan()` reads the product words the lexicon found and Jev's answers, and returns a
`Route`: the ability calls the service makes before the model runs, and what the
answer must then show. deepseek-flash only writes the answer from those results.
When Jev is unsure (confidence below `CONFIDENT`) or did not answer, the route makes
no call of its own and the model decides — except that a brand, series or model word
always runs the product search: a product word is never a greeting. A short body
that more than one product holds, or a shared trailing suffix with no other product
word, is a fixed question: the service writes it and the model does not run. An
inquiry a guest may send, the whole-project remit, and the weather are fixed
sentences the same way. The Roof detail step's role and the cost of skipping it
are a fixed sentence too (#497), with size-hint supplying the configurator
action.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from linker_genie import page as page_tool
from linker_genie import planning as planning_tool
from linker_genie import solution as solution_tool
from linker_genie.jev import Reading
from linker_genie.lexicon import MAX_WORDS, MIN_CODE, Match, _words, normalize
from linker_genie.nameplate import Identified
from linker_genie.prefill import stated_size_hint
from linker_genie.schema import PageContext
from linker_genie.stock import asks, explicit, phrase
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
# The smallest count that is "several models in one message" (#364). The
# acceptance case is three codes; two is already enough to report one and
# invent the other. Dossier 2026-10-19 §1.11 and §2 item 10: aggregating
# several models has no published implementation to copy, so the cut is this
# ticket's — one named model stays a single search.
SEVERAL_MODELS = 2
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
# `lieferbar` is one of them (#415). with_page() therefore sends every page
# question that contains it, and is not itself a stock route, to the team.
# That is wider than a stock question. Recorded in docs/specs/69-stock.md.
_LOGISTICS = re.compile(
    r"\b(?:deliver(?:y|ies)|shipping|shipment|freight|lieferung(?:en)?|lieferzeit(?:en)?|"
    r"lieferbar|lieferkosten|versand(?:kosten)?|fracht(?:kosten)?)\b",
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
SOLUTION_HINT = (
    " The customer asks about their saved solution; its figures and its selection "
    "basis are here. " + solution_tool.RULE + " Speak to the customer about their "
    "saved solution; never mention a service, a reading, a tool or an id in the "
    "text."
)
# A question on the design report names the solution in words Jev may not read as
# "about this page": the page type is `other` (the configurator). These words make
# the read deterministic; besides them Jev's about_this_page decides (#234).
# `erdgas`-like false friends are not here; the words are the product's own
# (solution, design report) and the report's metric names.
_SOLUTION_WORDS = re.compile(
    r"\b(?:solution|solutions|lösung|lösungen|loesung|loesungen|"
    r"design[ -]report|auslegungsbericht|autarkie|autarky|"
    r"self[ -]?sufficien\w*|eigenverbrauch\w*|self[ -]?consumption|"
    r"jahresertrag|ertrag|erträge|yield)\b",
    re.IGNORECASE,
)
SERVICE_HINT = (
    "This is a company, delivery or service question: answer with only the "
    "handoff block, and set its summary to exactly {fact:handoff.sentence}. "
    "Do not write the one-working-day sentence yourself. The service adds "
    "that reply and the contact card."
)
# Greetings and identity questions, after lexicon.normalize (letters and digits
# only). A longer message that merely starts with one of these is not in the set.
_TALK = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "hallo",
        "moin",
        "servus",
        "gutentag",
        "gutenmorgen",
        "gutenabend",
        "goodmorning",
        "goodafternoon",
        "goodevening",
        "whoareyou",
        "whatareyou",
        "wersindsie",
        "werbistdu",
        "wassindsie",
        "wasbistdu",
    }
)
AnswerShape = Literal["talk", "promise", "partner"]
# Customer wording of these hints is owned by template.py (TALK, PROMISE,
# REPLY_PROMISE, PARTNER). prompts/{en,de}/system.md and the agent reminder
# repeat it. Change the sentence there first, or the four copies drift.
_SHAPE_HINT = {
    "talk": (
        "This is a greeting or an identity question. Say that you are Linker's "
        "AI assistant and that you help with products, compatibility, documents "
        "and sizing. Ask one question with field application and options home "
        "and commercial (German: Wohngebäude and Gewerbe). State no product "
        "fact, no number and no handoff."
    ),
    "promise": (
        "The customer asks what happens after they send an inquiry. Say that "
        "the Linker team replies within one working day. In German write that "
        "das Linker-Team antwortet innerhalb eines Werktags. Add the "
        "view_inquiry action with empty args. No handoff and no mailbox."
    ),
    "partner": (
        "The customer asks whether partners see net prices, and names no "
        "product. Say that approved partner accounts see net prices. A guest "
        'sees "Net price after partner sign-in" on the product card. An '
        'account under review sees "Account under review. Prices after '
        'approval." In German: freigegebene Partnerkonten sehen die '
        "Nettopreise; auf der Produktkarte steht für einen Gast "
        "„Nettopreis nach Partner-Anmeldung“ und für ein Konto in Prüfung "
        "„Ihr Konto wird geprüft. Preise nach Freigabe.“ Name no price and "
        "no digit. Ask one question with field application. No handoff."
    ),
}
# A stock-status question is the product's status, not the team mailbox
# (#415, spec 69). The sentences are the product page's (stock.phrase).
# Quantities stay out.
STOCK_HINT = (
    "This is a stock-status question, not a company, delivery or logistics "
    "question, and not a question for the team. Read commerce.in_stock. "
    f'When it is true, say exactly "{phrase("en", True)}". When it is false, '
    f'say exactly "{phrase("en", False)}". A German answer says '
    f'"{phrase("de", True)}" or "{phrase("de", False)}". Never state a '
    "quantity. Show the product as a card. The price stays on the card. "
    "When the products differ, do not state one status for all of them."
)
# A stock question that also asks about delivery. Delivery stays out of scope
# (owner 2026-10-05): the stock half is answered, and this part is the team
# sentence from handoff-team.
DELIVERY_WITH_STOCK = (
    " The message also asks about delivery. Delivery is out of scope: add the "
    "handoff block from the handoff-team result for that part, and still "
    "answer the stock status. Do not drop either part."
)
# The message asks something besides the stock status (#415 review round 3).
# The deterministic status answer would drop that half, so the model writes
# the turn: the stock status is one part of it, from commerce.in_stock, beside
# the normal answer. Delivery keeps its own shape (DELIVERY_WITH_STOCK).
STOCK_BESIDE_ANSWER = (
    " The message asks something else beside the stock status. Answer the whole "
    "message: the other question from the product data and the documents, and "
    "the stock status as one part of the answer, saying exactly "
    f'"{phrase("en", True)}" or "{phrase("en", False)}" '
    f'(German: "{phrase("de", True)}" or "{phrase("de", False)}"). State no '
    "quantity, and do not hand this question to the team. Show the product as "
    "a card; the price stays on the card."
)
# No product was named. search-products has no stock filter, so the turn asks
# which product to check instead of stating one status for the catalogue.
WHICH_PRODUCT = {
    "en": "Which product should I check the stock for?",
    "de": "Für welches Produkt soll ich den Lagerstatus prüfen?",
}
# Confident readings that already own the turn. A stock word inside a
# document, pairing, comparison, sizing or inquiry question stays there.
_STOCK_YIELDS = frozenset(
    {
        "documents_specs",
        "pairing_compatibility",
        "compare",
        "sizing",
        "inquiry_status",
    }
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
    "When this note also names model codes, name each of those codes in the "
    "same answer. Naming them does not add a card while extreme.applied is "
    "true, and it does not name a cheapest product while prices are hidden. "
    "English and German use this same shape."
)

DOCUMENTS_HINT = (
    "This is a question about documents or technical values. Answer from the "
    "search-knowledge chunks (cite them) and the product facts; show the "
    "documents as document blocks. It is not a question for the team."
)


def _show_product_with_documents(message: str) -> bool:
    """An explicit request to show a product beside its documents (#563).

    The route already knows this is a document question. A product mentioned
    as the owner of a datasheet is not a second requested object. Keep this
    conservative: unquoted, affirmative display wording and two coordinated
    objects, one product and one document. No inference from a model hit.
    """
    message = re.sub(
        r"""„[^“”]*[“”]|“[^”]*”|"[^"\n]*"|‘[^’]*’|»[^«]*«|«[^»]*»|'[^'\n]*'|`[^`\n]*`""",
        " ",
        message,
    )
    if re.search(
        r"\b(?:not|no|don't|do\s+not|nicht|kein\w*|ohne)\b",
        message,
        re.IGNORECASE,
    ):
        return False
    display = re.compile(r"\b(?:show|display|zeige[n]?|anzeigen)\b", re.IGNORECASE)
    if not display.search(message):
        return False
    parts = re.split(r"\b(?:and|und|sowie|plus)\b", message, flags=re.IGNORECASE)
    document = re.compile(
        r"\b(?:data\s?sheets?|manuals?|handbooks?|datenblatt|datenblätter|datenblaetter|"
        r"handbuch|handbücher|handbuecher|anleitungen?)\b",
        re.IGNORECASE,
    )
    product = re.compile(r"\b(?:products?|models?|produkte?|modelle?)\b", re.IGNORECASE)
    if not any(document.search(part) for part in parts):
        return False
    for index, part in enumerate(parts):
        if not product.search(part) or document.search(part):
            continue
        # "datasheets for A and B products" coordinates document owners,
        # not a separately requested product. A fresh display verb can
        # explicitly start a second request after that ownership phrase.
        owners = any(
            document.search(earlier)
            and re.search(r"\b(?:for|of|für|fuer|von)\b", earlier, re.IGNORECASE)
            for earlier in parts[:index]
        )
        if display.search(part) or not owners:
            return True
    return False


# The three obligations for a message that names models (#363, #364, #367).
# prompts/en/system.md carries this paragraph unchanged. The German prompt
# states the same three obligations in its own words. The per-turn reminder
# (agent.py) appends this paragraph, so the English wording has one source.
# Dossier 2026-10-19 §1.1, §1.11 and §2 item 10: no competitor publishes the
# aggregation, so the obligations are this ticket's design.
NAMED_MODEL_RULE = (
    "Several models in one message are each searched on their own. "
    "Report every searched model from its own result and show each product "
    "returned. Say a model has no entry only when that model's search returned "
    "nothing. A model the routing note marks as not searched must be described "
    "as not searched, never as absent. When the note says the customer named a "
    "brand the product data does not list for that model, name the brand the "
    "customer wrote and the brand from the product data in the same sentence, "
    "and show the product. A code the product data does not contain is outside "
    "the range; offer the closest products the search returned. None of these "
    "is a question for the team."
)
# The short form of the first obligation, for a route hint that names the codes.
_NOT_SEARCHED_HINT = (
    "Say they were not searched. Never say they are absent from the product data."
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
    # A fixed sentence: an inquiry open to guests, the whole-project remit, or
    # the weather. The service writes `Route.answer`. No tool call, no model.
    "scripted",
    # The Roof detail step (#497): its role and what skipping it costs. The
    # service writes `Route.answer`; size-hint supplies the configurator URL.
    # No model.
    "roof",
    "planning_project",
]

# A kWp or a yearly kWh keeps the turn on sizing. The extreme search uses
# these two shapes only as that gate. The configurator fields are read in
# prefill.py.
_KWP = re.compile(r"(\d+(?:[.,]\d+)?)\s*kwp\b", re.IGNORECASE)
_ANNUAL = re.compile(
    r"(\d{1,3}(?:[.,]\d{3})+|\d{3,6})\s*kwh\s*(?:/\s*(?:a|yr|year|jahr)\b|per\s+year|a\s+year|"
    r"pro\s+jahr|im\s+jahr|jährlich|yearly|annual)",
    re.IGNORECASE,
)
# A size word keeps a skipping question on sizing even without a figure: "Wie
# viel kWp kann ich auf meiner Dachfläche aufnehmen?" asks for the size, not
# about the step (#497 review). The size may sit against a digit ("12kWp"), so
# the unit needs no boundary before it; a module count is a size too ("Wie
# viele Module kann meine Dachfläche aufnehmen?").
_SIZE_WORD = re.compile(
    r"(?:kwp|kwh|kw)\b|\bmodules?\b|\bmodul\w*",
    re.IGNORECASE,
)
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

    @property
    def is_conflict(self) -> bool:
        """The customer wrote a brand the catalog does not list for this model."""
        return bool(self.written_brand and self.catalog_brand)

    @property
    def searched_known(self) -> bool:
        """Searched, and the catalog lists the code."""
        return self.searched and not self.unknown


# How one named model's calls turned out, once the turn's tool log is known.
# `product_ids` are lexicon ids, not the search result, so they cannot say
# "searched and returned nothing". That state is the `empty` outcome.
LookupOutcome = Literal["products", "empty", "failed", "unsearched"]


@dataclass(frozen=True)
class ModelLookup:
    """One named model joined to this turn's tool calls."""

    note: NamedModel
    outcome: LookupOutcome


def lookup_models(
    notes: tuple[NamedModel, ...],
    calls: list[dict[str, Any]],
    qualified_ids: set[int],
) -> tuple[ModelLookup, ...]:
    """Join each note to the calls that looked its code up.

    A covering call is search-products whose `text` is the code, or
    get-product for one of its product ids. A call the model makes later
    counts the same way: a note the budget left unsearched becomes searched
    when that call is in the log.

    - `products`: a covering call succeeded and returned one of the model's
      products, or get-product fetched one.
    - `empty`: a covering search succeeded and qualified none of the model's
      products. That is "searched and returned nothing". An unknown code has
      no catalog ids, so a successful search of that code is this outcome.
    - `failed`: the route searched the code, or a covering call came back not
      ok, and no covering call succeeded. A route call that raises
      AbilityError is omitted from the log (understand.py); the note stays
      searched and the outcome is `failed`.
    - `unsearched`: nothing looked the code up.

    A successful search-products call with no `text` confirms notes the route
    already marked searched. It does not look up a code the route left out.
    Production search calls carry `text` (abilities.record).
    """
    qualified = set(qualified_ids)
    legacy_ok = any(
        _search_call(call) and _call_ok(call) and _call_text(call) is None
        for call in calls
    )
    found: list[ModelLookup] = []
    for note in notes:
        specific_ok = False
        specific_bad = False
        got_product = False
        for call in calls:
            if _search_call(call) and _call_text(call) == note.code:
                if _call_ok(call):
                    specific_ok = True
                else:
                    specific_bad = True
            elif _get_call(call) and _call_product(call) in note.product_ids:
                if _call_ok(call):
                    specific_ok = True
                    got_product = True
                else:
                    specific_bad = True
        covered = specific_ok or (legacy_ok and note.searched)
        if covered:
            own = bool(set(note.product_ids) & qualified)
            outcome: LookupOutcome = "products" if own or got_product else "empty"
            searched = True
        elif specific_bad or note.searched:
            outcome = "failed"
            searched = True
        else:
            outcome = "unsearched"
            searched = False
        refreshed = (
            replace(note, searched=searched) if note.searched != searched else note
        )
        found.append(ModelLookup(refreshed, outcome))
    return tuple(found)


def absence_allowed(lookup: ModelLookup) -> bool:
    """Whether the answer may say this code is absent from the product data.

    Only an `empty` outcome: this code's own search succeeded and qualified
    none of its products. A failed search is an outage. A conflict is named
    (`is_conflict`), not called absent. An unsearched code is never absent.
    """
    if lookup.note.is_conflict:
        return False
    return lookup.outcome == "empty"


def _call_name(call: dict[str, Any]) -> str:
    return str(call.get("name", ""))


def _call_args(call: dict[str, Any]) -> dict[str, Any]:
    arguments = call.get("arguments")
    return arguments if isinstance(arguments, dict) else {}


def _call_ok(call: dict[str, Any]) -> bool:
    return call.get("ok") is True


def _call_text(call: dict[str, Any]) -> str | None:
    text = _call_args(call).get("text")
    return text if isinstance(text, str) and text else None


def _call_product(call: dict[str, Any]) -> int | None:
    product_id = _call_args(call).get("product_id")
    return product_id if isinstance(product_id, int) else None


def _search_call(call: dict[str, Any]) -> bool:
    return _call_name(call).endswith("search-products")


def _get_call(call: dict[str, Any]) -> bool:
    return _call_name(call).endswith("get-product")


def several(notes: tuple[NamedModel, ...], *, searched: bool = False) -> bool:
    """Whether `notes` reaches `SEVERAL_MODELS`.

    `searched` counts only models this turn looked up. The route's "show
    cards" decision counts every catalog model the customer named, including
    one the budget left out.
    """
    if searched:
        count = sum(1 for note in notes if note.searched_known)
    else:
        count = sum(1 for note in notes if not note.unknown)
    return count >= SEVERAL_MODELS


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
    # The customer asked whether a product is in stock (#415). The answer is
    # the page's status sentence, never a quantity and never the team mailbox.
    stock: bool = False
    # The message also asks something else (#415 review round 3). The status
    # is one part of the model's answer; the service's deterministic status
    # answer is only the whole-question case (simple_stock).
    stock_beside: bool = False
    # The same message also asks about delivery. Stock is answered; delivery
    # is the team sentence (owner 2026-10-05). Not a second route.
    delivery: bool = False
    # A sentence for the model about what the code did and what is expected.
    hint: str = ""
    reasons: tuple[str, ...] = field(default=())
    # Calls the turn's budget left out (with_page), kept for the turn log.
    dropped: tuple[Call, ...] = ()
    # Models the customer named, in the order of the message (#363, #364, #367).
    named_models: tuple[NamedModel, ...] = ()
    # The service's own sentence: a `clarify` route, a `scripted` route, or a
    # stock question that names no product. Empty when the model or another
    # template writes the turn.
    answer: str = ""
    # Which next-step sentence this model turn keeps (#394). None when the
    # route already has its own block (cards, a document, the configurator).
    shape: AnswerShape | None = None

    def as_log(self) -> dict[str, Any]:
        log: dict[str, Any] = {
            "route": self.name,
            "calls": [_call_log(c) for c in self.calls],
            "show_products": self.show_products,
            "action": self.action,
            "no_cards": self.no_cards,
            "no_handoff": self.no_handoff,
            "stock": self.stock,
            "reasons": list(self.reasons),
        }
        if self.delivery:
            log["delivery"] = True
        if self.stock_beside:
            log["stock_beside"] = True
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
        if self.shape:
            log["shape"] = self.shape
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


def _esa_battery_fit(compact: str) -> bool:
    """The recorded ESA battery question, not a compare and not a nearby fit.

    `lexicon.normalize` drops spaces. "which battery works" and "welcher
    Speicher passt zum SAJ" do not match. A compare names the ESA and is
    excluded so this sentence does not replace that answer.
    """
    if "compare" in compact or "vergleichen" in compact:
        return False
    if "goodweesa" not in compact:
        return False
    return "whichbatteryfits" in compact or "welcherspeicherpasst" in compact


def _attach_esa_battery(route: Route, message: str, lang: str) -> Route:
    """Stamp the signed battery sentence without skipping the model.

    A products route with `answer` set still runs the model: `_answer`
    short-circuits only person, clarify, scripted, roof and parts. `finish()`
    replaces the model's prose when this reason is present. A route that
    already has its own sentence, a stock answer, or another name is left
    alone. Product ids stay the tool's; this stamp names the codes only.
    """
    if (
        route.stock
        or route.answer
        or route.name not in ("products", "pairing", "model")
    ):
        return route
    if not _esa_battery_fit(normalize(message)):
        return route
    # Lazy: template imports Route from this module.
    from linker_genie.template import ESA_BATTERY

    language = "de" if lang == "de" else "en"
    return replace(
        route,
        answer=ESA_BATTERY[language],
        reasons=(*route.reasons, "esa battery"),
    )


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

    An ESA battery-fit question also carries the signed battery sentence.
    The model still writes from the tool results; `finish()` replaces that
    prose so a kilowatt list cannot fail the number allowlist. Stamping here
    means a unit test that calls `plan()` sees the same route as a live turn.
    """
    return _attach_esa_battery(
        _plan_turn(message, matches, reading, subject, lang, bare, earlier),
        message,
        lang,
    )


def _plan_turn(
    message: str,
    matches: list[Match],
    reading: Reading | None,
    subject: Subject,
    lang: str,
    bare: bool = False,
    earlier: Sequence[str] = (),
) -> Route:
    """The route of one turn before the ESA battery stamp.

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

    # These three keep the routes they had before #394. The next step is the
    # prompt and the template, not a model route that skips them.
    if intent == "talk_to_person":
        # Frustration on another intent is answered as routed, with the contact
        # offer beside it (contact.decide).
        return person(reasons)
    # An inquiry a guest may send, the whole-project remit, and the weather are
    # fixed sentences (#440). They beat a confident inquiry, sizing or company
    # reading: those readings called inquiry-status, size-hint or handoff-team,
    # and the model then stated facts the reference does not contain.
    scripted = _scripted(message, lang, reasons)
    if scripted is not None:
        return scripted
    # The Roof detail step's role and the cost of skipping it (#497). The
    # sentence is signed, and the configurator action's URL comes from
    # size-hint. A named product, a stated or asked size or a company reading
    # keeps its own route; a confident sizing reading does not replace the
    # step's name.
    roof = _roof_step(message, matches, intent, lang, reasons)
    if roof is not None:
        return roof
    # A brand or series extreme is one aggregate (#368), not a brand/model
    # conflict. Two catalog models stay on the per-model searches for
    # smallest and largest: one class aggregate would hide those codes. An
    # unknown code beside a class extreme keeps the aggregate and a search
    # for every written code, known or unknown, including when several
    # catalog models are written beside it (#384). A cheapest question over
    # written models also keeps the aggregate, so a hidden price still
    # returns price_hidden, unless one written model conflicts with the
    # written brand. That conflict stays off the aggregate: the aggregate
    # is brand-filtered, so it cannot be the conflicting product, and the
    # conflict hint would also demand that product's card.
    # Dossier §1.1 and §1.11 have no procedure for either mix.
    # Written codes, unknown codes and the aggregate are read once.
    written = _written_models(matches, message)
    several_written = len(written) >= SEVERAL_MODELS
    unknown_codes = _unknown_codes(message, subject)
    brand_conflict = _conflicts_with_written_brand(written, matches, subject)
    aggregate = None if brand_conflict else extreme_input(message, matches, lang)
    # The extreme is the turn in the same cases the blocks below return it:
    # a composite (an unknown code, or a cheapest question over several
    # written models), or a single aggregate over at most one written model.
    extreme = aggregate is not None and (
        unknown_codes or not several_written or aggregate.get("extreme") == "cheapest"
    )
    # Stock status beats the logistics handoff (#415). Jev files "in stock" as
    # company_logistics_service; the product page already knows the status.
    # A catalogue extreme, and a confident document, pairing, comparison,
    # sizing or inquiry reading, keep the route they already have.
    if (
        _takes_stock(message, matches, subject)
        and intent not in _STOCK_YIELDS
        and not extreme
    ):
        return _stock_route(
            message,
            matches,
            subject,
            lang,
            reasons,
            whole=_asks_only_stock(message, matches),
        )
    if intent == "company_logistics_service":
        return service(message, reasons)
    if intent == "inquiry_status":
        return Route(
            "inquiry",
            (Call("linker/inquiry-status", {}),),
            no_handoff=True,
            hint=(
                "The inquiry-status result is fetched; answer from it. A "
                "signed-in answer adds the view_inquiry action with empty "
                "args. A guest (login_required) is exactly one text block, "
                "{fact:inquiry.login}, and nothing else."
            ),
            reasons=tuple(reasons),
        )
    # A partner-price question, an inquiry aftermath, or a greeting that no
    # intent route claimed stays on the model. A named product, and a bare
    # product word, stay a product search. Stock, company and inquiry already
    # returned, so a shape does not replace them (#394, #415).
    shape = _answer_shape(message, named=bool(named), bare=bare)
    if shape:
        reasons.append(f"answer shape: {shape}")
        return Route(
            "model",
            no_cards=True,
            no_handoff=True,
            hint=_SHAPE_HINT[shape],
            reasons=tuple(reasons),
            shape=shape,
        )
    if aggregate is not None and (
        unknown_codes or (several_written and aggregate.get("extreme") == "cheapest")
    ):
        return _composite_extreme(
            aggregate,
            reasons,
            matches,
            subject,
            lang,
            message,
            search_matched_models=bool(written),
            unknown_codes=unknown_codes,
        )
    if aggregate is not None and not several_written:
        reasons.append(f"extreme: {aggregate['extreme']}")
        return Route(
            "products",
            (Call("linker/search-products", aggregate),),
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
    reasons.extend(_note_reasons(notes))
    if intent == "documents_specs":
        # Known products are fetched with get-product; a code with no product
        # id is searched. Either call counts as searched. What does not fit
        # the four-call budget is searched=False — never reported absent.
        # Dossier 2026-10-19 §1.11: no competitor publishes this aggregation.
        doc_calls, notes = _documents_calls(
            calls, notes, message, matches, subject, lang
        )
        return Route(
            "documents",
            doc_calls,
            show_products=_show_product_with_documents(message),
            no_handoff=True,
            hint=DOCUMENTS_HINT + family + _model_hint(notes),
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
    hint_extra = _model_hint(notes)
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
        # search-knowledge shares the four-call budget with those searches
        # (spec 13 §B). A model whose search does not fit is not searched.
        doc_calls, notes = _limit_route_calls(
            (
                *calls,
                Call(
                    "linker/search-knowledge",
                    _knowledge_input(message, matches, subject, lang),
                ),
            ),
            notes,
            limit=MAX_TOOL_CALLS - DOCUMENTS_SPARE,
        )
        return Route(
            "documents",
            doc_calls,
            show_products=_show_product_with_documents(message),
            no_handoff=True,
            hint=DOCUMENTS_HINT + family + _model_hint(notes),
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


def _composite_extreme(
    extreme: dict[str, Any],
    reasons: list[str],
    matches: list[Match],
    subject: Subject,
    lang: str,
    message: str,
    *,
    search_matched_models: bool,
    unknown_codes: tuple[str, ...],
) -> Route:
    """The class aggregate, then one search per written code (#384).

    `search_matched_models` is true when the message writes catalog models.
    Those models are searched as well as `unknown_codes`, the codes this
    turn already read. Dossier §1.1 has no procedure for a sentence that is
    both an extreme and a list of codes, and §1.11 has none for separating
    those codes. Each part keeps the call it already had. The aggregate is
    first and is the only call that carries `extreme`, so a hidden price is
    recorded once and a per-code search cannot name a second winner. The
    hint names each unknown code, and it names known codes when at least
    two of them were searched. One known code beside one unknown code is
    not repeated in the known-code sentence. The hint still allows only the
    winner card when the aggregate is applied.
    """
    reasons.append(f"extreme: {extreme['extreme']}")
    if search_matched_models:
        calls, notes = _search_plan(matches, lang, subject, message)
        extra_calls, extra_notes = _unknown_calls(unknown_codes, lang, subject)
        calls = (*calls, *extra_calls)
        notes = (*notes, *extra_notes)
    else:
        calls, notes = _unknown_calls(unknown_codes, lang, subject)
    calls, notes = _limit_route_calls(
        (Call("linker/search-products", extreme), *calls),
        notes,
    )
    reasons.extend(_note_reasons(notes))
    return Route(
        "products",
        calls,
        show_products=True,
        no_handoff=True,
        hint=EXTREME_HINT + _model_hint(notes, winner_only=True),
        reasons=tuple(reasons),
        named_models=notes,
    )


def extreme_input(
    message: str, matches: list[Match], lang: str
) -> dict[str, Any] | None:
    """search-products arguments for a smallest, largest or cheapest question.

    A kWp or annual-consumption figure stays a sizing question. The floor is
    AC power for an inverter (or a kW figure) and energy for a battery (or a
    kWh figure). A named model is not a filter: the extreme is taken over the
    class, narrowed by a single brand or series when the message names one.
    `plan` uses this for the aggregate half of a composite question as well.
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


# A code-shaped token in the raw message: a letter, a digit, and at least two
# "-" or "/" joins. One join is a phase or a rating ("3-phase", "10-20"); the
# unknown-model case in #363 is GW50K-ETA-G20. MIN_CODE (lexicon.py) is the
# shortest real code, four characters ("L260", snapshot 2026-10-15). The token
# is a model only when it also has a catalog prefix or suffix (`_catalog_shaped`):
# an order number ("ABC-123-456") has the joins and is not a model.
_ASKED_CODE = re.compile(
    r"(?<![\w.])(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]+(?:[./][A-Za-z0-9]+)*"
    r"(?:[-/][A-Za-z0-9]+(?:[./][A-Za-z0-9]+)*){2,}(?![\w])"
)
_CODE_SPLIT = re.compile(r"[-/]")
_LEADING_LETTERS = re.compile(r"[A-Za-z]+")


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
    """Whether any written model belongs to a brand other than the one named.

    One conflicting code used to be the only case (#368). Several written
    models can carry the same conflict (#384): the aggregate is filtered to
    the written brand, so it can never be that product.
    """
    if not written:
        return False
    brands = [match for match in matches if match.kind == "brand"]
    if len({match.value for match in brands}) != 1:
        return False
    brand = brands[0].value
    return any(_conflicts(model, brand, subject) for model in written)


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
    prefixes = _catalog_shapes(subject)
    found: list[str] = []
    seen: set[str] = set()
    for match in _ASKED_CODE.finditer(message):
        code = match.group(0)
        key = normalize(code)
        if key in seen or key in known or len(key) < MIN_CODE:
            continue
        if not any(ch.isalpha() for ch in key) or not any(ch.isdigit() for ch in key):
            continue
        if not _catalog_shaped(code, prefixes):
            continue
        seen.add(key)
        found.append(code)
    return tuple(found)


def _catalog_shapes(subject: Subject) -> set[str]:
    """Leading tokens of the catalog's brands and model codes.

    A prefix is at least two characters. The shortest brand letter-run in the
    published catalog is two (GW, HS, EF; snapshot 2026-10-15, the store
    snapshot lexicon.MIN_CODE cites for the four-character code "L260"). A
    one-letter run is not a brand or a series. MIN_CODE is the full code, not
    this prefix. The shapes come from the catalog, not from a hand-written list.
    """
    prefixes: set[str] = set()
    for slug, label in subject.brand_names.items():
        for word in (slug, label):
            letters = _LEADING_LETTERS.match(word)
            # Two: shortest brand letter-run in that snapshot. Not a new cut.
            if letters and len(letters.group(0)) >= 2:
                prefixes.add(letters.group(0).casefold())
    for code in subject.catalog_models:
        parts = [part for part in _CODE_SPLIT.split(code) if part]
        if not parts:
            continue
        letters = _LEADING_LETTERS.match(parts[0])
        if letters and len(letters.group(0)) >= 2:
            prefixes.add(letters.group(0).casefold())
        if len(parts[0]) >= 2 and any(ch.isalpha() for ch in parts[0]):
            prefixes.add(parts[0].casefold())
    return prefixes


def _catalog_shaped(code: str, prefixes: set[str]) -> bool:
    """Whether `code` starts with a known brand, series, or model token.

    "GW" from GW10K-ETA-G20 makes GW50K-ETA-G20 catalog-shaped. A catalog
    suffix alone does not: ORDER-2026-G20 ends in G20 and DLK-2026-001 has
    the shop prefix, and neither is a model. "ABC-123-456" matches no prefix.
    """
    parts = [part for part in _CODE_SPLIT.split(code) if part]
    if not parts:
        return False
    letters = _LEADING_LETTERS.match(parts[0])
    lead = letters.group(0).casefold() if letters else ""
    if len(lead) >= 2 and lead in prefixes:
        return True
    return len(parts[0]) >= 2 and parts[0].casefold() in prefixes


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
    if any(note.is_conflict or note.unknown for note in notes):
        return True
    return several(notes)


def _note_reasons(notes: tuple[NamedModel, ...]) -> list[str]:
    reasons: list[str] = []
    if any(note.is_conflict for note in notes):
        reasons.append("brand and model disagree")
    if any(note.unknown for note in notes):
        reasons.append("model code not in the product data")
    if several(notes):
        reasons.append("several models")
    return reasons


def _model_hint(notes: tuple[NamedModel, ...], *, winner_only: bool = False) -> str:
    """What the model is told about each named code. English, both locales.

    `winner_only` is an extreme whose aggregate may be applied. Grounding then
    allows exactly that card, so this hint must not ask for a card per code.
    """
    parts: list[str] = []
    conflicts = [note for note in notes if note.is_conflict and note.searched]
    if conflicts:
        named = "; ".join(
            f"{note.code} is {note.catalog_brand} in the product data; "
            f"the customer wrote {note.written_brand}"
            for note in conflicts
        )
        parts.append(
            named + ". Name the brand the customer wrote and the brand from the "
            "product data in the same sentence, show that product as a card, and "
            "do not say the model is missing. This is not a question for the team."
        )
    unknown = [note.code for note in notes if note.unknown and note.searched]
    if unknown:
        if winner_only:
            parts.append(
                "These model codes are not in the product data: "
                + ", ".join(unknown)
                + ". Say that plainly. When extreme.applied is true, show only "
                "the winner card. Do not hand the question to the team."
            )
        else:
            parts.append(
                "These model codes are not in the product data: "
                + ", ".join(unknown)
                + ". Say that plainly and offer the closest products the search "
                "returned. Do not hand the question to the team."
            )
    known = [note.code for note in notes if note.searched_known]
    if len(known) >= SEVERAL_MODELS:
        listed = ", ".join(known)
        if winner_only:
            report = (
                "Name each one from its own result. "
                "When extreme.applied is true, show only the winner card. "
            )
        else:
            report = "Report each one from its own result and show each found product. "
        parts.append(
            "Every named model was searched on its own: "
            + listed
            + ". "
            + report
            + "Never say a model has no entry unless that model's search "
            "returned nothing."
        )
    missed = [note.code for note in notes if not note.searched]
    if missed:
        parts.append(
            "Not searched this turn: " + ", ".join(missed) + ". " + _NOT_SEARCHED_HINT
        )
    if not parts:
        return ""
    return " " + " ".join(parts)


def _documents_calls(
    calls: tuple[Call, ...],
    notes: tuple[NamedModel, ...],
    message: str,
    matches: list[Match],
    subject: Subject,
    lang: str,
) -> tuple[tuple[Call, ...], tuple[NamedModel, ...]]:
    """Knowledge, then get-product for known ids, then searches that are still needed.

    A model is searched when get-product fetches one of its products or
    search-products runs on its code. Search calls for a code get-product
    already covers are left out, so a single known model stays
    search-knowledge plus get-product. The list is then cut to
    `MAX_TOOL_CALLS - DOCUMENTS_SPARE` (spec 13 §B is four ability calls a
    turn; one stays for the model's follow-up, trial question 10). A model
    that does not fit is searched=False.
    """
    knowledge = Call(
        "linker/search-knowledge",
        _knowledge_input(message, matches, subject, lang),
    )
    body: list[Call] = []
    fetched: set[int] = set()
    for product_id in subject.ids:
        body.append(
            Call("linker/get-product", {"product_id": product_id, "lang": lang})
        )
        fetched.add(product_id)
    covered = {
        note.code
        for note in notes
        if note.product_ids and set(note.product_ids) <= fetched
    }
    for call in calls:
        text = call.arguments.get("text")
        if call.ability == "linker/search-products" and text in covered:
            continue
        body.append(call)
    return _limit_route_calls(
        (knowledge, *body), notes, limit=MAX_TOOL_CALLS - DOCUMENTS_SPARE
    )


def _limit_route_calls(
    calls: tuple[Call, ...],
    notes: tuple[NamedModel, ...],
    limit: int = MAX_TOOL_CALLS,
) -> tuple[tuple[Call, ...], tuple[NamedModel, ...]]:
    """Keep at most `limit` calls. A knowledge call is never the one dropped.

    Spec 13 §B: at most four ability calls a turn. Dropping a later search
    marks that model not searched (`_notes_after_calls`).
    """
    knowledge = sum(1 for call in calls if call.ability == "linker/search-knowledge")
    room = limit - knowledge
    kept: list[Call] = []
    others = 0
    for call in calls:
        if call.ability == "linker/search-knowledge":
            kept.append(call)
            continue
        if others >= room:
            continue
        kept.append(call)
        others += 1
    kept_calls = tuple(kept)
    return kept_calls, _notes_after_calls(notes, kept_calls)


def _notes_after_calls(
    notes: tuple[NamedModel, ...], calls: tuple[Call, ...]
) -> tuple[NamedModel, ...]:
    """A searched note stays searched only when a kept call looked the code up.

    search-products whose text is the code, or get-product for one of its
    product ids. A family-suffix search is not the code.
    """
    texts = {
        call.arguments.get("text")
        for call in calls
        if call.ability == "linker/search-products"
    }
    fetched = {
        call.arguments.get("product_id")
        for call in calls
        if call.ability == "linker/get-product"
    }
    updated: list[NamedModel] = []
    for note in notes:
        found = note.code in texts or any(pid in fetched for pid in note.product_ids)
        if note.searched and not found:
            updated.append(replace(note, searched=False))
        else:
            updated.append(note)
    return tuple(updated)


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


def simple_stock(route: Route) -> bool:
    """Whether the service can state this stock turn without the model.

    Only the whole question being about stock is the deterministic case
    (#415 review round 3): when the message also asks something else, the
    model answers the whole message and the status is one part of it
    (`stock_beside`). A brand conflict, an unknown code, or several models
    keep the clarification the product-word path already writes.
    """
    if not route.stock or route.stock_beside:
        return False
    notes = route.named_models
    if any(note.is_conflict or note.unknown for note in notes):
        return False
    return not several(notes)


def _takes_stock(message: str, matches: list[Match], subject: Subject) -> bool:
    """Whether this message is a stock question the product path should answer.

    "available", "unavailable", "verfügbar" and "ausverkauft" are stock
    asks when a product is named. "Is 3-phase available?" names no product
    and stays where Jev put it. An explicit status word ("in stock",
    "auf Lager", "stock status", "Lagerstatus") is stock either way,
    including "What do you have in stock?" with no product.
    """
    if not asks(message):
        return False
    if explicit(message):
        return True
    return _about_a_product(message, matches, subject)


def _about_a_product(message: str, matches: list[Match], subject: Subject) -> bool:
    """Whether the message names a product the catalogue can be asked about.

    A product word in the message, or an unknown model code, names one. The
    page's product id alone does not: "Is 3-phase available?" on a product
    page asks about a specification, and stays where Jev put it (the test
    test_available_without_a_product_stays_off_the_stock_route). A pointer at
    the page's product ("Is it available?") does name it.
    """
    if any(match.kind in ("brand", "series", "model", "category") for match in matches):
        return True
    if _unknown_codes(message, subject):
        return True
    return bool(subject.ids) and _PAGE_POINTER.search(message) is not None


# A question on a product page that points at the page's product ("Is it
# available?") is about that product. A specification ("Is 3-phase
# available?") is not (#415 review round 3).
_PAGE_POINTER = re.compile(
    r"\b(?:it|this|that|these|those|they|them|"
    r"der|die|das|den|dem|es|sie)\b",
    re.IGNORECASE,
)
# Clause separators of a message: a question mark, exclamation mark, semicolon
# or comma, a sentence-ending full stop (not the full stop inside a model code
# like GW99.99K-ET-G10), and the conjunctions that join two asks
# ("efficiency ... and is it in stock").
_ASK_CLAUSE = re.compile(r"[?？!;,，]|\.(?=\s|$)|\band\b|\bund\b", re.IGNORECASE)
# Words that carry no ask of their own, EN and DE. A clause that holds only
# these beside the product words is a mention of the product, not a second
# question.
_STOCK_FILLER = frozenset(
    {
        "a",
        "an",
        "the",
        "what",
        "which",
        "is",
        "are",
        "was",
        "were",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "can",
        "could",
        "would",
        "will",
        "you",
        "your",
        "i",
        "we",
        "me",
        "my",
        "our",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "of",
        "for",
        "to",
        "please",
        "tell",
        "say",
        "if",
        "whether",
        "currently",
        "right",
        "now",
        "still",
        "actually",
        "and",
        "or",
        "also",
        "about",
        "on",
        "at",
        "in",
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
        "ist",
        "sind",
        "war",
        "waren",
        "wie",
        "welche",
        "welcher",
        "welches",
        "sie",
        "er",
        "es",
        "ich",
        "wir",
        "mir",
        "mich",
        "uns",
        "bitte",
        "gerade",
        "aktuell",
        "zurzeit",
        "noch",
        "ob",
        "und",
        "oder",
        "haben",
        "hat",
        "habt",
        "kann",
        "können",
        "koennen",
        "koennte",
        "würde",
        "wuerde",
        "gibt",
        "zu",
        "im",
        "am",
        "für",
        "fuer",
        "von",
        "vom",
        "mit",
        "bei",
        "auch",
    }
)


def _asks_only_stock(message: str, matches: list[Match]) -> bool:
    """Whether every clause of the message asks about stock status or delivery.

    "What is the efficiency of the SAJ H2-10K-T3 and is it in stock?" has an
    efficiency clause, so the deterministic status answer would drop that half
    (#415 review round 3). A delivery clause does not count against the whole
    question: delivery is already the team sentence beside the stock
    (DELIVERY_WITH_STOCK).
    """
    clauses = [clause.strip() for clause in _ASK_CLAUSE.split(message)]
    clauses = [clause for clause in clauses if clause]
    if not clauses:
        return False
    for clause in clauses:
        if asks(clause) or _LOGISTICS.search(clause):
            continue
        if _only_product_words(clause, matches):
            continue
        return False
    return True


def _only_product_words(clause: str, matches: list[Match]) -> bool:
    """Whether this clause is a product mention and nothing else.

    The matched product words are removed, then the clause is only filler
    ("the SAJ H2-10K-T3", "What about the H2-10K-T3?"). Any other word is a
    second ask.
    """
    rest = clause
    for match in matches:
        for written in (match.words, match.value):
            if written:
                rest = re.sub(re.escape(written), " ", rest, flags=re.IGNORECASE)
    tokens = [token.casefold() for token in re.split(r"[^\w]+", rest) if token]
    return all(token in _STOCK_FILLER for token in tokens)


def _stock_route(
    message: str,
    matches: list[Match],
    subject: Subject,
    lang: str,
    reasons: list[str],
    *,
    whole: bool,
) -> Route:
    """The product search for a stock-status question, then the status hint.

    `whole` is true when every clause asks stock or delivery: the service can
    state the status itself (simple_stock). Otherwise the message also asks
    something else, the model answers the whole message, and the status is
    one part of it (STOCK_BESIDE_ANSWER, #415 review round 3).

    A page product with no model word in the message is read with get-product.
    The calls are the same searches a product question would make, so a
    conflict or an unknown code still reaches the clarification. No named
    product asks which one to check: search-products cannot filter by stock.
    A delivery word in the same message keeps a handoff-team call. Delivery
    is the team sentence; the stock half is still answered.
    """
    calls, notes = _search_plan(matches, lang, subject, message)
    if not calls and subject.ids:
        calls = tuple(
            Call("linker/get-product", {"product_id": product_id, "lang": lang})
            for product_id in subject.ids[:MAX_TOOL_CALLS]
        )
    delivery = _LOGISTICS.search(message) is not None
    if delivery:
        # Keep the team call inside the turn's budget. A later product search
        # is the one that yields, and its note is marked not searched.
        calls = calls[: MAX_TOOL_CALLS - 1]
        notes = _notes_after_calls(notes, calls)
        calls = (
            *calls,
            Call("linker/handoff-team", {"summary": message}),
        )
    product_calls = tuple(
        call for call in calls if not call.ability.endswith("handoff-team")
    )
    which = ""
    if whole and not product_calls and not notes:
        which = WHICH_PRODUCT["de" if lang.startswith("de") else "en"]
        reasons.append("no product named")
    hint = (STOCK_HINT if whole else STOCK_BESIDE_ANSWER) + _model_hint(notes)
    if delivery:
        hint += DELIVERY_WITH_STOCK
    label = "stock status" if whole else "stock status beside another answer"
    return Route(
        "products",
        calls,
        show_products=not which,
        no_cards=bool(which),
        no_handoff=not delivery,
        stock=True,
        stock_beside=not whole,
        delivery=delivery,
        hint=hint,
        reasons=(*reasons, label, *_note_reasons(notes)),
        named_models=notes,
        answer=which,
    )


# Account absence and an inquiry or quote noun, on the compact form
# `lexicon.normalize` produces (letters and digits only). "withoutanaccount"
# does not contain "noaccount"; "ohnekundenkonto" does not contain "ohnekonto".
_ABSENCE = (
    "withoutanaccount",
    "noaccount",
    "ohnekundenkonto",
    "ohnekonto",
    "ohneanmeldung",
)
_INQUIRY_NOUN = ("quote", "inquiry", "enquiry", "anfrage", "angebot")


def _scripted(message: str, lang: str, reasons: list[str]) -> Route | None:
    """A fixed sentence that beats a confident misreading (#440).

    An inquiry a guest may send, the whole-project remit, and the weather.
    Matched on `lexicon.normalize`, so spaces and punctuation do not matter.
    Weather is checked first: a sentence that names both stays weather. The
    baseline rows do not overlap.
    """
    compact = normalize(message)
    if "weather" in compact or "wetter" in compact:
        kind = "weather"
    elif _open_inquiry(compact):
        kind = "open"
    elif _whole_project(compact):
        kind = "remit"
    else:
        return None
    # Lazy: template imports Route from this module.
    from linker_genie.template import SCRIPTED

    language = "de" if lang == "de" else "en"
    return Route(
        "scripted",
        no_cards=True,
        no_handoff=True,
        action="send_inquiry" if kind == "open" else None,
        answer=SCRIPTED[kind][language],
        reasons=(*reasons, f"scripted: {kind}"),
    )


def _open_inquiry(compact: str) -> bool:
    return any(marker in compact for marker in _ABSENCE) and any(
        noun in compact for noun in _INQUIRY_NOUN
    )


def _whole_project(compact: str) -> bool:
    english = (
        "whole" in compact
        and any(word in compact for word in ("solar", "project", "pv"))
        and any(word in compact for word in ("plan", "help"))
    )
    german = "gesamt" in compact and any(
        word in compact for word in ("plan", "hilfe", "helfen")
    )
    return english or german


# Roof-step questions (#497). Each entry is (marker, source stem): the marker is
# `lexicon.normalize(source)`, so spaces, case and punctuation do not matter and
# the stem stops before the inflection ("Dach weglass" covers weglasse and
# weglassen). Sources: the step's name in the site copy (#12), the ticket's two
# questions and their natural variants, and the engine's "without a roof plane"
# sentence (#479 C57). `test_every_roof_marker_is_its_sources_normalized_form`
# holds the generation rule.
_ROOF_STEP_NAMES = (
    ("roofdetail", "Roof detail"),
    ("roofstep", "Roof step"),
    ("dachdetail", "Dachdetail"),
    ("dachschritt", "Dachschritt"),
)
_ROOF_STEP_SKIPS = (
    ("skiptheroof", "skip the roof"),
    ("skiproof", "skip roof"),
    ("withouttheroof", "without the roof"),
    ("withoutaroof", "without a roof"),
    ("leavetheroofout", "leave the roof out"),
    ("leaveouttheroof", "leave out the roof"),
    ("ignoretheroof", "ignore the roof"),
    ("dontusetheroof", "don't use the roof"),
    ("donotusetheroof", "do not use the roof"),
    ("notusetheroof", "not use the roof"),
    ("dontdrawtheroof", "don't draw the roof"),
    ("fillintheroof", "fill in the roof"),
    ("dontprovidetheroof", "don't provide the roof"),
    ("roofoptional", "roof optional"),
    ("roofmatter", "roof matter"),
    ("dachweglass", "Dach weglass"),
    ("dachauslass", "Dach auslass"),
    ("dachignorier", "Dach ignorier"),
    ("dachflächeaufnehm", "Dachfläche aufnehm"),
    ("dachflaecheaufnehm", "Dachflaeche aufnehm"),
    ("dachnichtaufnehm", "Dach nicht aufnehm"),
    ("dacheinzeich", "Dach einzeich"),
    ("dachnichtangeb", "Dach nicht angeb"),
    ("dachnichtausfüll", "Dach nicht ausfüll"),
    ("dachnichtausfuell", "Dach nicht ausfuell"),
    ("dachflächenichtausfüll", "Dachfläche nicht ausfüll"),
    ("dachflaechenichtausfuell", "Dachflaeche nicht ausfuell"),
    ("dachüberspring", "Dach überspring"),
    ("dachueberspring", "Dach ueberspring"),
    ("ohnedach", "ohne Dach"),
    ("ohnedasdach", "ohne das Dach"),
    ("keinedach", "keine Dach"),
    ("keindach", "kein Dach"),
    ("dachfehlt", "Dach fehlt"),
    ("dachflächefehlt", "Dachfläche fehlt"),
    ("dachflaechefehlt", "Dachflaeche fehlt"),
)
# Roof components that are not the step: "ohne Dachmontage" and "ohne
# Dachdurchdringung" are planning constraints, "keine Dachneigung" a property of
# the building. An absence marker does not fire when one of these is named.
_ROOF_COMPONENTS = (
    ("dachmontage", "Dachmontage"),
    ("dachdurchdring", "Dachdurchdring"),
    ("dachneigung", "Dachneigung"),
    ("dachfenster", "Dachfenster"),
    ("dachrinne", "Dachrinne"),
    ("dachhaube", "Dachhaube"),
    ("dachdämm", "Dachdämm"),
    ("dachdaemm", "Dachdaemm"),
    ("dachbefestig", "Dachbefestig"),
    ("dachhaken", "Dachhaken"),
    ("dachziegel", "Dachziegel"),
    ("dachaufbau", "Dachaufbau"),
    ("dachanlage", "Dachanlage"),
    ("dachabstand", "Dachabstand"),
)


def _roof_step(
    message: str,
    matches: Sequence[Match],
    intent: str | None,
    lang: str,
    reasons: list[str],
) -> Route | None:
    """The Roof detail step's role and the cost of skipping it (#497).

    Matched on `lexicon.normalize`. The step's own name answers even when Jev
    reads the question as sizing: the acceptance questions name the step. A
    skipping phrase is weaker, and a route that already has evidence keeps it:
    a named product word, a stated or asked kWp/kWh size or module count, or a
    confident company reading wins over the sentence. A named roof component
    ("ohne Dachmontage", "keine Dachneigung") is not the step, so the absence
    words do not fire on it. The sentence is signed in `template.ROOF`;
    size-hint supplies the configurator URL with no fields. No model runs.
    """
    compact = normalize(message)
    if any(match.kind in ("brand", "series", "model") for match in matches):
        return None
    marker = next((item for item, _ in _ROOF_STEP_NAMES if item in compact), None)
    if marker is None:
        if any(item in compact for item, _ in _ROOF_COMPONENTS):
            return None
        if intent == "company_logistics_service":
            return None
        if _SIZE_WORD.search(message):
            return None
        marker = next((item for item, _ in _ROOF_STEP_SKIPS if item in compact), None)
        if marker is None:
            return None
    # Lazy: template imports Route from this module.
    from linker_genie.template import ROOF

    language = "de" if lang == "de" else "en"
    return Route(
        "roof",
        (Call("linker/size-hint", {}),),
        action="open_configurator",
        no_cards=True,
        no_handoff=True,
        answer=ROOF[language],
        reasons=(*reasons, f"roof step: {marker}"),
    )


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
    *,
    planning_context: dict[str, Any] | None = None,
) -> Route:
    """The route with the page's content added when the message is about the page.

    Jev's `about_this_page` decides (#234). A signed-in customer's account page is
    their inquiries (inquiry-status); a solution draft is its products and the
    pairings among them; a page that carries a saved solution (#496) is that
    solution (read-solution); any other page is read (read-page). A request for a
    person, a company question, an inquiry status, a clarifying question, a
    scripted sentence or the Roof detail step's sentence reads nothing, and a
    delivery question about a page goes to the team whatever Jev says
    (`_LOGISTICS`).

    A solution page also reads the solution when the message names it in
    `_SOLUTION_WORDS`: the configurator is `other`, and the entry question of the
    design report's "Ask Genie" is exactly such a question.

    The calls fit the turn's budget in a fixed priority: the route's own calls (the
    subject's get-product among them) first, then the page, then the draft's pairs; a
    documents route leaves one call to the model (`DOCUMENTS_SPARE`). What does not
    fit is dropped, named in the turn log and, for a pair, in the hint.
    """
    if (
        route.name == "scripted"
        and "scripted: weather" in route.reasons
        and planning_tool.saved_result_question(planning_context, page, message)
    ):
        # A verified saved result's weather is historical calculation input.
        # Keep live-weather requests and missing/foreign context on their
        # existing fixed route; the planning tool still owns the actual facts.
        route = Route(
            "model",
            no_cards=True,
            no_handoff=True,
            reasons=(*route.reasons, "matching native saved-result context"),
        )
        about_page = True
    about_page = (
        about_page
        or (
            page.planning_project_id is not None
            and (route.name == "sizing" or _SOLUTION_WORDS.search(message) is not None)
        )
        or (
            page.solution_id is not None and _SOLUTION_WORDS.search(message) is not None
        )
    )
    if not about_page or route.name in (
        "person",
        "service",
        "inquiry",
        "clarify",
        "scripted",
        "roof",
    ):
        return route
    if _LOGISTICS.search(message) and not route.stock:
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
    elif page.planning_project_id:
        added.append(Call(planning_tool.NAME, {}))
        hint = planning_tool.RULE
        if route.name == "sizing":
            # Existing projects are read/explained here, not sent to a blank configurator.
            route = Route("planning_project", no_cards=True, no_handoff=True)
    elif page.solution_id:
        # The solution the design report's "Ask Genie" saved and opened with
        # (#496): the ability checks the customer's ownership of the post.
        added.append(Call(solution_tool.NAME, {"solution_id": page.solution_id}))
        hint = SOLUTION_HINT
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
    if any(c.ability == solution_tool.NAME for c in dropped):
        hint += (
            " The saved solution was not read in this turn: say that you could not "
            "read it just now; never guess its figures."
        )
    # A dropped search whose text is the model code was not searched. A family
    # suffix (ETA-G20) is not the code, so dropping only that search leaves the
    # code searched. get-product for one of the model's products also counts.
    # Rebuild the model paragraph so a code the page budget dropped is not
    # still described as searched earlier in the same hint.
    named = _notes_after_calls(route.named_models, calls)
    base = _hint_with_models(route.hint, route.named_models, named)
    return Route(
        route.name,
        calls,
        show_products=route.show_products,
        action=route.action,
        no_cards=route.no_cards,
        no_handoff=route.no_handoff,
        stock=route.stock,
        stock_beside=route.stock_beside,
        delivery=route.delivery,
        hint=(base + hint).strip(),
        reasons=(*route.reasons, f"about this page: {page.type}"),
        dropped=dropped,
        named_models=named,
        answer=route.answer,
        shape=route.shape,
    )


def _answer_shape(message: str, *, named: bool, bare: bool) -> AnswerShape | None:
    """The next-step shape of a model turn, or None when another route owns it.

    `plan` calls this after talk_to_person, company and inquiry, so a shape
    never replaces those routes (#394). `lexicon.normalize` drops spaces and
    punctuation, so the phrases are matched on that compact form. Aftermath
    questions match even when a product is named. Partner prices and greetings
    do not: a product word, including a bare category word, stays a product
    search. Only `_TALK` is a greeting or identity question: Jev also reads a
    thanks or a closing as small talk, and the signed greeting must not replace
    that closing (copy-review 2026-10-20 scopes TALK to greeting/identity; b45
    is a human-review row). A closing keeps the model's prose and gets the
    plain ask.
    """
    compact = normalize(message)
    aftermath = (
        "anfrage" in compact and ("nachdemich" in compact or "waspassiert" in compact)
    ) or (
        "inquiry" in compact
        and ("whathappensafter" in compact or "afterisend" in compact)
    )
    if aftermath:
        return "promise"
    if named or bare:
        return None
    if "partner" in compact and ("netprice" in compact or "nettopreis" in compact):
        return "partner"
    if compact in _TALK:
        return "talk"
    return None


def _hint_with_models(
    hint: str, before: tuple[NamedModel, ...], after: tuple[NamedModel, ...]
) -> str:
    """Swap the named-model paragraph after the page budget drops a call."""
    # An extreme hint already requires the winner card. Rebuilding the model
    # paragraph must keep that rule, or a dropped call puts "show each found
    # product" back beside it.
    winner_only = "extreme.applied" in hint
    old = _model_hint(before, winner_only=winner_only)
    new = _model_hint(after, winner_only=winner_only)
    if old and old in hint:
        return hint.replace(old, new, 1)
    if new.strip() == old.strip():
        return hint
    return (hint + new).strip()


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
