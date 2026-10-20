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
    REJECTED_AUTH,
    RFQ,
    RFQ_AMOUNT,
    RFQ_DE,
    SUPERSEDES,
    TURN_TIMEOUT,
    ability_matrix,
    answer_text,
    catalog_ok,
    changed_amount,
    check_fixture,
    expect_line,
    grade_approved_price_turn,
    grade_changed_price_turn,
    grade_commerce,
    grade_forged_query,
    grade_guest_replay,
    grade_other_replay,
    grade_own_inquiry,
    grade_owner_history,
    grade_price_confirmation,
    grade_push,
    grade_stock_after_out,
    grade_stock_confirmation,
    grade_stock_words,
    grade_transition,
    notes_line,
    priced_amount,
    rfq_amount,
    stock_badge_agrees,
    stock_poles,
    store_includes,
    summarize_rows,
    upper_median,
)
from run_battery import parse_stream

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


def test_degraded_turn_is_a_handoff_block() -> None:
    """template._degraded is a HandoffBlock. cycle.run sets fallback=True.

    The sentence is the block's summary. A reader that only joins text
    blocks grades this turn as an undeclared fallback.
    """
    summary = DEGRADED["en"]
    stream = (
        "event: meta\n"
        'data: {"fallback": true, "grounded": false, '
        '"failures": ["exceeded max retries count of 2"]}\n\n'
        "event: block\n"
        "data: "
        + json.dumps({"type": "handoff", "summary": summary}, ensure_ascii=False)
        + "\n\n"
    )
    meta, blocks = parse_stream(stream)
    assert blocks == [{"type": "handoff", "summary": summary}]
    text = answer_text(blocks)
    assert text == summary
    verdict, note, says_in = grade_stock_after_out(text, meta)
    assert (verdict, note, says_in) == ("pass", "degradation declared", False)
    german = answer_text([{"type": "handoff", "summary": DEGRADED["de"]}])
    assert grade_stock_after_out(german, {"fallback": True})[0] == "pass"


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
    unread = {key: value for key, value in stock.items() if key != "stock_card"}
    missing_lines = {**stock, "stock_card": {"data": {}}}
    not_a_list = {**stock, "stock_card": {"data": {"lines": "gone"}}}
    for malformed in (unread, missing_lines, not_a_list):
        verdict, note = grade_stock_confirmation(malformed)
        assert verdict == "defect"
        assert "lines" in note


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
    assert rfq_amount("33.250,00 €")
    assert rfq_amount("33250")
    assert not rfq_amount("€1,680.00")


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
    decimal = {**approved, "price": "1680.00"}
    assert grade_commerce("approved", "en", "priced", decimal, page)[0] == "pass"
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
    verdict, _note, stale = grade_changed_price_turn(
        200, "The net price is 1701.", ["€1,701.00"]
    )
    assert (verdict, stale) == ("defect", False)
    verdict, _note, stale = grade_changed_price_turn(
        200, "The net price is 2500.", ["€1,701.00"]
    )
    assert (verdict, stale) == ("defect", False)
    assert (
        grade_changed_price_turn(
            200,
            "The SAJ H2-10K-T3 price is on the card.",
            ["€1,701.00"],
        )[0]
        == "pass"
    )


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


def test_p50_s_is_the_upper_median() -> None:
    assert upper_median([1.0, 2.0, 4.0, 10.0]) == 4.0
    assert upper_median([1.0, 2.0, 3.0, 4.0, 10.0]) == 3.0
    rows = [
        {"id": "a", "verdict": "pass", "duration_s": 1},
        {"id": "b", "verdict": "pass", "duration_s": 10},
        {"id": "c", "verdict": "pass", "duration_s": 4},
        {"id": "d", "verdict": "pass", "duration_s": 2},
    ]
    summary = summarize_rows(rows)
    assert summary["p50_s"] == 4
    assert summary["max_s"] == 10


def _open_commerce() -> dict[str, Any]:
    return {"price_line": "€1,680.00", "price_visible": True, "price": PRICE}


def _closed_commerce(state: str) -> dict[str, Any]:
    return {"price_line": GATE[(state, "en")], "price_visible": False, "price": ""}


def _transition_report() -> dict[str, Any]:
    return {
        "roles": ["customer"],
        "pending_cookie_valid": True,
        "pending_commerce": _closed_commerce("pending"),
        "approved_cookie_valid": True,
        "approved_commerce": _open_commerce(),
        "rejected_cookie_valid": False,
        "rejected_auth_code": REJECTED_AUTH,
        "rejected_commerce": _closed_commerce("rejected"),
        "reapproved_auth_ok": True,
        "reapproved_commerce": _open_commerce(),
        "user_gone": True,
    }


