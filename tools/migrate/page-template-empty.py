#!/usr/bin/env python3
"""Restore the theme's empty page template on pages that lost it.

The picostrap5 page template prints a page title unconditionally
(themes/picostrap5/page.php, `<h1 class="display-4">`). LiveCanvas pages whose
own markup already carries the page's heading suppress that title with the
theme's own page template, `page-templates/empty.php` (Template Name: Empty
Page Template): header, the page content, footer, nothing else. That is a page
meta value (`_wp_page_template`), the same mechanism the live site uses — not
a style and not a snippet.

A local instance built from a snapshot can lose that meta while keeping the
page content, so the theme title renders above the page's own heading. This
script puts the meta back, and only that meta.

The authority is the live site, read through WP-CLI (`--source-wp`, read
only). A page is restored when all of these hold:

- it is published, of type page, and its language is the site's default
  (English; a site without Polylang has one language and every page qualifies);
- the live page of the same slug carries `page-templates/empty.php`;
- the local page's template meta is empty.

A page the live site does not render through that template (the blog index,
the shop, the cart, a page assigned a LiveCanvas dynamic template through
`lc_use_template_of_slug`) is never touched, and neither is a page that
already carries any template. The German twin gets the same value, because
Polylang's page-template sync is off on this site and the twin is its own
page; a twin that already carries a template is left as it is.

Nothing else is written: no post content, no other meta, no LiveCanvas
partial. Idempotent — a second run finds nothing to do.

    python3 tools/migrate/page-template-empty.py \
        --wp ~/de-linker-local/t110/wp.sh \
        --source-wp "ssh hostinger-de-linker /usr/local/bin/wp --path=..." plan
    python3 tools/migrate/page-template-empty.py \
        --wp ~/de-linker-local/t110/wp.sh \
        --source-wp "ssh hostinger-de-linker /usr/local/bin/wp --path=..." apply --write
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# The theme template that renders a page without the theme's page title.
EMPTY_TEMPLATE = "page-templates/empty.php"

# PHP deprecations the WP-CLI phar prints to stdout ahead of the value.
PHP_DIAGNOSTIC_PREFIXES = (
    "Deprecated:",
    "PHP Deprecated:",
    "Warning:",
    "PHP Warning:",
    "Notice:",
    "PHP Notice:",
)


def clean(output: str) -> str:
    """Drop the phar's own diagnostic lines; every reader treats stdout as data."""
    kept = [
        line
        for line in output.splitlines()
        if not line.startswith(PHP_DIAGNOSTIC_PREFIXES)
    ]
    return "\n".join(kept)


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
    """The ssh part of a remote WP-CLI prefix, or nothing for a local one.

    `ssh host /usr/local/bin/wp --path=…` splits after the host; the wp binary
    is the first argument that is `wp`, so `--path` stays with the wp command.
    """
    if not prefix or prefix[0] != "ssh":
        return []
    for index, part in enumerate(prefix):
        if part == "wp" or part.endswith("/wp"):
            return prefix[:index]
    raise SystemExit(f"no wp binary in the remote command: {' '.join(prefix)}")


