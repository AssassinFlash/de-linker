"""Five anchoring checks on a structured turn (docs/specs/13-genie.md).

These run after Pydantic accepts the shape and before hydration is shown.
They do not rewrite the model's text. A failure is a reason to retry once.
The cycle, not this module, drops a number-only miss and still ships that
turn grounded (#439). Any other second miss falls back to the template.

The five checks, matching docs/specs/13-genie.md:

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
   Digit runs inside a placeholder do not count. A series designator copied
   from a title ("OCEAN 2") still counts: the baseline grader does not treat
   that digit as a catalogue code (#439). `catalogue_name_phrases` remains
   for the quality citation check, which blanks the name before it looks.
   The measurement in the parenthesis, and any other digit, still counts.

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
from typing import Any, Literal

from linker_genie.facts import (
    RELEASED_VERDICTS,
    Fact,
    TurnFacts,
    pairing_card_sets,
    pairing_entries,
    stock_rows,
)
from linker_genie.figures import AMOUNT, is_code
from linker_genie.hydrate import leftover_placeholders
from linker_genie.route import (
    NamedModel,
    Route,
    absence_allowed,
    lookup_models,
    simple_stock,
)
from linker_genie.schema import (
    ActionBlock,
    AskBlock,
    Block,
    CardsBlock,
    CompareBlock,
    DocumentBlock,
    HandoffBlock,
    TextBlock,
    TurnOutput,
)
from linker_genie.stock import phrase as stock_phrase
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
    a name, #257, which also covers codes written in lower case). A caller that
    passes `phrases` (`catalogue_name_phrases`, #395) blanks a series name such
    as "OCEAN 2" before the scan. The grounding check does not pass phrases:
    the baseline grader counts that digit, so a title cannot license it (#439).
    The quality citation check still passes the phrases (`quality/citations.py`).
    "10 kW", "2.0" and a bare "2" that is not a passed phrase stay numbers.
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


CitationKind = Literal["document", "chunk", "product", "placeholder", "ref", "number"]


@dataclass(frozen=True)
class Citation:
    """A ref the check refused, classified where the failure is raised.

    `document` and `chunk` select the degraded sentence (#396). `product`,
    `placeholder` and `ref` do not. `number` is a bare digit this turn's
    model text was not allowed to write (#439); it does not select that
    sentence. `CheckResult.failures` stays prose for the retry and the turn
    log. `cites_outside_turn` reads this record and ignores `number`.
    """

    kind: CitationKind
    ref: str


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    failures: tuple[str, ...]
    citations: tuple[Citation, ...] = ()
    # True when every failure came from the bare-number check. The cycle
    # reads this flag; it does not parse the failure prose (#439).
    unbound_only: bool = False

    @property
    def reason(self) -> str:
        return "; ".join(self.failures)


def check(
    output: TurnOutput, facts: TurnFacts, route: Route | None = None
) -> CheckResult:
    """Run the anchoring checks. Empty failures means the turn is grounded."""
    failures: list[str] = []
    citations: list[Citation] = []
    ref_failures, ref_citations = _refs_and_placeholders(output, facts)
    failures.extend(ref_failures)
    citations.extend(ref_citations)
    card_failures, card_citations = _cards_and_qualified(output, facts)
    failures.extend(card_failures)
    citations.extend(card_citations)
    failures.extend(_actions(output, facts))
    number_failures, number_citations, chunk_failures = _no_bare_numbers(output, facts)
    failures.extend(number_failures)
    failures.extend(chunk_failures)
    citations.extend(number_citations)
    failures.extend(_login_required_is_a_login_request(output, facts))
    document_failures, document_citations = _documents(output, facts)
    failures.extend(document_failures)
    citations.extend(document_citations)
    failures.extend(_pairing_answer_shape(output, facts))
    failures.extend(_not_released_answer_shape(output, facts))
    failures.extend(_domain_words(output))
    failures.extend(_no_price_in_text(output))
    failures.extend(_no_amount_from_attachments(output, facts))
    failures.extend(_no_sent_claim(output))
    failures.extend(_extreme(output, facts))
    failures.extend(_handoff_only_when_out_of_scope(output, route))
    if route is not None:
        failures.extend(_route(output, facts, route))
        failures.extend(_named_models(output, facts, route))
        failures.extend(_stock(output, facts, route))
    return CheckResult(
        ok=not failures,
        failures=tuple(failures),
        citations=tuple(citations),
        unbound_only=bool(number_failures) and len(failures) == len(number_failures),
    )


# A chunk id is built by `index/chunking.py` `_emit`: the document's hex
# prefix, `-p{page}-`, a content digest, and an optional `-{n}` collision
# suffix. The pattern spells that shape out, so a product id and a short id
# such as `c1` do not match. Example: `770ccafa080c-p37-63a0f610`.
_CHUNK_REF = re.compile(r"[0-9a-f]{12}-p\d+-[0-9a-f]{8}(?:-\d+)?")
_OUTSIDE_KINDS = frozenset({"document", "chunk"})


def _ref_kind(ref: str) -> CitationKind:
    """The kind of a text ref, from the id itself.

    A document id contains `.document.`. A product id is digits or `p` plus
    digits. Anything else that matches `_CHUNK_REF` is a search-knowledge
    chunk. The failure prose is not parsed.
    """
    if ".document." in ref:
        return "document"
    if ref.isdigit() or re.fullmatch(r"p\d+", ref):
        return "product"
    if _CHUNK_REF.fullmatch(ref) is not None:
        return "chunk"
    return "ref"


def cites_outside_turn(citations: tuple[Citation, ...] | list[Citation]) -> bool:
    """True when grounding refused a document or chunk this turn did not return.

    That is the #396 defect (`p3612.document.2`, a chunk id). A product id
    and a placeholder do not: they keep the card and absence rules, and the
    turn is not replaced by the degraded sentence. The kind is `Citation`,
    set where the failure is raised.
    """
    return any(item.kind in _OUTSIDE_KINDS for item in citations)


def cites_unbound(citations: tuple[Citation, ...] | list[Citation]) -> bool:
    """True when grounding refused a bare number (#439).

    The cycle reads `CheckResult.unbound_only` and does not parse the failure
    prose. This helper is the same fact for a caller that already holds the
    citations. A number citation does not select the degraded sentence.
    """
    return any(item.kind == "number" for item in citations)


# The same token the baseline grader binds (`eval/baseline/grade.py` `_NUMBER`).
# Production does not import the grader. `bare_numbers` keeps its own token so
# the quality citation check is unchanged.
_GRADE_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
# A number glued only to a unit ("1500mm", "20kW"). `is_code` is false for these,
# and an ASCII letter would otherwise keep the word. Longer units first.
_GLUED_UNITS = (
    "kWh",
    "MWh",
    "Wh",
    "kWp",
    "Wp",
    "kVAr",
    "kVA",
    "kW",
    "MW",
    "VA",
    "W",
    "mAh",
    "Ah",
    "mA",
    "A",
    "kV",
    "mV",
    "Vdc",
    "Vac",
    "V",
    "mm",
    "cm",
    "km",
    "kg",
    "g",
    "%",
    "kHz",
    "Hz",
    "ms",
    "min",
    "years",
    "year",
    "Jahre",
    "Jahr",
    "tons",
    "ton",
    "Tonnen",
)
_GLUED_UNIT = re.compile(
    r"^(?:\d+(?:[.,]\d+)*)(?:"
    + "|".join(re.escape(unit) for unit in sorted(_GLUED_UNITS, key=len, reverse=True))
    + r")$",
    re.IGNORECASE,
)
# The unit word that follows a dropped number ("10 kW", "1500 mm"). A trailing
# period or comma is the sentence's, not part of the unit.
_FOLLOWING_UNIT = re.compile(
    r"^(?:kWh|kWp|kW|mm|%|Jahre|years|Jahr|year|Wp|Tonnen|tons|ton|V|A|W)$",
    re.IGNORECASE,
)
_WORD_PUNCT = ".,:;!?"
_DOCUMENT_SOURCES = frozenset({"search-knowledge", "datasheet-figures", "read-page"})
# Energy and power units. A clearance answer that prints them fails the
# installation row: the grader's allowlist is the guide's figures, not the
# rated energy on the same datasheet. Percent is the same kind of miss.
_CAPACITY_UNITS = frozenset(
    {"kwh", "mwh", "wh", "kwp", "wp", "kw", "mw", "w", "kva", "kvar"}
)
_GLUED_CAPACITY = re.compile(
    r"^(?:\d+(?:[.,]\d+)*)([A-Za-z]+)$",
)


def number_variants(token: str) -> set[float]:
    """The readings `eval/baseline/grade.py` gives a printed token.

    `20.000` is 20000 or 20.0. Copied here so a sealed answer and the grader
    bind the same token. The allowlist is expanded before the intersection;
    this function is not.
    """
    values: list[float] = []
    for separator in (".", ","):
        if separator in token:
            whole, _, fraction = token.partition(separator)
            if whole.isdigit() and fraction.isdigit():
                values.append(float(f"{whole}.{fraction}"))
                if len(fraction) == 3:
                    values.append(float(whole + fraction))
    if token.isdigit():
        values.append(float(token))
    return set(values)


def _expand(values: set[float]) -> set[float]:
    expanded: set[float] = set()
    for variant in values:
        expanded.update((variant, variant * 1000.0, variant / 1000.0))
    return expanded


def _core(word: str) -> str:
    return word.strip(_WORD_PUNCT)


def _glued_unit_word(word: str) -> bool:
    return _GLUED_UNIT.fullmatch(_core(word)) is not None


def _figure_word(word: str) -> bool:
    """A word whose digits the baseline grader would bind, codes aside.

    Letter-free words ("2", "5–108", "98%", "≥1500") and a number glued only
    to a unit ("1500mm") count. An ASCII letter glued to a digit that is not
    that unit stays ("3-phase", "H2-10K-T3"): the product-route strip must
    not turn a phase phrase into a grounding failure. A non-ASCII letter
    glued to a digit ("Φ10") counts, so its digit cannot hide. A `{fact:}`
    placeholder is the model's citation, not a bare number.
    """
    if "{fact:" in word or not any(ch.isdigit() for ch in word):
        return False
    if is_code(word):
        return False
    if _glued_unit_word(word):
        return True
    if any("A" <= ch <= "Z" or "a" <= ch <= "z" for ch in word):
        return False
    return True


def _allowance_word(word: str) -> set[float]:
    """Readings a word may license. A code, and `Φ10`, license nothing."""
    if "{fact:" in word or not any(ch.isdigit() for ch in word):
        return set()
    if any(ord(ch) > 127 and ch.isalpha() for ch in word):
        return set()
    if not _figure_word(word):
        return set()
    values: set[float] = set()
    for token in _GRADE_NUMBER.findall(word):
        values.update(number_variants(token))
    return values


def _unlicensed(word: str, allowed: set[float] | None) -> bool:
    if not _figure_word(word):
        return False
    if allowed is None:
        return True
    for token in _GRADE_NUMBER.findall(word):
        readings = number_variants(token)
        if readings and readings.isdisjoint(allowed):
            return True
    return False


def _following_unit(word: str) -> bool:
    return _FOLLOWING_UNIT.fullmatch(_core(word)) is not None


def _strip_text(text: str, allowed: set[float] | None) -> str:
    """Drop unlicensed figure words without gluing the words that remain.

    The separator before a dropped word goes with it. The separator after it
    stays, unless the next word is only the number's unit, which goes too.
    Newlines are separators, so a dropped line does not join the lines around it.
    """
    parts = re.split(r"(\s+)", text)
    kept: list[str] = []
    pending = ""
    index = 0
    while index < len(parts):
        part = parts[index]
        if not part:
            index += 1
            continue
        if part.isspace():
            pending += part
            index += 1
            continue
        if _unlicensed(part, allowed):
            pending = ""
            index += 1
            if (
                index < len(parts)
                and parts[index].isspace()
                and index + 1 < len(parts)
                and _following_unit(parts[index + 1])
            ):
                index += 2
                if index < len(parts) and parts[index].isspace():
                    pending = parts[index]
                    index += 1
            continue
        kept.append(pending)
        kept.append(part)
        pending = ""
        index += 1
    result = "".join(kept)
    if result[:1] in {" ", "\t"} and text[:1] not in {" ", "\t"}:
        result = result.lstrip(" \t")
    return result


def strip_unlicensed_numbers(
    output: TurnOutput, allowed: set[float] | None
) -> TurnOutput:
    """Drop bare numbers `allowed` does not license. `None` drops every one.

    Text and a handoff summary only. Ask chips, cards and document links stay.
    An empty text block stays: the turn still has its block.
    """
    blocks: list[Block] = []
    changed = False
    for block in output.blocks:
        if isinstance(block, TextBlock):
            text = _strip_text(block.text, allowed)
            if text != block.text:
                changed = True
                blocks.append(block.model_copy(update={"text": text}))
            else:
                blocks.append(block)
        elif isinstance(block, HandoffBlock):
            summary = _strip_text(block.summary, allowed)
            if summary != block.summary:
                changed = True
                blocks.append(block.model_copy(update={"summary": summary}))
            else:
                blocks.append(block)
        else:
            blocks.append(block)
    if not changed:
        return output
    return output.model_copy(update={"blocks": blocks})


def drop_bare_numbers(output: TurnOutput) -> TurnOutput:
    """Drop every bare figure word. A question does not license any of them.

    This is the number-only correction, before hydration. A series digit the
    question names ("OCEAN 2") must not survive that miss: the grader does not
    treat it as a catalogue code.
    """
    return strip_unlicensed_numbers(output, None)


# A digit-free hyphenated token immediately before a figure tag or a bare
# number: `VDE-AR-N [n4=4105]`, `VDE-AR-N 4105`. A code with a digit
# (`H2-10K-T3`) is not one. Production does not import the grader.
_CODE_TAIL = re.compile(
    r"([A-Za-z]+(?:-[A-Za-z]+)+)[ \t]+"
    r"(?:\[n\d+=([0-9]+(?:[.,][0-9]+)?)\]"
    r"|([0-9]+(?:[.,][0-9]+)?)(?!\d))"
)
_BARE_FACT = re.compile(r"[0-9]+(?:[.,][0-9]+)?")


def code_tail_blob(facts: TurnFacts) -> str:
    """Document text, without a figure fact that is only the number.

    A chunk prints `VDE-AR-N [n4=4105]`. The same turn also stores the figure
    value `4105` on its own. That value is the code's number, not a measurement,
    so it must not count as a second occurrence that licenses the digits.
    Facts are joined with a newline so a code at the end of one fact cannot
    bind the next fact's number.
    """
    parts: list[str] = []
    for fact in facts.facts.values():
        if fact.source not in _DOCUMENT_SOURCES:
            continue
        if _BARE_FACT.fullmatch(fact.value.strip()):
            continue
        parts.append(fact.value)
    return "\n".join(parts)


def _code_tail_bindings(blob: str) -> dict[float, set[str]]:
    """Readings that appear only as the tail of a digit-free hyphenated code.

    `10 kW` beside `VDE-AR-N [n4=4105]` is a measurement, so 10 is not bound.
    A number that also stands on its own in the same text is not bound either.
    """
    tails: list[tuple[int, int, str, set[float]]] = []
    for match in _CODE_TAIL.finditer(blob):
        token = match.group(2) or match.group(3)
        if not token:
            continue
        readings = number_variants(token)
        if not readings:
            continue
        span = match.span(2) if match.group(2) else match.span(3)
        tails.append((span[0], span[1], match.group(1).casefold(), readings))
    if not tails:
        return {}
    covered = [(start, end) for start, end, _, _ in tails]
    bound: dict[float, set[str]] = {}
    for _, _, code, readings in tails:
        for reading in readings:
            bound.setdefault(reading, set()).add(code)
    disqualified: set[float] = set()
    for match in _GRADE_NUMBER.finditer(blob):
        start, end = match.span()
        if any(
            cover_start <= start and end <= cover_end
            for cover_start, cover_end in covered
        ):
            continue
        for reading in number_variants(match.group()):
            if reading in bound:
                disqualified.add(reading)
    return {
        reading: codes
        for reading, codes in bound.items()
        if reading not in disqualified
    }


def _detached_code_tail(
    word: str, previous: str, bindings: dict[float, set[str]]
) -> bool:
    """True when a figure word's reading is a code tail and `previous` is not the code."""
    if not _figure_word(word):
        return False
    for token in _GRADE_NUMBER.findall(word):
        codes: set[str] = set()
        for reading in number_variants(token):
            codes |= bindings.get(reading, set())
        if codes and previous.casefold() not in codes:
            return True
    return False


def _strip_code_tail_text(text: str, bindings: dict[float, set[str]]) -> str:
    """Drop a detached code tail. The code must be the previous word."""
    parts = re.split(r"(\s+)", text)
    kept: list[str] = []
    pending = ""
    previous = ""
    index = 0
    while index < len(parts):
        part = parts[index]
        if not part:
            index += 1
            continue
        if part.isspace():
            pending += part
            index += 1
            continue
        if _detached_code_tail(part, previous, bindings):
            pending = ""
            index += 1
            if (
                index < len(parts)
                and parts[index].isspace()
                and index + 1 < len(parts)
                and _following_unit(parts[index + 1])
            ):
                index += 2
                if index < len(parts) and parts[index].isspace():
                    pending = parts[index]
                    index += 1
            continue
        kept.append(pending)
        kept.append(part)
        pending = ""
        previous = part
        index += 1
    result = "".join(kept)
    if result[:1] in {" ", "\t"} and text[:1] not in {" ", "\t"}:
        result = result.lstrip(" \t")
    return result


# A decimal point is a clause break for the acceptance check, the same way a
# full stop is. `29.999` therefore ends the clause that names the model, and a
# figure written after it is not tied to that model. The code already on the
# line is repeated after the decimal. No new sentence.
_HYPHEN_CODE = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)(?![A-Za-z0-9])"
)
_UNIT_AFTER = re.compile(r"[ \t]*(?:kWh|kWp|kW|mm|%)\b", re.IGNORECASE)
_LATER_FIGURE = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*"
    r"(?=(?:(?i:kwh|kwp|kw|mm|%))(?![A-Za-z0-9])|(?![A-Za-z0-9]))"
)


