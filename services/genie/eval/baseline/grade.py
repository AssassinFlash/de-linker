"""Grade a captured Genie turn against one baseline100 row (ticket #336).

The口径 is the Knocket trial's (docs/research/2026-10-17-knocket/TRIAL.md §1-2,
kept by docs/specs/13-genie.md "对照题集") turned into code:

- a product is hit when a cards or compare block shows it. Text `refs` are
  not rendered, so a numeric ref is not a shown product;
- every number in the hydrated answer must be traceable: to the row's expected
  values (an empty list means no number may appear; unit conversions count, as
  the judge rubric words it), or to a catalogue model/SKU token the answer
  names. A figure listed on `figure_subjects` is not a flat allowance: in its
  clause it may stand only next to the product that owns it;
- every answer carries a next step (goal 9);
- the map's hard rows (#329: trials 1, 8, 10, 14) never fall back and never
  deflect to the team mailbox;
- EN and DE rows share one structure (same slots, same assertion kinds).

Everything here is pure: the runner feeds it parsed turns, the tests feed it
hand-made ones. The rows live in baseline100.jsonl beside this module.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from linker_genie.figures import is_code

# AGENTS.md §3: these words are not this shop's vocabulary, in either language.
FORBIDDEN_WORDS = (
    "catalogue",
    "catalog",
    "cart",
    "basket",
    "artikel",
    "katalog",
    "warenkorb",
)

# What counts as a next step (docs/specs/13-genie.md 目标 9: "每条回答后两到
# 三个可点的下一步"). A handoff is one too: the mailbox sentence is the step.
NEXT_STEP_BLOCKS = (
    "ask",
    "cards",
    "compare",
    "action",
    "document",
    "parts",
    "contact",
    "handoff",
)

# The mailbox the one-sentence referrals name; a hard row that mentions it has
# deflected (the map's gate: 不兜底不转 sales@).
MAILBOX = "sales@de-linker.com"

# A word with a digit in it (model codes like H2-10K-T3, GW15K-ETA-G20, values).
_CODE_WORD = re.compile(r"[^\s]*\d[^\s]*")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


@dataclass
class Turn:
    """One captured turn: the SSE stream's meta event, blocks and done flag."""

    meta: dict[str, Any] = field(default_factory=dict)
    blocks: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False


def _field(line: str, name: str) -> str | None:
    """The value of one SSE field. One leading space after the colon is the
    separator the spec strips; further spaces belong to the value."""

    prefix = name + ":"
    if not line.startswith(prefix):
        return None
    value = line[len(prefix) :]
    if value.startswith(" "):
        value = value[1:]
    return value.rstrip("\r")


def parse_stream(stream: str) -> Turn:
    """Read the service's SSE text (`event:`/`data:` pairs) into a Turn.

    Continued `data:` lines are joined with a newline, as the SSE spec
    concatenates them. The meta object's `timing` sits at the end of a long
    line; keeping only the first data line would drop it when a proxy wraps
    the event.
    """

    turn = Turn()
    for chunk in stream.split("\n\n"):
        lines = [line.rstrip("\r") for line in chunk.strip().splitlines()]
        name = next((value for line in lines if (value := _field(line, "event"))), None)
        data_lines = [
            value for line in lines if (value := _field(line, "data")) is not None
        ]
        if name is None or not data_lines:
            continue
        data: Any = json.loads("\n".join(data_lines))
        if name == "meta" and isinstance(data, dict):
            turn.meta = data
        elif name == "block" and isinstance(data, dict):
            turn.blocks.append(data)
        elif name == "done":
            turn.done = True
    return turn


def answer_text(blocks: list[dict[str, Any]]) -> str:
    """The words the customer reads: text blocks plus a handoff's summary."""

    parts = []
    for block in blocks:
        if block.get("type") == "text":
            parts.append(str(block.get("text", "")))
        elif block.get("type") == "handoff":
            parts.append(str(block.get("summary", "")))
    return "\n".join(parts)


def block_types(blocks: list[dict[str, Any]]) -> set[str]:
    return {str(block.get("type")) for block in blocks}


