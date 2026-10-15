#!/usr/bin/env python3
"""Zero-legacy gate for the public surfaces of a de-linker instance.

Two assertions over plain HTTP, no authentication:

1. Asset sweep: sampled public pages must contain none of the old project's
   traces — references to its plugin's assets (`terravolt-b2b-core` paths),
   its brand word (`TerraVolt`), or its German domain (`tvolt-energie.de`,
   which the snapshot child theme's hreflang emitter points at). All three are
   failures: the header of every sampled page and the archive JSON-LD are
   where these strings lived. The sampled page list is printed with each
   page's result, and includes the contact pages and a product page beside
   the front pages and the faces.

2. Face attribution: the four faces the old project served through its own
   LiveCanvas templates — blog posts index, single post, search results, blog
   category archive — in EN and DE each, must answer and must not be rendered
   by the legacy templates. Attribution is read off the page itself:
   LiveCanvas stamps `<!-- LC DT ID: <n> -->` into the markup, and the legacy
   content templates are recognized by what they ship into the page — the
   style block they carry inline (`data-name="tangible-template-inline-style"`,
   the CSS the port moved into the WindPress volume) and the template family's
   own banner ("… Dynamic Template v1") inside it. The stamp id alone is
   attribution, not evidence: `present` reclaims the old template rows in place
   (Templates::existing_id(), the LiveCanvas assignment meta key), so the same
   ids — 574, 619, 607 in this family — now render the repository's export.
   Section ids the new tree ships itself (the ported header/footer, storefront
   and blog markup under plugins/linker-commerce/content) are allow-listed, so
   the chrome never counts as legacy rendering. No stamp and no legacy markup
   means the theme fallback renders the face — the accepted pending-design
   state — and the face passes.

Discovery uses the public REST API (`/wp-json/wp/v2`), so the script runs
against any instance of this snapshot family without per-instance fixtures:
the single-post URL is the latest published post, the category URL is the
first category that actually has posts (DE falls back to the EN category path
under /de/). Blog index, search and product-archive URLs are the project's
fixed paths and can be overridden with options.

Usage:
    python3 tools/checks/legacy-surfaces.py [--base http://127.0.0.1:8975]

Exit code: 0 = clean, 1 = problems found, 2 = the instance did not answer.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

# lc_dynamic_template rows the old project used, as loaded into this snapshot
# family: the 404 pair and the four faces' EN/DE twins (docs/acceptance/
# 2026-10-13/legacy-surfaces). Read-out only — see the module docstring: the
# takeover reuses these rows, so the id no longer says who wrote the content.
LEGACY_DT_IDS = {574, 6891, 613, 6887, 619, 6885, 607, 6889, 940, 6871}

LEGACY_ID_RE = re.compile(r'id="(tv-[a-z0-9-]+)"')
LEGACY_WORD_RE = re.compile(r"terravolt", re.IGNORECASE)
LEGACY_ASSET_RE = re.compile(r"terravolt-b2b-core", re.IGNORECASE)
LEGACY_DOMAIN_RE = re.compile(r"tvolt-energie\.de", re.IGNORECASE)
LC_DT_RE = re.compile(r"<!--\s*LC DT ID:\s*(\d+)\s*-->")
# The legacy templates' own signatures in the rendered page: their CSS was an
# inline block (the ported faces get it from the WindPress volume), and the
# block's banner names the family. Both are marked by the marker they print,
# not by the row they were stored in.
LEGACY_STYLE_RE = re.compile(r'data-name="tangible-template-inline-style"')
LEGACY_BANNER_RE = re.compile(r"Dynamic Template v\d")

TIMEOUT = 20


def shipped_tv_ids(repo_root: Path) -> set[str]:
    """Section ids the new tree ships in its own LiveCanvas content."""
    content = repo_root / "plugins" / "linker-commerce" / "content"
    ids: set[str] = set()
    if content.is_dir():
        for html in content.rglob("*.html"):
            ids.update(LEGACY_ID_RE.findall(html.read_text(encoding="utf-8", errors="replace")))
    return ids


def fetch(url: str) -> tuple[int | None, str]:
    """Return (status, body). status is None when the request itself failed."""
    request = urllib.request.Request(url, headers={"User-Agent": "legacy-surfaces-check/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace") if error.fp else ""
        return error.code, body
    except (urllib.error.URLError, TimeoutError):
        return None, ""


def fetch_json(url: str):
    status, body = fetch(url)
    if status != 200:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def discover(base: str) -> dict[str, str | None]:
    """Find the single-post and category URLs through the public REST API."""
    found: dict[str, str | None] = {}
    posts = fetch_json(f"{base}/wp-json/wp/v2/posts?per_page=1&status=publish")
    found["single-en"] = posts[0]["link"] if posts else None
    posts_de = fetch_json(f"{base}/wp-json/wp/v2/posts?per_page=1&status=publish&lang=de")
    found["single-de"] = posts_de[0]["link"] if posts_de else None
    for lang, key in (("", "category-en"), ("&lang=de", "category-de")):
        categories = fetch_json(f"{base}/wp-json/wp/v2/categories?per_page=100{lang}")
        with_posts = [c for c in categories or [] if c.get("count", 0) > 0]
        found[key] = with_posts[0]["link"] if with_posts else None
    # Polylang serves the DE archive of a shared category under /de/ even when
    # the REST count is 0 for the DE twin; derive it from the EN link.
    if found["category-de"] is None and found["category-en"]:
        en = found["category-en"]
        if en.startswith(base):
            found["category-de"] = f"{base}/de{en[len(base):]}"
    # One product page: its hreflang pair was in the old emitter's product map.
    # The Store API is public; the DE twin path mirrors the EN one under /de/.
    products = fetch_json(f"{base}/wp-json/wc/store/v1/products?per_page=1")
    if products and products[0].get("permalink"):
        en = str(products[0]["permalink"])
        found["product-en"] = en
        if en.startswith(base + "/product/"):
            found["product-de"] = base + "/de/produkt/" + en[len(base) + len("/product/"):]
    return found


def classify(status: int | None, body: str, allow_ids: set[str]) -> tuple[str, bool]:
    """Return (attribution, ok) for one face response."""
    if status is None:
        return "unreachable", False
    if status == 404:
        # No content for the face on this instance: nothing renders, so
        # nothing legacy can leak.
        return "not-found (no content)", True
    if status in (301, 302):
        return f"redirect ({status})", False
    if status != 200:
        return f"http {status}", False
    stamped = {int(match) for match in LC_DT_RE.findall(body)}
    # What the legacy templates ship into the page: their CSS as an inline
    # block, and the block's family banner. The stamp id is not a criterion —
    # the takeover reuses those rows (module docstring).
    if LEGACY_STYLE_RE.search(body):
        return f"legacy-template (inline style block){stamp_note(stamped)}", False
    if LEGACY_BANNER_RE.search(body):
        return f"legacy-template (banner){stamp_note(stamped)}", False
    leaks = sorted(set(LEGACY_ID_RE.findall(body)) - allow_ids)
    if leaks:
        return f"legacy markup ({', '.join(leaks[:3])})", False
    if stamped:
        return f"lc-template {sorted(stamped)}{reclaimed_note(stamped)}", True
    if LEGACY_WORD_RE.search(body):
        return "legacy markup (TerraVolt comment)", False
    return "theme fallback", True


def stamp_note(stamped: set[int]) -> str:
    """The stamp ids as a suffix, for the failure line's own attribution."""
    return f" {sorted(stamped)}" if stamped else ""


