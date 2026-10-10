#!/usr/bin/env python3
"""Write passed FAQ answers onto `_linker_faqs` (docs/specs/15-faq.md).

Reads docs/faq/<slug>.json produced by the per-product sessions. Only items
with status "pass" are written. The German pair is in the same JSON; when
Polylang has a twin, wordpress.php copies the meta there.

  python3 tools/faq/import.py --wp 'just wp t6' --from docs/faq
  python3 tools/faq/import.py --wp 'just wp t6' --from docs/faq --write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wpcli import wp_eval


def load_passed(directory: Path) -> list[dict[str, Any]]:
    """Passed items per product JSON in directory, skip missing or empty."""
    products: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        if path.name in {"questions.json", "summary.json"}:
            continue
        data = json.loads(path.read_text())
        product_id = data.get("id")
        items = [item for item in data.get("items", []) if item.get("status") == "pass"]
        if not isinstance(product_id, int):
            sys.exit(f"{path}: missing integer id")
        products.append(
            {
                "id": product_id,
                "slug": data.get("slug", path.stem),
                "items": items,
            }
        )
    return products


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True, help="WP-CLI invocation")
    parser.add_argument(
        "--from",
        dest="source",
        type=Path,
        default=Path("docs/faq"),
        help="Directory of per-product JSON (default docs/faq)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the field; without it, only report counts",
    )
    args = parser.parse_args()
    products = load_passed(args.source)
    n_items = sum(len(p["items"]) for p in products)
    print(f"{len(products)} products, {n_items} passed items", file=sys.stderr)
    if not args.write:
        return 0
    payload = wp_eval(args.wp, {"action": "import", "products": products})
    written = payload.get("written")
    if not isinstance(written, list):
        sys.exit("import: site did not return written[]")
    failed = [row for row in written if not row.get("done")]
    if failed:
        sys.exit(f"import: readback failed for {failed}")
    for row in written:
        print(f"wrote {row['id']} {row['slug']} n={row['count']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