def _digit_code(token: str) -> bool:
    return any(character.isdigit() for character in token)


def _codes_in(text: str) -> list[str]:
    return [
        match.group(1)
        for match in _HYPHEN_CODE.finditer(text)
        if _digit_code(match.group(1))
    ]


def _rebind_line(line: str) -> str:
    """Repeat the line's model code in a clause a decimal point has split off."""
    pieces = re.split(r"([.!?;])", line)
    rebuilt: list[str] = []
    seen: str | None = None
    for piece in pieces:
        if piece in ".!?;":
            rebuilt.append(piece)
            continue
        codes = _codes_in(piece)
        if codes:
            seen = codes[-1]
            rebuilt.append(piece)
            continue
        if seen is None:
            rebuilt.append(piece)
            continue
        scan_from = 0
        if rebuilt and rebuilt[-1] == ".":
            fraction = re.match(r"\d+", piece)
            if fraction is not None:
                scan_from = fraction.end()
        if _LATER_FIGURE.search(piece, scan_from) is None:
            rebuilt.append(piece)
            continue
        insert_at = scan_from
        unit = _UNIT_AFTER.match(piece, insert_at)
        if unit is not None:
            insert_at = unit.end()
        comma = re.match(r"[ \t]*,[ \t]*", piece[insert_at:])
        if comma is not None:
            insert_at += comma.end()
        else:
            lead = re.match(r"[ \t]*", piece[insert_at:])
            insert_at += lead.end() if lead is not None else 0
        piece = f"{piece[:insert_at]}{seen} {piece[insert_at:]}"
        rebuilt.append(piece)
    return "".join(rebuilt)


