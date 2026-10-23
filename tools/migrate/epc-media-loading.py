"""Plan the audited EPC media correction through the existing paired writer.

This module performs no WordPress writes. Apply its complete EN/DE result with
reviewed_page_pair, a verified recovery point, current pair/baseline preimage,
reviewed state digest and independent native readback.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from html import escape
from html.parser import HTMLParser
from pathlib import Path

CONTROLLER = Path(__file__).with_name("epc-media-controller.js").read_text()
OLD_CONTROLLER_SHA = "aaf74c0cd75526ace62ad3df97f097396c7066e83e1a81365511307cb3454462"
# Native getimagesize of the hosted snapshot originals, 2026-10-24. These are
# intrinsic file dimensions, not invented display sizes. The loaded originals
# also agree with the browser's naturalWidth/naturalHeight evidence.
IMAGE_SIZES = {
    "align-equipment-to-project-scope": (1600, 1000),
    "bess-quotation-and-order": (1600, 1000),
    "bess-system-sizing-and-architecture": (1672, 941),
    "containerized-bess-for-infrastructure": (2400, 1029),
    "engineering-backing-for-your-projects": (2048, 1152),
    "engineers-commission-storage-with-linker": (2400, 1600),
    "german-b2b-supply-and-warranty": (1672, 941),
    "grid-and-scada-documentation": (1600, 1100),
    "grid-documents-beside-the-hardware": (2560, 1440),
    "outdoor-cabinet-bess-for-ci": (2400, 1350),
    "product-support-after-delivery": (1600, 1000),
    "technical-files-for-planning-review": (1600, 1000),
}
IMAGE_DIMENSIONS = {
    f"/wp-content/uploads/2026/09/linker-{name}.webp": dimensions
    for name, dimensions in IMAGE_SIZES.items()
}
IMAGE_SOURCES = Counter(dict.fromkeys(IMAGE_DIMENSIONS, 1))
for repeated in (
    "german-b2b-supply-and-warranty",
    "technical-files-for-planning-review",
):
    IMAGE_SOURCES[f"/wp-content/uploads/2026/09/linker-{repeated}.webp"] += 1
VIDEO_NAMES = ("layout-for-planning", "sizing-for-the-site")
OLD_LOCALIZATION = """      if(source){source.setAttribute('src',de);}else{v.setAttribute('src',de);}
      var poster=v.getAttribute('data-poster-de');
      if(poster){v.setAttribute('poster',poster);}
      v.load();
      if(v.autoplay){var p=v.play();if(p){p.catch(function(){});}}"""
NEW_LOCALIZATION = """      var changed=source ? source.getAttribute('src')!==de : v.getAttribute('src')!==de;
      if(source){source.setAttribute('src',de);}else{v.setAttribute('src',de);}
      var poster=v.getAttribute('data-poster-de');
      if(poster){v.setAttribute('poster',poster);}
      if(changed){v.load();}
      // Playback belongs only to the visible-gallery lifecycle above."""
EPC_PREPARE = """    function prepareEpcImage(image,index) {
      if(config.key!=='epc')return;
      var original=items[index].querySelector(config.image);
      ['width','height','loading','decoding'].forEach(function(name){
        image.setAttribute(name,original.getAttribute(name));
      });
    }
"""


def _replace(content: str, before: str, after: str) -> str:
    if content.count(before) != 1:
        raise ValueError("Expected one exact audited block; no partial correction")
    return content.replace(before, after, 1)


def _attribute(raw: str, attrs: dict[str, str | None], name: str, value: str) -> str:
    if name in attrs:
        if attrs[name] != value:
            raise ValueError(f"Conflicting {name}; preserve the existing choice")
        return raw
    position = len(raw) - (2 if raw.endswith("/>") else 1)
    return raw[:position] + f' {name}="{escape(value, quote=True)}"' + raw[position:]


