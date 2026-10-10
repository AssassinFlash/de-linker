"""Pull the #9 migration fixtures from the live site, read-only.

Every request is a GET: the REST API with the credentials in
~/.config/terravolt-builder/rest-de.json (never printed), the public pages with
a cache-busting query (LiteSpeed sits in front of the HTML). The fixture is the
subset of the live content that the i18n migration reads: English objects with
their `_linker_de_*` German, the German page slugs, and the German that the old
plugin renders for SEO titles, descriptions and category names.

    python3 plugins/linker-i18n/tests/fixtures/pull_live.py

writes plugins/linker-i18n/tests/fixtures/live/*.json.
"""

from __future__ import annotations

import base64
import datetime
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

CREDENTIALS = Path.home() / ".config/terravolt-builder/rest-de.json"
OUT = Path(__file__).resolve().parent / "live"
USER_AGENT = "de-linker-t9-fixtures/1.0"

# The fixture subset: one product per live product category (all ten DE
# category URLs of /de-sitemap.xml are covered), the pages that carry the
# same-slug, child-page, shop, cart and checkout cases, and one post.
PRODUCT_IDS = [6528, 6522, 4106, 1957, 1959, 3618, 6530, 2281, 3587]
PAGE_IDS = [13, 14, 28, 862, 874, 1034, 1035, 1036, 1037, 5385]
POST_IDS = [551]
# The German the old plugin stores in post meta.
LEGACY_META = re.compile(r"^(_linker_de_|_tv_legacy_acf_json$|_seopress_titles_)")


def _credentials() -> tuple[str, str]:
    config = json.loads(CREDENTIALS.read_text())
    token = base64.b64encode(
        f"{config['username']}:{config['application_password']}".encode()
    ).decode()
    return config["site_url"].rstrip("/"), "Basic " + token


SITE, AUTHORIZATION = _credentials()


def get(
    path: str,
    params: dict[str, Any] | None = None,
    *,
    auth: bool = True,
    headers: dict[str, str] | None = None,
) -> bytes:
    """One GET; the only HTTP method this script has."""
    url = SITE + path
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
    request = urllib.request.Request(
        url, method="GET", headers={"User-Agent": USER_AGENT, **(headers or {})}
    )
    if auth:
        request.add_header("Authorization", AUTHORIZATION)
    with urllib.request.urlopen(request, timeout=90) as response:
        body: bytes = response.read()
        return body


