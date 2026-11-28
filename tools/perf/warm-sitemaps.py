"""Warm the HTML and public document sitemaps and verify LiteSpeed cache hits."""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree.ElementTree import fromstring

SITEMAPS = ("page", "product", "product_cat", "product_brand", "category", "post")
PDF_SITEMAP = "pdf"
TOOLKIT_PATH = "/downloads/engineering-toolkit/"
TOOLKIT_CSVS = (
    TOOLKIT_PATH + "linker-load-profile-template-15min-en.csv",
    TOOLKIT_PATH + "linker-vorlage-lastgang-15min-de.csv",
)
PAGINATED = (
    "/products/page/2/",
    "/products/page/3/",
    "/de/produkte/seite/2/",
    "/de/produkte/seite/3/",
    "/product-category/inverters/page/2/",
    "/de/produkt-kategorie/wechselrichter/seite/2/",
    "/brand/goodwe/page/2/",
    "/de/marke/goodwe/seite/2/",
    "/blog/page/2/",
    "/de/blog/seite/2/",
)
CONTACT = ("/contact/", "/de/kontakt/")
DYNAMIC_QUERIES = tuple(path + "?intent=project" for path in CONTACT)
DYNAMIC = (
    "/proforma-request/",
    "/de/proforma-anfrage/",
    "/cart/",
    "/de/loesungsentwurf/",
)
RETIRED = {"/solution-draft/": "/cart/", "/de/solution-draft/": "/de/loesungsentwurf/"}
ARCHIVE = (
    r"/(?:products|de/produkte|product-category/[^/?]+|de/produkt-kategorie/[^/?]+"
    r"|brand/[^/?]+|de/marke/[^/?]+|blog|de/blog)"
)
ARCHIVE_PAGE = re.compile(ARCHIVE + r"/(?:page|seite)/(?:[2-9]|[1-9][0-9]+)/")
MAX_DISCOVERED = 30


class Pagination(HTMLParser):
    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag != "a" and not (
            tag == "link" and "next" in (values.get("rel") or "").lower().split()
        ):
            return
        href = values.get("href")
        if not href:
            return
        url = urljoin(self.url, href)
        target = urlsplit(url)
        if (
            urlsplit(self.url)[:2] == target[:2]
            and not target.query
            and not target.fragment
            and ARCHIVE_PAGE.fullmatch(target.path)
        ):
            self.links.add(url)


def get(url: str, *, read_body: bool = False) -> tuple[dict[str, str | int], bytes]:
    request = Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
    )
    try:
        response = urlopen(request, timeout=45)
    except HTTPError as error:
        response = error
    with response:
        if read_body:
            body = response.read()
        else:
            while response.read(64 * 1024):
                pass
            body = b""
        return {
            "url": response.geturl(),
            "status": response.status,
            "cache": response.headers.get("X-LiteSpeed-Cache", ""),
            "server_policy": response.headers.get("X-LiteSpeed-Cache-Control", ""),
            "browser_policy": response.headers.get("Cache-Control", ""),
        }, body


