"""Figures of a document chunk: every number, tagged so an answer can cite it by ID.

The model never writes a number (docs/specs/13-genie.md); a number from a document
travels as `{fact:CHUNK_ID.nK}` and hydration fills the value the chunk states
(AGENTS.md §4: "模型只能引用检索块 ID，数字由服务端填入"). `tag` rewrites a chunk's text
for the model with each figure shown in place as `[nK=VALUE]`, and returns the
`CHUNK_ID.nK -> VALUE` table the facts of the turn are made of. The value is the
figure as the document prints it, with the unit written right after it, so a
hydrated answer reads "20000 Wp", never a bare "20000".

A figure is a number standing on its own (a datasheet cell "3", a range end "180 - 900",
"≥ 1500 mm"), a number glued to a unit ("10mm", "5-108kWh"), or a date (2026-01-01,
01.01.2026, "1 st January 2026", "1. Januar 2026"). A word that carries a model code is left whole: a segment mixing letters
and digits that is not a number with a unit (H2-10K-T3, CB2-100.3-HV5, GW10K-ET) makes
the word a name, and a name is written plainly, never as a placeholder. In a table
row whose label cell names a unit ("| Nominal Capacity (kWh) | 260 |"), a figure
without its own unit takes the row's: "260 kWh".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from unicodedata import category

# Units a datasheet, manual or warranty writes after a number, longest spelling
# first so "kWh" is not read as "kW" + "h". German and English, as the hosted
# documents use both. No bare "K": in these documents it is the kilo of a model code
# (10K), not a kelvin.
_UNITS = (
    "kWh", "MWh", "Wh", "kWp", "Wp", "kVAr", "kVA", "kW", "MW", "VA", "W",
    "mAh", "Ah", "mA", "A", "kV", "mV", "Vdc", "Vac", "V",
    "mm²", "mm2", "mm", "cm", "km", "m²", "m",
    "kg", "g", "°C", "℃", "%", "kHz", "Hz", "ms", "min", "s", "h",
    "dB(A)", "dBA", "dB", "Nm", "kPa", "Pa",
    "years", "year", "months", "month", "Jahren", "Jahre", "Jahr", "Monaten",
    "Monate", "Monat", "weeks", "week", "Wochen", "Woche", "days", "day", "Tagen",
    "Tage", "Tag", "cycles", "Zyklen", "tons", "ton", "Tonnen", "t",
)  # fmt: skip
_UNIT = "|".join(re.escape(unit) for unit in sorted(_UNITS, key=len, reverse=True))
# A number, with its thousands grouped or not ("1,680.00", "1.680,00", "20000", "3.552").
_NUMBER = r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
# A word: what stands between spaces and table or bracket marks.
_WORD = re.compile(r"[^\s|()\[\]{}]+")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}\.\d{1,2}\.\d{4}")
# Inside a word: a number not continuing another, with the unit glued to it.
_IN_WORD = re.compile(rf"(?<![\d.,]){_NUMBER}(?:{_UNIT})?(?![\d])")
_NUMBER_UNIT = re.compile(rf"{_NUMBER}(?:{_UNIT})")
_LONE_UNIT = re.compile(rf"(?:{_UNIT})[.,:;]?")
# A JSON string may close immediately after its known unit. Only the unit
# belongs to the figure; the closing quote and punctuation stay in the text.
_FOLLOWING_UNIT = re.compile(rf'({_UNIT})"?[.,:;]?')
# A written-out date is one figure: the warranty table's "produced on/after 1 st
# January 2026" (issue #257) loses its meaning as "1" and "2026".
_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|"
    "December|Januar|Jänner|Februar|März|Mai|Juni|Juli|Oktober|Dezember"
)
_DATE_PHRASE = re.compile(
    rf"\b\d{{1,2}}(?:\s?(?:st|nd|rd|th)|\.)?\s(?:{_MONTHS})\s\d{{4}}\b"
    rf"|\b(?:{_MONTHS})\s\d{{1,2}}(?:st|nd|rd|th)?,?\s\d{{4}}\b"
)
# A manufacturer's deadline can be written as words rather than digits. Keep
# that exact source phrase as a fact; never synthesize a numeral from it.
_WRITTEN_MONTH = re.compile(r"\b(?:one\s+month|eines\s+Monats)\b", re.IGNORECASE)
_TRIM = ".,:;!?"
_MARKS = "≥≤<>~±+−≈*'\"„“”"


@dataclass(frozen=True)
class Tagged:
    """A chunk's text as the model reads it, and the values of its figures."""

    text: str
    figures: dict[str, str]


