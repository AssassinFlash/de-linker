#!/usr/bin/env python3
"""Repair the two stored German SEO values measured on 2026-10-29.

Runs against a WordPress through WP-CLI (the pattern of
tools/migrate/category-sitemap.py):

    python3 tools/migrate/twin-indexing-fixes.py --wp "<wp-cli command>" plan
    python3 tools/migrate/twin-indexing-fixes.py --wp "<wp-cli command>" apply --write --backup <file>
    python3 tools/migrate/twin-indexing-fixes.py --wp "<wp-cli command>" verify

Why these writes (measured on production, 2026-10-29):

1. The English thank-you page (post 623) carries
   `_seopress_robots_index = yes` while its German twin (post 6873,
   /de/danke/) does not. The source now mirrors this on save and at render
   time; this migration brings the existing twin's stored value in line and
   takes it out of SEOPress's page sitemap.

2. The installed German blog-index LiveCanvas template (post 6881) contains
   `[linker_site_url]de/blog/`. `[linker_site_url]` already resolves to /de/
   on the German request, so the rendered JSON-LD URL is /de/de/blog/. The
   repository source is corrected too; this write repairs the installed copy
   without replacing unrelated LiveCanvas data.

Guards: the script refuses unless post 623 still carries `yes`, the Polylang
translation of 623 resolves to a German page, post 6881 is the German blog
index template, and the doubled fragment occurs at most once. Idempotent: a
second run plans nothing. `apply` records both previous values in the
`--backup` file and reads every write back.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

PHP_DIAGNOSTIC = re.compile(
    r"^(PHP (Warning|Notice|Deprecated|Fatal error)|Warning:|Notice:|Deprecated:|Fatal error):"
)

ROBOTS_INDEX_META = "_seopress_robots_index"
SOURCE_ID = 623  # The English thank-you page, "Thank You", post_name thank-you.
BLOG_TEMPLATE_ID = 6881  # The German blog-index LiveCanvas dynamic template.
BLOG_TEMPLATE_SLUG = "vorlage-fur-blog-beitragsindex"
DOUBLED_FRAGMENT = "[linker_site_url]de/blog/"
CORRECT_FRAGMENT = "[linker_site_url]blog/"
JSONLD_SCRIPT = '<script type="application/ld+json">'

STATE_PHP = f"""
$source = get_post( {SOURCE_ID} );
$out = array( 'source' => null, 'twin' => null, 'template' => null );
if ( $source instanceof WP_Post ) {{
    $out['source'] = array(
        'id' => (int) $source->ID,
        'name' => (string) $source->post_name,
        'type' => (string) $source->post_type,
        'index' => (string) get_post_meta( $source->ID, '{ROBOTS_INDEX_META}', true ),
    );
}}
$twin_id = function_exists( 'pll_get_post' ) ? (int) pll_get_post( {SOURCE_ID}, 'de' ) : 0;
$twin = $twin_id > 0 ? get_post( $twin_id ) : null;
if ( $twin instanceof WP_Post ) {{
    $out['twin'] = array(
        'id' => (int) $twin->ID,
        'name' => (string) $twin->post_name,
        'type' => (string) $twin->post_type,
        'language' => function_exists( 'pll_get_post_language' ) ? (string) pll_get_post_language( $twin->ID ) : '',
        'index' => (string) get_post_meta( $twin->ID, '{ROBOTS_INDEX_META}', true ),
    );
}}
$template = get_post( {BLOG_TEMPLATE_ID} );
if ( $template instanceof WP_Post ) {{
    $out['template'] = array(
        'id' => (int) $template->ID,
        'name' => (string) $template->post_name,
        'type' => (string) $template->post_type,
        'language' => function_exists( 'pll_get_post_language' ) ? (string) pll_get_post_language( $template->ID ) : '',
        'doubled' => substr_count( $template->post_content, {json.dumps(DOUBLED_FRAGMENT)} ),
        'correct' => substr_count( $template->post_content, {json.dumps(CORRECT_FRAGMENT)} ),
        'scripts' => substr_count( $template->post_content, {json.dumps(JSONLD_SCRIPT)} ),
        'content' => (string) $template->post_content,
    );
}}
echo wp_json_encode( $out );
"""


def clean(output: str) -> str:
    """Drop the phar's own diagnostic lines."""
    return "\n".join(
        line for line in output.splitlines() if not PHP_DIAGNOSTIC.match(line)
    )