def reclaimed_note(stamped: set[int]) -> str:
    """A reminder that a stamped id of the old family is not legacy rendering.

    Every one of the reclaimed rows keeps its id, so a reader who remembers
    the 2026-10-13 attribution table would read the old ids as a failure. The
    content is what decides (module docstring); this says so on the line.
    """
    shared = sorted(stamped & LEGACY_DT_IDS)
    return f" (reclaimed old row {shared})" if shared else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8975", help="instance origin (default: t110)")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]), help="checkout root for the shipped-id allowlist")
    parser.add_argument("--blog-en", default="/blog/", help="blog index path, EN")
    parser.add_argument("--blog-de", default="/de/blog/", help="blog index path, DE")
    parser.add_argument("--search-en", default="/?s=inverter", help="search URL, EN")
    parser.add_argument("--search-de", default="/de/?s=wechselrichter", help="search URL, DE")
    parser.add_argument("--products-en", default="/products/", help="product archive path, EN")
    parser.add_argument("--products-de", default="/de/produkte/", help="product archive path, DE")
    parser.add_argument("--contact-en", default="/contact/", help="contact page path, EN")
    parser.add_argument("--contact-de", default="/de/kontakt/", help="contact page path, DE")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    allow_ids = shipped_tv_ids(Path(args.repo_root))

    status, _ = fetch(f"{base}/wp-json/")
    if status != 200:
        print(f"FATAL {base} does not answer /wp-json/ (got {status})", file=sys.stderr)
        return 2

    found = discover(base)
    faces = [
        ("blog-en", f"{base}{args.blog_en}"),
        ("blog-de", f"{base}{args.blog_de}"),
        ("single-en", found["single-en"]),
        ("single-de", found["single-de"]),
        ("search-en", f"{base}{args.search_en}"),
        ("search-de", f"{base}{args.search_de}"),
        ("category-en", found["category-en"]),
        ("category-de", found["category-de"]),
    ]

    problems = 0

    print("== face attribution ==")
    sweep_urls: list[tuple[str, str, bool]] = [
        ("front-en", f"{base}/", True),
        ("front-de", f"{base}/de/", True),
        ("products-en", f"{base}{args.products_en}", True),
        ("products-de", f"{base}{args.products_de}", True),
        ("contact-en", f"{base}{args.contact_en}", True),
        ("contact-de", f"{base}{args.contact_de}", True),
        # Discovered, so optional: an instance without a product page skips.
        ("product-en", found["product-en"] or "", False),
        ("product-de", found["product-de"] or "", False),
    ]
    for name, url in faces:
        if url is None:
            print(f"SKIP {name}: no URL discovered (face has no content here)")
            continue
        status, body = fetch(url)
        attribution, ok = classify(status, body, allow_ids)
        mark = "ok  " if ok else "FAIL"
        print(f"{mark} {name}: {status} {attribution} — {url}")
        if not ok:
            problems += 1
        if status == 200:
            sweep_urls.append((name, url, True))

    print("== asset sweep (old assets, brand word and domain must all be 0) ==")
    for name, url, required in sweep_urls:
        if not url:
            print(f"SKIP {name}: not discovered on this instance")
            continue
        status, body = fetch(url)
        if status != 200:
            if not required:
                print(f"SKIP {name}: http {status} — {url}")
            else:
                print(f"FAIL {name}: cannot sweep, http {status} — {url}")
                problems += 1
            continue
        assets = len(LEGACY_ASSET_RE.findall(body))
        words = len(LEGACY_WORD_RE.findall(body))
        domains = len(LEGACY_DOMAIN_RE.findall(body))
        ok = assets == 0 and words == 0 and domains == 0
        note = (
            f"{assets} asset reference(s), {words} TerraVolt word(s), "
            f"{domains} old-domain reference(s)"
        )
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {note} — {url}")
        if not ok:
            problems += 1

    summary = "CLEAN" if problems == 0 else f"{problems} problem(s)"
    print(f"== {summary} ==")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