def figure_id(chunk_id: str, number: int) -> str:
    """The fact ID of a chunk's `number`-th figure, counted from 1."""
    return f"{chunk_id}.n{number}"


def tag(
    chunk_id: str, text: str, *, excluded_spans: tuple[tuple[int, int], ...] = ()
) -> Tagged:
    """Tag figures, leaving explicitly protected source annotations untouched.

    A qualified table's original footnotes and their page labels are source
    context, not additional table values. Their spans are supplied by the
    knowledge tool after it has checked the projection's source metadata.
    """
    phrases = [
        *(match.span() for match in _DATE_PHRASE.finditer(text)),
        *(match.span() for match in _WRITTEN_MONTH.finditer(text)),
    ]
    if chunk_id.startswith("be0569b4602a-p1-hs3-warranty-terms-"):
        phrases.extend(
            match.span() for match in re.finditer(r"\b(?:Ten years|Six months)\b", text)
        )
    spans: list[tuple[int, int]] = list(phrases)
    words = list(_WORD.finditer(text))
    skip_to = -1
    for index, word in enumerate(words):
        if (
            word.start() < skip_to
            or any(start <= word.start() < end for start, end in phrases)
            or is_code(word.group(0))
        ):
            continue
        bare = word.group(0).rstrip(_TRIM)
        date = _DATE.fullmatch(bare.lstrip(_MARKS))
        if date:
            offset = word.start() + len(bare) - len(bare.lstrip(_MARKS))
            spans.append((offset, offset + len(date.group(0))))
            continue
        found = list(_IN_WORD.finditer(word.group(0)))
        for position, match in enumerate(found):
            start, end = word.start() + match.start(), word.start() + match.end()
            # A sign is unary at the word's start or after a non-alphanumeric
            # boundary, including comparisons, quotes and range punctuation.
            # A sign directly after the previous complete figure is a binary
            # separator instead: both 180-900 and 40℃-60℃ have positive ends.
            sign = match.start() - 1
            if (
                sign >= 0
                and word.group(0)[sign] in "-−+"
                and (
                    sign == 0
                    or (
                        not word.group(0)[sign - 1].isalnum()
                        and (position == 0 or found[position - 1].end() != sign)
                    )
                )
            ):
                start -= 1
            last = position == len(found) - 1
            following = words[index + 1] if index + 1 < len(words) else None
            following_unit = (
                _FOLLOWING_UNIT.fullmatch(following.group(0))
                if following is not None
                else None
            )
            if (
                last
                and following is not None
                and match.end() == len(bare)
                and not _NUMBER_UNIT.fullmatch(match.group(0))
                and text[end : following.start()] == " "
                and following_unit is not None
            ):
                # "20000 Wp": the unit is the next word.
                end = following.start() + len(following_unit.group(1))
                skip_to = following.end()
            spans.append((start, end))
    figures: dict[str, str] = {}
    parts: list[str] = []
    cursor = 0
    for start, end in sorted(spans):
        if any(start < stop and begin < end for begin, stop in excluded_spans):
            continue
        number = len(figures) + 1
        value = text[start:end] + _row_unit(text, start, text[start:end])
        figures[figure_id(chunk_id, number)] = value
        parts.append(text[cursor:start])
        parts.append(f"[n{number}={value}]")
        cursor = end
    parts.append(text[cursor:])
    return Tagged("".join(parts), figures)


def _row_unit(text: str, start: int, value: str) -> str:
    """ " UNIT" when the figure stands in a table row and a cell to its left names a
    unit in brackets ("Nominal Capacity (kWh)", "Rated Input Power(W)" after a group
    cell), and the figure carries none of its own. The nearest such cell counts."""
    if not re.fullmatch(rf"[-−+]?{_NUMBER}", value):
        return ""
    line_start = text.rfind("\n", 0, start) + 1
    if not text[line_start:start].lstrip().startswith("|"):
        return ""
    cells = text[line_start:start].split("|")[1:-1]
    for cell in reversed(cells):
        unit = re.search(rf"[\[(]({_UNIT})[\])]", cell)
        if unit:
            return f" {unit.group(1)}"
    return ""


