"""Building outlines from the Microsoft global building footprints.

Where a country publishes no roof geometry, the position still sits inside a
real building, and the customer still wants the plan and the pitch they can see.
The Microsoft Global Building Footprints cover every country on earth as
GeoJSON outlines, published as open data (CDLA-Permissive 2.0), one gzipped
part per Bing quadkey cell.

The outline is what the model supplies; the pitch is the customer's, entered on
the map. That is a different claim from the Dutch and Swiss models, so the
result names its own source and licence and the caller must present it as an
outline rather than a measured roof.

Measured 2026-11-16: the part for quadkey `120230113` (Vienna centre) is 38 MB
compressed and holds 320,031 outlines, each a GeoJSON Polygon ring.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from functools import cache
from http.client import IncompleteRead
from pathlib import Path
from typing import Any, cast

USER_AGENT = "linker-engine (de-linker.com Solution Configurator)"

CATALOGUE = (
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"
)

# The catalogue keys each part by the quadkey of the Bing cell it covers. Zoom
# 9 is the resolution the published parts use; a position's own cell is looked
# up at the same zoom so the key matches.
ZOOM = 9

# A position belongs to the building whose outline it falls inside, or barring
# that the nearest one within this distance.
CLICK_TOLERANCE_M = 12.0
# Postcode centroids sit near a street or square centre rather than on a roof.
CENTROID_TOLERANCE_M = 60.0

# Consecutive points closer than this are one corner of a raster-derived
# outline, and keeping them all would give a 300-point ring for a rectangle.
SAME_POINT_M = 0.35

# The catalogue names regions in English, while the service speaks ISO codes.
# Measured 2026-11-16 against `dataset-links.csv`: 225 regions, of which these
# are the European ones the configurator serves.
REGION_NAMES = {
    "AD": "Andorra",
    "AL": "Albania",
    "AT": "Austria",
    "AX": "Finland",
    "BA": "Bosnia and Herzegovina",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "BY": "Belarus",
    "CH": "Switzerland",
    "CY": "Cyprus",
    "CZ": "Czechia",
    "DE": "Germany",
    "DK": "Denmark",
    "EE": "Estonia",
    "ES": "Spain",
    "FI": "Finland",
    "FO": "Faroe Islands",
    "FR": "France",
    "GB": "United Kingdom",
    "GG": "Guernsey",
    "GI": "Gibraltar",
    "GR": "Greece",
    "HR": "Croatia",
    "HU": "Hungary",
    "IE": "Ireland",
    "IM": "Isle of Man",
    "IS": "Iceland",
    "IT": "Italy",
    "JE": "Jersey",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MC": "Monaco",
    "MD": "Moldova",
    "ME": "Montenegro",
    "MK": "North Macedonia",
    "MT": "Malta",
    "NL": "Netherlands",
    "NO": "Norway",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "SE": "Sweden",
    "SI": "Slovenia",
    "SJ": "Norway",
    "SK": "Slovakia",
    "SM": "San Marino",
    "UA": "Ukraine",
    "VA": "Vatican City",
}

_REGION_ALIASES: dict[str, tuple[str, ...]] = {
    "SJ": ("Svalbard and Jan Mayen", "Norway"),
}

LICENCE = "CDLA-Permissive 2.0 (Microsoft Building Footprints)"
LICENCE_URL = (
    "https://github.com/microsoft/GlobalMLBuildingFootprints/blob/main/LICENSE"
)
OSM_LICENCE = "ODbL 1.0 (OpenStreetMap)"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
MAX_CACHED_PARTS = 10


def quadkey(latitude: float, longitude: float, zoom: int = ZOOM) -> str:
    """The Bing quadkey of the cell a position falls in."""
    sine = math.sin(latitude * math.pi / 180)
    x = (longitude + 180) / 360
    y = 0.5 - math.log((1 + sine) / (1 - sine)) / (4 * math.pi)
    digits: list[str] = []
    for level in range(zoom, 0, -1):
        digit = 0
        mask = 1 << (level - 1)
        if int(x * (1 << zoom)) & mask:
            digit += 1
        if int(y * (1 << zoom)) & mask:
            digit += 2
        digits.append(str(digit))
    return "".join(digits)


@cache
def _catalogue() -> dict[tuple[str, str], str]:
    """Every published part, keyed by region and quadkey."""
    with urllib.request.urlopen(
        urllib.request.Request(CATALOGUE, headers={"User-Agent": USER_AGENT}),
        timeout=120,
    ) as response:
        text = response.read().decode("utf-8", errors="replace")
    parts: dict[tuple[str, str], str] = {}
    for row in csv.DictReader(text.splitlines()):
        region = row.get("Location", "")
        key = row.get("QuadKey", "")
        url = row.get("Url", "")
        if region and key and url:
            parts[(region, key)] = url
    return parts


def part_url(region: str, key: str) -> str | None:
    """The published part for one region and quadkey, if the region is covered.

    `region` is the ISO code the service speaks; the catalogue uses the English
    name, so the code is mapped first. Microstates inside a neighbour's quadkey
    cell fall back to any published part matching the exact quadkey.
    """
    code = region.upper()
    if code not in REGION_NAMES:
        return None
    names = _REGION_ALIASES.get(code, (REGION_NAMES[code],))
    parts = _catalogue()
    for name in names:
        exact = parts.get((name, key))
        if exact is not None:
            return exact
    # A cell near a border is sometimes published under a neighbouring key; any
    # part of the same region that starts with the position's prefix is close
    # enough for a click, and the outline test below rejects a wrong building.
    for name in names:
        for (candidate_name, candidate), url in parts.items():
            if candidate_name == name and candidate.startswith(key[:7]):
                return url
    # Microstates (VA, SM, MC, AD, GI) often sit inside a neighbour's exact cell.
    for (_candidate_name, candidate), url in parts.items():
        if candidate == key:
            return url
    return None


def outlines(
    archive: bytes | Path, latitude: float, longitude: float
) -> list[list[tuple[float, float]]]:
    """Every outline of a part that sits near a position, in WGS84 degrees.

    Streams the gzipped GeoJSON lines so a 200 MB uncompressed cell never sits
    in RAM at once.
    """
    near: list[list[tuple[float, float]]] = []
    if isinstance(archive, Path):
        handle_ctx = gzip.open(archive, "rt", encoding="utf-8", errors="replace")
    else:
        handle_ctx = gzip.open(
            io.BytesIO(archive), "rt", encoding="utf-8", errors="replace"
        )
    with handle_ctx as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except ValueError:
                continue
            ring = _largest_ring(item)
            if ring is None:
                continue
            lons = [point[0] for point in ring]
            lats = [point[1] for point in ring]
            # 0.01 degrees is about 1 km, the scale of a click.
            if (
                min(lats) - 0.01 <= latitude <= max(lats) + 0.01
                and min(lons) - 0.01 <= longitude <= max(lons) + 0.01
            ):
                near.append(ring)
    return near


def _largest_ring(item: dict[str, Any]) -> list[tuple[float, float]] | None:
    geometry = item.get("geometry")
    if not isinstance(geometry, dict):
        return None
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        return None
    rings: list[list[Any]] = []
    if kind == "Polygon":
        rings = [coordinates[0]] if coordinates else []
    elif kind == "MultiPolygon":
        rings = [polygon[0] for polygon in coordinates if polygon]
    best: list[tuple[float, float]] | None = None
    best_area = 0.0
    for ring in rings:
        if not isinstance(ring, list) or len(ring) < 4:
            continue
        points = [
            (float(point[0]), float(point[1]))
            for point in ring
            if isinstance(point, (list, tuple)) and len(point) >= 2
        ]
        area = abs(_shoelace(points))
        if area > best_area:
            best_area = area
            best = points
    return best


def _shoelace(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for index in range(len(points)):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return total / 2


def simplify(
    ring: list[tuple[float, float]], tolerance_deg: float = 0.0000035
) -> list[tuple[float, float]]:
    """Drop points that repeat a corner, keeping the outline's shape.

    A raster-derived outline carries a point every 35 cm; a customer's roof has
    corners. The tolerance is about 35 cm at European latitudes.
    """
    if len(ring) < 4:
        return ring
    kept = [ring[0]]
    for point in ring[1:]:
        if (
            abs(point[0] - kept[-1][0]) > tolerance_deg
            or abs(point[1] - kept[-1][1]) > tolerance_deg
        ):
            kept.append(point)
    if len(kept) < 3:
        return ring
    return kept


def nearest(
    candidates: list[list[tuple[float, float]]],
    latitude: float,
    longitude: float,
    *,
    tolerance_m: float = CLICK_TOLERANCE_M,
) -> list[tuple[float, float]] | None:
    """The outline containing the position, or the closest one within tolerance."""
    inside: list[tuple[float, float]] | None = None
    best: tuple[float, list[tuple[float, float]]] | None = None
    for ring in candidates:
        distance = _distance_deg(ring, latitude, longitude)
        if distance == 0.0 and inside is None:
            inside = ring
            continue
        if best is None or distance < best[0]:
            best = (distance, ring)
    if inside is not None:
        return simplify(inside)
    if best is None:
        return None
    # 12 m at European latitudes is about 0.00011 degrees of latitude.
    if best[0] > tolerance_m / 111_320:
        return None
    return simplify(best[1])


def _distance_deg(
    ring: list[tuple[float, float]], latitude: float, longitude: float
) -> float:
    if _inside(ring, longitude, latitude):
        return 0.0
    best = math.inf
    for index in range(len(ring)):
        x1, y1 = ring[index]
        x2, y2 = ring[(index + 1) % len(ring)]
        dx, dy = x2 - x1, y2 - y1
        span = dx * dx + dy * dy
        if span <= 0:
            best = min(best, math.hypot(longitude - x1, latitude - y1))
            continue
        t = max(
            0.0,
            min(
                1.0,
                ((longitude - x1) * dx + (latitude - y1) * dy) / span,
            ),
        )
        best = min(
            best, math.hypot(longitude - (x1 + t * dx), latitude - (y1 + t * dy))
        )
    return best


def _inside(ring: list[tuple[float, float]], x: float, y: float) -> bool:
    crossings = 0
    count = len(ring)
    for index in range(count):
        x1, y1 = ring[index]
        x2, y2 = ring[(index + 1) % count]
        if (y1 > y) != (y2 > y):
            if x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                crossings += 1
    return crossings % 2 == 1


def area_m2(ring: list[tuple[float, float]]) -> float:
    """The outline's area on the ground, in square metres."""
    latitude = sum(point[1] for point in ring) / len(ring)
    metres_per_degree = 111_320.0
    span = math.cos(math.radians(latitude))
    scaled = [(x * metres_per_degree * span, y * metres_per_degree) for x, y in ring]
    return abs(_shoelace(scaled))