def test_transition_seven_cases() -> None:
    graded = grade_transition(_transition_report())
    assert [item[0] for item in graded] == [
        "transition-subject",
        "transition-pending-closed",
        "transition-approved-without-relogin",
        "transition-rejected-login",
        "transition-rejected-no-prices",
        "transition-relogin-after-approval",
        "transition-user-deleted",
    ]
    assert {item[0]: item[2] for item in graded} == {
        case_id: "pass" for case_id in (item[0] for item in graded)
    }
    decimal = _transition_report()
    opened = _open_commerce()
    opened["price"] = "1680.00"
    decimal["approved_commerce"] = opened
    approved = next(
        item
        for item in grade_transition(decimal)
        if item[0] == "transition-approved-without-relogin"
    )
    assert approved[2] == "pass"
    flips = {
        "roles": ["subscriber"],
        "pending_cookie_valid": False,
        "approved_cookie_valid": False,
        "rejected_cookie_valid": True,
        "rejected_commerce": _open_commerce(),
        "reapproved_auth_ok": False,
        "user_gone": False,
    }
    for key, value in flips.items():
        report = _transition_report()
        report[key] = value
        failed = [item[0] for item in grade_transition(report) if item[2] == "defect"]
        assert len(failed) == 1, key


def test_own_inquiry_isolation() -> None:
    made = {"pending": 10, "restricted": 11, "approved": 12}
    verdict, note, price = grade_own_inquiry(
        "approved", made, [{"id": 12, "total": "1680"}]
    )
    assert verdict == "pass"
    assert price == ""
    assert D2_NOTE in note
    closed, closed_note, closed_price = grade_own_inquiry(
        "pending", made, [{"id": 10, "total": "1680"}]
    )
    assert closed == "defect"
    assert "totals" in closed_note
    assert closed_price == "['1680']"
    foreign, foreign_note, _foreign_price = grade_own_inquiry(
        "pending", made, [{"id": 12, "total": ""}]
    )
    assert foreign == "defect"
    assert "expected only 10" in foreign_note
    quiet, _quiet_note, quiet_price = grade_own_inquiry(
        "restricted", made, [{"id": 11, "total": ""}]
    )
    assert quiet == "pass"
    assert quiet_price == ""


def test_logout_replay_verdicts() -> None:
    assert grade_guest_replay(200, "the thread")[:2] == (
        "pass",
        "status 200; euro=False",
    )
    guest = grade_guest_replay(200, "€1,680.00")
    assert guest[0] == "defect"
    assert guest[2] is True
    assert grade_other_replay(200, "€ 10 shipping")[0] == "pass"
    other = grade_other_replay(200, "Net €1,680.00")
    assert other[0] == "defect"
    assert other[2] is True
    owner, owner_note, showed = grade_owner_history(200, "€1,680.00")
    assert (owner, showed) == ("pass", True)
    assert owner_note == "historical thread kept for the owner"
    missing, missing_note, _showed = grade_owner_history(200, "no figure here")
    assert missing == "pass"
    assert missing_note == "owner thread had no stored price line"
    assert grade_owner_history(404, "€1,680.00")[0] == "defect"


def test_push_body_must_contain_the_expected_token() -> None:
    verdict, text = grade_push({"code": "invalid_qty", "sku": "DLK"}, "invalid_qty")
    assert verdict == "pass"
    assert "invalid_qty" in text
    assert grade_push({"code": "outofstock"}, "invalid_qty")[0] == "defect"
    assert grade_push({"state": "instock"}, "instock")[0] == "pass"


def test_stock_badge_agrees_with_in_stock() -> None:
    assert stock_badge_agrees(False, "Currently unavailable")[0] is True
    assert stock_badge_agrees(True, "In stock")[0] is True
    assert stock_badge_agrees(True, "Currently unavailable")[0] is False
    assert stock_badge_agrees(False, "Auf Lager")[0] is False
    assert stock_badge_agrees(True, "Auf Lager")[0] is True
    assert stock_badge_agrees(False, "Derzeit nicht verfügbar")[0] is True
    agrees, badge_in, badge_out = stock_badge_agrees(
        False, "In stock Currently unavailable"
    )
    assert (agrees, badge_in, badge_out) == (False, True, True)
