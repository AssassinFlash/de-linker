#!/usr/bin/env python3
"""No plugin writes an English address of this site into its own markup.

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


def is_runtime_php(path: Path) -> bool:
    """A PHP file of a plugin that ships to the site."""
    if path.suffix != ".php":
        return False
    parts = path.parts
    return "plugins" in parts and not EXCLUDED_PARTS.intersection(parts)


def scan_text(name: str, text: str) -> list[tuple[str, int, str]]:
    """The literal calls in one file, as (path, line, line text)."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if LITERAL.search(line):
            found.append((name, number, line.strip()))
    return found


def scan_root(root: Path) -> list[tuple[str, int, str]]:
    """Every literal under the working tree's plugins/."""
    found = []
    for path in sorted((root / "plugins").rglob("*.php")):
        relative = path.relative_to(root)
        if not is_runtime_php(relative):
            continue
        found.extend(scan_text(str(relative), path.read_text(encoding="utf-8")))
    return found


def scan_revision(root: Path, revision: str) -> list[tuple[str, int, str]]:
    """Every literal in a git revision's plugins/, without checking it out."""
    listed = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", revision, "--", "plugins"],
        check=True,
        capture_output=True,
        text=True,
    )
    found = []
    for name in listed.stdout.splitlines():
        if not is_runtime_php(Path(name)):
            continue
        text = subprocess.run(
            ["git", "-C", str(root), "show", f"{revision}:{name}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        found.extend(scan_text(name, text))
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
        print(f"internal home_url literal: {name}:{line}: {text}")
    if found:
        print(
            f"internal-home-urls: {len(found)} literal(s) — build the address "
            "through PageUrls (or the language layer's root)"
        )
        return 1
    print("internal-home-urls: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
