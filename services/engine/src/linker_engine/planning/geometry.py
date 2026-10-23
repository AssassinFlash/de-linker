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
    centre_enu: Vector
    u_axis_enu: Vector
    v_axis_enu: Vector
    normal_enu: Vector
    width_m: float
    length_m: float
    thickness_m: float
    stc_power_w: float

    def corners(self) -> list[Vector]:
        return [
            add(
                self.centre_enu,
                add(
                    scale(self.u_axis_enu, u * self.width_m / 2),
                    add(
                        scale(self.v_axis_enu, v * self.length_m / 2),
                        scale(self.normal_enu, n * self.thickness_m / 2),
                    ),
                ),
            )
            for u, v, n in product((-1, 1), repeat=3)
        ]


def panel_poses(document: GeometryDocument) -> list[PanelPose]:
    """Called only after bounded, referenced, orthonormal input validation."""
    roofs = {item.id: item for item in document.roofs}
    specs = {item.id: item for item in document.module_specs}
    poses = []
    for array in document.arrays:
        roof, spec = roofs[array.roof_id], specs[array.module_spec_id]
        angle, tilt = (
            math.radians(array.rotation_deg),
            math.radians(array.mount_tilt_deg),
        )
        normal = cross(roof.u_axis_enu, roof.v_axis_enu)
        u = add(
            scale(roof.u_axis_enu, math.cos(angle)),
            scale(roof.v_axis_enu, math.sin(angle)),
        )
        row_axis = add(
            scale(roof.u_axis_enu, -math.sin(angle)),
            scale(roof.v_axis_enu, math.cos(angle)),
        )
        v = add(scale(row_axis, math.cos(tilt)), scale(normal, math.sin(tilt)))
        panel_normal = cross(u, v)
        origin = on_roof(roof, *array.origin_uv)
        excluded = set(array.excluded_slots)
        for row, column in product(range(array.rows), range(array.columns)):
            x = column * (spec.width_m + array.column_gap_m) + spec.width_m / 2
            y = (
                row * (spec.length_m * math.cos(tilt) + array.row_gap_m)
                + spec.length_m * math.cos(tilt) / 2
            )
            z = array.lower_edge_clearance_m + spec.length_m * math.sin(tilt) / 2
            centre = add(
                origin, add(scale(u, x), add(scale(row_axis, y), scale(normal, z)))
            )
            poses.append(
                PanelPose(
                    f"{array.id}:{row}:{column}",
                    array.id,
                    roof.id,
                    row,
                    column,
                    f"{row}:{column}" not in excluded,
                    add(centre, scale(panel_normal, spec.thickness_m / 2)),
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