def php(prefix: list[str], code: str) -> str:
    """Run PHP through `wp eval-file`, so no shell ever parses it.

    The command prefix may be `ssh host -- wp`, whose remote shell would
    expand `$` and reject parentheses in an `eval` argument. A file has
    neither problem. A remote prefix receives the file through its ssh
    transport (`cat > file`); a local prefix gets a local temp file.
    """
    with tempfile.NamedTemporaryFile(
        "w", suffix=".php", prefix="page-template-", delete=False
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


def pages(prefix: list[str]) -> list[dict[str, Any]]:
    """Published pages with the template meta and the language layer's answers.

    Read in one process: the language of each page, its translation in the
    other language, and that translation's template. A site without Polylang
    reports every language as empty, which the plan treats as the only language.
    """
    code = (
        "$out=array();$has=function_exists('pll_get_post_language')&&function_exists('pll_get_post');"
        "$posts=get_posts(array('post_type'=>'page','post_status'=>'publish','posts_per_page'=>-1,"
        "'lang'=>'','orderby'=>'ID','order'=>'ASC'));"
        "foreach($posts as $post){"
        "$language=$has?pll_get_post_language($post->ID):'';"
        "$twin_id=0;"
        "if($has&&is_string($language)&&$language!==''){"
        "$twin_id=(int)pll_get_post($post->ID,$language==='en'?'de':'en');}"
        "$twin=$twin_id?get_post($twin_id):null;"
        "$out[]=array('id'=>(int)$post->ID,'slug'=>(string)$post->post_name,"
        "'language'=>is_string($language)?$language:'',"
        "'template'=>(string)get_post_meta($post->ID,'_wp_page_template',true),"
        "'twin_id'=>$twin_id,"
        "'twin_slug'=>$twin instanceof WP_Post?(string)$twin->post_name:'',"
        "'twin_template'=>$twin_id?(string)get_post_meta($twin_id,'_wp_page_template',true):'');}"
        "echo wp_json_encode($out);"
    )
    raw = php(prefix, code)
    start = raw.find("[")
    if start < 0:
        raise SystemExit(f"no page list in wp eval output:\n{raw[:400]}")
    parsed = json.loads(raw[start:])
    if not isinstance(parsed, list):
        raise SystemExit("wp eval did not return a page list")
    return parsed


def plan(
    local: list[dict[str, Any]], source: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The writes: local pages whose live twin renders through the empty template.

    Keyed by slug, because the live site and a local instance do not share post
    ids. Only an empty local template is filled; an existing one — the blog
    index's dynamic template, a Woo page's own assignment — is evidence of a
    choice and is reported, not overwritten.
    """
    live_by_slug = {str(page["slug"]): str(page["template"]) for page in source}
    writes: list[dict[str, Any]] = []
    seen: set[int] = set()
    for page in local:
        if page["language"] not in ("", "en"):
            continue
        slug = str(page["slug"])
        if live_by_slug.get(slug) != EMPTY_TEMPLATE:
            continue
        targets = [(int(page["id"]), slug, str(page["template"]))]
        if int(page["twin_id"]):
            targets.append(
                (
                    int(page["twin_id"]),
                    str(page["twin_slug"]),
                    str(page["twin_template"]),
                )
            )
        for post_id, post_slug, template in targets:
            if post_id in seen:
                continue
            seen.add(post_id)
            if template == EMPTY_TEMPLATE:
                continue
            if template != "":
                writes.append(
                    {
                        "id": post_id,
                        "slug": post_slug,
                        "action": "skip-existing",
                        "current": template,
                    }
                )
                continue
            writes.append(
                {"id": post_id, "slug": post_slug, "action": "set", "current": ""}
            )
    return writes


def apply_writes(prefix: list[str], writes: list[dict[str, Any]]) -> None:
    """Set the template meta. One guarded statement per page, checked by a readback."""
    targets = [item for item in writes if item["action"] == "set"]
    if not targets:
        print("nothing to write")
        return
    statements = [
        f"update_post_meta({int(item['id'])},'_wp_page_template',{json.dumps(EMPTY_TEMPLATE)});"
        for item in targets
    ]
    php(prefix, "".join(statements))
    for item in targets:
        got = run(
            prefix,
            "post",
            "meta",
            "get",
            str(int(item["id"])),
            "_wp_page_template",
        ).strip()
        if got != EMPTY_TEMPLATE:
            raise SystemExit(
                f"readback mismatch on {item['id']} {item['slug']}: {got!r}"
            )
        print(f"set {item['id']} {item['slug']} -> {EMPTY_TEMPLATE}")


def report(writes: list[dict[str, Any]]) -> None:
    """Print the plan. A skipped page is a stop, not a quiet success."""
    sets = [item for item in writes if item["action"] == "set"]
    skipped = [item for item in writes if item["action"] == "skip-existing"]
    if not sets and not skipped:
        print("nothing to do: every page already matches the live site")
        return
    for item in sets:
        print(f"set {item['id']} {item['slug']}: (empty) -> {EMPTY_TEMPLATE}")
    for item in skipped:
        print(
            f"SKIP {item['id']} {item['slug']}: carries {item['current']!r}, "
            f"not {EMPTY_TEMPLATE!r} — not overwritten"
        )
    print(f"{len(sets)} to set, {len(skipped)} skipped")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "--wp", required=True, help="WP-CLI command of the local instance"
    )
    parser.add_argument(
        "--source-wp",
        required=True,
        help="WP-CLI command of the live site, read only",
    )
    parser.add_argument("command", choices=("plan", "apply"))
    parser.add_argument("--write", action="store_true", help="required by apply")
    args = parser.parse_args(argv)

    local_prefix = shlex.split(args.wp)
    source_prefix = shlex.split(args.source_wp)
    local = pages(local_prefix)
    source = pages(source_prefix)
    writes = plan(local, source)
    report(writes)

    if args.command == "plan":
        return 0
    if not args.write:
        raise SystemExit("apply refuses to write without --write")
    apply_writes(local_prefix, writes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
