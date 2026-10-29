#!/usr/bin/env python3
"""Audit cached sitemap pages without recrawling their internal-link graph.

The input is the compact JSON produced by the URL/SEO sweep, plus one or more
existing curl caches for hreflang counterparts. Checks:

* sitemap page status, final URL, canonical and indexability;
* explicit EN/DE indexability symmetry;
* structured data required by indexable customer page type;
* page-node JSON-LD URLs that do not state their own URL;
* JSON-LD parse failures.

Generic marketing, legal, account and noindex pages are not required to carry
schema. That distinction is intentional: "no JSON-LD" alone is not a defect.

Usage:
    python3 tools/checks/seo-audit.py \
        --parsed /tmp/de-linker-seo-parsed.json \
        --cache /tmp/de-linker-internal-extra.txt=/tmp/de-linker-internal-cache.Jc8X76

Cache arguments are URL-list=directory pairs. Each directory has the sweep's
`N.body`, `N.headers` and `N.meta` files. No network request is made.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

LD_JSON = re.compile(
    r"<script[^>]*type=[\"']?application/ld\+json[\"']?[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True)
class Page:
    """The fields of one cached HTML response used by this audit."""

    url: str
    status: int
    final: str
    robots: tuple[str, ...]
    hreflang: dict[str, str]
    canonical: tuple[str, ...]
    jsonld: tuple[object, ...]
    internal_links: tuple[str, ...]
    error: str = ""


@dataclass(frozen=True)
class Finding:
    """One actionable URL/SEO defect."""

    kind: str
    url: str
    detail: str


@dataclass(frozen=True)
class Audit:
    """The findings plus the bounded inventory."""

    findings: tuple[Finding, ...]
    sitemap_urls: int
    parsed_pages: int
    internal_targets: int


class PageParser(HTMLParser):
    """Extract only the head/link/JSON-LD facts this audit needs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self.metas: list[dict[str, str]] = []
        self.anchors: set[str] = set()
        self.scripts: list[str] = []
        self._script: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "link":
            self.links.append(values)
        elif tag == "meta":
            self.metas.append(values)
        elif tag == "a" and values.get("href"):
            self.anchors.add(values["href"])
        elif tag == "script" and "ld+json" in values.get("type", "").lower():
            self._script = []

    def handle_data(self, data: str) -> None:
        if self._script is not None:
            self._script.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script is not None:
            self.scripts.append("".join(self._script))
            self._script = None


def parse_html(url: str, html: str) -> dict[str, Any]:
    """The Page fields derivable from one HTML body."""
    parser = PageParser()
    parser.feed(html)
    hreflang: dict[str, str] = {}
    canonical: list[str] = []
    for link in parser.links:
        if "alternate" in link.get("rel", "").lower().split():
            language = link.get("hreflang", "")
            if language and link.get("href"):
                hreflang[language] = urllib.parse.urljoin(url, link["href"])
        if "canonical" in link.get("rel", "").lower().split() and link.get("href"):
            canonical.append(urllib.parse.urljoin(url, link["href"]))
    robots = tuple(
        directive.strip().lower()
        for meta in parser.metas
        if meta.get("name", "").lower() == "robots"
        for directive in meta.get("content", "").split(",")
        if directive.strip()
    )
    jsonld: list[object] = []
    for raw in parser.scripts:
        try:
            jsonld.append(json.loads(raw))
        except json.JSONDecodeError as error:
            jsonld.append({"__parse_error__": str(error), "__raw__": raw[:300]})
    links = {
        urllib.parse.urljoin(url, href)
        for href in parser.anchors
        if urllib.parse.urlsplit(urllib.parse.urljoin(url, href)).hostname
        == urllib.parse.urlsplit(url).hostname
    }
    return {
        "robots": robots,
        "hreflang": hreflang,
        "canonical": tuple(canonical),
        "jsonld": tuple(jsonld),
        "internal_links": tuple(sorted(links)),
    }


