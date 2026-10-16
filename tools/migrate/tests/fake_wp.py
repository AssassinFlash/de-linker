"""Stands in for WP-CLI in the tests of the migrations.

`python fake_wp.py <site.json> eval-file -` takes the PHP side on stdin, finds
the request the Python side put in place of its payload placeholder, and
answers as the real file does, reading from and writing to site.json:

    {"siteurl": "...",
    "products": {"<id>": {"attributes": {"<taxonomy>": {"terms": [...], "attached": [...] | null}},
                          "figures": "<JSON object>",
                          "documents": "<JSON list>",
                          "legacy": {"en": "<JSON object>", "de": "<JSON object>"},
                          "protected": {"<field>": ...}}},
     "term_counts": {"<taxonomy>:<slug>": <count>},
     "faults": ["ignore-writes" | "touch-stock" | "fail-write" | "remove-legacy-group"],
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


class LegacyGroupRefusal(Exception):
    """A drop that would remove a spec group it does not name (7-facts.php throws too)."""

    def __init__(self, product_id: str, title: str) -> None:
        super().__init__(
            f'Dropping these rows would remove the spec group "{title}" '
            f"of product {product_id}. Name the group in drop_legacy.remove_groups "
            "to remove it with the row."
        )


def write(site: dict[str, Any], request: dict[str, Any]) -> None:
    """Applies a write request the way the migrations' PHP sides do."""
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
            if change["to"] is None:
                figures.pop(change["key"], None)
                drop = change.get("drop_legacy")
                if isinstance(drop, dict):
                    titles = {str(item) for item in drop.get("titles") or []}
                    labels = {str(item) for item in drop.get("labels") or []}
                    remove = {str(item) for item in drop.get("remove_groups") or []}
                    legacy = product.setdefault("legacy", {})
                    for side in ("en", "de"):
                        raw = legacy.get(side)
                        if not raw:
                            continue
                        decoded = json.loads(raw)
                        groups = []
                        for group in decoded.get("spec_groups") or []:
                            title = str(group.get("spec_group_title") or "")
                            if title not in titles:
                                groups.append(group)
                                continue
                            original = list(group.get("spec_rows") or [])
                            rows = [
                                row
                                for row in original
                                if str(row.get("spec_label") or "") not in labels
                            ]
                            if not rows:
                                if original and title not in remove:
                                    # 7-facts.php refuses this before it
                                    # writes: a drop may remove a group
                                    # with rows only where it names it.
                                    raise LegacyGroupRefusal(
                                        str(change["product"]), title
                                    )
                                if original or title in remove:
                                    # The group leaves: the drop emptied it,
                                    # or the drop names it for removal.
                                    continue
                                # A group that was already empty and is not
                                # named stays as it is.
                            group = {**group, "spec_rows": rows}
                            groups.append(group)
                        decoded["spec_groups"] = groups
                        legacy[side] = json.dumps(decoded, ensure_ascii=False)
            else:
                figures[change["key"]] = change["to"]
            # wp_json_encode of an emptied PHP array is "[]", not "{}".
            product["figures"] = (
                json.dumps(figures, ensure_ascii=False) if figures else "[]"
            )
        for change in request.get("legacy_copy", []):
            product = site["products"][str(change["product"])]
            side = {"_tv_legacy_acf_json": "en", "_linker_de_acf_json": "de"}[
                change["meta_key"]
            ]
            legacy = product.setdefault("legacy", {})
            decoded = json.loads(legacy.get(side) or "{}")
            node = decoded
            *parents, last = change["path"]
            for step in parents:
                node = node[step]
            node[last] = change["to"]
            legacy[side] = json.dumps(decoded, ensure_ascii=False)
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
    if "remove-legacy-group" in faults:
        # A write that loses a spec group through a path the PHP guard does
        # not see; the Python read-back must refuse the run.
        for product in site["products"].values():
            legacy = product.get("legacy") or {}
            for side, raw in legacy.items():
                if not raw:
                    continue
                decoded = json.loads(raw)
                if decoded.get("spec_groups"):
                    decoded["spec_groups"] = decoded["spec_groups"][1:]
                    legacy[side] = json.dumps(decoded, ensure_ascii=False)
    # The request counts as this site's write only once it applied: a refusal
    # is no write request seen (7-facts.php throws before any meta).
    site["writes"].append(request)


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
        try:
            write(site, request)
        except LegacyGroupRefusal as refusal:
            # What WP-CLI does when the PHP side throws: an error, no answer,
            # and nothing written.
            print(
                f"PHP Fatal error:  Uncaught RuntimeException: {refusal}",
                file=sys.stderr,
            )
            return 255
        site_path.write_text(json.dumps(site, ensure_ascii=False))
        answer = {"written": True}
    print("\n" + request["marker"] + json.dumps(answer, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
