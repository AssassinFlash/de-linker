#!/usr/bin/env python3
"""Resolve the six reviewed FAQ sets against one target's Woo catalog receipt."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "faq"))
from generate import markdown


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prefix = "GOODWE_CATALOG="
    receipts = [line[len(prefix):] for line in args.catalog.read_text().splitlines()
                if line.startswith(prefix)]
    if len(receipts) != 1:
        parser.error("expected one GOODWE_CATALOG= record")
    catalog = json.loads(receipts[0])
    files = []
    for model in ("lx-c101-10", "lx-c138-10", "lx-c156-10", "gw50k-et-10", "gw100k-ht", "gw120k-ht"):
        slug = f"goodwe-{model}"
        product = json.loads((ROOT / "docs" / "faq" / f"{slug}.json").read_text())
        mapped = catalog["products"][product["sku"]]
        if mapped["slug"] != slug or not mapped["en"] or not mapped["de"]:
            parser.error(f"missing Woo product pair for {slug}")
        product["id"] = mapped["en"]
        for item in product["items"]:
            citation = item["citation"]
            citation["url"] = catalog["media"][citation["doc"]]["url"]
        files.append(product)
    args.output.mkdir(parents=True, exist_ok=True)
    slugs = {product["slug"] for product in files}
    if any(path.stem not in slugs for path in args.output.glob("*.json")):
        parser.error("the output directory contains other products")
    for product in files:
        base = args.output / product["slug"]
        base.with_suffix(".json").write_text(json.dumps(product, ensure_ascii=False, indent=2) + "\n")
        base.with_suffix(".md").write_text(markdown(product, product["items"]))


if __name__ == "__main__":
    main()
