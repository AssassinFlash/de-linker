"""Stands in for WP-CLI in the tests of 7-facts.py.

`python fake_wp.py <site.json> eval-file -` takes 7-facts.php on stdin, finds
the request that 7-facts.py put in place of its payload placeholder, and
answers as the real file does, reading from and writing to site.json:

    {"siteurl": "...",
     "products": {"<id>": {"attributes": {"<taxonomy>": {"terms": [...], "attached": [...] | null}},
                           "figures": "<JSON object>",
                           "protected": {"<field>": ...}}},
     "faults": ["ignore-writes" | "touch-stock"],
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
    """Applies a write request the way 7-facts.php does."""
    site["writes"].append(request)
    faults = site.get("faults", [])
    if "ignore-writes" not in faults:
        for change in request["attributes"]:
            product = site["products"][str(change["product"])]
            terms = sorted(change["to"])
            product["attributes"][change["taxonomy"]] = {
                "terms": terms,
                "attached": terms or None,
            }
        for change in request["figures"]:
            product = site["products"][str(change["product"])]
            figures = json.loads(product["figures"])
            figures[change["key"]] = change["to"]
            product["figures"] = json.dumps(figures, ensure_ascii=False)
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
        answer: dict[str, Any] = {
            "siteurl": site["siteurl"],
            "products": {
                str(i): site["products"].get(str(i)) for i in request["products"]
            },
        }
    else:
        write(site, request)
        site_path.write_text(json.dumps(site, ensure_ascii=False))
        answer = {"written": True}
    print("\n" + request["marker"] + json.dumps(answer, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
