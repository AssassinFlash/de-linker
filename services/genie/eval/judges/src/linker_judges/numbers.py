"""Values as datasheets print them, and the exact rewritings the answers use."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

_NUMBER = re.compile(r"^(?P<num>\d+(?:\.\d+)?)")

# Exact conversions only: an answer that rounds would stop being a correct paraphrase.
_SCALE = {
    "Wp": ("kWp", Decimal("0.001")),
    "W": ("kW", Decimal("0.001")),
    "VA": ("kVA", Decimal("0.001")),
    "kW": ("W", Decimal("1000")),
    "kWp": ("Wp", Decimal("1000")),
    "kWh": ("Wh", Decimal("1000")),
}
_SPELLED = {
    "en": {"A": "amperes", "V": "volts", "kg": "kilograms"},
    "de": {"A": "Ampere", "V": "Volt", "kg": "Kilogramm"},
}
_COUNT_WORDS = {
    "en": [
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
    ],
    "de": [
        "null",
        "eins",
        "zwei",
        "drei",
        "vier",
        "fünf",
        "sechs",
        "sieben",
        "acht",
        "neun",
    ],
}


@dataclass(frozen=True)
class Quantity:
    """A printed number (decimals kept as printed) and its unit ("" for a count)."""

    text: str
    unit: str

    @property
    def value(self) -> Decimal:
        return Decimal(self.text)

    @property
    def decimals(self) -> int:
        return len(self.text.split(".")[1]) if "." in self.text else 0


def parse_cell(cell: str, unit: str) -> Quantity:
    """The number at the start of a table cell; footnote marks such as "8.7*2" fall away."""
    match = _NUMBER.match(cell.strip())
    if not match:
        raise ValueError(f"no number in cell {cell!r}")
    return Quantity(match.group("num"), unit)


def _plain(number: Decimal) -> str:
    text = format(number.normalize(), "f")
    return text


def localise(text: str, lang: str, thousands: bool = False) -> str:
    """`text` (a plain number like "15000" or "8.7") in the answer language's style."""
    integer, _, fraction = text.partition(".")
    if thousands and len(integer) > 3:
        groups: list[str] = []
        while integer:
            groups.insert(0, integer[-3:])
            integer = integer[:-3]
        integer = ("," if lang == "en" else ".").join(groups)
    if not fraction:
        return integer
    return integer + ("." if lang == "en" else ",") + fraction


def show(quantity: Quantity, lang: str, thousands: bool = False) -> str:
    """The quantity as an answer states it: "15000 Wp", German "8,7 kWh"."""
    number = localise(quantity.text, lang, thousands)
    return f"{number} {quantity.unit}".strip()


def rewrite(quantity: Quantity, lang: str) -> str:
    """The same value in another unit or spelled out: 15000 Wp -> 15 kWp, 8.7 A -> 8.7 amperes."""
    if quantity.unit in _SCALE:
        unit, factor = _SCALE[quantity.unit]
        number = _plain(quantity.value * factor)
        return f"{localise(number, lang, thousands=True)} {unit}"
    if quantity.unit in _SPELLED[lang]:
        return f"{localise(quantity.text, lang)} {_SPELLED[lang][quantity.unit]}"
    if quantity.unit == "" and quantity.decimals == 0 and quantity.value < 10:
        return _COUNT_WORDS[lang][int(quantity.value)]
    raise ValueError(f"no exact rewriting for {quantity}")


def tamper(quantity: Quantity, avoid: set[Decimal]) -> Quantity:
    """A plausible wrong value: scaled by a fixed factor, never one the table prints.

    `avoid` holds every value of the row, so a tampered answer cannot coincide with
    another model's value (that error class is `wrong_model`).
    """
    if quantity.unit == "" and quantity.decimals == 0:
        for step in (1, 2, -1, 3):
            candidate = quantity.value + step
            if candidate > 0 and candidate not in avoid:
                return Quantity(str(candidate), quantity.unit)
    for factor in ("1.2", "0.8", "1.25", "0.75", "1.5"):
        scaled = (quantity.value * Decimal(factor)).quantize(
            Decimal(1).scaleb(-quantity.decimals)
        )
        if scaled != quantity.value and scaled not in avoid and scaled > 0:
            return Quantity(format(scaled, "f"), quantity.unit)
    raise ValueError(f"no tampered value for {quantity} avoiding {avoid}")
