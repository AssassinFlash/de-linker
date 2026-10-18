#!/usr/bin/env python3
"""Point product 2003's L260-OMNI portfolio entry at the two-page excerpt (#285 C2).

The full 44-page portfolio stays in the media library. Two product document
sources change: `_linker_documents` (the site's list) and the ACF `downloads`
rows (`_tv_legacy_acf_json`, `_linker_de_acf_json`) that the knowledge index
reads for model tags. The excerpt is media item 7367, the same pattern as the
pp. 17-18 excerpt beside the full datasheet.

    python3 tools/migrate/285-l260-documents.py --wp "just wp c254"
    python3 tools/migrate/285-l260-documents.py --wp "just wp c254" \
        --write --backup-dir /tmp/285-l260

Production needs the SSH WP-CLI command and --production:

    python3 tools/migrate/285-l260-documents.py --wp \
        "ssh hostinger-de-linker /usr/local/bin/wp --path=/home/u388076051/domains/de-linker.com/public_html" \
        --write --production --backup-dir ~/de-linker-data/285-l260

Without --write it only reports apply / done / drift per field. With --write
it refuses on drift, saves the current product state outside the repository,
writes the applying fields, reads back and fails unless every field holds the
reviewed target and the product's name, SKU, status, prices and stock fields
are unchanged. Rollback is the saved JSON: run the same script with a plan
whose `to` values are the saved lists.
"""

from __future__ import annotations

import argparse
import base64
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PLAN = Path(__file__).with_name("285-l260-documents.json")
PHP = Path(__file__).with_name("285-l260-documents.php")
PAYLOAD = "'285-l260-documents-payload'"
MARKER = "@@285-l260-documents@@"
PRODUCTION_HOST = "de-linker.com"
PROTECTED = (
    "name",
    "sku",
    "status",
    "price",
    "regular_price",
    "sale_price",
    "stock_status",
    "stock_quantity",
)


def run(wp: list[str], request: dict[str, Any]) -> dict[str, Any]:
    """Run the PHP side with the request; return its decoded answer."""
    php = PHP.read_text(encoding="utf-8")
    if php.count(PAYLOAD) != 1:
        sys.exit(f"{PHP.name} must contain {PAYLOAD} exactly once.")
    payload = {**request, "marker": MARKER}
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    result = subprocess.run(
        [*wp, "eval-file", "-"],
        input=php.replace(PAYLOAD, f"'{encoded}'"),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.exit(
            f"wp eval-file failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    line = next(
        (line for line in result.stdout.splitlines() if line.startswith(MARKER)),
        None,
    )
    if line is None:
        sys.exit(f"no {MARKER} answer in wp eval-file output")
    answer = json.loads(base64.b64decode(line[len(MARKER) :]).decode())
    if not isinstance(answer, dict):
        sys.exit(f"{MARKER} answer is not a JSON object")
    return {str(key): value for key, value in answer.items()}


def read_request(plan: dict[str, Any]) -> dict[str, Any]:
    """The PHP read request naming the document list and every downloads array."""
    return {
        "action": "read",
        "product": plan["product"],
        "meta_key": plan["meta_key"],
        "download_keys": [spec["meta_key"] for spec in plan.get("downloads", [])],
    }


def checks(plan: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    """Every reviewed field with its current, before and after values."""
    items = [
        {
            "label": plan["meta_key"],
            "kind": "documents",
            "meta_key": plan["meta_key"],
            "current": state["documents"],
            "from": plan["from"],
            "to": plan["to"],
        }
    ]
    for spec in plan.get("downloads", []):
        items.append(
            {
                "label": spec["meta_key"],
                "kind": "downloads",
                "meta_key": spec["meta_key"],
                "current": state["downloads"].get(spec["meta_key"]),
                "from": spec["from"],
                "to": spec["to"],
            }
        )
    return items


def status(check: dict[str, Any]) -> str:
    """done, apply or drift for one field."""
    if check["current"] == check["to"]:
        return "done"
    if check["current"] == check["from"]:
        return "apply"
    return "drift"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "--wp",
        required=True,
        help='WP-CLI command of the target site, e.g. "just wp c254"',
    )
    parser.add_argument(
        "--plan",
        type=Path,
        default=PLAN,
        help="plan file (default: the reviewed production plan beside this script)",
    )
    parser.add_argument(
        "--write", action="store_true", help="write the change (default: dry run)"
    )
    parser.add_argument(
        "--production", action="store_true", help=f"allow writing to {PRODUCTION_HOST}"
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="directory outside the repository for the current product state; "
        "required with --write",
    )
    args = parser.parse_args(argv)
    if args.write and args.backup_dir is None:
        parser.error("--write needs --backup-dir")

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    wp = shlex.split(args.wp)
    state = run(wp, read_request(plan))

    host = state["site"].split("://", 1)[-1].split("/", 1)[0]
    print(f"Site: {state['site']}")
    print(
        f"Product {state['product']}: {state['fields']['name']} "
        f"({state['fields']['sku']})"
    )

    reviewed = checks(plan, state)
    drifted = [check for check in reviewed if status(check) == "drift"]
    if drifted:
        for check in drifted:
            print(
                f"drift: {check['label']} is neither the reviewed before nor "
                "the reviewed after state."
            )
            print(
                "current:", json.dumps(check["current"], ensure_ascii=False, indent=1)
            )
            print("from:", json.dumps(check["from"], ensure_ascii=False, indent=1))
        return 1

    pending = [check for check in reviewed if status(check) == "apply"]
    if not pending:
        print("done: every reviewed field already holds the target.")
        return 0

    print("apply: " + ", ".join(str(check["label"]) for check in pending))
    if not args.write:
        print("dry run; add --write to apply.")
        return 0
    if host in (PRODUCTION_HOST, f"www.{PRODUCTION_HOST}") and not args.production:
        sys.exit(f"Refusing to write to {state['site']} without --production.")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = args.backup_dir / (
        f"285-l260-documents-backup-{host.replace(':', '_')}-{stamp}.json"
    )
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n")
    print(f"backup: {backup}")

    fields = [
        {
            "kind": check["kind"],
            "meta_key": check["meta_key"],
            "value": check["to"],
        }
        for check in pending
    ]
    run(
        wp,
        {
            "action": "write",
            "product": plan["product"],
            "fields": fields,
        },
    )
    after = run(wp, read_request(plan))
    remaining = [check for check in checks(plan, after) if status(check) != "done"]
    if remaining:
        sys.exit(
            "readback mismatch: "
            + ", ".join(str(check["label"]) for check in remaining)
        )
    changed = [
        key for key in PROTECTED if after["fields"].get(key) != state["fields"].get(key)
    ]
    if changed:
        sys.exit("fields the migration must not change changed: " + ", ".join(changed))
    print(
        f"done: product {plan['product']} now points at the excerpt; "
        "protected fields unchanged."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