def run(prefix: list[str], *args: str) -> str:
    """Run one WP-CLI command. A failing command stops the script."""
    result = subprocess.run(
        [*prefix, *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(
            f"wp {' '.join(args[:4])} failed (exit {result.returncode}):\n"
            f"{result.stderr.strip()}"
        )
    return clean(result.stdout)


def transport_of(prefix: list[str]) -> list[str]:
    """The ssh part of a remote WP-CLI prefix, or nothing for a local one."""
    if not prefix or prefix[0] != "ssh":
        return []
    for index, part in enumerate(prefix):
        if part == "wp" or part.endswith("/wp"):
            return prefix[:index]
    raise SystemExit(f"no wp binary in the remote command: {' '.join(prefix)}")


def php(prefix: list[str], code: str) -> str:
    """Run PHP through `wp eval-file`, so no shell ever parses it."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".php", prefix="twin-indexing-", delete=False
    ) as handle:
        handle.write("<?php " + code)
        local = Path(handle.name)
    transport = transport_of(prefix)
    try:
        if transport:
            remote = f"/tmp/{local.name}"
            with local.open() as stream:
                sent = subprocess.run(
                    [*transport, f"cat > {shlex.quote(remote)}"],
                    stdin=stream,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            if sent.returncode != 0:
                raise SystemExit(
                    f"copying the eval file failed (exit {sent.returncode}):\n"
                    f"{sent.stderr.strip()}"
                )
            try:
                return run(prefix, "eval-file", remote)
            finally:
                subprocess.run(
                    [*transport, f"rm -f {shlex.quote(remote)}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
        return run(prefix, "eval-file", str(local))
    finally:
        local.unlink(missing_ok=True)


def read_state(prefix: list[str]) -> dict[str, Any]:
    """The source, its twin and the installed blog template in one process."""
    raw = php(prefix, STATE_PHP)
    start = raw.find("{")
    if start < 0:
        raise SystemExit(f"no state in wp eval output:\n{raw[:400]}")
    data = json.loads(raw[start:])
    if not isinstance(data, dict) or not isinstance(data.get("source"), dict):
        raise SystemExit(f"post {SOURCE_ID} did not read back")
    if not isinstance(data.get("twin"), dict):
        raise SystemExit(f"no German twin of post {SOURCE_ID} through pll_get_post")
    if not isinstance(data.get("template"), dict):
        raise SystemExit(f"blog-index template {BLOG_TEMPLATE_ID} did not read back")
    return data


def check_preconditions(state: dict[str, Any]) -> None:
    """Refuse unless the measured situation still holds."""
    source = state["source"]
    twin = state["twin"]
    template = state["template"]
    if source.get("name") != "thank-you" or source.get("type") != "page":
        raise SystemExit(f"post {SOURCE_ID} is not the thank-you page: {source!r}")
    if source.get("index") != "yes":
        raise SystemExit(
            f"post {SOURCE_ID} no longer carries {ROBOTS_INDEX_META}=yes "
            f"(now {source.get('index')!r}); the mirror must follow the source"
        )
    if twin.get("language") != "de" or twin.get("type") != "page":
        raise SystemExit(f"the twin is not a German page: {twin!r}")
    if (
        template.get("name") != BLOG_TEMPLATE_SLUG
        or template.get("type") != "lc_dynamic_template"
        or template.get("language") != "de"
    ):
        raise SystemExit(
            f"post {BLOG_TEMPLATE_ID} is not the German blog-index template: "
            f"{template!r}"
        )
    if template.get("doubled", 0) > 1:
        raise SystemExit(
            f"the doubled fragment occurs {template['doubled']} times in post "
            f"{template['id']}; this script only rewrites the single measured "
            "occurrence"
        )
    if template.get("scripts", 0) != 1:
        raise SystemExit(
            f"post {template['id']} carries {template.get('scripts')} JSON-LD "
            "scripts, expected 1"
        )


def plan(state: dict[str, Any]) -> list[dict[str, Any]]:
    """The writes the current state still needs."""
    check_preconditions(state)
    twin = state["twin"]
    template = state["template"]
    actions: list[dict[str, Any]] = []
    if twin.get("index") != "yes":
        actions.append(
            {
                "kind": "meta",
                "post": twin["id"],
                "key": ROBOTS_INDEX_META,
                "from": twin.get("index", ""),
                "to": "yes",
            }
        )
    if template.get("doubled", 0) == 1:
        actions.append(
            {
                "kind": "template",
                "post": template["id"],
                "from": DOUBLED_FRAGMENT,
                "to": CORRECT_FRAGMENT,
                "sha256": hashlib.sha256(
                    template.get("content", "").encode()
                ).hexdigest(),
            }
        )
    return actions


def template_write_code(action: dict[str, Any]) -> str:
    """PHP that protects, verifies and, on error, rolls back the template."""
    post_id = str(action["post"])
    return (
        "$previous = (string) get_post_field( 'post_content', "
        + post_id
        + " );\n"
        + "if ( ! hash_equals( "
        + json.dumps(action["sha256"])
        + ", hash( 'sha256', $previous ) ) ) { "
        + "throw new RuntimeException( 'The template changed after planning.' ); }\n"
        + f"if ( 1 !== substr_count( $previous, {json.dumps(JSONLD_SCRIPT)} ) ) {{ "
        + "throw new RuntimeException( 'The previous template has no unique JSON-LD script.' ); }\n"
        + "$content = str_replace( "
        + json.dumps(action["from"])
        + ", "
        + json.dumps(action["to"])
        + ", $previous );\n"
        + "$kses_was_on = false !== has_filter( 'content_save_pre', 'wp_filter_post_kses' );\n"
        + "try {\n"
        + "    if ( $kses_was_on ) { kses_remove_filters(); }\n"
        + "    $updated = wp_update_post( array( 'ID' => "
        + post_id
        + ", 'post_content' => $content ), true );\n"
        + "    if ( is_wp_error( $updated ) ) { "
        + "throw new RuntimeException( $updated->get_error_message() ); }\n"
        + "    $actual = (string) get_post_field( 'post_content', "
        + post_id
        + " );\n"
        + f"    if ( 1 !== substr_count( $actual, {json.dumps(JSONLD_SCRIPT)} ) ) {{ "
        + "throw new RuntimeException( 'The saved template lost its JSON-LD script.' ); }\n"
        + f"    if ( 0 !== substr_count( $actual, {json.dumps(DOUBLED_FRAGMENT)} ) ) {{ "
        + "throw new RuntimeException( 'The saved template still has the doubled URL.' ); }\n"
        + f"    if ( 1 !== substr_count( $actual, {json.dumps(CORRECT_FRAGMENT)} ) ) {{ "
        + "throw new RuntimeException( 'The saved template lacks the corrected URL.' ); }\n"
        + "} catch ( Throwable $failure ) {\n"
        + "    if ( $kses_was_on ) { kses_remove_filters(); }\n"
        + "    $rolled_back = wp_update_post( array( 'ID' => "
        + post_id
        + ", 'post_content' => $previous ), true );\n"
        + "    $restored = (string) get_post_field( 'post_content', "
        + post_id
        + " );\n"
        + "    if ( is_wp_error( $rolled_back ) || "
        + "! hash_equals( hash( 'sha256', $previous ), hash( 'sha256', $restored ) ) ) {\n"
        + "        throw new RuntimeException( 'Template update failed and rollback did not restore the backup: ' . $failure->getMessage() );\n"
        + "    }\n"
        + "    throw new RuntimeException( 'Template update failed; the previous template was restored: ' . $failure->getMessage() );\n"
        + "} finally {\n"
        + "    if ( $kses_was_on ) { kses_init_filters(); }\n"
        + "}\n"
    )


def apply(prefix: list[str], actions: list[dict[str, Any]], backup: Path) -> None:
    """Write the actions, recording the previous values first."""
    state = read_state(prefix)
    if plan(state) != actions:
        raise SystemExit("the site changed after planning; refusing stale writes")
    record: dict[str, Any] = {
        "actions": actions,
        "previous": {
            "thank_you_twin": {
                "post": state["twin"]["id"],
                "index": state["twin"].get("index", ""),
            },
            "blog_template": {
                "post": state["template"]["id"],
                "doubled": state["template"].get("doubled", 0),
                "content": state["template"].get("content", ""),
            },
        },
    }
    backup.write_text(
        json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    code = ""
    for action in actions:
        if action["kind"] == "template":
            code += template_write_code(action)
    for action in actions:
        if action["kind"] == "meta":
            code += (
                f"update_post_meta( {action['post']}, '{ROBOTS_INDEX_META}', 'yes' );\n"
            )
    php(prefix, code)


def verify(state: dict[str, Any]) -> list[str]:
    """The checks that must hold after the writes."""
    check_preconditions(state)
    twin = state["twin"]
    template = state["template"]
    failures = []
    if state["source"].get("index") != "yes":
        failures.append(f"post {SOURCE_ID} lost its own {ROBOTS_INDEX_META}=yes")
    if twin.get("index") != "yes":
        failures.append(
            f"post {twin.get('id')} {ROBOTS_INDEX_META} is "
            f"{twin.get('index')!r}, not 'yes'"
        )
    if template.get("doubled", 0) != 0:
        failures.append(
            f"post {template.get('id')} still carries "
            f"{template.get('doubled')} doubled URL prefix(es)"
        )
    if template.get("correct", 0) != 1:
        failures.append(
            f"post {template.get('id')} carries {template.get('correct')} "
            "correct URL prefixes, expected 1"
        )
    if template.get("scripts", 0) != 1:
        failures.append(
            f"post {template.get('id')} carries {template.get('scripts')} "
            "JSON-LD scripts, expected 1"
        )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "command", choices=("plan", "apply", "verify"), help="what to do"
    )
    parser.add_argument(
        "--wp",
        required=True,
        help="the WP-CLI command, quoted, e.g. "
        '"ssh host cd ~/domains/de-linker.com/public_html; /usr/local/bin/wp"',
    )
    parser.add_argument("--write", action="store_true", help="apply needs this")
    parser.add_argument(
        "--backup", type=Path, help="where apply records the previous values"
    )
    args = parser.parse_args()

    prefix = shlex.split(args.wp)
    state = read_state(prefix)
    if args.command == "plan":
        actions = plan(state)
        print(json.dumps(actions, indent=1))
        if not actions:
            print("nothing to do")
        return
    if args.command == "apply":
        actions = plan(state)
        if not actions:
            print("nothing to do")
            return
        if not args.write:
            raise SystemExit("apply needs --write")
        if args.backup is None:
            raise SystemExit("apply needs --backup <file>")
        apply(prefix, actions, args.backup)
        after = read_state(prefix)
        failures = verify(after)
        if failures:
            raise SystemExit("verify after apply failed:\n" + "\n".join(failures))
        print(f"applied {len(actions)} write(s); verified")
        return
    failures = verify(state)
    if failures:
        raise SystemExit("verify failed:\n" + "\n".join(failures))
    print("verified: twin meta mirrors the source; German blog URL has one prefix")


if __name__ == "__main__":
    main()
