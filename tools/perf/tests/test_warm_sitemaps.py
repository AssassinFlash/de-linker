"""Public pages must return a warm hit, private routes must retain their own URL and policy."""

import json
import runpy
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest

SITE = "https://linker.test"


def run_warmer(tmp_path, monkeypatch, *, bad_route=None, discover=True, extra_links=(), pdf_limit=24, omit_pdf_map=False):
    main = runpy.run_path(str(Path(__file__).parents[1] / "warm-sitemaps.py"))["main"]
    report = tmp_path / "warm.json"
    requests = []
    private = {"/contact/?intent=project", "/de/kontakt/?intent=project", *main.__globals__["DYNAMIC"]}
    targets = main.__globals__["RETIRED"]

    def get(url, *, read_body=False):
        requests.append(url)
        assert url.startswith(SITE + "/")
        route = url.removeprefix(SITE)
        target = targets.get(route, route)
        cached = route not in private and route not in targets
        if route == bad_route:
            if route == "/de/solution-draft/":
                target = "/cart/"
            else:
                cached = not cached
        result = {
            "status": 200,
            "url": SITE + target,
            "cache": "hit" if cached else "",
            "server_policy": "" if cached else "no-cache",
            "browser_policy": "" if cached else "no-cache, private",
        }
        body = ""
        if read_body and route == "/sitemaps.xml":
            names = list(main.__globals__["SITEMAPS"]) + ([] if omit_pdf_map else ["pdf"])
            body = "<sitemapindex>" + "".join(f"<sitemap><loc>{SITE}/{n}-sitemap1.xml</loc></sitemap>" for n in names) + "</sitemapindex>"
        elif read_body and route == "/pdf-sitemap1.xml":
            paths = [f"/downloads/engineering-toolkit/file-{i}.pdf" for i in range(6)] + ["/uploads/a.pdf", "/uploads/b.pdf"]
            body = "<urlset>" + "".join(f"<url><loc>{SITE}{path}</loc></url>" for path in paths) + "</urlset>"
        elif read_body and urlsplit(url).path.endswith(".xml"):
            body = f"<urlset><url><loc>{SITE}/blog/</loc></url><url><loc>{SITE}/contact/</loc></url></urlset>"
        elif read_body and route == "/blog/page/2/":
            body = '<link rel="next" href="/blog/page/3/"><a href="https://other.test/blog/page/4/">4</a>'
            body += '<a href="/blog/page/4/?sort=recent">Sorted archive</a><a href="/arbitrary/page/2/">Other</a>'
            body += "".join(f'<a href="{href}">Page</a>' for href in extra_links)
        elif read_body and route == "/blog/page/3/":
            body = '<a href="/blog/page/10/">10</a>'
        return result, body.encode()

    args = ["warm", "--pdf-limit", str(pdf_limit), "--site", SITE, "--workers", "1", "--output", str(report)]
    if not discover:
        args.append("--no-discover-pagination")
    monkeypatch.setitem(main.__globals__, "get", get)
    monkeypatch.setattr(sys, "argv", args)
    if bad_route:
        with pytest.raises(SystemExit):
            main()
    else:
        main()
    return json.loads(report.read_text()), requests


def test_warm_archive_and_contact_policy(tmp_path, monkeypatch):
    report, requests = run_warmer(tmp_path, monkeypatch)
    for path in (
        "/brand/goodwe/page/2/", "/de/marke/goodwe/seite/2/",
        "/blog/page/2/", "/de/blog/seite/2/", "/blog/page/3/", "/blog/page/10/",
        "/contact/", "/de/kontakt/",
    ):
        assert report["public"][SITE + path]["second"]["cache"] == "hit"
        assert requests.count(SITE + path) == 2
    for path in ("/contact/?intent=project", "/de/kontakt/?intent=project"):
        assert report["dynamic"][SITE + path]["second"]["server_policy"] == "no-cache"
    assert SITE + "/arbitrary/page/2/" not in requests
    assert SITE + "/blog/page/4/?sort=recent" not in requests
    assert report["failed"] == []


@pytest.mark.parametrize("discover,extra_count", [(True, 30), (False, 0)])
def test_discovery_limit_and_opt_out(tmp_path, monkeypatch, discover, extra_count):
    links = [f"/blog/page/{i}/" for i in range(3, 50)]
    report, _ = run_warmer(tmp_path, monkeypatch, discover=discover, extra_links=links)
    assert sum(SITE + url in report["public"] for url in links) == extra_count


@pytest.mark.parametrize("route", ["/de/solution-draft/", "/contact/", "/de/kontakt/?intent=project"])
def test_reports_a_wrong_destination_or_cache_policy(tmp_path, monkeypatch, route):
    report, _ = run_warmer(tmp_path, monkeypatch, bad_route=route)
    assert report["failed"] == [SITE + route]


@pytest.mark.parametrize("limit,expected", [(1, 9), (0, 10)])
def test_document_cache_covers_both_editions_and_oem_sample(tmp_path, monkeypatch, limit, expected):
    report, requests = run_warmer(tmp_path, monkeypatch, pdf_limit=limit)
    assert len(report["sitemaps"]) == 7
    assert len(report["documents"]) == expected
    assert all(row["second"]["cache"] == "hit" for row in report["documents"].values())
    assert len([url for url in report["documents"] if url.endswith(".csv")]) == 2
    assert requests.count(SITE + "/uploads/a.pdf") == 2
    assert report["pdf_sitemap"]["second"]["cache"] == "hit"


def test_index_must_include_pdf_sitemap(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="public PDF sitemap"):
        run_warmer(tmp_path, monkeypatch, omit_pdf_map=True)
