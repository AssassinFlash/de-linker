"""Storage spelling for a finished derived diagnostic, not a model input.

macOS libm and glibc need not agree in the last bit of a transcendental result.
That disagreement belongs to the derived witness text. It is not removed by
coarsening solar position, Perez inputs, DC, the AC profile or energy.

IEEE 754-2008 binary64 has p = 53. digits10 = floor((p - 1) * log10(2)) = 15:
a decimal with at most that many significant digits survives conversion to
binary64 and back. Recovering every original binary64 needs max_digits10 = 17;
this derived diagnostic does not claim that identity, engineering accuracy or
a tolerance. The chosen decimal is converted to the stored binary64, whose
shortest JSON spelling may use exponent notation. ``canonical.encode`` remains
the only JSON encoder.

Original weather and other retained inputs stay exact. A worker with the same
code and the same environment replays those inputs in full. The spelled float
must not be read back into any calculation.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from decimal import ROUND_HALF_EVEN, Decimal

# IEEE 754-2008 binary64 digits10. p = 53, so floor(52 * log10(2)) = 15.
DERIVED_WITNESS_DIGITS10 = 15


def _shortest_digits10(value: float) -> str:
    """Shortest fixed-point spelling with at most 15 significant digits."""
    exact = Decimal.from_float(value)
    quantum = Decimal(1).scaleb(exact.adjusted() - (DERIVED_WITNESS_DIGITS10 - 1))
    # IEEE default rounding. A tie does not walk away from even.
    rounded = exact.quantize(quantum, rounding=ROUND_HALF_EVEN)
    spelling = format(rounded, "f")
    if "." in spelling:
        spelling = spelling.rstrip("0").rstrip(".")
    if spelling in {"", "-", "-0"}:
        return "0"
    return spelling


def derived_witness_number(value: float) -> float:
    """Binary64 named by the digits10 spelling, with signed zero stored as +0.

    The result is a storage spelling of an already computed diagnostic. Callers
    must not multiply, transpose or integrate it.
    """
    number = float(value)
    if number == 0.0:
        return 0.0
    if not math.isfinite(number):
        raise ValueError("derived witness spelling requires a finite number")
    spelled = float(_shortest_digits10(number))
    return 0.0 if spelled == 0.0 else spelled


def derived_witness_numbers(values: Iterable[float]) -> list[float]:
    return [derived_witness_number(float(item)) for item in values]
