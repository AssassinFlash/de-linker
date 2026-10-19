"""Pure graders for the #333 account, price and stock battery.

Runners shell out and talk HTTP. A verdict is decided here, so the tests lock
it without an instance.

Sources, so the next reader does not treat the numbers as arbitrary:

- ``PRICED`` / ``PRICED_DE`` / ``PRICE``: snapshot ``20261019-1715``, SKU
  ``DLK-SAJ-H210KT3``. EN post 4107, Polylang twin 6628, regular price 1680.
  Spec 13 names the rendered forms ``€1,680.00`` and ``1.680,00 €``.
- ``RFQ`` / ``RFQ_DE`` / ``RFQ_AMOUNT``: the same snapshot, SKU
  ``DLK-GOODWE-GW2089BATLCDG10``, mode ``rfq_only``. EN 1957, twin 6800.
  The stored price 33250 must not be shown. Spec 13 records that the twin
  once lacked its own ``rfq_only`` flag and leaked ``33.250,00 €``.
- ``TURN_TIMEOUT``: the shell waits 60 s (``UserContext::TTL`` is twice that;
  ``prices.LOOKUP_DEADLINE`` is 50 s inside the same budget). 180 s is this
  harness's ceiling for a slow local model, not a product timeout.
- ``MISSING_USER``: no row in the snapshot has user id 999999. ``UserContext``
  will still sign a token for it. The missing row must not open prices.
- ``AMOUNT`` / ``QTY``: the amount pattern is those two catalogue figures in
  EN grouping (``1,680.00``), DE grouping (``1.680,00``) and the bare
  integer. It does not match a model code. A quantity is a count plus a unit,
  or an explicit qty label (spec 69: status, not a count). "in stock" is not
  a quantity. "in stock" is also a substring of "not in stock"; stock poles
  remove the negated phrase before they look for the positive one.
"""

from __future__ import annotations

import re
from typing import Any

PRICED = 4107
PRICED_DE = 6628
PRICE = "1680"
RFQ = 1957
RFQ_DE = 6800
RFQ_AMOUNT = "33250"
TURN_TIMEOUT = 180
MISSING_USER = 999999

# One euro-shaped figure that is not the catalogue price. The re-ask and the
# confirmation both use it, so a stale card cannot pass by still showing 1680.
CHANGED_PRICE = "1701"

# Spec 13, template.DEGRADED. A turn whose meta says fallback must say this.
# The products fallback ("Here are matching products…") is not this sentence.
DEGRADED = {
    "en": (
        "I could not answer this time. Please try again in a moment, "
        "or write to our team."
    ),
    "de": (
        "Ich konnte Ihre Frage diesmal nicht beantworten. Bitte versuchen "
        "Sie es gleich noch einmal, oder wenden Sie sich an unser Team."
    ),
}
PRODUCTS_FALLBACK = "Here are matching products from our range."
INQUIRY_CHANGED = "linker_genie_inquiry_changed"

# Store API rows grade the permalink string the API returned. They do not
# open a German Genie card. #413 stays the product ticket for the card link.
D1_NOTE = (
    "Store API permalink only; the German card link was not opened. "
    "#413 remains the product ticket."
)
# The fixture order has no line items. set_total writes the figure the
# ability echoes. That is the ability bypass. A customer-visible inquiry
# list may still hide the total. #414 is this ability.
D2_NOTE = (
    "Itemless order with a hand-set total; this is the ability bypass. "
    "A customer-visible inquiry list may be gated elsewhere. #414 is this ability."
)

GATE = {
    ("visitor", "en"): "Net price after partner sign-in",
    ("visitor", "de"): "Nettopreis nach Partner-Anmeldung",
    ("pending", "en"): "Account under review. Prices after approval.",
    ("pending", "de"): "Ihr Konto wird geprüft. Preise nach Freigabe.",
    ("restricted", "en"): "Not available for your account",
    ("restricted", "de"): "Für Ihr Konto nicht verfügbar",
    # CommerceState::visitor_reason has no rejected branch. A signed-in
    # account that is not pending reads the restricted sentence. The
    # customer-visible check is the login refusal, graded separately.
    ("rejected", "en"): "Not available for your account",
    ("rejected", "de"): "Für Ihr Konto nicht verfügbar",
}
RFQ_LINE = {"en": "Quoted per project", "de": "Angebot pro Projekt"}
CARD_LOGIN = {"en": "Log in for prices", "de": "Preise nach Anmeldung"}