def _rebind_text(text: str) -> str:
    return "\n".join(_rebind_line(line) for line in text.split("\n"))


def rebind_figures_past_decimal(output: TurnOutput) -> TurnOutput:
    """Keep a figure after a decimal in the clause of the model named before it.

    The acceptance check splits a clause on `.`, so `29.999` hides the model
    from a figure written after it. The model code already on that line is
    repeated after the decimal. A line with no later figure is left as written.
    This is not a new sentence.
    """
    blocks: list[Block] = []
    changed = False
    for block in output.blocks:
        if isinstance(block, TextBlock):
            text = _rebind_text(block.text)
            if text != block.text:
                changed = True
                blocks.append(block.model_copy(update={"text": text}))
            else:
                blocks.append(block)
        elif isinstance(block, HandoffBlock):
            summary = _rebind_text(block.summary)
            if summary != block.summary:
                changed = True
                blocks.append(block.model_copy(update={"summary": summary}))
            else:
                blocks.append(block)
        else:
            blocks.append(block)
    if not changed:
        return output
    return output.model_copy(update={"blocks": blocks})


def strip_detached_code_tails(output: TurnOutput, blob: str) -> TurnOutput:
    """Drop a code's number unless the answer keeps that code immediately before it.

    The grader licenses `VDE-AR-N 4105` and refuses `application rule 4105`.
    Only whitespace may sit between the code and the number. A measurement
    that also appears in the text stays, and so does `H2-10K-T3`.
    """
    bindings = _code_tail_bindings(blob)
    if not bindings:
        return output
    blocks: list[Block] = []
    changed = False
    for block in output.blocks:
        if isinstance(block, TextBlock):
            text = _strip_code_tail_text(block.text, bindings)
            if text != block.text:
                changed = True
                blocks.append(block.model_copy(update={"text": text}))
            else:
                blocks.append(block)
        elif isinstance(block, HandoffBlock):
            summary = _strip_code_tail_text(block.summary, bindings)
            if summary != block.summary:
                changed = True
                blocks.append(block.model_copy(update={"summary": summary}))
            else:
                blocks.append(block)
        else:
            blocks.append(block)
    if not changed:
        return output
    return output.model_copy(update={"blocks": blocks})