def shown_ids(blocks: list[dict[str, Any]]) -> set[int]:
    """Product ids the customer can see: a cards or compare block.

    The shell renders those blocks. A text block's `refs` are stored and not
    drawn, so a numeric ref is not a shown product (the map's hard rows and
    every row that requires a product fail without the block).
    """

    ids: set[int] = set()
    for block in blocks:
        if block.get("type") in {"cards", "compare"}:
            ids.update(int(pid) for pid in block.get("product_ids") or [])
    return ids


def compare_ids(blocks: list[dict[str, Any]]) -> list[set[int]]:
    """Every compare block's product ids, one set per block."""

    return [
        {int(pid) for pid in block.get("product_ids") or []}
        for block in blocks
        if block.get("type") == "compare"
    ]


def cited_refs(blocks: list[dict[str, Any]]) -> set[str]:
    """The refs of text blocks (a `page` ref means the answer cites the page)."""

    return {
        str(ref)
        for block in blocks
        if block.get("type") == "text"
        for ref in block.get("refs") or []
    }


def action_names(blocks: list[dict[str, Any]]) -> set[str]:
    return {str(block.get("name")) for block in blocks if block.get("type") == "action"}


def contact_reasons(blocks: list[dict[str, Any]]) -> set[str]:
    return {
        str(block.get("reason")) for block in blocks if block.get("type") == "contact"
    }


def price_lines(blocks: list[dict[str, Any]]) -> list[str]:
    """The card price lines the service filled (#242): the only price surface."""

    lines = []
    for block in blocks:
        if block.get("type") != "cards":
            continue
        for price in block.get("prices") or []:
            if isinstance(price, dict) and price.get("text"):
                lines.append(str(price["text"]))
    return lines


def number_variants(token: str) -> set[float]:
    """The numbers a printed token can mean: `20.000` is 20000 (EN thousands)
    or 20.0 (a decimal), `20,000` the same pair the other way round."""

    values: list[float] = []
    for separator in (".", ","):
        if separator in token:
            whole, _, fraction = token.partition(separator)
            if whole.isdigit() and fraction.isdigit():
                values.append(float(f"{whole}.{fraction}"))
                if len(fraction) == 3:  # a thousands group, EN or DE print
                    values.append(float(whole + fraction))
    if token.isdigit():
        values.append(float(token))
    return set(values)


def _catalog_tokens(catalog: Mapping[str, str]) -> set[str]:
    """A word is a catalogue code when its letters-and-digits form is one.

    Catalogue tokens arrive as the Store API prints them - the model attribute
    ("EF HD-P1-3K68-S2") and the product name - so a token is split on
    whitespace first: the answer names the model without the brand prefix
    ("HD-P1-3K68-S2")."""

    codes: set[str] = set()
    for token in catalog:
        for part in str(token).split():
            stripped = re.sub(r"[^a-z0-9]", "", part.lower())
            if stripped:
                codes.add(stripped)
    return codes


def untraceable_numbers(
    text: str, allowed: list[str], catalog: Mapping[str, str] | None = None
) -> list[str]:
    """Numbers in the answer that no expected fact and no catalogue code backs.

    `allowed` is the row's `expect.numbers` (strings, e.g. "20000", "6.6",
    "2026"): a token passes when any of its readings equals an allowed value or
    its 1000-fold (15000 Wp = 15 kWp = 15.000 Wp, as the judge rubric words
    it). A number inside a catalogue model/SKU (H2-10K-T3) is traceable by
    being that product's name.
    """

    permitted: set[float] = set()
    for value in allowed:
        for variant in number_variants(str(value)):
            permitted.update({variant, variant * 1000.0, variant / 1000.0})
    codes = _catalog_tokens(catalog or {})
    untraceable = []
    for word in _CODE_WORD.findall(text):
        # The same model-code rule as ground.bare_numbers (figures.is_code).
        # "BD-JC-S2" is a designation, not the measurement 2.
        if is_code(word):
            continue
        stripped = re.sub(r"[^a-z0-9]", "", word.lower())
        if stripped in codes:
            continue
        # A series prefix as printed on its own ("CB2" for CB2-100.3-HV5) is
        # still the product's own code.
        if any(letter.isalpha() for letter in stripped) and any(
            code.startswith(stripped) for code in codes
        ):
            continue
        # A designation the manual uses for equipment we do not sell (CH2, the
        # inverter a CB2 cabinet connects to): letters first, then digits, no
        # unit - unlike a measurement ("1500mm", digits first).
        if re.match(r"[a-z]{1,4}\d", stripped):
            continue
        for token in _NUMBER.findall(word):
            readings = number_variants(token)
            if readings and not readings & permitted:
                untraceable.append(token)
    return untraceable


