"""The commerce snippets use the reviewed German and preserve unrelated SEO fields."""

import json
from importlib import import_module
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]


def test_descriptions_match_native_fields_and_german_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(HERE))
    release = import_module("public-commerce-descriptions")
    manifest = json.loads(release.MANIFEST.read_text())
    german = {
        item["source"]: item.get("set", {})
        for item in json.loads(
            (
                HERE.parents[1] / "plugins/linker-i18n/content/german-copy.json"
            ).read_text()
        )
    }
    for slug, pair in manifest.items():
        before, final = release.revisions(pair)
        for post in before:
            assert before[post].keys() == final[post].keys()
            assert set(before[post]) <= {
                "_seopress_titles_desc",
                "_seopress_social_fb_desc",
                "_seopress_social_twitter_desc",
            }
        german_desc = german.get(slug, {}).get("meta:_seopress_titles_desc")
        if german_desc:
            assert pair["de"]["description"] == german_desc
        if slug in {"cart", "my-account", "proforma-request"}:
            for values in final.values():
                assert len(values) == 3
                assert len(set(values.values())) == 1
        if slug == "terms-of-sale":
            assert all(
                set(values) == {"_seopress_titles_desc"} for values in final.values()
            )
        if slug == "products":
            assert all(
                "_seopress_titles_desc" not in values for values in final.values()
            )