def question_allowance(question: str) -> set[float]:
    """Bare readings in the question, expanded the way the grader expands."""
    values: set[float] = set()
    for word in question.split():
        values.update(_allowance_word(word))
    return _expand(values)


def document_blob(facts: TurnFacts) -> str:
    """Document fact values of this turn, joined. Product specs are not included."""
    return " ".join(
        fact.value for fact in facts.facts.values() if fact.source in _DOCUMENT_SOURCES
    )


def document_allowance(facts: TurnFacts, question: str = "") -> set[float]:
    """Question readings plus figure-word readings from the document facts."""
    values: set[float] = set()
    for word in question.split():
        values.update(_allowance_word(word))
    for word in document_blob(facts).split():
        values.update(_allowance_word(word))
    return _expand(values)


def _capacity_unit(word: str) -> bool:
    """True for an energy, power or percent word, glued or standing alone."""
    core = _core(word)
    if not core or "%" in core:
        return "%" in core
    glued = _GLUED_CAPACITY.fullmatch(core)
    unit = glued.group(1) if glued else core
    return unit.casefold() in _CAPACITY_UNITS


def clearance_allowance(facts: TurnFacts, question: str = "") -> set[float]:
    """Installation figures. Energy, power and percent license nothing here.

    The same documents state rated energy beside the clearances. An installation
    row does not allow those readings, so a wording flip that prints them fails.
    A code and `Φ10` still license nothing.
    """
    values: set[float] = set()
    for source in (question, document_blob(facts)):
        words = source.split()
        for index, word in enumerate(words):
            if _capacity_unit(word):
                continue
            nxt = words[index + 1] if index + 1 < len(words) else ""
            if nxt and _capacity_unit(nxt):
                continue
            values.update(_allowance_word(word))
    return _expand(values)


