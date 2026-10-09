#!/usr/bin/env python3
"""Data changes of ticket #7, applied through WP-CLI.

The changes are data in 7-facts.json beside this script: product attributes
(pa_application, pa_phase) and product figures (_tv_b2b_figures entries), each
with the value read on the live site ("from"), the value to write ("to") and
the documents it rests on ("basis"). For every change the script reads the
target site and reports one of

  apply  the site holds "from": --write will write "to"
  done   the site already holds "to"
  drift  the site holds something else: nothing is written until a person
         has looked (the plan no longer describes the site)

Without --write it stops after the report (dry run). With --write it refuses
on any drift, saves what the touched products hold now to a backup file in
--backup-dir, writes, reads everything back and fails unless every change
reads "done" and no product's name, SKU, status, descriptions, prices or stock
fields changed. --reverse applies the plan backwards ("to" becomes "from"),
which undoes a write. Writing to https://de-linker.com also needs
--production; until the cutover (#17) the target is a local instance:

  python3 tools/migrate/7-facts.py --wp ~/de-linker-local/t7/wp
  python3 tools/migrate/7-facts.py --wp ~/de-linker-local/t7/wp --write --backup-dir ~/de-linker-local/t7/backups

The WordPress side is 7-facts.php, which WP-CLI evaluates (wp eval-file -).
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

PLAN = Path(__file__).with_name("7-facts.json")
PHP = Path(__file__).with_name("7-facts.php")
PHP_PAYLOAD = "'7-facts-payload'"
PRODUCTION_HOST = "de-linker.com"
FIGURES_META_KEY = "_tv_b2b_figures"
MARKER = "@@7-facts@@"
GROUPS = ("attributes", "figures")


def wp_eval(wp: list[str], request: dict[str, Any]) -> dict[str, Any]:
    """Runs 7-facts.php inside WordPress with the request; returns its answer."""
    php = PHP.read_text()
    if php.count(PHP_PAYLOAD) != 1:
        sys.exit(f"{PHP.name} must contain {PHP_PAYLOAD} exactly once.")
    payload = {**request, "marker": MARKER, "meta_key": FIGURES_META_KEY}
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    result = subprocess.run(
        [*wp, "eval-file", "-"],
        input=php.replace(PHP_PAYLOAD, f"'{encoded}'"),
        capture_output=True,
        text=True,
        check=False,
    )
    answer = next(
        (
            line[len(MARKER) :]
            for line in result.stdout.splitlines()
            if line.startswith(MARKER)
        ),
        None,
    )
    if result.returncode != 0 or answer is None:
        sys.exit(
            f"WP-CLI failed ({result.returncode}):\n{result.stdout}\n{result.stderr}"
        )
    loaded: dict[str, Any] = json.loads(answer)
    return loaded


def read_site(wp: list[str], plan: dict[str, Any]) -> dict[str, Any]:
    """The site URL and, per touched product, its attributes, raw figures and
    the fields the migration must not change."""
    ids = sorted({c["product"] for group in GROUPS for c in plan[group]})
    taxonomies = sorted({c["taxonomy"] for c in plan["attributes"]})
    return wp_eval(wp, {"action": "read", "products": ids, "taxonomies": taxonomies})


def current_value(site: dict[str, Any], group: str, change: dict[str, Any]) -> Any:
    """What the site holds for one change: term slugs, or a figure entry."""
    product = site["products"].get(str(change["product"]))
    if product is None:
        return None
    if group == "attributes":
        return product["attributes"][change["taxonomy"]]["terms"]
    figures = json.loads(product["figures"] or "{}")
    return figures.get(change["key"])


def is_done(site: dict[str, Any], group: str, change: dict[str, Any]) -> bool:
    """Whether the site holds "to"; an attribute must also be on the product."""
    if current_value(site, group, change) != change["to"]:
        return False
    if group == "attributes":
        product = site["products"][str(change["product"])]
        attached = product["attributes"][change["taxonomy"]]["attached"]
        return bool(attached == (change["to"] or None))
    return True


def status(site: dict[str, Any], group: str, change: dict[str, Any]) -> str:
    """apply, done or drift (see the module docstring)."""
    if is_done(site, group, change):
        return "done"
    return "apply" if current_value(site, group, change) == change["from"] else "drift"


def report(
    site: dict[str, Any], plan: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Prints one line per change and returns the changes by status."""
    by_status: dict[str, list[dict[str, Any]]] = {"apply": [], "done": [], "drift": []}
    for group in GROUPS:
        for change in plan[group]:
            state = status(site, group, change)
            by_status[state].append({"group": group, **change})
            if group == "attributes":
                field = change["taxonomy"]
            else:
                field = f"{FIGURES_META_KEY}.{change['key']}"
            current = short(current_value(site, group, change))
            target = short(change["to"])
            print(
                f"{state:5}  {change['product']:>5}  {field:46}  "
                f"{current} -> {target}  [{change['basis']}]"
            )
    print(
        f"\n{len(by_status['apply'])} to apply, {len(by_status['done'])} done, "
        f"{len(by_status['drift'])} drifted."
    )
    return by_status


