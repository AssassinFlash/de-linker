"""Move the Contact page pair to its published WindPress stylesheet."""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any, TypedDict

import reviewed_page_pair as wp

IDS = (28, 6907)
STYLE = re.compile(r'<style data-site-css="contact-journal\.css">.*?</style>', re.S)
ARCHIVE = (
    Path(__file__).resolve().parents[2]
    / "plugins/linker-i18n/tests/fixtures/live/pages.json"
)


# Moving this non-translatable style block in the reviewed EN/DE pair changes
# only WordPress's source fingerprint. These are the native rehearsal values.
SOURCE_HASH = "_linker_i18n_source_hash"
SOURCE_BEFORE = "562380e17ddd6a2ee7af3575361307264acb2486"
SOURCE_AFTER = "880b191dbd4f760e5297e5c13db0e53209a91c36"


def expected_metadata(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = copy.deepcopy(snapshot["metadata"])
    if metadata[str(IDS[1])][SOURCE_HASH] != [SOURCE_BEFORE]:
        raise ValueError("Contact source differs from the reviewed migration")
    metadata[str(IDS[1])][SOURCE_HASH] = [SOURCE_AFTER]
    return metadata


def verify_applied(original: dict[str, Any], current: dict[str, Any]) -> None:
    expected = original.get("expected_metadata") or expected_metadata(original)
    after = {str(row["id"]): row["after"] for row in plan(original["pages"])}
    if (
        current["home"] != original["home"]
        or current["pages"] != after
        or current["metadata"] != expected
        or not current["current"]
    ):
        raise ValueError(
            "Contact pages or their translation baseline changed after migration"
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
        verify_applied(original, current)
        changes = plan(original["pages"])
        payload = {
            "mode": "restore",
            "require_current": True,
            "metadata_before": expected_metadata(original),
            "metadata_restore": original["metadata"],
            "changes": [
                {"id": row["id"], "before": row["after"], "after": row["before"]}
                for row in changes
            ],
        }
    else:
        changes = plan(current["pages"])
        if not changes:
            if args.apply and args.apply.exists():
                verify_applied(json.loads(args.apply.read_text()), current)
            print("Contact pages already use the WindPress stylesheet")
            return
        if not args.apply:
            print(
                f"{current['home']} Contact pages {IDS}: replace two reviewed inline styles with the WindPress volume"
            )
            return
        if not current["current"]:
            raise ValueError("Contact translation has pending changes")
        expected = expected_metadata(current)
        receipt = {**current, "expected_metadata": expected}
        if args.apply.exists():
            if json.loads(args.apply.read_text()) not in (current, receipt):
                raise ValueError("Backup path holds a different preimage")
        else:
            with args.apply.open("x") as backup:
                args.apply.chmod(0o600)
                json.dump(receipt, backup, ensure_ascii=False)
        payload = {
            "mode": "adopt",
            "expected_metadata": expected,
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
