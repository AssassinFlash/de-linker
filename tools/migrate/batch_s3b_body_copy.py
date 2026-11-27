"""Publish or restore the reviewed EN/DE availability wording in five page pairs."""

from __future__ import annotations

import argparse
import json
import os
import re
import runpy
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import reviewed_page_pair as wp

PAIRS = {
    "home": (13, 6913),
    "about": (862, 6865),
    "for-installer": (826, 6869),
    "services-support": (2748, 6700),
    "residential-storage": (749, 6923),
}
COPY: dict[str, list[list[str]]] = json.loads(
    Path(__file__).with_name("batch-s3b-body-copy.json").read_text()
)
INLINE = re.compile(
    r"<(?:script\b[^>]*>.*?</script|style\b[^>]*>.*?</style)>", re.I | re.S
)


def planned(ids: tuple[int, int], pages: dict[str, str]) -> dict[str, str]:
    """Both complete originals or both complete revisions must be present."""
    stages = set()
    after = pages.copy()
    for pid in map(str, ids):
        for before, replacement in COPY[pid]:
            counts = pages[pid].count(before), pages[pid].count(replacement)
            if counts not in {(1, 0), (0, 1)}:
                raise ValueError(
                    f"Page {pid}: expected one reviewed source or replacement ({counts})"
                )
            stages.add(counts)
            after[pid] = after[pid].replace(before, replacement)
        if INLINE.findall(pages[pid]) != INLINE.findall(after[pid]):
            raise ValueError(f"Page {pid}: reviewed fragment inside an inline asset")
    if len(stages) != 1:
        raise ValueError(f"Pages {ids}: partially updated copy")
    return after


def record(path: Path, receipt: dict[str, Any]) -> None:
    """Publish a complete private receipt without overwriting its original."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != receipt:
            raise ValueError(f"Recovery point differs: {path}")
        return
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(receipt, stream, ensure_ascii=False)
            stream.flush()
            os.link(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True, help="WP-CLI command prefix")
    parser.add_argument("--page", choices=PAIRS)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--full-backup", type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    if (args.apply or args.restore) and not args.backup_dir:
        parser.error("--apply and --restore require --backup-dir")

    pending = []
    for page in [args.page] if args.page else PAIRS:
        ids = PAIRS[page]
        current = wp.read(args.wp, *ids)
        site = urlsplit(current["home"])
        path = (
            args.backup_dir / f"{site.netloc.replace(':', '-')}-{page}-s3b.json"
            if args.backup_dir
            else None
        )
        saved = json.loads(path.read_text()) if path and path.exists() else None
        if args.restore:
            if saved is None:
                if args.page:
                    raise ValueError(f"No recovery point for {page}")
                print(f"{page}: no change recorded")
                continue
            if current == saved["before"]:
                print(f"{page}: original pair")
                continue
            wp.verify_published(saved, current)
            pending.append((page, ids, current, path, saved))
            continue

        after = planned(ids, current["pages"])
        if after == current["pages"]:
            if saved is not None:
                wp.verify_published(saved, current)
            print(f"{page}: reviewed copy already present")
            continue
        if not args.apply:
            print(f"{page}: ready")
            continue
        if saved is not None and saved["before"] != current:
            raise ValueError(f"Recovery point differs: {path}")
        metadata = current["metadata"]
        if current["current"]:
            metadata = wp.invoke(
                args.wp,
                {
                    "mode": "preview_page_adoption",
                    "changes": wp.changes(ids, current["pages"], after),
                },
            )["expected_metadata"]
        receipt = {
            "before": current,
            "published_pages": after,
            "published_metadata": metadata,
        }
        if saved is not None and saved != receipt:
            raise ValueError(f"Recovery point differs: {path}")
        pending.append((page, ids, current, path, receipt))

    if args.apply and any(
        urlsplit(current["home"]).hostname in {"de-linker.com", "www.de-linker.com"}
        for _, _, current, _, _ in pending
    ):
        if args.full_backup is None:
            parser.error("Production publication requires --full-backup")
        runpy.run_path(str(Path(__file__).with_name("repair-legal-script.py")))[
            "verify_full_backup"
        ](args.full_backup)

    for page, ids, current, path, receipt in pending:
        if args.restore:
            original = receipt["before"]
            restored = wp.write(
                args.wp, ids, current, original["pages"], original["metadata"]
            )
            if restored != original:
                raise RuntimeError(f"{page}: original pair did not read back")
            print(f"{page}: restored")
        else:
            assert path is not None
            record(path, receipt)
            result = wp.write(
                args.wp,
                ids,
                current,
                receipt["published_pages"],
                receipt["published_metadata"],
                adopt=current["current"],
            )
            wp.verify_published(receipt, result)
            print(f"{page}: published and verified")


if __name__ == "__main__":
    main()
