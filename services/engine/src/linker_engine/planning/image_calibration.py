"""Two-point image calibration: a recorded scale, never a survey or a rectification.

The photograph or drawing stays in the customer's browser; this module owns the
recorded arithmetic of the declared control points. The dossier precedent
(docs/research/2026-10-23-map-workbench-integration/IMPLEMENTATION.md) fixes
what a two-point ruler can and cannot establish: one uniform scale, an explicit
drawing type, an independent second span, and no engineering measurement from a
perspective photograph. A single uniform scale cannot rectify a photograph or a
non-uniform scaling, so such a source stays reference-only.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .energy_inputs import Document, SchemaVersion

# Declared here rather than imported: this module is imported by
# geometry_documents, and a shared alias module would rename the generated
# $defs of every other browser contract.
type Text = Annotated[str, Field(min_length=1, max_length=4096)]
type Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
type Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
type PositiveInteger = Annotated[int, Field(strict=True, gt=0, le=2**53 - 1)]
# Named distinctly from the document's Vec2: an identical name would be emitted
# as a second, module-qualified $def and rewrite every existing reference.
type PixelPoint = Annotated[list[float], Field(min_length=2, max_length=2)]

# Arithmetic-support tolerance between the browser's and the server's binary64
# square root and division; not drawing accuracy, survey accuracy or a fitting
# epsilon. The recorded scale is only meaningful to the source's own precision.
SCALE_RELATIVE_TOLERANCE = 1e-9
RESIDUAL_ABSOLUTE_TOLERANCE = 1e-12


def pixel_distance(first: Sequence[float], second: Sequence[float]) -> float:
    """Distance in image pixels; x is right and y is down as displayed."""
    return math.hypot(second[0] - first[0], second[1] - first[1])


def derived_residual_ratio(
    first: Sequence[float],
    second: Sequence[float],
    declared_length_m: float,
    m_per_pixel: float,
) -> float:
    measured = pixel_distance(first, second) * m_per_pixel
    return abs(measured - declared_length_m) / declared_length_m


def measurement_status(
    view: str,
    check: CalibrationCheck | None,
) -> Literal["usable_uniform_scale", "reference_only"]:
    """Only a measurable view with a passing independent span is usable."""
    if view == "perspective_photo" or check is None:
        return "reference_only"
    if check.status != "within_tolerance":
        return "reference_only"
    return "usable_uniform_scale"


class CalibrationImage(Document):
    """The image as displayed; its bytes are not uploaded by this increment."""

    media_type: Literal["image/png", "image/jpeg", "image/webp"]
    pixel_width: PositiveInteger
    pixel_height: PositiveInteger


class CalibrationPoints(Document):
    first: PixelPoint
    second: PixelPoint


class CalibrationCheck(Document):
    points: CalibrationPoints
    declared_length_m: Positive
    residual_ratio: Nonnegative
    status: Literal["within_tolerance", "exceeds_tolerance"]


class ImageCalibration(Document):
    schema_version: SchemaVersion
    method: Literal["two_point_uniform_scale_v1"]
    view: Literal["horizontal_plan", "roof_slope_elevation", "perspective_photo"]
    image: CalibrationImage
    control_points: CalibrationPoints
    known_length_m: Positive
    m_per_pixel: Positive
    rotation_deg: Annotated[float, Field(ge=0, lt=360, allow_inf_nan=False)]
    check: CalibrationCheck | None
    check_tolerance_ratio: Positive
    # Declared pitch whose one cosine converted a horizontal plan into slope
    # lengths. It is a recorded derivation, not a claim about the roof today.
    applied_pitch_deg: Annotated[float, Field(ge=0, lt=90, allow_inf_nan=False)] | None
    measurement_status: Literal["usable_uniform_scale", "reference_only"]
    note: Text

    def _inside(self, point: Sequence[float]) -> bool:
        return (
            0 <= point[0] <= self.image.pixel_width
            and 0 <= point[1] <= self.image.pixel_height
        )

    @model_validator(mode="after")
    def recorded_scale(self) -> Self:
        if not self.note.strip():
            raise ValueError("calibration needs its written summary")
        for label, point in (
            ("control first", self.control_points.first),
            ("control second", self.control_points.second),
        ):
            if not self._inside(point):
                raise ValueError(f"{label} point lies outside the image")
        distance = pixel_distance(self.control_points.first, self.control_points.second)
        if distance <= 0:
            raise ValueError("calibration control points must differ")
        expected = self.known_length_m / distance
        if abs(self.m_per_pixel - expected) > SCALE_RELATIVE_TOLERANCE * expected:
            raise ValueError("recorded scale does not follow from its control points")
        check = self.check
        if check is not None:
            for point in (check.points.first, check.points.second):
                if not self._inside(point):
                    raise ValueError("check point lies outside the image")
            if pixel_distance(check.points.first, check.points.second) <= 0:
                raise ValueError("calibration check points must differ")
            residual = derived_residual_ratio(
                check.points.first,
                check.points.second,
                check.declared_length_m,
                self.m_per_pixel,
            )
            if abs(check.residual_ratio - residual) > RESIDUAL_ABSOLUTE_TOLERANCE:
                raise ValueError("recorded residual does not follow from its check")
            expected_status = (
                "within_tolerance"
                if residual <= self.check_tolerance_ratio
                else "exceeds_tolerance"
            )
            if check.status != expected_status:
                raise ValueError("recorded check status contradicts its residual")
        if self.view == "horizontal_plan":
            if self.applied_pitch_deg is None:
                raise ValueError("a horizontal plan records its conversion pitch")
        elif self.applied_pitch_deg is not None:
            raise ValueError("only a horizontal plan converts through a pitch")
        if self.measurement_status != measurement_status(self.view, check):
            raise ValueError("recorded measurement status contradicts its evidence")
        return self
