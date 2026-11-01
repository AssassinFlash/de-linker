"""Storage spelling for a finished derived diagnostic, not a model input.

macOS libm and glibc need not agree in the last bits of a transcendental
result, and numpy dispatches transcendental ufuncs to different SIMD kernels
per host. Measured on the exported preparation fixture (numpy 2.5.3,
pvlib 0.16.1, CPython 3.12; Apple silicon macOS vs x86-64 Ubuntu 24.04),
platform siblings of a derived PV float differ by at most ~3e-12 relative,
with the bulk at 1e-16..1e-15. A witness that stores those floats at
binary64 digits10 therefore hashes differently per platform.

The witness spelling collapses that spread to identical diagnostic spellings:
every float in the derived part of a witness document is spelled
with DERIVED_WITNESS_SIGNIFICANT_DIGITS = 10 significant decimal digits
(ROUND_HALF_EVEN). The decimal quantum is 1e-9 relative, at least 300x
coarser than the measured platform spread, so platform siblings round to
the same decimal and the canonical encoding is byte-identical. The price is
documented: a stored witness float sits within 5e-10 relative (half the
quantum) of its unrounded value. The stored decimal is converted back to
binary64; ``canonical.encode`` remains the only JSON encoder.

Retained inputs and the complete AC and DC watt series are not coarsened.
``canonical_witness_document`` skips the ``inputs`` subtree, which carries
pinned parameters, hashes and retained weather documents that other code
re-verifies against exact bytes, and skips ``available_ac_w`` and
``dc_available_w``, which profile preview, projection and energy replay read
back as their physical output series. The spelled floats must not be read back
into any calculation.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

# Significant decimal digits of a stored witness float. 1e-9 relative
# quantum vs ~3e-12 measured cross-platform spread: >=300x margin.
DERIVED_WITNESS_SIGNIFICANT_DIGITS = 10

# Witness-document subtree whose contents are pinned inputs, not derived
# physics. It stays byte-exact; other code re-verifies its hashes.
WITNESS_INPUTS_KEY = "inputs"
WITNESS_EXACT_SERIES_KEYS = frozenset({"available_ac_w", "dc_available_w"})


def _shortest_significant(value: float) -> str:
    """Shortest fixed-point spelling with at most 10 significant digits."""
    exact = Decimal.from_float(value)
    quantum = Decimal(1).scaleb(
        exact.adjusted() - (DERIVED_WITNESS_SIGNIFICANT_DIGITS - 1)
    )
    # IEEE default rounding. A tie does not walk away from even.
    rounded = exact.quantize(quantum, rounding=ROUND_HALF_EVEN)
    spelling = format(rounded, "f")
    if "." in spelling:
        spelling = spelling.rstrip("0").rstrip(".")
    if spelling in {"", "-", "-0"}:
        return "0"
    return spelling


def derived_witness_number(value: float) -> float:
    """Binary64 named by the 10-significant-digit spelling, -0 stored as +0.

    The result is a storage spelling of an already computed diagnostic. Callers
    must not multiply, transpose or integrate it. Spelling an already spelled
    value returns it unchanged, so a document-level second pass is a fixed
    point and adds no double rounding.
    """
    number = float(value)
    if number == 0.0:
        return 0.0
    if not math.isfinite(number):
        raise ValueError("derived witness spelling requires a finite number")
    spelled = float(_shortest_significant(number))
    return 0.0 if spelled == 0.0 else spelled


def derived_witness_numbers(values: Iterable[float]) -> list[float]:
    return [derived_witness_number(float(item)) for item in values]


def canonical_witness_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Spell every float of a derived witness document; keep inputs exact.

    Walks the document and replaces each float outside the ``inputs`` subtree
    with ``derived_witness_number(value)`` so the canonical encoding is the
    same diagnostic bytes on every platform. Exact input/output series are
    passed through and can retain host-specific low bits. Ints, bools, strings
    and nulls pass through, and so does the whole ``inputs`` subtree: it carries
    retained inputs whose exact bytes other code re-verifies.
    """
    return {
        key: value
        if key == WITNESS_INPUTS_KEY or key in WITNESS_EXACT_SERIES_KEYS
        else _canonical_node(value)
        for key, value in document.items()
    }


def canonical_witness_in_place(
    document: dict[str, Any], *, checkpoint: Callable[[], None] = lambda: None
) -> dict[str, Any]:
    """Normalize a private, finished witness without duplicating its arrays.

    The caller gives up the mutable document; the emitted values and retained
    exact subtrees are identical to canonical_witness_document().
    """

    def normalize(node: Any) -> Any:
        if isinstance(node, float):
            return derived_witness_number(node)
        if isinstance(node, dict):
            for key, value in node.items():
                if key not in WITNESS_EXACT_SERIES_KEYS:
                    node[key] = normalize(value)
            return node
        if isinstance(node, list):
            for index, value in enumerate(node):
                node[index] = normalize(value)
            return node
        if isinstance(node, tuple):
            return [normalize(value) for value in node]
        return node

    for key, value in document.items():
        if key != WITNESS_INPUTS_KEY and key not in WITNESS_EXACT_SERIES_KEYS:
            if key == "modules" and isinstance(value, list):
                for index, module in enumerate(value):
                    checkpoint()
                    value[index] = normalize(module)
            else:
                document[key] = normalize(value)
    return document


def _canonical_node(node: Any) -> Any:
    if isinstance(node, float):
        return derived_witness_number(node)
    if isinstance(node, dict):
        return {
            key: value if key in WITNESS_EXACT_SERIES_KEYS else _canonical_node(value)
            for key, value in node.items()
        }
    if isinstance(node, (list, tuple)):
        return [_canonical_node(item) for item in node]
    return node
