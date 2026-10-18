"""Read-only c254 route/title/consumer acceptance; reviewed expectations are data."""

import argparse
import concurrent.futures
import html
import json
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[4]
SITE = "http://127.0.0.1:9129"
ROUTES = ROOT / "plugins/linker-i18n/tests/fixtures/german-routes.json"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.canonical = ""
        self.hreflang = {}
        self.share = ""
        self.feed(text)
        title = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
        self.title = re.sub(r"\s+", " ", html.unescape(title[1])).strip() if title else ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href", "")
        if tag == "link" and "hreflang" in attrs:
            self.hreflang[attrs["hreflang"]] = attrs.get("href", "")
        if tag == "meta" and attrs.get("property") == "og:url":
            self.share = attrs.get("content", "")


def fetch(path, cookie=""):
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Only paths on c254 may be fetched")
    request = urllib.request.Request(SITE + path, headers={"Cookie": cookie} if cookie else {})
    try:
        response = urllib.request.build_opener(NoRedirect).open(request, timeout=60)
    except urllib.error.HTTPError as error:
        response = error
    return response.status, response.headers.get("Location", ""), response.read().decode("utf-8", "replace")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cookie-file", type=pathlib.Path, required=True, help="Owned local customer fixture cookie; never committed")
    args = parser.parse_args()
    cookie = args.cookie_file.read_text().strip()
    rows = json.loads(ROUTES.read_text())
    paths = sorted({row[key] for row in rows for key in ("old", "new")})
    authenticated = {row[key] for row in rows if row["kind"] in ("native Woo endpoint", "native Woo address child") for key in ("old", "new")}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        responses = dict(zip(paths, pool.map(lambda path: fetch(path, cookie if path in authenticated else ""), paths)))
    defects = []
    titles = defaultdict(list)
    pages = {}
    retired = {row["old"]: row["new"] for row in rows if row["old"] != row["new"]}
    for row in rows:
        first = responses[row["old"]]
        final = responses[row["new"]]
        row.update(first_status=first[0], location=first[1], new_status=final[0], state="customer" if row["new"] in authenticated else "guest")
        if row["old"] != row["new"] and (first[0] != 301 or first[1] != SITE + row["new"]):
            defects.append(f"Redirect: {row['old']} {first[:2]}")
        action = row["kind"] == "native Woo action"
        if action:
            if final[0] != 302 or not final[1].startswith(SITE + row["terminal"]):
                defects.append(f"Native action: {row['new']} {final[:2]}")
            final = responses[row["terminal"]]
        row["final_status"] = final[0]
        if final[0] != 200:
            defects.append(f"Final: {row['new']} {final[:2]}")
        page = Page(final[2])
        row["title"] = page.title
        row.update(canonical=page.canonical, hreflang=page.hreflang, share=page.share)
        if not action:
            if row['old'] != row['new']:
                if page.hreflang.get('de', '') != page.canonical:
                    defects.append(f"German alternate differs from canonical: {row['new']}: {page.hreflang.get('de', '')} != {page.canonical}")
                if page.canonical and page.canonical != SITE + row['new']:
                    defects.append(f"Canonical is not the final address: {row['new']}: {page.canonical}")
            pages[row["new"]] = page
    for path, page in pages.items():
        if not page.title:
            defects.append(f"Missing title: {path}")
        if path in ('/de/mein-konto/registrieren/', '/de/mein-konto/passwort-zuruecksetzen/'):
            for label, url in [('canonical', page.canonical), ('share', page.share)]:
                if url != SITE + path:
                    defects.append(f'Missing or incorrect {label} tag: {path}: {url}')
        titles[page.title].append(path)
        for label, url in [("canonical", page.canonical), ("share", page.share), *page.hreflang.items()]:
            if not url:
                continue
            parsed = urllib.parse.urlsplit(url)
            if parsed.path in retired:
                defects.append(f"Retired {label}: {path} -> {parsed.path}")
        for url in page.links:
            parsed = urllib.parse.urlsplit(urllib.parse.urljoin(SITE + path, url))
            if parsed.netloc == urllib.parse.urlsplit(SITE).netloc and parsed.path in retired:
                defects.append(f"Retired link: {path} -> {parsed.path}")
    duplicates = {title: paths for title, paths in titles.items() if len(paths) > 1}
    defects.extend(f"Duplicate title: {title}: {paths}" for title, paths in duplicates.items())
    def locations(xml):
        return {urllib.parse.urlsplit(n.text).path for n in ET.fromstring(xml).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')}
    index = fetch('/sitemaps.xml')
    if index[0] != 200:
        defects.append('Sitemap index is not 200')
    current_locations = set()
    for path in sorted(locations(index[2])):
        response = fetch(path)
        if response[0] != 200:
            defects.append(f'Sitemap child is not 200: {path}')
        current_locations.update(locations(response[2]))
    original_locations = set()
    for document in json.loads((pathlib.Path(__file__).parent / 'live-sitemaps.json').read_text()):
        if not document['url'].endswith('/sitemaps.xml'):
            original_locations.update(locations(document['xml']))
    original_en = {p for p in original_locations if not p.startswith('/de/')}
    current_en = {p for p in current_locations if not p.startswith('/de/')}
    expected_de = {retired.get(p, p) for p in original_locations if p.startswith('/de/')}
    current_de = {p for p in current_locations if p.startswith('/de/')}
    if original_en != current_en:
        defects.append(f'English sitemap changed: removed {sorted(original_en-current_en)}, added {sorted(current_en-original_en)}')
    if expected_de != current_de:
        defects.append(f'German sitemap mismatch: missing {sorted(expected_de-current_de)}, extra {sorted(current_de-expected_de)}')
    report = {"site": SITE, "routes": rows, "canonical_pages": len(pages), "duplicate_titles": duplicates, "sitemap": {"german": len(current_de), "english": len(current_en), "english_unchanged": original_en == current_en, "german_expected": expected_de == current_de}, "defects": sorted(set(defects))}
    (pathlib.Path(__file__).parent / "route-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"routes": len(rows), "canonical_pages": len(pages), "defects": len(report["defects"])}, ensure_ascii=False))
    for defect in report["defects"][:30]:
        print(defect)
    raise SystemExit(bool(defects))


if __name__ == "__main__":
    main()
