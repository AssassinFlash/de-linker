"""Hidden empty CookieYes categories are removed; any other shape is refused."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "disclosure", Path(__file__).parents[1] / "cookieyes-disclosure.py"
)
assert spec and spec.loader
disclosure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(disclosure)


def category(slug: str, category_id: int, *, visibility: int = 0) -> dict[str, object]:
    labels = {
        "necessary": {"en": "Essential", "de": "Notwendig"},
        "functional": {"en": "Functional", "de": "Funktionale"},
        "analytics": {"en": "Website analytics", "de": "Website-Analyse"},
        "performance": {"en": "Performance", "de": "Leistungs"},
        "advertisement": {"en": "Visit source", "de": "Besuchsquelle"},
    }[slug]
    return {
        "category_id": category_id,
        "slug": slug,
        "labels": labels,
        "visibility": visibility,
        "prior_consent": 1 if slug == "necessary" else 0,
    }


def snapshot(categories: list[dict[str, object]]) -> dict[str, object]:
    return {
        "categories": categories,
        "cookies": [
            {"cookie_id": 1, "name": "_ga", "category": 3},
            {"cookie_id": 2, "name": "_ga_*", "category": 3},
            {"cookie_id": 3, "name": "sbjs_*", "category": 5},
        ],
    }


LIVE = snapshot(
    [
        category("necessary", 1, visibility=1),
        category("functional", 2),
        category("analytics", 3, visibility=1),
        category("performance", 4),
        category("advertisement", 5, visibility=1),
    ]
)


def test_live_rows_are_an_apply_and_a_repeat_is_done() -> None:
    decision = disclosure.classify(LIVE)
    assert decision["status"] == "apply"
    assert [row["slug"] for row in decision["remove"]] == ["functional", "performance"]
    remaining = snapshot(
        [
            category("necessary", 1, visibility=1),
            category("analytics", 3, visibility=1),
            category("advertisement", 5, visibility=1),
        ]
    )
    assert disclosure.classify(remaining)["status"] == "done"


def test_visible_named_or_populated_rows_are_drift() -> None:
    visible = json.loads(json.dumps(LIVE))
    visible["categories"][1]["visibility"] = 1
    renamed = json.loads(json.dumps(LIVE))
    renamed["categories"][3]["labels"] = {"en": "Performance", "de": "Leistung"}
    populated = json.loads(json.dumps(LIVE))
    populated["cookies"].append({"cookie_id": 9, "name": "extra", "category": 2})
    partial = snapshot(
        [
            category("necessary", 1, visibility=1),
            category("functional", 2),
            category("analytics", 3, visibility=1),
            category("advertisement", 5, visibility=1),
        ]
    )
    for item in (visible, renamed, populated, partial):
        assert disclosure.classify(item)["status"] == "drift"


def test_rendered_config_and_titles_are_read_from_the_page() -> None:
    html = """
    <script>var _ckyConfig = {"_categories":[{"slug":"necessary"},{"slug":"analytics"}]};</script>
    <script id="ckyBannerTemplate" type="text/template">
      <button data-cky-tag="detail-category-title">Essential</button>
    </script>
    """
    assert disclosure.rendered_categories(html) == ["necessary", "analytics"]
    assert disclosure.rendered_titles(html) == ["Essential"]


def test_write_without_a_backup_directory_is_refused_before_wordpress() -> None:
    with pytest.raises(SystemExit):
        disclosure.main(["--wp", "wp", "--write"])


def test_rollback_cannot_bypass_the_production_backup_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup = tmp_path / "backup.json"
    backup.write_text(json.dumps({"remove": [category("functional", 2)]}))
    calls = []

    def read(wp: list[str], payload: dict[str, object]) -> dict[str, object]:
        calls.append((wp, payload))
        return {"home": "https://de-linker.com", **LIVE}

    monkeypatch.setattr(disclosure, "invoke", read)
    with pytest.raises(RuntimeError, match="non-loopback site"):
        disclosure.main(["--wp", "wp", "--rollback", str(backup)])
    assert calls == [
        (["wp"], {"operation": "read"}),
    ]
