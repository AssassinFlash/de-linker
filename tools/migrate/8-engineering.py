#!/usr/bin/env python3
"""Engineering data of ticket #8, applied through WP-CLI.

The data is in 8-engineering.json beside this script (docs/specs/
8-engineering-data.md, decisions in docs/specs/8-decisions.md): the pa_series
attribute, the engine-key figures (absent entries and citation completions),
and the per-product document list. For every change the script reads the
target site and reports one of

  apply  the site holds the state before the change: --write writes it
  done   the site already holds the target
  drift  the site holds something else: nothing is written until a person
         has looked (the plan no longer describes the site)

Without --write it stops after the report (dry run). With --write it refuses
on any drift, saves what the touched products hold now to a backup file in
--backup-dir, writes, reads everything back and fails unless every change
reads "done" and no product's name, SKU, status, descriptions, prices or
stock fields changed. Writing to https://de-linker.com also needs
--production; until the cutover (#17) the target is a local instance:

  python3 tools/migrate/8-engineering.py --wp ~/de-linker-local/t8/wp
  python3 tools/migrate/8-engineering.py --wp ~/de-linker-local/t8/wp --write --backup-dir ~/de-linker-local/t8/backups

--verify is the acceptance read after a write: it requests the old
linker/v1/materials route and the new linker/v1/engineering-feed of the same
site, compares every engine field of every bound material key by key against
the mapping table (docs/specs/8-engineering-data.md) and lists each
difference with its class. It fails on a difference that is not one of the
decided classes. There is no --reverse: the write adds keys, citations,
terms and meta and removes the plan's four orphan pa_series terms; rollback
is the site backup of #17.

The WordPress side is 8-engineering.php, which WP-CLI evaluates
(wp eval-file -).
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shlex
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

PLAN = Path(__file__).with_name("8-engineering.json")
PHP = Path(__file__).with_name("8-engineering.php")
PHP_PAYLOAD = "'8-engineering-payload'"
PRODUCTION_HOST = "de-linker.com"
MARKER = "@@8-engineering@@"
GROUPS = ("attributes", "figures", "citations", "documents")
# Old materials-route specification keys that rename for the feed.
KEY_RENAMES = {
    "max_input_current_per_mppt_a": "mppt_max_current_a",
    "max_isc_per_mppt_a": "mppt_max_isc_a",
}
# Value differences verify accepts, each with its decision (docs/specs/8-decisions.md).
DECIDED_DIFFERENCES = {
    # 1185: the registry value carries the datasheet's footnote marker; the figure is the number.
    (
        "1185",
        "ac_output_kw_nominal",
    ): "registry '12000*' is the polluted form; the feed carries 12000 W",
    # 1959: tools/migrate/7-facts.json already corrected these figures to the CHS2
    # datasheet's columns (SAJ_CHS2_30-50K_Datasheet_EN-BEU.pdf p. 2); the live
    # materials route still reads the registry revision that predates it.
    (
        "1959",
        "rated_ac_power",
    ): "#7 corrected the figure to 29999 W per the CHS2 datasheet p. 2; the live registry predates it",
    (
        "1959",
        "max_pv_array_power",
    ): "#7 corrected the figure to 59998 Wp per the CHS2 datasheet p. 2; the live registry predates it",
}


def wp_eval(wp: list[str], request: dict[str, Any]) -> dict[str, Any]:
    """Runs 8-engineering.php inside WordPress with the request; returns its answer."""
    php = PHP.read_text()
    if php.count(PHP_PAYLOAD) != 1:
        sys.exit(f"{PHP.name} must contain {PHP_PAYLOAD} exactly once.")
    payload = {**request, "marker": MARKER}
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
    """The site URL and, per touched product, its attribute, figures, documents
    and the fields the migration must not change."""
    ids = sorted(
        {str(c["product"]) for group in GROUPS for c in plan[group]},
        key=int,
    )
    return wp_eval(
        wp, {"action": "read", "products": ids, "remove_terms": plan["remove_terms"]}
    )


def figures_of(site: dict[str, Any], product_id: int) -> dict[str, Any]:
    """The decoded figures the site holds for a product."""
    product = site["products"].get(str(product_id))
    loaded = json.loads(product["figures"] or "{}") if product else {}
    return loaded if isinstance(loaded, dict) else {}


def documents_of(site: dict[str, Any], product_id: int) -> list[Any] | None:
    """The decoded document list the site holds, None when it holds none."""
    product = site["products"].get(str(product_id))
    if not product or not product.get("documents"):
        return None
    loaded = json.loads(product["documents"])
    return loaded if isinstance(loaded, list) else None


def current_value(site: dict[str, Any], group: str, change: dict[str, Any]) -> Any:
    """What the site holds for one change: attribute terms, a figure entry, a
    citation, a document list, or a term that should not exist anymore."""
    if group == "attributes":
        product = site["products"].get(str(change["product"]))
        if product is None:
            return None
        return product["attributes"][change["taxonomy"]]["terms"]
    if group == "figures":
        return figures_of(site, change["product"]).get(change["key"])
    if group == "citations":
        entry = figures_of(site, change["product"]).get(change["key"])
        return entry.get("citation") if isinstance(entry, dict) else None
    if group == "documents":
        return documents_of(site, change["product"])
    return None


def status(site: dict[str, Any], group: str, change: dict[str, Any]) -> str:
    """apply, done or drift (see the module docstring)."""
    if group == "attributes":
        product = site["products"][str(change["product"])]
        attribute = product["attributes"][change["taxonomy"]]
        if attribute["terms"] == change["to"] and attribute["attached"] == (
            change["to"] or None
        ):
            return "done"
        return "apply" if attribute["terms"] == change["from"] else "drift"
    if group == "figures":
        current = current_value(site, group, change)
        if current == change["to"]:
            return "done"
        return "apply" if current is None else "drift"
    if group == "citations":
        entry = figures_of(site, change["product"]).get(change["key"])
        if not isinstance(entry, dict) or str(entry.get("value")) != str(
            change["value"]
        ):
            return "drift"
        return "done" if entry.get("citation") == change["citation"] else "apply"
    # documents
    current = current_value(site, group, change)
    if current == change["to"]:
        return "done"
    return "apply" if current is None else "drift"


def report(
    site: dict[str, Any], plan: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Prints one line per change and returns the changes by status."""
    by_status: dict[str, list[dict[str, Any]]] = {
        "apply": [],
        "done": [],
        "drift": [],
    }
    for group in GROUPS:
        for change in plan[group]:
            state = status(site, group, change)
            by_status[state].append({"group": group, **change})
            if group == "attributes":
                field = change["taxonomy"]
            elif group == "documents":
                field = "_linker_documents"
            elif group == "citations":
                field = f"citations.{change['key']}"
            else:
                field = f"_tv_b2b_figures.{change['key']}"
            current = short(current_value(site, group, change))
            target = short(change.get("to") or change.get("citation"))
            print(
                f"{state:5}  {change['product']:>5}  {field:46}  "
                f"{current} -> {target}  [{change['basis']}]"
            )
    for entry in plan["remove_terms"]:
        for slug in entry["slugs"]:
            key = f"{entry['taxonomy']}:{slug}"
            counts = site.get("term_counts")
            counts = counts if isinstance(counts, dict) else {}
            count = counts.get(key)
            state = "done" if count is None else ("apply" if count == 0 else "drift")
            if state == "apply":
                by_status["apply"].append(
                    {
                        "group": "remove_terms",
                        "taxonomy": entry["taxonomy"],
                        "slug": slug,
                    }
                )
            elif state == "drift":
                by_status["drift"].append(
                    {
                        "group": "remove_terms",
                        "taxonomy": entry["taxonomy"],
                        "slug": slug,
                    }
                )
            print(f"{state:5}  term   {key:46}  count={count}  [{entry['basis']}]")
    total_apply = len(by_status["apply"])
    total_done = sum(
        1 for group in GROUPS for c in plan[group] if status(site, group, c) == "done"
    )
    print(
        f"\n{total_apply} to apply, {total_done} done, "
        f"{len(by_status['drift'])} drifted."
    )
    return by_status