def download(url: str) -> bytes:
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=180
    ) as response:
        return cast(bytes, response.read())


def cache_dir(root: Path) -> Path:
    directory = root / "footprints"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _footprints_cache_dir() -> Path:
    root = Path(os.environ.get("LINKER_ENGINE_CACHE") or "/tmp/linker-engine-cache")
    return cache_dir(root)


def _prune_footprints_cache(directory: Path) -> None:
    files = sorted(
        directory.glob("*.geojsonl.gz"),
        key=lambda item: item.stat().st_mtime,
    )
    for stale in files[:-MAX_CACHED_PARTS]:
        stale.unlink(missing_ok=True)


def _archive_path(country: str, key: str, url: str) -> Path | None:
    """The published part stored on disk with bounded LRU eviction."""
    directory = _footprints_cache_dir()
    path = directory / f"{country.upper()}-{key}.geojsonl.gz"
    if path.exists():
        path.touch()
        return path
    tmp_path: Path | None = None
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": USER_AGENT}),
            timeout=180,
        ) as response:
            with tempfile.NamedTemporaryFile(
                dir=directory, suffix=".part", delete=False
            ) as handle:
                tmp_path = Path(handle.name)
                while chunk := response.read(65536):
                    handle.write(chunk)
        os.replace(tmp_path, path)
        _prune_footprints_cache(directory)
        return path
    except (OSError, ValueError):
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        return None


