"""CPU rays against declared surfaces/prisms, rebased before local arithmetic.

Mature sampling reference: retained Aladdin 7b939ab, solarPanelSimulation
791-818/1231-1239; CAPABILITY-MAP section 8. No rendering mesh/shadow map,
invented building volume, polygon repair, optical or electrical model is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.geometry import Point, Polygon

from .canonical import Json
from .errors import InvalidInput, NumericalFailure
from .geometry import Vector, cross, panel_poses, read_geometry, vector_from_roof
from .geometry_documents import RoofFace
from .geometry_numerics import MAX_UV_RESOLUTION_M, uv_resolution

# Arithmetic guard policy for composed binary64 frame/dot/intersection work,
# not survey accuracy or an independently established intersection error bound.
ULP_ALLOWANCE = 64
ANGULAR_GUARD = ULP_ALLOWANCE * math.ulp(1.0)


def plus(a: Vector, b: Vector) -> Vector:
    return (math.fsum((a[0], b[0])), math.fsum((a[1], b[1])), math.fsum((a[2], b[2])))


def vector(values: list[float]) -> Vector:
    return (values[0], values[1], values[2])


def times(a: Vector, scale: float) -> Vector:
    return (a[0] * scale, a[1] * scale, a[2] * scale)


def scalar(a: Vector, b: Vector) -> float:
    return math.fsum(x * y for x, y in zip(a, b, strict=True))


def unit(a: Vector) -> Vector:
    length = math.hypot(*a)
    if not math.isfinite(length) or length <= ANGULAR_GUARD:
        raise NumericalFailure("degenerate direct-beam surface basis")
    return times(a, 1 / length)


def polygon(boundary: list[list[float]], holes: list[list[list[float]]]) -> Polygon:
    shape = Polygon(boundary, holes)
    if (
        not shape.is_valid
        or shape.is_empty
        or not math.isfinite(shape.area)
        or shape.area <= 0
    ):
        raise InvalidInput("invalid direct-beam polygon; no repair is applied")
    for ring in [boundary, *holes]:
        if any(a == b for a, b in zip(ring, [*ring[1:], ring[0]], strict=True)):
            raise InvalidInput("degenerate direct-beam polygon edge")
    return shape


@dataclass(frozen=True)
class Face:
    origin: Vector
    u: Vector
    v: Vector
    shape: Polygon

    @property
    def normal(self) -> Vector:
        return unit(cross(self.u, self.v))

    def coordinates(self, point: Vector) -> Point:
        delta = plus(point, times(self.origin, -1))
        coordinates = (scalar(delta, self.u), scalar(delta, self.v))
        if not all(math.isfinite(value) for value in coordinates):
            raise NumericalFailure("nonfinite direct-beam local intersection")
        return Point(*coordinates)

    def ray_hit(self, point: Vector, direction: Vector, epsilon: float) -> bool:
        normal = self.normal
        distance = scalar(plus(self.origin, times(point, -1)), normal)
        denominator = scalar(direction, normal)
        if denominator == 0:
            if abs(distance) <= epsilon:
                raise NumericalFailure("coplanar direct-beam ray is unresolved")
            return False
        if abs(denominator) <= ANGULAR_GUARD:
            raise NumericalFailure("near-parallel direct-beam ray is unresolved")
        travel = distance / denominator
        if not math.isfinite(travel):
            raise NumericalFailure("nonfinite direct-beam intersection")
        if travel < -epsilon:
            return False
        hit = self.coordinates(plus(point, times(direction, travel)))
        if self.shape.boundary.distance(hit) <= epsilon:
            raise NumericalFailure("direct-beam edge intersection is unresolved")
        covered = bool(self.shape.covers(hit))
        if covered and travel <= epsilon:
            raise NumericalFailure("receiver touches a declared opaque surface")
        return covered


@dataclass(frozen=True)
class Opaque:
    id: str
    kind: str
    base: Face
    axis: Vector | None
    height: float | None
    faces: tuple[Face, ...]

    def contains_receiver(self, point: Vector, epsilon: float) -> bool:
        if self.axis is None or self.height is None:
            return False
        divisor = scalar(self.axis, self.base.normal)
        if abs(divisor) <= ANGULAR_GUARD:
            raise NumericalFailure("degenerate direct-beam extrusion")
        height = (
            scalar(plus(point, times(self.base.origin, -1)), self.base.normal) / divisor
        )
        if height < -epsilon or height > self.height + epsilon:
            return False
        projected = self.base.coordinates(plus(point, times(self.axis, -height)))
        return (
            bool(self.base.shape.covers(projected))
            or self.base.shape.boundary.distance(projected) <= epsilon
        )


def prism(id: str, kind: str, base: Face, axis: Vector, height: float) -> Opaque:
    if abs(scalar(axis, base.normal)) <= ANGULAR_GUARD:
        raise NumericalFailure("extrusion axis is tangent to its footprint")
    extrusion = times(axis, height)
    faces = [base, Face(plus(base.origin, extrusion), base.u, base.v, base.shape)]
    rings = [base.shape.exterior, *base.shape.interiors]
    for ring in rings:
        coordinates = list(ring.coords)
        for a, b in zip(coordinates[:-1], coordinates[1:], strict=True):
            origin = plus(base.origin, plus(times(base.u, a[0]), times(base.v, a[1])))
            edge = plus(times(base.u, b[0] - a[0]), times(base.v, b[1] - a[1]))
            u = unit(edge)
            v = unit(plus(extrusion, times(u, -scalar(extrusion, u))))
            width = math.hypot(*edge)
            along, across = scalar(extrusion, u), scalar(extrusion, v)
            faces.append(
                Face(
                    origin,
                    u,
                    v,
                    polygon(
                        [[0, 0], [width, 0], [width + along, across], [along, across]],
                        [],
                    ),
                )
            )
    return Opaque(id, kind, base, axis, height, tuple(faces))


@dataclass(frozen=True)
class Receiver:
    id: str
    array_id: str
    roof_id: str
    centre: Vector
    u: Vector
    v: Vector
    normal: Vector
    width: float
    length: float

    def midpoint(self, x: int, y: int, count: int) -> Vector:
        return plus(
            self.centre,
            plus(
                times(self.u, ((x + 0.5) / count - 0.5) * self.width),
                times(self.v, ((y + 0.5) / count - 0.5) * self.length),
            ),
        )


@dataclass(frozen=True)
class Scene:
    receivers: tuple[Receiver, ...]
    opaque: tuple[Opaque, ...]
    excluded_nonopaque_ids: tuple[str, ...]
    epsilon_m: float


def build_scene(value: Json) -> Scene:
    document = read_geometry(value)
    if not document.roofs or uv_resolution(document) > MAX_UV_RESOLUTION_M:
        raise NumericalFailure("direct-beam local coordinate resolution is unsupported")
    origin = tuple(document.roofs[0].origin_enu)

    def local_origin(roof: RoofFace) -> Vector:
        return (
            roof.origin_enu[0] - origin[0],
            roof.origin_enu[1] - origin[1],
            roof.origin_enu[2] - origin[2],
        )

    roofs = {roof.id: roof for roof in document.roofs}
    opaque: list[Opaque] = []
    for roof in document.roofs:
        u, v = vector(roof.u_axis_enu), vector(roof.v_axis_enu)
        if (
            max(abs(scalar(u, u) - 1), abs(scalar(v, v) - 1), abs(scalar(u, v)))
            > ANGULAR_GUARD
        ):
            raise NumericalFailure("direct-beam roof basis exceeds arithmetic support")
        face = Face(
            local_origin(roof),
            vector(roof.u_axis_enu),
            vector(roof.v_axis_enu),
            polygon(roof.boundary_uv, roof.holes_uv),
        )
        opaque.append(Opaque(roof.id, "roof_surface", face, None, None, (face,)))
    for obstacle in document.obstacles:
        roof = roofs[obstacle.roof_id]
        base = Face(
            local_origin(roof),
            vector(roof.u_axis_enu),
            vector(roof.v_axis_enu),
            polygon(obstacle.footprint_uv, []),
        )
        opaque.append(
            prism(
                obstacle.id,
                "obstacle_volume",
                base,
                vector(obstacle.extrusion_axis_enu),
                obstacle.height_m,
            )
        )
    receivers = []
    for pose in panel_poses(document):
        if not pose.included:
            continue
        # Keep local UVN. pose.centre_enu has already added the possibly huge
        # display origin; subtracting that value again would lose local detail.
        centre = plus(
            local_origin(roofs[pose.roof_id]),
            vector_from_roof(roofs[pose.roof_id], pose.centre_uvn),
        )
        u, v, normal = pose.u_axis_enu, pose.v_axis_enu, pose.normal_enu
        rectangle = polygon(
            [
                [-pose.width_m / 2, -pose.length_m / 2],
                [pose.width_m / 2, -pose.length_m / 2],
                [pose.width_m / 2, pose.length_m / 2],
                [-pose.width_m / 2, pose.length_m / 2],
            ],
            [],
        )
        base = Face(plus(centre, times(normal, -pose.thickness_m / 2)), u, v, rectangle)
        opaque.append(prism(pose.id, "module_volume", base, normal, pose.thickness_m))
        receivers.append(
            Receiver(
                pose.id,
                pose.array_id,
                pose.roof_id,
                plus(centre, times(normal, pose.thickness_m / 2)),
                u,
                v,
                normal,
                pose.width_m,
                pose.length_m,
            )
        )
    if not receivers:
        raise InvalidInput("direct-beam visibility requires included receiver modules")
    coordinates = [
        number
        for item in opaque
        for face in item.faces
        for number in (
            *face.origin,
            *(
                coordinate
                for ring in (face.shape.exterior, *face.shape.interiors)
                for point in ring.coords
                for coordinate in point
            ),
        )
    ]
    epsilon = ULP_ALLOWANCE * max(
        math.ulp(1.0), *(math.ulp(number) for number in coordinates)
    )
    if not math.isfinite(epsilon) or epsilon > MAX_UV_RESOLUTION_M:
        raise NumericalFailure(
            "direct-beam rebased arithmetic resolution is unsupported"
        )
    return Scene(
        tuple(receivers), tuple(opaque), tuple(k.id for k in document.keepouts), epsilon
    )
