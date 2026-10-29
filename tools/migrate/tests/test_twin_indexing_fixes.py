"""The noindex and German blog-template repair uses the measured targets."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

MIGRATIONS = Path(__file__).resolve().parents[1]


def load_migration() -> ModuleType:
    sys.path.insert(0, str(MIGRATIONS))
    spec = importlib.util.spec_from_file_location(
        "twin_indexing_fixes", MIGRATIONS / "twin-indexing-fixes.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def migration() -> ModuleType:
    """Load the file each time so pytest's module state cannot hide a defect."""
    return load_migration()


def state(
    *,
    twin_index: str = "",
    doubled: int = 1,
    correct: int = 0,
    template_slug: str = "vorlage-fur-blog-beitragsindex",
) -> dict[str, Any]:
    return {
        "source": {
            "id": 623,
            "name": "thank-you",
            "type": "page",
            "index": "yes",
        },
        "twin": {
            "id": 6873,
            "name": "danke",
            "type": "page",
            "language": "de",
            "index": twin_index,
        },
        "template": {
            "id": 6881,
            "name": template_slug,
            "type": "lc_dynamic_template",
            "language": "de",
            "doubled": doubled,
            "correct": correct,
            "content": (
                '<script type="application/ld+json">'
                '{"url":"[linker_site_url]de/blog/"}</script>'
            ),
        },
    }


def test_plan_names_the_two_measured_posts_separately() -> None:
    actions = migration().plan(state())

    assert actions == [
        {
            "kind": "meta",
            "post": 6873,
            "key": "_seopress_robots_index",
            "from": "",
            "to": "yes",
        },
        {
            "kind": "template",
            "post": 6881,
            "from": "[linker_site_url]de/blog/",
            "to": "[linker_site_url]blog/",
        },
    ]


def test_plan_is_idempotent_after_both_values_are_repaired() -> None:
    assert migration().plan(state(twin_index="yes", doubled=0, correct=1)) == []


def test_a_different_template_or_removed_source_ruling_is_refused() -> None:
    with pytest.raises(SystemExit, match="not the German blog-index template"):
        migration().plan(state(template_slug="another-template"))

    changed = state()
    changed["source"]["index"] = ""
    with pytest.raises(SystemExit, match="no longer carries"):
        migration().plan(changed)


def test_apply_targets_each_post_and_records_both_old_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = migration()
    current = state()
    actions = module.plan(current)
    backup = tmp_path / "backup.json"
    written: list[str] = []

    monkeypatch.setattr(module, "read_state", lambda _prefix: current)
    monkeypatch.setattr(module, "php", lambda _prefix, code: written.append(code))

    module.apply(["wp"], actions, backup)

    record = json.loads(backup.read_text(encoding="utf-8"))
    assert record["previous"]["thank_you_twin"] == {"post": 6873, "index": ""}
    assert record["previous"]["blog_template"]["post"] == 6881
    assert record["previous"]["blog_template"]["doubled"] == 1
    assert len(written) == 1
    assert "update_post_meta( 6873, '_seopress_robots_index', 'yes' )" in written[0]
    assert "get_post_field( 'post_content', 6881 )" in written[0]
    assert "wp_update_post( array( 'ID' => 6881" in written[0]
    assert "6873, 'post_content'" not in written[0]


def test_apply_refuses_actions_planned_against_an_older_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = migration()
    old_actions = module.plan(state())
    monkeypatch.setattr(
        module,
        "read_state",
        lambda _prefix: state(twin_index="yes", doubled=0, correct=1),
    )
    monkeypatch.setattr(
        module,
        "php",
        lambda *_args: (_ for _ in ()).throw(AssertionError("must not write")),
    )

    with pytest.raises(SystemExit, match="changed after planning"):
        module.apply(["wp"], old_actions, tmp_path / "backup.json")


def test_verify_requires_both_stored_values() -> None:
    module = migration()
    failures = module.verify(state())

    assert len(failures) == 3
    assert "6873 _seopress_robots_index" in failures[0]
    assert "6881 still carries 1 doubled" in failures[1]
    assert "expected 1" in failures[2]
    assert module.verify(state(twin_index="yes", doubled=0, correct=1)) == []