def _overpass_outline(
    latitude: float, longitude: float, *, tolerance_m: float = 25.0
) -> list[tuple[float, float]] | None:
    """Lightweight OpenStreetMap Overpass building fallback when footprints miss."""
    radius = max(25, int(math.ceil(tolerance_m)))
    query = (
        f'[out:json][timeout:10];way["building"]'
        f"(around:{radius},{latitude},{longitude});out geom;"
    )
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        OVERPASS_URL, data=body, headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = cast(dict[str, Any], json.load(response))
    except (OSError, ValueError, urllib.error.URLError, TimeoutError):
        return None
    elements = payload.get("elements")
    if not isinstance(elements, list):
        return None
    candidates: list[list[tuple[float, float]]] = []
    for element in elements:
        if not isinstance(element, dict) or element.get("type") != "way":
            continue
        geometry = element.get("geometry")
        if not isinstance(geometry, list):
            continue
        points: list[tuple[float, float]] = []
        for point in geometry:
            if (
                isinstance(point, dict)
                and isinstance(point.get("lon"), (int, float))
                and isinstance(point.get("lat"), (int, float))
            ):
                points.append((float(point["lon"]), float(point["lat"])))
        if len(points) >= 3:
            candidates.append(points)
    if not candidates:
        return None
    return nearest(candidates, latitude, longitude, tolerance_m=tolerance_m)


