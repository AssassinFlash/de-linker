#!/usr/bin/env python3
r"""No plugin writes an English address of this site into its own markup.

Polylang gives a page its language from the request's URL; a plugin that calls
`home_url( '/contact/' )` itself gets the English page on a German request
(the audit's H1/H5/M9: the product page's "Produkt anfragen", the breadcrumb's
home and the admin-triggered emails). Every plugin address goes through one
entry point instead — `PageUrls` in linker-commerce, or the language layer's
own root — and this gate keeps the next literal from being written.

The rule reads runtime PHP under plugins/: a call to home_url() whose first
argument begins with a path literal (`'/'` included). `home_url( $path )`,
`home_url()` (the host only) and the one entry point's own fallback are not
literals. Tests and vendor code are not customer surfaces.

Since #265 the gate also reads the German LiveCanvas exports (every `de/`
HTML file under a plugin's `content/`, installed by `present`): a literal
internal href there must be German (`/de/…`). Dynamic targets are free
(`{Field url}`, `[shortcode]`), and fragments, `mailto:`/`tel:` and absolute
off-site URLs are not site paths. The audit's M2 found the defect this keeps
out: `/de/category/system-design/` hard-coded `/product/`, a 404, in
`content/livecanvas/de/category_archive.html`.

`[linker_site_url]` is already the request language's root (`/de/` on the
German face). A following literal `de/` therefore doubles the prefix; the
German blog index made `/de/de/blog/` this way until 2026-10-29.

Usage:
    python3 tools/checks/internal-home-urls.py [--root .] [--rev origin/main]

Exit code: 0 = no literal, 1 = at least one (printed with its line).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# home_url( '... ) or home_url( "... ) where the string starts with a path.
LITERAL = re.compile(r"\bhome_url\s*\(\s*(['\"])/")
EXCLUDED_PARTS = {"vendor", "node_modules", "tests", "languages", ".git"}

# href="…" on a German export: literal internal targets must start with /de/.
HREF = re.compile(r"""href\s*=\s*["']([^"'{}]*)["']""")
OFF_SITE = re.compile(r"^(?:/de/|https?://|//|#|mailto:|tel:)", re.IGNORECASE)
DYNAMIC = re.compile(r"^[\[{]")
DOUBLED_SITE_URL = re.compile(r"\[linker_site_url\]de(?:/|\b)")


def is_runtime_php(path: Path) -> bool:
    """A PHP file of a plugin that ships to the site."""
    if path.suffix != ".php":
        return False
    parts = path.parts
    return "plugins" in parts and not EXCLUDED_PARTS.intersection(parts)


def is_german_export(path: Path) -> bool:
    """An HTML export of a German page or partial, installed by `present`."""
    if path.suffix != ".html":
        return False
    parts = path.parts
    return (
        "plugins" in parts
        and "content" in parts
        and "de" in parts
        and not EXCLUDED_PARTS.intersection(parts)
    )


def scan_text(name: str, text: str) -> list[tuple[str, int, str]]:
    """The literal calls in one file, as (path, line, line text)."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if LITERAL.search(line):
            found.append((name, number, line.strip()))
    return found


def scan_german_export(name: str, text: str) -> list[tuple[str, int, str]]:
    """German-export URL defects, as (path, line, offending text)."""
    found = []
    for match in HREF.finditer(text):
        target = match.group(1).strip()
        if target and not OFF_SITE.match(target) and not DYNAMIC.match(target):
            number = text.count("\n", 0, match.start()) + 1
            found.append((name, number, f'href="{target}"'))
    for match in DOUBLED_SITE_URL.finditer(text):
        number = text.count("\n", 0, match.start()) + 1
        found.append((name, number, match.group(0)))
    return found


def scan_root(root: Path) -> list[tuple[str, int, str]]:
    """Every literal under the working tree's plugins/."""
    found: list[tuple[str, int, str]] = []
    for path in sorted((root / "plugins").rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file():
            continue
        if is_runtime_php(relative):
            found.extend(scan_text(str(relative), path.read_text(encoding="utf-8")))
        elif is_german_export(relative):
            found.extend(
                scan_german_export(str(relative), path.read_text(encoding="utf-8"))
            )
    return found


def scan_revision(root: Path, revision: str) -> list[tuple[str, int, str]]:
    """Every literal in a git revision's plugins/, without checking it out."""
    listed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-tree",
            "-r",
            "--name-only",
            revision,
            "--",
            "plugins",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    found = []
    for name in listed.stdout.splitlines():
        path = Path(name)
        if not (is_runtime_php(path) or is_german_export(path)):
            continue
        text = subprocess.run(
            ["git", "-C", str(root), "show", f"{revision}:{name}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if is_runtime_php(path):
            found.extend(scan_text(name, text))
        else:
            found.extend(scan_german_export(name, text))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--rev",
        help="Read a git revision instead of the working tree, e.g. origin/main.",
    )
    arguments = parser.parse_args()
    root = Path(arguments.root).resolve()
    found = scan_revision(root, arguments.rev) if arguments.rev else scan_root(root)
    for name, line, text in found:
        print(f"internal address does not follow the language: {name}:{line}: {text}")
    if found:
        print(
            f"internal-home-urls: {len(found)} literal(s) — build the address "
            "through PageUrls (or the language layer's root), and keep German "
            "export hrefs German (/de/…)"
        )
        return 1
    print("internal-home-urls: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
