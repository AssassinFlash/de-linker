"""Capture the Store API vocabulary of a local instance as the lexicon's test fixture.

    uv run python eval/understanding/capture.py http://127.0.0.1:9057 \
        tests/fixtures/storeapi.json

Keeps only the fields the lexicon reads (storeapi.py), so the fixture stays small and
holds no prices or descriptions. Run it against an instance loaded with the latest
live snapshot (`just pull load <instance> latest`).
"""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx

from linker_genie.storeapi import MAX_PAGES, PAGE_SIZE


def pages(client: httpx.Client, path: str, lang: str | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        params: dict[str, Any] = {"per_page": PAGE_SIZE, "page": page}
        if lang:
            params["lang"] = lang
        response = client.get("/wp-json/wc/store/v1" + path, params=params)
        response.raise_for_status()
        items.extend(response.json())
        if page >= int(response.headers.get("X-WP-TotalPages", "1")):
            break
    return items


def trim_product(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "sku": item["sku"],
        "attributes": [
            {
                "taxonomy": a["taxonomy"],
                "terms": [{"name": t["name"], "slug": t["slug"]} for t in a["terms"]],
            }
            for a in item.get("attributes") or []
            if a.get("taxonomy") in ("pa_brand", "pa_model", "pa_series", "pa_phase")
        ],
        "categories": [
            {"name": c["name"], "slug": c["slug"]} for c in item.get("categories") or []
        ],
    }


def trim_category(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "slug": item["slug"],
        "parent": item.get("parent", 0),
    }


def main() -> None:
    base, out = sys.argv[1], sys.argv[2]
    with httpx.Client(base_url=base.rstrip("/"), timeout=30) as client:
        fixture = {
            lang or "en": {
                "products": [trim_product(p) for p in pages(client, "/products", lang)],
                "categories": [
                    trim_category(c)
                    for c in pages(client, "/products/categories", lang)
                ],
            }
            for lang in (None, "de")
        }
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(fixture, handle, ensure_ascii=False, indent=1)
        handle.write("\n")


if __name__ == "__main__":
    main()
