"""Publish the four commercial configurator entries and the GoodWe commercial range."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode

import reviewed_page_pair as wp

SCENARIOS = {
    "en": {
        "Plan peak-shaving": "peak_shaving",
        "Plan solar self-consumption": "self_consumption",
        "Size an EV charging buffer": "ev_buffer",
        "Plan backup for critical loads": "backup",
    },
    "de": {
        "Lastspitzenkappung planen": "peak_shaving",
        "Solar-Eigenverbrauch planen": "self_consumption",
        "Ladepuffer für E-Fahrzeuge auslegen": "ev_buffer",
        "Notstrom für kritische Lasten planen": "backup",
    },
}
GOODWE = {
    "en": (
        "/product/goodwe-etr-125-kw-ci-three-phase-hybrid-inverter-1000v/",
        "View GoodWe package",
        "/products/",
        "Browse GoodWe commercial equipment",
    ),
    "de": (
        "/de/produkt/goodwe-etr-125-kw-ci-dreiphasiger-hybridwechselrichter-1000v/",
        "GoodWe-Paket ansehen",
        "/de/produkte/",
        "GoodWe-Geräte für Gewerbeanlagen ansehen",
    ),
}


def update(content: str, lang: str) -> str:
    planner = "/de/loesungskonfigurator/" if lang == "de" else "/solution-configurator/"
    replacements = {}
    for title, goal in SCENARIOS[lang].items():
        query = urlencode({"application": "commercial", "goal": goal}).replace(
            "&", "&amp;"
        )
        replacements[f'href="{planner}" rel="noopener" target="_blank">{title} →'] = (
            f'href="{planner}?{query}">{title} →'
        )
    old, title, catalog, label = GOODWE[lang]
    replacements[f'href="{old}">{title} →'] = (
        f'href="{catalog}?brand=goodwe&amp;application=commercial">{label} →'
    )
    for before, after in replacements.items():
        if content.count(before) == 1 and after not in content:
            content = content.replace(before, after)
        elif before in content or content.count(after) != 1:
            raise ValueError(f"Unexpected {lang} commercial link: {before}")
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument("--en", type=int, required=True)
    parser.add_argument("--de", type=int, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true")
    action.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    ids = args.en, args.de
    current = wp.read(args.wp, *ids)
    if args.restore:
        backup = json.loads(args.backup.read_text())
        wp.verify_published(backup, current)
        original = backup["before"]
        wp.write(args.wp, ids, current, original["pages"], original["metadata"])
        print("Commercial page pair restored.")
        return
    after = {
        str(post): update(current["pages"][str(post)], lang)
        for post, lang in zip(ids, ("en", "de"), strict=True)
    }
    if after == current["pages"]:
        print("Commercial links are current.")
        return
    if not args.write:
        print("Five link updates per language.")
        return
    metadata = current["metadata"]
    if current["current"]:
        metadata = wp.invoke(
            args.wp,
            {
                "mode": "preview_page_adoption",
                "changes": wp.changes(ids, current["pages"], after),
            },
        )["expected_metadata"]
    backup = {
        "before": current,
        "published_pages": after,
        "published_metadata": metadata,
    }
    if args.backup.exists():
        if json.loads(args.backup.read_text()) != backup:
            raise ValueError(
                "The saved commercial pair differs from the current source."
            )
    else:
        with args.backup.open("x") as file:
            json.dump(backup, file, ensure_ascii=False)
    wp.write(args.wp, ids, current, after, metadata, adopt=current["current"])
    print("Commercial links updated and read back in both languages.")


if __name__ == "__main__":
    main()