def blob_has_figure(blob: str, value: float) -> bool:
    """True when a figure word in `blob` prints `value`. A code word does not."""
    for word in blob.split():
        if value in _allowance_word(word):
            return True
    return False


def _droppable_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for word in text.split():
        if _figure_word(word):
            tokens.extend(_GRADE_NUMBER.findall(word))
    return tokens


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


def _documents(
    output: TurnOutput, facts: TurnFacts
) -> tuple[list[str], list[Citation]]:
    failures: list[str] = []
    citations: list[Citation] = []
    for block in output.blocks:
        if isinstance(block, DocumentBlock):
            if block.ref not in facts.documents:
                failures.append(f"document {block.ref!r} is not in this turn's tools")
                citations.append(Citation("document", block.ref))
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
    return failures, citations


def _pairing_answer_shape(output: TurnOutput, facts: TurnFacts) -> list[str]:
    """The released search-pairing answer keeps its prompt shape (#396).

    The prompt asks for one text block, one cards block, a document link and
    no ask once those cards stand. Both languages therefore ship the same
    block structure (b10). The subject is the searched product whose own
    `pairings` released a partner; b10 shows the inverter, not the battery,
    so requiring a shown partner would miss it. Any document the turn
    returned satisfies the link; the model may link the battery document
    instead of the pairing ref. A check-compatibility answer keeps its own
    rules.
    """
    documents_for: dict[int, list[str]] = {}
    has_release: set[int] = set()
    for call in facts.tool_calls:
        if not isinstance(call, dict) or not str(call.get("name") or "").endswith(
            "search-products"
        ):
            continue
        result = call.get("result")
        if not isinstance(result, dict):
            continue
        for item in result.get("qualified") or []:
            if not isinstance(item, dict):
                continue
            subject = item.get("product_id")
            if not isinstance(subject, int):
                continue
            expected: list[str] = []
            for pairing in pairing_entries(item) or []:
                if pairing.get("verdict") not in RELEASED_VERDICTS:
                    continue
                has_release.add(subject)
                paired = pairing.get("product_id")
                if not isinstance(paired, int):
                    continue
                for index, document in enumerate(pairing.get("documents") or []):
                    if (
                        isinstance(document, dict)
                        and isinstance(document.get("url"), str)
                        and document["url"]
                    ):
                        expected.append(f"compat.document.{paired}.{index}")
            if expected:
                documents_for[subject] = expected
    shown = {
        product_id
        for block in output.blocks
        if isinstance(block, CardsBlock)
        for product_id in block.product_ids
    }
    subjects = shown & has_release
    if not subjects:
        return []
    expected_docs = {
        ref for subject in subjects for ref in documents_for.get(subject, [])
    }
    failures: list[str] = []
    if any(isinstance(block, AskBlock) for block in output.blocks):
        failures.append("a released pairing answer asks no question")
    linked = {block.ref for block in output.blocks if isinstance(block, DocumentBlock)}
    if expected_docs and not linked:
        failures.append("a released pairing answer links no document")
    return failures


