#!/usr/bin/env python3
"""Second pass for campaign #333.

Appends retest rows to the evidence log. Never POSTs a matching inquiry
digest, never calls the contact route, and never sends mail.

The 1701 turn and the order sweep go through the PHP helpers. Orders are
deleted with WC_Order::delete(true) and read back. wp_delete_post does not
remove an HPOS order. Conversations are posts, so wp_delete_post stays.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("battery", HERE / "run_battery.py")
battery = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(battery)

b = battery


def delete_approved_conversations(author: int) -> str:
    return b.wp_eval(
        f"""
$ids = get_posts(array(
  "post_type" => "linker_conversation",
  "author" => {int(author)},
  "post_status" => "any",
  "posts_per_page" => -1,
  "fields" => "ids",
));
foreach ($ids as $id) {{ wp_delete_post((int) $id, true); }}
echo wp_json_encode(array("deleted" => count($ids)));
"""
    )


def turn(
    case_id: str,
    secrets: dict[str, Any],
    page: dict[str, Any],
    question: str,
    grade: Any,
) -> None:
    delete_approved_conversations(b.account_id(secrets["accounts"], "approved"))
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
        timeout=b.TURN_TIMEOUT,
    )
    body = b.json_body(result) or {}
    meta, blocks = b.parse_stream(body.get("stream") or "")
    text = b.answer_text(blocks)
    prices = b.price_texts(blocks)
    verdict, note, stale = grade(result, text, prices)
    b.case(
        case_id,
        state="approved",
        req={"message": question, "page": page},
        result=result,
        verdict=verdict,
        note=note,
        price=" | ".join(prices),
        stale=stale,
        meta=meta
        or {"status": result["status"], "url": result["url"], "code": body.get("code")},
        blocks=blocks,
    )


def grade_current(
    result: dict[str, Any], text: str, prices: list[str]
) -> tuple[str, str, bool]:
    return b.grade_approved_price_turn(result["status"], text, prices)


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
    blob = (
        json.dumps(result["json"], ensure_ascii=False)
        if result["json"] is not None
        else ""
    )
    leaked = b.euro(blob)
    b.case(
        "retest-token-query-only",
        state="visitor",
        req={"where": "query parameter, not the header"},
        result=result,
        verdict="defect" if leaked else "pass",
        note=f"status {result['status']}; leaked={leaked}",
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
            state="visitor",
            req={"url": page},
            result=result,
            verdict="pass" if sentence and not amount else "defect",
            note=f"aria_or_row_sentence={sentence} amount={amount} row_len={len(row)}",
            price="" if not amount else "amount in the price row",
        )

    for lang, page, product in (
        ("en", f"{b.WP}/product/saj-h2-10k-t3/", b.PRICED),
        ("de", f"{b.WP}/de/produkt/saj-h2-10k-t3/", b.PRICED),
    ):
        result = b.request(
            page,
            headers={"Accept": "text/html", **b.cookie_header("approved", secrets)},
        )
        text = b.visible_text(result["body"].decode(errors="replace")).replace(
            "\xa0", " "
        )
        amount = b.priced_amount(text)
        gate = b.GATE[("visitor", lang)] in text
        looked = b.ability(
            "linker/get-product",
            {"product_id": product, "lang": lang},
            {
                **b.auth_headers("approved", secrets),
                "X-Linker-User-Context": secrets["tokens"]["approved"],
            },
        )
        line = str(b.commerce_of(looked).get("price_line") or "")
        b.case(
            f"retest-page-approved-priced-{lang}",
            state="approved",
            req={"url": page},
            result=result,
            verdict="pass" if amount and not gate else "defect",
            note=f"amount={amount} visitor_gate={gate} ability={line!r}",
            price=line,
        )

    store = b.request(
        f"{b.WP}/wp-json/wc/store/v1/products?include={b.PRICED},{b.RFQ}&per_page=2&lang=de",
        headers={"Accept": "application/json"},
    )
    products = b.json_body(store) or []
    links = (
        [
            {"id": item.get("id"), "permalink": item.get("permalink")}
            for item in products
            if isinstance(item, dict)
        ]
        if isinstance(products, list)
        else []
    )
    de_link = (
        all("/de/" in str(item["permalink"]) for item in links) and len(links) == 2
    )
    b.case(
        "retest-store-visitor-de-links",
        state="visitor",
        req={"url": store["url"]},
        result=store,
        verdict="pass" if de_link else "defect",
        note=json.dumps(links, ensure_ascii=False) + " | " + b.D1_NOTE,
        price=json.dumps(links, ensure_ascii=False),
    )

    question = "What is the net price of the SAJ H2-10K-T3?"
    turn(
        "retest-turn-approved-en-compare",
        secrets,
        {
            "type": "other",
            "url": f"{b.WP}/compare-products/?ids={b.PRICED},{b.RFQ}",
            "title": "Compare",
        },
        question,
        grade_current,
    )
    turn(
        "retest-turn-approved-en-config",
        secrets,
        {
            "type": "solution",
            "url": f"{b.WP}/solution-configurator/",
            "title": "Solution Configurator",
        },
        question,
        grade_current,
    )

    try:
        report = b.eval_file("price_turn.php")
    except RuntimeError as error:
        b.script_failed(
            "retest-turn-approved-after-price-change",
            "approved",
            "price_turn.php",
            error,
        )
    else:
        meta, blocks = b.parse_stream(str(report.get("stream") or ""))
        text = b.answer_text(blocks)
        prices = b.price_texts(blocks)
        verdict, note, stale = b.grade_changed_price_turn(
            int(report.get("status") or 0), text, prices
        )
        b.case(
            "retest-turn-approved-after-price-change",
            state="approved",
            req={"message": question, "price": b.CHANGED_PRICE},
            result={
                "status": report.get("status"),
                "duration_s": None,
                "url": "/linker-ai/v1/genie/turn",
            },
            verdict=verdict,
            note=note,
            price=" | ".join(prices),
            stale=stale,
            meta=meta,
            blocks=blocks,
        )

    try:
        b.run_mutation(secrets)

        # onbackorder is the snapshot state of the RFQ rows, not a temporary
        # mutation. The finally block still forces the known-good catalogue.
        b.wp_eval(
            f"""
