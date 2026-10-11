#!/usr/bin/env python3
"""A mock ERP driving the stock push channel end to end (ticket #69).

Pushes a scripted sequence (normal, out of stock, recovery) at a local
instance's linker/v1/stock endpoint and asserts what a visitor sees change:
the catalogue's in-stock badge, the in-stock-only listing, and the solution
draft gate (WooCommerce's add-to-cart). It is a just recipe's helper
(`just mock-erp <instance>`), not a plugin feature: outside WordPress, it
speaks plain HTTP to the instance like a real ERP would.

Stdlib only; every assertion prints a PASS line and a failure stops the run
with a non-zero exit.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

IN_STOCK = "In stock"
OUT_OF_STOCK = "Currently unavailable"


class Erp:
    """The HTTP side of the mock ERP."""

    def __init__(self, base: str, key: str) -> None:
        self.base = base.rstrip("/")
        self.key = key
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def _request(self, path: str, data: dict[str, str] | None = None) -> tuple[int, str]:
        url = self.base + path
        body = urllib.parse.urlencode(data).encode() if data else None
        request = urllib.request.Request(url, data=body)
        if body is not None:
            request.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with self.opener.open(request, timeout=30) as answer:
                return answer.status, answer.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8", "replace")

    def push(self, items: list[dict[str, object]], key: str | None = None) -> tuple[int, dict[str, object]]:
        """POST one batch at the stock endpoint; answers status and JSON."""
        request = urllib.request.Request(
            self.base + "/wp-json/linker/v1/stock",
            data=json.dumps({"items": items}).encode(),
            method="POST",
        )
        request.add_header("Content-Type", "application/json")
        request.add_header("X-Linker-Stock-Key", self.key if key is None else key)
        try:
            with self.opener.open(request, timeout=60) as answer:
                return answer.status, json.loads(answer.read().decode())
        except urllib.error.HTTPError as error:
            payload = error.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                parsed = {"raw": payload}
            return error.code, parsed

    def page(self, path: str) -> str:
        status, html = self._request(path if path.startswith("/") else "/" + path)
        if status != 200:
            raise AssertionError(f"GET {path} answered {status}, expected 200")
        return html

    def add_to_cart(self, product_id: int) -> dict[str, object]:
        """The draft gate: WooCommerce's own add-to-cart AJAX verdict."""
        _, payload = self._request("/?wc-ajax=add_to_cart", {"product_id": str(product_id), "quantity": "1"})
        return json.loads(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Instance address, e.g. http://127.0.0.1:8933")
    parser.add_argument("--key", required=True, help="The push key the recipe set on the instance")
    parser.add_argument(
        "--payload",
        required=True,
        help='JSON from WP-CLI: {"products": {"SKU": {"id": N, "url": "...", "listing": "..."}}} (two SKUs)',
    )
    options = parser.parse_args()

    payload = json.loads(options.payload)
    products: dict[str, dict[str, object]] = payload["products"]
    if len(products) < 2:
        raise SystemExit("mock-erp needs two stock-managed products with SKUs on the instance")
    (subject_sku, subject), (bystander_sku, bystander) = list(products.items())[:2]

    def path_of(url: object) -> str:
        return "/" + urllib.parse.urlparse(str(url)).path.lstrip("/")

    subject_path = path_of(subject["url"])
    subject_listing = path_of(subject["listing"])
    bystander_listing = path_of(bystander["listing"])
    subject_id = int(subject["id"])

    erp = Erp(options.base, options.key)
    passed = 0

    def check(what: str, ok: bool, detail: str = "") -> None:
        nonlocal passed
        if not ok:
            raise AssertionError(f"FAIL {what}{': ' + detail if detail else ''}")
        passed += 1
        print(f"PASS {what}")

    # 1. A wrong key is rejected; the channel has exactly one credential.
    status, body = erp.push([{"sku": subject_sku, "qty": 1}], key="not-the-key")
    check("wrong key rejected with 401", status == 401 and body.get("code") == "linker_stock_unauthorized", f"{status} {body}")

    # 2. Baseline: each SKU sits in its own category archive (the shop page
    #    is paginated; a product's category shows it).
    check("catalogue lists the subject", f'data-sku="{subject_sku}"' in erp.page(subject_listing))
    check("catalogue lists the bystander", f'data-sku="{bystander_sku}"' in erp.page(bystander_listing))
    check("subject page answers", IN_STOCK in erp.page(subject_path) or OUT_OF_STOCK in erp.page(subject_path))

    # 3. Normal push: in stock, visible, addable (9 differs from the
    #    binding's 7, so the row is an applied one).
    status, body = erp.push([{"sku": subject_sku, "qty": 9}])
    check(
        "normal push applied",
        status == 200 and body.get("applied") == 1 and body["results"][0]["stock_status"] == "instock",
        f"{status} {body}",
    )
    check("badge says in stock", IN_STOCK in erp.page(subject_path))
    check("add-to-cart opens", erp.add_to_cart(subject_id).get("error") is not True)

    # 4. Out of stock: the product leaves the catalogue, badge flips, draft gate shuts.
    status, body = erp.push([{"sku": subject_sku, "qty": 0}])
    check(
        "out-of-stock push applied",
        status == 200 and body.get("applied") == 1 and body["results"][0]["stock_status"] == "outofstock",
        f"{status} {body}",
    )
    shop_html = erp.page(subject_listing)
    check("catalogue drops the out-of-stock product", f'data-sku="{subject_sku}"' not in shop_html)
    check("catalogue keeps the bystander", f'data-sku="{bystander_sku}"' in erp.page(bystander_listing))
    check("badge says currently unavailable", OUT_OF_STOCK in erp.page(subject_path))
    check("badge no longer says in stock", IN_STOCK not in erp.page(subject_path))
    check("add-to-cart refuses", erp.add_to_cart(subject_id).get("error") is True)

    # 5. Wrong SKU branch: the unknown row errors, the known row applies.
    status, body = erp.push(
        [
            {"sku": "MOCK-ERP-NO-SUCH-SKU", "qty": 3},
            {"sku": subject_sku, "qty": 2},
        ]
    )
    rows = {row["sku"]: row for row in body.get("results", [])}
    check(
        "unknown sku is a per-row error, the batch is not rolled back",
        status == 200
        and rows.get("MOCK-ERP-NO-SUCH-SKU", {}).get("code") == "unknown_sku"
        and rows.get(subject_sku, {}).get("status") == "applied",
        f"{status} {body}",
    )

    # 6. Idempotency: the same push again is a no-op row.
    status, body = erp.push(
        [
            {"sku": "MOCK-ERP-NO-SUCH-SKU", "qty": 3},
            {"sku": subject_sku, "qty": 2},
        ]
    )
    rows = {row["sku"]: row for row in body.get("results", [])}
    check(
        "same values again are unchanged rows",
        status == 200 and body.get("unchanged") == 1 and rows.get(subject_sku, {}).get("status") == "unchanged",
        f"{status} {body}",
    )

    # 7. A second product pulled by quantity: the state word belongs to
    #    products without managed stock; snapshot products manage stock.
    status, body = erp.push([{"sku": bystander_sku, "qty": 0}])
    check(
        "bystander pulled from the catalogue",
        status == 200 and body.get("applied") == 1 and f'data-sku="{bystander_sku}"' not in erp.page(bystander_listing),
        f"{status} {body}",
    )

    # 8. Recovery: everything comes back.
    status, body = erp.push(
        [
            {"sku": subject_sku, "qty": 12},
            {"sku": bystander_sku, "qty": 10},
        ]
    )
    check("recovery applied", status == 200 and body.get("applied") == 2, f"{status} {body}")
    check("catalogue lists the subject again", f'data-sku="{subject_sku}"' in erp.page(subject_listing))
    check("catalogue lists the bystander again", f'data-sku="{bystander_sku}"' in erp.page(bystander_listing))
    check("badge says in stock again", IN_STOCK in erp.page(subject_path))
    check("add-to-cart opens again", erp.add_to_cart(subject_id).get("error") is not True)

    print(f"\nmock-erp: {passed} assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