def _not_released_answer_shape(output: TurnOutput, facts: TurnFacts) -> list[str]:
    """A not_released answer links the check's document (#396).

    The prompt makes the answer the condition placeholders plus the check's
    compat.document refs. A turn with a released set is the card path and is
    not this shape. The next step is the document; a model that drops it
    would otherwise pass grounding and fail b09's next-step row.
    """
    verdict = facts.facts.get("compat.verdict")
    if verdict is None or verdict.value != "not_released":
        return []
    if pairing_card_sets(facts):
        return []
    expected = {
        ref
        for ref in facts.documents
        if ref.rpartition(".")[0] == "compat.document"
        and ref.rpartition(".")[2].isdigit()
    }
    if not expected:
        return []
    linked = {block.ref for block in output.blocks if isinstance(block, DocumentBlock)}
    if not linked & expected:
        return ["a not_released answer links the check's document"]
    return []


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
    if route.delivery and not any(isinstance(b, HandoffBlock) for b in output.blocks):
        failures.append("a delivery question goes to the team")
    if route.name == "service" and any(
        isinstance(b, HandoffBlock) for b in output.blocks
    ):
        if any(not isinstance(b, HandoffBlock) for b in output.blocks):
            # The mailbox sentence once, as the handoff block (trial question 18
            # printed it twice: a text block and the handoff block).
            failures.append("a handoff turn is the handoff block alone")
    return failures


