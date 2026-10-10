"""Reading datasheet values as they are stored in the feed's figures.

Figures keep the datasheet's own spelling ("120~950", "21/21/21/21", "42 × 8",
"6 (Floor mounted) / 3 (Wall mounted)"); #8 keeps the unit as stored and
leaves conversion to the reader (docs/specs/8-engineering-data.md, target
shape 1). Conversion follows the unit only, as #7 does for the facts it
derives: W and Wp divide by 1000, kW and kWp stay; nothing is guessed from the
size of a number. A value these functions cannot read is `None`, never a
default.
"""

from __future__ import annotations

import re

_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")
_RANGE = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*(?:~|–|-|to)\s*(-?\d+(?:[.,]\d+)?)")
_TIMES = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*[×x*]\s*(\d+)\s*$")

_TO_KILO = {"w": 0.001, "wp": 0.001, "va": 0.001, "kw": 1.0, "kwp": 1.0, "kva": 1.0}
_TO_KWH = {"wh": 0.001, "kwh": 1.0}


def _float(text: str) -> float:
    return float(text.replace(",", "."))


def number(value: str | float | int | None) -> float | None:
    """The first number in a stored value ("57.5±1" -> 57.5, "10" -> 10.0)."""
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    match = _NUMBER.search(value.replace(" ", ""))
    return _float(match.group(0)) if match else None


def number_range(value: str | float | int | None) -> tuple[float, float] | None:
    """A "low~high" or "low-high" span ("120~950", "160 ~ 1000", "180-900")."""
    if value is None or isinstance(value, int | float):
        return None
    match = _RANGE.search(value)
    if not match:
        return None
    low, high = sorted((_float(match.group(1)), _float(match.group(2))))
    return low, high


def per_input(
    value: str | float | int | None, count: int | None = None
) -> list[float] | None:
    """One value per MPPT: "21/21/42/42", "42 × 8", or a single value for all inputs.

    A single value is repeated `count` times when the number of inputs is known.
    """
    if value is None:
        return None
    if isinstance(value, int | float):
        return [float(value)] * (count or 1)
    times = _TIMES.match(value)
    if times:
        return [_float(times.group(1))] * int(times.group(2))
    if "/" in value:
        parts = [number(part) for part in value.split("/")]
        if all(part is not None for part in parts):
            return [part for part in parts if part is not None]
        return None
    single = number(value)
    if single is None:
        return None
    return [single] * (count or 1)


def kilo(value: str | float | int | None, unit: str | None) -> float | None:
    """A power in kW (or kVA) from W, Wp, VA, kW, kWp or kVA; other units -> None."""
    factor = _TO_KILO.get((unit or "").strip().lower())
    amount = number(value)
    if factor is None or amount is None:
        return None
    return round(amount * factor, 6)


def kwh(value: str | float | int | None, unit: str | None) -> float | None:
    """An energy in kWh from Wh or kWh; other units -> None."""
    factor = _TO_KWH.get((unit or "").strip().lower())
    amount = number(value)
    if factor is None or amount is None:
        return None
    return round(amount * factor, 6)


def count(value: str | float | int | None) -> int | None:
    """A whole count; for "6 (Floor mounted) / 3 (Wall mounted)" the first option."""
    amount = number(value)
    if amount is None or amount < 0 or amount != int(amount):
        return None
    return int(amount)
