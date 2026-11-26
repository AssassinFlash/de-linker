"""Mixed SEO baselines restore only fields published by this migration."""

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import batch_s1_pages as s1
import reviewed_page_pair as pairs
from batch_r3_pages import PAGES, save


def test_restore_preserves_an_existing_final_field_and_reverts_a_changed_field(
    tmp_path: Path,
) -> None:
    states: dict[str, dict[str, Any]] = {}
    for name in ("utility-storage", "services-support"):
        key, old, new = s1.SEO[name]
        en, de = PAGES[name]
        states[name] = {
            "home": "http://linker.test/",
            "current": False,
            "metadata": {},
            "values": {
                str(en): {key: "English"},
                str(de): {key: new if name == "utility-storage" else old},
            },
        }
        save(tmp_path / f"{name}-seo-before.json", states[name])
    original = deepcopy(states)
    writes = []

    def read(_wp: str, name: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return [{"id": pid} for pid in PAGES[name]], deepcopy(states[name])

    def invoke(_wp: str, request: dict[str, Any]) -> dict[str, Any]:
        assert request["mode"] == "save_descriptions"
        name = next(n for n in states if PAGES[n][0] == request["changes"][0]["id"])
        states[name]["values"] = deepcopy(request["after"])
        writes.append(name)
        return {}

    with patch.object(s1, "seo_read", read), patch.object(pairs, "invoke", invoke):
        for action in ("apply", "apply", "restore", "restore"):
            for name in states:
                s1.seo_update("wp", tmp_path, name, action)
    assert states == original
    assert writes == ["services-support", "services-support"]
    assert not (tmp_path / "utility-storage-seo-change.json").exists()
    assert (
        json.loads((tmp_path / "services-support-seo-change.json").read_text())[
            "before"
        ]
        == original["services-support"]
    )
