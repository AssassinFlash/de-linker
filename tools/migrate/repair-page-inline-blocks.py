#!/usr/bin/env python3
"""Preserve service and utility-page copy through WordPress formatting.

The 2026-10-21 browser audit found formatting-generated breaks in the status
bar and four invalid scripts. Removing blank lines inside existing inline
blocks prevents paragraph insertion. Keeping the small status bar on one
source line prevents forced breaks between its inline elements.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import UTC, datetime
from pathlib import Path

path = Path(__file__).with_name("repair-legal-script.py")
spec = importlib.util.spec_from_file_location("content_repair", path)
assert spec and spec.loader
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)


def repair(content: str) -> str:
    if 'id="tv-utility-page-v1"' in content:
        # These exact side-effect-free comparisons are the only literal '<'
        # tokens in the audited utility scripts. wptexturize treats their span
        # as markup and encodes subsequent && operators. Reverse the operands
        # without introducing escapes that another unslashed save could lose.
        def comparisons(match: re.Match[str]) -> str:
            script = match[0]
            for before, after in (
                ("i<3", "3>i"),
                ("position<0", "0>position"),
                ("dx<0", "0>dx"),
                ("delta<0", "0>delta"),
                ("track.scrollLeft<width", "width>track.scrollLeft"),
            ):
                script = script.replace(before, after)
            if "<" in script.split(">", 1)[1].rsplit("</script>", 1)[0]:
                raise ValueError("Unexpected less-than token in utility script")
            return script

        content = re.sub(r"<script\b[^>]*>.*?</script>", comparisons, content, flags=re.S)
    content = re.sub(
        r"(<(script|style)\b[^>]*>)(.*?)(</\2>)",
        lambda match: match[1] + re.sub(r"\n[ \t]*(?=\n)", "", match[3]) + match[4],
        content,
        flags=re.S | re.I,
    )
    return re.sub(
        r'<header class="lk-topbar">.*?</header>',
        lambda match: re.sub(r"\s*\n\s*", " ", match[0]),
        content,
        flags=re.S,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument("--page", type=int, action="append", required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--full-backup", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    snapshot = writer.invoke(args.wp, {"operation": "read", "ids": args.page})
    changes = []
    for key, row in snapshot["rows"].items():
        if row["type"] != "page" or not any(
            marker in row["content"]
            for marker in ('id="service-redesign"', 'id="tv-utility-page-v1"')
        ):
            raise ValueError("Not an audited service or utility page; refusing to patch")
        changes.append(
            {"id": int(key), "before": row["content"], "after": repair(row["content"])}
        )
    if args.write:
        writer.verify_full_backup(args.full_backup)
        args.backup_dir.mkdir(parents=True, exist_ok=True)
        backup = args.backup_dir / (
            "inline-blocks-before-"
            + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            + ".json"
        )
        with backup.open("x") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        backup.chmod(0o600)
        print(f"Backup: {backup}")
        writer.invoke(args.wp, {"operation": "save", "changes": changes})
        readback = writer.invoke(args.wp, {"operation": "read", "ids": args.page})
        if any(
            readback["rows"][str(c["id"])]["content"] != c["after"] for c in changes
        ):
            raise RuntimeError("Page readback differs")
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
                    }
                    for c in changes
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
