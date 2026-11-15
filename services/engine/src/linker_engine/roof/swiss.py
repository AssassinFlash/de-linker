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
from dataclasses import dataclass

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


def read_archive(archive: bytes) -> Tile:
    """Parse one published tile archive into buildings and faces."""
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        name = next(
            (item for item in bundle.namelist() if item.lower().endswith(".dxf")),
            None,
        )
        if name is None:
            raise ValueError("the tile carries no DXF")
        text = bundle.read(name).decode("utf-8", errors="replace")
    return parse(_pairs(text))


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
    return Surface(
        tilt_deg=round(tilt, 1),
        azimuth_deg=round(azimuth, 1),
        area_m2=round(area, 2),
        outline=_hull_points(tile, members),
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
    """Plan-projected vertices used by a set of faces, deduplicated."""
    seen: dict[tuple[float, float], None] = {}
    for position in component:
        for index in tile.faces[position]:
            vertex = tile.vertices[index]
            seen[(round(vertex[0], 2), round(vertex[1], 2))] = None
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