def _outline_with_source(
    country: str,
    latitude: float,
    longitude: float,
    *,
    tolerance_m: float = CENTROID_TOLERANCE_M,
) -> tuple[list[tuple[float, float]], str, str] | None:
    if country.upper() not in REGION_NAMES:
        return None
    key = quadkey(latitude, longitude)
    try:
        url = part_url(country, key)
    except (OSError, ValueError, IncompleteRead):
        url = None
    if url is not None:
        archive = _archive_path(country, key, url)
        if archive is not None:
            ring = nearest(
                outlines(archive, latitude, longitude),
                latitude,
                longitude,
                tolerance_m=tolerance_m,
            )
            if ring is not None:
                return ring, "Microsoft building footprints", LICENCE
    osm_ring = _overpass_outline(
        latitude, longitude, tolerance_m=max(25.0, tolerance_m)
    )
    if osm_ring is not None:
        return osm_ring, "OpenStreetMap contributors", OSM_LICENCE
    return None


def outline_at(
    country: str,
    latitude: float,
    longitude: float,
    *,
    tolerance_m: float = CENTROID_TOLERANCE_M,
) -> list[tuple[float, float]] | None:
    """The mapped building outline at a position, or None where none is known.

    This is the geometric answer alone: no module layout, no pitch, no area
    claim. A caller that shows it must say where it came from.
    """
    result = _outline_with_source(country, latitude, longitude, tolerance_m=tolerance_m)
    return result[0] if result is not None else None


def outline_payload(
    country: str,
    latitude: float,
    longitude: float,
    *,
    tolerance_m: float = CENTROID_TOLERANCE_M,
) -> dict[str, Any] | None:
    """The outline with the source and licence a screen has to display."""
    result = _outline_with_source(country, latitude, longitude, tolerance_m=tolerance_m)
    if result is None:
        return None
    ring, source, licence = result
    return {
        "outline": [
            [round(longitude_value, 7), round(latitude_value, 7)]
            for longitude_value, latitude_value in ring
        ],
        "source": source,
        "licence": licence,
        "planes": [],
    }
