"""Derived-witness spelling is a storage contract, not a coarser physical model."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import cast

import numpy as np
import pytest

import linker_engine.planning.report_numbers as report_numbers
from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.model_numbers import (
    DERIVED_WITNESS_SIGNIFICANT_DIGITS,
    canonical_witness_document,
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


def test_spelling_is_ten_significant_digits_not_an_identity_or_a_tolerance() -> None:
    # The decimal quantum (1e-9 relative) is >=300x coarser than the measured
    # macOS-libm/glibc spread of a derived PV float (~3e-12 relative), so
    # platform siblings share one spelling. Ten digits is a stability
    # contract, not an engineering accuracy; the stored value stays within
    # 5e-10 relative of the unrounded one.
    assert DERIVED_WITNESS_SIGNIFICANT_DIGITS == 10
    raw = math.pi
    stored = derived_witness_number(raw)
    assert stored != raw
    rendered = json.dumps(stored)
    assert _significant_digits(rendered) <= DERIVED_WITNESS_SIGNIFICANT_DIGITS
    assert float(rendered) == stored
    assert abs(stored - raw) <= abs(raw) * 5e-10
    # A coefficient already inside ten digits is unchanged. That does not
    # send frozen report sources through this function.
    assert derived_witness_number(-0.0029) == -0.0029
    assert derived_witness_number(0.1805) == 0.1805


def test_spelled_value_stays_within_the_documented_distance() -> None:
    # Ten significant digits is a stability contract, not a rounding-free
    # identity: every stored float sits within half the 1e-9 relative
    # quantum of its unrounded value, and a spelled value is a fixed point
    # of the spelling.
    for raw in (math.pi, math.pi * 1e6, math.pi * 1e-6, 2943.945050162976):
        stored = derived_witness_number(raw)
        assert abs(stored - raw) <= abs(raw) * 5e-10
        assert derived_witness_number(stored) == stored


def test_adjacent_ulps_share_one_spelling() -> None:
    # Platform libm/SIMD siblings differ by a few ulps. The spelling must
    # collapse such neighbours to identical stored bytes, otherwise the
    # witness hashes differ per platform. A neighbour within one ulp of a
    # 1e-9 relative quantum can only cross a spelling boundary when the
    # value sits at the quantum edge; values at the edge are checked too.
    for value in (
        0.5,
        1.0,
        -3.7,
        math.pi,
        math.pi * 1e6,
        math.pi * 1e-6,
        2943.945050162976,
        8707.219664,
        123456789.123,
    ):
        for _ in range(9):
            neighbour = math.nextafter(value, math.inf)
            assert derived_witness_number(value) == derived_witness_number(neighbour), (
                value
            )
            value = neighbour
    # Ten ulps of drift in the last bits, the observed order of the
    # macOS/Linux spread, also collapses.
    value = math.pi
    drifted = value
    for _ in range(10):
        drifted = math.nextafter(drifted, math.inf)
    assert derived_witness_number(value) == derived_witness_number(drifted)


def test_witness_document_encoding_spells_diagnostics_but_not_output_series() -> None:
    # Derived diagnostics move by one ulp and still encode identically. The
    # retained AC series is read back as physics, so it must stay exact and
    # make the document differ when a watt moves.
    document = {
        "schema_version": 1,
        "kind": "test",
        "inputs": {"parameters_sha256": "x", "lat": 52.5200065},
        "solar_geometry": {
            "apparent_zenith_deg": [81.27299494312053, math.pi * 100],
            "azimuth_deg": [math.pi],
        },
        "arrays": [
            {
                "id": "a",
                "cell_temperature_c": [31.498294829 + math.pi * 1e-9],
                "dc_available_w": [1234567.8901234567, math.pi * 1e8],
            }
        ],
        "available_ac_w": [46405.811538460756, math.pi * 1e7],
        "energy_kwh": 2943.945050162976,
        "release": {"status": "not_assessed"},
    }

    # A freshly built worker witness can be normalized in place, avoiding a
    # second complete annual document; its retained bytes must stay identical.
    from copy import deepcopy

    from linker_engine.planning.model_numbers import canonical_witness_in_place

    owned = deepcopy(document)
    assert encode(canonical_witness_in_place(owned)) == encode(
        canonical_witness_document(document)
    )

    from linker_engine.planning.errors import LeaseLost

    def cancelled() -> None:
        raise LeaseLost("fixture cancellation")

    with pytest.raises(LeaseLost):
        canonical_witness_in_place({"modules": [{"value": 1.1}]}, checkpoint=cancelled)

    def bump(node: object) -> object:
        if isinstance(node, float):
            return math.nextafter(node, math.inf)
        if isinstance(node, dict):
            return {
                key: value if key == "inputs" else bump(value)
                for key, value in node.items()
            }
        if isinstance(node, list):
            return [bump(item) for item in node]
        return node

    bumped = bump(document)
    canonical = canonical_witness_document(cast(Mapping[str, object], document))
    canonical_bumped = canonical_witness_document(cast(Mapping[str, object], bumped))
    assert canonical["available_ac_w"] == document["available_ac_w"]
    assert (
        canonical_bumped["available_ac_w"]
        == cast(Mapping[str, object], bumped)["available_ac_w"]
    )
    assert canonical["available_ac_w"] != canonical_bumped["available_ac_w"]
    assert encode(canonical) != encode(canonical_bumped)
    assert canonical["solar_geometry"] == canonical_bumped["solar_geometry"]
    arrays = cast(list[Object], canonical["arrays"])
    bumped_arrays = cast(list[Object], canonical_bumped["arrays"])
    assert arrays[0]["cell_temperature_c"] == bumped_arrays[0]["cell_temperature_c"]
    assert arrays[0]["dc_available_w"] != bumped_arrays[0]["dc_available_w"]
    # The inputs subtree is pinned and never respelled, not even a ulp.
    pinned = encode(canonical)
    inputs_bumped = encode(
        canonical_witness_document({**document, "inputs": bump(document["inputs"])})
    )
    assert pinned != inputs_bumped
    spelled = json.loads(pinned)
    assert spelled["inputs"] == document["inputs"]


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
