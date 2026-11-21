"""Preview, publish or restore the bilingual homepage configurator showcase."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import reviewed_page_pair as wp

TEMPLATES = (
    Path(__file__).resolve().parents[2]
    / "plugins/linker-commerce/content/livecanvas/home-configurator"
)
MOUNT = '[linker_planner mode="home"]\n'
CAPABILITIES = '<section class="home-trust" id="capabilities">'
SERVICES = '<section id="services">'
TESTIMONIALS = '<section id="testimonials">'
SHOWCASE = 'id="configurator-showcase"'
HERO_LINK = re.compile(
    r'(data-linker-planner-entry="home-hero"[^>]*>\s*<a\b[^>]*?\bhref="'
    r"(?:/solution-configurator/|/de/loesungskonfigurator/))"
    r'(?:#sc-preliminary-options|\?compare=preliminary)"'
)


def place(content: str, markup: str) -> str:
    """Keep every other byte of both neighboring LiveCanvas sections."""
    if (
        content.count(SERVICES) != 1
        or content.count(TESTIMONIALS) != 1
        or content.index(SERVICES) > content.index(TESTIMONIALS)
    ):
        raise ValueError("Expected the services section before testimonials")
    if markup.count(SHOWCASE) != 1 or not markup.startswith("<section"):
        raise ValueError("Expected the published configurator showcase template")
    if content.count(MOUNT) == 1 and MOUNT + CAPABILITIES in content:
        content = content.replace(MOUNT, "", 1)
    if "[linker_planner" in content:
        raise ValueError("Unrecognized planner mount on the homepage")
    content, links = HERO_LINK.subn(r'\g<1>?compare=preliminary"', content)
    if links != 1:
        raise ValueError("Expected the existing homepage hero comparison link")
    placement = markup + "\n" + TESTIMONIALS
    if SHOWCASE in content:
        if content.count(SHOWCASE) == 1 and placement in content:
            return content
        raise ValueError("The installed showcase differs from the published template")
    return content.replace(TESTIMONIALS, placement, 1)


def planned(pages: dict[str, str], ids: tuple[int, int]) -> dict[str, str]:
    return {
        str(post): place(
            pages[str(post)], (TEMPLATES / f"showcase-{lang}.html").read_text().strip()
        )
        for post, lang in zip(ids, ("en", "de"), strict=True)
    }


def write(
    prefix: str,
    ids: tuple[int, int],
    before: dict[str, Any],
    after: dict[str, str],
    restore: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "mode": "adopt" if restore is None else "restore",
        "changes": [
            {
                "id": post,
                "before": before["pages"][str(post)],
                "after": after[str(post)],
            }
            for post in ids
        ],
        "metadata_before": before["metadata"],
    }
    if restore is not None:
        payload["metadata_restore"] = restore
    result = wp.invoke(prefix, payload)
    saved = wp.read(prefix, *ids)
    if saved["pages"] != after or saved["metadata"] != result["expected_metadata"]:
        raise RuntimeError(
            "The paired homepage content or translation did not read back"
        )
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True, help="WP-CLI command prefix")
    parser.add_argument("--en", required=True, type=int)
    parser.add_argument("--de", required=True, type=int)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--remove", action="store_true", help="Replace the old form")
    action.add_argument("--restore", type=Path, metavar="BACKUP")
    parser.add_argument("--backup", type=Path, help="Local pre-release page pair")
    args = parser.parse_args()

    ids = (args.en, args.de)
    current = wp.read(args.wp, *ids)
    site = current["home"]
    if args.restore:
        backup = json.loads(args.restore.read_text())
        original = backup["before"]
        if (
            original["home"] != site
            or original["pages"].keys() != current["pages"].keys()
        ):
            raise ValueError("The recovery point belongs to another homepage pair")
        if current == original:
            print(f"{site} {ids}: homepage pair already restored")
            return
        if current["pages"] != backup["published_pages"] or current[
            "metadata"
        ] != backup.get("published_metadata", original["metadata"]):
            raise ValueError(
                "The homepage pair changed since the showcase was published"
            )
        saved = write(args.wp, ids, current, original["pages"], original["metadata"])
        if saved != original:
            raise RuntimeError("The original homepage pair did not read back")
        print(f"{site} {ids}: original homepages and translation metadata restored")
        return

    after = planned(current["pages"], ids)
    if after == current["pages"]:
        print(f"{site} {ids}: localized showcases already in place")
        return
    if not args.remove:
        print(
            f"{site} {ids}: replace the embedded planner and insert the EN/DE showcases"
        )
        return
    path = args.backup or (
        Path.home()
        / "de-linker-data"
        / "acceptance"
        / "home-showcase"
        / f"{urlsplit(site).netloc.replace(':', '-')}-{args.en}-{args.de}.json"
    )
    snapshot = {"before": current, "published_pages": after}
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = json.loads(path.read_text())
        if backup["before"] != current or backup["published_pages"] != after:
            raise ValueError("The recovery point contains a different homepage pair")
    else:
        with path.open("x") as backup_file:
            json.dump(snapshot, backup_file, ensure_ascii=False)
    # A stale source retains its existing translator state, including pending edits.
    saved = write(
        args.wp,
        ids,
        current,
        after,
        None if current["current"] else current["metadata"],
    )
    if saved["metadata"] != current["metadata"]:
        snapshot["published_metadata"] = saved["metadata"]
        receipt = path.with_suffix(".tmp")
        receipt.write_text(json.dumps(snapshot, ensure_ascii=False))
        receipt.replace(path)
    print(f"{site} {ids}: published and verified both showcases; recovery point {path}")


if __name__ == "__main__":
    main()
