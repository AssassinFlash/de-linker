"""The `linker/read-page` tool: what the page the customer is on says (#234).

Every turn carries the page (`schema.PageContext`: type, address, title and the IDs of
what it shows). This module reads that page's content for the answer when Jev says the
message is about the page (understand.py), or when the model asks for it.

The source is the page itself, read the way an anonymous visitor reads it: a GET of
the page's own path on the site, its `<main>` element turned into text. WordPress's
REST content (`/wp/v2/pages/<id>`) is not what the visitor sees on the pages that
LiveCanvas renders through a dynamic template: on 2026-10-18 the FAQ page's REST
content was an older page body with unrendered shortcodes, while
the page shows 244 questions and 159 documents; the shop, the product categories, the
solution draft, the account and the blog index have no post content at all
(docs/specs/13-genie.md, 页面感知). A generated content pack would have to be rebuilt
and deployed on every edit and every German translation. The page read needs no code
on the WordPress side (AGENTS.md §5: native mechanisms first) and is cached for
`TTL_SECONDS`.

The address is never fetched as the browser sent it: only its path is taken, joined to
the site this service serves (`GENIE_WP_URL`), and a redirect is followed only on that
site. Pages that show the customer's own data are not read this way, since an anonymous
read would not see them: the solution draft is the draft's products, which the shell
puts in the page context (`draft_ids`); a signed-in customer's account is their
inquiries, which the route reads with inquiry-status (route.py).

The model reads the page's passages most related to the question, with every figure
tagged as `[nK=VALUE]` the way a document chunk's are (`figures.tag`): it cites a figure
as `{fact:page.nK}` and the page as the ref `page`, and hydration writes the value.

A page that cannot be read raises `PageUnavailable`; the caller logs it on the turn
(understand.py), and the answer goes on without it — the model is told it has no page
text and must not guess (route.PAGE_HINT).
"""

from __future__ import annotations

import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx

from linker_genie import facts
from linker_genie.facts import TurnFacts
from linker_genie.figures import tag
from linker_genie.schema import PageContext

NAME = "linker/read-page"
# The input the model is told about (agent.INPUT_DOCS): the page is the turn's own.
INPUT_DOC = "{} — no input: reads the page the customer is on (this turn's page)"
# The ref an answer cites the page by, and the prefix of the page's figures (page.nK).
REF = "page"

# Pages change when staff edit them and when the German auto-translation syncs; ten
# minutes is the vocabulary's starting value too (storeapi.TTL_SECONDS), and one read
# is one page view of the site.
TTL_SECONDS = 600.0
# Pages kept in the cache: the site has 25 pages per language, a few blog posts, 16
# product categories and 106 products (snapshot 2026-10-18); 256 holds the pages
# customers ask from without growing without bound.
CACHE_SIZE = 256
# One page view is a full LiveCanvas render: 0.5–3.4 s on the local instance
# (2026-10-18: home 0.49 s, product category 3.39 s). Ten seconds keeps a slow page
# from holding the turn past the shell's 60 s proxy.
TIMEOUT_SECONDS = 10.0
# Same-site redirects followed (a trailing slash, a language prefix).
MAX_REDIRECTS = 3
# What the model reads of one page, measured on the live snapshot 2026-10-18 (text of
# <main>): home 7,300 characters, product category 8,400, residential storage 10,400,
# the FAQ and documents page 118,000. Twelve thousand (about three thousand tokens)
# holds every page but the FAQ whole; there the passages most related to the question
# are chosen (`select`).
PAGE_CHARS = 12_000
# The opening of the page always comes first, so the answer knows what the page is
# about: about the hero and the first section of the pages above.
LEAD_CHARS = 1_500
# A passage is cut at a heading or at this length: one FAQ answer or one section's
# paragraph, small enough that a long page gives the question's passages room.
PASSAGE_CHARS = 700
# A block this long or longer is a sentence, kept once; a shorter one is a label
# that each product card of a category page repeats ("MPPT trackers", 13 characters;
# the longest card label on the inverter category, "Nominal AC voltage L/N/PE", has
# 25), kept every time.
REPEAT_CHARS = 40
# Headings listed so the model knows what else the page has (the FAQ page has 31
# section headings, measured 2026-10-18).
OUTLINE_ITEMS = 40
# Products of a solution draft the reader names (Store API `include`, one request).
DRAFT_ITEMS = 50
# Paths that are no page for a visitor: the admin, the REST API, the login, the feeds.
_NOT_PAGES = re.compile(r"^/(?:wp-admin|wp-json|wp-login\.php|xmlrpc\.php)|/feed/?$")

