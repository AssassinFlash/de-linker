"""swissBUILDINGS3D roof surfaces, read from the published DXF tiles.

swisstopo publishes swissBUILDINGS3D as a 3D model of every building in
Switzerland and Liechtenstein under terms that allow free use, distribution and
commercial exploitation with attribution. A tile is a DXF, not CityGML, so
`lod2.py`'s reader cannot take it.

The DXF carries the buildings as `AcDbPolyFaceMesh` records: a table of
`AcDbPolyFaceMeshVertex` coordinates followed by `AcDbFaceRecord` entries that
name three vertex indices. Faces carry no surface role, so walls and roofs
arrive identically and tilt separates them.

Two groupings matter and neither is optional:

1. **Faces into buildings.** A tile holds every building of a 1 km² area in one
   flat face list. Faces that share a vertex belong to one building, so the
   connected components of that relation are the buildings.
2. **Faces into roof surfaces.** One physical roof face arrives as dozens of
   triangles. Reporting each triangle would give a customer 800 "planes" for
   one gable.

Measured 2026-11-16 on tile `1166-42` (Bern): 456,411 mesh vertices and
864,537 faces, parsed in about 8 s.
"""

from __future__ import annotations

import io
import math
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import MultiPoint, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from .citygml import RoofPlane

# AutoCAD flags: a polyface mesh vertex is 64|128 = 192, a face record is 128
# alone. They are told apart by the whole value. Measured on the Bern tile, a
# bitwise mask that ignored 128 read every face as a coordinate.
_MESH_VERTEX = 192
_FACE = 128

# Layers whose contents are buildings a customer could put modules on. A wall,
# a chimney or an underground structure is not one.
BUILDING_LAYERS = frozenset(
    {
        "Gebaeude Einzelhaus",
        "Gebaeude und Anlage",
        "Offenes Gebaeude",
        "Hochhaus",
        "Sakrales Gebaeude",
        "Kapelle",
        "Flugdach",
        "Treibhaus",
    }
)

# Two triangles are one roof surface when their normals agree to this angle.
SAME_PLANE_DEG = 2.0
# A roof is not a wall. At or beyond this tilt the surface is a facade.
MAX_ROOF_TILT_DEG = 89.0
# The largest surface this tool will call a roof plane, matching the German and
# Dutch readers and the bound a visitor's drawn plane must meet.
MAX_ROOF_PLANE_M2 = 3000.0
# A gable's two halves are metres apart; anything under this is a sliver.
MIN_ROOF_PLANE_M2 = 1.0

Point3 = tuple[float, float, float]


@dataclass(frozen=True)
class Surface:
    """One roof face of one building, in the model's projected metres."""

    tilt_deg: float
    azimuth_deg: float
    area_m2: float
    # Plan-projected corners, enough to draw the face on the map.
    outline: list[tuple[float, float]]


@dataclass(frozen=True)
class BuildingSurfaces:
    """The roof faces of the building nearest a position."""

    surfaces: list[Surface]
    # Plan-projected extent of the whole building, for the click test.
    footprint: list[tuple[float, float]]
    distance_m: float


def _pairs(text: str) -> list[tuple[int, str]]:
    """DXF group codes: a code line followed by its value line, in order."""
    lines = text.splitlines()
    pairs: list[tuple[int, str]] = []
    index = 0
    while index < len(lines) - 1:
        code = lines[index].strip()
        if code.lstrip("-").isdigit():
            pairs.append((int(code), lines[index + 1].strip()))
            index += 2
            continue
        index += 1
    return pairs


def _iter_pairs(stream: io.TextIOBase) -> Iterator[tuple[int, str]]:
    """Stream DXF group codes two lines at a time without loading the file."""
    while True:
        code_line = stream.readline()
        if not code_line:
            break
        code_str = code_line.strip()
        if not code_str.lstrip("-").isdigit():
            continue
        value_line = stream.readline()
        if not value_line:
            break
        yield int(code_str), value_line.strip()


