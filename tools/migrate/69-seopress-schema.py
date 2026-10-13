#!/usr/bin/env python3
"""#69 migration: a product page carries one Product node, and it is ours.

Runs against a WordPress through WP-CLI (the pattern of 9-i18n.py and
68-contact-form.py):

    python3 tools/migrate/69-seopress-schema.py --wp ~/de-linker-local/t110/wp.sh plan
    python3 tools/migrate/69-seopress-schema.py --wp ~/de-linker-local/t110/wp.sh apply --write
    python3 tools/migrate/69-seopress-schema.py --wp ~/de-linker-local/t110/wp.sh verify

What changes (debt ①, 2026-10-13; docs/acceptance/2026-10-13/debts/):

SEOPress PRO keeps a library of schema templates as the post type
`seopress_schemas`. On `wp_head` priority 2, `seopress_pro_rich_snippets`
(wp-seopress-pro/inc/functions/options.php) includes
options-automatic-rich-snippets.php, which queries every published row of that
type and, when `_seopress_pro_rich_snippets_rules` matches the current post,
prints the row. The product row is a custom template
(`_seopress_pro_rich_snippets_type` = custom, body in
`_seopress_pro_rich_snippets_custom_manual_custom_global`) whose rule is
`post_type equal product`. Its body is a fixed Product node: brand and
manufacturer "Linker", category "Energy storage system", no sku, no model, no
image, no availability. It applies to every product of every brand.

This tree already emits the product page's Product node
(plugins/linker-commerce/includes/Storefront/ProductSchema.php), from the
product's own brand, sku and stock. Leaving the row published puts two
contradictory Product nodes on every product page.

The row is retired by making it a draft, which is the plugin's own off switch:
the query that applies a template is `WP_Query` with the default
`post_status=publish` (options-automatic-rich-snippets.php), and a draft is a
row an operator can put back by hand. The row is not deleted. The master
switch `seopress_rich_snippets_enable` stays on, and every other template
(article, collection, contact, about) stays published: nothing else emits
those, and none of them is a Product node.

Idempotent: a second run finds no published Product template and reports
nothing to do. A published template that is not a Product node is left alone.
A Product template whose type is not `custom` is refused rather than drafted:
this migration knows one shape, the stored custom body, and drafting a
different one would be a guess.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from typing import Any

# WP-CLI's PHP diagnostics, which must not be parsed as the listing.
PHP_DIAGNOSTIC = re.compile(
    r"^(PHP (Warning|Notice|Deprecated|Fatal error)|Warning:|Notice:|Deprecated:|Fatal error):"
)

# The plugin's own post type and the meta the emitter reads. Both names are
# SEOPress PRO's (inc/functions/options-automatic-rich-snippets.php).
POST_TYPE = "seopress_schemas"
TYPE_META = "_seopress_pro_rich_snippets_type"
BODY_META = "_seopress_pro_rich_snippets_custom_manual_custom_global"
RULES_META = "_seopress_pro_rich_snippets_rules"

# The node this migration retires, and the only template type it knows how to
# retire. A Product node stored any other way is reported and not touched.
RETIRED_TYPE = "Product"
KNOWN_TEMPLATE = "custom"

LIST_PHP = f"""
$out = array();
foreach ( get_posts( array(
    'post_type' => '{POST_TYPE}',
    'post_status' => 'any',
    'numberposts' => -1,
    'orderby' => 'ID',
    'order' => 'ASC',
) ) as $row ) {{
    $body = (string) get_post_meta( $row->ID, '{BODY_META}', true );
    $out[] = array(
        'id' => (int) $row->ID,
        'title' => $row->post_title,
        'status' => $row->post_status,
        'type' => (string) get_post_meta( $row->ID, '{TYPE_META}', true ),
        'rules' => get_post_meta( $row->ID, '{RULES_META}', true ),
        'product' => 1 === preg_match( '/"@type"\\s*:\\s*"{RETIRED_TYPE}"/', $body ),
    );
}}
echo wp_json_encode( $out );
"""


class WP:
    """WP-CLI, as a command prefix (the 68-contact-form.py wrapper)."""

    def __init__(self, command: str) -> None:
        self.prefix = shlex.split(command)

    def run(self, *args: str) -> str:
        result = subprocess.run(
            [*self.prefix, *args], capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            raise SystemExit(
                f"wp {' '.join(args[:3])} failed:\n{result.stderr.strip()}"
            )
        lines = result.stdout.splitlines()
        return "\n".join(line for line in lines if not PHP_DIAGNOSTIC.match(line))

    def json(self, *args: str) -> Any:
        out = self.run(*args)
        start = min((i for i in (out.find("["), out.find("{")) if i >= 0), default=-1)
        return json.loads(out[start:]) if start >= 0 else None

    def eval_php(self, code: str) -> Any:
        return self.json("eval", code)


def rows(wp: WP) -> list[dict[str, Any]]:
    """Every schema template, published or not."""
    listed = wp.eval_php(LIST_PHP)
    if not isinstance(listed, list):
        raise SystemExit("the schema listing did not return a list")
    return [row for row in listed if isinstance(row, dict)]


def stale(listed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Published templates whose stored body is a Product node.

    A draft is already retired: the plugin's query reads published rows only,
    so reporting it again would make a second run look like it still had work.
    """
    return [
        row for row in listed if row.get("product") and row.get("status") == "publish"
    ]


