#!/usr/bin/env python3
"""Catalog validity gate: every catalog compiles.

`msgfmt --check` on every plugins/*/languages/*.po and *.pot. The coverage
gate reads the German catalogs only, so a .pot that lost an entry's msgstr
section or that repeats a msgid passes it and reaches the trunk silently —
the template catalog is generated, not parsed, on the way in. msgfmt is the
parser; this is where it runs.

Exit 0 when every catalog compiles. Exit 1 when one does not, printing
msgfmt's own diagnosis, or when msgfmt cannot be run.

Usage:
    python3 tools/checks/i18n-validity.py
"""

from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def catalogs() -> list[Path]:
    """The catalogs the plugins ship, template last so a .po fails first."""
    pot = sorted(ROOT.glob("plugins/*/languages/*.pot"))
    po = sorted(ROOT.glob("plugins/*/languages/*.po"))
    return [path.relative_to(ROOT) for path in po + pot]


def main() -> int:
    failed = False
    for catalog in catalogs():
        # -o: without it msgfmt writes its default messages.mo beside the
        # catalog it just checked.
        result = subprocess.run(
            ["msgfmt", "--check", "-o", os.devnull, str(ROOT / catalog)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"{catalog}: does not compile", file=sys.stderr)
            print(result.stderr.strip(), file=sys.stderr)
            failed = True

    if failed:
        print("i18n-validity: FAIL", file=sys.stderr)
        return 1
    print(f"i18n-validity: clean ({len(catalogs())} catalogs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