def _parse_vertex_record(
    record: list[tuple[int, str]],
    b_vertices: list[Point3],
    b_faces: list[tuple[int, int, int]],
) -> tuple[float, float] | None:
    """Parse one VERTEX record into building-local vertices or faces."""
    if not record or record[0][1] != "VERTEX":
        return None
    fields = {code: value for code, value in record}
    flag = int(fields.get(70, "0") or 0)
    if flag == _MESH_VERTEX:
        try:
            x = float(fields[10])
            y = float(fields[20])
            z = float(fields.get(30, "0.0"))
        except (KeyError, ValueError):
            return None
        b_vertices.append((x, y, z))
        return (x, y)
    if flag == _FACE:
        try:
            indices = [int(fields[key]) for key in (71, 72, 73) if key in fields]
        except ValueError:
            return None
        if len(indices) < 3:
            return None
        triangle = (indices[0] - 1, indices[1] - 1, indices[2] - 1)
        if all(0 <= index < len(b_vertices) for index in triangle):
            b_faces.append(triangle)
    return None


def read_archive(
    archive: bytes | Path,
    *,
    target: tuple[float, float] | None = None,
    radius_m: float = 80.0,
) -> Tile:
    """Stream one published tile archive into buildings and faces.

    When `target` is given, only buildings whose XY bounding box comes within
    `radius_m` of `target` are retained so full-tile memory stays bounded.
    """
    source: Path | io.BytesIO = (
        archive if isinstance(archive, Path) else io.BytesIO(archive)
    )
    vertices: list[Point3] = []
    faces: list[tuple[int, int, int]] = []
    owners: list[int] = []
    building = -1

    b_vertices: list[Point3] = []
    b_faces: list[tuple[int, int, int]] = []
    min_x = math.inf
    max_x = -math.inf
    min_y = math.inf
    max_y = -math.inf
    in_polyline = False
    pending: list[tuple[int, str]] = []

    def flush_building() -> None:
        nonlocal building, b_vertices, b_faces, min_x, max_x, min_y, max_y
        if b_faces:
            keep = target is None or (
                min_x - radius_m <= target[0] <= max_x + radius_m
                and min_y - radius_m <= target[1] <= max_y + radius_m
            )
            if keep:
                building += 1
                offset = len(vertices)
                vertices.extend(b_vertices)
                for a, b, c in b_faces:
                    faces.append((offset + a, offset + b, offset + c))
                    owners.append(building)
        b_vertices = []
        b_faces = []
        min_x = math.inf
        max_x = -math.inf
        min_y = math.inf
        max_y = -math.inf

    def flush_record() -> None:
        nonlocal min_x, max_x, min_y, max_y, pending
        if in_polyline and pending:
            point = _parse_vertex_record(pending, b_vertices, b_faces)
            if point is not None:
                px, py = point
                if px < min_x:
                    min_x = px
                if px > max_x:
                    max_x = px
                if py < min_y:
                    min_y = py
                if py > max_y:
                    max_y = py
        pending = []

    with zipfile.ZipFile(source) as bundle:
        name = next(
            (item for item in bundle.namelist() if item.lower().endswith(".dxf")),
            None,
        )
        if name is None:
            raise ValueError("the tile carries no DXF")
        with (
            bundle.open(name) as raw,
            io.TextIOWrapper(raw, encoding="utf-8", errors="replace") as stream,
        ):
            for code, value in _iter_pairs(stream):
                if code == 0:
                    flush_record()
                    if value == "POLYLINE":
                        flush_building()
                        in_polyline = True
                    elif value == "SEQEND":
                        flush_building()
                        in_polyline = False
                if in_polyline:
                    pending.append((code, value))
            flush_record()
            flush_building()
    return Tile(vertices=vertices, faces=faces, owners=owners)


