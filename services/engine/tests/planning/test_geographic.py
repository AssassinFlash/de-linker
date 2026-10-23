"""Independent analytic boundary and frozen browser/PROJ parity, not site accuracy."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.geographic import (
    GeographicBridge,
    GeographicReference,
    horizontal_on_roof,
)
from linker_engine.planning.geometry_documents import RoofFace

ROOT = Path(__file__).resolve().parents[4]


def reference(**changes: object) -> GeographicReference:
    return GeographicReference.model_validate(
        {
            "schema_version": 1,
            "method": "wgs84_cart_topocentric_v1",
            "longitude_deg": 0,
            "latitude_deg": 0,
            "ellipsoid_height_m": 0,
            "height_basis": "known_wgs84_ellipsoid",
            **changes,
        }
    )


def test_equator_has_an_independent_analytic_ecef_solution() -> None:
    bridge = GeographicBridge(reference())
    angle = math.radians(1)
    assert bridge.forward(1, 0, 0) == pytest.approx(
        (6378137 * math.sin(angle), 0, 6378137 * (math.cos(angle) - 1)), abs=1e-8
    )
    assert bridge.forward(0, 0, 5) == pytest.approx((0, 0, 5), abs=1e-10)
    assert bridge.inverse(0, 0, 5) == pytest.approx((0, 0, 5), abs=1e-8)
    manifest = bridge.manifest()
    assert manifest["grid_dependencies"] == []
    assert manifest["input_axis_order"] == "longitude_latitude_ellipsoid_height"
    assert "+ellps=WGS84" in str(manifest["operation"])


def test_frozen_proj_oracle_and_ellipsoid_contract_are_current() -> None:
    from pyproj import CRS

    fixture = json.loads(
        (ROOT / "fixtures/planning/geographic-proj-reference.json").read_text()
    )
    for case in fixture["cases"]:
        bridge = GeographicBridge(GeographicReference.model_validate(case["reference"]))
        for point in case["points"]:
            assert bridge.forward(*point["geodetic"]) == pytest.approx(
                point["enu"], abs=1e-10
            )
            assert bridge.inverse(*point["enu"]) == pytest.approx(
                point["inverse"], abs=1e-10
            )
    ellipsoid = json.loads(
        (ROOT / "apps/planner/src/contracts/wgs84-ellipsoid.json").read_text()
    )
    wgs84 = CRS.from_epsg(4979).ellipsoid
    assert ellipsoid["semi_major_axis_m"] == wgs84.semi_major_metre
    assert ellipsoid["inverse_flattening"] == wgs84.inverse_flattening


def test_horizontal_zero_is_a_declared_convention_and_invalid_positions_fail() -> None:
    bridge = GeographicBridge(
        reference(height_basis="zero_height_horizontal_convention")
    )
    with pytest.raises(ValidationError):
        reference(
            height_basis="zero_height_horizontal_convention", ellipsoid_height_m=4
        )
    with pytest.raises(InvalidInput):
        bridge.forward(0, 0, 4)
    for point in [(181, 0, 0), (0, 91, 0), (float("nan"), 0, 0), (0, 0, float("inf"))]:
        with pytest.raises(InvalidInput):
            bridge.forward(*point)
    with pytest.raises(InvalidInput):
        bridge.inverse(0, float("inf"), 0)


def test_horizontal_projection_keeps_true_slope_length_and_relative_height() -> None:
    roof = RoofFace(
        id="roof",
        name="Synthetic 3-4-5 roof",
        source_id="source",
        origin_enu=[2, 3, 10],
        u_axis_enu=[1, 0, 0],
        v_axis_enu=[0, 0.8, -0.6],
        boundary_uv=[[0, 0], [10, 0], [10, 10], [0, 10]],
        holes_uv=[],
    )
    assert horizontal_on_roof(roof, 5, 7) == pytest.approx((3, 5), abs=1e-12)
    with pytest.raises(InvalidInput):
        horizontal_on_roof(roof.model_copy(update={"v_axis_enu": [0, 0, -1]}), 5, 7)