def clauses(text: str) -> list[str]:
    """Sentences and semicolon-separated claims, so a later negation cannot
    license an earlier one."""

    return [part.strip() for part in re.split(r"[.!?;\n]+", text) if part.strip()]


# A copula, colon, dash, "comes to", "liegt bei", or "of"/"von" that hands
# the next standalone number to the banned phrase. "of the L260" does not:
# "of" binds only when a digit follows. "comes to" is the judge template's
# copula (eval/judges/src/linker_judges/templates.py). "liegt" and "bei" are
# two prefill filler tokens (prefill.py); up to three words may sit between
# them ("liegt die nutzbare Energie bei"). A word is \S+, so a hyphen
# compound (L260-OMNI) is one word, not two. The clause split already ends
# the phrase at .!?; so the gap cannot cross a sentence. A dash (—, –, or a
# spaced hyphen) presents the same way a colon does. A number that opens the
# tail ("usable capacity 260 kWh") is a bare presenter; that alternative is
# only the start of the tail, so "is not 260" stays a denial.
_LIEGT_GAP = r"(?:\s+\S+){0,3}"
_PRESENTED_FIGURE = re.compile(
    r"(?i)(?:"
    r"\b(?:is|are|equals?|was|were|comes\s+to|"
    r"beträgt|betraegt|betragen|ist|sind)\b"
    rf"|\bliegt{_LIEGT_GAP}\s+bei\b"
    r"|[:=—–]"
    r"|\s-\s"
    r"|\b(?:of|von)\s+(?=\d)"
    r"|^\s*(?=\d)"
    r")"
)
# The same binder when the banned phrase sits inside the gap
# ("liegt die nutzbare Energie bei 260").
_LIEGT_BEI = re.compile(rf"(?i)\bliegt(?P<mid>{_LIEGT_GAP})\s+bei\b")
# A full token. "L260" must not yield 60, and "H2-20K" must not yield 20.
_STANDALONE_NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*(?![A-Za-z0-9])")
_DENIAL_WORD = re.compile(
    r"(?i)\b(?:not|no|without|rather|none|kein(?:e[rmns]?)?|nicht|ohne)\b"
)
# The banned phrase is the complement: "260 kWh is the usable capacity".
# Only a determiner may sit between the copula and the phrase, so "is not
# the" stays a denial.
_INVERTED_COPULA = re.compile(
    r"(?i)\b(?:is|are|equals?|was|were|comes\s+to|"
    r"beträgt|betraegt|betragen|ist|sind)\b"
    r"(?:\s+(?:the|a|an|der|die|das|den|dem|des|"
    r"ein|eine|einer|einem|einen|eines))?\s*$"
)
# "40 and 30 kW, respectively": pair by order, not by nearest subject.
_RESPECTIVELY = re.compile(r"(?i)\b(?:respectively|respektive)\b")
# The figure's own noun. Bare "nominal" is not enough: "the nominal L260" is
# the model, not a different figure. "nominal capacity of 260" and
# "Nennkapazität 260" are this noun sitting on its own figure.
_OTHER_HEAD = re.compile(
    r"(?i)\b(?:nominal\s+(?:capacity|energy)"
    r"|nenn(?:kapazität|kapazitaet|energie)"
    r"|depth\s+of\s+discharge|entladetiefe|\bdod\b)\b"
)
# "not 95 but 260" re-asserts the number after the contrast. "and"/"und" are
# not in this set: they start a new claim, which the other-subject cut handles.
_FIGURE_CONTRAST = re.compile(
    r"(?i)\b(?:but|however|although|though|aber|jedoch|doch|sondern)\b"
)
# A comma or "and"/"und" can start a new claim ("…, the nominal capacity is").
_NEW_CLAIM = re.compile(r"(?i)\b(?:and|und)\b|,")
# "260 kWh usable capacity": the number sits against the phrase, before it.
# The number is a whole token, so "L260" does not match on the digits 60.
_APPOSITION = re.compile(
    r"(?i)(?<![A-Za-z0-9])\d+(?:[.,]\d+)*"
    r"(?:\s*(?:kwh|kw|%))?(?![A-Za-z0-9])\s*,?\s*$"
)
# Trial 19. "and"/"und" end the absence ("…whether it supports, and it
# supports"). "that"/"dass" are denial binders beside "whether"/"ob".
_CONTRAST = re.compile(
    r"(?i)\b(?:but|however|although|though|and|und|aber|jedoch|doch|sondern)\b"
)
_DENIAL_BINDER = re.compile(r"(?i)\b(?:whether|that|ob|dass)\b")
_ABSENCE = re.compile(
    r"(?i)\b(?:do(?:es)? not|don't)\s+state\b"
    r"|\b(?:nicht|kein(?:e[rmns]?)?|keinen)\b"
)