def parse(pairs: list[tuple[int, str]]) -> Tile:
    """Every mesh vertex and face of the tile, grouped per building.

    The DXF groups them already: one `POLYLINE` record is followed by that
    building's vertices and face records. Measured 2026-11-16 on the Bern tile,
    there are 10,934 polylines and 864,537 faces. Grouping by shared vertices
    instead merges the whole tile into one building, because neighbouring
    buildings reference adjacent entries of the same flat vertex table.

    A face record numbers its vertices from 1 **within its own polyline**, not
    in the file's vertex table. Read as a global index, a face inside the tenth
    building points at the vertices of the first, which produces surfaces of
    thousands of square metres from unrelated corners of the tile.
    """
    vertices: list[Point3] = []
    faces: list[tuple[int, int, int]] = []
    owners: list[int] = []
    pending: list[tuple[int, str]] = []
    building = -1
    offset = 0
    for code, value in pairs:
        if code == 0:
            _record(pending, vertices, faces, owners, building, offset)
            pending = []
            if value == "POLYLINE":
                building += 1
                offset = len(vertices)
        pending.append((code, value))
    _record(pending, vertices, faces, owners, building, offset)
    return Tile(vertices=vertices, faces=faces, owners=owners)


def _record(
    record: list[tuple[int, str]],
    vertices: list[Point3],
    faces: list[tuple[int, int, int]],
    owners: list[int],
    building: int,
    offset: int,
) -> None:
    """Read one DXF record, appending a vertex or a face."""
    if not record or record[0][1] != "VERTEX":
        return
    fields = {code: value for code, value in record}
    flag = int(fields.get(70, "0") or 0)
    if flag == _MESH_VERTEX:
        try:
            vertices.append(
                (float(fields[10]), float(fields[20]), float(fields.get(30, "0.0")))
            )
        except (KeyError, ValueError):
            return
        return
    if flag == _FACE:
        try:
            indices = [int(fields[key]) for key in (71, 72, 73) if key in fields]
        except ValueError:
            return
        if len(indices) < 3:
            return
        # Local to this polyline, numbered from 1.
        triangle = (
            offset + indices[0] - 1,
            offset + indices[1] - 1,
            offset + indices[2] - 1,
        )
        if all(0 <= index < len(vertices) for index in triangle):
            faces.append(triangle)
            owners.append(building)


@dataclass
class Tile:
    """One parsed tile: the mesh vertices, the triangles, and their building.

    The grid index is built on first use and kept, because a tile answers many
    positions and rebuilding the index costs more than the lookup.
    """

    vertices: list[Point3]
    faces: list[tuple[int, int, int]]
    owners: list[int]
    _grid: _Grid | None = None

    def buildings(self) -> dict[int, list[int]]:
        """Face indices grouped by the POLYLINE that carries them."""
        grouped: dict[int, list[int]] = {}
        for position, owner in enumerate(self.owners):
            grouped.setdefault(owner, []).append(position)
        return grouped

    def nearest(
        self, x: float, y: float, tolerance_m: float
    ) -> BuildingSurfaces | None:
        """The building whose plan projection is closest to a position.

        A tile holds the whole 1 km² area, so a scan over every triangle would
        cost seconds per request: measured 2026-11-16, an unindexed pass over
        the Bern tile's 864,537 faces did not finish in five minutes. Faces are
        binned into a grid once per tile and only the bins around the position
        are searched.
        """
        if self._grid is None:
            self._grid = _Grid(self)
        grid = self._grid
        best: tuple[float, int] | None = None
        for number in grid.near(x, y, tolerance_m):
            distance = _component_distance(self, grid.components[number], x, y)
            if distance <= tolerance_m and (best is None or distance < best[0]):
                best = (distance, number)
        if best is None:
            return None
        distance, number = best
        component = grid.components[number]
        return BuildingSurfaces(
            surfaces=_surfaces(self, component),
            footprint=_hull_points(self, component),
            distance_m=round(distance, 2),
        )


# One grid cell in metres. A building spans a few cells, so a position has to
# scan its own cell and its neighbours.
CELL_M = 32.0