def sitemap_links(url: str, kind: str) -> list[str]:
    result, body = get(url, read_body=True)
    if result["status"] != 200 or result["url"] != url:
        raise ValueError(f"Invalid sitemap response for {url}: {result}")
    return [
        node.text.strip()
        for node in fromstring(body).findall(f"{{*}}{kind}/{{*}}loc")
        if node.text
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="https://de-linker.com")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--discover-pagination", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--delay-ms", type=int, default=0)
    parser.add_argument("--pdf-limit", type=int, default=24, help="OEM PDF sample size; 0 warms all PDFs")
    args = parser.parse_args()
    if args.workers < 1 or args.delay_ms < 0:
        parser.error("--workers must be positive and --delay-ms must be nonnegative")
    site = args.site.rstrip("/")
    if args.pdf_limit < 0:
        parser.error("--pdf-limit must be nonnegative")
    index = sitemap_links(f"{site}/sitemaps.xml", "sitemap")
    expected = {f"{site}/{name}-sitemap1.xml" for name in (*SITEMAPS, PDF_SITEMAP)}
    if set(index) != expected or len(index) != len(expected):
        raise ValueError("Expected the six HTML sitemaps and the public PDF sitemap")
    maps = {name: sitemap_links(f"{site}/{name}-sitemap1.xml", "url") for name in SITEMAPS}
    if not all(maps.values()):
        raise ValueError("Empty HTML sitemap")
    pdf_map = f"{site}/{PDF_SITEMAP}-sitemap1.xml"
    pdfs = sitemap_links(pdf_map, "url")
    for url in pdfs:
        parsed = urlsplit(url)
        if parsed[:2] != urlsplit(site)[:2] or not parsed.path.lower().endswith(".pdf") or parsed.query or parsed.fragment:
            raise ValueError(f"Invalid PDF sitemap location: {url}")
    toolkit = [url for url in pdfs if url.startswith(site + TOOLKIT_PATH)]
    if len(set(toolkit)) != 6 or len(pdfs) != len(set(pdfs)):
        raise ValueError("Expected six toolkit PDFs and unique PDF locations")
    oem = [url for url in pdfs if not url.startswith(site + TOOLKIT_PATH)]
    documents = toolkit + [site + path for path in TOOLKIT_CSVS] + (oem[:args.pdf_limit] if args.pdf_limit else oem)
    public = dict.fromkeys(url for urls in maps.values() for url in urls)
    public.update(dict.fromkeys(site + path for path in (*PAGINATED, *CONTACT)))
    if any(urlsplit(url)[:2] != urlsplit(site)[:2] for url in public):
        raise ValueError("Sitemap contains a URL outside the target site")
    private = [site + path for path in (*DYNAMIC, *DYNAMIC_QUERIES)]
    redirects = {site + path: site + target for path, target in RETIRED.items()}
    for url in (*private, *redirects):
        public.pop(url, None)
    urls = list(public) + list(private) + list(redirects) + [pdf_map] + documents

    def request(url: str, *, discover: bool = False) -> tuple[dict[str, str | int], set[str]]:
        path = urlsplit(url).path
        archive = discover and args.discover_pagination and (
            re.fullmatch(ARCHIVE + "/", path) or ARCHIVE_PAGE.fullmatch(path)
        )
        if args.delay_ms:
            time.sleep(args.delay_ms / 1000)
        result, body = get(url, read_body=bool(archive))
        links: set[str] = set()
        if archive and result["status"] == 200 and result["url"] == url:
            pagination = Pagination(url)
            pagination.feed(body.decode("utf-8"))
            links = pagination.links
        return result, links

    first = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        batch = urls.copy()
        remaining = MAX_DISCOVERED
        while batch:
            discovered = set()
            warm = pool.map(partial(request, discover=True), batch)
            for url, (result, links) in zip(batch, warm, strict=True):
                first[url] = result
                discovered.update(links)
            batch = sorted(discovered.difference(public))[:remaining]
            public.update(dict.fromkeys(batch))
            urls.extend(batch)
            remaining -= len(batch)
        second = {
            url: result for url, (result, _) in zip(urls, pool.map(request, urls), strict=True)
        }

    failed = []
    for url, result in second.items():
        expected = redirects.get(url, url)
        attempts = (first[url], result)
        ok = all(read["status"] == 200 and read["url"] == expected for read in attempts)
        if url in public or url in documents or url == pdf_map:
            ok = ok and result["cache"] == "hit"
        else:
            ok = ok and all(
                read["cache"] != "hit"
                and "no-cache" in str(read["server_policy"])
                and "no-cache" in str(read["browser_policy"])
                for read in attempts
            )
        if not ok:
            failed.append(url)

    def reads(group: Iterable[str]) -> dict[str, dict[str, dict[str, str | int]]]:
        return {url: {"first": first[url], "second": second[url]} for url in group}

    public_reads = reads(public)
    dynamic_reads = reads(private)
    retired_reads = reads(redirects)
    report = {
        "sitemaps": {**maps, PDF_SITEMAP: pdfs},
        "pdf_sitemap": reads([pdf_map])[pdf_map],
        "documents": reads(documents),
        "public": public_reads,
        "dynamic": dynamic_reads,
        "retired": retired_reads,
        "failed": failed,
    }
    args.output.write_text(json.dumps(report, indent=2))
    for name, entries in maps.items():
        print(f"{name}: {len(entries)} URLs")
    print(
        f"{len(public_reads)} public cache reads; {len(dynamic_reads)} dynamic routes; {len(retired_reads)} retired drafts; {len(failed)} failures"
    )
    print(f"{len(documents)} public PDF/CSV cache reads")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
