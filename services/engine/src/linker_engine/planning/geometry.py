"""Deterministic metric placement, independent of browser or GPU libraries."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product

from pydantic import ValidationError

from .canonical import Json, Object
from .errors import InvalidInput
from .geometry_documents import (
    GeometryDocument,
    GeometrySource,
    Keepout,
    ModuleSpec,
    Obstacle,
    PanelArray,
    RoofFace,
    RoofLayoutRules,
)
from .wire_numbers import MAX_WIRE_NUMBER, check_wire_numbers

type Vector = tuple[float, float, float]

# Orthonormal floating-point comparison only, not survey/installation tolerance.
BASIS_EPSILON = 1e-9
# Application preview/storage policy; not maximum building/array dimensions.
MAX_PANELS = 5000
MAX_VERTICES = 20000
MAX_OBJECTS = 1024


def add(a: list[float] | Vector, b: list[float] | Vector) -> Vector:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale(a: list[float] | Vector, by: float) -> Vector:
    return (a[0] * by, a[1] * by, a[2] * by)


def dot(a: list[float] | Vector, b: list[float] | Vector) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def cross(a: list[float] | Vector, b: list[float] | Vector) -> Vector:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def on_roof(roof: RoofFace, u: float, v: float) -> Vector:
    return add(
        roof.origin_enu, add(scale(roof.u_axis_enu, u), scale(roof.v_axis_enu, v))
    )


def roof_coordinates(roof: RoofFace, point: Vector) -> tuple[float, float]:
    delta = add(point, scale(roof.origin_enu, -1))
    return (dot(delta, roof.u_axis_enu), dot(delta, roof.v_axis_enu))


@dataclass(frozen=True)
class PanelPose:
    id: str
    array_id: str
    roof_id: str
    row: int
    column: int
    included: bool
    centre_uvn: Vector
    u_axis_uvn: Vector
    v_axis_uvn: Vector
    normal_uvn: Vector
    footprint_uv: list[list[float]]
    # Absolute display coordinates can lose local detail at huge origins.
    # Fit/rays/rebased rendering must use the retained local frame instead.
    centre_enu: Vector
    u_axis_enu: Vector
    v_axis_enu: Vector
    normal_enu: Vector
    width_m: float
    length_m: float
    thickness_m: float
    stc_power_w: float

    def corners_uvn(self) -> list[Vector]:
        return cuboid_corners(
            self.centre_uvn,
            self.u_axis_uvn,
            self.v_axis_uvn,
            self.normal_uvn,
            self.width_m,
            self.length_m,
            self.thickness_m,
        )

    def corners(self) -> list[Vector]:
        return cuboid_corners(
            self.centre_enu,
            self.u_axis_enu,
            self.v_axis_enu,
            self.normal_enu,
            self.width_m,
            self.length_m,
            self.thickness_m,
        )


def cuboid_corners(
    centre: Vector,
    u_axis: Vector,
    v_axis: Vector,
    normal: Vector,
    width: float,
    length: float,
    thickness: float,
) -> list[Vector]:
    return [
        add(
            centre,
            add(
                scale(u_axis, u * width / 2),
                add(
                    scale(v_axis, v * length / 2),
                    scale(normal, n * thickness / 2),
                ),
            ),
        )
        for u, v, n in product((-1, 1), repeat=3)
    ]


def sin_cos_degrees(degrees: float) -> tuple[float, float]:
    # Signed binary64 remainder matches JS %, before multiplication by pi.
    # Exact quadrant values prevent a nominal 90deg edge from drifting.
    reduced = math.fmod(degrees, 360)
    quadrants: dict[float, tuple[float, float]] = {
        0: (0.0, 1.0),
        90: (1.0, 0.0),
        -90: (-1.0, 0.0),
        180: (0.0, -1.0),
        -180: (0.0, -1.0),
        270: (-1.0, 0.0),
        -270: (1.0, 0.0),
    }
    if reduced in quadrants:
        return quadrants[reduced]
    radians = (reduced * math.pi) / 180
    return math.sin(radians), math.cos(radians)


def vector_from_roof(roof: RoofFace, uvn: Vector) -> Vector:
    return add(
        scale(roof.u_axis_enu, uvn[0]),
        add(
            scale(roof.v_axis_enu, uvn[1]),
            scale(cross(roof.u_axis_enu, roof.v_axis_enu), uvn[2]),
        ),
    )


def panel_poses(document: GeometryDocument) -> list[PanelPose]:
    """Called only after bounded, referenced, orthonormal input validation."""
    roofs = {item.id: item for item in document.roofs}
    specs = {item.id: item for item in document.module_specs}
    poses = []
    for array in document.arrays:
        roof, spec = roofs[array.roof_id], specs[array.module_spec_id]
        sin_angle, cos_angle = sin_cos_degrees(array.rotation_deg)
        sin_tilt, cos_tilt = sin_cos_degrees(array.mount_tilt_deg)
        local_u = (cos_angle, sin_angle, 0.0)
        local_v = (-sin_angle * cos_tilt, cos_angle * cos_tilt, sin_tilt)
        local_normal = cross(local_u, local_v)
        u, v, panel_normal = (
            vector_from_roof(roof, axis) for axis in (local_u, local_v, local_normal)
        )
        excluded = set(array.excluded_slots)
        for row, column in product(range(array.rows), range(array.columns)):
            x = column * (spec.width_m + array.column_gap_m) + spec.width_m / 2
            y = (
                row * (spec.length_m * cos_tilt + array.row_gap_m)
                + spec.length_m * cos_tilt / 2
            )
            z = array.lower_edge_clearance_m + spec.length_m * sin_tilt / 2
            centre_uvn = add(
                (
                    array.origin_uv[0] + x * cos_angle - y * sin_angle,
                    array.origin_uv[1] + x * sin_angle + y * cos_angle,
                    z,
                ),
                scale(local_normal, spec.thickness_m / 2),
            )
            # Shared grid edges retain analytic zero-gap contact, unlike
            # separately rounded centres plus half-sizes for each polygon.
            left = column * spec.width_m + column * array.column_gap_m
            right = (column + 1) * spec.width_m + column * array.column_gap_m
            lower = (
                row * (spec.length_m * cos_tilt)
                + row * array.row_gap_m
                - spec.thickness_m * sin_tilt
            )
            upper = (row + 1) * (spec.length_m * cos_tilt) + row * array.row_gap_m
            footprint = [
                [
                    array.origin_uv[0] + a * cos_angle - b * sin_angle,
                    array.origin_uv[1] + a * sin_angle + b * cos_angle,
                ]
                for a, b in [
                    (left, lower),
                    (right, lower),
                    (right, upper),
                    (left, upper),
                ]
            ]
            centre = add(roof.origin_enu, vector_from_roof(roof, centre_uvn))
            poses.append(
                PanelPose(
                    f"{array.id}:{row}:{column}",
                    array.id,
                    roof.id,
                    row,
                    column,
                    f"{row}:{column}" not in excluded,
                    centre_uvn,
                    local_u,
                    local_v,
                    local_normal,
                    footprint,
                    centre,
                    u,
                    v,
                    panel_normal,
                    spec.width_m,
                    spec.length_m,
                    spec.thickness_m,
                    spec.stc_power_w,
                )
            )
    return poses


def read_geometry(value: Json) -> GeometryDocument:
    try:
        check_wire_numbers(value)
        document = GeometryDocument.read(value)
        validate_geometry(document)
    except (ValueError, ValidationError, OverflowError) as error:
        raise InvalidInput("invalid geometry document") from error
    return document


def validate_geometry(document: GeometryDocument) -> None:
    objects: list[
        GeometrySource | RoofFace | ModuleSpec | PanelArray | Obstacle | Keepout
    ] = [
        *document.sources,
        *document.roofs,
        *document.module_specs,
        *document.arrays,
        *document.obstacles,
        *document.keepouts,
    ]
    if len(objects) + len(document.layout_rules) > MAX_OBJECTS:
        raise InvalidInput("geometry object resource limit exceeded")
    ids = [item.id for item in objects]
    if len(ids) != len(set(ids)):
        raise InvalidInput("duplicate geometry object ID")
    sources = {item.id for item in document.sources}
    roofs = {item.id for item in document.roofs}
    modules = {item.id for item in document.module_specs}
    sourced: list[RoofFace | PanelArray | Obstacle | Keepout | RoofLayoutRules] = [
        *document.roofs,
        *document.arrays,
        *document.obstacles,
        *document.keepouts,
        *document.layout_rules,
    ]
    for item in sourced:
        if item.source_id not in sources:
            raise InvalidInput("geometry source reference missing")
    coordinate = document.coordinate_system
    if coordinate.anchor is not None and coordinate.anchor.source_id not in sources:
        raise InvalidInput("geographic anchor source missing")
    if (coordinate.north_reference == "unreferenced") != (
        coordinate.north_source_id is None
    ):
        raise InvalidInput("north reference source required")
    if (
        coordinate.north_source_id is not None
        and coordinate.north_source_id not in sources
    ):
        raise InvalidInput("north source reference missing")
    rule_roofs = [r.roof_id for r in document.layout_rules]
    if len(rule_roofs) != len(set(rule_roofs)):
        raise InvalidInput("duplicate roof layout rules")
    bound: list[PanelArray | Obstacle | Keepout | RoofLayoutRules] = [
        *document.arrays,
        *document.obstacles,
        *document.keepouts,
        *document.layout_rules,
    ]
    for item in bound:
        if item.roof_id not in roofs:
            raise InvalidInput("roof reference missing")
    vertices = (
        sum(len(r.boundary_uv) + sum(map(len, r.holes_uv)) for r in document.roofs)
        + sum(len(r.footprint_uv) for r in document.obstacles)
        + sum(len(r.footprint_uv) for r in document.keepouts)
    )
    if vertices > MAX_VERTICES:
        raise InvalidInput("geometry vertex resource limit exceeded")
    for roof in document.roofs:
        unit(roof.u_axis_enu)
        unit(roof.v_axis_enu)
        if (
            abs(dot(roof.u_axis_enu, roof.v_axis_enu)) > BASIS_EPSILON
            or cross(roof.u_axis_enu, roof.v_axis_enu)[2] <= 0
        ):
            raise InvalidInput("roof needs an upward orthonormal basis")
        for ring in [roof.boundary_uv, *roof.holes_uv]:
            for uv in ring:
                representable(on_roof(roof, *uv))
    for obstacle in document.obstacles:
        unit(obstacle.extrusion_axis_enu)
        roof = next(r for r in document.roofs if r.id == obstacle.roof_id)
        for uv in obstacle.footprint_uv:
            representable(
                add(
                    on_roof(roof, *uv),
                    scale(obstacle.extrusion_axis_enu, obstacle.height_m),
                )
            )
    if sum(a.rows * a.columns for a in document.arrays) > MAX_PANELS:
        raise InvalidInput("geometry panel resource limit exceeded")
    for array in document.arrays:
        if array.module_spec_id not in modules:
            raise InvalidInput("module reference missing")
        if len(array.excluded_slots) != len(set(array.excluded_slots)):
            raise InvalidInput("duplicate excluded panel slot")
        for slot in array.excluded_slots:
            row, column = map(int, slot.split(":"))
            if (
                slot != f"{row}:{column}"
                or row >= array.rows
                or column >= array.columns
            ):
                raise InvalidInput("invalid excluded panel slot")
    poses = panel_poses(document)
    if math.fsum(p.stc_power_w for p in poses if p.included) / 1000 > MAX_WIRE_NUMBER:
        raise InvalidInput("aggregate module rating is not representable")
    for pose in poses:
        representable(pose.centre_enu)
        for point in pose.corners():
            representable(point)


def unit(axis: list[float]) -> None:
    if abs(dot(axis, axis) - 1) > BASIS_EPSILON:
        raise InvalidInput("geometry axis must be a unit vector")


def representable(point: Vector) -> None:
    if not all(math.isfinite(v) and abs(v) <= MAX_WIRE_NUMBER for v in point):
        raise InvalidInput("derived geometry is not representable")


def validate_project_geometry(inputs: Object) -> None:
    if "geometry" in inputs:
        read_geometry(inputs["geometry"])