def get_json(
    path: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """A REST GET.

    Two live quirks are tolerated: the host now and then answers with an empty
    body (up to three tries), and on the blog page a template plugin prints a
    <style> block before the JSON (the JSON is the value that runs to the end).
    """
    decoder = json.JSONDecoder()
    for attempt in range(3):
        body = get(path, params, headers=headers).decode()
        for match in re.finditer(r"[{\[]", body):
            try:
                data, end = decoder.raw_decode(body, match.start())
            except json.JSONDecodeError:
                continue
            if body[end:].strip() == "":
                return data
        if attempt < 2:
            time.sleep(5)
    raise ValueError(f"no JSON in the answer to {path}")


def get_page(url: str) -> str:
    """A public page, past the page cache."""
    separator = "&" if "?" in url else "?"
    return get(
        url.replace(SITE, "") + f"{separator}cbq={time.time_ns()}", auth=False
    ).decode()


def head_facts(page: str) -> dict[str, Any]:
    """What the head of a rendered page says: title, description, canonical, hreflang, h1."""

    def first(pattern: str) -> str | None:
        match = re.search(pattern, page, re.S)
        return html.unescape(match.group(1)).strip() if match else None

    h1 = first(r"<h1[^>]*>(.*?)</h1>")
    return {
        "title": first(r"<title>(.*?)</title>"),
        "description": first(r'<meta name="description" content="([^"]*)"'),
        "canonical": first(r'<link rel="canonical" href="([^"]*)"'),
        "hreflang": dict(re.findall(r'hreflang="([^"]+)" href="([^"]+)"', page)),
        "h1": re.sub(r"<[^>]+>", "", h1).strip() if h1 else None,
        "html_lang": first(r"<html[^>]* lang=\"([^\"]+)\""),
    }


def product(product_id: int) -> dict[str, Any]:
    data = get_json(f"/wp-json/wc/v3/products/{product_id}")
    en_page = get_page(data["permalink"])
    en_head = head_facts(en_page)
    de_url = en_head["hreflang"].get("de")
    return {
        "id": data["id"],
        "name": data["name"],
        "slug": data["slug"],
        "status": data["status"],
        "type": data["type"],
        "sku": data["sku"],
        "regular_price": data["regular_price"],
        "sale_price": data["sale_price"],
        "tax_status": data["tax_status"],
        "tax_class": data["tax_class"],
        "manage_stock": data["manage_stock"],
        "stock_status": data["stock_status"],
        "weight": data["weight"],
        "dimensions": data["dimensions"],
        "menu_order": data["menu_order"],
        "description": data["description"],
        "short_description": data["short_description"],
        "categories": [category["id"] for category in data["categories"]],
        "attributes": [
            {
                "id": attribute["id"],
                "name": attribute["name"],
                "position": attribute["position"],
                "visible": attribute["visible"],
                "options": attribute["options"],
            }
            for attribute in data["attributes"]
        ],
        "meta": {
            item["key"]: item["value"]
            for item in data["meta_data"]
            if LEGACY_META.match(item["key"])
        },
        "live": {
            "en_url": data["permalink"],
            "en": en_head,
            "de_url": de_url,
            "de": head_facts(get_page(de_url)) if de_url else None,
        },
    }


def rendered_content(raw: str, english_page: str, german_page: str) -> str | None:
    """The German counterpart of `raw` in the rendered German page.

    The old plugin does not swap the body in REST (the German header only
    changes the title), so the German body is cut out of the German page: the
    English body appears verbatim in the English page, and the German page
    starts and ends it with the same markup (the first and last 80 bytes, a
    script tag on the LiveCanvas pages). None when that does not hold.
    """
    raw = raw.strip()
    if len(raw) < 200 or raw not in english_page:
        return None
    head, tail = raw[:80], raw[-80:]
    start = german_page.find(head)
    end = german_page.find(tail, start)
    if start < 0 or end < 0:
        return None
    return german_page[start : end + len(tail)]


def post(post_type: str, post_id: int) -> dict[str, Any]:
    base = "pages" if post_type == "page" else "posts"
    fields = "id,slug,status,parent,menu_order,template,title,content,excerpt,link,meta,categories"
    en = get_json(
        f"/wp-json/wp/v2/{base}/{post_id}", {"context": "edit", "_fields": fields}
    )
    # The old plugin answers REST in German when asked with this header, for
    # the title and the excerpt; the body stays English (see rendered_content()).
    de = get_json(
        f"/wp-json/wp/v2/{base}/{post_id}",
        {"_fields": "id,title,excerpt"},
        headers={"X-Linker-Locale": "de"},
    )
    english_page = get_page(en["link"])
    en_head = head_facts(english_page)
    de_url = en_head["hreflang"].get("de")
    german_page = get_page(de_url) if de_url else ""
    meta = en.get("meta") or {}
    return {
        "id": en["id"],
        "type": post_type,
        "slug": en["slug"],
        "status": en["status"],
        "parent": en.get("parent", 0),
        "menu_order": en.get("menu_order", 0),
        "template": en.get("template", ""),
        "categories": en.get("categories", []),
        "title": en["title"]["raw"],
        "content": en["content"]["raw"],
        "excerpt": en["excerpt"]["raw"],
        "seo": {
            key: meta.get(key, "")
            for key in ("_seopress_titles_title", "_seopress_titles_desc")
        },
        "de": {
            "title": html.unescape(de["title"]["rendered"]),
            # Only a real excerpt: with none, WordPress renders the start of the body.
            "excerpt_rendered": de["excerpt"]["rendered"]
            if en["excerpt"]["raw"].strip()
            else "",
            "content_rendered": rendered_content(
                en["content"]["raw"], english_page, german_page
            ),
        },
        "live": {
            "en_url": en["link"],
            "en": en_head,
            "de_url": de_url,
            "de": head_facts(german_page) if german_page else None,
        },
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    products = [product(product_id) for product_id in PRODUCT_IDS]
    pages = [post("page", page_id) for page_id in PAGE_IDS]
    posts = [post("post", post_id) for post_id in POST_IDS]

    category_ids = {category for item in products for category in item["categories"]}
    all_categories = {
        category["id"]: category
        for category in get_json(
            "/wp-json/wc/v3/products/categories", {"per_page": 100}
        )
    }
    for category_id in list(category_ids):
        parent = all_categories[category_id]["parent"]
        while parent:
            category_ids.add(parent)
            parent = all_categories[parent]["parent"]
    product_categories = []
    for category_id in sorted(category_ids):
        category = all_categories[category_id]
        path = [category["slug"]]
        parent = category["parent"]
        while parent:
            path.insert(0, all_categories[parent]["slug"])
            parent = all_categories[parent]["parent"]
        en_url = f"{SITE}/product-category/{'/'.join(path)}/"
        en_head = head_facts(get_page(en_url))
        de_url = en_head["hreflang"].get("de")
        product_categories.append(
            {
                "id": category["id"],
                "name": html.unescape(category["name"]),
                "slug": category["slug"],
                "parent": category["parent"],
                "description": category["description"],
                "menu_order": category["menu_order"],
                "live": {
                    "en_url": en_url,
                    "en": en_head,
                    "de_url": de_url,
                    "de": head_facts(get_page(de_url)) if de_url else None,
                },
            }
        )

    post_categories = [
        {
            "id": term["id"],
            "name": html.unescape(term["name"]),
            "slug": term["slug"],
            "parent": term["parent"],
            "description": term["description"],
        }
        for term in get_json("/wp-json/wp/v2/categories", {"per_page": 100})
        if term["id"] in {category for item in posts for category in item["categories"]}
    ]

    attributes = []
    used = {
        (attribute["id"], option)
        for item in products
        for attribute in item["attributes"]
        for option in attribute["options"]
    }
    for attribute in get_json("/wp-json/wc/v3/products/attributes"):
        terms: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = get_json(
                f"/wp-json/wc/v3/products/attributes/{attribute['id']}/terms",
                {"per_page": 100, "page": page},
            )
            terms += batch
            if len(batch) < 100:
                break
            page += 1
        attributes.append(
            {
                "id": attribute["id"],
                "name": attribute["name"],
                "slug": attribute["slug"],
                "type": attribute["type"],
                "order_by": attribute["order_by"],
                "has_archives": attribute["has_archives"],
                "terms": [
                    {
                        "id": term["id"],
                        "name": html.unescape(term["name"]),
                        "slug": term["slug"],
                        "description": term["description"],
                        "menu_order": term["menu_order"],
                    }
                    for term in terms
                    if (attribute["id"], html.unescape(term["name"])) in used
                ],
            }
        )

    settings = get_json("/wp-json/wp/v2/settings")
    advanced = {
        item["id"]: item.get("value")
        for item in get_json("/wp-json/wc/v3/settings/advanced")
    }
    products_settings = {
        item["id"]: item.get("value")
        for item in get_json("/wp-json/wc/v3/settings/products")
    }
    general = {
        item["id"]: item.get("value")
        for item in get_json("/wp-json/wc/v3/settings/general")
    }
    site = {
        "show_on_front": settings["show_on_front"],
        "page_on_front": settings["page_on_front"],
        "page_for_posts": settings["page_for_posts"],
        "woocommerce_shop_page_id": products_settings.get("woocommerce_shop_page_id"),
        "woocommerce_cart_page_id": advanced.get("woocommerce_cart_page_id"),
        "woocommerce_checkout_page_id": advanced.get("woocommerce_checkout_page_id"),
        "woocommerce_myaccount_page_id": advanced.get("woocommerce_myaccount_page_id"),
        "woocommerce_currency": general.get("woocommerce_currency"),
        "woocommerce_default_country": general.get("woocommerce_default_country"),
    }

    sitemap = get_page(SITE + "/de-sitemap.xml")
    de_urls = re.findall(r"<loc>([^<]+)</loc>", sitemap)

    fetched_at = datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat()
    files = {
        "products.json": products,
        "pages.json": pages,
        "posts.json": posts,
        "product-categories.json": product_categories,
        "post-categories.json": post_categories,
        "attributes.json": attributes,
        "site.json": site,
        "de-sitemap.json": de_urls,
        "provenance.json": {
            "site": SITE,
            "fetched_at": fetched_at,
            "method": "GET only: REST with an application password; public pages with ?cbq=<ns>",
            "products": PRODUCT_IDS,
            "pages": PAGE_IDS,
            "posts": POST_IDS,
        },
    }
    for name, data in files.items():
        (OUT / name).write_text(
            json.dumps(data, ensure_ascii=False, indent="\t", sort_keys=True) + "\n"
        )
        print(f"wrote {name}")


if __name__ == "__main__":
    main()