class _Grid:
    """Face bins over the tile, plus the face-to-building map, built once."""

    def __init__(self, tile: Tile) -> None:
        self.components = tile.buildings()
        self._owner_of = list(tile.owners)
        self._cells: dict[tuple[int, int], set[int]] = {}
        for position, triangle in enumerate(tile.faces):
            key = self._key(tile.vertices[triangle[0]])
            self._cells.setdefault(key, set()).add(position)

    @staticmethod
    def _key(vertex: Point3) -> tuple[int, int]:
        return (int(vertex[0] // CELL_M), int(vertex[1] // CELL_M))

    def near(self, x: float, y: float, tolerance_m: float) -> set[int]:
        """Building numbers whose faces sit in the cells around a position.

        A face is binned by one of its vertices, so the search reaches far
        enough to cover a whole building: a roof whose first vertex is one cell
        away still belongs to the building under the position.
        """
        span = max(2, int(math.ceil(tolerance_m / CELL_M)) + 2)
        cell = (int(x // CELL_M), int(y // CELL_M))
        buildings: set[int] = set()
        for dx in range(-span, span + 1):
            for dy in range(-span, span + 1):
                for position in self._cells.get((cell[0] + dx, cell[1] + dy), ()):
                    number = self._owner_of[position]
                    if number >= 0:
                        buildings.add(number)
        return buildings


def _normal(a: Point3, b: Point3, c: Point3) -> Point3:
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def _agrees(first: Point3, second: Point3) -> bool:
    if first == (0.0, 0.0, 0.0) or second == (0.0, 0.0, 0.0):
        return False
    dot = abs(sum(a * b for a, b in zip(first, second, strict=True)))
    return dot >= math.cos(math.radians(SAME_PLANE_DEG))


def _shares_edge(first: tuple[int, int, int], second: tuple[int, int, int]) -> bool:
    return len(set(first) & set(second)) >= 2


def _surfaces(tile: Tile, component: list[int]) -> list[Surface]:
    """Merge one building's coplanar connected triangles into roof faces."""
    normals = {
        position: _normal(*(tile.vertices[index] for index in tile.faces[position]))
        for position in component
    }

    parent = {position: position for position in component}

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(first: int, second: int) -> None:
        a, b = find(first), find(second)
        if a != b:
            parent[b] = a

    # Adjacency is only worth testing between faces that already share a vertex.
    by_vertex: dict[int, list[int]] = {}
    for position in component:
        for index in tile.faces[position]:
            by_vertex.setdefault(index, []).append(position)
    for sharing in by_vertex.values():
        for outer in range(len(sharing)):
            for inner in range(outer + 1, len(sharing)):
                first, second = sharing[outer], sharing[inner]
                if _shares_edge(tile.faces[first], tile.faces[second]) and _agrees(
                    normals[first], normals[second]
                ):
                    union(first, second)

    grouped: dict[int, list[int]] = {}
    for position in component:
        grouped.setdefault(find(position), []).append(position)

    surfaces: list[Surface] = []
    for members in grouped.values():
        surface = _surface(tile, members, normals)
        if surface is not None:
            surfaces.append(surface)
    return surfaces


def _surface(
    tile: Tile, members: list[int], normals: dict[int, Point3]
) -> Surface | None:
    """Tilt, facing, true area and outline of one merged roof face."""
    nx = ny = nz = 0.0
    area = 0.0
    for position in members:
        a, b, c = (tile.vertices[index] for index in tile.faces[position])
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        area += math.sqrt(cx * cx + cy * cy + cz * cz) / 2
        normal = normals[position]
        nx += normal[0]
        ny += normal[1]
        nz += normal[2]
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-9 or area < MIN_ROOF_PLANE_M2 or area > MAX_ROOF_PLANE_M2:
        return None
    nx, ny, nz = nx / length, ny / length, nz / length
    if nz < 0:
        nx, ny, nz = -nx, -ny, -nz
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, nz))))
    if tilt >= MAX_ROOF_TILT_DEG:
        return None
    azimuth = (math.degrees(math.atan2(nx, ny)) + 360) % 360
    tilt_deg = round(tilt, 1)
    area_m2 = round(area, 2)
    if (
        tilt_deg < 0.0
        or tilt_deg >= MAX_ROOF_TILT_DEG
        or area_m2 < MIN_ROOF_PLANE_M2
        or area_m2 > MAX_ROOF_PLANE_M2
    ):
        return None
    outline = _hull_points(tile, members)
    if len(outline) < 3:
        return None
    azimuth_deg = round(azimuth, 1) % 360.0
    return Surface(
        tilt_deg=tilt_deg,
        azimuth_deg=azimuth_deg,
        area_m2=area_m2,
        outline=outline,
    )