def _expanded_values(values: list[str]) -> set[float]:
    """A listed figure plus the 1000-fold the flat number check already allows."""

    permitted: set[float] = set()
    for value in values:
        for variant in number_variants(str(value)):
            permitted.update({variant, variant * 1000.0, variant / 1000.0})
    return permitted


def _number_is_denied(text: str, start: int) -> bool:
    """True when a denial still covers the number at `start`.

    "not 95 kWh but 260 kWh": the contrast cancels the denial for what follows
    it. "is not 260 kWh" and "does not have 40 kW" stay denials.
    """

    left = text[:start]
    denials = list(_DENIAL_WORD.finditer(left))
    if not denials:
        return False
    contrasts = list(_FIGURE_CONTRAST.finditer(left))
    return not contrasts or denials[-1].end() > contrasts[-1].end()


def _asserted_number(span: str) -> bool:
    """True when `span` states a number that a denial does not still cover."""

    return any(
        not _number_is_denied(span, number.start())
        for number in _STANDALONE_NUMBER.finditer(span)
    )


def _phrase_predicate(tail: str) -> str | None:
    """The words the banned phrase's own presenter governs.

    The presenter belongs to the banned phrase when no other-subject noun sits
    before it. "is the nominal capacity of 260" is that presenter: the nominal
    noun is the predicate, not a separate figure. A later ", the nominal
    capacity is …" or "and the nominal capacity is …" is a new claim and is
    cut off. There is no character window: a 48-character lookback exempted
    any "nominal capacity" in the predicate.
    """

    presenter: re.Match[str] | None = None
    for candidate in _PRESENTED_FIGURE.finditer(tail):
        if _OTHER_HEAD.search(tail[: candidate.start()]):
            continue
        presenter = candidate
        break
    if presenter is None:
        return None
    predicate = tail[presenter.end() :]
    for claim in _NEW_CLAIM.finditer(predicate):
        if _OTHER_HEAD.search(predicate[claim.end() :]):
            predicate = predicate[: claim.start()]
            break
    return predicate


def _apposes_figure(prefix: str) -> bool:
    """True when a number and its unit sit directly against the phrase."""

    return _APPOSITION.search(prefix) is not None


def _inverted_copula(prefix: str) -> bool:
    """True when the phrase is the complement of a copula that carries a number.

    "The nominal capacity of 260 kWh is the usable capacity" states 260 as
    that phrase. "is not the usable capacity" does not: "not" breaks the
    determiner-only gap.
    """

    copula = _INVERTED_COPULA.search(prefix)
    if copula is None:
        return False
    return _asserted_number(prefix[: copula.start()])


def _liegt_binds_phrase(clause: str, start: int, end: int) -> bool:
    """True when `liegt … bei` wraps the banned phrase and a number follows.

    "Beim Modell L260-OMNI liegt die nutzbare Energie bei 260 kWh": the phrase
    is inside the gap, so a search of the tail never sees "liegt".
    """

    for binder in _LIEGT_BEI.finditer(clause):
        mid_start = binder.start("mid")
        bei = binder.end("mid")
        if (
            mid_start <= start
            and end <= bei
            and _asserted_number(clause[binder.end() :])
        ):
            return True
    return False


