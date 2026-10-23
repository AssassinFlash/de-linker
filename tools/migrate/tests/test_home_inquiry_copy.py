"""A content-only repair must preserve scripts, quotes and unrelated occurrences."""

import importlib.util
from pathlib import Path

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