# Words a question about the page says that do not tell which passage it means.
_STOPWORDS = frozenset(
    """
    about also and are can could does for from have here how into its mean means
    meant page please says say tell than that the their them then there these this
    those what when where which who why will with would you your one ones post
    aber auch auf bedeutet bedeuten bitte das dass dem den der des die dies diese
    diesem diesen dieser dieses ein eine einem einen einer eines für gibt hier ich
    ist mit seite steht und von was welche welchen welcher welches wie wird wir zum
    zur sie ihr ihre meint gemeint beitrag artikel
    """.split()
)
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_QUOTED = re.compile(r"[\"“”„‚‘’'«»]([^\"“”„‚‘’'«»]{3,80})[\"“”„‚‘’'«»]")


class PageUnavailable(RuntimeError):
    """The page could not be read; the message names the cause."""


@dataclass(frozen=True)
class Passage:
    """A run of the page's text under its nearest heading."""

    heading: str
    text: str
    is_heading: bool = False


class _MainText(HTMLParser):
    """The text of the page's `<main>`, cut into passages at block elements.

    Hidden elements (`hidden`, `aria-hidden="true"`) and what is not text (scripts,
    styles, SVG, form selects) are left out; comments are dropped by the parser.
    """

    _SKIP = frozenset(
        {"script", "style", "noscript", "template", "svg", "select", "textarea"}
    )
    _VOID = frozenset(
        {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
         "source", "track", "wbr"}
    )  # fmt: skip
    _BLOCK = frozenset(
        {"address", "article", "aside", "blockquote", "br", "dd", "details", "div",
         "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
         "h3", "h4", "h5", "h6", "header", "hr", "label", "li", "main", "nav", "ol",
         "p", "section", "summary", "table", "td", "th", "tr", "ul", "button"}
    )  # fmt: skip
    _HEADINGS = frozenset({"h1", "h2", "h3", "h4"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, bool]] = []
        self._main_depth = 0
        self._skip_depth = 0
        self._stack: list[tuple[str, bool]] = []
        self._buffer: list[str] = []
        self._heading = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._VOID:
            if tag == "br" and self._main_depth:
                self._flush()
            return
        values = dict(attrs)
        hidden = (
            "hidden" in values
            or values.get("aria-hidden") == "true"
            or tag in self._SKIP
        )
        self._stack.append((tag, hidden))
        if hidden:
            self._skip_depth += 1
        if tag == "main":
            self._main_depth += 1
        if tag in self._BLOCK:
            self._flush()
        if tag in self._HEADINGS:
            self._heading += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._VOID or not any(name == tag for name, _ in self._stack):
            return
        while self._stack:
            name, hidden = self._stack.pop()
            if tag in self._BLOCK or name in self._BLOCK:
                self._flush()
            if hidden:
                self._skip_depth -= 1
            if name == "main":
                self._main_depth -= 1
            if name in self._HEADINGS:
                self._heading = max(0, self._heading - 1)
            if name == tag:
                break

    def handle_data(self, data: str) -> None:
        if self._main_depth and not self._skip_depth:
            self._buffer.append(data)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        text = " ".join("".join(self._buffer).split())
        self._buffer = []
        if text:
            self.blocks.append((text, self._heading > 0))


