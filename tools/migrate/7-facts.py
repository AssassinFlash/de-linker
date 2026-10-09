#!/usr/bin/env python3
"""Data changes of ticket #7, applied through WP-CLI.

The changes are data in 7-facts.json beside this script: product attributes
(pa_application, pa_phase) and product figures (_tv_b2b_figures entries), each
with the value read on the live site ("from"), the value to write ("to") and
the document it rests on ("basis"). For every change the script reads the
target site and reports one of

  apply  the site holds "from": --write will write "to"
  done   the site already holds "to"
  drift  the site holds something else: nothing is written until a person
         has looked (the plan no longer describes the site)

Without --write it stops after the report (dry run). With --write it refuses
on any drift, saves what the touched products hold now to a backup file,
writes, reads everything back and fails unless every change reads "done".
--reverse applies the plan backwards ("to" becomes "from"), which undoes a
write. Writing to https://de-linker.com also needs --production; until the
cutover (#17) the target is a local instance:

  python3 tools/migrate/7-facts.py --wp ~/de-linker-local/t7/wp
  python3 tools/migrate/7-facts.py --wp ~/de-linker-local/t7/wp --write

Python 3.12, standard library only.
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
PRODUCTION_HOST = "de-linker.com"
FIGURES_META_KEY = "_tv_b2b_figures"
MARKER = "@@7-facts@@"

# Runs inside WordPress (wp eval-file -). $payload is the JSON the script
# embeds below; the answer is one JSON line after MARKER on stdout.
PHP_READ = r"""
$linker_ids    = json_decode( base64_decode( '%(payload)s' ), true );
$linker_answer = array( 'siteurl' => get_option( 'siteurl' ), 'products' => array() );
foreach ( $linker_ids['products'] as $linker_id ) {
	$linker_product = wc_get_product( $linker_id );
	if ( ! $linker_product ) {
		$linker_answer['products'][ $linker_id ] = null;
		continue;
	}
	$linker_attributes = array();
	foreach ( $linker_ids['taxonomies'] as $linker_taxonomy ) {
		$linker_terms = wp_get_object_terms( $linker_id, $linker_taxonomy, array( 'fields' => 'slugs' ) );
		$linker_attached = null;
		$linker_attribute = $linker_product->get_attributes()[ $linker_taxonomy ] ?? null;
		if ( $linker_attribute instanceof WC_Product_Attribute ) {
			$linker_attached = array();
			foreach ( $linker_attribute->get_options() as $linker_term_id ) {
				$linker_term       = get_term( $linker_term_id, $linker_taxonomy );
				$linker_attached[] = $linker_term instanceof WP_Term ? $linker_term->slug : '#' . $linker_term_id;
			}
			sort( $linker_attached );
		}
		$linker_terms = is_wp_error( $linker_terms ) ? array() : $linker_terms;
		sort( $linker_terms );
		$linker_attributes[ $linker_taxonomy ] = array( 'terms' => $linker_terms, 'attached' => $linker_attached );
	}
	$linker_answer['products'][ $linker_id ] = array(
		'name'       => $linker_product->get_name(),
		'status'     => $linker_product->get_status(),
		'attributes' => $linker_attributes,
		'figures'    => (string) get_post_meta( $linker_id, '%(meta_key)s', true ),
	);
}
echo "\n%(marker)s" . wp_json_encode( $linker_answer ) . "\n";
"""

PHP_WRITE = r"""
$linker_plan = json_decode( base64_decode( '%(payload)s' ), true );
foreach ( $linker_plan['attributes'] as $linker_change ) {
	$linker_product    = wc_get_product( $linker_change['product'] );
	$linker_taxonomy   = $linker_change['taxonomy'];
	$linker_attributes = $linker_product->get_attributes();
	if ( array() === $linker_change['to'] ) {
		unset( $linker_attributes[ $linker_taxonomy ] );
	} else {
		$linker_attribute = $linker_attributes[ $linker_taxonomy ] ?? null;
		if ( $linker_attribute instanceof WC_Product_Attribute ) {
			// A copy: changing the product's own object leaves set_attributes() nothing to compare, and save() skips it.
			$linker_attribute = clone $linker_attribute;
		} else {
			$linker_settings  = $linker_plan['new_attribute'][ $linker_taxonomy ];
			$linker_attribute = new WC_Product_Attribute();
			$linker_attribute->set_id( wc_attribute_taxonomy_id_by_name( $linker_taxonomy ) );
			$linker_attribute->set_name( $linker_taxonomy );
			$linker_attribute->set_position( $linker_settings['position'] );
			$linker_attribute->set_visible( $linker_settings['visible'] );
			$linker_attribute->set_variation( false );
		}
		$linker_term_ids = array();
		foreach ( $linker_change['to'] as $linker_slug ) {
			$linker_term = get_term_by( 'slug', $linker_slug, $linker_taxonomy );
			if ( ! $linker_term instanceof WP_Term ) {
				WP_CLI::error( "No term {$linker_slug} in {$linker_taxonomy}." );
			}
			$linker_term_ids[] = $linker_term->term_id;
		}
		$linker_attribute->set_options( $linker_term_ids );
		$linker_attributes[ $linker_taxonomy ] = $linker_attribute;
	}
	$linker_product->set_attributes( $linker_attributes );
	$linker_product->save();
}
foreach ( $linker_plan['figures'] as $linker_change ) {
	$linker_figures = json_decode( (string) get_post_meta( $linker_change['product'], '%(meta_key)s', true ), true );
	if ( ! is_array( $linker_figures ) ) {
		WP_CLI::error( "Product {$linker_change['product']} has no readable figures." );
	}
	$linker_figures[ $linker_change['key'] ] = $linker_change['to'];
	// The stored figures are written with unescaped Unicode and slashes; keep that form.
	update_post_meta( $linker_change['product'], '%(meta_key)s', wp_slash( wp_json_encode( $linker_figures, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) ) );
	wc_delete_product_transients( $linker_change['product'] );
}
echo "\n%(marker)s" . wp_json_encode( array( 'written' => true ) ) . "\n";
"""


def wp_eval(wp: list[str], php: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Runs PHP inside WordPress with the payload embedded; returns its JSON answer."""
    code = "<?php\n" + php % {
        "payload": base64.b64encode(json.dumps(payload).encode()).decode(),
        "meta_key": FIGURES_META_KEY,
        "marker": MARKER,
    }
    result = subprocess.run(
        [*wp, "eval-file", "-"], input=code, capture_output=True, text=True, check=False
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
    """The site URL and, per touched product, its attributes and raw figures."""
    ids = sorted(
        {c["product"] for group in ("attributes", "figures") for c in plan[group]}
    )
    taxonomies = sorted({c["taxonomy"] for c in plan["attributes"]})
    return wp_eval(wp, PHP_READ, {"products": ids, "taxonomies": taxonomies})


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
    """Whether the site holds "to"; an attribute must also be attached to the product."""
    if current_value(site, group, change) != change["to"]:
        return False
    if group == "attributes":
        attached = site["products"][str(change["product"])]["attributes"][
            change["taxonomy"]
        ]["attached"]
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
    for group in ("attributes", "figures"):
        for change in plan[group]:
            state = status(site, group, change)
            by_status[state].append({"group": group, **change})
            field = (
                change["taxonomy"]
                if group == "attributes"
                else f"{FIGURES_META_KEY}.{change['key']}"
            )
            current = current_value(site, group, change)
            print(
                f"{state:5}  {change['product']:>5}  {field:46}  {short(current)} -> {short(change['to'])}  [{change['basis']}]"
            )
    print(
        f"\n{len(by_status['apply'])} to apply, {len(by_status['done'])} done, {len(by_status['drift'])} drifted."
    )
    return by_status


def short(value: Any) -> str:
    """A value for the report: a figure entry as its value and unit."""
    if isinstance(value, dict):
        return json.dumps(
            {k: value[k] for k in ("value", "unit") if k in value}, ensure_ascii=False
        )
    return json.dumps(value, ensure_ascii=False)


def reversed_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """The plan backwards: every change goes from its "to" to its "from"."""
    backwards = dict(plan)
    for group in ("attributes", "figures"):
        backwards[group] = [
            {**c, "from": c["to"], "to": c["from"]} for c in plan[group]
        ]
    return backwards


def refuse(message: str) -> int:
    """Says on stderr, after the report, why nothing is written."""
    sys.stdout.flush()
    print(message, file=sys.stderr)
    return 1


def main() -> int:
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
        default=Path.cwd(),
        help="where --write saves the products' current values",
    )
    args = parser.parse_args()

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

    backup = (
        args.backup_dir
        / f"7-facts-backup-{host.replace(':', '_')}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    )
    backup.write_text(json.dumps(site, ensure_ascii=False, indent=1) + "\n")
    print(f"Backup of the current values: {backup}")

    apply = {
        "new_attribute": plan["new_attribute"],
        "attributes": [c for c in by_status["apply"] if c["group"] == "attributes"],
        "figures": [c for c in by_status["apply"] if c["group"] == "figures"],
    }
    wp_eval(wp, PHP_WRITE, apply)

    print("\nRead back:")
    after = report(read_site(wp, plan), plan)
    return (
        0 if len(after["done"]) == len(plan["attributes"]) + len(plan["figures"]) else 1
    )


if __name__ == "__main__":
    sys.exit(main())
