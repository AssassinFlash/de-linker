"""Exercise the real EN/DE media shape and refuse partial or unsafe drift."""

import importlib.util
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "epc_media_loading", Path(__file__).parents[1] / "epc-media-loading.py"
)
assert spec and spec.loader
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)
FIXTURES = Path(__file__).parent / "fixtures" / "epc-media"
OLD = tuple((FIXTURES / f"old-{lang}.html").read_text() for lang in ("en", "de"))
UNCHANGED = r"""<p>Preserve C:\project\files and quoted \u003csvg markers.</p>
<script>const originalSvg='\u003csvg>'; const originalWords=/\s+/g;</script>"""


class Snapshot(HTMLParser):
    def __init__(self, content: str) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []
        self.excluded: list[str] = []
        self.feed(content)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))
        if tag in {"script", "style"}:
            self.excluded.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.excluded and self.excluded[-1] == tag:
            self.excluded.pop()

    def handle_data(self, text: str) -> None:
        if not self.excluded and text.strip():
            self.text.append(" ".join(text.split()))


def replace_one(content: str, before: str, after: str) -> str:
    assert content.count(before) == 1
    return content.replace(before, after, 1)


def test_complete_pair_preserves_customer_content_and_has_native_media_policy() -> None:
    before = tuple(content + UNCHANGED for content in OLD)
    final = media.plan_pair(*before)
    assert media.plan_pair(*final) == final
    for language, old, new in zip(("en", "de"), before, final, strict=True):
        a, b = Snapshot(old), Snapshot(new)
        assert a.text == b.text
        assert [attrs for tag, attrs in a.tags if tag == "a"] == [
            attrs for tag, attrs in b.tags if tag == "a"
        ]
        assert UNCHANGED in new
        assert new.count("\\") == old.count("\\") > 0
        images = [attrs for tag, attrs in b.tags if tag == "img"]
        assert len(images) == 14
        hero = [a for a in images if a.get("class") == "epc-cover-image"]
        assert len(hero) == 1 and hero[0]["fetchpriority"] == "high"
        assert hero[0].get("loading") != "lazy"
        assert all(
            int(a.get("width") or "0") > 0 and int(a.get("height") or "0") > 0
            for a in images
        )
        assert sum(a.get("loading") == "lazy" for a in images) == 13
        videos = [attrs for tag, attrs in b.tags if tag == "video"]
        assert len(videos) == 2
        assert all(
            all(
                a.get(flag) == ""
                for flag in ("muted", "loop", "playsinline", "controls")
            )
            and a.get("preload") == "none"
            and "autoplay" not in a
            and f"-{language}-poster.webp" in (a.get("poster") or "")
            for a in videos
        )
        sources = [attrs for tag, attrs in b.tags if tag == "source"]
        assert len(sources) == 2
        assert all((a.get("src") or "").endswith(f"-{language}.mp4") for a in sources)
        tabs = [
            a
            for tag, a in b.tags
            if tag == "button" and (a.get("class") or "").startswith("lk-sp-bar")
        ]
        assert len(tabs) == 3
        assert [a["aria-controls"] for a in tabs] == [f"sp-pane-{i}" for i in range(3)]


@pytest.mark.parametrize("side", (0, 1))
def test_mixed_language_state_is_rejected(side: int) -> None:
    final = media.plan_pair(*OLD)
    mixed = list(OLD)
    mixed[side] = final[side]
    with pytest.raises(ValueError, match="Partially changed"):
        media.plan_pair(*mixed)


