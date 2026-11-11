"""Two-point calibration: recorded scale, independent span, reference-only views."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from linker_engine.planning.geometry import read_geometry
from linker_engine.planning.geometry_documents import GeometryDocument, geometry_schema
from linker_engine.planning.image_calibration import (
    RESIDUAL_ABSOLUTE_TOLERANCE,
    SCALE_RELATIVE_TOLERANCE,
    ImageCalibration,
    derived_residual_ratio,
    measurement_status,
    pixel_distance,
)

ROOT = Path(__file__).resolve().parents[4]
IMAGE = {"media_type": "image/png", "pixel_width": 1200, "pixel_height": 800}
CONTROL = {"first": [100, 700], "second": [400, 700]}
CHECK = {"first": [100, 100], "second": [700, 100]}


def calibration(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": 1,
        "method": "two_point_uniform_scale_v1",
        "view": "horizontal_plan",
        "image": IMAGE,
        "control_points": CONTROL,
        "known_length_m": 6,
        "m_per_pixel": 0.02,
        "rotation_deg": 0,
        "check": {
            "points": CHECK,
            "declared_length_m": 12,
            "residual_ratio": 0,
            "status": "within_tolerance",
        },
        "check_tolerance_ratio": 0.01,
        "applied_pitch_deg": 0,
        "measurement_status": "usable_uniform_scale",
        "note": "Synthetic fixture drawing; not a survey.",
    }
    value.update(overrides)
    return value


def test_browser_contract_carries_the_optional_calibration() -> None:
    contracts = ROOT / "apps/planner/src/contracts/geometry.schema.json"
    assert json.loads(contracts.read_text()) == geometry_schema()
    source = geometry_schema()["$defs"]["GeometrySource"]
    # Optional: a revision saved before this field stays valid verbatim.
    assert "calibration" in source["properties"]
    assert "calibration" not in source["required"]


def test_scale_follows_from_its_control_points() -> None:
    assert pixel_distance(CONTROL["first"], CONTROL["second"]) == 300
    recorded = ImageCalibration.model_validate(calibration())
    assert recorded.m_per_pixel == pytest.approx(0.02)
    assert recorded.measurement_status == "usable_uniform_scale"
    assert recorded.check is not None
    assert recorded.check.residual_ratio == 0


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"m_per_pixel": 0.021}, "recorded scale does not follow"),
        (
            {"control_points": {"first": [100, 700], "second": [100, 700]}},
            "control points must differ",
        ),
        (
            {"control_points": {"first": [100, 700], "second": [5000, 700]}},
            "lies outside the image",
        ),
        ({"note": " "}, "written summary"),
        ({"applied_pitch_deg": None}, "records its conversion pitch"),
        ({"measurement_status": "reference_only"}, "contradicts its evidence"),
    ],
)
def test_contradictory_records_are_refused(
    change: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        ImageCalibration.model_validate(calibration(**change))


def test_a_failing_or_missing_second_span_stays_reference_only() -> None:
    failing = ImageCalibration.model_validate(
        calibration(
            check={
                "points": CHECK,
                "declared_length_m": 9,
                "residual_ratio": 1 / 3,
                "status": "exceeds_tolerance",
            },
            measurement_status="reference_only",
        )
    )
    assert failing.check is not None
    assert abs(failing.check.residual_ratio - 1 / 3) <= RESIDUAL_ABSOLUTE_TOLERANCE
    assert measurement_status(failing.view, failing.check) == "reference_only"
    assert measurement_status("roof_slope_elevation", None) == "reference_only"
    assert measurement_status("perspective_photo", failing.check) == "reference_only"
    with pytest.raises(ValidationError, match="contradicts its evidence"):
        ImageCalibration.model_validate(
            calibration(
                check={
                    "points": CHECK,
                    "declared_length_m": 9,
                    "residual_ratio": 1 / 3,
                    "status": "exceeds_tolerance",
                }
            )
        )


def test_a_perspective_photo_cannot_apply_a_pitch_or_measure() -> None:
    photo = ImageCalibration.model_validate(
        calibration(
            view="perspective_photo",
            applied_pitch_deg=None,
            measurement_status="reference_only",
        )
    )
    assert photo.applied_pitch_deg is None
    with pytest.raises(ValidationError, match="only a horizontal plan"):
        ImageCalibration.model_validate(
            calibration(view="perspective_photo", measurement_status="reference_only")
        )


def test_residual_refuses_arithmetic_that_contradicts_its_check() -> None:
    recorded = ImageCalibration.model_validate(calibration())
    assert recorded.check is not None
    residual = derived_residual_ratio(CHECK["first"], CHECK["second"], 12, 0.02)
    assert abs(recorded.check.residual_ratio - residual) <= RESIDUAL_ABSOLUTE_TOLERANCE
    with pytest.raises(ValidationError, match="recorded residual"):
        ImageCalibration.model_validate(
            calibration(
                check={
                    "points": CHECK,
                    "declared_length_m": 12,
                    "residual_ratio": 0.5,
                    "status": "within_tolerance",
                }
            )
        )


def test_scale_tolerance_is_arithmetic_support_not_accuracy() -> None:
    assert SCALE_RELATIVE_TOLERANCE == 1e-9
    width = 6 / 300
    exact = ImageCalibration.model_validate(calibration(m_per_pixel=width))
    assert exact.m_per_pixel == width
    with pytest.raises(ValidationError):
        ImageCalibration.model_validate(
            calibration(m_per_pixel=width * (1 + 10 * SCALE_RELATIVE_TOLERANCE))
        )


def test_the_document_accepts_a_calibrated_source_and_keeps_legacy_ones() -> None:
    (ROOT / "fixtures/planning/geometry-flat.json").read_text()
    fixture = json.loads((ROOT / "fixtures/planning/geometry-flat.json").read_text())
    source = fixture["sources"][0]
    calibrated = dict(source, calibration=calibration(), spatial_precision_m=0.05)
    value = dict(fixture, sources=[calibrated])
    document = read_geometry(value)
    assert document.sources[0].calibration is not None
    assert document.sources[0].spatial_precision_m == 0.05

    # The same saved revision without the field keeps its original meaning.
    assert read_geometry(fixture).sources[0].calibration is None
    assert "calibration" not in GeometryDocument.model_validate(fixture).sources[
        0
    ].model_dump(exclude_unset=True)


def test_a_calibrated_source_requires_its_writer_contract() -> None:
    from linker_engine.planning.project_input_contracts import (
        CALIBRATION_INPUT_CONTRACT,
        SUPPORTED_INPUT_CONTRACTS,
        required_contracts,
    )
    from linker_engine.planning.project_input_floor import (
        check_project_input_contracts,
    )

    assert CALIBRATION_INPUT_CONTRACT in SUPPORTED_INPUT_CONTRACTS
    assert SUPPORTED_INPUT_CONTRACTS[-1] == CALIBRATION_INPUT_CONTRACT
    # An uncalibrated document needs no new writer; the field is additive.
    assert required_contracts({"geometry": {"sources": [{"id": "source_a"}]}}) == ()
    assert required_contracts({"geometry": {"sources": []}}) == ()
    assert required_contracts({}) == ()
    assert (
        required_contracts(
            {"geometry": {"sources": [{"id": "source_a", "calibration": None}]}}
        )
        == ()
    )
    assert required_contracts(
        {"geometry": {"sources": [{"id": "source_a", "calibration": calibration()}]}}
    ) == (CALIBRATION_INPUT_CONTRACT,)
    # The retained-feature detector reads the same declaration without a workspace.
    assert check_project_input_contracts is not None
