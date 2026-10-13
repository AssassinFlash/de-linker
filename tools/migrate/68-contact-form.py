#!/usr/bin/env python3
"""#68 migration: the /contact/ pages mount the contact form.

Runs against a WordPress through WP-CLI (the pattern of 9-i18n.py and
12-site-chrome.py):

    python3 tools/migrate/68-contact-form.py --wp ~/de-linker-local/t68/wp.sh plan
    python3 tools/migrate/68-contact-form.py --wp ~/de-linker-local/t68/wp.sh --user <admin> apply --write
    python3 tools/migrate/68-contact-form.py --wp ~/de-linker-local/t68/wp.sh verify

What changes (ticket #68, GAP-8; docs/specs/11-commerce.md, the contact form):

1. Inside the contact page's form region the previous runtime left a mount
   and a fallback: `<div data-linker-contact-mount><div class="cp-contact-fallback"
   data-contact-fallback>…</div></div>`. The fallback is replaced by the
   shortcode `[linker_contact_form]`, so the minimal form renders
   server-side (plugins/linker-commerce, Contact) — no JavaScript is needed
   to see or send it.
2. The `<noscript>` "if the form cannot load" line next to the mount goes: it
   describes the JavaScript runtime that no longer exists, and the form works
   without JavaScript.
3. The German twin gets the same edit; its fallback text is German and the
   replacement is identical, so both languages carry the same mount.
4. The page's own script keeps driving the hero and the story panels, but its
   header comment credits the previous runtime by name; the name goes with
   the runtime (the mount above it is this repository's form now). A page
   that names the previous tree anywhere else is refused rather than guessed
   at.

Nothing else in the page changes: the hero, the intro and the story stay.

The migration is idempotent: the replacement is applied once per page, a
second run reports nothing to do, and a page whose region matches neither the
old nor the new shape is refused instead of guessed at.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import urllib.request
from typing import Any

# WP-CLI's PHP diagnostics, which must not land in a post's content.
PHP_DIAGNOSTIC = re.compile(
    r"^(PHP (Warning|Notice|Deprecated|Fatal error)|Warning:|Notice:|Deprecated:|Fatal error):"
)

# The mount div of the form region, with the fallback inside it.
MOUNT = re.compile(
    r"(<div data-linker-contact-mount[^>]*>)\s*"
    r'<div class="cp-contact-fallback"[^>]*>.*?</div>\s*'
    r"(</div>)",
    re.S,
)

# The noscript fallback line of the same region.
NOSCRIPT = re.compile(
    r"\s*<noscript><p class=\"cp-contact-fallback\">.*?</noscript>", re.S
)

# The shortcode the form is mounted with.
SHORTCODE = "[linker_contact_form]"

# The page script's header comment credits the previous runtime by name.
PREVIOUS_RUNTIME = re.compile(r"\s*\(terravolt-b2b-core contact-request\.js\)")
# What must not survive anywhere in the page.
PREVIOUS_BRAND = re.compile(r"terravolt", re.IGNORECASE)

RESOLVE_PHP = """
$en = get_page_by_path('contact');
if (!$en) { echo 'null'; return; }
$out = array('en' => (int) $en->ID, 'de' => 0, 'en_path' => $en->post_name);
if (function_exists('pll_get_post')) {
    $de = pll_get_post((int) $en->ID, 'de');
    if ($de) { $out['de'] = (int) $de; }
}
echo json_encode($out);
"""


class WP:
    """WP-CLI, as a command prefix (the 9-i18n.py wrapper)."""

    def __init__(self, command: str, user: str | None) -> None:
        self.prefix = shlex.split(command)
        self.user = user

    def run(self, *args: str, stdin: str | None = None, as_user: bool = False) -> str:
        command = [*self.prefix, *args]
        if as_user and self.user:
            command.append(f"--user={self.user}")
        result = subprocess.run(
            command, input=stdin, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            raise SystemExit(
                f"wp {' '.join(args[:3])} failed:\n{result.stderr.strip()}"
            )
        lines = result.stdout.splitlines()
        return "\n".join(line for line in lines if not PHP_DIAGNOSTIC.match(line))

    def json(self, *args: str, stdin: str | None = None, as_user: bool = False) -> Any:
        out = self.run(*args, stdin=stdin, as_user=as_user)
        start = min((i for i in (out.find("["), out.find("{")) if i >= 0), default=-1)
        return json.loads(out[start:]) if start >= 0 else None

    def eval_php(self, code: str) -> Any:
        return self.json("eval", code)


def resolve(wp: WP) -> dict[str, int]:
    pages = wp.eval_php(RESOLVE_PHP)
    if not isinstance(pages, dict) or not pages.get("en"):
        raise SystemExit("the English contact page (slug 'contact') was not found")
    if not pages.get("de"):
        raise SystemExit(
            "the German twin of the contact page is missing (is Polylang set up?)"
        )
    return {"en": int(pages["en"]), "de": int(pages["de"])}


def planned(content: str) -> tuple[str, list[str]]:
    """The new content and the changes it makes, or the reason it is refused."""
    changes: list[str] = []
    new = content
    if SHORTCODE not in new:
        if not MOUNT.search(new):
            raise SystemExit(
                "the contact form region matches neither the old mount with its "
                "fallback nor the new shortcode; nothing is written"
            )
        new = MOUNT.sub(lambda m: f"{m.group(1)}{SHORTCODE}{m.group(2)}", new, count=1)
        changes.append("mount: fallback -> " + SHORTCODE)
        if NOSCRIPT.search(new):
            new = NOSCRIPT.sub("", new, count=1)
            changes.append("noscript fallback removed")
    if PREVIOUS_RUNTIME.search(new):
        new = PREVIOUS_RUNTIME.sub("", new, count=1)
        changes.append("script comment: the previous runtime's name removed")
    if PREVIOUS_BRAND.search(new):
        raise SystemExit(
            "the page still names the previous tree somewhere this step does "
            "not know; nothing is written"
        )
    return new, changes


def read_post(wp: WP, post_id: int) -> dict[str, str]:
    content = wp.run("post", "get", str(post_id), "--field=post_content")
    if not content.strip():
        raise SystemExit(f"post {post_id}: content not readable")
    return {"post_content": content}


def do_plan(wp: WP) -> int:
    pages = resolve(wp)
    for lang, post_id in pages.items():
        content = read_post(wp, post_id)["post_content"]
        _, changes = planned(content)
        state = "; ".join(changes) if changes else "nothing to do"
        print(f"{lang} #{post_id}: {state}", flush=True)
    return 0


def do_apply(wp: WP, write: bool) -> int:
    pages = resolve(wp)
    for lang, post_id in pages.items():
        content = read_post(wp, post_id)["post_content"]
        new, changes = planned(content)
        if not changes:
            print(f"{lang} #{post_id}: nothing to do", flush=True)
            continue
        print(f"{lang} #{post_id}: {', '.join(changes)}", flush=True)
        if not write:
            continue
        wp.run("post", "update", str(post_id), "-", stdin=new, as_user=True)
    if not write:
        print("\ndry run: nothing written (add --write)", flush=True)
    return 0


def do_verify(wp: WP, base: str) -> int:
    pages = resolve(wp)
    ok = True
    for lang, post_id in pages.items():
        content = read_post(wp, post_id)["post_content"]
        if SHORTCODE not in content:
            print(f"{lang} #{post_id}: the shortcode is missing", flush=True)
            ok = False
        if PREVIOUS_BRAND.search(content):
            print(
                f"{lang} #{post_id}: the previous tree is still named",
                flush=True,
            )
            ok = False
    for path in ("/contact/", "/de/kontakt/"):
        try:
            with urllib.request.urlopen(
                base.rstrip("/") + path, timeout=60
            ) as response:
                html = response.read().decode("utf-8", "replace")
        except Exception as error:  # noqa: BLE001 - the report carries the reason.
            print(f"{path}: {error}", flush=True)
            ok = False
            continue
        form = 'class="linker-contact-form' in html
        fallback = "cp-contact-fallback" in html
        print(f"{path}: form={form} old-fallback={fallback}", flush=True)
        ok = ok and form and not fallback
    print("ok" if ok else "not ok", flush=True)
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wp", required=True, help="WP-CLI command, e.g. ~/de-linker-local/t68/wp.sh"
    )
    parser.add_argument(
        "--user", default=None, help="administrator login for the writes"
    )
    parser.add_argument(
        "--base",
        default="http://127.0.0.1:8975",
        help="instance address for verify (default: the reference instance, t110)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--write", action="store_true")
    subparsers.add_parser("verify")
    args = parser.parse_args()

    wp = WP(args.wp, args.user)
    if args.command == "plan":
        return do_plan(wp)
    if args.command == "apply":
        return do_apply(wp, bool(args.write))
    return do_verify(wp, args.base)


if __name__ == "__main__":
    sys.exit(main())
