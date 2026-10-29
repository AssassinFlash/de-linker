"""Derived-witness spelling is a storage contract, not a coarser physical model."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from linker_engine.planning import report_numbers
from linker_engine.planning.canonical import encode
from linker_engine.planning.model_numbers import (
    DERIVED_WITNESS_DIGITS10,
    derived_witness_number,
    derived_witness_numbers,
)
from linker_engine.planning.pv_physics import values

from .test_pv_generation import weather


def _significant_digits(text: str) -> int:
    mantissa = text.lower().split("e", 1)[0].replace("-", "").replace("+", "")
    mantissa = mantissa.replace(".", "").lstrip("0")
    return len(mantissa)


def test_signed_zero_is_one_stored_witness_value() -> None:
    assert derived_witness_number(-0.0) == 0.0
    assert math.copysign(1.0, derived_witness_number(-0.0)) == 1.0
    assert derived_witness_numbers([-0.0, 0.0]) == [0.0, 0.0]


def test_spelling_is_binary64_digits10_not_an_identity_or_a_tolerance() -> None:
    # IEEE 754-2008 binary64 digits10. Seventeen digits would name one binary64;
    # fifteen does not, and neither number is an engineering accuracy.
    assert DERIVED_WITNESS_DIGITS10 == 15
    raw = math.pi
    stored = derived_witness_number(raw)
    assert stored != raw
    rendered = json.dumps(stored)
    assert _significant_digits(rendered) <= DERIVED_WITNESS_DIGITS10
    assert float(rendered) == stored
    # A coefficient already inside fifteen digits is unchanged. That does not
    # send frozen report sources through this function.
    assert derived_witness_number(-0.0029) == -0.0029
    assert derived_witness_number(0.1805) == 0.1805


def test_spelling_before_the_loss_product_is_a_different_number() -> None:
    before = math.pi * 1000
    real_after = before * 0.9506
    real_reduction = before - real_after
    fed_back_after = derived_witness_number(derived_witness_number(before) * 0.9506)
    fed_back_reduction = derived_witness_number(
        derived_witness_number(before) - derived_witness_number(real_after)
    )
    assert derived_witness_number(real_after) != fed_back_after
    assert derived_witness_number(real_reduction) != fed_back_reduction


def test_adjacent_values_need_not_share_a_spelling() -> None:
    # A nextafter pair that stays distinct. Collapsing every adjacent value
    # would only show that the spelling is coarse enough to hide the host; it
    # would not prove macOS libm and glibc agree, and this contract does not
    # make that claim.
    value = 1.0
    for _ in range(64):
        neighbour = math.nextafter(value, math.inf)
        if derived_witness_number(value) != derived_witness_number(neighbour):
            return
        value = neighbour
    raise AssertionError("expected an adjacent pair with two spellings")


def test_original_sources_and_canonical_encode_do_not_spell() -> None:
    raw = math.pi
    encoded = json.loads(encode({"ghi_w_m2": raw}))
    assert encoded["ghi_w_m2"] == raw
    assert derived_witness_number(raw) != raw
    meteo = weather(ghi=800.1234567890123)
    document = json.loads(encode(meteo.document()))
    points = document["points"]
    assert isinstance(points, list)
    assert points[0]["ghi_w_m2"] == meteo.points[0].ghi_w_m2
    assert report_numbers.significant(raw, "en") == "3.142"


def test_values_spells_only_the_returned_witness_list() -> None:
    raw = math.pi
    vector = np.asarray([raw], dtype=np.float64)
    assert values(vector) == [derived_witness_number(raw)]
    assert vector.tolist() == [raw]
    with pytest.raises(ValueError, match="finite"):
        derived_witness_number(math.nan)
