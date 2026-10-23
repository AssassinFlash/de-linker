"""Shared fixtures: the real Store API vocabulary of the live snapshot (2026-10-15).

tests/fixtures/storeapi.json is the trimmed Store API of a local instance loaded with
the live snapshot (eval/understanding/capture.py).
"""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from linker_genie.gate import HEADER, TOKEN_VARIABLE
from linker_genie.lexicon import Vocabulary
from linker_genie.storeapi import StoreVocabulary

STORE_FIXTURE: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "storeapi.json").read_text()
)


def store_transport(
    fixture: dict[str, Any], calls: list[str] | None = None
) -> httpx.MockTransport:
    """The Store API listings of `fixture`, paged as WooCommerce pages them."""

    def handle(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(request.url))
        lang = request.url.params.get("lang") or "en"
        kind = "categories" if request.url.path.endswith("/categories") else "products"
        items = fixture[lang][kind]
        size = int(request.url.params["per_page"])
        page = int(request.url.params["page"])
        pages = max(1, -(-len(items) // size))
        return httpx.Response(
            200,
            json=items[(page - 1) * size : page * size],
            headers={"X-WP-TotalPages": str(pages)},
        )

    return httpx.MockTransport(handle)


@pytest.fixture(scope="session")
def vocabulary() -> Vocabulary:
    return StoreVocabulary(
        "http://site.test", transport=store_transport(STORE_FIXTURE)
    ).get()


# The shell's shared token (gate.py): every test process has one, and a test client
# sends it the way the proxy does.
SHELL_TOKEN = "shell-test-token"
SHELL = {HEADER: SHELL_TOKEN}


@pytest.fixture(autouse=True)
def _service_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TOKEN_VARIABLE, SHELL_TOKEN)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """One copy of each #339 pass condition.

    ``test_campaign_339`` reexports the home test, marks included, and pytest
    expands it. When that module is in the same collection, drop the home
    item whose campaign copy is still selected. This runs after ``-k``, so a
    keyword that matches ``test_prices.py`` and not the campaign node id
    keeps the home price item. A run of the home file alone still collects it.
    """
    if not any(
        getattr(getattr(item, "module", None), "__name__", "") == "test_campaign_339"
        for item in items
    ):
        return
    import test_campaign_339

    owned = set(test_campaign_339.REEXPORTED_NAMES)
    present = {
        str(getattr(item, "originalname", ""))
        for item in items
        if getattr(getattr(item, "module", None), "__name__", "") == "test_campaign_339"
    }
    kept: list[pytest.Item] = []
    dropped: list[pytest.Item] = []
    for item in items:
        name = str(getattr(item, "originalname", ""))
        home = (
            getattr(getattr(item, "module", None), "__name__", "")
            != "test_campaign_339"
        )
        if home and name in owned and name in present:
            dropped.append(item)
        else:
            kept.append(item)
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = kept


@pytest.fixture(autouse=True)
def _published_turn_fixture(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The existing injected-generator HTTP tests also supply their Woo permission.

    These modules already replace understanding, abilities and the model. Their
    fixed Store API fixture is the publication set; dedicated publication tests use
    real HTTP transports/SQLite and mutate permission during the actual request.
    """
    if request.module.__name__ not in {
        "test_turn",
        "test_inquiry",
        "test_nameplate",
        "test_quality",
    }:
        return
    import linker_genie.app as service
    from linker_genie.app import app
    from linker_genie.publication import PublicationClient

    ids = {
        int(p["id"])
        for locale in ("en", "de")
        for p in STORE_FIXTURE[locale]["products"]
    }
    raw = {
        "schema_version": 1,
        "source_revision": "fixture",
        "compatibility_revision": "fixture",
        "products": [
            {
                "product_id": pid,
                "product_revision": str(pid),
                "published_locale_ids": [pid],
            }
            for pid in ids
        ],
        "documents": [],
    }

    def handle(call: httpx.Request) -> httpx.Response:
        if call.url.path.endswith("/manifest"):
            return httpx.Response(200, json=raw)
        if call.url.path.endswith("/identify"):
            return httpx.Response(200, json={"models": []})
        return httpx.Response(200, json={"valid": True})

    client = PublicationClient("https://site.test", httpx.MockTransport(handle))
    monkeypatch.setattr(app.state, "publication", client, raising=False)
    monkeypatch.setattr(service, "current", lambda: client)
    monkeypatch.setattr(service, "_client", None)
