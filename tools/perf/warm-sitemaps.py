"""Warm the four public sitemaps after a LiteSpeed purge and read the cache back."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from xml.etree.ElementTree import fromstring

SITEMAPS = ("page", "product", "product_cat", "post")
DYNAMIC = (
    "/contact/",
    "/de/kontakt/",
    "/proforma-request/",
    "/de/proforma-anfrage/",
    "/cart/",
    "/de/loesungsentwurf/",
)
RETIRED = "/solution-draft/"


def get(url: str, *, xml: bool = False) -> tuple[dict[str, str | int], bytes]:
    request = Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; Linker cache warmup)"}
    )
    try:
        response = urlopen(request, timeout=45)
    except HTTPError as error:
        response = error
    with response:
        body = response.read()
        return {
            "url": response.geturl(),
            "status": response.status,
            "cache": response.headers.get("X-LiteSpeed-Cache", ""),
            "server_policy": response.headers.get("X-LiteSpeed-Cache-Control", ""),
            "browser_policy": response.headers.get("Cache-Control", ""),
        }, body if xml else b""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="https://de-linker.com")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    site = args.site.rstrip("/")
    maps: dict[str, list[str]] = {}
    for name in SITEMAPS:
        url = f"{site}/{name}-sitemap1.xml"
        result, body = get(url, xml=True)
        if result["status"] != 200:
            raise ValueError(f"{url} returned {result['status']}")
        maps[name] = [
            node.text.strip()
            for node in fromstring(body).findall("{*}url/{*}loc")
            if node.text
        ]
        if not maps[name]:
            raise ValueError(f"{url} contains no page URLs")
    public = list(dict.fromkeys(url for urls in maps.values() for url in urls))
    urls = list(dict.fromkeys(public + [site + path for path in (*DYNAMIC, RETIRED)]))

    def request(url: str) -> dict[str, str | int]:
        return get(url)[0]

    with ThreadPoolExecutor(max_workers=4) as pool:
        first = list(pool.map(request, urls))
        second = list(pool.map(request, urls))

    failed: list[str] = []
    for url, result in zip(urls, second, strict=True):
        route = urlsplit(url).path
        if route in DYNAMIC or route == RETIRED:
            ok = (
                result["status"] == 200
                and result["url"] == (site + "/cart/" if route == RETIRED else url)
                and result["cache"] != "hit"
                and "no-cache" in str(result["server_policy"])
                and "no-cache" in str(result["browser_policy"])
            )
        else:
            ok = (
                result["status"] == 200
                and result["url"] == url
                and result["cache"] == "hit"
            )
        if not ok:
            failed.append(url)
    report = {
        "sitemaps": maps,
        "public": {
            url: {"first": first[i], "second": second[i]}
            for i, url in enumerate(urls)
            if url in public and urlsplit(url).path not in DYNAMIC
        },
        "dynamic": {
            url: {"first": first[i], "second": second[i]}
            for i, url in enumerate(urls)
            if urlsplit(url).path in DYNAMIC
        },
        "retired": {"first": first[-1], "second": second[-1]},
        "failed": failed,
    }
    args.output.write_text(json.dumps(report, indent=2))
    for name, entries in maps.items():
        print(f"{name}: {len(entries)} URLs")
    print(
        f"{len(report['public'])} public cache reads; {len(report['dynamic'])} dynamic routes; retired draft {second[-1]['status']}; {len(failed)} failures"
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
