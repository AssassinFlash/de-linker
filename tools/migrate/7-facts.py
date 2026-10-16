#!/usr/bin/env python3
"""Data changes of ticket #7, applied through WP-CLI.

The changes are data in 7-facts.json beside this script, or in the file named
by --plan: product attributes (pa_application, pa_phase), product figures
(_tv_b2b_figures entries) and product page copy (one string of a legacy ACF
JSON, addressed by meta_key and path), each with the value read on the live
site ("from"), the value to write ("to") and the documents it rests on
("basis"). A figure whose "to" is null is removed. "from" may be one value or
a list of values the site may hold; any of them is "apply". For every change
the script reads the target site and reports one of

  apply  the site holds "from": --write will write "to"
  done   the site already holds "to"
  drift  the site holds something else: nothing is written until a person
         has looked (the plan no longer describes the site)

Without --write it stops after the report (dry run). With --write it refuses
on any drift, saves what the touched products hold now to a backup file in
--backup-dir, writes, reads everything back and fails unless every change
reads "done", no product's name, SKU, status, descriptions, prices or stock
fields changed, and no spec group left a touched product's legacy tables
(7-facts.php drops an emptied group only where the change names it in
drop_legacy.remove_groups; the read-back refuses an undeclared loss too).
--reverse applies the plan backwards ("to" becomes "from"), which undoes a
write. Writing to https://de-linker.com also needs --production; until the
cutover (#17) the target is a local instance:

  python3 tools/migrate/7-facts.py --wp ~/de-linker-local/t7/wp
  python3 tools/migrate/7-facts.py --wp ~/de-linker-local/t7/wp --write --backup-dir ~/de-linker-local/t7/backups
  python3 tools/migrate/7-facts.py --plan tools/migrate/c15-facts.json --wp ~/de-linker-local/t110/wp.sh

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
GROUPS = ("attributes", "figures", "legacy_copy")
# The rendered copy of the product page: the English table and the German twin,
# both on the English product (7-facts.php carries the same map).
LEGACY_KEYS = {"_tv_legacy_acf_json": "en", "_linker_de_acf_json": "de"}


def plan_changes(plan: dict[str, Any], group: str) -> list[dict[str, Any]]:
    """The changes of one group; a plan may carry only some of the groups."""
    changes = plan.get(group) or []
    return list(changes)


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
    ids = sorted({c["product"] for group in GROUPS for c in plan_changes(plan, group)})
    taxonomies = sorted({c["taxonomy"] for c in plan_changes(plan, "attributes")})
    return wp_eval(wp, {"action": "read", "products": ids, "taxonomies": taxonomies})


def expected_from(group: str, change: dict[str, Any]) -> list[Any]:
    """The values "apply" accepts.

    An attribute's "from" is the term list itself. A figure's or a copy
    change's "from" may be a list of recorded values the site may hold
    (stored entries, strings, or None for "the key is absent"); any of them
    is apply.
    """
    if group == "attributes":
        return [change["from"]]
    source = change["from"]
    if (
        isinstance(source, list)
        and source
        and all(item is None or isinstance(item, (dict, str)) for item in source)
    ):
        return list(source)
    return [source]


def legacy_value(site: dict[str, Any], change: dict[str, Any]) -> Any:
    """The string a copy change addresses in the product's legacy meta, or None
    when the meta, the JSON or the path does not hold one."""
    product = site["products"].get(str(change["product"]))
    if product is None:
        return None
    side = LEGACY_KEYS.get(change["meta_key"])
    raw = (product.get("legacy") or {}).get(side)
    if not raw:
        return None
    try:
        decoded: Any = json.loads(raw)
    except json.JSONDecodeError:
        return None
    for step in change["path"]:
        try:
            decoded = decoded[step]
        except (KeyError, IndexError, TypeError):
            return None
    return decoded


def current_value(site: dict[str, Any], group: str, change: dict[str, Any]) -> Any:
    """What the site holds for one change: term slugs, a figure entry, or the
    addressed copy string."""
    product = site["products"].get(str(change["product"]))
    if product is None:
        return None
    if group == "attributes":
        return product["attributes"][change["taxonomy"]]["terms"]
    if group == "legacy_copy":
        return legacy_value(site, change)
    figures = json.loads(product["figures"] or "{}")
    # A product whose last figure was deleted stores "[]" — the write's own
    # wp_json_encode of an emptied PHP array, not an object. An emptied map
    # holds no keys; reading it must not crash the report.
    if not isinstance(figures, dict):
        figures = {}
    return figures.get(change["key"])


def legacy_row_present(raw: str, titles: list[str], labels: list[str]) -> bool:
    """Whether a legacy spec table still has the row a deletion names."""
    try:
        decoded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return False
    if not isinstance(decoded, dict):
        return False
    for group in decoded.get("spec_groups") or []:
        if not isinstance(group, dict):
            continue
        if str(group.get("spec_group_title") or "") not in titles:
            continue
        for row in group.get("spec_rows") or []:
            if isinstance(row, dict) and str(row.get("spec_label") or "") in labels:
                return True
    return False


def is_done(site: dict[str, Any], group: str, change: dict[str, Any]) -> bool:
    """Whether the site holds "to"; an attribute must also be on the product."""
    if current_value(site, group, change) != change["to"]:
        return False
    if group == "attributes":
        product = site["products"][str(change["product"])]
        attached = product["attributes"][change["taxonomy"]]["attached"]
        return bool(attached == (change["to"] or None))
    if group == "legacy_copy":
        return True
    drop = change.get("drop_legacy")
    if isinstance(drop, dict):
        product = site["products"][str(change["product"])]
        legacy = product.get("legacy") or {}
        titles = [str(item) for item in drop.get("titles") or []]
        labels = [str(item) for item in drop.get("labels") or []]
        if any(legacy_row_present(raw, titles, labels) for raw in legacy.values()):
            return False
    return True


def status(site: dict[str, Any], group: str, change: dict[str, Any]) -> str:
    """apply, done or drift (see the module docstring)."""
    if is_done(site, group, change):
        return "done"
    # A deleted figure whose legacy row is still on the page: the key is
    # already gone, so "from" no longer matches, but the row still has to go.
    if (
        group == "figures"
        and change["to"] is None
        and current_value(site, group, change) is None
        and isinstance(change.get("drop_legacy"), dict)
    ):
        return "apply"
    return (
        "apply"
        if current_value(site, group, change) in expected_from(group, change)
        else "drift"
    )


def report(
    site: dict[str, Any], plan: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Prints one line per change and returns the changes by status."""
    by_status: dict[str, list[dict[str, Any]]] = {"apply": [], "done": [], "drift": []}
    for group in GROUPS:
        for change in plan_changes(plan, group):
            state = status(site, group, change)
            by_status[state].append({"group": group, **change})
            if group == "attributes":
                field = change["taxonomy"]
            elif group == "legacy_copy":
                field = (
                    f"{change['meta_key']}[{'.'.join(str(s) for s in change['path'])}]"
                )
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


