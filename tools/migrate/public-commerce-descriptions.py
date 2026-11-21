"""Preview, publish or restore the reviewed SEOPress descriptions for public commerce pages."""

from __future__ import annotations

import argparse
import json
from importlib import import_module
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import reviewed_page_pair as wp

MANIFEST = Path(__file__).with_name("commerce-descriptions.json")
FIELDS = {
    "search": ("_seopress_titles_desc",),
    "social": ("_seopress_social_fb_desc", "_seopress_social_twitter_desc"),
}


def revisions(
    pair: dict[str, Any],
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Expand one reviewed bilingual pair into the exact stored fields."""
    before = {}
    after = {}
    for page in pair.values():
        post = str(page["id"])
        before[post] = {
            key: value
            for group, value in page["previous"].items()
            for key in FIELDS[group]
        }
        after[post] = dict.fromkeys(before[post], page["description"])
    return before, after


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--full-backup", type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true")
    action.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    if (args.write or args.restore) and not args.backup_dir:
        parser.error("A write or restore needs --backup-dir")
    verified_backup = False
    for slug, pair in json.loads(MANIFEST.read_text()).items():
        old, final = revisions(pair)
        changes = [{"id": int(post), "keys": list(keys)} for post, keys in old.items()]
        request = {"mode": "read_descriptions", "changes": changes}
        state = wp.invoke(args.wp, request)
        site = urlsplit(state["home"])
        receipt = (
            args.backup_dir
            / f"{site.netloc.replace(':', '-')}-{slug}-descriptions.json"
            if args.backup_dir
            else None
        )
        if not state["current"]:
            raise ValueError(f"{slug}: review the changed translation baseline")
        if args.restore:
            assert receipt
            if not receipt.is_file():
                if state["values"] == old:
                    print(f"{slug}: original")
                    continue
                raise ValueError(f"{slug}: missing release receipt")
            recorded = json.loads(receipt.read_text())
            target = recorded["before"]
            if state == target:
                print(f"{slug}: restored")
                continue
            if state != recorded["published"]:
                raise ValueError(f"{slug}: changed since publication")
        else:
            if state["values"] == final:
                print(f"{slug}: final")
                continue
            if state["values"] != old:
                raise ValueError(
                    f"{slug}: descriptions differ from the reviewed wording"
                )
            if not args.write:
                print(f"{slug}: ready ({sum(map(len, final.values()))} fields)")
                continue
            assert receipt
            preview = wp.invoke(
                args.wp,
                {
                    "mode": "preview_page_adoption",
                    "changes": [
                        {"id": int(post), "descriptions": values}
                        for post, values in final.items()
                    ],
                },
            )
            target = {
                **state,
                "values": final,
                "metadata": preview["expected_metadata"],
            }
            recorded = {"before": state, "published": target}
            if receipt.exists() and recorded != json.loads(receipt.read_text()):
                raise ValueError(f"{slug}: recovery point differs")
        if (
            site.hostname in ("de-linker.com", "www.de-linker.com")
            and not verified_backup
        ):
            if not args.full_backup:
                parser.error("Production requires --full-backup")
            import_module("repair-legal-script").verify_full_backup(args.full_backup)
            verified_backup = True
        if not receipt.exists():
            receipt.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with receipt.open("x", encoding="utf-8") as handle:
                receipt.chmod(0o600)
                json.dump(recorded, handle, ensure_ascii=False)
        wp.invoke(
            args.wp,
            {
                "mode": "save_descriptions",
                "changes": changes,
                "before": state["values"],
                "after": target["values"],
                "metadata_before": state["metadata"],
                "expected_metadata": target["metadata"],
            },
        )
        if wp.invoke(args.wp, request) != target:
            raise RuntimeError(f"{slug}: independent readback differs")
        print(f"{slug}: {'restored' if args.restore else 'published'} ({receipt})")


if __name__ == "__main__":
    main()
