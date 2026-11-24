"""Publish or restore the reviewed bilingual public pages.

With --wp alone, preview all pairs. --write and --restore also require
--backup-dir. Production writes also require --full-backup with the completed
site backup manifest in addition to the cutover database snapshot. Use --page
to publish or restore a single pair.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import reviewed_page_pair as wp

PAGES = {
    "about": (862, 6865),
    "contact": (28, 6907),
    "services": (2748, 6700),
    "utility": (1755, 6917),
    "privacy": (1673, 6827),
    "imprint": (1672, 6829),
    "capability": (874, 6919),
    "epc": (842, 6867),
    "installer": (826, 6869),
    "home": (13, 6913),
    "faq": (932, 6863),
}


def source(name: str) -> Any:
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contact_workspace(content: str, title: str) -> str:
    """Keep the native form mount, deep links and authored sections beneath it."""
    heading = f'<header class="cp-contact-heading"><h1 id="cp-page-title">{title}</h1></header>'
    if heading in content and 'data-site-js="contact-page.js"' not in content:
        return content
    content, hero = re.subn(
        r'<section\b[^>]*class="cp-hero"[^>]*>.*?</section>\s*(<div class="cp-paper">)\s*<section\b[^>]*class="cp-intro"[^>]*>.*?</section>',
        lambda match: heading + match[1],
        content,
        flags=re.S,
    )
    content, script = re.subn(
        r'<script data-site-js="contact-page\.js">.*?</script>', "", content, flags=re.S
    )
    if (hero, script) != (1, 1) or "data-linker-contact-mount" not in content:
        raise ValueError("Contact form workspace differs from the reviewed layout")
    return content


def planned(page: str, snapshot: dict[str, Any]) -> dict[str, str]:
    ids, pages = PAGES[page], snapshot["pages"]
    if page == "contact":
        return {
            str(post): contact_workspace(pages[str(post)], title)
            for post, title in zip(ids, ("Contact Linker", "Kontakt"), strict=True)
        }
    if page in {"privacy", "capability", "epc", "installer"}:
        payload = source("quotation-page-copy").plan_pair(
            ids, snapshot, require_current=False
        )
        return (
            {str(row["id"]): row["after"] for row in payload["changes"]}
            if payload
            else pages
        )
    if page == "services":
        transform = source("industry-standards").plan_pair
    else:
        marketing = source("marketing-controls")
        transform = getattr(
            marketing,
            {
                "imprint": "plan_imprint_operator",
                "about": "plan_about_registration",
                "utility": "plan_utility_equipment_tools",
                "home": "plan_home_delivery_documents",
                "faq": "plan_faq_warranty_reference",
            }[page],
        )
    en, de = ids
    results = transform(pages[str(en)], pages[str(de)])
    return dict(zip(map(str, ids), results, strict=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True, help="WP-CLI prefix")
    parser.add_argument("--page", help="Limit publication to one named page pair")
    parser.add_argument("--vocabulary", action="store_true", help="Publish the reviewed Wave 3 marketing wording")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument(
        "--full-backup", type=Path, help="Completed production backup directory"
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true")
    action.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    if (args.write or args.restore) and not args.backup_dir:
        parser.error("--write and --restore require --backup-dir")
    full_backup_verified = False
    vocabulary = json.loads(Path(__file__).with_name("wave3-vocabulary.json").read_text()) if args.vocabulary else {}
    pairs = vocabulary.get("page_pairs", PAGES)
    if args.page and args.page not in pairs:
        parser.error(f"Unknown page in this publication: {args.page}")
    for page in (args.page,) if args.page else pairs:
        ids = tuple(pairs[page])
        current = wp.read(args.wp, *ids)
        site = current["home"]
        host = urlsplit(site).netloc.replace(":", "-")
        path = args.backup_dir / f"{host}-{page}{'-vocabulary' if args.vocabulary else ''}.json" if args.backup_dir else None
        if args.restore:
            assert path is not None
            if not args.page and not path.exists():
                print(f"{site} {page}: no change recorded")
                continue
            backup = json.loads(path.read_text())
            original = backup["before"]
            if (
                original["home"] != site
                or original["pages"].keys() != current["pages"].keys()
            ):
                raise ValueError(f"{page}: wrong recovery point")
            if current != original:
                wp.verify_published(backup, current)
                if (
                    wp.write(
                        args.wp, ids, current, original["pages"], original["metadata"]
                    )
                    != original
                ):
                    raise RuntimeError(f"{page}: original pair did not read back")
            print(f"{site} {page}: restored")
            continue
        if args.vocabulary:
            after = current["pages"].copy()
            for post, content in current["pages"].items():
                for previous, replacement in vocabulary["page_copy"].items():
                    content = content.replace(previous, replacement)
                after[post] = content
        else:
            after = planned(page, current)
        if after == current["pages"]:
            if path and path.exists():
                wp.verify_published(json.loads(path.read_text()), current)
            print(f"{site} {page}: final content")
            continue
        if not args.write:
            print(f"{site} {page}: ready to publish")
            continue
        if (
            urlsplit(site).hostname in {"de-linker.com", "www.de-linker.com"}
            and not full_backup_verified
        ):
            if (
                not args.full_backup
                or not (args.full_backup / "manifest.json").is_file()
            ):
                parser.error("Production requires a completed --full-backup")
            source("repair-legal-script").verify_full_backup(args.full_backup)
            full_backup_verified = True
        meta = current["metadata"]
        if current["current"]:
            preview = wp.invoke(
                args.wp,
                {
                    "mode": "preview_page_adoption",
                    "changes": wp.changes(ids, current["pages"], after),
                },
            )
            meta = preview["expected_metadata"]
        backup = {
            "before": current,
            "published_pages": after,
            "published_metadata": meta,
        }
        assert path is not None
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.exists():
            if json.loads(path.read_text()) != backup:
                raise ValueError(f"{page}: recovery point differs")
        else:
            with path.open("x", encoding="utf-8") as handle:
                path.chmod(0o600)
                json.dump(backup, handle, ensure_ascii=False)
        wp.write(args.wp, ids, current, after, meta, adopt=current["current"])
        print(f"{site} {page}: published and verified; {path}")


if __name__ == "__main__":
    main()