class EpcMedia(HTMLParser):
    """Edit only actual known tags; preserve text, URLs and every other byte."""

    def __init__(self, content: str, language: str, state: str) -> None:
        super().__init__(convert_charrefs=False)
        self.content, self.language, self.state = content, language, state
        self.lines = [0] + [i + 1 for i, c in enumerate(content) if c == "\n"]
        self.edits: list[tuple[int, int, str]] = []
        self.images: Counter[str] = Counter()
        self.videos = 0
        self.sources = 0
        self.video: str | None = None
        self.video_sources = 0
        self.heroes = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in {"img", "video", "source"}:
            return
        attributes = dict(attrs)
        if len(attributes) != len(attrs):
            raise ValueError("Ambiguous duplicate media attributes")
        raw = self.get_starttag_text()
        assert raw is not None
        original = raw
        if tag == "img":
            source = attributes.get("src")
            if source not in IMAGE_DIMENSIONS:
                raise ValueError("Unexpected EPC image; audit before changing")
            assert source is not None
            self.images[source] += 1
            width, height = IMAGE_DIMENSIONS[source]
            if "epc-cover-image" in (attributes.get("class") or "").split():
                self.heroes += 1
                if (
                    source
                    != "/wp-content/uploads/2026/09/linker-german-b2b-supply-and-warranty.webp"
                ):
                    raise ValueError("Hero image changed; do not defer it")
            if self.state == "old" and any(
                k in attributes for k in ("width", "height", "decoding")
            ):
                raise ValueError("Partially changed EPC image attributes")
            for name, value in (("width", str(width)), ("height", str(height))):
                raw = _attribute(raw, attributes, name, value)
            if "epc-cover-image" not in (attributes.get("class") or "").split():
                for name, value in (("loading", "lazy"), ("decoding", "async")):
                    raw = _attribute(raw, attributes, name, value)
        elif tag == "video":
            if self.video is not None or self.videos >= len(VIDEO_NAMES):
                raise ValueError("Unexpected EPC video structure")
            name = VIDEO_NAMES[self.videos]
            self.video = name
            self.video_sources = 0
            self.videos += 1
            prefix = f"/wp-content/uploads/2026/09/linker-bess-{name}"
            if (
                attributes.get("data-src-de") != prefix + "-de.mp4"
                or attributes.get("data-poster-de") != prefix + "-de-poster.webp"
            ):
                raise ValueError("Unexpected native German media mapping")
            expected_language = "en" if self.state == "old" else self.language
            if attributes.get("poster") != prefix + f"-{expected_language}-poster.webp":
                raise ValueError("Video poster drifted from the reviewed state")
            if self.state == "old":
                if attributes.get("preload") != "auto" or "autoplay" not in attributes:
                    raise ValueError("Partially changed native video policy")
                raw = _replace(raw, ' autoplay=""', "")
                raw = _replace(raw, 'preload="auto"', 'preload="none"')
                if self.language == "de":
                    raw = _replace(
                        raw,
                        f'poster="{prefix}-en-poster.webp"',
                        f'poster="{prefix}-de-poster.webp"',
                    )
            elif attributes.get("preload") != "none" or "autoplay" in attributes:
                raise ValueError("Final native video policy changed")
        else:
            if self.video is None:
                raise ValueError("Unexpected source outside the audited videos")
            self.sources += 1
            self.video_sources += 1
            prefix = f"/wp-content/uploads/2026/09/linker-bess-{self.video}"
            expected_language = "en" if self.state == "old" else self.language
            if attributes.get("src") != prefix + f"-{expected_language}.mp4":
                raise ValueError("Video source drifted from the reviewed state")
            if self.state == "old" and self.language == "de":
                raw = _replace(raw, f'src="{prefix}-en.mp4"', f'src="{prefix}-de.mp4"')
        if raw != original:
            line, column = self.getpos()
            start = self.lines[line - 1] + column
            self.edits.append((start, start + len(original), raw))

    def handle_endtag(self, tag: str) -> None:
        if tag == "video":
            if self.video is None or self.video_sources != 1:
                raise ValueError("Expected one source in each native video")
            self.video = None

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _pagination(language: str) -> str:
    pause, play, label = (
        ("Pause slideshow", "Play slideshow", "Planning tools")
        if language == "en"
        else ("Diashow pausieren", "Diashow abspielen", "Planungswerkzeuge")
    )
    parts = [
        '<div class="lk-sp-pagination">',
        f'<div class="epc-media-tabs" role="tablist" aria-label="{label}" hidden>',
    ]
    for i in range(3):
        active = " active" if i == 0 else ""
        selected = "true" if i == 0 else "false"
        tab = "0" if i == 0 else "-1"
        parts.append(
            f'<button class="lk-sp-bar{active}" id="epc-media-tab-{i}" type="button" role="tab" aria-controls="sp-pane-{i}" aria-labelledby="epc-media-title-{i}" aria-selected="{selected}" tabindex="{tab}" disabled><span class="lk-sp-bar-fill"></span></button>'
        )
    parts.extend(
        [
            "</div>",
            f'<button class="epc-motion-toggle" type="button" aria-label="{pause}" data-pause-label="{pause}" data-play-label="{play}" hidden><svg class="epc-motion-pause" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5v14M15 5v14"/></svg><svg class="epc-motion-play" viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7Z"/></svg></button>',
            '<span class="lk-sp-page-count" id="sp-counter" hidden>1 / 3</span>',
            "</div>",
        ]
    )
    return "\n".join(parts)


