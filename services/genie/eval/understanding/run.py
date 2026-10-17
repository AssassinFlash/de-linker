"""The bare-word evaluation of #233 against a running local instance.

    uv run python eval/understanding/run.py http://127.0.0.1:9057 out.json

Sends every case of bare_words.json as a first turn through the site's Genie route
(`/wp-json/linker-ai/v1/genie/turn`, the path the shell uses) and scores the answer:
it passes when it shows product cards, every card belongs to the expectation (the
brand, the series, the model's product, the titles' family word, the device class),
and no text greets the customer — a product word is never a name. Products are read
from tests/fixtures/storeapi.json, the snapshot the instance was loaded with.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from linker_genie.lexicon import normalize

HERE = Path(__file__).resolve().parent
FIXTURE = json.loads(
    (HERE.parents[1] / "tests" / "fixtures" / "storeapi.json").read_text()
)
CASES = json.loads((HERE / "bare_words.json").read_text())["cases"]
# A greeting or form of address in either language: what "Hello saj, welcome" was.
GREETING = re.compile(
    r"\b(hello|hi|hey|welcome|dear|hallo|willkommen|guten tag|liebe[rs]?)\b",
    re.IGNORECASE,
)
# Four turns at a time: each is one deepseek-flash run of 5-20 s on the local stack.
WORKERS = 4


def products() -> dict[int, dict[str, Any]]:
    table: dict[int, dict[str, Any]] = {}
    for item in FIXTURE["en"]["products"]:
        attributes = {
            a["taxonomy"]: [t["slug"] for t in a["terms"]] for a in item["attributes"]
        }
        table[item["id"]] = {
            "name": item["name"],
            "sku": item["sku"],
            "brand": attributes.get("pa_brand", []),
            "series": attributes.get("pa_series", []),
            "models": [
                t["name"]
                for a in item["attributes"]
                if a["taxonomy"] == "pa_model"
                for t in a["terms"]
            ],
            "categories": [c["slug"] for c in item["categories"]],
        }
    return table


PRODUCTS = products()
PARENTS = {c["slug"]: c["parent"] for c in FIXTURE["en"]["categories"]}
SLUG_OF = {c["id"]: c["slug"] for c in FIXTURE["en"]["categories"]}


def device_classes(product: dict[str, Any]) -> set[str]:
    classes = set()
    for slug in product["categories"]:
        while slug:
            classes.add(slug)
            slug = SLUG_OF.get(PARENTS.get(slug, 0), "")
    return classes


def belongs(product_id: int, expect: dict[str, str]) -> bool:
    product = PRODUCTS.get(product_id)
    if product is None:
        return False
    ((kind, value),) = expect.items()
    if kind == "brand":
        # 25 GoodWe products of the 2026-10-15 snapshot carry no pa_brand term;
        # their titles start with the brand (reported on #233), and
        # search-products keeps them as brand-unknown.
        return value in product["brand"] or normalize(product["name"]).startswith(
            normalize(value)
        )
    if kind == "series":
        return value in product["series"]
    if kind == "model":
        key = normalize(value)
        return key in normalize(product["name"]) or any(
            normalize(m) == key for m in product["models"]
        )
    if kind == "title":
        return normalize(value) in normalize(product["name"])
    return value in device_classes(product)


def parse(raw: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    stream = json.loads(raw)["stream"]
    meta: dict[str, Any] = {}
    blocks: list[dict[str, Any]] = []
    for event in stream.split("\n\n"):
        lines = dict(line.split(": ", 1) for line in event.splitlines() if ": " in line)
        if lines.get("event") == "meta":
            meta = json.loads(lines["data"])
        elif lines.get("event") == "block":
            blocks.append(json.loads(lines["data"]))
    return meta, blocks


def score(case: dict[str, Any], blocks: list[dict[str, Any]]) -> dict[str, Any]:
    cards = [pid for b in blocks if b["type"] == "cards" for pid in b["product_ids"]]
    texts = [b["text"] for b in blocks if b["type"] == "text"]
    greeted = [t for t in texts if GREETING.search(t)]
    outside = [pid for pid in cards if not belongs(pid, case["expect"])]
    return {
        "cards": len(cards),
        "outside": outside,
        "greeted": greeted,
        "ok": bool(cards) and not outside and not greeted,
    }


def turn(base: str, case: dict[str, Any]) -> dict[str, Any]:
    body = {
        "messages": [{"role": "user", "content": case["message"]}],
        "locale": case["lang"],
        "page": {"type": "other"},
    }
    started = time.perf_counter()
    try:
        response = httpx.post(
            base.rstrip("/") + "/wp-json/linker-ai/v1/genie/turn",
            json=body,
            timeout=180,
        )
        meta, blocks = parse(response.text)
    except (httpx.HTTPError, ValueError, KeyError) as error:
        return {**case, "error": str(error), "ok": False}
    return {
        **case,
        "seconds": round(time.perf_counter() - started, 1),
        "meta": meta,
        "blocks": blocks,
        **score(case, blocks),
    }


def main() -> None:
    base, out = sys.argv[1], sys.argv[2]
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        rows = list(pool.map(lambda case: turn(base, case), CASES))
    Path(out).write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    for lang in ("en", "de"):
        sub = [r for r in rows if r["lang"] == lang]
        print(f"{lang}: {sum(r['ok'] for r in sub)}/{len(sub)} show their products")
    print("greeted:", sum(bool(r.get("greeted")) for r in rows))
    print("routes:", sorted({r.get("meta", {}).get("route") for r in rows} - {None}))
    for row in rows:
        if not row["ok"]:
            print(
                "  FAIL",
                row["lang"],
                row["message"],
                {k: row.get(k) for k in ("error", "cards", "outside", "greeted")},
                row.get("meta", {}).get("failures"),
            )


if __name__ == "__main__":
    main()