@pytest.mark.parametrize("state", ("old", "final"))
@pytest.mark.parametrize(
    ("old_side", "before", "after"),
    (
        (0, ' muted=""', ""),
        (1, ' loop=""', ""),
        (0, ' playsinline=""', ""),
        (1, 'fetchpriority="high"', 'fetchpriority="low"'),
        (0, 'type="video/mp4"', 'type="application/octet-stream"'),
        (1, "linker-bess-layout-for-planning-en.mp4", "wrong-source.mp4"),
    ),
)
def test_native_media_policy_drift_is_rejected(
    old_side: int, state: str, before: str, after: str
) -> None:
    # The parser is shared. Exercise each rejection on old and final inputs,
    # alternating the language instead of repeating the full Cartesian product.
    side = old_side if state == "old" else 1 - old_side
    pair = list(OLD if state == "old" else media.plan_pair(*OLD))
    if state == "final" and side == 1 and before.endswith("-en.mp4"):
        before = before.replace("-en.mp4", "-de.mp4")
    assert before in pair[side]
    pair[side] = pair[side].replace(before, after, 1)
    with pytest.raises(ValueError):
        media.plan_pair(*pair)


@pytest.mark.parametrize("state", ("old", "final"))
@pytest.mark.parametrize(
    ("old_side", "mutation"),
    (
        (0, "pager"),
        (1, "extra-bar"),
        (0, "duplicate-id"),
        (1, "extra-pane"),
        (0, "duplicate-attribute"),
    ),
)
def test_controls_must_produce_one_complete_three_pane_workbench(
    old_side: int, state: str, mutation: str
) -> None:
    side = old_side if state == "old" else 1 - old_side
    final = list(OLD if state == "old" else media.plan_pair(*OLD))
    if mutation == "pager":
        if state == "final":
            pager = media._pagination(("en", "de")[side])
        else:
            start = final[side].index('<div class="lk-sp-pagination">')
            counter = final[side].index('id="sp-counter"', start)
            end = final[side].index("</div>", counter) + len("</div>")
            pager = final[side][start:end]
        final[side] = replace_one(final[side], pager, pager + pager)
    elif mutation == "extra-bar":
        start = final[side].index('id="sp-workbench"')
        end = final[side].index(">", start) + 1
        extra = '<button class="lk-sp-bar" type="button"><span class="lk-sp-bar-fill"></span></button>'
        final[side] = final[side][:end] + extra + final[side][end:]
    elif mutation == "duplicate-id":
        final[side] += '<span id="sp-counter"></span>'
    elif mutation == "extra-pane":
        final[side] += '<div class="lk-sp-pane"></div>'
    else:
        final[side] = replace_one(
            final[side],
            'id="sp-workbench"',
            'id="sp-workbench" id="other-workbench"',
        )
    with pytest.raises(ValueError):
        media.plan_pair(*final)


@pytest.mark.parametrize("side", (0, 1))
def test_partial_image_edits_and_unrecognized_controller_are_rejected(
    side: int,
) -> None:
    for old, new in (
        ('fetchpriority="high"', 'fetchpriority="high" width="1672"'),
        ("      // 2. ", "      // changed 2. "),
        ("linker-grid-and-scada-documentation.webp", "unknown-image.webp"),
    ):
        pair = list(OLD)
        assert old in pair[side]
        pair[side] = pair[side].replace(old, new, 1)
        with pytest.raises(ValueError):
            media.plan_pair(*pair)


def test_shared_photo_helper_leaves_about_and_services_untouched() -> None:
    # Execute the actual inserted helper. Non-EPC consumers must return before
    # reading EPC items or writing sizing/loading attributes to their images.
    program = r"""
const assert = require('node:assert/strict');
const helper = JSON.parse(process.argv[1]);
const execute = new Function('config','items','image','index',
  helper + '\n prepareEpcImage(image,index);');
for (const key of ['about','services']) {
  execute({key},new Proxy([],{get(){throw Error('read non-EPC items')}}),
    {setAttribute(){throw Error('mutated non-EPC image')}},0);
}
const attrs = {width:'1600',height:'1000',loading:'lazy',decoding:'async'};
const copied = {};
execute({key:'epc',image:'.photo'},[{querySelector(selector){
  assert.equal(selector,'.photo');return {getAttribute(name){return attrs[name]}};
}}],{setAttribute(name,value){copied[name]=value}},0);
assert.deepEqual(copied,attrs);
"""
    result = subprocess.run(
        ["node", "-e", program, json.dumps(media.EPC_PREPARE)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