add_filter("pre_wp_mail", static function () {{ return true; }});
foreach (array({b.RFQ}, {b.RFQ_DE}) as $id) {{
  $product = wc_get_product($id);
  if ($product instanceof WC_Product) {{
    $product->set_stock_status("onbackorder");
    $product->save();
  }}
}}
echo "back";
"""
        )
        pages = {
            b.RFQ: f"{b.WP}/product/goodwe-gw208-9-bat-lcd-g10/",
            b.RFQ_DE: f"{b.WP}/de/produkt/goodwe-gw208-9-bat-lcd-g10/",
        }
        for product_id, page in pages.items():
            looked = b.ability(
                "linker/get-product",
                {
                    "product_id": product_id,
                    "lang": "de" if product_id == b.RFQ_DE else "en",
                },
                {"Accept": "application/json"},
            )
            commerce = b.commerce_of(looked)
            fetched = b.request(page, headers={"Accept": "text/html"})
            text = b.visible_text(fetched["body"].decode(errors="replace"))
            badge_in = ("In stock" in text) or ("Auf Lager" in text)
            badge_out = ("Currently unavailable" in text) or (
                "Derzeit nicht verfügbar" in text
            )
            agrees = (
                commerce.get("in_stock") is True and badge_in and not badge_out
            ) or (commerce.get("in_stock") is False and badge_out and not badge_in)
            b.case(
                f"retest-stock-backorder-{product_id}",
                state="visitor",
                req={
                    "product_id": product_id,
                    "woo_status": "onbackorder",
                    "url": page,
                },
                result=looked,
                verdict="pass" if agrees else "defect",
                note=(
                    f"in_stock={commerce.get('in_stock')} "
                    f"page_in={badge_in} page_out={badge_out}"
                ),
                stock="in_stock" if commerce.get("in_stock") else "out_of_stock",
            )

        ids = [
            b.account_id(secrets["accounts"], state)
            for state in ("pending", "restricted", "approved")
        ]
        id_list = ", ".join(str(value) for value in ids)
        cleanup = json.loads(
            b.wp_eval(
                b.catalog_require()
                + "\n"
                + f"echo wp_json_encode(c333_delete_customer_orders(array({id_list})));\n"
            )
        )
        print(json.dumps(cleanup))
        if cleanup.get("remaining"):
            b.case(
                "followup-orders-cleanup",
                state="approved",
                req={"remaining": cleanup.get("remaining")},
                result={"status": 0, "duration_s": None, "url": "catalog.php"},
                verdict="defect",
                note=f"HPOS readback still has {cleanup.get('remaining')}",
            )
    finally:
        catalog = b.force_restore()
        print(json.dumps(catalog))
        if not b.catalog_ok(catalog):
            raise SystemExit("catalogue was not restored")


if __name__ == "__main__":
    main()
