"""Optional CPU broadphase; candidates still need the existing exact checks.

Bounds enclose the declared finite faces and receiver-contact tolerance. Closed
slabs use outward-rounded intervals; uncertain arithmetic retains an object.
This is computation policy, not survey accuracy or a visibility error bound.
No sampler, task, irradiance or electrical model is registered here.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from .direct_beam_geometry import ANGULAR_GUARD, Face, Opaque, Scene
from .errors import InvalidInput, NumericalFailure
from .geometry import Vector

type _Interval = tuple[float, float]
_UNKNOWN: _Interval = (-math.inf, math.inf)


def _outward(low: float, high: float) -> _Interval:
    if math.isnan(low) or math.isnan(high):
        return _UNKNOWN
    return math.nextafter(low, -math.inf), math.nextafter(high, math.inf)


def _add(a: _Interval, b: _Interval) -> _Interval:
    return _outward(a[0] + b[0], a[1] + b[1])


def _subtract(a: _Interval, b: _Interval) -> _Interval:
    return _add(a, (-b[1], -b[0]))


def _multiply(a: _Interval, b: _Interval) -> _Interval:
    products = [x * y for x in a for y in b]
    if any(math.isnan(value) for value in products):
        return _UNKNOWN
    return _outward(min(products), max(products))


def _divide(a: _Interval, b: _Interval) -> _Interval:
    if b[0] <= 0 <= b[1]:
        return _UNKNOWN
    return _multiply(a, _outward(1 / b[1], 1 / b[0]))


def _dot(a: Vector, b: Vector) -> _Interval:
    result = (0.0, 0.0)
    for x, y in zip(a, b, strict=True):
        result = _add(result, _multiply((x, x), (y, y)))
    return result


@dataclass(frozen=True)
class _Bounds:
    low: Vector
    high: Vector

    def intersects(self, point: Vector, direction: Vector, epsilon: float) -> bool:
        # Face.ray_hit also retains travel in [-epsilon, 0]. A point inside or
        # on a volume must reach contains_receiver even if the ray points away.
        near, far = -epsilon, math.inf
        for axis in range(3):
            if direction[axis] == 0:
                if not self.low[axis] <= point[axis] <= self.high[axis]:
                    return False
                continue
            travel = _divide(
                _subtract(
                    (self.low[axis], self.high[axis]), (point[axis], point[axis])
                ),
                (direction[axis], direction[axis]),
            )
            if not all(math.isfinite(value) for value in travel):
                return True  # Overflow/uncertainty is never an empty candidate set.
            near, far = max(near, travel[0]), min(far, travel[1])
            if near > far:
                return False
        return True


def _bounds(values: tuple[_Interval, _Interval, _Interval]) -> _Bounds | None:
    if not all(math.isfinite(value) for interval in values for value in interval):
        return None
    return _Bounds(
        (values[0][0], values[1][0], values[2][0]),
        (values[0][1], values[1][1], values[2][1]),
    )


def _face_bounds(face: Face, epsilon: float) -> _Bounds | None:
    if not all(
        math.isfinite(value)
        for vector in (face.origin, face.u, face.v)
        for value in vector
    ):
        raise InvalidInput("nonfinite direct-beam index surface")
    if (
        face.shape.is_empty
        or not face.shape.is_valid
        or not math.isfinite(face.shape.area)
        or face.shape.area <= 0
        or any(
            not math.isfinite(value)
            for ring in (face.shape.exterior, *face.shape.interiors)
            for coordinate in ring.coords
            for value in coordinate
        )
    ):
        raise InvalidInput("degenerate direct-beam index polygon")
    try:
        _ = face.normal  # Same nondegenerate basis as the exact primitive.
    except NumericalFailure as error:
        raise InvalidInput("degenerate direct-beam index surface") from error
    uu, uv, vv = _dot(face.u, face.u), _dot(face.u, face.v), _dot(face.v, face.v)
    determinant = _subtract(_multiply(uu, vv), _multiply(uv, uv))
    if determinant[0] <= 0 <= determinant[1]:
        return None
    x0, y0, x1, y1 = face.shape.bounds
    x, y = _add((x0, x1), (-epsilon, epsilon)), _add((y0, y1), (-epsilon, epsilon))
    coordinates = []
    for axis in range(3):
        u, v = (face.u[axis], face.u[axis]), (face.v[axis], face.v[axis])
        # Face.coordinates uses dot products. Its dual basis, rather than an
        # assumed exactly orthonormal frame, encloses the corresponding surface.
        a = _divide(_subtract(_multiply(vv, u), _multiply(uv, v)), determinant)
        b = _divide(_subtract(_multiply(uu, v), _multiply(uv, u)), determinant)
        coordinate = _add(
            (face.origin[axis], face.origin[axis]),
            _add(_multiply(a, x), _multiply(b, y)),
        )
        coordinates.append(_add(coordinate, (-epsilon, epsilon)))
    return _bounds((coordinates[0], coordinates[1], coordinates[2]))


def _union(items: tuple[_Bounds, ...]) -> _Bounds:
    low = tuple(min(item.low[axis] for item in items) for axis in range(3))
    high = tuple(max(item.high[axis] for item in items) for axis in range(3))
    return _Bounds(
        (low[0], low[1], low[2]),
        (high[0], high[1], high[2]),
    )


def _opaque_bounds(item: Opaque, epsilon: float) -> _Bounds | None:
    if not item.faces:
        raise InvalidInput("empty direct-beam index object")
    faces = [_face_bounds(face, epsilon) for face in item.faces]
    if (item.axis is None) != (item.height is None):
        raise InvalidInput("incomplete direct-beam index volume")
    if item.axis is not None and item.height is not None:
        if (
            not all(math.isfinite(value) for value in item.axis)
            or not math.isfinite(item.height)
            or item.height <= 0
        ):
            raise InvalidInput("degenerate direct-beam index volume")
        base = _face_bounds(item.base, epsilon)
        divisor = _dot(item.axis, item.base.normal)
        if -ANGULAR_GUARD <= divisor[0] <= divisor[1] <= ANGULAR_GUARD:
            raise InvalidInput("degenerate direct-beam index extrusion")
        if base is None or divisor[0] <= ANGULAR_GUARD and divisor[1] >= -ANGULAR_GUARD:
            return None
        # contains_receiver permits the declared extrusion height +/-epsilon.
        height = _add((0.0, item.height), (-epsilon, epsilon))
        volume = tuple(
            _add(
                (base.low[axis], base.high[axis]),
                _multiply((item.axis[axis], item.axis[axis]), height),
            )
            for axis in range(3)
        )
        faces.append(_bounds((volume[0], volume[1], volume[2])))
    if any(face is None for face in faces):
        return None
    return _union(tuple(face for face in faces if face is not None))


@dataclass(frozen=True)
class _Entry:
    item: Opaque
    bounds: _Bounds


@dataclass(frozen=True)
class _Node:
    bounds: _Bounds
    entries: tuple[_Entry, ...]
    children: tuple[_Node, ...]


def _tree(entries: tuple[_Entry, ...], leaf_size: int) -> _Node:
    bounds = _union(tuple(entry.bounds for entry in entries))
    if len(entries) <= leaf_size:
        return _Node(bounds, entries, ())
    axis = max(range(3), key=lambda index: bounds.high[index] - bounds.low[index])
    ordered = tuple(
        sorted(
            entries,
            key=lambda entry: (
                entry.bounds.low[axis] / 2 + entry.bounds.high[axis] / 2,
                entry.item.id,
                entry.item.kind,
            ),
        )
    )
    middle = len(ordered) // 2
    return _Node(
        bounds,
        (),
        (_tree(ordered[:middle], leaf_size), _tree(ordered[middle:], leaf_size)),
    )


@dataclass(frozen=True)
class CandidateQuery:
    opaque: tuple[Opaque, ...]
    bounds_tested: int


@dataclass(frozen=True)
class DirectBeamIndex:
    """Immutable scene-local BVH; leaf_size is an explicit CPU resource policy.

    query() does no exact intersection or receiver classification. The caller
    keeps the original self-module exemption, contains_receiver and ray_hit.
    Finite but uncertain bounds always remain candidates; there is no global
    cache or mutable geometry/source lookup.
    """

    epsilon_m: float
    leaf_size: int
    _root: _Node | None
    _uncertain: tuple[Opaque, ...]

    @classmethod
    def from_scene(cls, scene: Scene, *, leaf_size: int) -> DirectBeamIndex:
        if type(leaf_size) is not int or leaf_size <= 0:
            raise InvalidInput("positive direct-beam index leaf size required")
        if not math.isfinite(scene.epsilon_m) or scene.epsilon_m < 0:
            raise InvalidInput(
                "finite nonnegative direct-beam index tolerance required"
            )
        ordered = sorted(scene.opaque, key=lambda item: (item.id, item.kind))
        keys = [(item.id, item.kind) for item in ordered]
        if any(not item.id or not item.kind for item in ordered) or len(
            set(keys)
        ) != len(keys):
            raise InvalidInput("unique stable direct-beam index identities required")
        entries, uncertain = [], []
        for item in ordered:
            bounds = _opaque_bounds(item, scene.epsilon_m)
            if bounds is None:
                uncertain.append(item)
            else:
                entries.append(_Entry(item, bounds))
        return cls(
            scene.epsilon_m,
            leaf_size,
            _tree(tuple(entries), leaf_size) if entries else None,
            tuple(uncertain),
        )

    def query(
        self,
        point: Vector,
        direction: Vector,
        *,
        on_bounds_check: Callable[[], None] | None = None,
    ) -> CandidateQuery:
        if (
            not all(math.isfinite(value) for value in (*point, *direction))
            or abs(math.hypot(*direction) - 1) > ANGULAR_GUARD
        ):
            raise InvalidInput("finite point and unit direct-beam index ray required")
        found = list(self._uncertain)
        pending = [self._root] if self._root is not None else []
        tested = 0
        while pending:
            node = pending.pop()
            if on_bounds_check is not None:
                on_bounds_check()
            tested += 1
            if not node.bounds.intersects(point, direction, self.epsilon_m):
                continue
            pending.extend(node.children)
            for entry in node.entries:
                if on_bounds_check is not None:
                    on_bounds_check()
                tested += 1
                if entry.bounds.intersects(point, direction, self.epsilon_m):
                    found.append(entry.item)
        return CandidateQuery(
            tuple(sorted(found, key=lambda item: (item.id, item.kind))), tested
        )

    def upward_clearance(
        self,
        receiver_id: str,
        points: tuple[Vector, ...],
        *,
        on_bounds_check: Callable[[], None] | None = None,
    ) -> float | None:
        """Prove a horizontal sample set clear above a conservative ray slope.

        This uses the same outward bounds and negative-travel allowance as
        query(). Unknown bounds, overlapping horizontal boxes, non-horizontal
        sample sets, or a non-useful proof return None; callers then use query.
        """
        if (
            not points
            or self._uncertain
            or any(not all(math.isfinite(value) for value in point) for point in points)
        ):
            return None
        z = points[0][2]
        if any(point[2] != z for point in points):
            return None
        x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
        y0, y1 = min(p[1] for p in points), max(p[1] for p in points)
        threshold = 0.0
        pending = [self._root] if self._root is not None else []
        while pending:
            node = pending.pop()
            pending.extend(node.children)
            for entry in node.entries:
                if entry.item.kind == "module_volume" and entry.item.id == receiver_id:
                    continue
                if on_bounds_check is not None:
                    on_bounds_check()
                bounds = entry.bounds
                if math.nextafter(bounds.high[2] + self.epsilon_m, math.inf) < z:
                    continue
                gap = max(
                    bounds.low[0] - x1,
                    x0 - bounds.high[0],
                    bounds.low[1] - y1,
                    y0 - bounds.high[1],
                )
                gap = math.nextafter(gap, -math.inf)
                if not math.isfinite(gap) or gap <= self.epsilon_m:
                    return None
                margin = math.nextafter(
                    max(0.0, bounds.high[2] - z) + 2 * self.epsilon_m + 8 * math.ulp(z),
                    math.inf,
                )
                if not math.isfinite(margin):
                    return None
                threshold = max(
                    threshold, math.nextafter(margin / (gap - self.epsilon_m), math.inf)
                )
                if threshold >= 1:
                    return None
        return threshold