def _presents_banned_figure(tail: str) -> bool:
    """True when `tail` (the words after a banned phrase) binds a standalone
    number to that phrase.

    "nominal capacity of 260 kWh" and "Nennkapazität 260 kWh" pass when that
    noun is the figure's own label. "The usable capacity is the nominal
    capacity of 260 kWh" fails: the copula's subject is the usable phrase.
    "comes to" and "liegt bei" are the same copula. "is not 95 but 260"
    re-asserts 260.
    """

    predicate = _phrase_predicate(tail)
    if predicate is None:
        return False
    return _asserted_number(predicate)


def numbered_claim_failures(text: str, patterns: list[str]) -> list[str]:
    """A clause matching `patterns` may not present a number as that figure.

    Trial 6 names "usable capacity" only to say the documents do not state
    one. Writing 260 kWh onto that phrase is the figure the rubric bans,
    including apposition ("260 kWh usable capacity"), a dash, a bare number
    ("usable capacity 260 kWh"), the inverted copula ("260 kWh is the usable
    capacity"), "liegt … bei" with the phrase inside the gap, and "not X but Y".
    The nominal value and the depth of discharge are not that figure when
    the noun labelling them is their own. A model token (L260) is not a number.
    """

    failures = []
    for clause in clauses(text):
        presented = False
        for pattern in patterns:
            for match in re.finditer(pattern, clause):
                prefix = clause[: match.start()]
                if _apposes_figure(prefix) or _inverted_copula(prefix):
                    presented = True
                    break
                if _presents_banned_figure(clause[match.end() :]):
                    presented = True
                    break
                if _liegt_binds_phrase(clause, match.start(), match.end()):
                    presented = True
                    break
            if presented:
                break
        if presented:
            failures.append(f"a banned figure is stated in '{clause[:120]}'")
    return failures


def _mention_is_denied(clause: str, start: int) -> bool:
    """True when the match sits inside "do not state whether/that …" or
    "nicht, ob/dass …", and not past that binder's clause.

    A comma after the binder, or and/und/but before the verb, starts a new
    claim. "do not state whether it supports, and it supports" fails on the
    second verb. "do not state that it supports" is the absence.
    """

    before = clause[:start]
    absence = list(_ABSENCE.finditer(before))
    if not absence:
        return False
    tail = before[absence[-1].end() :]
    if _CONTRAST.search(tail):
        return False
    binder = _DENIAL_BINDER.search(tail)
    if binder is None:
        return False
    return "," not in tail[binder.end() :]


def subject_figure_failures(
    text: str, bindings: list[dict[str, Any]]
) -> tuple[list[str], set[str]]:
    """A neighbour's figure may stand only next to that neighbour.

    `bindings` is the row's `figure_subjects`: a product pattern and the
    figures that belong to it. A number listed on any binding is not a flat
    allowlist value. Inside one clause it passes only when the nearest named
    subject lists it, so "GW15K-ETA-G20 has 40 kW" fails (40 is the GW20K
    PV input) and "GW20K-ETA-G20 has 40 kW" passes. "respectively" /
    "respektive" pairs subjects and numbers in order instead of by distance.
    A denial ("does not have 40 kW") is not a claim: the number is waived so
    the flat check does not fail it either. The clause is the window: a later
    sentence does not lend its subject. The returned tokens were licensed by
    their subject or waived by a denial, so the flat check can leave them off
    the allowlist.
    """

    compiled: list[tuple[re.Pattern[str], set[float]]] = []
    owned: set[float] = set()
    for binding in bindings:
        values = _expanded_values([str(item) for item in binding.get("numbers") or []])
        compiled.append((re.compile(str(binding["subject"])), values))
        owned |= values
    if not compiled or not owned:
        return [], set()
    failures: list[str] = []
    licensed: set[str] = set()
    waived: set[str] = set()
    blocked: set[str] = set()
    for clause in clauses(text):
        found: list[tuple[int, int, set[float], str]] = []
        for pattern, values in compiled:
            for match in pattern.finditer(clause):
                found.append((match.start(), match.end(), values, match.group()))
        ordered = sorted(found, key=lambda item: item[0])
        outside = [
            number
            for number in _STANDALONE_NUMBER.finditer(clause)
            if not any(
                number.start() < end and number.end() > start
                for start, end, _, _ in ordered
            )
        ]
        paired: dict[int, tuple[int, int, set[float], str]] = {}
        if _RESPECTIVELY.search(clause) and ordered and len(outside) == len(ordered):
            paired = {
                number.start(): subject
                for number, subject in zip(outside, ordered, strict=True)
            }
        for number in _STANDALONE_NUMBER.finditer(clause):
            readings = _expanded_values([number.group()])
            if not readings & owned:
                continue
            token = number.group()
            if _number_is_denied(clause, number.start()):
                waived.add(token)
                continue
            if not found:
                blocked.add(token)
                failures.append(
                    f"number {token} is not tied to the product it belongs to"
                )
                continue
            nearest = paired.get(number.start())
            if nearest is None:
                nearest = min(
                    found,
                    key=lambda item: (
                        item[0] - number.end()
                        if number.start() < item[0]
                        else number.start() - item[1]
                        if number.start() > item[1]
                        else 0
                    ),
                )
            if readings & nearest[2]:
                licensed.add(token)
            else:
                blocked.add(token)
                failures.append(f"number {token} is not a figure of {nearest[3]}")
    return failures, (licensed | waived) - blocked