def describe(row: dict[str, Any]) -> str:
    return (
        f"#{row.get('id')} {row.get('title')!r} "
        f"status={row.get('status')} type={row.get('type')}"
    )


def refuse_unknown(found: list[dict[str, Any]]) -> None:
    """A Product template this migration does not know how to retire stops it."""
    unknown = [row for row in found if row.get("type") != KNOWN_TEMPLATE]
    if unknown:
        listed = "; ".join(describe(row) for row in unknown)
        raise SystemExit(
            "a published Product template is not the stored custom body this "
            f"migration retires; nothing is written: {listed}"
        )


def do_plan(wp: WP) -> int:
    listed = rows(wp)
    found = stale(listed)
    print(
        f"{len(listed)} schema templates, {len(found)} published carrying a "
        f"{RETIRED_TYPE} node",
        flush=True,
    )
    for row in listed:
        marker = "retire" if row in found else "keep"
        print(f"  {marker}: {describe(row)}", flush=True)
    refuse_unknown(found)
    if not found:
        print("nothing to retire", flush=True)
    return 0


def do_apply(wp: WP, write: bool) -> int:
    found = stale(rows(wp))
    refuse_unknown(found)
    if not found:
        print("nothing to retire", flush=True)
        return 0
    ids = [str(row["id"]) for row in found]
    for row in found:
        print(f"draft: {describe(row)}", flush=True)
    if not write:
        print("dry run: nothing written (add --write)", flush=True)
        return 0
    # Draft, not delete. The type does not support the trash (WP-CLI refuses
    # without --force), and a draft is the state the plugin's own query skips.
    wp.run("post", "update", *ids, "--post_status=draft")
    print("wp post update " + " ".join(ids) + " --post_status=draft", flush=True)
    return 0


def do_verify(wp: WP) -> int:
    listed = rows(wp)
    found = stale(listed)
    ok = not found
    if found:
        for row in found:
            print(f"still published: {describe(row)}", flush=True)
    else:
        print(f"no published {RETIRED_TYPE} template", flush=True)
    kept = [row for row in listed if row.get("status") == "publish"]
    print(f"{len(kept)} schema templates still published", flush=True)
    for row in kept:
        if row.get("product"):
            print(f"published Product template: {describe(row)}", flush=True)
            ok = False
    print("ok" if ok else "not ok", flush=True)
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--wp", required=True, help="WP-CLI command, e.g. ~/de-linker-local/t110/wp.sh"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--write", action="store_true")
    subparsers.add_parser("verify")
    args = parser.parse_args()

    wp = WP(args.wp)
    if args.command == "plan":
        return do_plan(wp)
    if args.command == "apply":
        return do_apply(wp, bool(args.write))
    return do_verify(wp)


if __name__ == "__main__":
    sys.exit(main())