def legacy_groups(raw: Any) -> set[str]:
    """The spec group titles one legacy table states."""
    try:
        decoded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return set()
    if not isinstance(decoded, dict):
        return set()
    return {
        str(group.get("spec_group_title") or "")
        for group in decoded.get("spec_groups") or []
        if isinstance(group, dict)
    }


def declared_removals(applied: list[dict[str, Any]]) -> dict[str, set[str]]:
    """The groups each product's applied changes name in drop_legacy.remove_groups."""
    declared: dict[str, set[str]] = {}
    for change in applied:
        drop = change.get("drop_legacy")
        if isinstance(drop, dict):
            declared.setdefault(str(change["product"]), set()).update(
                str(item) for item in drop.get("remove_groups") or []
            )
    return declared


def legacy_groups_lost(
    before: dict[str, Any], after: dict[str, Any], applied: list[dict[str, Any]]
) -> list[str]:
    """Spec groups that a write removed from a touched product's legacy tables
    without the change saying so (drop_legacy.remove_groups).

    A group is a tab of the product page: a change that removes one changes
    the page's structure, so the plan has to name it — a row drop that empties
    its group and stays silent is the C15 accident (2026-10-13, the Inverter
    side group left t110 with its last row).
    """
    declared = declared_removals(applied)
    lost = []
    for product_id, product in before["products"].items():
        if product is None:
            continue
        legacy = product.get("legacy") or {}
        now = (after["products"].get(product_id) or {}).get("legacy") or {}
        for side, raw in legacy.items():
            for title in sorted(legacy_groups(raw) - legacy_groups(now.get(side))):
                if title not in declared.get(product_id, set()):
                    lost.append(f"{product_id} {side}: {title!r}")
    return lost


def reversed_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """The plan backwards: every change goes from its "to" to its "from"."""
    backwards = dict(plan)
    for group in GROUPS:
        if group not in plan:
            continue
        reversed_changes = []
        for change in plan[group]:
            source = expected_from(group, change)
            if change["to"] is None:
                # A deleted key has nothing to put back, and more than one
                # recorded "from" has no single value to restore.
                if len(source) != 1:
                    raise ValueError(
                        f"{change['product']} {change.get('key', change.get('meta_key', change.get('taxonomy')))} "
                        "deletes a key from more than one recorded value; it cannot be reversed."
                    )
            reversed_changes.append({**change, "from": change["to"], "to": source[0]})
        backwards[group] = reversed_changes
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
        "--plan",
        type=Path,
        help="facts plan to apply instead of 7-facts.json (same from/to shape)",
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

    plan_path = args.plan if args.plan is not None else PLAN
    plan = json.loads(plan_path.read_text())
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
    label = "7-facts" if plan_path.name == PLAN.name else plan_path.stem
    backup = args.backup_dir / f"{label}-backup-{host.replace(':', '_')}-{stamp}.json"
    backup.write_text(json.dumps(site, ensure_ascii=False, indent=1) + "\n")
    print(f"Backup of the current values: {backup}")

    wp_eval(
        wp,
        {
            "action": "write",
            "new_attribute": plan["new_attribute"],
            "attributes": [c for c in by_status["apply"] if c["group"] == "attributes"],
            "figures": [c for c in by_status["apply"] if c["group"] == "figures"],
            "legacy_copy": [
                c for c in by_status["apply"] if c["group"] == "legacy_copy"
            ],
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
    lost = legacy_groups_lost(site, after_site, by_status["apply"])
    if lost:
        return refuse(
            "The write removed spec groups the plan does not name "
            "(drop_legacy.remove_groups):\n" + "\n".join(lost)
        )
    total = sum(len(plan_changes(plan, group)) for group in GROUPS)
    return 0 if len(after["done"]) == total else refuse("Not every change reads done.")


if __name__ == "__main__":
    sys.exit(main())
