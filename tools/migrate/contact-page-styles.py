"""Move the Contact page pair to its published WindPress stylesheet."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import TypedDict

import reviewed_page_pair as wp

IDS = (28, 6907)
STYLE = re.compile(r'<style data-site-css="contact-journal\.css">.*?</style>', re.S)
ARCHIVE = (
    Path(__file__).resolve().parents[2]
    / "plugins/linker-i18n/tests/fixtures/live/pages.json"
)


class Change(TypedDict):
    id: int
    before: str
    after: str


def original_block() -> str:
    page = next(row for row in json.loads(ARCHIVE.read_text()) if row["id"] == IDS[0])
    body: str = page["content"]
    matches = list(STYLE.finditer(body))
    (block,) = matches
    return block.group()


def plan(pages: dict[str, str]) -> list[Change]:
    original = original_block()
    changes: list[Change] = []
    for post in IDS:
        content = pages[str(post)]
        if 'id="tv-contact-v1"' not in content:
            raise ValueError(f"Contact layout missing from page {post}")
        blocks = STYLE.findall(content)
        if not blocks:
            continue
        if blocks != [original]:
            raise ValueError(f"Contact stylesheet changed on page {post}")
        changes.append(
            {"id": post, "before": content, "after": content.replace(original, "", 1)}
        )
    if len(changes) == 1:
        raise ValueError("Contact pages are in different migration states")
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True, help="WP-CLI command prefix")
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--apply",
        type=Path,
        metavar="BACKUP",
        help="Save the preimage here before applying",
    )
    action.add_argument(
        "--restore", type=Path, metavar="BACKUP", help="Restore the saved Contact pair"
    )
    args = parser.parse_args()
    current = wp.read(args.wp, *IDS)
    if args.restore:
        original = json.loads(args.restore.read_text())
        if current["home"] != original["home"]:
            raise ValueError("Backup belongs to a different site")
        if (
            current["pages"] == original["pages"]
            and current["metadata"] == original["metadata"]
        ):
            print("Contact pages already restored")
            return
        changes = plan(original["pages"])
        payload = {
            "mode": "restore",
            "metadata_before": current["metadata"],
            "metadata_restore": original["metadata"],
            "changes": [
                {"id": row["id"], "before": row["after"], "after": row["before"]}
                for row in changes
            ],
        }
    else:
        changes = plan(current["pages"])
        if not changes:
            print("Contact pages already use the WindPress stylesheet")
            return
        if not args.apply:
            print(
                f"{current['home']} Contact pages {IDS}: replace two reviewed inline styles with the WindPress volume"
            )
            return
        if not current["current"]:
            raise ValueError("Contact translation has pending changes")
        if args.apply.exists():
            if json.loads(args.apply.read_text()) != current:
                raise ValueError("Backup path holds a different preimage")
        else:
            with args.apply.open("x") as backup:
                args.apply.chmod(0o600)
                json.dump(current, backup, ensure_ascii=False)
        payload = {
            "mode": "adopt",
            "changes": changes,
            "metadata_before": current["metadata"],
        }
    result = wp.invoke(args.wp, payload)
    saved = wp.read(args.wp, *IDS)
    if saved["metadata"] != result["expected_metadata"] or not all(
        saved["pages"][str(row["id"])] == row["after"] for row in payload["changes"]
    ):
        raise RuntimeError("Contact page pair did not read back")
    print(f"{saved['home']} Contact pages {IDS} verified")


if __name__ == "__main__":
    main()
