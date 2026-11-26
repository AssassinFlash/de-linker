from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from pytest import MonkeyPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from batch_s3_pages import DESCRIPTIONS, FIELDS, desired_values


def test_social_overrides_follow_the_localized_search_description() -> None:
    search, facebook, twitter = FIELDS
    before: dict[str, Any] = {
        "13": {search: "old English copy", facebook: "old Facebook copy"},
        "6913": {search: "alte Beschreibung", twitter: "alter X-Text"},
    }
    target = desired_values("home", before)
    en, de = DESCRIPTIONS["home"]
    assert target == {
        "13": {search: en, facebook: en},
        "6913": {search: de, twitter: de},
    }
    assert desired_values("home", target) == target


def test_installer_page_and_german_copy_source_agree() -> None:
    import json
    from pathlib import Path

    rules = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "plugins/linker-i18n/content/german-copy.json"
        ).read_text()
    )
    installer = next(rule for rule in rules if rule["source"] == "for-installer")
    assert (
        installer["set"]["meta:_seopress_titles_desc"]
        == DESCRIPTIONS["for-installer"][1]
    )
    assert all(
        len(description) <= 155
        for pair in DESCRIPTIONS.values()
        for description in pair
    )


def test_wp_escaped_tagline_round_trip(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    import html

    import batch_s3_pages as migration

    value = "Original tagline"

    def wp(command: list[str], *, text: bool) -> str:
        nonlocal value
        if command[-1] == "home":
            return "https://example.org"
        if command[2] == "update":
            value = html.escape(html.unescape(command[-1]))
        return value

    monkeypatch.setattr(migration.subprocess, "check_output", wp)
    for action in ("backup", "apply", "apply", "read"):
        migration.tagline("wp", tmp_path, action)
    assert value == migration.TAGLINE.replace("&", "&amp;")
    migration.tagline("wp", tmp_path, "restore")
    assert value == "Original tagline"
