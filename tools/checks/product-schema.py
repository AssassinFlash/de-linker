#!/usr/bin/env python3
"""A product page carries exactly one Product node, and it is the product's.

Two assertions over plain HTTP, no authentication:

1. Count: the page's JSON-LD holds exactly one schema.org `Product` node.
   Blocks are not the count — a single `@graph` holds two contradictory nodes
   as readily as two blocks do — and a block that does not parse is a failure,
   not a zero. Two nodes is the failure this check exists for: SEOPress PRO's
   stored product template (`seopress_schemas`, rule `post_type equal product`)
   says every product is made by this company, and this tree emits the real
   one beside it.

2. Identity: that node's `brand` is not the site name, and it carries a `sku`.
   The stored template's brand is the site name ("Linker") and it has no sku;
   the node this tree emits carries the manufacturer's name and the product's
   sku. A page with one node that is still the stored template fails here.

Discovery uses the public Store API, so the script runs against any instance
of this snapshot family without a fixture: the default page is the first
in-stock product. `--product` repeats and overrides discovery; pass it twice
to check two pages. `--site-name` overrides the name read from the homepage's
`WebSite` node, which is where this site publishes it.

Usage:
    python3 tools/checks/product-schema.py [--base http://127.0.0.1:8975]
    python3 tools/checks/product-schema.py --product /product/<slug>/ --product /product/<other>/

Exit code: 0 = every checked page is clean, 1 = a page failed an assertion,
2 = the instance did not answer or no product page could be found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# WordPress writes the type attribute quoted and in either style, and not
# always first, so neither is assumed here.
LD_JSON = re.compile(
    r"<script[^>]*type=[\"']?application/ld\+json[\"']?[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)

PRODUCT = "Product"
TIMEOUT = 30


def fetch(url: str) -> tuple[int | None, str]:
    """Return (status, body). status is None when the request itself failed."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "product-schema-check/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace") if error.fp else ""
        return error.code, body
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, ""


def fetch_json(url: str) -> object | None:
    status, body = fetch(url)
    if status != 200:
        return None
    try:
        parsed: object = json.loads(body)
    except json.JSONDecodeError:
        return None
    return parsed


def product_nodes(value: object) -> list[dict[str, object]]:
    """Every schema.org Product node in one parsed JSON-LD value."""
    if isinstance(value, list):
        found: list[dict[str, object]] = []
        for item in value:
            found.extend(product_nodes(item))
        return found
    if not isinstance(value, dict):
        return []
    found = []
    types = value.get("@type")
    if types == PRODUCT or (isinstance(types, list) and PRODUCT in types):
        found.append(value)
    graph = value.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            found.extend(product_nodes(item))
    return found


def parse_page(html: str) -> tuple[list[dict[str, object]], int]:
    """(Product nodes, JSON-LD blocks that did not parse) in a page."""
    nodes: list[dict[str, object]] = []
    unreadable = 0
    for block in LD_JSON.findall(html):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            unreadable += 1
            continue
        nodes.extend(product_nodes(parsed))
    return nodes, unreadable


def brand_name(node: dict[str, object]) -> str:
    """The brand a Product node claims, as text. Absent is an empty string."""
    brand = node.get("brand")
    if isinstance(brand, str):
        return brand.strip()
    if isinstance(brand, dict):
        name = brand.get("name")
        return name.strip() if isinstance(name, str) else ""
    return ""


def sku_of(node: dict[str, object]) -> str:
    sku = node.get("sku")
    return sku.strip() if isinstance(sku, str) else ""


def site_name(base: str) -> str | None:
    """The site name, from the homepage's WebSite node. None if it is not there."""
    status, html = fetch(base + "/?cbq=product-schema-site")
    if status != 200:
        return None
    for block in LD_JSON.findall(html):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        for node in [parsed] if isinstance(parsed, dict) else []:
            types = node.get("@type")
            if types == "WebSite" or (isinstance(types, list) and "WebSite" in types):
                name = node.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
    return None


def discover(base: str) -> str | None:
    """The path of the first in-stock product, or the first product there is."""
    products = fetch_json(f"{base}/wp-json/wc/store/v1/products?per_page=20")
    if not isinstance(products, list) or not products:
        return None
    in_stock = [
        item
        for item in products
        if isinstance(item, dict) and item.get("is_in_stock") and item.get("permalink")
    ]
    chosen = (
        in_stock[0]
        if in_stock
        else next(
            (
                item
                for item in products
                if isinstance(item, dict) and item.get("permalink")
            ),
            None,
        )
    )
    if not isinstance(chosen, dict):
        return None
    permalink = str(chosen["permalink"])
    path = urllib.parse.urlparse(permalink).path
    return path or None


def check(base: str, path: str, name: str) -> tuple[bool, str]:
    """One page. The string is the report line; False is a failed assertion."""
    url = base.rstrip("/") + path
    separator = "&" if "?" in url else "?"
    status, html = fetch(url + separator + "cbq=product-schema")
    if status is None:
        return False, f"{path}: the instance did not answer"
    if status != 200:
        return False, f"{path}: answered {status}"
    nodes, unreadable = parse_page(html)
    if unreadable:
        return False, f"{path}: {unreadable} JSON-LD block(s) did not parse"
    if len(nodes) != 1:
        brands = ", ".join(brand_name(node) or "?" for node in nodes) or "none"
        return (
            False,
            f"{path}: {len(nodes)} Product node(s) (brand: {brands}), expected 1",
        )
    node = nodes[0]
    brand = brand_name(node)
    sku = sku_of(node)
    problems: list[str] = []
    if not brand:
        problems.append("brand is missing")
    elif brand.casefold() == name.casefold():
        problems.append(f"brand is the site name ({brand!r})")
    if not sku:
        problems.append("sku is missing")
    if problems:
        return False, f"{path}: 1 Product node, " + "; ".join(problems)
    return True, f"{path}: 1 Product node, brand={brand}, sku={sku}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--base",
        default="http://127.0.0.1:8975",
        help="instance address (default: the reference instance, t110)",
    )
    parser.add_argument(
        "--product",
        action="append",
        default=[],
        help="product path to check; repeat for several. Default: the first in-stock product",
    )
    parser.add_argument(
        "--site-name",
        default=None,
        help="the site name a product brand must not equal (default: the homepage WebSite name)",
    )
    args = parser.parse_args()
    base = args.base.rstrip("/")

    paths = list(args.product)
    if not paths:
        found = discover(base)
        if found is None:
            print(f"{base}: no product page found", flush=True)
            return 2
        paths = [found]

    name = args.site_name if args.site_name else site_name(base)
    if not name:
        print(f"{base}: the site name could not be read", flush=True)
        return 2
    print(f"site name: {name}", flush=True)

    ok = True
    answered = True
    for path in paths:
        if not path.startswith("/"):
            path = "/" + path
        passed, line = check(base, path, name)
        print(line, flush=True)
        ok = ok and passed
        if "did not answer" in line:
            answered = False
    if not answered and not ok:
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
