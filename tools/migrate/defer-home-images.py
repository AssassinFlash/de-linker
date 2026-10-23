#!/usr/bin/env python3
"""Defer the audited below-fold homepage photos without changing page content.

Use native loading/decoding attributes and retain every src. The shared content
writer transports JSON over STDIN, calls wp_slash(), locks both original rows
and refuses drift. Production writes require a verified complete local backup.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

path = Path(__file__).with_name("repair-legal-script.py")
spec = importlib.util.spec_from_file_location("content_writer", path)
assert spec and spec.loader
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)

# Published EN/DE front pages, verified through page_on_front and Polylang.
HOMEPAGES = (13, 6913)
# Actual homepage IMG sources from the complete snapshot. The container image
# appears twice; the last scene-card photo was already lazy. Header/logo and
# the CSS hero background are outside this list and remain unchanged.
PHOTO_PATHS = (
    "2026/09/linker-source-solar-and-storage-in-one-place-1.webp",
    "2026/09/linker-check-what-works-together-1.webp",
    "2026/09/linker-trade-support-from-germany-1.webp",
    "2026/10/linker-residential-goodwe-esa-all-in-one.webp",
    "2026/09/linker-commercial-storage-for-contractors-1.webp",
    "2026/09/linker-utility-scale-bess.webp",
    "2026/09/linker-find-the-system-you-need-1.webp",
    "2026/09/linker-match-inverter-battery-accessories-1.webp",
    "2026/09/linker-trade-pricing-and-availability-1.webp",
    "2026/09/linker-order-the-system-1.webp",
    "2026/09/linker-support-after-the-order-1.webp",
    "2026/09/linker-installers-buy-through-linker.webp",
    "2026/09/linker-contractors-buy-through-linker.webp",
    "2026/09/linker-grid-projects-buy-through-linker.webp",
    "2026/09/linker-utility-scale-bess.webp",
    "2026/09/linker-when-demand-gets-bigger.webp",
)
PHOTO_SOURCES = Counter("/wp-content/uploads/" + name for name in PHOTO_PATHS)


class HomeImages(HTMLParser):
    """Locate real opening tags, ignoring IMG-like script/comment strings."""

    def __init__(self, content: str) -> None:
        super().__init__(convert_charrefs=False)
        self.content = content
        self.line_starts = [0]
        self.line_starts.extend(i + 1 for i, char in enumerate(content) if char == "\n")
        self.sources: Counter[str] = Counter()
        self.edits: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        attributes = dict(attrs)
        if len(attributes) != len(attrs):
            raise ValueError("Duplicate image attributes; refusing ambiguous markup")
        source = attributes.get("src")
        if source not in PHOTO_SOURCES:
            raise ValueError(
                "Unexpected homepage image; audit its position before changing"
            )
        assert source is not None
        self.sources[source] += 1
        added = ""
        for name, value in (("loading", "lazy"), ("decoding", "async")):
            if name not in attributes:
                added += f' {name}="{value}"'
            elif attributes[name] != value:
                raise ValueError(f"Conflicting {name} attribute; refusing to override")
        if not added:
            return
        raw = self.get_starttag_text()
        if raw is None:
            raise ValueError("Image has no intact opening tag")
        # Insert before the optional XHTML slash, preserving the original tag.
        end = len(raw) - (2 if raw.endswith("/>") else 1)
        line, column = self.getpos()
        self.edits.append((self.line_starts[line - 1] + column + end, added))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def defer_images(content: str) -> str:
    """Only add attributes to the complete, known homepage image set."""
    if 'id="home-a"' not in content:
        raise ValueError("Not the audited LiveCanvas homepage")
    parser = HomeImages(content)
    parser.feed(content)
    parser.close()
    if parser.sources != PHOTO_SOURCES:
        raise ValueError("Homepage image set changed; refusing a partial repair")
    result = content
    for position, added in reversed(parser.edits):
        result = result[:position] + added + result[position:]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--full-backup", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    snapshot = writer.invoke(args.wp, {"operation": "read", "ids": HOMEPAGES})
    changes = []
    for page_id in HOMEPAGES:
        row = snapshot["rows"][str(page_id)]
        if row["type"] != "page":
            raise ValueError("Homepage ID is not a page")
        changes.append(
            {
                "id": page_id,
                "before": row["content"],
                "after": defer_images(row["content"]),
            }
        )
    if args.write:
        if args.backup_dir is None:
            parser.error("--write requires --backup-dir")
        if urlsplit(snapshot["home"]).hostname in {
            "de-linker.com",
            "www.de-linker.com",
        }:
            if args.full_backup is None:
                parser.error("Production requires --full-backup")
            writer.verify_full_backup(args.full_backup)
        args.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = args.backup_dir / (
            "homepage-images-before-"
            + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            + ".json"
        )
        with backup.open("x") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        backup.chmod(0o600)
        print(f"Backup: {backup}")
        writer.invoke(args.wp, {"operation": "save", "changes": changes})
        readback = writer.invoke(args.wp, {"operation": "read", "ids": HOMEPAGES})
        if any(
            readback["rows"][str(c["id"])]["content"] != c["after"] for c in changes
        ):
            raise RuntimeError("Independent homepage readback differs")
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
