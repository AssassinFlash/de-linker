"""Plan responsive sources for the three existing bilingual Home story photos.

This module only transforms page content. Apply the pair using the existing
reviewed-page writer after checking the image files and retaining a preimage.
"""

from collections import Counter
from html.parser import HTMLParser

ROOT = "/wp-content/uploads/2026/09/linker-"
# The saved Home CSS uses 4:3 story media up to 767px. Limit this pass to the
# narrower <=600px range: the approximately 3:2 source needs about 1.13 times
# the card width under object-fit:cover, so 120vw leaves room for that crop.
# 2400px is the largest original width and selects each original on wider
# layouts at DPR >= 1, where the tall desktop crop needs more source pixels.
SIZES = "(max-width: 600px) 120vw, 2400px"
# All candidates preserve their original aspect ratios. The first two smaller
# sizes still cover a 4:3 phone card at the relevant device pixel densities.
SOURCES = {
    "installers": ("2048", "1360", ("768x510", "1024x680", "1536x1020")),
    "contractors": ("2400", "1600", ("768x512", "1536x1024")),
    "grid-projects": ("2048", "1360", ("768x510", "1024x680", "1536x1020")),
}


def _insertion(name: str) -> str:
    width, _, variants = SOURCES[name]
    path = f"{ROOT}{name}-buy-through-linker"
    candidates = [f"{path}-{size}.webp {size.split('x')[0]}w" for size in variants]
    candidates.append(f"{path}.webp {width}w")
    return f' srcset="{", ".join(candidates)}" sizes="{SIZES}"'


INSERTIONS = {name: _insertion(name) for name in SOURCES}
PATHS = {f"{ROOT}{name}-buy-through-linker.webp": name for name in SOURCES}
STORY_IDS = dict(zip(SOURCES, ("story-0", "story-1", "story-2"), strict=True))


class _Photos(HTMLParser):
    def __init__(self, content: str) -> None:
        super().__init__(convert_charrefs=False)
        self.line_starts = [0]
        self.line_starts.extend(i + 1 for i, c in enumerate(content) if c == "\n")
        self.section_depth = 0
        self.story: str | None = None
        self.sections = 0
        self.seen: Counter[str] = Counter()
        self.states: list[str] = []
        self.edits: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "section":
            if self.section_depth:
                self.section_depth += 1
            elif ("id", "testimonials") in attrs:
                self.section_depth = 1
                self.sections += 1
        if tag == "article" and self.section_depth:
            if self.story is not None:
                raise ValueError("Nested story; refusing ambiguous markup")
            self.story = dict(attrs).get("id")
        if tag != "img":
            return
        candidates = [value for key, value in attrs if key == "src" and value in PATHS]
        if not candidates:
            return
        attributes = dict(attrs)
        if len(attributes) != len(attrs) or len(candidates) != 1:
            raise ValueError("Duplicate image attributes")
        name = PATHS[candidates[0]]
        if not self.section_depth or self.story != STORY_IDS[name]:
            raise ValueError("Story image is outside its expected card")
        self.seen[name] += 1
        width, height, _ = SOURCES[name]
        required = {
            "loading": "eager",
            "decoding": "async",
            "fetchpriority": "low",
            "width": width,
            "height": height,
        }
        if any(attributes.get(key) != value for key, value in required.items()):
            raise ValueError("Existing image loading or dimensions changed")
        inserted = INSERTIONS[name]
        srcset = inserted.split(' srcset="', 1)[1].split('" sizes=', 1)[0]
        if "srcset" in attributes or "sizes" in attributes:
            if attributes.get("srcset") != srcset or attributes.get("sizes") != SIZES:
                raise ValueError("Conflicting responsive source")
            self.states.append("final")
            return
        self.states.append("original")
        raw = self.get_starttag_text()
        if raw is None:
            raise ValueError("Image tag is unavailable")
        line, column = self.getpos()
        end = len(raw) - (2 if raw.endswith("/>") else 1)
        self.edits.append((self.line_starts[line - 1] + column + end, inserted))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "article" and self.section_depth:
            self.story = None
        if tag == "section" and self.section_depth:
            self.section_depth -= 1


def plan(content: str) -> str:
    """Add only the two native image attributes; refuse partial or drifting inputs."""
    parser = _Photos(content)
    parser.feed(content)
    parser.close()
    if parser.sections != 1 or parser.seen != Counter(dict.fromkeys(SOURCES, 1)):
        raise ValueError("Expected exactly the three audited story photos")
    if len(set(parser.states)) != 1:
        raise ValueError("Story images are only partially updated")
    result = content
    for position, insertion in reversed(parser.edits):
        result = result[:position] + insertion + result[position:]
    return result


def plan_pair(en: str, de: str) -> tuple[str, str]:
    """Keep the two native language pages in the same original/final state."""
    output = (plan(en), plan(de))
    if (output[0] == en) != (output[1] == de):
        raise ValueError("Home language pair is only partially updated")
    return output