def passages(html: str) -> list[Passage]:
    """The page's text in passages, in page order, each repeated block kept once.

    The live pages print some blocks twice (a hero for wide and for narrow screens);
    the repeat says nothing new. A short block is kept every time: it is a label
    each product card repeats ("Rated AC power", "MPPT trackers"), and its value
    means nothing without it.
    """
    parser = _MainText()
    parser.feed(html)
    parser.close()
    found: list[Passage] = []
    seen: set[str] = set()
    heading = ""
    current: list[str] = []

    def close() -> None:
        if current:
            found.append(Passage(heading, " ".join(current)))
            current.clear()

    for text, is_heading in parser.blocks:
        if len(text) >= REPEAT_CHARS:
            if text in seen:
                continue
            seen.add(text)
        if is_heading:
            close()
            heading = text
            found.append(Passage(heading, text, is_heading=True))
            continue
        if current and len(" ".join(current)) + len(text) > PASSAGE_CHARS:
            close()
        current.append(text)
    close()
    return found


def _terms(question: str) -> tuple[set[str], list[str]]:
    """The question's telling words (lower case) and its quoted phrases."""
    words = {
        word.lower()
        for word in _WORD.findall(question)
        if len(word) >= 3 and word.lower() not in _STOPWORDS
    }
    phrases = [phrase.strip().lower() for phrase in _QUOTED.findall(question)]
    return words, phrases


def _score(passage: Passage, words: set[str], phrases: list[str]) -> int:
    text = f"{passage.heading} {passage.text}".lower()
    found = sum(1 for word in words if word in text)
    return found + sum(2 for phrase in phrases if phrase in text)


def select(
    found: list[Passage], question: str, budget: int = PAGE_CHARS
) -> list[Passage]:
    """The page's opening and the passages most related to the question, in page order.

    The opening (`LEAD_CHARS`) always stays. The rest is ranked by how many of the
    question's telling words a passage (with its heading) contains, a quoted phrase
    counting double; a passage that shares no word is taken only when the page fits
    the budget anyway. Ties keep page order.
    """
    if sum(len(p.text) for p in found) <= budget:
        return list(found)
    chosen: set[int] = set()
    used = 0
    for index, passage in enumerate(found):
        if used >= LEAD_CHARS:
            break
        chosen.add(index)
        used += len(passage.text)
    words, phrases = _terms(question)
    ranked = sorted(
        (
            (score, index)
            for index, passage in enumerate(found)
            if index not in chosen
            and (score := _score(passage, words, phrases)) > 0
            and not passage.is_heading
        ),
        key=lambda item: (-item[0], item[1]),
    )
    for _score_value, index in ranked:
        size = len(found[index].text)
        if used + size > budget:
            continue
        chosen.add(index)
        used += size
    return [found[index] for index in sorted(chosen)]


def render(chosen: list[Passage]) -> str:
    """The chosen passages as the model reads them: headings marked, one per line."""
    lines: list[str] = []
    heading = None
    for passage in chosen:
        if passage.is_heading:
            lines.append(f"## {passage.text}")
            heading = passage.text
            continue
        if passage.heading and passage.heading != heading:
            lines.append(f"## {passage.heading}")
            heading = passage.heading
        lines.append(passage.text)
    return "\n".join(lines)


def page_path(url: str | None) -> str | None:
    """The path of a page address, or None when it is no page of a site."""
    if not url:
        return None
    path = urlsplit(url).path or "/"
    if not path.startswith("/") or path.startswith("//") or _NOT_PAGES.search(path):
        return None
    return path