def is_code(word: str) -> bool:
    """Whether a word names a model: a segment mixes letters and digits and is not
    a number with its unit."""
    for segment in re.split(r"[-−/–_]", word.strip(_TRIM)):
        # Quoted measurements still name a number and unit. Unicode punctuation
        # covers typographic quotes too, without a finite quote allowlist.
        while segment and (
            segment[0] in _MARKS or category(segment[0]).startswith("P")
        ):
            segment = segment[1:]
        while segment and (
            segment[-1] in _MARKS or category(segment[-1]).startswith("P")
        ):
            segment = segment[:-1]
        if (
            re.search(r"[A-Za-z]", segment)
            and re.search(r"\d", segment)
            and not _NUMBER_UNIT.fullmatch(segment)
        ):
            return True
    return False


# Only the grid-code the documents print as a hyphenated name: `VDE-AR-N 4105`
# and the model's `VDE-AR-N [n4=4105]`. The bracket span covers the fact index
# as well as 4105. A hyphenated measurement (`Start-up 400`, `single-phase 10`,
# `grid-code 4105`) is not this code. The number must be its own word: `4105kWh`
# stays a figure.
_REGULATION_CODE_TAIL = re.compile(
    r"(?i)\bVDE-AR-N[ \t]+"
    r"(?:(\[n\d+=[0-9]+(?:[.,][0-9]+)?\])"
    r"|([0-9]+(?:[.,][0-9]+)?))(?!\w)"
)
# Clause labels a grid rule uses. `Art` is German for type, `Satz` and `Nr.`
# introduce a measurement, and `Methode` / `Schritt` are steps. None of those
# is a clause. A lone `§` is a label, not a mark: `§ 400` is still a figure.
_CLAUSE_LABEL = re.compile(r"(?i)^(?:abs\.?|absatz|abschnitt|clause|§)$")
# The window that makes a clause number a regulation reference, not a step.
_REGULATION_MARK = re.compile(r"(?i)(?:\benwg\b|\beeg\b|\bvde\b|\b14a\b)")
# A dotted clause (`5.7.4.1`) is one number. A smashed tail (`1-500`) is not:
# the hyphen stops the match, so the extra digits stay a figure.
_CLAUSE_DIGITS = re.compile(r"[0-9]+(?:[.,][0-9]+)*")
_DIGIT_RUN = re.compile(r"\d+(?:[.,]\d+)*")
# Words of context around a clause label. Far enough for `EnWG 14a Abs. 1`,
# not so far that an earlier EnWG licenses a later step number.
_REGULATION_WINDOW = 8


def _unit_word(word: str) -> bool:
    """True when `word` is a unit or a number glued to one (`230 V`, `10kW`)."""
    core = word.strip(".,;:()[]")
    return bool(core) and (
        _NUMBER_UNIT.fullmatch(core) is not None
        or _LONE_UNIT.fullmatch(core) is not None
    )


def regulation_number_spans(text: str) -> list[tuple[int, int]]:
    """Digit spans that name a regulation, not a measurement (#443).

    `VDE-AR-N 4105` keeps 4105. `EnWG 14a Abs. 1` and `Abschnitt 5.7.4.1` keep
    the clause number when EnWG, EEG, VDE or `14a` is in the same short window.
    `4105 kWh`, `Start-up 400`, `Art 10 kW`, `Abs. 230 V`, `§ 400`, `Methode 1`
    and a detached `4105` are not regulation numbers. `14a` itself is a
    model-code word (`is_code`) and is not a span here.
    """
    spans: list[tuple[int, int]] = []
    for match in _REGULATION_CODE_TAIL.finditer(text):
        if match.group(1):
            spans.append(match.span(1))
        elif match.group(2):
            spans.append(match.span(2))
    words = list(re.finditer(r"\S+", text))
    for index, word in enumerate(words):
        label = word.group().strip(".,;:()[]")
        if not _CLAUSE_LABEL.fullmatch(label):
            continue
        if index + 1 >= len(words):
            continue
        number = words[index + 1]
        if is_code(number.group()) or _unit_word(number.group()):
            continue
        following = words[index + 2].group() if index + 2 < len(words) else ""
        if following and _unit_word(following):
            continue
        digits = _CLAUSE_DIGITS.search(number.group())
        if digits is None:
            continue
        start = words[max(0, index - _REGULATION_WINDOW)].start()
        end = words[min(len(words) - 1, index + 1 + _REGULATION_WINDOW)].end()
        if not _REGULATION_MARK.search(text[start:end]):
            continue
        spans.append((number.start() + digits.start(), number.start() + digits.end()))
    return spans