def _plan(content: str, language: str) -> tuple[str, str]:
    if (
        content.count('id="tv-solutions-developers-v1"') != 1
        or content.count('id="sp-workbench"') != 1
    ):
        raise ValueError("Expected the audited EPC page and workbench")
    start = content.find("      // 2. ")
    end = content.find("      // 3. Horizontal project", start)
    if start < 0 or end < 0:
        raise ValueError("Audited media controller boundary changed")
    current = content[start:end]
    if current == CONTROLLER:
        state = "final"
    elif hashlib.sha256(current.encode()).hexdigest() == OLD_CONTROLLER_SHA:
        state = "old"
    else:
        raise ValueError("Media controller changed; inspect before retrying")
    parser = EpcMedia(content, language, state)
    parser.feed(content)
    parser.close()
    if (
        parser.images != IMAGE_SOURCES
        or parser.videos != 2
        or parser.sources != 2
        or parser.heroes != 1
        or parser.video is not None
    ):
        raise ValueError("EPC media set changed; refusing a partial correction")
    for start_tag, end_tag, replacement in reversed(parser.edits):
        content = content[:start_tag] + replacement + content[end_tag:]
    if state == "final":
        if (
            parser.edits
            or _pagination(language) not in content
            or content.count(EPC_PREPARE) != 1
            or content.count(NEW_LOCALIZATION) != 1
        ):
            raise ValueError("Final EPC pair is incomplete")
        required = [
            "prepareEpcImage(photo,0); photo.src = photos[0];",
            "prepareEpcImage(thumbnail,i); thumbnail.src = photos[i];",
            "prepareEpcImage(photo,index); photo.src = photos[index];",
            "prepareEpcImage(photo,i);photo.src=photos[i];buttons.forEach",
        ]
        required.extend(
            f'<h2 class="lk-sp-h2" id="epc-media-title-{i}">' for i in range(3)
        )
        if any(content.count(marker) != 1 for marker in required):
            raise ValueError("Final EPC controls or derived images are incomplete")
        return content, state
    content = _replace(content, current, CONTROLLER)
    old_pagination = (
        '<div class="lk-sp-pagination">\n'
        + "\n".join(
            f'<div class="lk-sp-bar{" active" if i == 0 else ""}" data-index="{i}"><div class="lk-sp-bar-fill"></div></div>'
            for i in range(3)
        )
        + '\n<span class="lk-sp-page-count" id="sp-counter">1 / 3</span>\n</div>'
    )
    content = _replace(content, old_pagination, _pagination(language))
    for i in range(3):
        content = _replace(
            content,
            f'<div class="lk-sp-pane{" active" if i == 0 else ""}" id="sp-pane-{i}">',
            f'<div class="lk-sp-pane{" active" if i == 0 else ""}" id="sp-pane-{i}" role="tabpanel" aria-labelledby="epc-media-tab-{i}">',
        )
        pane_start = content.index(f'id="sp-pane-{i}"')
        heading = content.index('<h2 class="lk-sp-h2">', pane_start)
        content = content[:heading] + content[heading:].replace(
            '<h2 class="lk-sp-h2">',
            f'<h2 class="lk-sp-h2" id="epc-media-title-{i}">',
            1,
        )
    content = _replace(content, OLD_LOCALIZATION, NEW_LOCALIZATION)
    content = _replace(
        content,
        "    var visual = document.createElement('div');",
        EPC_PREPARE + "    var visual = document.createElement('div');",
    )
    for old, new in (
        (
            "photo.alt = ''; photo.src = photos[0];",
            "photo.alt = ''; prepareEpcImage(photo,0); photo.src = photos[0];",
        ),
        (
            "thumbnail.alt = ''; thumbnail.src = photos[i];",
            "thumbnail.alt = ''; prepareEpcImage(thumbnail,i); thumbnail.src = photos[i];",
        ),
        (
            "      photo.src = photos[index];",
            "      prepareEpcImage(photo,index); photo.src = photos[index];",
        ),
        (
            "});photo.src=photos[i];buttons.forEach",
            "});prepareEpcImage(photo,i);photo.src=photos[i];buttons.forEach",
        ),
    ):
        content = _replace(content, old, new)
    return content, state


def plan_pair(english: str, german: str) -> tuple[str, str]:
    """Accept complete old or final native pairs; refuse mixed/partial states."""
    en, en_state = _plan(english, "en")
    de, de_state = _plan(german, "de")
    if en_state != de_state:
        raise ValueError("Partially changed EPC language pair")
    return en, de
