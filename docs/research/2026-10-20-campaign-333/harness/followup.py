#!/usr/bin/env python3
"""Second pass for campaign #333.

Appends retest rows to the evidence log. Never POSTs a matching inquiry
digest, never calls the contact route, and never sends mail.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("battery", HERE / "run_battery.py")
battery = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(battery)

b = battery


def delete_approved_conversations() -> str:
    return b.wp_eval(
        r'''
$ids = get_posts(array(
  "post_type" => "linker_conversation",
  "author" => 45,
  "post_status" => "any",
  "posts_per_page" => -1,
  "fields" => "ids",
));
foreach ($ids as $id) { wp_delete_post((int) $id, true); }
echo wp_json_encode(array("deleted" => count($ids)));
'''
    )


def turn(case_id: str, secrets: dict, page: dict, question: str, grade) -> None:
    delete_approved_conversations()
    payload = {
        "locale": "en",
        "messages": [{"role": "user", "content": question}],
        "page": page,
    }
    headers = b.auth_headers("approved", secrets)
    headers["Content-Type"] = "application/json"
    result = b.request(
        f"{b.WP}/wp-json/linker-ai/v1/genie/turn",
        method="POST",
        headers=headers,
        body=json.dumps(payload).encode(),
        timeout=180,
    )
    body = b.json_body(result) or {}
    meta, blocks = b.parse_stream(body.get("stream") or "")
    text = b.answer_text(blocks)
    prices = b.price_texts(blocks)
    verdict, note, stale = grade(result, text, prices)
    b.case(
        case_id,
        "approved",
        {"message": question, "page": page},
        result,
        verdict,
        note,
        price=" | ".join(prices),
        stale=stale,
        meta=meta or {"status": result["status"], "url": result["url"], "code": body.get("code")},
        blocks=blocks,
    )


def main() -> None:
    secrets = b.mint(b.load_accounts())
    b.remint(secrets)

    token = b.urllib.parse.quote(secrets["tokens"]["approved"], safe="")
    url = (
        f"{b.WP}/wp-json/wp-abilities/v1/abilities/linker/get-product/run"
        f"?input[product_id]={b.PRICED}&input[lang]=en&X-Linker-User-Context={token}"
    )
    result = b.request(url, headers={"Accept": "application/json"})
    result["json"] = b.json_body(result)
    result["body"] = None
    blob = json.dumps(result["json"], ensure_ascii=False) if result["json"] is not None else ""
    leaked = b.euro(blob)
    b.case(
        "retest-token-query-only",
        "visitor",
        {"where": "query parameter, not the header"},
        result,
        "defect" if leaked else "pass",
        f"status {result['status']}; leaked={leaked}",
        price="leaked" if leaked else "",
    )

    for lang, page in (
        ("en", f"{b.WP}/compare-products/?ids={b.PRICED},{b.RFQ}"),
        ("de", f"{b.WP}/de/produkte-vergleichen/?ids={b.PRICED},{b.RFQ}"),
    ):
        result = b.request(page, headers={"Accept": "text/html"})
        raw = result["body"].decode(errors="replace")
        row = b.compare_price_row(raw)
        sentence = b.GATE[("visitor", lang)] in row
        amount = bool(b.AMOUNT.search(row))
        b.case(
            f"retest-page-visitor-compare-{lang}",
            "visitor",
            {"url": page},
            result,
            "pass" if sentence and not amount else "defect",
            f"aria_or_row_sentence={sentence} amount={amount} row_len={len(row)}",
            price="" if not amount else "amount in the price row",
        )

    for lang, page, product in (
        ("en", f"{b.WP}/product/saj-h2-10k-t3/", b.PRICED),
        ("de", f"{b.WP}/de/produkt/saj-h2-10k-t3/", b.PRICED),
    ):
        result = b.request(page, headers={"Accept": "text/html", **b.cookie_header("approved", secrets)})
        text = b.visible_text(result["body"].decode(errors="replace")).replace("\xa0", " ")
        amount = bool(b.re.search(r"1[.,]680", text))
        gate = b.GATE[("visitor", lang)] in text
        looked = b.ability(
            "linker/get-product",
            {"product_id": product, "lang": lang},
            {**b.auth_headers("approved", secrets), "X-Linker-User-Context": secrets["tokens"]["approved"]},
        )
        line = str(b.commerce_of(looked).get("price_line") or "")
        b.case(
            f"retest-page-approved-priced-{lang}",
            "approved",
            {"url": page},
            result,
            "pass" if amount and not gate else "defect",
            f"amount={amount} visitor_gate={gate} ability={line!r}",
            price=line,
        )

    store = b.request(
        f"{b.WP}/wp-json/wc/store/v1/products?include={b.PRICED},{b.RFQ}&per_page=2&lang=de",
        headers={"Accept": "application/json"},
    )
    products = b.json_body(store) or []
    links = [
        {"id": item.get("id"), "permalink": item.get("permalink")}
        for item in products
        if isinstance(item, dict)
    ] if isinstance(products, list) else []
    de_link = all("/de/" in str(item["permalink"]) for item in links) and len(links) == 2
    b.case(
        "retest-store-visitor-de-links",
        "visitor",
        {"url": store["url"]},
        store,
        "pass" if de_link else "defect",
        json.dumps(links, ensure_ascii=False),
        price=json.dumps(links, ensure_ascii=False),
    )

    question = "What is the net price of the SAJ H2-10K-T3?"

    def grade_current(result, text, prices):
        if result["status"] != 200:
            return "defect", f"no answer status {result['status']}", False
        if b.euro(text):
            return "defect", "price amount in the prose", False
        shown = " | ".join(prices)
        if any(b.re.search(r"1[.,]680", price) for price in prices):
            return "pass", shown, False
        return "defect", f"card {prices!r}", False

    turn(
        "retest-turn-approved-en-compare",
        secrets,
        {"type": "other", "url": f"{b.WP}/compare-products/?ids={b.PRICED},{b.RFQ}", "title": "Compare"},
        question,
        grade_current,
    )
    turn(
        "retest-turn-approved-en-config",
        secrets,
        {"type": "solution", "url": f"{b.WP}/solution-configurator/", "title": "Solution Configurator"},
        question,
        grade_current,
    )

    b.wp_eval(
        r'''
foreach (array(4107, 6628) as $id) {
  $product = wc_get_product($id);
  $product->set_regular_price("1701");
  $product->set_price("1701");
  $product->save();
}
echo "set";
'''
    )
    try:

        def grade_1701(result, text, prices):
            if result["status"] != 200:
                return "defect", f"no answer status {result['status']}", False
            stale = any(b.re.search(r"1[.,]680", price) for price in prices) or bool(b.re.search(r"1[.,]680", text))
            current = any("1,701" in price or "1701" in price for price in prices)
            if b.euro(text) or stale or not current:
                return "defect", " | ".join(prices) or text[:240], stale
            return "pass", " | ".join(prices), False

        turn(
            "retest-turn-approved-after-price-change",
            secrets,
            {"type": "home", "url": f"{b.WP}/", "title": "Linker"},
            question,
            grade_1701,
        )
    finally:
        b.wp_eval(
            r'''
foreach (array(4107, 6628) as $id) {
  $product = wc_get_product($id);
  $product->set_regular_price("1680");
  $product->set_price("1680");
  $product->set_stock_status("instock");
  $product->save();
}
echo "restored";
'''
        )

    b.run_mutation(secrets)

    b.wp_eval(
        r'''
add_filter("pre_wp_mail", static function () { return true; });
foreach (array(1957, 6800) as $id) {
  $product = wc_get_product($id);
  if ($product instanceof WC_Product) {
    $product->set_stock_status("onbackorder");
    $product->save();
  }
}
echo "back";
'''
    )
    pages = {
        1957: f"{b.WP}/product/goodwe-gw208-9-bat-lcd-g10/",
        6800: f"{b.WP}/de/produkt/goodwe-gw208-9-bat-lcd-g10/",
    }
    for product_id, page in pages.items():
        looked = b.ability(
            "linker/get-product",
            {"product_id": product_id, "lang": "de" if product_id == 6800 else "en"},
            {"Accept": "application/json"},
        )
        commerce = b.commerce_of(looked)
        fetched = b.request(page, headers={"Accept": "text/html"})
        text = b.visible_text(fetched["body"].decode(errors="replace"))
        badge_in = ("In stock" in text) or ("Auf Lager" in text)
        badge_out = ("Currently unavailable" in text) or ("Derzeit nicht verfügbar" in text)
        agrees = (commerce.get("in_stock") is True and badge_in and not badge_out) or (
            commerce.get("in_stock") is False and badge_out and not badge_in
        )
        b.case(
            f"retest-stock-backorder-{product_id}",
            "visitor",
            {"product_id": product_id, "woo_status": "onbackorder", "url": page},
            looked,
            "pass" if agrees else "defect",
            f"in_stock={commerce.get('in_stock')} page_in={badge_in} page_out={badge_out}",
            stock="in_stock" if commerce.get("in_stock") else "out_of_stock",
        )

    b.wp_eval(
        r'''
add_filter("pre_wp_mail", static function () { return true; });
$ids = wc_get_orders(array("customer_id" => array(43, 44, 45), "limit" => -1, "return" => "ids"));
foreach ($ids as $id) { wp_delete_post((int) $id, true); }
echo wp_json_encode(array("deleted_orders" => array_values($ids)));
'''
    )
    print(b.wp_eval(
        r'''
$out = array();
foreach (array(4107, 6628, 1957, 6800) as $id) {
  $out[$id] = array(
    "regular" => get_post_meta($id, "_regular_price", true),
    "stock" => get_post_meta($id, "_stock_status", true),
  );
}
echo wp_json_encode($out);
'''
    ))


if __name__ == "__main__":
    main()