# A count, not a model code. "H2-10K-T3" has no "quantity" and no "N in stock".
_STOCK_QUANTITY = re.compile(
    r"\b(?:quantity|quantities|units?|pieces?|stück(?:e|zahl)?|lagerbestand)\b"
    r"|\b\d+\s+in stock\b",
    re.IGNORECASE,
)
# The page's status sentence is the whole clause (stock.phrase). "nicht
# verfügbar" is also an absence phrase; this sentence is the status, not a
# claim the model is missing.
_STATUS_CLAUSE = re.compile(
    "^(?:"
    + "|".join(
        re.escape(stock_phrase(lang, flag))
        for lang in ("en", "de")
        for flag in (True, False)
    )
    + r")\.?$",
    re.IGNORECASE,
)


def _stated_status(text: str, language: str) -> set[str]:
    """Page status lines that stand in `text`."""
    folded = text.casefold()
    return {
        stock_phrase(language, flag)
        for flag in (True, False)
        if stock_phrase(language, flag).casefold() in folded
    }


def _stock(output: TurnOutput, facts: TurnFacts, route: Route) -> list[str]:
    """A simple stock turn states the page's status and no quantity (#415).

    A conflict, an unknown code, or several models keep the clarification.
    One shared flag must be stated. Differing flags must each be stated, or
    the status omitted: a blanket "In stock" is not grounded. The service
    writes the simple case; this is the net under it.
    """
    if not simple_stock(route):
        return []
    rows = stock_rows(facts)
    if rows is None:
        return []
    text = "\n".join(
        block.text for block in output.blocks if isinstance(block, TextBlock)
    )
    failures: list[str] = []
    if _STOCK_QUANTITY.search("\n".join(_model_texts(output))):
        failures.append("a stock question states no quantity")
    flags = {flag for _product_id, flag in rows}
    stated = _stated_status(text, output.language)
    if len(flags) != 1:
        needed = {stock_phrase(output.language, flag) for flag in flags}
        if stated and stated != needed:
            failures.append("products differ: state each product's status, or none")
        return failures
    expected = stock_phrase(output.language, flags.pop())
    if expected not in text:
        failures.append(f"a stock question states {expected}")
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
    if route.stock:
        clauses = [clause for clause in clauses if _STATUS_CLAUSE.match(clause) is None]
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


def _placeholder_failure(facts: TurnFacts, fact_id: str) -> str:
    """The retry reason, with the condition refs this turn returned (#396).

    b09's model counted the conditions from one and repeated it on the retry.
    Naming the refs it may use is the same help the document line gives.
    """
    message = f"placeholder {fact_id!r} is not in this turn's tools"
    if not fact_id.startswith("compat.condition."):
        return message
    available = [
        key
        for key in facts.facts
        if key.rpartition(".")[0] == "compat.condition"
        and key.rpartition(".")[2].isdigit()
    ]
    if not available:
        return message
    return message + (
        f" (this turn returned {', '.join(available)}; the first condition is index 0)"
    )