def clause_failures(text: str, patterns: list[str]) -> list[str]:
    """Patterns no clause may assert.

    Trial 19: "supports EnWG 14a; the documents do not state it explicitly"
    is a support claim. "The documents do not state whether the H2 supports
    …" is the absence the rubric asks for, and it does not cancel another
    clause that asserts support.
    """

    failures = []
    for clause in clauses(text):
        for pattern in patterns:
            for match in re.finditer(pattern, clause):
                if _mention_is_denied(clause, match.start()):
                    continue
                failures.append(f"clause asserts /{pattern}/: '{clause[:120]}'")
                break
    return failures


# A rated-power figure, including a range ("3–6 kW", "5 to 15 kW").
_KW = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:(?:[–\-]|to|bis)\s*(\d+(?:[.,]\d+)?)\s*)?kW\b",
    re.IGNORECASE,
)
# How far a power may sit from the phase label it belongs to.
_PHASE_WINDOW = 80


def phase_power_failures(text: str, bindings: list[dict[str, Any]]) -> list[str]:
    """Each kW figure must belong to the nearest phase label, and each phase
    must have at least one of its own powers stated with it.

    Trial 8: single-phase is 3–6 kW (Plus up to 12) and three-phase is 5–15 kW.
    Listing both phase words and both families of numbers is not enough:
    "single-phase 15 kW, three-phase 3.68 kW" swaps them.
    """

    labels: list[tuple[int, int, dict[str, Any]]] = []
    for binding in bindings:
        for match in re.finditer(str(binding["label"]), text):
            labels.append((match.start(), match.end(), binding))
    # A heading names the section that follows it ("### Einphasige
    # Ausführung"). A prose sentence that mentions both phase words ("both
    # single- and three-phase") must not capture the bullets below it.
    headings: list[tuple[int, dict[str, Any]]] = []
    for start, end, binding in labels:
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)
        line = text[line_start : line_end if line_end != -1 else len(text)]
        # Strip the bullet marker so "- **Einphasig:** …" reads as a heading,
        # while a long intro sentence that happens to end with ":" and mentions
        # both phase words is not one (#336B review, local smoke). A plain
        # "Einphasig: …" only heads a section when the label is followed by a
        # colon near the start of the line.
        marker = re.match(r"[ \t]*(?:[-*+]\s+)?", line)
        body_offset = line_start + (marker.end() if marker else 0)
        body = text[body_offset : line_end if line_end != -1 else len(text)]
        label_text = text[start:end]
        heading_like = (
            body.startswith(("#", "**"))
            or re.match(rf"(?i)^{re.escape(label_text)}[^\n:]{{0,10}}:", body)
            is not None
        )
        if heading_like:
            headings.append((start, binding))
    headings.sort(key=lambda item: item[0])
    failures: list[str] = []
    seen = {str(binding["phase"]): False for binding in bindings}
    for match in _KW.finditer(text):
        nearest: dict[str, Any] | None = None
        nearest_distance: int | None = None
        if headings:
            before = [binding for start, binding in headings if start <= match.start()]
            if before:
                nearest = before[-1]
                nearest_distance = 0
        for start, end, binding in labels:
            if match.start() < start:
                distance = start - match.end()
            elif match.start() > end:
                distance = match.start() - end
            else:
                distance = 0
            if nearest_distance is None or distance < nearest_distance:
                nearest = binding
                nearest_distance = distance
        allowed: set[float] = set()
        phase = None
        if (
            nearest is not None
            and nearest_distance is not None
            and nearest_distance <= _PHASE_WINDOW
        ):
            phase = str(nearest["phase"])
            for value in nearest["powers"]:
                allowed.update(number_variants(str(value)))
        for raw in (group for group in match.groups() if group):
            readings = number_variants(raw)
            if phase is None:
                failures.append(f"power {raw} kW is not tied to a phase")
            elif not readings & allowed:
                failures.append(f"power {raw} kW is not a {phase}-phase rating")
            else:
                seen[phase] = True
    for phase, stated in seen.items():
        if not stated:
            failures.append(f"no {phase}-phase power is tied to that phase")
    return failures