def short(value: Any) -> str:
    """A value for the report: a figure entry as its value and unit."""
    if isinstance(value, dict):
        value = {k: value[k] for k in ("value", "unit") if k in value}
    return json.dumps(value, ensure_ascii=False)


def protected_changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Fields the migration must not change that differ between two reads."""
    changes = []
    for product_id, product in before["products"].items():
        if product is None:
            continue
        now = (after["products"].get(product_id) or {}).get("protected", {})
        for field, old in product["protected"].items():
            if now.get(field) != old:
                changes.append(f"{product_id}: {field} {old!r} -> {now.get(field)!r}")
    return changes


def reversed_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """The plan backwards: every change goes from its "to" to its "from"."""
    backwards = dict(plan)
    for group in GROUPS:
        backwards[group] = [
            {**c, "from": c["to"], "to": c["from"]} for c in plan[group]
        ]
    return backwards


def refuse(message: str) -> int:
    """Says on stderr, after the report, why nothing more is done."""
    sys.stdout.flush()
    print(message, file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "--wp",
        required=True,
        help="WP-CLI command of the target site, e.g. ~/de-linker-local/t7/wp",
    )
    parser.add_argument(
        "--write", action="store_true", help="write the changes (default: dry run)"
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="apply the plan backwards, undoing a write",
    )
    parser.add_argument(
        "--production", action="store_true", help=f"allow writing to {PRODUCTION_HOST}"
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="directory outside the repository for the products' current values; "
        "required with --write",
    )
    args = parser.parse_args(argv)
    if args.write and args.backup_dir is None:
        parser.error("--write needs --backup-dir")

    plan = json.loads(PLAN.read_text())
    if args.reverse:
        plan = reversed_plan(plan)
    wp = shlex.split(args.wp)

    site = read_site(wp, plan)
    print(f"Site: {site['siteurl']}{'  (plan reversed)' if args.reverse else ''}\n")
    by_status = report(site, plan)
    if not args.write:
        return 1 if by_status["drift"] else 0

    if by_status["drift"]:
        return refuse("Refusing to write: the site has drifted from the plan.")
    host = site["siteurl"].split("://", 1)[-1].split("/", 1)[0]
    if host in (PRODUCTION_HOST, f"www.{PRODUCTION_HOST}") and not args.production:
        return refuse(f"Refusing to write to {site['siteurl']} without --production.")
    if not by_status["apply"]:
        print("Nothing to write.")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = args.backup_dir / f"7-facts-backup-{host.replace(':', '_')}-{stamp}.json"
    backup.write_text(json.dumps(site, ensure_ascii=False, indent=1) + "\n")
    print(f"Backup of the current values: {backup}")

    wp_eval(
        wp,
        {
            "action": "write",
            "new_attribute": plan["new_attribute"],
            "attributes": [c for c in by_status["apply"] if c["group"] == "attributes"],
            "figures": [c for c in by_status["apply"] if c["group"] == "figures"],
        },
    )

    print("\nRead back:")
    after_site = read_site(wp, plan)
    after = report(after_site, plan)
    changed = protected_changes(site, after_site)
    if changed:
        return refuse(
            "Fields the migration must not change changed:\n" + "\n".join(changed)
        )
    total = sum(len(plan[group]) for group in GROUPS)
    return 0 if len(after["done"]) == total else refuse("Not every change reads done.")


if __name__ == "__main__":
    sys.exit(main())