class PageReader:
    """Reads a page of the site this service serves; `read()` returns the tool result."""

    def __init__(
        self,
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        ttl: float = TTL_SECONDS,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._host = urlsplit(self._base).netloc
        self._client = httpx.Client(
            base_url=self._base,
            headers={"Accept": "text/html,application/json"},
            timeout=TIMEOUT_SECONDS,
            transport=transport,
            follow_redirects=False,
        )
        self._clock = clock
        self._ttl = ttl
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def close(self) -> None:
        self._client.close()

    def read(self, page: PageContext, question: str, logged_in: bool) -> dict[str, Any]:
        """The page's content for `question`: its passages, or a draft's products.

        Raises `PageUnavailable` when the page cannot be read.
        """
        result: dict[str, Any] = {"type": page.type, "title": page.title or ""}
        if page.type == "draft":
            result["products"] = self._draft(page.draft_ids or [])
            return result
        if page.type == "account" and logged_in:
            # Anonymous, the account page is the sign-in form; the customer's own
            # account is their inquiries (route.py reads them with inquiry-status).
            result["note"] = (
                "The signed-in customer's account: their inquiries come from "
                "inquiry-status."
            )
            return result
        path = page_path(page.url)
        if path is None:
            raise PageUnavailable(f"no page address to read: {page.url!r}")
        found = self._cached(f"page:{path}", lambda: passages(self._html(path)))
        if not found:
            raise PageUnavailable(f"page {path} shows no text in <main>")
        chosen = select(found, question)
        tagged = tag(REF, render(chosen))
        result.update(
            {
                "url": path,
                "outline": [p.text for p in found if p.is_heading][:OUTLINE_ITEMS],
                "text": tagged.text,
                "figures": tagged.figures,
                "complete": len(chosen) == len(found),
            }
        )
        return result

    def _cached(self, key: str, load: Callable[[], Any]) -> Any:
        with self._lock:
            now = self._clock()
            hit = self._cache.get(key)
            if hit is not None and now - hit[0] < self._ttl:
                self._cache.move_to_end(key)
                return hit[1]
        value = load()
        with self._lock:
            self._cache[key] = (self._clock(), value)
            self._cache.move_to_end(key)
            while len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
        return value

    def _html(self, path: str) -> str:
        target = path
        for _hop in range(MAX_REDIRECTS + 1):
            try:
                response = self._client.get(target)
            except httpx.TransportError as error:
                raise PageUnavailable(f"page {path}: {type(error).__name__}") from error
            if response.is_redirect:
                location = urljoin(self._base + target, response.headers["location"])
                parts = urlsplit(location)
                if parts.netloc != self._host:
                    raise PageUnavailable(f"page {path} redirects off the site")
                target = parts.path or "/"
                continue
            if response.status_code >= 400:
                raise PageUnavailable(f"page {path} returned {response.status_code}")
            return response.text
        raise PageUnavailable(f"page {path} redirects more than {MAX_REDIRECTS} times")

    def _draft(self, ids: list[int]) -> list[dict[str, Any]]:
        """The draft's products by name, from WooCommerce's Store API."""
        wanted = [pid for pid in dict.fromkeys(ids) if pid > 0][:DRAFT_ITEMS]
        if not wanted:
            return []
        key = "draft:" + ",".join(str(pid) for pid in sorted(wanted))
        names = self._cached(key, lambda: self._names(wanted))
        return [
            {"product_id": pid, "title": names[pid]} for pid in wanted if pid in names
        ]

    def _names(self, ids: list[int]) -> dict[int, str]:
        try:
            response = self._client.get(
                "/wp-json/wc/store/v1/products",
                params={
                    "include": ",".join(str(pid) for pid in ids),
                    "per_page": len(ids),
                },
            )
        except httpx.TransportError as error:
            raise PageUnavailable(f"draft products: {type(error).__name__}") from error
        if response.status_code >= 400:
            raise PageUnavailable(f"draft products returned {response.status_code}")
        body = response.json()
        if not isinstance(body, list):
            raise PageUnavailable("draft products: the Store API did not return a list")
        return {
            int(item["id"]): str(item.get("name") or "")
            for item in body
            if isinstance(item, dict) and isinstance(item.get("id"), int)
        }


Reader = Callable[[PageContext, str, bool], dict[str, Any]]


def record(
    reader: Reader, page: PageContext, question: str, logged_in: bool
) -> tuple[dict[str, Any], TurnFacts]:
    """Read the page and collect its facts, the call logged with its result.

    The one way a turn runs this tool, from the route (understand.py) or the model
    (agent.py), as `knowledge.record` is for the document search.
    """
    payload = reader(page, question, logged_in)
    gathered = collect(payload)
    gathered.tool_calls.append(
        {"name": NAME, "arguments": {}, "ok": True, "result": payload}
    )
    return payload, gathered


def collect(payload: dict[str, Any]) -> TurnFacts:
    """The page as facts (`facts.collect`, which the quality check also rebuilds from
    the turn log): the ref `page`, its text, its figures, a draft's products."""
    return facts.collect(NAME, payload)


def model_view(payload: dict[str, Any]) -> dict[str, Any]:
    """The result as the model reads it: tagged text, no figure table."""
    return {key: value for key, value in payload.items() if key != "figures"}