def _floors(row: dict[str, Any], turn: Turn) -> list[str]:
    """The checks every row of the set shares (TRIAL.md's zero-error lines)."""

    failures: list[str] = []
    if not turn.done:
        failures.append("stream did not finish (no done event)")
    if turn.meta.get("fallback"):
        failures.append("fell back to the template (no answer)")
    if not turn.meta.get("grounded"):
        failures.append(
            f"ungrounded: {'; '.join(map(str, turn.meta.get('failures') or []))}"
        )
    if str(turn.meta.get("language")) != row["lang"]:
        failures.append(
            f"answered in {turn.meta.get('language')!r}, the customer wrote {row['lang']}"
        )
    text = answer_text(turn.blocks).lower()
    for word in FORBIDDEN_WORDS:
        if re.search(rf"\b{word}\b", text):
            failures.append(f"forbidden word '{word}' (AGENTS.md §3)")
    return failures


# Content of the #394 signed sentences (template.py owns the wording). A row
# fails when the customer would read that content twice. The canonical partner
# paragraph says "net price" / "Nettopreis" twice (the net-price sentence and
# the guest line); a third mention is the paragraph repeated after a paraphrase.
_ONCE = (
    ("ai assistant", "AI assistant"),
    ("ki-assistent", "KI-Assistent"),
    ("which product category", "product-category question"),
    ("welche produktkategorie", "Produktkategorie question"),
    ("approved partner accounts see net prices", "partner net-price sentence"),
    ("net price after partner sign-in", "guest price line"),
    ("prices after approval", "review price line"),
    ("freigegebene partnerkonten sehen die nettopreise", "Partner-Nettopreise"),
    ("nettopreis nach partner-anmeldung", "guest price line"),
    ("preise nach freigabe", "review price line"),
    ("within one working day", "one-working-day reply"),
    ("innerhalb eines werktags", "Werktag reply"),
)


# The signed next-step answers put one question to the customer: TALK ends
# with "Which product category do you want to look at?" and the ask chips
# answer it (copy-review 2026-10-20, EN/DE greeting). Goal 9's second block is
# the clickable ask, never a second question sentence.
MAX_QUESTIONS = 1


def repeated_signed_copy(text: str) -> list[str]:
    """Why this answer repeats a signed next-step sentence or asks twice."""

    folded = text.casefold()
    failures = [
        f"signed copy repeated: {label}"
        for needle, label in _ONCE
        if folded.count(needle) > 1
    ]
    if folded.count("net price") > 2:
        failures.append("signed copy repeated: net price")
    if folded.count("nettopreis") > 2:
        failures.append("signed copy repeated: Nettopreis")
    if text.count("?") > MAX_QUESTIONS:
        failures.append("more than one question")
    return failures