def _component_distance(tile: Tile, component: list[int], x: float, y: float) -> float:
    """Plan distance from a position to the nearest triangle of a building."""
    best = math.inf
    for position in component:
        projected = [
            (tile.vertices[index][0], tile.vertices[index][1])
            for index in tile.faces[position]
        ]
        if _inside(projected, x, y):
            return 0.0
        best = min(best, _ring_distance(projected, x, y))
    return best


def _hull_points(tile: Tile, component: list[int]) -> list[tuple[float, float]]:
    """Clean, non-self-intersecting counter-clockwise plan outline of faces."""
    triangles: list[Polygon] = []
    pts: list[tuple[float, float]] = []
    seen: dict[tuple[float, float], None] = {}
    for position in component:
        tri_pts: list[tuple[float, float]] = []
        for index in tile.faces[position]:
            vertex = tile.vertices[index]
            pt = (vertex[0], vertex[1])
            tri_pts.append(pt)
            pts.append(pt)
            seen[(round(vertex[0], 2), round(vertex[1], 2))] = None
        if len(tri_pts) >= 3:
            poly = Polygon(tri_pts)
            if poly.is_valid and not poly.is_empty and poly.area > 1e-6:
                triangles.append(poly)
    ring_poly: Polygon | None = None
    if triangles:
        merged = unary_union(triangles)
        if (
            isinstance(merged, Polygon)
            and merged.is_valid
            and not merged.is_empty
            and merged.area > 1e-6
        ):
            ring_poly = merged
    if ring_poly is None and len(pts) >= 3:
        hull = MultiPoint(pts).convex_hull
        if (
            isinstance(hull, Polygon)
            and hull.is_valid
            and not hull.is_empty
            and hull.area > 1e-6
        ):
            ring_poly = hull
    if ring_poly is not None:
        ccw = orient(ring_poly, sign=1.0)
        coords = [(round(x, 2), round(y, 2)) for x, y in ccw.exterior.coords[:-1]]
        deduped: list[tuple[float, float]] = []
        for coord in coords:
            if not deduped or coord != deduped[-1]:
                deduped.append(coord)
        if len(deduped) > 1 and deduped[0] == deduped[-1]:
            deduped.pop()
        if len(deduped) >= 3:
            return deduped
    return list(seen)


def _ring_distance(points: list[tuple[float, float]], x: float, y: float) -> float:
    best = math.inf
    for index in range(len(points)):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % len(points)]
        dx, dy = x2 - x1, y2 - y1
        span = dx * dx + dy * dy
        if span <= 0:
            best = min(best, math.hypot(x - x1, y - y1))
            continue
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / span))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


def _inside(points: list[tuple[float, float]], x: float, y: float) -> bool:
    crossings = 0
    count = len(points)
    for index in range(count):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % count]
        if (y1 > y) != (y2 > y):
            if x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                crossings += 1
    return crossings % 2 == 1


def planes(surfaces: list[Surface]) -> list[RoofPlane]:
    """The published `RoofPlane` shape the rest of the roof service reads."""
    return [
        RoofPlane(
            ring=[(x, y) for x, y in surface.outline],
            tilt_deg=surface.tilt_deg,
            azimuth_deg=surface.azimuth_deg,
            area_m2=surface.area_m2,
        )
        for surface in surfaces
    ]
