"""Five anchoring checks on a structured turn (docs/specs/13-genie.md).

These run after Pydantic accepts the shape and before hydration is shown.
They do not rewrite the model's text. A failure is a reason to retry once,
then fall back to the deterministic template.

The five checks, matching the ticket and old-repo-006 §2:

1. Every `{fact:ID}` and every `refs` id is in this turn's tool results, and
   a fact placeholder can be rendered (has a value).
2. Card / compare product IDs ⊆ this turn's tool product IDs; cards ⊆ text
   refs when a text block names products; recommended ⊆ search-products
   qualified when that tool ran.
3. Action names are on the allow-list (enforced by the schema) and arguments
   only use IDs from this turn's tools.
4. Out-of-scope company/service/logistics answers are only a handoff block
   (no product cards or actions beside it). The model chooses handoff via
   the schema; this check catches a mixed turn.
5. Bare numbers must not appear in model text (they belong in `{fact:ID}`).
   Digit runs inside a placeholder do not count. Neither does a series
   designator copied from a title this turn's tools returned ("OCEAN 2" in
   "EcoFlow OCEAN 2 HD-P1-3K-S2 (3 kW …)", #395). The measurement in the
   parenthesis, and any other digit, still counts.

Ask's wording "数字出现在被引块" is the knowledge-index citation rule
(docs/specs/10-knowledge-index.md): a number the answer states from a
document must occur in a cited chunk. A document's numbers reach the answer
only as figures of a retrieved chunk (`{fact:CHUNK_ID.nK}`, `figures.tag`),
and each figure's value is checked against the chunk texts of this turn.
Product facts (`pID.FIELD`) come from the product data, not from documents,
and are not held to the chunk texts. Check 5 forbids bare digits in the model
text either way.

Beside the five, the checks of the understanding layer (#233):

6. A document is a document block whose `ref` names a document of this turn's
   tools; no URL stands in the text, neither written nor through a placeholder.
7. The domain words of AGENTS.md §3 are kept: no article, catalogue, cart or
   basket (Artikel, Katalog, Warenkorb) in the model's text.
8. The route's requirements (route.py): a product word's search shows its cards; a
   sizing turn carries the configurator action and no cards; a product, document,
   pairing, comparison or sizing turn is never the team handoff.

And the price rule (#242):

9. No text writes a price, not even through a price placeholder; the product card
   carries it (prices.fill).
10. No text states an amount of money from a file the customer attached (#236): a
    price list or delivery terms are the customer's paper, never our price or
    delivery cost (the same rule `page.RULE` gives a page).
11. No text claims an inquiry, request or quote was sent (#250, A8): only the
    customer's Send button on the confirmation card sends.
12. A model is not described as absent unless that model's own search succeeded
    and returned none of its products (#364). A failed search is an outage, not
    an absence. The exemption is one sentence that names the brand the customer
    wrote and the catalog brand, with the product shown (#363, #367); the code
    may sit in another sentence. A model nothing looked up is never described as
    absent. A later search or get-product updates that note. Each searched model
    whose products qualified is shown as a card when the route requires cards.
    An applied extreme (#368) already requires that one card, so this card rule
    does not also require the others.

Registered reading of guarantee 2: "推荐 ⊆ search-products 的 qualified"
means qualified by this turn's tool results. That is search-products'
`qualified` list, plus the batteries its own `pairings` released (verdict
`released` / `released_with_accessory`) — the tool cleared those pairs, the
same rank as qualification. A product-page or compare turn whose cards come
from get-product / compare-products has no qualified set — those cards are
the subject of the answer, not recommendations, and they stay gated by
"product IDs ⊆ this turn's tool results". Card IDs are always required to
be cited in the text refs; that half of the guarantee is unconditional.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from linker_genie.facts import Fact, TurnFacts
from linker_genie.figures import AMOUNT, is_code
from linker_genie.hydrate import leftover_placeholders
from linker_genie.route import NamedModel, Route, absence_allowed, lookup_models
from linker_genie.schema import (
    ActionBlock,
    AskBlock,
    CardsBlock,
    CompareBlock,
    DocumentBlock,
    HandoffBlock,
    TextBlock,
    TurnOutput,
)
from linker_genie.template import NOT_IN_RANGE_DE, NOT_IN_RANGE_EN

BARE_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
PLACEHOLDER = re.compile(r"\{fact:[^}]+\}")
# A token of letters+digits (GW10K, H2, ETA-G20) is a model code, not a
# number; a pure numeric token (48, 5.0, 700) is one.
_TOKEN = re.compile(r"[A-Za-z0-9]+(?:[.,][0-9]+)?")
_NUMERIC_TOKEN = re.compile(r"\d+(?:[.,]\d+)?")
_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
# AGENTS.md §3: products and product categories — never article, catalogue, cart or
# basket; the German counterparts are Artikel, Katalog and Warenkorb. The prompts
# carry the same list (prompts/*/system.md).
BANNED_WORDS = re.compile(
    r"\b(?:articles?|catalogues?|catalogs?|carts?|baskets?|"
    r"artikel[ns]?|katalog(?:e|en|s)?|warenk(?:o|ö)rb(?:e|en|s)?)\b",
    re.IGNORECASE,
)

# A sentence that claims an inquiry went out (#250, acceptance A8). Only the
# customer's Send button sends (inquiry.py); a model sentence that says otherwise
# must never ship. The patterns name the inquiry (or quote/proforma) itself, so
# "I sent you the datasheet" and "the document was sent" stay ordinary answers.
_SENT_CLAIM = re.compile(
    r"(?:\b(?:i|we)(?: have|'ve| ve)?(?: just| already)? "
    r"(?:sent|submitted|placed|filed|created) (?:\w+ )?"
    r"(?:inquiry|enquiry|request|quote|proforma|rfq)\b"
    r"|\b(?:your|the|my|our|this) (?:inquiry|enquiry|request|quote|proforma|rfq) "
    r"(?:has|have|was|were) (?:now |just |already )?(?:been )?"
    r"(?:sent|submitted|placed|filed)\b"
    r"|\b(?:ich|wir) habe(?:n)? (?:\w+ )?(?:anfrage|angebot|proformarechnung)"
    r" (?:\w+ )?(?:gesendet|abgeschickt|gestellt|erstellt|übermittelt|uebermittelt)\b"
    r"|\b(?:die|ihre|meine|unsere) (?:anfrage|angebot|proformarechnung)"
    r" (?:wurde|ist) (?:\w+ )?(?:gesendet|abgeschickt|gestellt|erstellt|"
    r"übermittelt|uebermittelt)(?: worden)?\b)",
    re.IGNORECASE,
)


# A model code written whole: upper-case letters and digits joined by hyphens or
# slashes, with at least one letter ("CB2-100.3-HV5", "HS3-5K-T2-W/G-PX"). Its
# numeric segments are part of the name, not numbers: "CB2-100.3-HV5" was refused
# as the number "100.3" again and again (trial question 10, 2026-10-17), although
# the prompt asks for model names as plain codes. "3-phase" (lower case) and
# "10-20" (no letter) are not codes and stay caught.
_MODEL_CODE = re.compile(
    r"(?<![\w.])(?=[A-Z0-9.,/-]*[A-Z])[A-Z0-9]+(?:[.,][0-9]+)?"
    r"(?:[-/][A-Z0-9]+(?:[.,][0-9]+)?)+(?![\w])"
)
# A series designator written with a space, in the title head before the
# parenthesis: "OCEAN 2" of "EcoFlow OCEAN 2 HD-P1-3K-S2 (3 kW …)" (#395).
# One letter-word, then 1 or 2 digits. The feed's series slugs
# (services/engine/tests/fixtures/feed.json, 106 products) put 1 digit there
# (ocean-2, esa-3, esa-5, hv-5) or 2 (et-80, sts-30). sts-125k glues 125 to
# the unit, so a third digit is not one of those marks and "100" stays a
# number. The lookahead rejects a decimal ("2.0"). The parenthesis is where
# this catalogue writes the power ("10 kW", "3 kW").
_SERIES_DESIGNATOR = re.compile(r"\b[A-Za-z][A-Za-z]*[ \u00a0]+\d{1,2}\b(?![.,]\d)")
_NAME_HEAD = re.compile(r"[(\uFF08]")


def catalogue_name_phrases(tool_calls: list[dict[str, Any]]) -> tuple[str, ...]:
    """Series designators in the titles this turn's tools actually returned.

    The name head is the title before the first parenthesis. "OCEAN 2" from
    "EcoFlow OCEAN 2 HD-P1-3K-S2 (3 kW single-phase power module)" is a name,
    the same way "CB2-100.3-HV5" is. "10 kW" inside the parenthesis is not.
    Longest phrase first, so "AB 12" is removed before "AB 1".
    """
    found: set[str] = set()
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        for title in _catalogue_titles(call.get("result")):
            head = _NAME_HEAD.split(title, maxsplit=1)[0]
            for match in _SERIES_DESIGNATOR.finditer(head):
                found.add(re.sub(r"[ \u00a0]+", " ", match.group(0)))
    return tuple(sorted(found, key=lambda phrase: (-len(phrase), phrase.casefold())))


def _catalogue_titles(node: Any, *, in_documents: bool = False) -> list[str]:
    """Product, document and knowledge-hit titles. Not FAQ text, not a page body."""
    found: list[str] = []
    if isinstance(node, dict):
        title = node.get("title")
        if (
            isinstance(title, str)
            and title.strip()
            and (
                in_documents
                or "product_id" in node
                or "chunk_id" in node
                or "doc_url" in node
            )
        ):
            found.append(title)
        for key, value in node.items():
            found.extend(_catalogue_titles(value, in_documents=key == "documents"))
    elif isinstance(node, list):
        for item in node:
            found.extend(_catalogue_titles(item, in_documents=in_documents))
    return found


def _blank_name_phrases(text: str, phrases: Sequence[str]) -> str:
    """Remove each catalogue phrase, case-insensitively, on a word boundary.

    `phrases` is the tuple `catalogue_name_phrases` already returned: one
    space, longest first. This does not strip or sort again. "OCEAN 2" does
    not swallow "OCEAN 20" or "OCEAN 2.0": the digits must end the token. A
    bare "2" elsewhere in the sentence is left for the scan.
    """
    for phrase in phrases:
        parts = phrase.split(" ")
        if len(parts) < 2:
            continue
        pattern = (
            r"(?<!\w)"
            + r"[ \u00a0]+".join(re.escape(part) for part in parts)
            + r"(?!\w|[.,]\d)"
        )
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text


def bare_numbers(text: str, phrases: Sequence[str] = ()) -> list[str]:
    """Digit tokens that stand outside alphanumeric model codes.

    A model code keeps its numeric segments: "CB2-100.3-HV5" is a name, written
    plainly (`_MODEL_CODE`, #233; and a whole word that `figures.is_code` reads as
    a name, #257, which also covers codes written in lower case). A series
    designator from a title this turn's tools returned is a name too
    (`catalogue_name_phrases`, #395) and is blanked before the code strip.
    `phrases` is that tuple, already normalized and longest-first. "10 kW",
    "2.0" and a "2" that is not that phrase stay numbers. Callers that check a
    fact's own value pass no phrases. The quality worker's citation check
    reads the shipped answer with this same rule (`quality/citations.py`, #258),
    so the two never disagree on what a number is.
    """
    text = _blank_name_phrases(text, phrases)
    text = _MODEL_CODE.sub(" ", text)
    return [
        token
        for word in text.split()
        if not is_code(word)
        for token in _TOKEN.findall(word)
        if _NUMERIC_TOKEN.fullmatch(token)
    ]


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    failures: tuple[str, ...]

    @property
    def reason(self) -> str:
        return "; ".join(self.failures)


def check(
    output: TurnOutput, facts: TurnFacts, route: Route | None = None
) -> CheckResult:
    """Run the anchoring checks. Empty failures means the turn is grounded."""
    failures: list[str] = []
    failures.extend(_refs_and_placeholders(output, facts))
    failures.extend(_cards_and_qualified(output, facts))
    failures.extend(_actions(output, facts))
    failures.extend(_handoff_only_when_out_of_scope(output))
    failures.extend(_no_bare_numbers(output, facts))
    failures.extend(_login_required_is_a_login_request(output, facts))
    failures.extend(_documents(output, facts))
    failures.extend(_domain_words(output))
    failures.extend(_no_price_in_text(output))
    failures.extend(_no_amount_from_attachments(output, facts))
    failures.extend(_no_sent_claim(output))
    failures.extend(_extreme(output, facts))
    if route is not None:
        failures.extend(_route(output, facts, route))
        failures.extend(_named_models(output, facts, route))
    return CheckResult(ok=not failures, failures=tuple(failures))


def _model_texts(output: TurnOutput) -> list[str]:
    texts: list[str] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            texts.append(block.text)
        elif isinstance(block, HandoffBlock):
            texts.append(block.summary)
        elif isinstance(block, AskBlock):
            texts.extend(block.options)
    return texts


def _documents(output: TurnOutput, facts: TurnFacts) -> list[str]:
    failures: list[str] = []
    for block in output.blocks:
        if isinstance(block, DocumentBlock):
            if block.ref not in facts.documents:
                failures.append(f"document {block.ref!r} is not in this turn's tools")
            if block.label is not None or block.url is not None:
                failures.append("a document block carries only its ref")
    for text in _model_texts(output):
        if _URL.search(PLACEHOLDER.sub("", text)):
            failures.append("a URL stands in the text; use a document block")
        for fact_id in leftover_placeholders(text):
            fact = _fact_known(facts, fact_id)
            if fact_id in facts.documents or (fact and _URL.search(fact.value)):
                failures.append(
                    f"placeholder {fact_id!r} would print a URL; use a document block"
                )
    return failures


def _no_price_in_text(output: TurnOutput) -> list[str]:
    """Check 9. The price is the card's (#242): the service fills it there from the
    customer's own tool result, so no text names it, not even as a placeholder."""
    return [
        f"placeholder {fact_id!r} writes a price; the product card shows it, "
        "show the product as a card instead"
        for text in _model_texts(output)
        for fact_id in leftover_placeholders(text)
        if fact_id.endswith(".price")
    ]


def _no_amount_from_attachments(output: TurnOutput, facts: TurnFacts) -> list[str]:
    """Check 10. An amount of money read from the customer's file (a price list, an
    offer, delivery terms) is never stated: not as our price, not as a delivery
    cost. `figures.mark_amounts` keeps such a figure's currency in its value."""
    failures: list[str] = []
    for text in _model_texts(output):
        for fact_id in leftover_placeholders(text):
            fact = facts.facts.get(fact_id)
            if (
                fact is not None
                and fact.source == "read-attachment"
                and AMOUNT.search(fact.value)
            ):
                failures.append(
                    f"placeholder {fact_id!r} states an amount of money from the "
                    "customer's file; a price or a delivery cost never comes from an "
                    "attached file"
                )
    return failures


def _domain_words(output: TurnOutput) -> list[str]:
    failures: list[str] = []
    for text in _model_texts(output):
        found = BANNED_WORDS.findall(PLACEHOLDER.sub("", text))
        if found:
            failures.append(
                f"banned words {sorted({w.lower() for w in found})!r}: say product, "
                "product category or solution draft"
            )
    return failures


def _no_sent_claim(output: TurnOutput) -> list[str]:
    """Check 11. No sentence claims an inquiry went out (#250, A8).

    Only the customer's Send button on the confirmation card sends; the model has
    no ability that writes an inquiry. A model text that says one was sent would
    describe a state the site is not in, so it is refused like any other
    unsupported claim: the retry is told why, and the fallback carries no claim.
    """
    return [
        "the text claims the inquiry was sent; only the customer's Send button on "
        "the confirmation card sends it"
        for text in _model_texts(output)
        if _SENT_CLAIM.search(PLACEHOLDER.sub("", text))
    ]


# A cheapest claim next to a model code, when prices are hidden (#368).
# Explaining that no cheapest product can be named has the word and no code.
_CHEAPEST_WORD = re.compile(
    r"\b(?:cheapest|günstigst\w*|guenstigst\w*|billigst\w*|preiswertest\w*)\b",
    re.IGNORECASE,
)


def _extreme(output: TurnOutput, facts: TurnFacts) -> list[str]:
    """An applied extreme names that one product. A hidden price names none.

    The ability already filtered and sorted the catalogue. Grounding keeps the
    answer on that result: one card, the model code, and no price ranking when
    the account cannot see prices.
    """
    hidden = facts.facts.get("search.extreme_price_hidden")
    winner = facts.facts.get("search.extreme_product_id")
    if hidden is not None and winner is None:
        failures: list[str] = []
        for text in _model_texts(output):
            plain = PLACEHOLDER.sub("", text)
            if _CHEAPEST_WORD.search(plain) and _MODEL_CODE.search(plain):
                failures.append(
                    "prices are hidden for this account: do not name a cheapest product"
                )
        return failures
    if winner is None:
        return []
    product_id = int(winner.value)
    failures = []
    cards = [block for block in output.blocks if isinstance(block, CardsBlock)]
    if len(cards) != 1 or cards[0].product_ids != [product_id]:
        failures.append(
            f"an extreme of the product range is product {product_id} and only that card"
        )
    model = facts.facts.get("search.extreme_model")
    if model is not None and all(
        model.value not in text for text in _model_texts(output)
    ):
        failures.append(f"an extreme of the product range is named {model.value}")
    return failures


def _route(output: TurnOutput, facts: TurnFacts, route: Route) -> list[str]:
    failures: list[str] = []
    cards = [b for b in output.blocks if isinstance(b, CardsBlock)]
    if route.show_products and facts.qualified_ids:
        shown = {pid for block in cards for pid in block.product_ids}
        if not shown & facts.qualified_ids:
            failures.append(
                "the customer named products: show the search result as cards"
            )
    if route.no_cards and cards:
        failures.append(f"a {route.name} turn shows no product cards")
    if route.action and "size.configurator_url" in facts.facts:
        if not any(
            isinstance(b, ActionBlock) and b.name == route.action for b in output.blocks
        ):
            failures.append(f"a {route.name} turn carries the {route.action} action")
    if route.no_handoff and any(isinstance(b, HandoffBlock) for b in output.blocks):
        failures.append(f"a {route.name} turn is not a question for the team")
    if route.name == "service" and any(
        isinstance(b, HandoffBlock) for b in output.blocks
    ):
        if any(not isinstance(b, HandoffBlock) for b in output.blocks):
            # The mailbox sentence once, as the handoff block (trial question 18
            # printed it twice: a text block and the handoff block).
            failures.append("a handoff turn is the handoff block alone")
    return failures


# A clause that says a model is missing from the catalog. The range phrases are
# the fallback's own sentences (template.NOT_IN_RANGE_*): imported, not copied,
# so a rewording cannot leave this check matching text the customer no longer
# sees. The other phrases are ones campaign answers used and the prompts invite
# (#364 "no entry" / "product data"; the German prompt's "keinen Eintrag";
# #367 "kein Produkt", "nicht in unserem Sortiment", "nicht geführt",
# "finde ich … kein Produkt"). "our documents do not state" is a document
# answer and is not one of them. "finde ich … kein Produkt" is bounded by the
# clause split below. A character window would be an unsourced threshold
# (AGENTS.md §4), so the clause is the bound.
_ABSENCE = re.compile(
    "|".join(
        (
            r"no entry",
            re.escape(NOT_IN_RANGE_EN),
            r"not in our product data",
            r"we don'?t (?:carry|stock)",
            r"we do not (?:carry|stock)",
            r"not available",
            r"kein Produkt\b",
            r"keine Produkte\b",
            re.escape(NOT_IN_RANGE_DE),
            r"keinen Eintrag",
            r"nicht in den Produktdaten",
            r"gibt es bei uns nicht",
            r"führen wir nicht",
            r"nicht verfügbar",
            r"nicht in unserem Sortiment",
            r"nicht geführt",
            r"finde ich\b.*?kein Produkt\b",
        )
    ),
    re.IGNORECASE,
)
_CLAUSE = re.compile(r"[^\n.!?]+")
# A clause that points at a model without writing its code ("It is not…",
# "Es ist nicht…", "These two model codes return no entry"). This runs only
# inside an absence clause, so "es" here is the model. Bare "Sie" is the
# customer and is not a reference.
_REFERS = re.compile(
    r"\b(?:it|they|these|those|both|model codes?|this model|these models|"
    r"es|dieses modell|diese modelle|diese beiden|die beiden)\b",
    re.IGNORECASE,
)


def _named_models(output: TurnOutput, facts: TurnFacts, route: Route) -> list[str]:
    """Each named model is reported from its own search (#363, #364, #367).

    The check is structural, like the sent-claim check: it does not rewrite the
    text. Absence is a clause, including one that points at a code named
    elsewhere ("these two model codes", "it is not"). A conflict may use an
    absence clause only when that same sentence names both brands and the
    product is shown. An unsearched code is never absent. A failed search is
    an outage: absence is refused, and the note is not "not searched".
    When an extreme was applied, that one card is already required: the
    per-model card rule would demand the other cards as well, so it yields.
    """
    if not route.named_models:
        return []
    looked = lookup_models(route.named_models, facts.tool_calls, facts.qualified_ids)
    full = "\n".join(_model_texts(output))
    folded = full.casefold()
    clauses = [clause.strip() for clause in _CLAUSE.findall(full) if clause.strip()]
    cards = [block for block in output.blocks if isinstance(block, CardsBlock)]
    shown = {pid for block in cards for pid in block.product_ids}
    codes = [item.note.code for item in looked]
    # The applied winner is the only card. Absence claims are still refused.
    # A code searched beside that winner, or beside a hidden price, is named
    # in the text (#384). Known models beside an applied winner stay optional
    # here: the card rule already yielded, and requiring them would refuse the
    # one-card answer the extreme check demands.
    applied = facts.facts.get("search.extreme_product_id") is not None
    hidden = facts.facts.get("search.extreme_price_hidden") is not None
    failures: list[str] = []
    for item in looked:
        note = item.note
        about = _absence_about(note.code, clauses, codes, folded)
        if item.outcome == "unsearched":
            if note.code.casefold() not in folded:
                failures.append(f"say that {note.code} was not searched")
            if about:
                failures.append(
                    f"say that {note.code} was not searched, not that it is absent"
                )
            continue
        if (
            note.searched
            and note.code.casefold() not in folded
            and (hidden or (applied and note.unknown))
        ):
            failures.append(f"name {note.code} as well as the extreme result")
        if item.outcome == "failed" and about:
            failures.append(
                f"do not say {note.code} has no entry; that search did not succeed"
            )
            continue
        if (
            note.is_conflict
            and item.outcome == "products"
            and not _conflict_pointed(note, clauses, shown)
        ):
            failures.append(
                f"name {note.written_brand} and {note.catalog_brand} for "
                f"{note.code} in the same sentence, and show the product"
            )
        exempt = note.is_conflict and _conflict_exempt(note, about, shown, facts)
        if about and not (absence_allowed(item) or exempt):
            failures.append(
                f"do not say {note.code} has no entry; report that model's own "
                "search result"
            )
        if (
            not applied
            and route.show_products
            and note.searched_known
            and note.product_ids
        ):
            wanted = {pid for pid in note.product_ids if pid in facts.qualified_ids}
            if wanted and not wanted & shown:
                failures.append(f"show {note.code} as a card")
    return failures


def _absence_about(
    code: str, clauses: list[str], codes: list[str], full: str
) -> list[str]:
    """Absence clauses that assert `code` is missing.

    A clause that contains the code does. A clause that contains a different
    named code does not. A clause that names no code, but refers to a model
    ("it", "these model codes"), does when `code` appears somewhere in the
    answer — the campaign sentence named the codes in a different sentence
    from "no entry".
    """
    folded_code = code.casefold()
    others = [item.casefold() for item in codes if item.casefold() != folded_code]
    named = folded_code in full
    found: list[str] = []
    for clause in clauses:
        if not _ABSENCE.search(clause):
            continue
        folded = clause.casefold()
        if folded_code in folded:
            found.append(clause)
            continue
        if any(other in folded for other in others):
            continue
        if named and _REFERS.search(clause):
            found.append(clause)
    return found


def _conflict_pointed(note: NamedModel, clauses: list[str], shown: set[int]) -> bool:
    """Both brands in one sentence, and the product on a card.

    The code may sit in that sentence or in another. The route hint and the
    German prompt ask for the two brands together and the product shown.
    """
    written = note.written_brand.casefold()
    catalog = note.catalog_brand.casefold()
    together = any(
        written in clause.casefold() and catalog in clause.casefold()
        for clause in clauses
    )
    return together and bool(set(note.product_ids) & shown)


def _conflict_exempt(
    note: NamedModel, about: list[str], shown: set[int], facts: TurnFacts
) -> bool:
    """Absence is allowed only inside the sentence that names both brands.

    The product has to be on a card. A later sentence that only says the
    catalog brand ("GoodWe may help.") does not exempt the absence.
    """
    wanted = {pid for pid in note.product_ids if pid in facts.qualified_ids}
    if not wanted & shown:
        return False
    written = note.written_brand.casefold()
    catalog = note.catalog_brand.casefold()
    return all(
        written in clause.casefold() and catalog in clause.casefold()
        for clause in about
    )


def _refs_and_placeholders(output: TurnOutput, facts: TurnFacts) -> list[str]:
    known = facts.ids()
    failures: list[str] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            for fact_id in leftover_placeholders(block.text):
                if _fact_known(facts, fact_id) is None:
                    failures.append(
                        f"placeholder {fact_id!r} is not in this turn's tools"
                    )
            for ref in block.refs:
                if ref not in known:
                    failures.append(f"ref {ref!r} is not in this turn's tools")
        elif isinstance(block, HandoffBlock):
            # The handoff summary hydrates too (the team mailbox sentence is a
            # fact of the handoff-team tool), so its placeholder is checked.
            for fact_id in leftover_placeholders(block.summary):
                if _fact_known(facts, fact_id) is None:
                    failures.append(
                        f"placeholder {fact_id!r} is not in this turn's tools"
                    )
    return failures


def _cards_and_qualified(output: TurnOutput, facts: TurnFacts) -> list[str]:
    failures: list[str] = []
    text_product_refs: set[int] = set()
    for block in output.blocks:
        if isinstance(block, TextBlock):
            for ref in block.refs:
                if ref.isdigit():
                    text_product_refs.add(int(ref))
                elif ref.startswith("p") and ref[1:].split(".", 1)[0].isdigit():
                    text_product_refs.add(int(ref[1:].split(".", 1)[0]))
    for block in output.blocks:
        if isinstance(block, CardsBlock | CompareBlock):
            for product_id in block.product_ids:
                if product_id not in facts.product_ids:
                    failures.append(
                        f"product {product_id} is not in this turn's tool results"
                    )
                if facts.qualified_ids and product_id not in facts.qualified_ids:
                    failures.append(
                        f"product {product_id} is not in search-products qualified"
                    )
            if isinstance(block, CardsBlock):
                extra = set(block.product_ids) - text_product_refs
                for product_id in extra:
                    failures.append(f"card {product_id} is not cited in the text refs")
    return failures


def _actions(output: TurnOutput, facts: TurnFacts) -> list[str]:
    failures: list[str] = []
    fact_values = {fact.value for fact in facts.facts.values()}
    for block in output.blocks:
        if not isinstance(block, ActionBlock):
            continue
        args = block.args
        product_id = args.get("product_id")
        if product_id is not None and product_id not in facts.product_ids:
            failures.append(f"action {block.name} product_id is not from this turn")
        product_ids = args.get("product_ids")
        if isinstance(product_ids, list):
            for item in product_ids:
                if item not in facts.product_ids:
                    failures.append(f"action {block.name} product_ids contains {item}")
        # An action's URL is only allowed when a tool of this turn returned
        # it (size-hint's configurator_url). A URL the model invented — or a
        # view_inquiry URL, which no tool returns — is refused here; the
        # shell links such actions to the account page itself.
        url = args.get("url")
        if block.name == "open_configurator" and "size.configurator_url" in facts.facts:
            # The service writes this URL from size-hint (hydrate.py); what the
            # model put there is replaced, not checked.
            continue
        if isinstance(url, str) and url and url not in fact_values:
            failures.append(f"action {block.name} url is not from this turn's tools")
    return failures


def _login_required_is_a_login_request(
    output: TurnOutput, facts: TurnFacts
) -> list[str]:
    """R7 unsigned-out: a guest inquiry fact may only ship the login sentence.

    The fact is recorded by `facts._from_inquiry` when inquiry-status answers
    401. The model has answered that turn with the team mailbox sentence
    (PR #96, German "Wo steht meine Proforma?"); grounding refuses that shape
    so the cycle falls back to `template.login_required` instead of hydrating
    the mailbox sentence.
    """
    if "inquiry.login_required" not in facts.facts:
        return []
    from linker_genie.template import LOGIN_PLACEHOLDER, LOGIN_REQUIRED

    # Either exact sentence, or the placeholder. cycle.align_login rewrites
    # the block to the answer language before the customer sees it.
    accepted = {LOGIN_REQUIRED["en"], LOGIN_REQUIRED["de"], LOGIN_PLACEHOLDER}
    if (
        len(output.blocks) == 1
        and isinstance(output.blocks[0], TextBlock)
        and output.blocks[0].text in accepted
        and not output.blocks[0].refs
    ):
        return []
    return [
        "a guest inquiry turn must be the login request and nothing else "
        "(no team mailbox sentence, no inquiry data)"
    ]


def _handoff_only_when_out_of_scope(output: TurnOutput) -> list[str]:
    handoffs = [block for block in output.blocks if isinstance(block, HandoffBlock)]
    others = [block for block in output.blocks if not isinstance(block, HandoffBlock)]
    if handoffs and any(
        isinstance(block, CardsBlock | CompareBlock | ActionBlock) for block in others
    ):
        return ["a handoff turn may not also recommend products or actions"]
    return []


def _fact_known(facts: TurnFacts, fact_id: str) -> Fact | None:
    """The fact for an ID, tolerating a missing leading 'p' (model shorthand)."""
    fact = facts.facts.get(fact_id)
    if fact is None and not fact_id.startswith("p"):
        fact = facts.facts.get(f"p{fact_id}")
    return fact


def _no_bare_numbers(output: TurnOutput, facts: TurnFacts) -> list[str]:
    failures: list[str] = []
    # Phrases from this turn's titles only, as catalogue_name_phrases returns
    # them. A fact's own digits are checked against the cited chunk with no
    # phrases, so a title cannot vouch for them.
    phrases = catalogue_name_phrases(facts.tool_calls)
    cited_chunk_text = " ".join(
        fact.value
        for fact in facts.facts.values()
        if fact.source == "search-knowledge" and fact.id.endswith(".text")
    )
    for block in output.blocks:
        if isinstance(block, TextBlock):
            texts = [block.text]
        elif isinstance(block, HandoffBlock):
            texts = [block.summary]
        else:
            continue
        for text in texts:
            stripped = PLACEHOLDER.sub("", text)
            numbers = bare_numbers(stripped, phrases)
            if numbers:
                failures.append(f"model text contains numbers {numbers!r}")
                continue
            if cited_chunk_text:
                for fact_id in leftover_placeholders(text):
                    fact = facts.facts.get(fact_id)
                    if fact is None:
                        fact = _fact_known(facts, fact_id)
                    if fact is None or fact.source != "search-knowledge":
                        continue
                    if fact.id.endswith(".text") or fact.id in facts.chunk_ids:
                        continue
                    digits = bare_numbers(fact.value)
                    if digits and not any(
                        digit in cited_chunk_text for digit in digits
                    ):
                        failures.append(
                            f"number in {fact_id!r} does not appear in a cited chunk"
                        )
    return failures


def shipped(output: dict[str, Any], route: Route, offer: str | None) -> list[str]:
    """Checks of the answer as it ships, the contact card included (#243).

    The service adds the card after `check()` held the model's answer to the route
    (contact.decide); this holds the shipped whole: one card at most, last, and only
    the one the service decided; a company turn is its mailbox sentence and, when
    offered, the card. A failure is the service's own mistake: the card is dropped.
    """
    blocks = [b for b in output.get("blocks") or [] if isinstance(b, dict)]
    cards = [b for b in blocks if b.get("type") == "contact"]
    failures: list[str] = []
    if len(cards) > 1:
        failures.append("one contact card at most")
    if cards and blocks[-1].get("type") != "contact":
        failures.append("the contact card comes last")
    if offer is None and cards:
        failures.append("a contact card without an offer")
    if offer is not None and [c.get("reason") for c in cards] != [offer]:
        failures.append(f"the contact card is the {offer} offer")
    if route.name == "service" and any(
        b.get("type") not in ("handoff", "contact") for b in blocks
    ):
        failures.append("a company turn is the handoff block and the contact card")
    return failures
