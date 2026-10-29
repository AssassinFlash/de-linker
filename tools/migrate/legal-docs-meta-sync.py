#!/usr/bin/env python3
"""Sync the stale cross-document version lines in the saved legal pages.

The "Legal documents" navigation of each legal page is built by the page's own
tv-legal-js block, whose DOCS array repeats every document's meta line (the
line under that document's H1). On 2026-10-27 the Terms of Sale (v1.2) and the
Refund and Returns Policy (v1.1) were re-dated to 27 October 2026 on their own
four pages, but the copies embedded in Imprint (1672/6829) and Privacy Policy
(1673/6827) still say 30 July 2026, so their navigation shows wrong versions.

This script replaces exactly those two DOCS lines, per page, reusing the
hardened WP-CLI content transaction of repair-legal-script.php. A page is

  apply  it holds the stale lines: --write will write the re-dated lines
  done   it already holds the re-dated lines
  drift  it holds something else: nothing is written until a person has
         looked (the plan no longer describes the page)

Without --write it stops after the report. With --write it requires
--backup-dir, saves what the pages hold now, writes, reads everything back
and fails unless every page reads back the planned bytes. Writing to
https://de-linker.com also needs --full-backup (a completed full site backup
directory), exactly as repair-legal-script.py demands.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location("repair", HERE / "repair-legal-script.py")
assert _spec and _spec.loader
repair = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(repair)

# The live pages carry each DOCS line byte for byte; these four replacements
# are the exact rendered strings read on de-linker.com on 2026-10-29.
REPLACEMENTS = (
    (
        "en: ['Terms of Sale', 'Version 1.2 · 30 July 2026'], "
        "de: ['Verkaufsbedingungen', 'Version 1.2 · Stand: 30. Juli 2026']",
        "en: ['Terms of Sale', 'Version 1.2 · 27 October 2026'], "
        "de: ['Verkaufsbedingungen', 'Version 1.2 · Stand: 27. Oktober 2026']",
    ),
    (
        "en: ['Refund & Returns', 'Version 1.1 · 30 July 2026'], "
        "de: ['Rückgabe & Erstattung', 'Version 1.1 · Stand: 30. Juli 2026']",
        "en: ['Refund & Returns', 'Version 1.1 · 27 October 2026'], "
        "de: ['Rückgabe & Erstattung', 'Version 1.1 · Stand: 27. Oktober 2026']",
    ),
)


def plan_page(content: str) -> str:
    """Re-date both DOCS lines, or return the content unchanged when done.

    Refuses anything but exactly the stale pair or exactly the re-dated pair,
    so a page that changed since 2026-10-29 is never silently overwritten.
    """
    counts = [(content.count(old), content.count(new)) for old, new in REPLACEMENTS]
    if counts == [(0, 1)] * len(REPLACEMENTS):
        return content
    if counts != [(1, 0)] * len(REPLACEMENTS):
        raise ValueError(
            f"DOCS version lines drifted: stale/fresh counts {counts}, "
            "expected [(1, 0)] or [(0, 1)] per line"
        )
    for old, new in REPLACEMENTS:
        content = content.replace(old, new, 1)
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument(
        "--page",
        action="append",
        required=True,
        type=int,
        help="page ID to sync (repeat for each of the four stale pages)",
    )
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument(
        "--full-backup", type=Path, help="completed full site backup directory"
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    snapshot = repair.invoke(args.wp, {"operation": "read", "ids": args.page})
    changes = []
    for page in args.page:
        current = snapshot["rows"][str(page)]["content"]
        if len(re.findall(r'id="tv-legal-js"', current)) != 1:
            raise ValueError(f"Page {page} does not hold exactly one tv-legal-js block")
        fixed = plan_page(current)
        changes.append({"id": page, "before": current, "after": fixed})

    if args.write:
        if args.backup_dir is None:
            parser.error("--write requires --backup-dir")
        if urlsplit(snapshot["home"]).hostname in {
            "de-linker.com",
            "www.de-linker.com",
        }:
            if (
                args.full_backup is None
                or not (args.full_backup / "manifest.json").is_file()
            ):
                parser.error("Production requires a completed --full-backup")
            repair.verify_full_backup(args.full_backup)
        args.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup = args.backup_dir / f"legal-docs-meta-before-{stamp}.json"
        with backup.open("x") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        backup.chmod(0o600)
        print(f"Backup: {backup}")
        repair.invoke(args.wp, {"operation": "save", "changes": changes})
        readback = repair.invoke(args.wp, {"operation": "read", "ids": args.page})
        if any(
            readback["rows"][str(c["id"])]["content"] != c["after"] for c in changes
        ):
            raise RuntimeError(f"Independent readback failed; backup: {backup}")

    print(
        json.dumps(
            {
                "write": args.write,
                "pages": [
                    {
                        "id": c["id"],
                        "changed": c["before"] != c["after"],
                        "before_sha256": repair.digest(c["before"]),
                        "after_sha256": repair.digest(c["after"]),
                    }
                    for c in changes
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