def check(
    row: dict[str, Any],
    turn: Turn,
    catalog: Mapping[str, str] | None = None,
) -> list[str]:
    """Why the row fails; empty when it passes. Judge/human-review rows still
    run the floors and any `expect` they carry — the verdict beyond that is the
    judge's or a person's, not this function's."""

    failures = _floors(row, turn)
    expect = row.get("expect") or {}
    blocks = turn.blocks
    text = answer_text(blocks)
    types = block_types(blocks)
    shown = shown_ids(blocks)

    for product_id in expect.get("products", []):
        if int(product_id) not in shown:
            failures.append(f"product {product_id} is not in a cards or compare block")
    any_of = expect.get("products_any")
    absence = expect.get("absence_any") or []
    claims_absence = bool(absence) and any(
        re.search(pattern, text) for pattern in absence
    )
    partners = {int(pid) for pid in any_of} if any_of else set()
    # `released` means the row's ground says this battery is released (b10,
    # compatibility.json line 1546). A no-pairing sentence about a released
    # battery fails on its own, partner card or not (#396). A row that is not
    # released may still accept an absence sentence; an unrelated card on
    # that sentence still fails.
    if any_of and claims_absence and expect.get("released"):
        failures.append(
            "released battery: a no-pairing sentence does not replace the partner cards"
        )
    if any_of and claims_absence and not expect.get("released"):
        unrelated = sorted(shown - partners)
        if unrelated:
            failures.append(f"no documented pairing, but unrelated cards {unrelated}")
    elif any_of and not partners & shown:
        failures.append(f"none of products {any_of} is in a cards or compare block")

    groups = expect.get("compare")
    if groups is not None:
        wanted = [{int(pid) for pid in group} for group in groups]
        comparisons = compare_ids(blocks)
        held = any(group <= block_ids for group in wanted for block_ids in comparisons)
        if not comparisons:
            failures.append("no compare block")
        elif not held:
            failures.append(f"no compare block holds one of {groups}")

    for kind in expect.get("blocks", []):
        if kind not in types:
            failures.append(f"no {kind} block")
    for kind in expect.get("not_blocks", []):
        if kind in types:
            failures.append(f"must not carry a {kind} block")

    if "action" in expect and expect["action"] not in action_names(blocks):
        failures.append(f"no {expect['action']} action")

    if expect.get("document") and "document" not in types:
        failures.append("no document link cited")

    contact = expect.get("contact")
    if contact is not None:
        reasons = contact_reasons(blocks)
        if not reasons:
            failures.append("no contact offer")
        elif isinstance(contact, str) and contact not in reasons:
            failures.append(f"contact offer is {sorted(reasons)}, expected '{contact}'")

    if expect.get("no_handoff"):
        if "handoff" in types:
            failures.append("deflected to the team (handoff block)")
        if MAILBOX in text:
            failures.append(f"sent the customer to {MAILBOX}")

    gate = expect.get("price_gate")
    if gate is not None:
        lines = price_lines(blocks)
        if not lines:
            failures.append("cards carry no price line")
        elif not any(re.search(gate, line) for line in lines):
            failures.append(f"card price line is {lines}, expected /{gate}/")

    for pattern in expect.get("all", []):
        if not re.search(pattern, text):
            failures.append(f"missing /{pattern}/")
    for pattern in expect.get("none", []):
        if re.search(pattern, text):
            failures.append(f"must not match /{pattern}/")

    if expect.get("next_step") and not types & set(NEXT_STEP_BLOCKS):
        failures.append("no next step after the answer (goal 9)")

    if expect.get("cites_page") and "page" not in cited_refs(blocks):
        failures.append("the answer does not cite the page")

    # Every row carries `numbers`. Missing means the same as empty: no number
    # may appear, apart from a catalogue model/SKU and a unit conversion of an
    # expected value. The check always runs (#329: 0 fabricated numbers).
    # `figure_subjects` is stricter than that list: a neighbour's figure is
    # traceable only in the clause of the product that owns it. A token that
    # clause licenses is added for this turn so the flat check does not fail
    # it a second time. A blocked occurrence is not licensed.
    licensed: set[str] = set()
    subjects = expect.get("figure_subjects")
    if subjects:
        bound, licensed = subject_figure_failures(text, subjects)
        failures.extend(bound)
    allowed = [str(value) for value in expect.get("numbers") or []]
    for token in untraceable_numbers(text, [*allowed, *licensed], catalog):
        failures.append(f"number {token} is in no expected fact")

    failures.extend(repeated_signed_copy(text))

    phase_powers = expect.get("phase_powers")
    if phase_powers:
        failures.extend(phase_power_failures(text, phase_powers))
    no_figure = expect.get("no_figure_on")
    if no_figure:
        failures.extend(numbered_claim_failures(text, [str(p) for p in no_figure]))
    no_clause = expect.get("no_clause")
    if no_clause:
        failures.extend(clause_failures(text, [str(p) for p in no_clause]))
    return failures
