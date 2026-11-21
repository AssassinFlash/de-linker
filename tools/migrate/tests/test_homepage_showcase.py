"""Paired transition from the embedded planner to its published LiveCanvas views."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    "homepage_showcase", HERE / "homepage-project-comparison.py"
)
assert spec and spec.loader
showcase = importlib.util.module_from_spec(spec)
spec.loader.exec_module(showcase)
sys.path.pop(0)

MOUNT = '[linker_planner mode="home"]\n'
CAPABILITIES = '<section class="home-trust" id="capabilities">Trust</section>'
SERVICES = '<section id="services"><div>Services</div></section>'
TESTIMONIALS = '<section id="testimonials">Stories</section>'


def test_pair_preserves_the_existing_livecanvas_bytes_and_repeats_without_changes() -> (
    None
):
    for name in ("Compare", "Vergleichen"):
        markup = f'<section id="configurator-showcase"><h2>{name}</h2></section>'
        beginning = f"<section>{name}</section>\n"
        middle = f"{CAPABILITIES}\n{SERVICES}\n<style>/* local */</style>\n"
        ending = TESTIMONIALS + "\n[linker_contact]"
        before = beginning + MOUNT + middle + ending
        expected = beginning + middle + markup + "\n" + ending
        assert showcase.place(before, markup) == expected
        assert showcase.place(expected, markup) == expected


@pytest.mark.parametrize("synced", [False, True])
def test_publish_and_restore_use_the_same_native_page_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, synced: bool
) -> None:
    import copy
    import json
    from typing import Any

    templates = tmp_path / "templates"
    templates.mkdir()
    for lang in ("en", "de"):
        (templates / f"showcase-{lang}.html").write_text(
            f'<section id="configurator-showcase">{lang}</section>\n'
        )
    monkeypatch.setattr(showcase, "TEMPLATES", templates)
    state: dict[str, Any] = {
        "home": "http://review.test",
        "pages": {
            str(i): f"<p>{i}</p>\n" + MOUNT + CAPABILITIES + SERVICES + TESTIMONIALS
            for i in (13, 6913)
        },
        "metadata": {"13": {"status": ["synced" if synced else "pending"]}},
        "current": synced,
    }
    original = copy.deepcopy(state)
    calls = []
    backup = tmp_path / "homepages.json"

    def invoke(prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
        assert json.loads(backup.read_text())["before"] == original
        assert payload["metadata_before"] == state["metadata"]
        calls.append(payload["mode"])
        for change in payload["changes"]:
            assert state["pages"][str(change["id"])] == change["before"]
            state["pages"][str(change["id"])] = change["after"]
        state["metadata"] = payload.get(
            "metadata_restore", {"13": {"status": ["reviewed"]}}
        )
        return {"expected_metadata": state["metadata"]}

    monkeypatch.setattr(showcase.wp, "read", lambda *args: copy.deepcopy(state))
    monkeypatch.setattr(showcase.wp, "invoke", invoke)
    cli = ["homepage", "--en", "13", "--de", "6913", "--wp", "wp"]
    monkeypatch.setattr(sys, "argv", cli)
    showcase.main()
    assert state == original and not backup.exists()

    monkeypatch.setattr(sys, "argv", cli + ["--remove", "--backup", str(backup)])
    showcase.main()
    showcase.main()
    assert calls == ["adopt" if synced else "restore"]
    published = copy.deepcopy(state)
    for name, id_ in (("en", "13"), ("de", "6913")):
        assert (
            f'<section id="configurator-showcase">{name}</section>\n{TESTIMONIALS}'
            in state["pages"][id_]
        )
        assert MOUNT not in state["pages"][id_]
    monkeypatch.setattr(sys, "argv", cli + ["--restore", str(backup)])
    state["pages"]["13"] += "<p>Subsequent edit</p>"
    with pytest.raises(ValueError, match="changed"):
        showcase.main()
    state.update(published)
    showcase.main()
    showcase.main()
    assert state == original
    assert calls == ["adopt" if synced else "restore", "restore"]
