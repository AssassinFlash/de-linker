"""Shared fixtures: the engine on the test feed, never on the network.

The feed and compatibility fixtures are built by scripts/build_fixtures.py from
the live site's published products (read-only REST, 2026-10-09) and the old
repository's documented facts; the PVGIS profile is a real PVGIS answer for
Munich, the LoD2 cut a real Bavarian tile (see tests/fixtures/*/source.json).
"""

from __future__ import annotations

import gzip
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from linker_engine.app import Settings, create_app
from linker_engine.compatibility import Compatibility
from linker_engine.engine import Engine
from linker_engine.products import Products
from linker_engine.pvgis import Pvgis
from linker_engine.roof import lod2

FIXTURES = Path(__file__).parent / "fixtures"
MUNICH_LOD2 = FIXTURES / "lod2" / "munich-80538-triftstrasse.gml.gz"
TRIFTSTRASSE_5 = (
    48.140278,
    11.588411,
)  # centroid of the building, ETRS89 692552.7 / 5335132.2


def no_network(*_: Any) -> Any:
    raise AssertionError("tests never call PVGIS; the cache must answer")


@pytest.fixture(scope="session")
def products() -> Products:
    return Products.load(FIXTURES / "feed.json")


@pytest.fixture(scope="session")
def compatibility() -> Compatibility:
    return Compatibility.load(FIXTURES / "compatibility.json")


@pytest.fixture
def pvgis(tmp_path: Path) -> Pvgis:
    cache = tmp_path / "pvgis"
    shutil.copytree(FIXTURES / "pvgis", cache)
    return Pvgis(cache, fetch=no_network)


@pytest.fixture
def engine(products: Products, compatibility: Compatibility, pvgis: Pvgis) -> Engine:
    return Engine(products=products, compatibility=compatibility, pvgis=pvgis)


def munich_tile(tile: lod2.Tile, target: Path) -> None:
    assert tile.key == "DE-BY_32_692_5334", tile.key
    with gzip.open(MUNICH_LOD2, "rb") as source, target.open("wb") as sink:
        shutil.copyfileobj(source, sink)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    cache = tmp_path / "cache"
    shutil.copytree(FIXTURES / "pvgis", cache / "pvgis")
    monkeypatch.setattr("linker_engine.pvgis._pvgis_fetch", no_network)
    monkeypatch.setattr("linker_engine.roof.lod2.fetch", munich_tile)
    settings = Settings(
        feed=FIXTURES / "feed.json",
        compatibility=FIXTURES / "compatibility.json",
        cache=cache,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client
