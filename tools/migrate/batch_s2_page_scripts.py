"""Retire the unused prototype link handler from the paired marketing pages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import reviewed_page_pair as pairs
from batch_r3_pages import PAGES, publish_pair, save

MARKETING = {**PAGES, "contact": (28, 6907)}
STUB_HANDLER = """    document.addEventListener("click", function (event) {
      var link = event.target.closest("a[data-stub]");
      if (!link) {
        return;
      }
      event.preventDefault();
    });
"""


def update(content: str) -> str:
    if STUB_HANDLER in content:
        if "data-stub=" in content:
            raise ValueError("A prototype link is still in use")
        content = content.replace(STUB_HANDLER, "")
    for selector in ("[data-adv-select]", ".home-adv-trigger", "[data-chapter]"):
        old = f"event.target.closest('{selector}')"
        content = content.replace(old, f"event.target.closest?.('{selector}')")
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backup", "apply", "read", "restore"))
    parser.add_argument("--wp", required=True)
    parser.add_argument("--backup-dir", required=True, type=Path)
    args = parser.parse_args()
    folder = args.backup_dir
    folder.mkdir(parents=True, exist_ok=True)
    for name, ids in MARKETING.items():
        before = folder / f"{name}-before.json"
        current = pairs.read(args.wp, *ids)
        if args.action == "backup":
            save(before, current)
            if json.loads(before.read_text()) != current:
                raise ValueError(f"{name}: backup differs from current page")
            continue
        after = {pid: update(body) for pid, body in current["pages"].items()}
        if any(
            'event.target.closest("a[data-stub]")' in body for body in after.values()
        ):
            raise ValueError(f"{name}: unexpected prototype handler")
        publish_pair(
            args.wp,
            args.action,
            folder,
            name,
            ids,
            current,
            None if args.action == "restore" else after,
        )


if __name__ == "__main__":
    main()
