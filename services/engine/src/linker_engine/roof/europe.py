"""Documented 3D building models outside Germany, fetched per position.

Germany publishes LoD2 CityGML per federal state and `lod2.py` reads it. Two
other European countries publish a nationwide model with roof surfaces at the
same level, and this module reads them:

- **NL** — 3D BAG (TU Delft / 3DGI), CC BY 4.0. An OGC API returns CityJSON for
  a bounding box; each building carries its roof surfaces as `MultiSurface`
  geometry with an explicit level of detail.
- **CH** — swissBUILDINGS3D, published by swisstopo for free reuse with
  attribution. Its per-tile downloads are read the same way once a tile is
  located for the position.

Measured 2026-11-15 against the live Dutch service: a query at Amsterdam's
centre returns one building with `b3_dak_type=slanted`, ridge height 15.0 m,
eave 7.47 m, four storeys and a `MultiSurface` roof. The response is real
geometry, not footprints.

Anything else in Europe publishes footprints only. There the roof's pitch and
facing come from the customer or from the plane they draw, which `pack_drawn`
already handles.
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, cast

from pyproj import Transformer

from .citygml import Building, RoofPlane, plane_of

USER_AGENT = "linker-engine (de-linker.com Solution Configurator)"

# The Dutch model is published in EPSG:7415 (RD New + NAP); a bounding box in
# degrees returns nothing, which the service proves by answering an empty set.
DUTCH_CRS = "EPSG:7415"
DUTCH_ENDPOINT = "https://api.3dbag.nl/collections/pand/items"
# The API caps a page; one building's neighbours are enough to pick from.
DUTCH_LIMIT = 8

# A position is inside this many metres of a building to select it, matching
# the German path's click tolerance.
CLICK_TOLERANCE_M = 3.0

LICENCES = {
    "NL": "CC BY 4.0 (3D BAG, TU Delft / 3DGI)",
    "CH": "swisstopo free geodata, attribution required",
}


class ModelUnavailable(RuntimeError):
    """No documented 3D model could be read for the position."""


@dataclass(frozen=True)
class ModelResult:
    country: str
    buildings: list[Building]
    licence: str
    # Coordinates are returned in the model's own projected CRS so the caller
    # can reproduce the same rings for the map.
    transformer: Transformer


def _dutch_bbox(latitude: float, longitude: float, metres: float) -> str:
    to_rd = Transformer.from_crs("EPSG:4326", DUTCH_CRS, always_xy=True)
    x, y = to_rd.transform(longitude, latitude)
    return f"{x - metres},{y - metres},{x + metres},{y + metres}"


def _fetch_dutch(latitude: float, longitude: float) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {"limit": DUTCH_LIMIT, "bbox": _dutch_bbox(latitude, longitude, 30.0)}
    )
    request = urllib.request.Request(
        f"{DUTCH_ENDPOINT}?{query}",
        headers={"Accept": "application/geo+json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return cast(dict[str, Any], json.load(response))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise ModelUnavailable(f"3D BAG did not answer: {error}") from error


def _ring(
    points: list[Any],
    vertices: list[list[float]],
    offset: list[float],
    scale: list[float],
) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    for index in points:
        vertex = vertices[index]
        out.append(
            (
                vertex[0] * scale[0] + offset[0],
                vertex[1] * scale[1] + offset[1],
                vertex[2] * scale[2] + offset[2],
            )
        )
    return out


def _dutch_buildings(document: dict[str, Any]) -> list[Building]:
    """Roof surfaces of every building in the answer.

    CityJSON stores one vertex table per document and indexes it per surface,
    so the rings are rebuilt here before `plane_of` measures them. Only the
    surfaces belonging to a roof are kept: a building's walls and floor carry
    no module.
    """
    transform = document.get("transform") or {}
    scale = [float(v) for v in transform.get("scale", [1.0, 1.0, 1.0])]
    offset = [float(v) for v in transform.get("translate", [0.0, 0.0, 0.0])]
    vertices = cast(list[list[float]], document.get("vertices") or [])
    buildings: list[Building] = []
    for feature in cast(list[dict[str, Any]], document.get("features") or []):
        objects = cast(dict[str, Any], feature.get("CityObjects") or {})
        for object_id, item in objects.items():
            attributes = cast(dict[str, Any], item.get("attributes") or {})
            # The published roof type is a documented fact about the building,
            # not something derived from a point cloud here.
            if attributes.get("b3_dak_type") == "no_roof":
                continue
            planes: list[RoofPlane] = []
            footprint: list[list[tuple[float, float]]] = []
            for geometry in cast(list[dict[str, Any]], item.get("geometry") or []):
                lod = str(geometry.get("lod", ""))
                boundaries = cast(list[Any], geometry.get("boundaries") or [])
                if not boundaries:
                    continue
                # LoD 2 carries the roof surfaces; LoD 0/1 is the extrusion
                # envelope, whose top face is not a roof plane of the building.
                surfaces = cast(list[list[list[int]]], boundaries[0])
                for surface in surfaces:
                    if not surface:
                        continue
                    ring = _ring(surface[0], vertices, offset, scale)
                    if lod.startswith("2"):
                        plane = plane_of(ring)
                        if plane is not None:
                            planes.append(plane)
                    elif lod.startswith("0") or lod.startswith("1"):
                        footprint.append([(x, y) for x, y, _ in ring])
            if planes:
                buildings.append(
                    Building(
                        id=object_id,
                        address=None,
                        footprint=footprint,
                        planes=planes,
                    )
                )
    return buildings


def documented_models() -> dict[str, str]:
    """The countries whose official model this module can read, and its licence."""
    return dict(LICENCES)


def read(country: str, latitude: float, longitude: float) -> ModelResult | None:
    """The official 3D model at a position, or None where none is published.

    Only the Dutch model is read today; Switzerland's tiles need a lookup of
    their own and are named in `documented_models` so the caller can tell
    "no model exists" from "not implemented yet".
    """
    if country != "NL":
        return None
    document = _fetch_dutch(latitude, longitude)
    buildings = _dutch_buildings(document)
    if not buildings:
        return None
    return ModelResult(
        country="NL",
        buildings=buildings,
        licence=LICENCES["NL"],
        transformer=Transformer.from_crs(DUTCH_CRS, "EPSG:4326", always_xy=True),
    )


def distance_m(ring: list[tuple[float, float]], x: float, y: float) -> float:
    """Distance from a point to a footprint, in the model's own metres.

    Zero inside the ring: a click within a building selects that building, and
    the caller compares the answer with a tolerance. The edge distance alone
    would report a point in the middle of a large building as metres away.
    """
    if _inside(ring, x, y):
        return 0.0
    best = math.inf
    for index in range(len(ring)):
        x1, y1 = ring[index]
        x2, y2 = ring[(index + 1) % len(ring)]
        dx, dy = x2 - x1, y2 - y1
        span = dx * dx + dy * dy
        if span <= 0:
            best = min(best, math.hypot(x - x1, y - y1))
            continue
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / span))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


def _inside(ring: list[tuple[float, float]], x: float, y: float) -> bool:
    """Crossing-number test: odd crossings mean the point is inside."""
    inside = False
    for index in range(len(ring)):
        x1, y1 = ring[index]
        x2, y2 = ring[(index + 1) % len(ring)]
        if (y1 > y) != (y2 > y):
            crossing = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < crossing:
                inside = not inside
    return inside