def load_parsed(path: Path) -> dict[str, Page]:
    """Read the sweep's JSON object."""
    data: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object keyed by URL")
    pages: dict[str, Page] = {}
    for url, raw in data.items():
        if not isinstance(url, str) or not isinstance(raw, dict):
            continue
        pages[url] = Page(
            url=url,
            status=_integer(raw.get("status")),
            final=_string(raw.get("final")),
            robots=tuple(_strings(raw.get("robots"))),
            hreflang=_mapping(raw.get("hreflang")),
            canonical=tuple(_strings(raw.get("canonical"))),
            jsonld=tuple(
                raw.get("jsonld", []) if isinstance(raw.get("jsonld"), list) else []
            ),
            internal_links=tuple(_strings(raw.get("internal_links"))),
            error=_string(raw.get("error")),
        )
    return pages


def load_cache(url_list: Path, directory: Path) -> dict[str, Page]:
    """Read page responses already cached by the sweep."""
    pages: dict[str, Page] = {}
    for index, url in enumerate(url_list.read_text(encoding="utf-8").splitlines()):
        body = directory / f"{index}.body"
        meta = directory / f"{index}.meta"
        if not body.exists() or not meta.exists():
            continue
        fields = meta.read_text(encoding="utf-8").strip().split("\t")
        fields += [""] * (4 - len(fields))
        parsed = parse_html(url, body.read_text(encoding="utf-8", errors="replace"))
        pages[url] = Page(
            url=url,
            status=int(fields[0]) if fields[0].isdigit() else 0,
            final=fields[1] or url,
            robots=tuple(parsed["robots"]),
            hreflang=parsed["hreflang"],
            canonical=tuple(parsed["canonical"]),
            jsonld=tuple(parsed["jsonld"]),
            internal_links=tuple(parsed["internal_links"]),
            error=fields[3],
        )
    return pages


def json_types(value: object) -> set[str]:
    """Every @type below one JSON-LD value."""
    found: set[str] = set()
    if isinstance(value, list):
        for item in value:
            found.update(json_types(item))
    elif isinstance(value, dict):
        declared = value.get("@type")
        if isinstance(declared, str):
            found.add(declared)
        elif isinstance(declared, list):
            found.update(item for item in declared if isinstance(item, str))
        for key, item in value.items():
            if key != "@type":
                found.update(json_types(item))
    return found


def declared_types(value: object) -> set[str]:
    """The @type values declared by one node."""
    if not isinstance(value, dict):
        return set()
    declared = value.get("@type")
    if isinstance(declared, str):
        return {declared}
    if isinstance(declared, list):
        return {item for item in declared if isinstance(item, str)}
    return set()


def page_nodes(value: object) -> list[dict[str, Any]]:
    """Page-like JSON-LD nodes that can state a canonical URL."""
    node_types = {
        "BlogPosting",
        "CollectionPage",
        "ItemPage",
        "Product",
        "WebPage",
    }
    found: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            found.extend(page_nodes(item))
    elif isinstance(value, dict):
        if declared_types(value) & node_types:
            found.append(value)
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                found.extend(page_nodes(item))
    return found


def required_types(url: str) -> frozenset[str]:
    """Structured data required for this indexable customer page type."""
    path = urllib.parse.urlsplit(url).path
    if path in {"/faq-download/", "/de/faq-dokumente/"}:
        return frozenset({"FAQPage"})
    if path in {"/blog/", "/de/blog/"}:
        return frozenset({"CollectionPage"})
    if path.startswith(("/category/", "/de/kategorie/")):
        return frozenset({"CollectionPage", "BreadcrumbList"})
    if path.startswith(("/product-category/", "/de/produkt-kategorie/")):
        return frozenset({"CollectionPage", "BreadcrumbList"})
    if path.startswith(("/product/", "/de/produkt/")):
        return frozenset({"Product"})
    return frozenset()


def noindex(page: Page) -> bool:
    """Whether the page's meta robots excludes indexing."""
    return "noindex" in page.robots


