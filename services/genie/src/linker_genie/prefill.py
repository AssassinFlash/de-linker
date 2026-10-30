"""Configurator prefill read from the customer's own words (#365).

The residential URL (spec 14) is filled only from user messages in this
conversation. ``stated_size_hint`` is the one derivation: the sizing route
stores that dict, and the wire sends the same object. A later message
overrides the same field. A question never sets phase or backup. A denial
is a stated value: phase is removed, backup is ``none``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Literal

# Residential configurator only (spec 14). A commercial site is sized from a
# load profile, not from these two fields. Zero is a parse fragment — a
# thousands group read on its own ("000") — not a size the customer stated.
# The ceilings are sanity caps, wider than the form's own typing bounds
# (ResidentialInput in services/engine/src/linker_engine/models.py: pv_kwp
# le=100, annual_kwh le=50_000). A figure the customer did state, such as
# 150 kWp, stays in the URL and the form reports it. Above the caps the
# figure is not this form:
# pv_kwp 1 000 — ten times the form field, and above a misread thousands
# group ("12.000 kWp" is 12 000).
# annual_load_kwh 100 000 — registering load-profile metering
# (MsbG § 55 (1) Nr. 1; linker_engine.rules.RLM_THRESHOLD_KWH).
_MAX_KWP = 1000
_MAX_KWH = 100_000
# A negation governs the keyword when it stands within this many words of it
# in the same clause. Three words is a copula plus a short modifier
# ("ist nicht nötig", "is not required", "do not need"). The count is words:
# a German compound is one word however long it is.
_NEG_WINDOW = 3

# A quantity, including a thousands group. A group is three digits
# (German "4.500", English "12,000", spaced "12 000"). Space, dot and comma
# are grouping; the last separator is the decimal when both appear. Grouped
# forms are tried first so "12 000" is one token and never the trailing
# "000". One or two digits after a single separator stay a decimal
# ("12,5", "12.5").
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
# The year word may sit before the number or after it. Longer phrases come
# first so "jahresstromverbrauch" is not read as a shorter stem.
_YEAR_BEFORE = (
    r"jahresstromverbrauch|stromverbrauch|jahresverbrauch|"
    r"annual\s+consumption|annual\s+load|yearly\s+consumption|yearly\s+load|"
    r"consumption\s+per\s+year|verbrauch\s+pro\s+jahr|"
    r"pro\s+jahr|im\s+jahr|jährlich|jaehrlich|yearly|annual"
)
_YEAR_AFTER = (
    r"(?:/\s*(?:year|yr|jahr|a)\b|per\s+year|a\s+year|pro\s+jahr|im\s+jahr|"
    r"jährlich|jaehrlich|yearly|annual|jahresverbrauch|p\.\s*a\.)"
)
# Copula or filler between the year word and the number: "of about",
# "is" / "are" / "ist", "liegt bei", "beträgt". Each token is optional and
# repeatable, so "of about" is two tokens and "liegt bei" is two tokens.
_FILLER = (
    r"of|von|ca\.?|about|around|circa|rund|etwa|ungefähr|ungefaehr|"
    r"approx(?:imately)?|is|are|ist|sind|liegt|bei|beträgt|betraegt|"
    r"betragen|equals?"
)
_GAP = rf"(?:\s*[:\-]\s*|\s+)(?:(?:{_FILLER})\s+)*"
_ANNUAL_BEFORE = re.compile(
    rf"\b(?:{_YEAR_BEFORE}){_GAP}{_NUM}\s*kwh\b",
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
# European postal formats vary: four or five digits, letter/digit forms, and
# an optional space or country prefix. The label supplies the field boundary;
# a five-digit value before the label remains the conservative unlabelled form.
# Values stay strings so a leading zero ("01067") is preserved.
_PLZ_WORD = r"\b(?:plz|postleitzahl|postcode|zip(?:\s+code)?)\b"
_POSTAL_AFTER = (
    r"(?=[A-Za-z0-9 -]{2,24}\b)"
    r"(?=[A-Za-z0-9 -]*\d)"
    r"[A-Za-z0-9]{1,10}"
    r"(?:[ -](?:(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{1,6}|[A-Za-z]{1,3}))?"
    r"(?!\w)"
)
_PLZ = re.compile(
    rf"{_PLZ_WORD}\s*[:\-]?\s*(?P<after>{_POSTAL_AFTER})"
    rf"|(?<!\d)(?P<before>\d{{5}})(?!\d)\s*[:\-]?\s*{_PLZ_WORD}",
    re.IGNORECASE,
)
# Longer phrases before shorter ones so "do not" is not read as "not".
_NEG_WORD = (
    r"(?:ohne|kein(?:e[mnrs]?)?|nicht|nie|niemals|without|"
    r"do not|does not|don'?t|doesn'?t|never|not|no)"
)
_NEG_BEFORE = re.compile(
    rf"\b{_NEG_WORD}\b(?:\s+\w+){{0,{_NEG_WINDOW}}}\s*$",
    re.IGNORECASE,
)
_NEG_AFTER = re.compile(
    rf"^(?:\s+\w+){{0,{_NEG_WINDOW}}}\s+\b{_NEG_WORD}\b",
    re.IGNORECASE,
)
# "nicht nur" / "not only" does not deny the keyword. The contrast is not a
# stated "none" and not a stated "needed".
_NOT_ONLY = re.compile(
    r"\b(?:nicht\s+nur|not\s+only)(?:\s+\w+){0,2}\s*$",
    re.IGNORECASE,
)
_WITH = re.compile(r"\b(?:mit|with)\s*$", re.IGNORECASE)
# Articles, copulas and coordinators. A content noun is not in this list:
# "ohne Netz und mit Notstrom" — "Netz" blocks "ohne" from governing "mit".
_FUNCTION = (
    r"ist|sind|is|are|was|were|war|ein|eine|einer|einem|einen|eines|"
    r"der|die|das|den|dem|des|the|a|an|auch|also|too|es|it|"
    r"sehr|really|zu|to|of|für|fur|for|und|and|oder|or|doch|"
    r"ich|du|wir|sie|man|i|you|we|they|he|she"
)
_POLARITY_VERB = (
    r"need|needs|brauche|brauchen|braucht|want|wants|"
    r"habe|haben|has|have|möchte|moechte|möchten|"
    r"benötige|benoetige|benötigen|benoetigen"
)
_NEG_ON_WITH = re.compile(
    rf"\b{_NEG_WORD}\b(?:\s+(?:{_FUNCTION}))*\s+(?:mit|with)\s*$",
    re.IGNORECASE,
)
# The negation sits on the keyword itself, or on the verb whose object it
# is ("do not need backup"), or in the copula after it ("is not required").
_DIRECT_BEFORE = re.compile(
    rf"\b{_NEG_WORD}\b(?:\s+(?:{_FUNCTION}|{_POLARITY_VERB}))*\s*$",
    re.IGNORECASE,
)
_DIRECT_AFTER = re.compile(
    rf"^(?:\s+(?:{_FUNCTION}|needed|nötig|noetig|erforderlich|required))*"
    rf"\s+\b{_NEG_WORD}\b",
    re.IGNORECASE,
)
_AFFIRM = re.compile(
    rf"\b(?:mit|with|{_POLARITY_VERB})\b",
    re.IGNORECASE,
)
_ANY_NEG = re.compile(rf"\b{_NEG_WORD}\b", re.IGNORECASE)

# A clause is a question when the interrogative governs it: a question mark,
# verb-first / auxiliary inversion, or an indirect question (ob / whether / if).
# A wh-word that introduces a statement ("Was ich brauche", "What I need is",
# "Wie gesagt") does not. German question word order puts the finite verb
# first, or second after the wh-word; a statement keeps the verb after the
# subject.
_OPEN = r"""[\s"'“”«»(\[]*"""
_COORD = r"und|oder|aber|and|or|but"
_COORD_OPT = rf"(?:(?:{_COORD})\s+)?"
_DE_VERB = (
    r"ist|sind|hat|haben|kann|können|koennen|wird|werden|"
    r"unterstützt|unterstuetzt|gibt|geht|kostet|kosten|braucht|"
    r"soll|sollen|darf|dürfen|duerfen|lässt|laesst|lassen|"
    r"wäre|waere|hätte|haette|funktioniert|klappt"
)
_EN_AUX = (
    r"can|could|does|do|did|is|are|was|were|will|would|should|"
    r"has|have|may|might"
)
_WH = (
    r"what|which|how|why|when|where|who|"
    r"wie|was|welche[rsnm]?|warum|wann|wo|wer|wieso|weshalb"
)
_DEGREE = r"groß|gross|big|large|much|many|size|long|far|viel|viele"
_VERB_FIRST = re.compile(
    rf"^{_OPEN}{_COORD_OPT}(?:{_DE_VERB}|{_EN_AUX})\b",
    re.IGNORECASE,
)
_WH_INVERSION = re.compile(
    rf"^{_OPEN}(?:{_WH})\s+(?:(?:{_DEGREE})\s+)?(?:{_DE_VERB}|{_EN_AUX})\b",
    re.IGNORECASE,
)
_INDIRECT = re.compile(
    rf"^{_OPEN}{_COORD_OPT}(?:ob|whether|if)\b",
    re.IGNORECASE,
)
# "do not" / "don't" is the negation dummy, not subject-auxiliary inversion.
# "do you need backup?" is a question; "do not need backup" is a denial.
_NEGATED_DO = re.compile(
    rf"^{_OPEN}{_COORD_OPT}(?:do not|does not|don'?t|doesn'?t)\b",
    re.IGNORECASE,
)
# Comma-joined clauses are separate ("Ich habe Drehstrom, ist das möglich?").
# A comma between digits stays in the number ("12,5", "12,000"). A dot
# followed by a digit stays in the number ("4.500", "12.5"). The terminator
# stays on the clause so a question mark still marks that clause only.
_SPLIT = re.compile(r"([?!;\n]|\.(?!\d)|(?<!\d),(?!\d))")

_Polarity = Literal["pos", "neg", "unsure"]


def stated_size_hint(message: str | Sequence[str]) -> dict[str, Any]:
    """The size-hint object a configurator URL may be built from (#365).

    A string is one message. A sequence is the conversation's user messages
    in order. A later message overrides the same field. A later denial
    removes phase and sets backup to ``none``. Callers pass this dict on
    and drop whatever object they were given. A catalogue fact is not a
    source (docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md §1.12;
    the read stays deterministic, §1.1).

    A negated backup word is ``none`` (SizeHint.php's enum). Omitting it
    would drop a decision the customer made. A negated phase word sets
    nothing and does not flip to the other phase. When a clause holds both
    a negation and an affirmative marker and neither governs the keyword,
    the field is left out. An interrogative clause does not set phase or
    backup. A figure or a postcode in that clause is still read.
    """
    texts = (message,) if isinstance(message, str) else tuple(message)
    found: dict[str, Any] = {}
    for text in texts:
        _read_message(text, found)
    return found


def sizing_input(message: str) -> dict[str, Any]:
    """The five size-hint fields this message states (spec 13 §A)."""
    found: dict[str, Any] = {}
    _read_message(message, found)
    return found


def _read_message(message: str, found: dict[str, Any]) -> None:
    """Fold one user message into ``found``.

    Phase and backup are decided per clause, so a question mark or a
    leading verb suppresses only the clause it governs. Figures and the
    postcode are read from the whole message: a comma in "6000 kWh, jährlich"
    is not a second sentence, and a question still carries the kWp the
    customer gave.
    """
    for clause, interrogative in _clauses(message):
        if interrogative:
            continue
        _read_phase(clause, found)
        _read_backup(clause, found)
    _read_kwp(message, found)
    _read_annual(message, found)
    _read_plz(message, found)


def _clauses(message: str) -> list[tuple[str, bool]]:
    pieces = _SPLIT.split(message)
    clauses: list[tuple[str, bool]] = []
    pending = ""
    for index, piece in enumerate(pieces):
        pending += piece
        if index % 2 == 0 and index + 1 < len(pieces):
            continue
        text = pending.strip()
        pending = ""
        if text:
            clauses.append((text, _is_question(text)))
    return clauses


def _is_question(text: str) -> bool:
    if "?" in text:
        return True
    flat = _flat(text)
    if _NEGATED_DO.search(flat):
        return False
    return (
        _VERB_FIRST.search(flat) is not None
        or _WH_INVERSION.search(flat) is not None
        or _INDIRECT.search(flat) is not None
    )


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
    """True when ``separator`` groups thousands, not a decimal.

    A thousands group is three digits and the head group is one to three
    ("4.500", "12,000"). One or two digits after the separator are a
    decimal ("12,5", "12.5").
    """
    parts = text.split(separator)
    if len(parts) > 2:
        return True
    return len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3


def _polarity(text: str, start: int, end: int) -> _Polarity:
    """Whether the keyword at [start, end) is stated, denied, or unclear.

    ``pos`` writes the field, ``neg`` denies it, ``unsure`` leaves it out.
    The look is the clause, in words: a character budget drops a negation
    that sits three long compounds away.
    """
    before = _flat(text[:start])
    after = _flat(text[end:])
    if _NOT_ONLY.search(before):
        return "unsure"
    # "mit" / "with" on the keyword wins when the negation governs another
    # noun ("ohne Netz und mit Notstrom"). "nicht mit" denies it.
    if _WITH.search(before):
        if _NEG_ON_WITH.search(before):
            return "neg"
        return "pos"
    if _DIRECT_BEFORE.search(before) or _DIRECT_AFTER.search(after):
        return "neg"
    clause = _flat(text)
    affirm = _AFFIRM.search(clause) is not None
    if _window_negated(before, after):
        # The negation is near the keyword but a content word sits between
        # it and an affirmative marker ("kein Problem ich brauche Notstrom").
        # Guessing "none" is the failure this branch avoids.
        return "unsure" if affirm else "neg"
    if affirm and _ANY_NEG.search(clause):
        return "unsure"
    return "pos"


def _window_negated(before: str, after: str) -> bool:
    return (
        _NEG_BEFORE.search(before) is not None or _NEG_AFTER.search(after) is not None
    )


def _flat(text: str) -> str:
    """Curly apostrophes as ``'``, so U+2019 in "don't" matches the straight mark."""
    return text.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")


def _read_kwp(text: str, found: dict[str, Any]) -> None:
    for match in _KWP.finditer(text):
        token = match.group("num")
        if token is None:
            continue
        value = _parse_number(token)
        if value is not None and 0 < value <= _MAX_KWP:
            found["pv_kwp"] = value


def _read_annual(text: str, found: dict[str, Any]) -> None:
    hits: list[tuple[int, str]] = []
    for pattern in (_ANNUAL_BEFORE, _ANNUAL_AFTER):
        hits.extend(
            (match.start(), match.group("num"))
            for match in pattern.finditer(text)
            if match.group("num") is not None
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
        polarity = _polarity(text, start, end)
        if polarity == "neg":
            if found.get("phase") == phase:
                del found["phase"]
            continue
        if polarity == "unsure":
            continue
        found["phase"] = phase


def _read_backup(text: str, found: dict[str, Any]) -> None:
    for match in _BACKUP.finditer(text):
        polarity = _polarity(text, match.start(), match.end())
        if polarity == "unsure":
            continue
        # ``none`` is a value the customer stated. The form's backup enum is
        # none / needed / needed_accessory_ok (SizeHint.php).
        found["backup"] = "none" if polarity == "neg" else "needed"


def _read_plz(text: str, found: dict[str, Any]) -> None:
    for match in _PLZ.finditer(text):
        code = match.group("after") or match.group("before")
        if code:
            found["plz"] = code