EURO = re.compile(r"€|(?:\bEUR\b)", re.I)
AMOUNT = re.compile(
    r"1[.,]680(?:[.,]00)?|\b1680(?:[.,]00)?\b|"
    r"33[.,]250(?:[.,]00)?|\b33250(?:[.,]00)?\b"
)
PRICED_AMOUNT = re.compile(r"1[.,]680")
CHANGED_AMOUNT = re.compile(r"1[.,]701|\b1701\b")
QTY = re.compile(
    r"\b\d+\s*(?:pcs|pieces|units|stück|stueck|stk)\b|"
    r"\b(?:qty|quantity|menge)\s*[:=]?\s*\d+",
    re.I,
)
# Longer negated phrases first. They are removed before the positive
# pattern runs, so "in stock" does not match inside "not in stock".
_OUT = re.compile(
    r"not in stock|out of stock|currently unavailable|"
    r"nicht auf lager|nicht verfügbar|derzeit nicht verfügbar|"
    r"nicht lieferbar|\bunavailable\b",
    re.I,
)
_IN = re.compile(r"\bin stock\b|auf lager|\blieferbar\b", re.I)

# followup.py writes these ids. Each one is the final verdict of the
# original case. Count the pair once (NOTES, the 11 revised rows).
SUPERSEDES = {
    "retest-token-query-only": "token-query-only-get-product",
    "retest-page-visitor-compare-en": "page-visitor-compare-en",
    "retest-page-visitor-compare-de": "page-visitor-compare-de",
    "retest-page-approved-priced-en": "page-approved-priced-en",
    "retest-page-approved-priced-de": "page-approved-priced-de",
    "retest-store-visitor-de-links": "store-visitor-de",
    "retest-turn-approved-en-compare": "turn-approved-en-compare",
    "retest-turn-approved-en-config": "turn-approved-en-config",
    "retest-turn-approved-after-price-change": "turn-approved-after-price-change",
    "retest-stock-backorder-1957": "stock-backorder-product-1957",
    "retest-stock-backorder-6800": "stock-backorder-product-6800",
}

# GeniePricesTest::test_the_token_is_bound_to_its_abilities. The route
# accepts GET. A query string that only names an ability stays a guest,
# so users/me answers 401. GET of the POST-only turn route is 404 and is
# not this contract.
FORGED_QUERY_PATH = (
    "/wp-json/wp/v2/users/me?x=/wp-abilities/v1/abilities/linker/get-product/run"
)


def euro(text: str) -> bool:
    return bool(EURO.search(text) or AMOUNT.search(text))


def priced_amount(text: str) -> bool:
    """The catalogue 1680 in either grouping. Not 1701 and not 33250."""
    return bool(PRICED_AMOUNT.search(text))


def changed_amount(text: str) -> bool:
    return bool(CHANGED_AMOUNT.search(text))


def stock_poles(text: str) -> tuple[bool, bool]:
    """``(says_in, says_out)``. Negated phrases do not count as in stock."""
    lowered = text.lower()
    says_out = bool(_OUT.search(lowered))
    scrubbed = _OUT.sub(" ", lowered)
    says_in = bool(_IN.search(scrubbed))
    return says_in, says_out


def expect_line(state: str, lang: str, kind: str) -> str:
    if state == "approved" and kind == "priced":
        return ""
    if state == "approved":
        return RFQ_LINE[lang]
    return GATE[(state, lang)]


def grade_commerce(
    state: str,
    lang: str,
    kind: str,
    commerce: dict[str, Any],
    page_text: str | None = None,
) -> tuple[str, str]:
    line = str(commerce.get("price_line") or "")
    visible = commerce.get("price_visible")
    if state != "approved" or kind == "rfq":
        if visible or "price" in commerce or euro(line):
            return "defect", "price visible to a closed account or an RFQ product"
        expected = expect_line(state, lang, kind)
        if line != expected:
            return "defect", f"price line {line!r} != {expected!r}"
        if page_text is not None and expected not in page_text:
            return "defect", "product page does not carry the same sentence"
        if kind == "rfq" and page_text is not None and AMOUNT.search(page_text):
            return "defect", "RFQ page still shows the stored amount"
        return "pass", line
    if not visible or commerce.get("price") != PRICE or not euro(line):
        return "defect", f"approved price missing: {commerce}"
    if page_text is not None:
        # The ability line glues the currency symbol. The page shows the same
        # amount with a space or NBSP, so the raw line is not a substring.
        compact = page_text.replace("\xa0", " ").replace("\u00a0", " ")
        amount_on_page = priced_amount(compact)
        gate_on_page = GATE[("visitor", lang)] in compact
        if not amount_on_page or gate_on_page:
            return (
                "defect",
                "approved page missed the amount or still showed the visitor gate",
            )
    return "pass", line


