from __future__ import annotations

from typing import Any

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