def digits_are_regulation(
    text: str,
    start: int,
    end: int,
    spans: list[tuple[int, int]] | None = None,
) -> bool:
    """True when every digit run in the slice sits wholly inside a regulation span.

    Overlap is not enough. `VDE-AR-N 4105/600` and `EnWG 14a Abs. 1-500` name a
    regulation and a measurement in one word; the measurement stays a figure.
    """
    if spans is None:
        spans = regulation_number_spans(text)
    runs = list(_DIGIT_RUN.finditer(text[start:end]))
    if not runs:
        return False
    return all(
        any(
            span_start <= start + run.start() and start + run.end() <= span_end
            for span_start, span_end in spans
        )
        for run in runs
    )


def chunk_of(fact_id: str) -> str | None:
    """The chunk ID inside a figure's fact ID, or None for any other fact."""
    match = re.fullmatch(r"(.+)\.n\d+", fact_id)
    return match.group(1) if match else None


# Word units and month names in the other language of the turn. A figure keeps the
# document's spelling except for these words: an English warranty quoted in a German
# answer reads "10 Jahre", not "10 years" (issue #257 trial run).
_WORDS = {
    "de": {
        "years": "Jahre", "year": "Jahr", "months": "Monate", "month": "Monat",
        "cycles": "Zyklen", "tons": "Tonnen", "ton": "Tonne", "weeks": "Wochen",
        "week": "Woche", "days": "Tage", "day": "Tag",
    },
    "en": {
        "Jahren": "years", "Jahre": "years", "Jahr": "year", "Monaten": "months",
        "Monate": "months", "Monat": "month", "Zyklen": "cycles", "Tonnen": "tons",
        "Wochen": "weeks", "Woche": "week", "Tagen": "days", "Tage": "days",
        "Tag": "day",
    },
}  # fmt: skip
_MONTH_NAMES = {
    "en": (
        "January", "February", "March", "April", "May", "June", "July", "August",
        "September", "October", "November", "December",
    ),
    "de": (
        "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
        "September", "Oktober", "November", "Dezember",
    ),
}  # fmt: skip
_MONTH_NUMBER = {
    name.lower(): number
    for names in _MONTH_NAMES.values()
    for number, name in enumerate(names, start=1)
} | {"jänner": 1}


def localize(value: str, locale: str, *, source_id: str = "") -> str:
    """A figure's value in the turn's language: word units and written dates."""
    language = "de" if locale.startswith("de") else "en"
    if (
        language == "de"
        and source_id.startswith("be0569b4602a-p1-hs3-warranty-terms-")
        and value in {"Ten years", "Six months"}
    ):
        return {"Ten years": "zehn Jahre", "Six months": "sechs Monate"}[value]
    if language == "de" and value.casefold() == "one month":
        return "1 Monat"
    if _DATE_PHRASE.fullmatch(value):
        day = re.search(r"\d{1,2}(?!\d)", value)
        year = re.search(r"\d{4}", value)
        month = re.search(_MONTHS, value)
        if day and year and month:
            name = _MONTH_NAMES[language][_MONTH_NUMBER[month.group(0).lower()] - 1]
            if language == "de":
                return f"{int(day.group(0))}. {name} {year.group(0)}"
            return f"{int(day.group(0))} {name} {year.group(0)}"
    for word, other in _WORDS[language].items():
        value = re.sub(rf"(?<=\d)(\s?){word}\b", rf"\g<1>{other}", value)
    return value


# Currencies a price list or an offer writes beside an amount: the symbols and ISO
# codes of the currencies of the EU, the UK, Switzerland and the makers' China
# (de-linker.com sells in the EU; registration is open to every country, owner
# 2026-10-17, Europe first).
CURRENCY = (
    r"(?:€|EUR|Euro|US\$|USD|\$|£|GBP|CHF|Fr\.|CNY|RMB|¥|PLN|zł|CZK|Kč|HUF|Ft|"
    r"SEK|DKK|NOK|RON|BGN)"
)
_TAG = re.compile(r"\[(n\d+)=([^\]]*)\]")
_AMOUNT_BEFORE = re.compile(rf"{CURRENCY}\s?\[(n\d+)=([^\]]*)\]")
_AMOUNT_AFTER = re.compile(rf"\[(n\d+)=([^\]]*)\]\s?{CURRENCY}(?![A-Za-z])")
AMOUNT = re.compile(rf"(?:^|\s){CURRENCY}(?:\s|$)|^{CURRENCY}|{CURRENCY}$")


