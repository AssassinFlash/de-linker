"""Official LoD2 building tiles of the federal states, fetched on demand and indexed once.

`data/lod2-sources.json` holds each state's download pattern, grid and licence
as verified by real downloads on 2026-07-18 (old repository research,
2026-08-29). A tile is downloaded the first time a building in it is asked
for, reduced to a compact index of footprints and roof planes and cached;
later requests read only the index. Kinds:

- grid-gml, grid-query: one CityGML file per tile;
- grid-zip: one zip per tile;
- bulk-zip, bulk-zip-districts: tiles are members of a large zip; the member
  is read with HTTP range requests, never the whole archive;
- two-step (Sachsen-Anhalt) and gemeinde-zip (Hessen) are portal workflows
  with ephemeral links; they are not fetched automatically, and the roof step
  falls back to drawing the roof by hand there.
"""

from __future__ import annotations

import gzip
import io
import json
import math
import os
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import IO, Any

import requests
from pyproj import Transformer

from .citygml import read_buildings

DATA = Path(__file__).resolve().parents[3] / "data" / "lod2-sources.json"
TIMEOUT_S = 120  # a 120 MB Bavarian tile arrives in well under a minute on 2026-10-09
USER_AGENT = "linker-engine (de-linker.com Solution Configurator)"


class Lod2Unavailable(RuntimeError):
    """No LoD2 tile could be read for the position."""


@dataclass(frozen=True)
class Tile:
    state: str
    kind: str
    zone: int
    e_km: int
    n_km: int
    url: str
    member: str | None
    licence: str

    @property
    def key(self) -> str:
        return f"{self.state}_{self.zone}_{self.e_km}_{self.n_km}"


@cache
def sources() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())["states"]
    return data


@cache
def _to_utm(zone: int) -> Transformer:
    return Transformer.from_crs("EPSG:4326", f"EPSG:258{zone}", always_xy=True)


@cache
def _to_wgs84(zone: int) -> Transformer:
    return Transformer.from_crs(f"EPSG:258{zone}", "EPSG:4326", always_xy=True)


def to_utm(zone: int, latitude: float, longitude: float) -> tuple[float, float]:
    x, y = _to_utm(zone).transform(longitude, latitude)
    return float(x), float(y)


def to_wgs84(zone: int, x: float, y: float) -> tuple[float, float]:
    longitude, latitude = _to_wgs84(zone).transform(x, y)
    return float(longitude), float(latitude)