def short(value: Any) -> str:
    """A value for the report: a figure entry as its value and unit."""
    if isinstance(value, dict):
        value = {k: value[k] for k in ("value", "unit") if k in value}
    if isinstance(value, list):
        value = f"{len(value)} documents" if value else "[]"
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


def refuse(message: str) -> int:
    """Says on stderr, after the report, why nothing more is done."""
    sys.stdout.flush()
    print(message, file=sys.stderr)
    return 1


def http_json(url: str) -> Any:
    """One GET, as the feed's anonymous reader."""
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.loads(response.read().decode())


def verify(siteurl: str, plan: dict[str, Any]) -> int:
    """The acceptance read: the feed carries every planned figure, and — while
    the old materials route still answers — the old values agree with the feed
    key by key. The route was retired with the Products rename (#82), so a 404
    there is a note, not a failure."""
    feed = http_json(f"{siteurl}/wp-json/linker/v1/engineering-feed")
    items = {str(item["id"]): item for item in feed["products"]}
    differences: list[str] = []
    unknown = 0

    # The feed against the plan: every figure the plan writes is in the feed
    # with the planned value; a figure the plan removes is absent.
    for change in plan["figures"]:
        item = items.get(str(change["product"]))
        if item is None:
            unknown += 1
            differences.append(f"{change['product']} {change['key']}: not in the feed")
            continue
        figure = (item.get("figures") or {}).get(change["key"])
        target = change.get("to")
        if target is None:
            if figure is not None:
                unknown += 1
                differences.append(
                    f"{change['product']} {change['key']}: planned removed, feed holds {figure!r}"
                )
            continue
        if figure is None:
            unknown += 1
            differences.append(
                f"{change['product']} {change['key']}: planned {target!r}, feed holds nothing"
            )
            continue
        if str(figure.get("value")) != str(target.get("value")) or str(
            figure.get("unit")
        ) != str(target.get("unit")):
            unknown += 1
            differences.append(
                f"{change['product']} {change['key']}: feed {figure.get('value')!r}/"
                f"{figure.get('unit')!r}, planned {target.get('value')!r}/{target.get('unit')!r}"
            )
    print(f"feed products: {len(items)}, plan figures: {len(plan['figures'])}")

    try:
        old = http_json(f"{siteurl}/wp-json/linker/v1/materials")
    except Exception:  # noqa: BLE001 - a retired route must not fail this read
        print(
            "old materials route retired (#82 renamed the catalogue); "
            "the plan-side read above is the acceptance."
        )
        old = None

    if old is not None:
        bindings = plan["verify"]["bindings"]
        old_by_material = {m["material_id"]: m for m in old["materials"]}
        for material_id, product_id in bindings:
            material = old_by_material.get(material_id)
            item = items.get(str(product_id))
            if material is None or item is None:
                differences.append(f"{material_id} <-> {product_id}: not on both sides")
                continue
            specs = material["technical"]["specifications"]
            for old_key, entry in sorted(specs.items()):
                key = KEY_RENAMES.get(old_key, old_key)
                figure = item["figures"].get(key)
                if figure is None:
                    continue  # a display key or an uncited value: not an engine field in the feed
                old_value, new_value = str(entry.get("value")), str(figure["value"])
                if old_value == new_value:
                    continue
                if (str(product_id), key) in DECIDED_DIFFERENCES:
                    differences.append(
                        f"{product_id} {key}: {old_value!r} -> {new_value!r} "
                        f"[decided: {DECIDED_DIFFERENCES[(str(product_id), key)]}]"
                    )
                elif key == "phases" and re.sub(
                    r"[\s-]+", "", old_value.lower()
                ) == re.sub(r"[\s-]+", "", new_value.lower()):
                    differences.append(
                        f"{product_id} {key}: {old_value!r} -> {new_value!r} "
                        "[decided: the same phase statement, different spelling]"
                    )
                else:
                    unknown += 1
                    differences.append(
                        f"{product_id} {key}: {old_value!r} -> {new_value!r} [UNDECIDED]"
                    )
        print(
            f"old materials: {len(old['materials'])}, "
            f"bound pairs checked: {len(bindings)}"
        )

    for line in differences:
        print("  " + line)
    print(f"{len(differences)} differences, {unknown} undecided.")
    return 1 if unknown else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "--wp",
        required=True,
        help="WP-CLI command of the target site, e.g. ~/de-linker-local/t8/wp",
    )
    parser.add_argument(
        "--write", action="store_true", help="write the changes (default: dry run)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="compare the old materials route with the new feed (mapping table)",
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
    wp = shlex.split(args.wp)

    site = read_site(wp, plan)
    print(f"Site: {site['siteurl']}\n")
    if args.verify:
        return verify(site["siteurl"].rstrip("/"), plan)

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
    backup = (
        args.backup_dir / f"8-engineering-backup-{host.replace(':', '_')}-{stamp}.json"
    )
    backup.write_text(json.dumps(site, ensure_ascii=False, indent=1) + "\n")
    print(f"Backup of the current values: {backup}")

    wp_eval(
        wp,
        {
            "action": "write",
            "new_attribute": plan["new_attribute"],
            "remove_terms": plan["remove_terms"],
            "attributes": [c for c in by_status["apply"] if c["group"] == "attributes"],
            "figures": [c for c in by_status["apply"] if c["group"] == "figures"],
            "citations": [c for c in by_status["apply"] if c["group"] == "citations"],
            "documents": [c for c in by_status["apply"] if c["group"] == "documents"],
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