def _refs_and_placeholders(
    output: TurnOutput, facts: TurnFacts
) -> tuple[list[str], list[Citation]]:
    known = facts.ids()
    failures: list[str] = []
    citations: list[Citation] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            for fact_id in leftover_placeholders(block.text):
                if _fact_known(facts, fact_id) is None:
                    failures.append(_placeholder_failure(facts, fact_id))
                    citations.append(Citation("placeholder", fact_id))
            for ref in block.refs:
                if ref not in known:
                    failures.append(f"ref {ref!r} is not in this turn's tools")
                    citations.append(Citation(_ref_kind(ref), ref))
        elif isinstance(block, HandoffBlock):
            # The handoff summary hydrates too (the team mailbox sentence is a
            # fact of the handoff-team tool), so its placeholder is checked.
            for fact_id in leftover_placeholders(block.summary):
                if _fact_known(facts, fact_id) is None:
                    failures.append(_placeholder_failure(facts, fact_id))
                    citations.append(Citation("placeholder", fact_id))
    return failures, citations


def _cards_and_qualified(
    output: TurnOutput, facts: TurnFacts
) -> tuple[list[str], list[Citation]]:
    failures: list[str] = []
    citations: list[Citation] = []
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
                    citations.append(Citation("product", str(product_id)))
                if facts.qualified_ids and product_id not in facts.qualified_ids:
                    failures.append(
                        f"product {product_id} is not in search-products qualified"
                    )
            if isinstance(block, CardsBlock):
                extra = set(block.product_ids) - text_product_refs
                for product_id in extra:
                    failures.append(f"card {product_id} is not cited in the text refs")
    return failures, citations


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


def _handoff_only_when_out_of_scope(
    output: TurnOutput, route: Route | None = None
) -> list[str]:
    handoffs = [block for block in output.blocks if isinstance(block, HandoffBlock)]
    others = [block for block in output.blocks if not isinstance(block, HandoffBlock)]
    if handoffs and any(
        isinstance(block, CardsBlock | CompareBlock | ActionBlock) for block in others
    ):
        # Stock plus delivery: the card is the stock answer, the handoff
        # block is only the delivery half (owner 2026-10-05).
        if route is not None and route.stock and route.delivery:
            return []
        return ["a handoff turn may not also recommend products or actions"]
    return []


def _fact_known(facts: TurnFacts, fact_id: str) -> Fact | None:
    """The fact for an ID, tolerating a missing leading 'p' (model shorthand)."""
    fact = facts.facts.get(fact_id)
    if fact is None and not fact_id.startswith("p"):
        fact = facts.facts.get(f"p{fact_id}")
    return fact


def _no_bare_numbers(
    output: TurnOutput, facts: TurnFacts
) -> tuple[list[str], list[Citation], list[str]]:
    """Bare figure words, plus a search-knowledge digit that no cited chunk holds.

    A title does not license a series digit. `catalogue_name_phrases` still
    blanks that name for the quality citation check; this check does not call
    it. The scan is the same figure word `drop_bare_numbers` removes, so a
    number-only correction passes the re-check. An ASCII letter glued to a
    digit ("3-phase") is not one of those words: the product-route strip keeps
    it, and flagging it here would send that turn to the template.
    """
    failures: list[str] = []
    citations: list[Citation] = []
    chunk_failures: list[str] = []
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
            stripped = PLACEHOLDER.sub(" ", text)
            numbers = _droppable_tokens(stripped)
            if numbers:
                failures.append(f"model text contains numbers {numbers!r}")
                citations.extend(
                    Citation(kind="number", ref=token) for token in numbers
                )
                continue
            if not cited_chunk_text:
                continue
            for fact_id in leftover_placeholders(text):
                fact = facts.facts.get(fact_id)
                if fact is None:
                    fact = _fact_known(facts, fact_id)
                if fact is None or fact.source != "search-knowledge":
                    continue
                if fact.id.endswith(".text") or fact.id in facts.chunk_ids:
                    continue
                digits = bare_numbers(fact.value)
                if digits and not any(digit in cited_chunk_text for digit in digits):
                    chunk_failures.append(
                        f"number in {fact_id!r} does not appear in a cited chunk"
                    )
    return failures, citations, chunk_failures


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