def grade_stock_words(text: str, *, expect: str) -> tuple[str, str]:
    says_in, says_out = stock_poles(text)
    if QTY.search(text):
        return "defect", "stock answer gave a quantity"
    if expect == "in" and says_in and not says_out:
        return "pass", "says in stock"
    if expect == "out" and says_out and not says_in:
        return "pass", "says out of stock"
    return "defect", f"stock wording unclear: {text[:240]}"


def degradation_declared(text: str) -> bool:
    return any(sentence in text for sentence in DEGRADED.values())


def grade_stock_after_out(
    text: str, meta: dict[str, Any] | None
) -> tuple[str, str, bool]:
    """D3. A fallback must declare the degradation (spec 13, 无静默降级).

    Returns verdict, note, and whether the answer still claimed the product
    was in stock.
    """
    says_in, _says_out = stock_poles(text)
    fallback = bool(isinstance(meta, dict) and meta.get("fallback"))
    if fallback and not degradation_declared(text):
        failures = meta.get("failures") if isinstance(meta, dict) else None
        return (
            "defect",
            f"fallback without a degradation declaration; failures={failures!r}",
            says_in,
        )
    verdict, note = grade_stock_words(text, expect="out")
    return verdict, note, says_in


def grade_forged_query(status: int, body: str) -> tuple[str, str]:
    leaked = euro(body)
    if status == 401 and not leaked:
        return "pass", f"status {status}"
    return "defect", f"status {status}; leaked={leaked}"


def grade_approved_price_turn(
    status: int, text: str, prices: list[str]
) -> tuple[str, str, bool]:
    if status != 200:
        return "defect", f"no answer status {status}", False
    if euro(text):
        return "defect", "price amount in the prose", False
    if any(priced_amount(price) for price in prices):
        return "pass", " | ".join(prices), False
    return "defect", f"card {prices!r}", False


def grade_changed_price_turn(
    status: int, text: str, prices: list[str]
) -> tuple[str, str, bool]:
    stale = any(priced_amount(price) for price in prices) or priced_amount(text)
    current = any(changed_amount(price) for price in prices)
    if status != 200:
        return "defect", f"no answer status {status}", False
    if euro(text) or stale or not current:
        return "defect", " | ".join(prices) or text[:240], stale
    return "pass", " | ".join(prices), False


def posted_code(posted: dict[str, Any] | None) -> str:
    if not isinstance(posted, dict):
        return ""
    data = posted.get("data")
    if isinstance(data, dict) and isinstance(data.get("code"), str):
        return str(data["code"])
    return ""


def _lines_blob(report: dict[str, Any], key: str) -> str:
    section = report.get(key)
    data = section.get("data") if isinstance(section, dict) else None
    lines = data.get("lines") if isinstance(data, dict) else None
    return "" if lines is None else str(lines)


def grade_price_confirmation(report: dict[str, Any]) -> tuple[str, str, bool]:
    after_lines = _lines_blob(report, "after_price")
    price_changed = bool(report.get("price_digest_changed"))
    posted = report.get("posted_price")
    posted_map = posted if isinstance(posted, dict) else {}
    shows_new = changed_amount(after_lines)
    shows_old = priced_amount(after_lines)
    stale_price = (not shows_new) or shows_old
    sent = report.get("orders_after") != report.get("orders_before")
    code = posted_code(posted_map)
    if sent:
        return "defect", "stale confirmation created an order", shows_old
    if not price_changed:
        return "defect", "price change left the confirmation digest unchanged", False
    if posted_map.get("status") != 409 or code != INQUIRY_CHANGED:
        return (
            "defect",
            f"stale POST status {posted_map.get('status')} code {code}",
            False,
        )
    if stale_price:
        return "defect", "confirmation card kept the old price", True
    return "pass", "new price on the card; stale digest refused; no order", False


def grade_stock_confirmation(report: dict[str, Any]) -> tuple[str, str]:
    posted = report.get("posted_stock")
    posted_map = posted if isinstance(posted, dict) else {}
    stock_card = report.get("stock_card")
    data = stock_card.get("data") if isinstance(stock_card, dict) else None
    lines = data.get("lines") if isinstance(data, dict) else None
    added = report.get("added_after_stock")
    sent = report.get("orders_after") != report.get("orders_before")
    code = posted_code(posted_map)
    if sent:
        return "defect", "an order exists after the stock probe"
    if added:
        return "defect", "out-of-stock add_to_cart succeeded"
    if isinstance(lines, list) and len(lines) > 0:
        return "defect", "out-of-stock card still has lines"
    if not report.get("stock_digest_changed"):
        return "defect", "stock change left the confirmation digest unchanged"
    if posted_map.get("status") != 409 or code != INQUIRY_CHANGED:
        return "defect", f"stale stock POST {posted_map.get('status')} code {code}"
    return "pass", "out-of-stock lines empty; stale digest refused; no order"


