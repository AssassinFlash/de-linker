"""Stands in for WP-CLI in the tests of the migrations.

`python fake_wp.py <site.json> eval-file -` takes the PHP side on stdin, finds
the request the Python side put in place of its payload placeholder, and
answers as the real file does, reading from and writing to site.json:

    {"siteurl": "...",
     "products": {"<id>": {"attributes": {"<taxonomy>": {"terms": [...], "attached": [...] | null}},
                           "figures": "<JSON object>",
                           "documents": "<JSON list>",
                           "protected": {"<field>": ...}}},
     "term_counts": {"<taxonomy>:<slug>": <count>},
     "faults": ["ignore-writes" | "touch-stock" | "fail-write"],
     "writes": [<every write request>]}
"""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path
from typing import Any

PAYLOAD = re.compile(r"\)\( '([A-Za-z0-9+/=]+)' \);\s*$")


def write(site: dict[str, Any], request: dict[str, Any]) -> None:
    """Applies a write request the way the migrations' PHP sides do."""
    site["writes"].append(request)
    faults = site.get("faults", [])
    if "ignore-writes" not in faults:
        for change in request.get("attributes", []):
            product = site["products"][str(change["product"])]
            terms = sorted(change["to"])
            product["attributes"][change["taxonomy"]] = {
                "terms": terms,
                "attached": terms or None,
            }
        for change in request.get("figures", []):
            product = site["products"][str(change["product"])]
            figures = json.loads(product["figures"])
            figures[change["key"]] = change["to"]
            product["figures"] = json.dumps(figures, ensure_ascii=False)
        for change in request.get("citations", []):
            product = site["products"][str(change["product"])]
            figures = json.loads(product["figures"])
            figures[change["key"]]["citation"] = change["citation"]
            product["figures"] = json.dumps(figures, ensure_ascii=False)
        for change in request.get("documents", []):
            product = site["products"][str(change["product"])]
            product["documents"] = json.dumps(change["to"], ensure_ascii=False)
        for entry in request.get("remove_terms", []):
            for slug in entry["slugs"]:
                site["term_counts"].pop(f"{entry['taxonomy']}:{slug}", None)
    if "touch-stock" in faults:
        for product in site["products"].values():
            product["protected"]["stock_status"] = "outofstock"


def main() -> int:
    site_path = Path(sys.argv[1])
    if sys.argv[2:] != ["eval-file", "-"]:
        print(f"unexpected arguments {sys.argv[2:]}", file=sys.stderr)
        return 1
    match = PAYLOAD.search(sys.stdin.read())
    if match is None:
        print("no request in the PHP", file=sys.stderr)
        return 1
    request = json.loads(base64.b64decode(match.group(1)))
    site = json.loads(site_path.read_text())
    if request["action"] == "read":
        counts = site.get("term_counts", {})
        answer: dict[str, Any] = {
            "siteurl": site["siteurl"],
            "products": {
                str(i): site["products"].get(str(i)) for i in request["products"]
            },
            "term_counts": {
                f"{entry['taxonomy']}:{slug}": counts[f"{entry['taxonomy']}:{slug}"]
                for entry in request.get("remove_terms", [])
                for slug in entry["slugs"]
                if f"{entry['taxonomy']}:{slug}" in counts
            },
            "series_attr": site.get("series_attr", 2),
        }
    elif "fail-write" in site.get("faults", []):
        # What WP-CLI does when the PHP side throws: an error, no answer.
        print("PHP Fatal error:  Uncaught RuntimeException: refused", file=sys.stderr)
        return 255
    else:
        write(site, request)
        site_path.write_text(json.dumps(site, ensure_ascii=False))
        answer = {"written": True}
    print("\n" + request["marker"] + json.dumps(answer, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
