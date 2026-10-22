#!/usr/bin/env python3
"""Keep the Installer entry at the top, retaining user-initiated tab scrolling.

Only the two audited Installer records are writable. Reuse the transactional
WordPress content writer: backup first, compare the locked source, wp_slash(),
and read both saved pages back byte for byte. No prose or layout changes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

spec = importlib.util.spec_from_file_location(
    "content_repair", Path(__file__).with_name("repair-legal-script.py")
)
assert spec and spec.loader
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)

# Production IDs and markup were read from both published language records.
PAGES = (826, 6869)
SCRIPT = re.compile(r"<script\b[^>]*>.*?</script>", re.S | re.I)
REPLACEMENTS = (
    ("function show(index) {", "function show(index, revealTab = false) {"),
    (
        "if (tabs[index]) tabs[index].scrollIntoView({block:'nearest',inline:'nearest'});",
        "if (revealTab && tabs[index]) tabs[index].scrollIntoView({block:'nearest',inline:'nearest'});",
    ),
    (
        "tab.addEventListener('click', () => show(i));",
        "tab.addEventListener('click', () => show(i, true));",
    ),
    ("        show(next);", "        show(next, true);"),
)


def repair(content: str) -> str:
    """Accept one known tab controller, in either intact source state."""
    if content.count('id="installer-journal"') != 1:
        raise ValueError("Expected one Installer page root")
    blocks = [m for m in SCRIPT.finditer(content) if "function tabSet(" in m[0]]
    if len(blocks) != 1:
        raise ValueError("Expected one Installer tab controller")
    block = blocks[0]
    source = block[0]
    if source.count("function tabSet(") != 1 or source.count("    show(0);") != 1:
        raise ValueError("Installer tab initialization changed; refusing to patch")
    if all(source.count(after) == 1 for _, after in REPLACEMENTS):
        # The guarded scroll statement contains the old scroll as a suffix;
        # require an exact inverse/forward round trip rather than substring
        # absence for the already-fixed state.
        previous = source
        for before, after in REPLACEMENTS:
            previous = previous.replace(after, before, 1)
        if not all(previous.count(before) == 1 for before, _ in REPLACEMENTS):
            raise ValueError("Ambiguous repaired Installer controller")
        return content
    if not all(source.count(before) == 1 for before, _ in REPLACEMENTS) or any(
        after in source for _, after in REPLACEMENTS
    ):
        raise ValueError("Installer tab controller differs; refusing a partial patch")
    fixed = source
    for before, after in REPLACEMENTS:
        fixed = fixed.replace(before, after, 1)
    return content[: block.start()] + fixed + content[block.end() :]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--full-backup", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    snapshot = writer.invoke(args.wp, {"operation": "read", "ids": list(PAGES)})
    changes = []
    for page in PAGES:
        row = snapshot["rows"][str(page)]
        if row["type"] != "page":
            raise ValueError("Not an audited Installer page")
        changes.append(
            {"id": page, "before": row["content"], "after": repair(row["content"])}
        )
    if args.write:
        if args.backup_dir is None:
            parser.error("--write requires --backup-dir")
        if urlsplit(snapshot["home"]).hostname in {
            "de-linker.com",
            "www.de-linker.com",
        }:
            if args.full_backup is None:
                parser.error("Production requires a completed --full-backup")
            writer.verify_full_backup(args.full_backup)
        args.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = args.backup_dir / (
            "installer-scroll-before-"
            + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            + ".json"
        )
        with backup.open("x") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        backup.chmod(0o600)
        print(f"Backup: {backup}")
        writer.invoke(args.wp, {"operation": "save", "changes": changes})
        readback = writer.invoke(args.wp, {"operation": "read", "ids": list(PAGES)})
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
                        "before_sha256": writer.digest(c["before"]),
                        "after_sha256": writer.digest(c["after"]),
                        "backslashes_before": c["before"].count("\\"),
                        "backslashes_after": c["after"].count("\\"),
                    }
                    for c in changes
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
