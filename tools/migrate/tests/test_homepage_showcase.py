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


def hero(path: str, label: str) -> str:
    return f'<div data-linker-planner-entry="home-hero"><a class="home-btn home-btn-primary" href="{path}#sc-preliminary-options">{label}</a></div>'


def test_pair_preserves_the_existing_livecanvas_bytes_and_repeats_without_changes() -> (
    None
):
    for name, path in (
        ("Compare", "/solution-configurator/"),
        ("Vergleichen", "/de/loesungskonfigurator/"),
    ):
        markup = f'<section id="configurator-showcase"><h2>{name}</h2></section>'
        beginning = (
            hero(path, name) + f'<a href="{path}#sc-preliminary-options">Other</a>\n'
        )
        middle = f"{CAPABILITIES}\n{SERVICES}\n<style>/* local */</style>\n"
        ending = TESTIMONIALS + "\n[linker_contact]"
        before = beginning + MOUNT + middle + ending
        expected = (
            beginning.replace("#sc-preliminary-options", "?compare=preliminary", 1)
            + middle
            + markup
            + "\n"
            + ending
        )
        assert showcase.place(before, markup) == expected
        assert showcase.place(expected, markup) == expected


@pytest.mark.parametrize("synced", [False, True])
@pytest.mark.parametrize("interruption", [None, "commit_ack", "readback"])
def test_publish_and_restore_use_the_same_native_page_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    synced: bool,
    interruption: str | None,
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
            str(i): hero(path, str(i)) + MOUNT + CAPABILITIES + SERVICES + TESTIMONIALS
            for i, path in (
                (13, "/solution-configurator/"),
                (6913, "/de/loesungskonfigurator/"),
            )
        },
        "metadata": {"13": {"status": ["synced" if synced else "pending"]}},
        "current": synced,
    }
    original = copy.deepcopy(state)
    calls: list[str] = []
    backup = tmp_path / "homepages.json"

    adopted_metadata = {"13": {"status": ["reviewed"]}}
    interrupt = interruption

    def read(*_: Any) -> dict[str, Any]:
        nonlocal interrupt
        if interrupt == "readback" and calls:
            interrupt = None
            raise ConnectionError("readback")
        return copy.deepcopy(state)

    def invoke(prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal interrupt
        if payload["mode"] == "preview_page_adoption":
            assert synced and not calls
            return {"expected_metadata": adopted_metadata}
        snapshot = json.loads(backup.read_text())
        assert snapshot["before"] == original
        assert snapshot.get("published_metadata", original["metadata"]) == (
            adopted_metadata if synced else original["metadata"]
        )
        assert payload["metadata_before"] == state["metadata"]
        calls.append(payload["mode"])
        for change in payload["changes"]:
            assert state["pages"][str(change["id"])] == change["before"]
            state["pages"][str(change["id"])] = change["after"]
        if payload["mode"] == "adopt":
            assert payload["expected_metadata"] == adopted_metadata
            state["metadata"] = adopted_metadata
        else:
            state["metadata"] = payload["metadata_restore"]
        if interrupt == "commit_ack":
            interrupt = None
            raise ConnectionError("commit_ack")
        return {"expected_metadata": state["metadata"]}

    monkeypatch.setattr(showcase.wp, "read", read)
    monkeypatch.setattr(showcase.wp, "invoke", invoke)
    cli = ["homepage", "--en", "13", "--de", "6913", "--wp", "wp"]
    monkeypatch.setattr(sys, "argv", cli)
    showcase.main()
    assert state == original and not backup.exists()

    monkeypatch.setattr(sys, "argv", cli + ["--remove", "--backup", str(backup)])
    if interruption:
        with pytest.raises(ConnectionError, match=interruption):
            showcase.main()
    else:
        showcase.main()
    # A lost commit acknowledgement may be followed immediately by rollback.
    if interruption != "commit_ack":
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
    state.update(copy.deepcopy(published))
    state["metadata"]["13"]["status"] = ["later manual review"]
    with pytest.raises(ValueError, match="changed"):
        showcase.main()
    monkeypatch.setattr(sys, "argv", cli + ["--remove", "--backup", str(backup)])
    with pytest.raises(ValueError, match="changed"):
        showcase.main()
    state.update(published)
    monkeypatch.setattr(sys, "argv", cli + ["--restore", str(backup)])
    showcase.main()
    showcase.main()
    assert state == original
    assert calls == ["adopt" if synced else "restore", "restore"]
