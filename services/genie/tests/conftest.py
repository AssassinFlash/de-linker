"""Shared fixtures: the real Store API vocabulary of the live snapshot (2026-10-15).

tests/fixtures/storeapi.json is the trimmed Store API of a local instance loaded with
the live snapshot (eval/understanding/capture.py).
"""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

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
