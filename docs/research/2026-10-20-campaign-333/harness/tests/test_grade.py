"""The #333 graders, locked without an instance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from grade import (
    AMOUNT,
    CHANGED_PRICE,
    D1_NOTE,
    D2_NOTE,
    DEGRADED,
    GATE,
    MISSING_USER,
    PRICE,
    PRICED,
    PRICED_DE,
    PRODUCTS_FALLBACK,
    QTY,
    RFQ,
    RFQ_AMOUNT,
    RFQ_DE,
    SUPERSEDES,
    TURN_TIMEOUT,
    ability_matrix,
    catalog_ok,
    changed_amount,
    check_fixture,
    expect_line,
    grade_approved_price_turn,
    grade_changed_price_turn,
    grade_commerce,
    grade_forged_query,
    grade_price_confirmation,
    grade_stock_after_out,
    grade_stock_confirmation,
    grade_stock_words,
    notes_line,
    priced_amount,
    stock_poles,
    store_includes,
    summarize_rows,
)

FIXTURE = Path(__file__).parent / "fixtures" / "recorded-verdicts.json"
COUNTED = "counted 108: 101 pass, 7 defect"
DEFECTS = {
    "store-visitor-de",
    "store-pending-de",
    "store-restricted-de",
    "store-approved-de",
    "inquiry-own-pending",
    "inquiry-own-restricted",
    "turn-visitor-en-stock-after-out",
}


def recorded() -> list[dict[str, Any]]:
    data = json.loads(FIXTURE.read_text())
    assert isinstance(data, list)
    return data


def test_recorded_log_counts_final_verdicts() -> None:
    rows = recorded()
    unique = {str(row["id"]) for row in rows}
    assert len(rows) == 122
    assert len(unique) == 120
    summary = summarize_rows(rows)
    assert summary["notes"] == COUNTED
    assert summary["cases"] == 108
    assert summary["counts"] == {"pass": 101, "defect": 7}
    assert notes_line(108, {"pass": 101, "defect": 7}) == COUNTED
    found = {item.split(":", 1)[0] for item in summary["defects"]}
    assert found == DEFECTS
    assert "inquiry-flow" not in found
    assert "p50_s" not in summary


def test_supersedes_is_the_eleven_retests() -> None:
    assert len(SUPERSEDES) == 11
    assert SUPERSEDES["retest-store-visitor-de-links"] == "store-visitor-de"
    assert SUPERSEDES["retest-stock-backorder-6800"] == "stock-backorder-product-6800"


def test_stock_poles_do_not_read_in_stock_inside_a_negation() -> None:
    assert stock_poles("It is not in stock.") == (False, True)
    assert stock_poles("The item is out of stock.") == (False, True)
    assert stock_poles("nicht auf lager") == (False, True)
    assert stock_poles("It is in stock.") == (True, False)
    assert stock_poles("Auf Lager und lieferbar.") == (True, False)
    verdict, note = grade_stock_words("It is not in stock.", expect="in")
    assert verdict == "defect"
    assert "unclear" in note
    assert grade_stock_words("It is in stock.", expect="in")[0] == "pass"
    assert grade_stock_words("The product is not in stock.", expect="out")[0] == "pass"


def test_a_quantity_is_not_the_words_in_stock() -> None:
    assert QTY.search("It is in stock.") is None
    assert QTY.search("nicht auf lager") is None
    assert QTY.search("3 pcs left")
    assert grade_stock_words("3 pcs and it is in stock.", expect="in") == (
        "defect",
        "stock answer gave a quantity",
    )


def test_silent_degradation_on_the_stock_after_out_turn() -> None:
    meta = {
        "fallback": True,
        "grounded": False,
        "failures": ["a products turn is not a question for the team"],
        "intent": "company_logistics_service",
    }
    verdict, note, says_in = grade_stock_after_out(PRODUCTS_FALLBACK, meta)
    assert verdict == "defect"
    assert "degradation" in note
    assert says_in is False
    declared, declared_note, declared_in = grade_stock_after_out(
        DEGRADED["en"] + " It is not in stock.",
        {"fallback": True},
    )
    assert (declared, declared_in) == ("pass", False)
    assert declared_note == "says out of stock"
    bare, _bare_note, bare_in = grade_stock_after_out(
        "The product is not in stock.",
        None,
    )
    assert (bare, bare_in) == ("pass", False)
    silent, silent_note, _silent_in = grade_stock_after_out(
        "not in stock",
        {"fallback": True},
    )
    assert silent == "defect"
    assert "degradation" in silent_note


def test_forged_query_string_is_401() -> None:
    assert grade_forged_query(401, "{}") == ("pass", "status 401")
    assert grade_forged_query(404, "{}")[0] == "defect"
    leaked = grade_forged_query(401, "€1,680.00")
    assert leaked[0] == "defect"
    assert "leaked=True" in leaked[1]


def test_confirmation_requires_the_409_code_and_empty_stock_lines() -> None:
    price = {
        "orders_before": 1,
        "orders_after": 1,
        "price_digest_changed": True,
        "posted_price": {
            "status": 409,
            "data": {"code": "linker_genie_inquiry_changed"},
        },
        "after_price": {"data": {"lines": [{"price_html": "€1,701.00"}]}},
    }
    assert grade_price_confirmation(price) == (
        "pass",
        "new price on the card; stale digest refused; no order",
        False,
    )
    wrong_code = {
        **price,
        "posted_price": {"status": 409, "data": {"code": "other"}},
    }
    assert grade_price_confirmation(wrong_code)[0] == "defect"
    assert "linker_genie_inquiry_changed" not in grade_price_confirmation(wrong_code)[1]
    stale = {
        **price,
        "after_price": {"data": {"lines": [{"price_html": "€1,680.00"}]}},
    }
    assert grade_price_confirmation(stale)[2] is True

    stock = {
        "orders_before": 1,
        "orders_after": 1,
        "added_after_stock": False,
        "stock_digest_changed": True,
        "posted_stock": {
            "status": 409,
            "data": {"code": "linker_genie_inquiry_changed"},
        },
        "stock_card": {"data": {"lines": []}},
    }
    assert grade_stock_confirmation(stock) == (
        "pass",
        "out-of-stock lines empty; stale digest refused; no order",
    )
    added = {**stock, "added_after_stock": "cart-key"}
    assert grade_stock_confirmation(added)[0] == "defect"
    lined = {**stock, "stock_card": {"data": {"lines": [{"sku": "x"}]}}}
    assert "lines" in grade_stock_confirmation(lined)[1]


def test_amount_patterns_split_1680_from_1701_and_33250() -> None:
    assert priced_amount("€1,680.00")
    assert priced_amount("1.680,00 €")
    assert not priced_amount("€1,701.00")
    assert not priced_amount("33.250,00 €")
    assert changed_amount("€1,701.00")
    assert changed_amount("1.701,00 €")
    assert changed_amount(CHANGED_PRICE)
    assert not changed_amount(PRICE)
    assert AMOUNT.search("33.250,00 €")
    assert not AMOUNT.search("SAJ H2-10K-T3")


def test_commerce_lines_and_approved_page_parity() -> None:
    assert expect_line("visitor", "en", "priced") == GATE[("visitor", "en")]
    assert expect_line("approved", "en", "priced") == ""
    assert expect_line("approved", "de", "rfq") == "Angebot pro Projekt"
    assert expect_line("rejected", "en", "priced") == GATE[("restricted", "en")]
    closed = {
        "price_line": GATE[("pending", "en")],
        "price_visible": False,
    }
    assert grade_commerce("pending", "en", "priced", closed)[0] == "pass"
    opened = {**closed, "price_visible": True, "price": PRICE}
    assert grade_commerce("pending", "en", "priced", opened)[0] == "defect"
    approved = {
        "price_line": "€1,680.00",
        "price_visible": True,
        "price": PRICE,
    }
    page = "Net price 1,680.00 for partners"
    assert grade_commerce("approved", "en", "priced", approved, page)[0] == "pass"
    gated = "1,680.00 " + GATE[("visitor", "en")]
    assert grade_commerce("approved", "en", "priced", approved, gated)[0] == "defect"


def test_price_turns() -> None:
    assert grade_approved_price_turn(200, "See the card.", ["€1,680.00"])[0] == "pass"
    assert grade_approved_price_turn(200, "It costs €1,680.00.", ["€1,680.00"])[0] == (
        "defect"
    )
    verdict, _note, stale = grade_changed_price_turn(
        200, "The card has the current net price.", ["€1,701.00"]
    )
    assert (verdict, stale) == ("pass", False)
    verdict, _note, stale = grade_changed_price_turn(200, "still 1,680", ["€1,701.00"])
    assert verdict == "defect"
    assert stale is True


def test_catalog_and_fixture_agree_with_the_constants() -> None:
    assert (PRICED, PRICED_DE, RFQ, RFQ_DE) == (4107, 6628, 1957, 6800)
    assert (PRICE, RFQ_AMOUNT, MISSING_USER, TURN_TIMEOUT) == (
        "1680",
        "33250",
        999999,
        180,
    )
    good = {
        "key": False,
        "products": {
            "4107": {"regular": "1680", "stock": "instock"},
            "6628": {"regular": "1680.00", "stock": "instock"},
            "1957": {"regular": "33250", "stock": "onbackorder"},
            "6800": {"regular": "33250", "stock": "onbackorder"},
        },
    }
    assert catalog_ok(good)
    assert not catalog_ok({**good, "key": True})
    accounts = {
        "products": {
            "priced": {"en": PRICED, "de": PRICED_DE, "price": PRICE},
            "rfq": {"en": RFQ, "de": RFQ_DE, "price": RFQ_AMOUNT},
        }
    }
    check_fixture(accounts)
    accounts["products"]["priced"]["de"] = 1
    with pytest.raises(RuntimeError, match="priced.de"):
        check_fixture(accounts)


def test_twin_probes_are_in_the_matrix() -> None:
    matrix = ability_matrix()
    assert ("de", PRICED_DE, "priced", "-twin") in matrix
    assert ("de", RFQ_DE, "rfq", "-twin") in matrix
    assert ("de", PRICED, "priced", "") in matrix
    includes = store_includes()
    assert ("de", f"{PRICED_DE},{RFQ_DE}", "-twin") in includes
    assert ("de", f"{PRICED},{RFQ}", "") in includes


def test_evidence_notes_name_the_limit() -> None:
    assert "#413" in D1_NOTE
    assert "card" in D1_NOTE
    assert "#414" in D2_NOTE
    assert "Itemless" in D2_NOTE