def borrow_units(tagged: Tagged) -> Tagged:
    """Each figure without a unit takes the unit its line names for it.

    A nameplate prints one unit for a pair or a range ("12.5/12.5 A", "200 ... 850
    Vdc") and a label may name the unit in brackets ("Max. input current (A): 12.5");
    without it an answer read "bei 12.5" (review round 1 of PR #309, item 9). The
    unit is the next figure's on the same line, else a bracketed unit before it.
    """
    figures = dict(tagged.figures)
    for line in tagged.text.split("\n"):
        found = list(_TAG.finditer(line))
        for index, match in enumerate(found):
            name, value = match.group(1), match.group(2)
            if not re.fullmatch(rf"[-−+]?{_NUMBER}", value):
                continue
            unit = next(
                (
                    tail.group(1)
                    for later in found[index + 1 :]
                    if (tail := re.search(rf"\s({_UNIT})$", later.group(2)))
                ),
                None,
            )
            if unit is None:
                named = re.findall(rf"[\[(]({_UNIT})[\])]", line[: match.start()])
                unit = named[-1] if named else None
            if unit is not None:
                fact_id = _fact_of(figures, name)
                if fact_id is not None:
                    figures[fact_id] = f"{value} {unit}"
    return _retagged(tagged.text, figures)


def mark_amounts(tagged: Tagged) -> Tagged:
    """An amount of money keeps its currency in its value ("1,680.00 €").

    A figure is an amount when a currency stands right before or after it, or when
    its line names a currency and the figure carries no unit of its own (a price
    list's row "| GW10K-ET | 1.680,00 | EUR |").
    """
    figures = dict(tagged.figures)

    def keep(name: str, value: str, currency: str) -> None:
        fact_id = _fact_of(figures, name)
        if fact_id is not None and not AMOUNT.search(value):
            figures[fact_id] = f"{value} {currency}"

    for line in tagged.text.split("\n"):
        for match in _AMOUNT_BEFORE.finditer(line):
            keep(
                match.group(1), match.group(2), match.group(0).split("[", 1)[0].strip()
            )
        for match in _AMOUNT_AFTER.finditer(line):
            keep(
                match.group(1), match.group(2), match.group(0).rsplit("]", 1)[1].strip()
            )
        named = re.search(rf"(?<![A-Za-z]){CURRENCY}(?![A-Za-z])", _TAG.sub("", line))
        if named:
            for match in _TAG.finditer(line):
                if re.fullmatch(_NUMBER + r"(?:[.,]\d+)*", match.group(2)):
                    keep(match.group(1), match.group(2), named.group(0))
    return _retagged(tagged.text, figures)


def _fact_of(figures: dict[str, str], name: str) -> str | None:
    return next((key for key in figures if key.endswith("." + name)), None)


def _retagged(text: str, figures: dict[str, str]) -> Tagged:
    """`text` with each tag showing its figure's value from `figures`."""

    def show(match: re.Match[str]) -> str:
        fact_id = _fact_of(figures, match.group(1))
        return f"[{match.group(1)}={figures[fact_id] if fact_id else match.group(2)}]"

    return Tagged(_TAG.sub(show, text), figures)


_SWAP = str.maketrans(".,", ",.")


def swap_decimals(value: str, mark: str, locale: str) -> str:
    """A figure in the turn's language: "12.5 A" reads "12,5 A" in German.

    `mark` is the decimal mark of the text the figure comes from, "" when that
    text wrote no decimal number at all: its separators are thousands marks, and
    converting them blind turns "3,552 kWh" into a three-decimal "3.552" a German
    reader takes for 3552 (review round 1 of PR #309, item 9). When the turn's
    language writes the other mark, the decimal and thousands marks trade places
    ("1,680.00" ↔ "1.680,00"). Dates keep their dots.
    """
    wanted = "," if locale.startswith("de") else "."
    if mark not in (".", ",") or mark == wanted or _DATE.search(value):
        return value
    return re.sub(
        r"\d[\d.,]*\d",
        lambda m: m.group(0).translate(_SWAP),
        value,
    )
