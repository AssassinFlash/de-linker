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

import http.client
import json
import math
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from pyproj import Transformer

from . import swiss
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

# The largest surface this tool will call a roof plane. The bound is the same
# one a visitor's drawn plane must meet (`MAX_DRAWN_PLANE_M2`), and it is what
# separates a roof from the walls and ground slab that CityJSON puts in the
# same MultiSurface.
MAX_ROOF_PLANE_M2 = 3000.0

LICENCES = {
    "NL": "CC BY 4.0 (3D BAG, TU Delft / 3DGI)",
    "CH": "swisstopo free geodata, attribution required",
    "LI": "swisstopo free geodata, attribution required",
}

# Each model is published in its own national grid; the rings are transformed
# back to WGS84 for the map and the report.
CRS = {"NL": DUTCH_CRS, "CH": "EPSG:2056", "LI": "EPSG:2056"}
MAX_SWISS_CACHE_FILES = 6


def model_crs(country: str) -> str:
    """The projected CRS a country's model answers in."""
    return CRS[country]


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


def _fetch_dutch(
    latitude: float, longitude: float, *, search_m: float = 30.0
) -> dict[str, Any]:
    """The building page for a position, with one retry on a short read.

    Measured 2026-11-15: the same service occasionally closes a chunked body
    before its last chunk (`IncompleteRead: 36731 bytes read, 9998 more
    expected`). A second attempt answers in full, so one retry covers it and a
    persistent failure still surfaces as unavailable.
    """
    query = urllib.parse.urlencode(
        {"limit": DUTCH_LIMIT, "bbox": _dutch_bbox(latitude, longitude, search_m)}
    )
    url = f"{DUTCH_ENDPOINT}?{query}"
    last: Exception | None = None
    for _attempt in range(2):
        request = urllib.request.Request(
            url, headers={"Accept": "application/geo+json", "User-Agent": USER_AGENT}
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return cast(dict[str, Any], json.load(response))
        except http.client.IncompleteRead as error:
            last = error
            continue
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            raise ModelUnavailable(f"3D BAG did not answer: {error}") from error
    raise ModelUnavailable(f"3D BAG read was truncated twice: {last}")


def _rings(node: Any) -> list[list[int]]:
    """Every ring under a CityJSON `boundaries` value, at whatever depth it sits.

    The specification nests one level per dimension, but a `Surface` and a
    `CompositeSurface` differ by one: the Dutch roof geometry measured on
    2026-11-15 arrives as `[ring]` where the fixture had `[surface[ring]]`. A
    depth-first walk takes both, and an empty or malformed branch contributes
    nothing rather than raising.
    """
    if not isinstance(node, list) or not node:
        return []
    if all(isinstance(item, int) for item in node):
        return [cast(list[int], node)]
    out: list[list[int]] = []
    for item in node:
        out.extend(_rings(item))
    return out


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


def _transform(
    document: dict[str, Any], feature: dict[str, Any]
) -> tuple[list[float], list[float]]:
    """The affine a feature's integer vertices are stored in.

    CityJSON lets the transform sit at three depths and the Dutch service uses
    the deepest: measured 2026-11-15, `document["metadata"]["metadata"]
    ["transform"]` carries `scale 0.001` and a `translate` near 121497, 487042
    — RD New metres — while the document and the feature both have no
    `transform` key at all. Reading the shallow places gave scale 1 and
    translate 0, which turned one building's ground slab into 94 km².
    """
    for holder in (
        feature.get("transform"),
        document.get("transform"),
        (document.get("metadata") or {}).get("transform"),
        ((document.get("metadata") or {}).get("metadata") or {}).get("transform"),
    ):
        if isinstance(holder, dict):
            scale = [float(v) for v in holder.get("scale", [1.0, 1.0, 1.0])]
            offset = [float(v) for v in holder.get("translate", [0.0, 0.0, 0.0])]
            return scale, offset
    return [1.0, 1.0, 1.0], [0.0, 0.0, 0.0]


def _dutch_buildings(document: dict[str, Any]) -> list[Building]:
    """Roof surfaces of every building in the answer.

    The vertex table sits on each feature, not on the document: measured
    2026-11-15 against the live service, `document["vertices"]` is empty and
    `feature["vertices"]` holds 118 entries for one building. Reading the
    document table indexes nothing. Only roof surfaces are kept — a building's
    walls and floor carry no module.
    """
    buildings: list[Building] = []
    for feature in cast(list[dict[str, Any]], document.get("features") or []):
        objects = cast(dict[str, Any], feature.get("CityObjects") or {})
        scale, offset = _transform(document, feature)
        vertices = cast(
            list[list[float]], feature.get("vertices") or document.get("vertices") or []
        )
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
                # CityJSON nests one level per dimension, but the levels present
                # depend on the surface type: a CompositeSurface is
                # `[surface[ring[index]]]`, while a plain Surface is
                # `[ring[index]]`. Measured 2026-11-15 against the live Dutch
                # service, the roof geometry arrives one level shallower than the
                # fixture assumed, so the depth is read rather than trusted.
                for indices in _rings(boundaries):
                    ring = _ring(indices, vertices, offset, scale)
                    if lod.startswith("2"):
                        plane = plane_of(ring)
                        # CityJSON has no `RoofSurface` element: a building's
                        # roof, walls and floor are all surfaces of the same
                        # MultiSurface. Measured 2026-11-15, taking every LoD 2
                        # surface gave one Amsterdam building 52 "roof planes"
                        # of up to 94,892,716 m² — the walls and the ground
                        # slab. A roof plane is not vertical and is not larger
                        # than any plane this tool would let a visitor draw.
                        if (
                            plane is not None
                            and plane.tilt_deg < 89.0
                            and 0.5 <= plane.area_m2 <= MAX_ROOF_PLANE_M2
                        ):
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

    The Netherlands and Switzerland both publish a nationwide model with roof
    surfaces. Every other country in the service area publishes footprints
    only, and there the pitch and facing come from the customer or from the
    plane they draw, which `pack_drawn` already handles.
    """
    if country == "NL":
        document = _fetch_dutch(latitude, longitude)
        buildings = _dutch_buildings(document)
        if not buildings:
            document = _fetch_dutch(latitude, longitude, search_m=60.0)
            buildings = _dutch_buildings(document)
        if not buildings:
            return None
        return ModelResult(
            country="NL",
            buildings=buildings,
            licence=LICENCES["NL"],
            transformer=Transformer.from_crs(DUTCH_CRS, "EPSG:4326", always_xy=True),
        )
    if country in ("CH", "LI"):
        return _read_swiss(latitude, longitude, country=country, tolerance_m=60.0)
    return None


# swisstopo publishes swissBUILDINGS3D as 1 km² tiles on a fixed EPSG:2056 grid.
SWISS_STAC = "https://data.geo.admin.ch/api/stac/v0.9"
SWISS_COLLECTION = "ch.swisstopo.swissbuildings3d_2"
# The tile grid step in metres: measured 2026-11-16, tile `1166-42` covers
# 7.414-7.471 E and 46.924-46.951 N, so one step is 1000 m of the projected grid.
SWISS_TILE_M = 1000.0


def _swiss_tile_name(x: float, y: float) -> str:
    """The tile identifier covering a position on the published grid."""
    return f"{int(x // SWISS_TILE_M)}-{int(y // SWISS_TILE_M)}"


def _swiss_cache_dir() -> Path:
    root = Path(os.environ.get("LINKER_ENGINE_CACHE") or "/tmp/linker-engine-cache")
    directory = root / "swiss"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _prune_swiss_cache(directory: Path) -> None:
    files = sorted(
        directory.glob("*.dxf.zip"),
        key=lambda item: item.stat().st_mtime,
    )
    for stale in files[:-MAX_SWISS_CACHE_FILES]:
        stale.unlink(missing_ok=True)


def _read_swiss(
    latitude: float,
    longitude: float,
    *,
    country: str = "CH",
    tolerance_m: float = CLICK_TOLERANCE_M * 4,
) -> ModelResult | None:
    """Roof surfaces of the buildings near a Swiss or Liechtenstein position.

    The tile is 16 MB compressed and hundreds of MB expanded, so the zip is
    cached on disk (bounded LRU) and streamed with target filtering.

    The STAC search takes a WGS84 bbox, not the model's own metres: measured
    2026-11-16, sending EPSG:2056 metres answers `HTTP 400 Bad Request`.
    """
    to_lv95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)
    x, y = to_lv95.transform(longitude, latitude)
    tile = _swiss_tile(x, y, latitude, longitude)
    if tile is None:
        return None
    found = tile.nearest(x, y, tolerance_m)
    if found is None or not found.surfaces:
        return None
    building = Building(
        id=f"{country} {_swiss_tile_name(x, y)}",
        address=None,
        footprint=[found.footprint],
        planes=[
            RoofPlane(
                ring=surface.outline,
                tilt_deg=surface.tilt_deg,
                azimuth_deg=surface.azimuth_deg,
                area_m2=surface.area_m2,
            )
            for surface in found.surfaces
        ],
    )
    return ModelResult(
        country=country,
        buildings=[building],
        licence=LICENCES[country],
        transformer=Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True),
    )


def _swiss_tile(
    x: float, y: float, latitude: float, longitude: float
) -> swiss.Tile | None:
    """Download to bounded disk LRU cache and stream-parse around `(x, y)`."""
    span = 0.01
    url = (
        f"{SWISS_STAC}/collections/{SWISS_COLLECTION}/items"
        f"?bbox={longitude - span},{latitude - span},"
        f"{longitude + span},{latitude + span}&limit=50"
    )
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": USER_AGENT}),
            timeout=120,
        ) as response:
            document = cast(dict[str, Any], json.load(response))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise ModelUnavailable(
            f"swissBUILDINGS3D index did not answer: {error}"
        ) from error

    candidates: list[tuple[float, str, str]] = []
    for feature in cast(list[dict[str, Any]], document.get("features") or []):
        assets = cast(dict[str, Any], feature.get("assets") or {})
        href = next(
            (
                str(asset.get("href", ""))
                for asset in assets.values()
                if str(asset.get("href", "")).endswith(".dxf.zip")
            ),
            None,
        )
        if href is None:
            continue
        bbox = feature.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        west, south, east, north = (float(value) for value in bbox)
        if not (west <= longitude <= east and south <= latitude <= north):
            continue
        raw_id = str(
            feature.get("id")
            or Path(urllib.parse.urlparse(href).path).name.removesuffix(".dxf.zip")
            or _swiss_tile_name(x, y)
        )
        tile_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_id) or _swiss_tile_name(x, y)
        candidates.append(((east - west) * (north - south), tile_id, href))
    if not candidates:
        return None
    candidates.sort()
    _, tile_id, href = candidates[0]
    directory = _swiss_cache_dir()
    zip_path = directory / f"{tile_id}.dxf.zip"
    if zip_path.exists():
        zip_path.touch()
    else:
        tmp_path: Path | None = None
        try:
            with urllib.request.urlopen(
                urllib.request.Request(href, headers={"User-Agent": USER_AGENT}),
                timeout=180,
            ) as response:
                with tempfile.NamedTemporaryFile(
                    dir=directory, suffix=".part", delete=False
                ) as handle:
                    tmp_path = Path(handle.name)
                    while chunk := response.read(65536):
                        handle.write(chunk)
            os.replace(tmp_path, zip_path)
            _prune_swiss_cache(directory)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)
            raise ModelUnavailable(
                f"swissBUILDINGS3D tile did not download: {error}"
            ) from error
    return swiss.read_archive(
        zip_path, target=(x, y), radius_m=max(60.0, CLICK_TOLERANCE_M * 8)
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