def audit(parsed: dict[str, Page], cache_pages: dict[str, Page]) -> Audit:
    """Run the rules over the cached evidence."""
    pages = dict(cache_pages)
    pages.update(parsed)
    sitemap = set(parsed)
    findings: list[Finding] = []

    for url, page in sorted(parsed.items()):
        if page.status != 200:
            findings.append(Finding("sitemap-status", url, f"answered {page.status}"))
            continue
        if page.final != url:
            findings.append(Finding("sitemap-final", url, f"finished at {page.final}"))
        if tuple(page.canonical) != (url,):
            findings.append(
                Finding("canonical", url, f"canonical is {list(page.canonical)!r}")
            )
        if noindex(page):
            findings.append(Finding("sitemap-noindex", url, "sitemap URL is noindex"))
            continue
        present = set().union(*(json_types(item) for item in page.jsonld))
        missing = sorted(required_types(url) - present)
        if missing:
            findings.append(
                Finding(
                    "structured-data",
                    url,
                    "missing required type(s): " + ", ".join(missing),
                )
            )

    for url, page in sorted(pages.items()):
        # An internal link may legitimately be a retired alias whose final URL
        # is the canonical page. Only inspect the page that actually answered
        # at this URL; an alias's own schema is not evidence about the alias.
        if page.status != 200 or (url not in sitemap and page.final != url):
            continue
        for item in page.jsonld:
            if isinstance(item, dict) and "__parse_error__" in item:
                findings.append(
                    Finding("jsonld-parse", url, _string(item["__parse_error__"]))
                )
        for node in page_nodes(list(page.jsonld)):
            claim = node.get("url")
            if not isinstance(claim, str) or not claim:
                continue
            if _without_trailing_slash(claim) != _without_trailing_slash(url):
                findings.append(
                    Finding(
                        "jsonld-self-url",
                        url,
                        f"{node.get('@type')!r} claims {claim}",
                    )
                )
                break

    for url in sorted(sitemap):
        page = parsed[url]
        if noindex(page):
            continue
        for language in ("en", "de"):
            target_url = page.hreflang.get(language)
            if target_url in (None, url):
                continue
            target = pages.get(target_url)
            if target is not None and noindex(target):
                findings.append(
                    Finding(
                        "indexability-asymmetry",
                        url,
                        f"{language} alternate {target_url} is noindex",
                    )
                )
                break

    targets = {
        urllib.parse.urlunsplit(
            (
                urllib.parse.urlsplit(target).scheme,
                urllib.parse.urlsplit(target).netloc,
                urllib.parse.urlsplit(target).path,
                "",
                "",
            )
        )
        for page in parsed.values()
        for target in page.internal_links
    }
    return Audit(
        findings=tuple(dict.fromkeys(findings)),
        sitemap_urls=len(parsed),
        parsed_pages=len(pages),
        internal_targets=len(targets),
    )


def _without_trailing_slash(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path.rstrip("/"), parts.query, "")
    )


def _integer(value: object) -> int:
    return value if isinstance(value, int) else 0


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _strings(value: object) -> list[str]:
    return (
        [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else []
    )


def _mapping(value: object) -> dict[str, str]:
    return (
        {
            key: item
            for key, item in value.items()
            if isinstance(key, str) and isinstance(item, str)
        }
        if isinstance(value, dict)
        else {}
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--parsed", required=True, type=Path)
    parser.add_argument(
        "--cache",
        action="append",
        default=[],
        metavar="URL_LIST=CACHE_DIR",
        help="read cached counterpart pages without making requests",
    )
    parser.add_argument(
        "--json", action="store_true", help="print machine-readable output"
    )
    args = parser.parse_args()

    parsed = load_parsed(args.parsed)
    cached: dict[str, Page] = {}
    for value in args.cache:
        url_list, separator, directory = value.partition("=")
        if not separator:
            parser.error("--cache expects URL_LIST=CACHE_DIR")
        cached.update(load_cache(Path(url_list), Path(directory)))
    result = audit(parsed, cached)

    if args.json:
        print(
            json.dumps(
                {
                    "findings": [
                        {
                            "kind": finding.kind,
                            "url": finding.url,
                            "detail": finding.detail,
                        }
                        for finding in result.findings
                    ],
                    "sitemap_urls": result.sitemap_urls,
                    "parsed_pages": result.parsed_pages,
                    "internal_targets": result.internal_targets,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for finding in result.findings:
            print(f"{finding.kind}: {finding.url}: {finding.detail}")
        print(
            f"seo-audit: {len(result.findings)} finding(s); "
            f"{result.sitemap_urls} sitemap URLs, {result.parsed_pages} parsed pages, "
            f"{result.internal_targets} unique internal path targets"
        )
    return 1 if result.findings else 0


if __name__ == "__main__":
    sys.exit(main())