class _Keep(dict[str, int]):
    """Format fields; placeholders a pattern fills elsewhere ({district}, {date}) stay as they are."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def tile_for(state: str, latitude: float, longitude: float) -> Tile:
    source = sources().get(state)
    if source is None:
        raise Lod2Unavailable(f"no LoD2 source for {state}")
    zone = int(source["zone"])
    x, y = to_utm(zone, latitude, longitude)
    e, n = math.floor(x / 1000), math.floor(y / 1000)
    anchor = source["anchor"]
    if anchor == "even":
        e, n = e - e % 2, n - n % 2
    elif anchor == "odd-e-even-n":
        e, n = (e if e % 2 else e - 1), n - n % 2
    fields = {"e": e, "n": n, "e10": e - e % 10, "n10": n - n % 10}
    member = source.get("member")
    return Tile(
        state=state,
        kind=source["kind"],
        zone=zone,
        e_km=e,
        n_km=n,
        url=source["url"].format_map(_Keep(fields)),
        member=member.format_map(_Keep(fields)) if member else None,
        licence=source["license"],
    )


# Fetching ------------------------------------------------------------------------------

Fetch = Callable[[Tile, Path], None]


def _download(url: str, target: Path) -> None:
    with requests.get(
        url, stream=True, timeout=TIMEOUT_S, headers={"User-Agent": USER_AGENT}
    ) as response:
        if response.status_code == 404:
            raise Lod2Unavailable(f"no tile at {url}")
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                handle.write(chunk)


class RangeFile(io.RawIOBase):
    """A remote file read with HTTP range requests, so zipfile reads only what it needs."""

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url
        head = requests.head(
            url,
            timeout=TIMEOUT_S,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        head.raise_for_status()
        if head.headers.get("Accept-Ranges") != "bytes":
            raise Lod2Unavailable(f"{url} does not serve byte ranges")
        self._size = int(head.headers["Content-Length"])
        self._position = 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._position, io.SEEK_END: self._size}[
            whence
        ]
        self._position = max(0, base + offset)
        return self._position

    def tell(self) -> int:
        return self._position

    def readinto(self, buffer: Any) -> int:
        if self._position >= self._size:
            return 0
        end = min(self._size, self._position + len(buffer)) - 1
        response = requests.get(
            self._url,
            headers={
                "Range": f"bytes={self._position}-{end}",
                "User-Agent": USER_AGENT,
            },
            timeout=TIMEOUT_S,
        )
        response.raise_for_status()
        data = response.content
        buffer[: len(data)] = data
        self._position += len(data)
        return len(data)


def _extract(archive: zipfile.ZipFile, wanted: str | None, target: Path) -> bool:
    for info in archive.infolist():
        name = os.path.basename(info.filename)
        if wanted is not None and name != wanted:
            continue
        if not name.lower().endswith((".gml", ".xml")):
            continue
        with archive.open(info) as source, target.open("wb") as sink:
            while chunk := source.read(1 << 20):
                sink.write(chunk)
        return True
    return False


def fetch(tile: Tile, target: Path) -> None:
    """Write the tile's CityGML to `target`, by the state's delivery kind."""
    if tile.kind in ("grid-gml", "grid-query"):
        _download(tile.url, target)
        return
    if tile.kind == "grid-zip":
        with tempfile.NamedTemporaryFile(suffix=".zip") as handle:
            _download(tile.url, Path(handle.name))
            with zipfile.ZipFile(handle.name) as archive:
                if not _extract(archive, None, target):
                    raise Lod2Unavailable(f"no CityGML in {tile.url}")
        return
    if tile.kind in ("bulk-zip", "bulk-zip-districts"):
        districts = sources()[tile.state].get("districts") or [""]
        for district in districts:
            url = tile.url.replace("{district}", district)
            with (
                RangeFile(url) as remote,
                zipfile.ZipFile(io.BufferedReader(remote, 1 << 20)) as archive,
            ):
                if _extract(archive, tile.member, target):
                    return
        raise Lod2Unavailable(f"tile {tile.member} not in the {tile.state} archive")
    raise Lod2Unavailable(
        f"LoD2 for {tile.state} is published through a portal workflow"
    )


# Index ----------------------------------------------------------------------------------


def build_index(source: IO[bytes] | str) -> dict[str, Any]:
    """Footprints and roof planes of every building in a CityGML document."""
    buildings = []
    for building in read_buildings(source):
        if not building.planes:
            continue
        buildings.append(
            {
                "id": building.id,
                "address": building.address,
                "footprint": [
                    [[round(x, 2), round(y, 2)] for x, y in ring]
                    for ring in building.footprint
                ],
                "planes": [
                    {
                        "ring": [[round(x, 2), round(y, 2)] for x, y in plane.ring],
                        "tilt": plane.tilt_deg,
                        "azimuth": plane.azimuth_deg,
                        "area": plane.area_m2,
                    }
                    for plane in building.planes
                ],
            }
        )
    return {"buildings": buildings}


class TileIndex:
    """Compact per-tile indexes in a cache directory; the tile is fetched once."""

    def __init__(self, cache_dir: Path, fetcher: Fetch | None = None) -> None:
        self._cache_dir = cache_dir
        self._fetch = fetcher

    def load(self, tile: Tile) -> dict[str, Any]:
        path = self._cache_dir / f"{tile.key}.index.json.gz"
        if path.exists():
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                index: dict[str, Any] = json.load(handle)
                return index
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".gml", dir=self._cache_dir) as raw:
            try:
                (self._fetch or fetch)(tile, Path(raw.name))
            except requests.RequestException as error:
                raise Lod2Unavailable(str(error)) from error
            index = build_index(raw.name)
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(index, handle)
        return index
