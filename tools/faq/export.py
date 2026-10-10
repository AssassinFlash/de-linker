#!/usr/bin/env python3
"""Export each published product's existing FAQ questions (docs/specs/15-faq.md).

Reads the local instance through WP-CLI (`just wp <name> …` or --wp). Prints JSON
of {id, slug, sku, title, brand, model, series, questions:[{index, category,
question_en, question_de}]}. Scripts here only read and write fields.

  python3 tools/faq/export.py --wp 'just wp t6'
  python3 tools/faq/export.py --wp 'just wp t6' --out docs/faq/questions.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wpcli import wp_eval


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wp",
        required=True,
        help="WP-CLI invocation for the instance, e.g. 'just wp t6'",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Write JSON here instead of stdout",
    )
    args = parser.parse_args()
    payload = wp_eval(args.wp, {"action": "export"})
    products = payload.get("products")
    if not isinstance(products, list):
        sys.exit("export: site did not return a products list")
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"{len(products)} products -> {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