def canonical_id(case_id: str) -> str:
    return SUPERSEDES.get(case_id, case_id)


def _harness_failure(row: dict[str, Any]) -> bool:
    """The eval-file compile failure. The confirmation rows are the rerun."""
    return (
        row.get("id") == "inquiry-flow"
        and row.get("verdict") == "defect"
        and "flow script failed" in str(row.get("note") or "")
    )


def final_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Latest row per case. A retest id replaces the original it names."""
    latest: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in rows:
        cid = canonical_id(str(row["id"]))
        if cid not in latest:
            order.append(cid)
        latest[cid] = row
    return [latest[cid] for cid in order if not _harness_failure(latest[cid])]


def notes_line(total: int, counts: dict[str, int]) -> str:
    return (
        f"counted {total}: {counts.get('pass', 0)} pass, "
        f"{counts.get('defect', 0)} defect"
    )


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    finals = final_rows(rows)
    counts: dict[str, int] = {}
    for row in finals:
        verdict = str(row["verdict"])
        counts[verdict] = counts.get(verdict, 0) + 1
    durations = sorted(
        float(row["duration_s"])
        for row in finals
        if isinstance(row.get("duration_s"), int | float)
    )
    summary: dict[str, Any] = {
        "cases": len(finals),
        "counts": counts,
        "defects": [
            canonical_id(str(row["id"])) + ": " + str(row.get("note") or "")
            for row in finals
            if row.get("verdict") == "defect"
        ],
        "notes": notes_line(len(finals), counts),
    }
    if durations:
        summary["p50_s"] = durations[len(durations) // 2]
        summary["max_s"] = durations[-1]
    return summary


def ability_matrix() -> list[tuple[str, int, str, str]]:
    """``(lang, product_id, kind, id_suffix)`` for get-product.

    The ``-twin`` rows query the DE post by id. Asking the EN id with
    ``lang=de`` is a different probe and stays in the matrix too.
    """
    return [
        ("en", PRICED, "priced", ""),
        ("de", PRICED, "priced", ""),
        ("de", PRICED_DE, "priced", "-twin"),
        ("en", RFQ, "rfq", ""),
        ("de", RFQ, "rfq", ""),
        ("de", RFQ_DE, "rfq", "-twin"),
    ]


def store_includes() -> list[tuple[str, str, str]]:
    """``(lang, include, id_suffix)`` for the Store API."""
    return [
        ("en", f"{PRICED},{RFQ}", ""),
        ("de", f"{PRICED},{RFQ}", ""),
        ("de", f"{PRICED_DE},{RFQ_DE}", "-twin"),
    ]


def price_is(value: object, expected: str) -> bool:
    text = str(value).strip()
    return text == expected or text == f"{expected}.00"


def catalog_ok(report: dict[str, Any]) -> bool:
    """The four catalogue rows and a closed push channel, after restore."""
    if report.get("key"):
        return False
    products = report.get("products")
    if not isinstance(products, dict):
        return False
    for pid in (PRICED, PRICED_DE):
        row = products.get(str(pid))
        if not isinstance(row, dict):
            return False
        if not price_is(row.get("regular"), PRICE) or row.get("stock") != "instock":
            return False
    for pid in (RFQ, RFQ_DE):
        row = products.get(str(pid))
        if not isinstance(row, dict) or row.get("stock") != "onbackorder":
            return False
    return True


def check_fixture(accounts: dict[str, Any]) -> None:
    """The constants above and accounts.json name the same snapshot rows."""
    products = accounts.get("products")
    if not isinstance(products, dict):
        raise RuntimeError("accounts.json has no products")
    priced = products.get("priced")
    rfq = products.get("rfq")
    if not isinstance(priced, dict) or not isinstance(rfq, dict):
        raise RuntimeError("accounts.json products are incomplete")
    expected = {
        "priced.en": (int(priced["en"]), PRICED),
        "priced.de": (int(priced["de"]), PRICED_DE),
        "priced.price": (str(priced["price"]), PRICE),
        "rfq.en": (int(rfq["en"]), RFQ),
        "rfq.de": (int(rfq["de"]), RFQ_DE),
        "rfq.price": (str(rfq["price"]), RFQ_AMOUNT),
    }
    drifted = [name for name, (got, want) in expected.items() if got != want]
    if drifted:
        raise RuntimeError(
            "fixture drifted from the harness constants: " + ", ".join(drifted)
        )
