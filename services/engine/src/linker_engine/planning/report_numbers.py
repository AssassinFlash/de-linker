"""One display format for report values, so sections cannot drift apart.

Frozen sources keep full precision; this module exists only because sections
had each grown their own convention. The report's established look is three
decimals, but a bare three decimals destroys the coefficients this report is
built on: -0.0029 °/C became -0.003 and a 0.1805 h irradiance offset became
0.18. One section therefore printed raw floats instead, which is how the same
report came to show 9315.200808684325 kWh beside 9,315.201 kWh, and a German
report came to carry English decimal points in one of its sections.

The rule is stated once, here: **three decimals, extended when a value needs
more digits to keep six significant ones**. Ordinary quantities keep exactly
the display they had, small coefficients keep their digits, and every section
reaches the same answer for the same number.
"""

from __future__ import annotations

import math

from .canonical import Json

# The typographic range the report copy already uses between two ends.
RANGE = " – "

# The established quantity resolution, and the significant digits a value
# below 1 needs before that resolution would round it away.
DECIMALS = 3
SIGNIFICANT = 6

_MARKS = {"en": (",", "."), "de": (".", ",")}


def _group(digits: str, locale: str) -> str:
    thousands = _MARKS["de" if locale == "de" else "en"][0]
    return thousands.join(
        [digits[max(0, index - 3) : index] for index in range(len(digits), 0, -3)][::-1]
    )


def _decimal(shown: str, locale: str) -> str:
    """Group the integer part, then use this locale's decimal mark."""
    decimal = _MARKS["de" if locale == "de" else "en"][1]
    if "e" in shown or "E" in shown:
        # A magnitude outside the plain range keeps its exponent; grouping a
        # mantissa would misstate the value.
        return shown.replace(".", decimal)
    sign = ""
    if shown.startswith("-"):
        sign, shown = "-", shown[1:]
    whole, _, fraction = shown.partition(".")
    whole = _group(whole, locale)
    return f"{sign}{whole}{decimal}{fraction}" if fraction else f"{sign}{whole}"


def _places(value: float) -> int:
    """Three decimals, and more only where three would round a value away.

    A quantity of 1 or more is shown exactly as the report always showed it. A
    fraction below 1 keeps six significant digits instead, because that is the
    scale the report's own coefficients live on: -0.0029 °/C, a 0.1805 h
    irradiance offset, and a 0.9637 conversion factor all round to nothing at
    three decimals.
    """
    if value == 0 or not math.isfinite(value):
        return DECIMALS
    if abs(value) >= 1:
        return DECIMALS
    exponent = math.floor(math.log10(abs(value)))
    return max(DECIMALS, SIGNIFICANT - 1 - exponent)


def significant(value: Json, locale: str) -> str:
    """The report's display resolution, in this locale's own convention."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    if isinstance(value, int):
        # A module count, a year or an interval count is not rounded, and it
        # does not acquire a fractional part from the display format.
        return _group(str(value), locale)
    places = _places(value)
    if places > SIGNIFICANT:
        # A magnitude such as a 1e-12 diode current would need more zeros than
        # a reader can count, so it keeps the exponent notation this report
        # already used for those values.
        return _decimal(f"{value:.{SIGNIFICANT}g}", locale)
    shown = f"{value:.{places}f}".rstrip("0").rstrip(".")
    return _decimal(shown if shown not in ("", "-") else "0", locale)


def percent(value: Json, locale: str) -> str:
    """A ratio already scaled to percent, at the same resolution."""
    shown = significant(value, locale)
    return f"{shown} %" if shown != "—" else shown


def number(value: Json, locale: str, unit: str = "") -> str:
    """One value with its optional unit; non-numbers are shown as unavailable."""
    shown = significant(value, locale)
    return f"{shown} {unit}" if unit and shown != "—" else shown


def span(start: Json, end: Json, locale: str) -> str:
    """A two-ended range whose ends share one locale convention.

    Timestamps are shown verbatim: their separators are not decimal points.
    """
    if isinstance(start, str) and isinstance(end, str):
        return start + RANGE + end
    return significant(start, locale) + RANGE + significant(end, locale)
