"""A content-only repair must preserve scripts, quotes and unrelated occurrences."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

spec = importlib.util.spec_from_file_location(
    "home_copy", Path(__file__).parents[1] / "home-inquiry-copy.py"
)
assert spec and spec.loader
copy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(copy)


def document(lang: str) -> str:
    heading, body, _, _ = copy.COPY[lang]
    return (
        '<script>const escaped="\\u003csvg";const pattern=/\\s+/;</script>'
        f"<blockquote>{body}</blockquote><p>{heading}</p>"
        '<div class="scene-card home-scene-card"><div class="scene-card-body">'
        f"<h4>{heading}</h4><p>{body}</p>"
        '<a href="/contact/?intent=offer&amp;kind=page" data-x="keep">CTA</a>'
        '</div><img width="1620" src="/photo.webp"/></div>'
    )


def test_changes_only_reviewed_scene_and_is_idempotent() -> None:
    before = (document("en"), document("de"))
    after = copy.plan_pair(*before)
    for lang, original, final in zip(("en", "de"), before, after, strict=True):
        old_h, old_p, new_h, new_p = copy.COPY[lang]
        assert final == original.replace(
            f"<h4>{old_h}</h4><p>{old_p}</p>", f"<h4>{new_h}</h4><p>{new_p}</p>"
        )
        assert final.count("\\") == original.count("\\")
    assert copy.plan_pair(*after) == after


@pytest.mark.parametrize("fault", ["missing", "duplicate", "unknown", "mixed"])
def test_refuses_ambiguous_or_concurrently_edited_content(fault: str) -> None:
    en, de = document("en"), document("de")
    if fault == "missing":
        en = en.replace('class="scene-card home-scene-card"', 'class="changed"')
    elif fault == "duplicate":
        de += de
    elif fault == "unknown":
        de = de.replace("<h4>Online bestellen", "<h4>Unreviewed")
    else:
        en = copy.plan_pair(en, de)[0]
    with pytest.raises(ValueError):
        copy.plan_pair(en, de)


def test_interrupted_success_receipt_cannot_truncate_prewrite_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise the application CLI through the post-commit receipt failure."""
    before: dict[str, Any] = {
        "home": "http://127.0.0.1:9410",
        "pages": {"13": document("en"), "6913": document("de")},
        "metadata": {"original": [r"keep\u003c"]},
        "current": False,
    }
    state = json.loads(json.dumps(before))
    called = False

    def read(_prefix: str, _en: int, _de: int) -> dict[str, Any]:
        answer: dict[str, Any] = json.loads(json.dumps(state))
        return answer

    def invoke(_prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal called
        called = True
        state["pages"] = {str(c["id"]): c["after"] for c in payload["changes"]}
        state["metadata"] = {"reviewed": [r"keep\u003c"]}
        state["current"] = True
        return {"expected_metadata": state["metadata"]}

    fake = ModuleType("reviewed_page_pair")
    monkeypatch.setattr(fake, "read", read, raising=False)
    monkeypatch.setattr(fake, "invoke", invoke, raising=False)
    monkeypatch.setitem(sys.modules, "reviewed_page_pair", fake)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "home-inquiry-copy.py",
            "--wp",
            "unused",
            "--evidence",
            str(tmp_path),
            "--write",
        ],
    )
    original_open = Path.open

    def interrupted_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.name.endswith(".result.json"):
            with original_open(path, *args, **kwargs) as handle:
                handle.write("{")
            raise OSError("Injected receipt interruption")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", interrupted_open)
    with pytest.raises(OSError, match="Injected receipt interruption"):
        copy.main()
    assert called
    assert state["pages"] != before["pages"]
    backups = [
        p
        for p in tmp_path.glob("home-copy-*.json")
        if not p.name.endswith(".result.json")
    ]
    assert len(backups) == 1
    recovered = json.loads(backups[0].read_text())
    assert recovered["before"] == before
    assert recovered["planned"][0]["before"] == before["pages"]["13"]
