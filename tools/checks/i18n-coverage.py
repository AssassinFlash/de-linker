#!/usr/bin/env python3
"""German formal catalog coverage gate.

For every plugins/*/languages/*-de_DE_formal.po, untranslated entries
(msgattrib --untranslated --no-obsolete) minus the exemption list must be
zero. An exemption is a developer-facing string: a REST/Abilities JSON Schema
description, an ERP error returned as JSON, or a post type that no screen
shows. Customer and staff strings are not exempt.

Prints one line per catalog: path, untranslated, exempt, gap.
Exit 0 when every gap is 0. Exit 1 when a gap remains, an exemption is stale,
or msgattrib cannot be run.

Usage:
    python3 tools/checks/i18n-coverage.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXEMPT_PATH = Path(__file__).resolve().parent / "i18n-exempt.json"


def catalogs() -> list[Path]:
    found = sorted(ROOT.glob("plugins/*/languages/*-de_DE_formal.po"))
    return [path.relative_to(ROOT) for path in found]


def untranslated(catalog: Path) -> list[str]:
    """msgids msgattrib reports as untranslated.

    The catalog header is the empty msgid whose msgstr holds the metadata.
    msgattrib still prints that header, so it is dropped here. A real entry
    always has a non-empty msgid.
    """
    result = subprocess.run(
        ["msgattrib", "--untranslated", "--no-obsolete", str(ROOT / catalog)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"i18n-coverage: msgattrib failed on {catalog}", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(1)
    entries: list[str] = []
    msgid: list[str] | None = None
    msgstr: list[str] | None = None
    for line in result.stdout.splitlines() + [""]:
        if line.startswith("msgid "):
            flush(entries, msgid, msgstr)
            msgid = [decode(line[len("msgid ") :])]
            msgstr = None
        elif line.startswith("msgstr"):
            msgstr = []
        elif line.startswith('"') and msgstr is not None:
            msgstr.append(decode(line))
        elif line.startswith('"') and msgid is not None:
            msgid.append(decode(line))
        elif line == "":
            flush(entries, msgid, msgstr)
            msgid = None
            msgstr = None
    return entries


def flush(entries: list[str], msgid: list[str] | None, msgstr: list[str] | None) -> None:
    if not msgid:
        return
    text = "".join(msgid)
    # Header: empty msgid, metadata in msgstr. Not a translatable entry.
    if text == "":
        return
    translated = "".join(msgstr or [])
    if translated == "":
        entries.append(text)


def decode(quoted: str) -> str:
    return json.loads(quoted)


def load_exemptions() -> dict[str, list[dict[str, str]]]:
    data = json.loads(EXEMPT_PATH.read_text(encoding="utf-8"))
    catalogs_in = data.get("catalogs")
    if not isinstance(catalogs_in, dict):
        print("i18n-coverage: exemptions file has no catalogs object", file=sys.stderr)
        raise SystemExit(1)
    return catalogs_in


def main() -> int:
    exemptions = load_exemptions()
    found = catalogs()
    if not found:
        print("i18n-coverage: no de_DE_formal catalogs", file=sys.stderr)
        return 1

    failed = False
    known = {str(path) for path in found}
    for name in sorted(exemptions):
        if name not in known:
            print(f"i18n-coverage: exemption names a missing catalog: {name}", file=sys.stderr)
            failed = True

    for catalog in found:
        missing = untranslated(catalog)
        rows = exemptions.get(str(catalog), [])
        allowed = {row["msgid"] for row in rows}
        stale = sorted(allowed - set(missing))
        gap = [entry for entry in missing if entry not in allowed]
        print(
            f"{catalog}: untranslated={len(missing)} exempt={len(missing) - len(gap)} "
            f"gap={len(gap)}"
        )
        for entry in gap:
            print(f"  gap: {entry}")
            failed = True
        for entry in stale:
            print(f"  stale exemption (now translated or gone): {entry}")
            failed = True

    if failed:
        print("i18n-coverage: FAIL", file=sys.stderr)
        return 1
    print("i18n-coverage: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
