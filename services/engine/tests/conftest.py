"""Shared fixtures: the engine on the test feed, never on the network.

The feed and compatibility fixtures are built by scripts/build_fixtures.py from
the live site's published products (read-only REST, 2026-10-09) and the old
repository's documented facts; the PVGIS profile is a real PVGIS answer for
Munich, the LoD2 cut a real Bavarian tile (see tests/fixtures/*/source.json).
"""

from __future__ import annotations

import gzip
import json
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
# The contract the site ships, so the tests that pin a release decision or a
# meter fact read the file production reads (#481, #482, #489).
SHIPPED_COMPATIBILITY = (
    Path(__file__).resolve().parents[3]
    / "plugins"
    / "linker-commerce"
    / "data"
    / "compatibility.json"
)
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


@pytest.fixture(scope="session")
def shipped_compatibility() -> Compatibility:
    return Compatibility.load(SHIPPED_COMPATIBILITY)


@pytest.fixture(scope="session")
def shipping_compatibility(shipped_compatibility: Compatibility) -> Compatibility:
    """The #482/#483 locks read the same shipped contract under this name."""
    return shipped_compatibility


@pytest.fixture(scope="session")
def products_without_backup() -> Products:
    """The test feed as the live feed reaches the engine: no backup figures.

    Production product meta carries `backup_power_kw` with a doc-name citation,
    and the feed carries only figures whose citation names a hosted URL, so the
    engine sees no backup output for the residential inverters. Missing
    capability data must not turn the backup input into a dead input (#483).
    """
    feed = json.loads((FIXTURES / "feed.json").read_text())
    for item in feed["products"]:
        item["figures"] = {
            key: value for key, value in item["figures"].items() if "backup" not in key
        }
    return Products.from_feed(feed)


@pytest.fixture
def pvgis(tmp_path: Path) -> Pvgis:
    cache = tmp_path / "pvgis"
    shutil.copytree(FIXTURES / "pvgis", cache)
    return Pvgis(cache, fetch=no_network)


@pytest.fixture
def engine(products: Products, compatibility: Compatibility, pvgis: Pvgis) -> Engine:
    return Engine(products=products, compatibility=compatibility, pvgis=pvgis)


@pytest.fixture
def shipped_engine(
    products: Products, shipped_compatibility: Compatibility, pvgis: Pvgis
) -> Engine:
    """The engine on the fixture feed and the shipped contract (#481, #489)."""
    return Engine(products=products, compatibility=shipped_compatibility, pvgis=pvgis)


@pytest.fixture
def engine_without_backup(
    products_without_backup: Products, compatibility: Compatibility, pvgis: Pvgis
) -> Engine:
    return Engine(
        products=products_without_backup,
        compatibility=compatibility,
        pvgis=pvgis,
    )


@pytest.fixture
def shipping_engine(
    products_without_backup: Products,
    shipping_compatibility: Compatibility,
    pvgis: Pvgis,
) -> Engine:
    """The live shape: the shipped contract and a feed with no backup figures."""
    return Engine(
        products=products_without_backup,
        compatibility=shipping_compatibility,
        pvgis=pvgis,
    )


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
    prepared = publication_feed(
        json.loads((FIXTURES / "feed.json").read_text()),
        json.loads((FIXTURES / "compatibility.json").read_text()),
    )
    feed_path = tmp_path / "published-feed.json"
    feed_path.write_text(json.dumps(prepared))
    settings = Settings(
        feed=feed_path,
        compatibility=FIXTURES / "compatibility.json",
        cache=cache,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def publication_feed(raw: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    """Real engineering facts with explicit synthetic Woo publication identities."""
    import re

    from linker_engine.publication import digest

    raw = json.loads(json.dumps(raw))
    raw["compatibility"] = contract
    raw["compatibility_revision"] = digest([contract, raw["overlay"]])
    for product in raw["products"]:
        urls = {document["url"] for document in product["documents"]}
        refs = [figure["citation"]["url"] for figure in product["figures"].values()]
        for row in contract["pairs"] + contract["requirements"]:
            if any(
                re.search(row[key], product["model"])
                for key in ("inverter", "battery")
                if key in row
            ):
                refs.extend(document["url"] for document in row["documents"])
        for url in refs:
            if url not in urls:
                product["documents"].append(
                    {
                        "url": url,
                        "title": "Fixture evidence",
                        "type": "manual",
                        "lang": "en",
                    }
                )
                urls.add(url)
        for document in product["documents"]:
            document.update(
                document_id=digest(document["url"]),
                document_revision=digest(document["url"]),
                blob_sha256=digest(document["url"]),
                product_ids=[product["id"]],
            )
        product["canonical_product_id"] = product["id"]
        product["product_revision"] = digest(product)
    raw["source_revision"] = digest(raw)
    return raw


def publication_manifest(feed: dict[str, Any]) -> dict[str, Any]:
    docs: dict[str, Any] = {}
    products = []
    for product in feed["products"]:
        products.append(
            {
                "product_id": product["canonical_product_id"],
                "product_revision": product["product_revision"],
                "documents": [d["document_id"] for d in product["documents"]],
                "ready": {"engineering": False},
            }
        )
        for doc in product["documents"]:
            current = docs.setdefault(doc["document_id"], {**doc, "product_ids": []})
            current["product_ids"].append(product["canonical_product_id"])
    return {
        "schema_version": 1,
        "source_revision": feed["source_revision"],
        "compatibility_revision": feed["compatibility_revision"],
        "products": products,
        "documents": list(docs.values()),
    }


@pytest.fixture(autouse=True)
def no_publication_network(monkeypatch: pytest.MonkeyPatch) -> None:
    from linker_engine.publication import Publication

    monkeypatch.setattr(
        Publication, "read", lambda self: publication_manifest(self.feed)
    )
