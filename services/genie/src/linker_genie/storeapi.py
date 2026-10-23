"""The product vocabulary, read from WooCommerce's own Store API.

The Store API (`/wp-json/wc/store/v1/products`, `/products/categories`) is public,
read-only and native to WooCommerce, and lists every published product with its
brand, model and series attributes, SKU and categories; `lang=de` (Polylang) lists
the German posts. Nothing new is registered on the WordPress side for this (AGENTS.md
§5: Woo's own mechanisms before custom code).

The vocabulary is cached for `TTL_SECONDS`. A load that fails is raised as
`VocabularyError`: the caller logs it on the turn and goes on without product words —
never silently (AGENTS.md §5).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import httpx

from linker_genie.lexicon import Category, Product, Vocabulary, build
from linker_genie.publication import PublicationClient, PublicationUnavailable

# Store API's own page size ceiling (WooCommerce Store API, `per_page` maximum 100).
PAGE_SIZE = 100
# Staff edit products a few times a day (the 2026-10-17 snapshot holds 106); a new
# product should be matchable within minutes, and one reload is three to five
# requests on the loopback. Ten minutes is the starting value.
TTL_SECONDS = 600.0
# Pages read at most per listing: 106 products are two pages; twenty leaves room for
# 2 000 products before the reader stops instead of looping on a broken pager.
MAX_PAGES = 20


class VocabularyError(RuntimeError):
    """The Store API could not be read."""


class StoreVocabulary:
    """`get()` returns the cached vocabulary, reloading it when it is older than the TTL."""

    def __init__(
        self,
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        ttl: float = TTL_SECONDS,
        publication: PublicationClient | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Accept": "application/json"},
            # The same per-call ceiling as the abilities client (abilities.py).
            timeout=20.0,
            transport=transport,
        )
        self._clock = clock
        self._ttl = ttl
        self._lock = threading.Lock()
        self._cached: Vocabulary | None = None
        self._loaded_at = 0.0
        self._publication = publication
        self._source_revision = ""

    def close(self) -> None:
        self._client.close()

    def get(self) -> Vocabulary:
        with self._lock:
            now = self._clock()
            try:
                source = (
                    self._publication.snapshot()
                    if self._publication is not None
                    else None
                )
            except PublicationUnavailable as error:
                raise VocabularyError(str(error)) from error
            changed = (
                source is not None and self._source_revision != source.source_revision
            )
            if self._cached is None or changed or now - self._loaded_at >= self._ttl:
                self._cached = self._load()
                self._loaded_at = now
                if source is not None:
                    self._source_revision = source.source_revision
            return self._cached

    def _load(self) -> Vocabulary:
        permit = self._publication.snapshot() if self._publication is not None else None
        english = [
            _product(item)
            for item in self._pages("/products", {})
            if permit is None or permit.canonical(int(item.get("id", 0))) is not None
        ]
        categories = [
            _category(item) for item in self._pages("/products/categories", {})
        ]
        german = [
            _product(item)
            for item in self._pages("/products", {"lang": "de"})
            if permit is None or permit.canonical(int(item.get("id", 0))) is not None
        ]
        german_categories = [
            _category(item)
            for item in self._pages("/products/categories", {"lang": "de"})
        ]
        return build(
            english,
            categories,
            [(product, german_categories) for product in german],
        )

    def _pages(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for page in range(1, MAX_PAGES + 1):
            try:
                response = self._client.get(
                    "/wp-json/wc/store/v1" + path,
                    params={**params, "per_page": PAGE_SIZE, "page": page},
                )
            except httpx.TransportError as error:
                raise VocabularyError(f"store api {path}: {error}") from error
            if response.status_code >= 400:
                raise VocabularyError(
                    f"store api {path} returned {response.status_code}"
                )
            body = response.json()
            if not isinstance(body, list):
                raise VocabularyError(f"store api {path} did not return a list")
            items.extend(item for item in body if isinstance(item, dict))
            total_pages = int(response.headers.get("X-WP-TotalPages", "1") or 1)
            if page >= total_pages or not body:
                break
        return items


def _terms(item: dict[str, Any], taxonomy: str) -> list[dict[str, Any]]:
    for attribute in item.get("attributes") or []:
        if isinstance(attribute, dict) and attribute.get("taxonomy") == taxonomy:
            return [t for t in attribute.get("terms") or [] if isinstance(t, dict)]
    return []


def _product(item: dict[str, Any]) -> Product:
    return Product(
        id=int(item.get("id") or 0),
        name=str(item.get("name") or ""),
        sku=str(item.get("sku") or ""),
        brands=tuple(
            (str(t.get("name", "")), str(t.get("slug", "")))
            for t in _terms(item, "pa_brand")
        ),
        series=tuple(str(t.get("slug", "")) for t in _terms(item, "pa_series")),
        models=tuple(str(t.get("name", "")) for t in _terms(item, "pa_model")),
        phases=tuple(str(t.get("slug", "")) for t in _terms(item, "pa_phase")),
        categories=tuple(
            (str(c.get("name", "")), str(c.get("slug", "")))
            for c in item.get("categories") or []
            if isinstance(c, dict)
        ),
    )


def _category(item: dict[str, Any]) -> Category:
    return Category(
        id=int(item.get("id") or 0),
        name=str(item.get("name") or ""),
        slug=str(item.get("slug") or ""),
        parent=int(item.get("parent") or 0),
    )
