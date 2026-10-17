"""The after-the-fact quality check (#258): log, item, citations, cascade, worker.

The turns are logged through the service's own endpoint (the real log shape);
the judges are replaced at the one call they make (`linker_judges.cascade.call`)
and the site by an httpx MockTransport, so no test reaches a model or a site.
"""

from __future__ import annotations

import copy
import json
import logging
import re
import sqlite3
import time
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from linker_judges import cascade as cascade_module
from linker_judges.judges import Answer, Judge, Verdict
from linker_judges.registry import JUDGES
from linker_judges.rubric import APPROPRIATE, BETTER_PICK, REMIT, Question

import linker_genie.app as app_module
from linker_genie.app import app
from linker_genie.facts import Fact, TurnFacts
from linker_genie.log import ADDED_COLUMNS, TurnLog
from linker_genie.quality import citations
from linker_genie.quality.item import Skip, build, rendered
from linker_genie.quality.store import Store
from linker_genie.quality.turns import (
    COLUMNS,
    LATER_COLUMNS,
    LoggedTurn,
    TurnSource,
    select_list,
)
from linker_genie.quality.wordpress import ROUTE, PushError, WordPress
from linker_genie.quality.worker import (
    MAX_ATTEMPTS,
    PRUNE_EVERY_SECONDS,
    RETENTION_DAYS,
    RETRY_AFTER_SECONDS,
    Worker,
    flags_for,
    judge_turn,
)
from linker_genie.schema import CardsBlock, TextBlock, TurnOutput, TurnRequest

SEARCH = {
    "qualified": [
        {"product_id": 4107, "facts": {"ac_power_kw": 10, "phase": "three"}},
        {"product_id": 6507, "facts": {"ac_power_kw": 12, "phase": "three"}},
    ]
}


def _generate(request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
    """A turn that read search-products and recommends one of its two hits."""
    facts = TurnFacts()
    facts.product_ids = {4107, 6507}
    facts.qualified_ids = {4107, 6507}
    facts.add(Fact(id="p4107.ac_power_kw", value="10", source="selection-facts"))
    facts.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {"q": "10 kW"},
            "ok": True,
            "result": SEARCH,
        }
    )
    return (
        TurnOutput(
            language=request.locale,
            blocks=[
                TextBlock(
                    text="This inverter is {fact:p4107.ac_power_kw} kW.", refs=["4107"]
                ),
                CardsBlock(product_ids=[4107]),
            ],
        ),
        facts,
    )


@pytest.fixture()
def turns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    path = tmp_path / "turns.sqlite"
    log = TurnLog(path)
    monkeypatch.setattr(app_module, "_log", log)
    app.state.generate = _generate
    yield path
    app.state.generate = None
    log.close()


def _ask(
    question: str,
    page: dict[str, Any] | None = None,
    user: dict[str, Any] | None = None,
) -> None:
    body: dict[str, Any] = {
        "conversation_id": "812",
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": question},
        ],
        "locale": "en",
    }
    if page is not None:
        body["page_context"] = page
    if user is not None:
        body["user"] = user
    assert TestClient(app).post("/assistant/turn", json=body).status_code == 200


# --- the log -----------------------------------------------------------------


def test_the_log_keeps_the_question_page_and_tool_results(turns: Path) -> None:
    _ask("10 kW three-phase?", {"type": "product", "product_id": 6507})
    [turn] = TurnSource(turns).after(0, 10)
    assert turn.question == "10 kW three-phase?"
    assert turn.page["product_id"] == 6507
    assert turn.tool_calls[0]["result"] == SEARCH
    assert turn.conversation_id == "812"


def test_an_old_log_gains_the_columns_and_keeps_its_rows(tmp_path: Path) -> None:
    path = tmp_path / "turns.sqlite"
    old = sqlite3.connect(path)
    old.execute(
        "CREATE TABLE turns (id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now')), locale TEXT NOT NULL, "
        "grounded INTEGER NOT NULL, failures TEXT NOT NULL, fallback INTEGER NOT NULL, "
        "provider TEXT NOT NULL, model TEXT NOT NULL, tool_calls TEXT NOT NULL, "
        "output TEXT NOT NULL, vote INTEGER)"
    )
    old.execute(
        "INSERT INTO turns (conversation_id, locale, grounded, failures, fallback, "
        "provider, model, tool_calls, output) VALUES "
        "('7', 'de', 1, '[]', 0, 'deepseek', 'deepseek-flash', '[]', '{}')"
    )
    old.commit()
    # The worker reads a log the service has not upgraded yet.
    [before] = TurnSource(path).after(0, 10)
    assert before.question is None
    old.close()

    TurnLog(path).close()
    [after] = TurnSource(path).after(0, 10)
    assert after.question is None and after.conversation_id == "7"
    # A turn logged before the log kept the account reads as not approved.
    assert before.approved is False and after.approved is False


def test_the_log_keeps_whether_the_account_is_approved(turns: Path) -> None:
    _ask("What does it cost?", user={"logged_in": True, "partner": True})
    _ask("What does it cost?", user={"logged_in": True})
    _ask("What does it cost?")
    approved, pending, guest = TurnSource(turns).after(0, 10)
    assert approved.approved is True
    # No `partner` sent (the shell sends none before #242): not approved.
    assert pending.approved is False and guest.approved is False


def test_the_columns_added_later_come_from_the_log_itself() -> None:
    assert LATER_COLUMNS == {name for name, _ in ADDED_COLUMNS}
    full = select_list(set(COLUMNS))
    assert full == ", ".join(COLUMNS)
    # A log from before the question and the account flag: those read as NULL.
    oldest = select_list(set(COLUMNS) - {"question", "page", "approved"})
    assert "NULL AS question" in oldest and "NULL AS page" in oldest
    assert oldest.endswith("NULL AS approved")
    assert oldest.startswith("id, conversation_id")


def test_a_missing_log_reads_as_empty(tmp_path: Path) -> None:
    source = TurnSource(tmp_path / "absent.sqlite")
    assert source.latest_id() == 0
    assert source.after(0, 10) == []


# --- the item ----------------------------------------------------------------


def _turn(**changes: Any) -> LoggedTurn:
    base = LoggedTurn(
        id=5,
        conversation_id="812",
        created_at="2026-10-17 09:00:00",
        locale="en",
        fallback=False,
        tool_calls=[
            {"name": "linker/search-products", "arguments": {}, "result": SEARCH}
        ],
        output={
            "language": "en",
            "blocks": [
                {"type": "text", "text": "This inverter is 10 kW.", "refs": ["4107"]},
                {"type": "cards", "product_ids": [4107]},
            ],
        },
        question="10 kW three-phase?",
        page={"type": "other"},
    )
    return replace(base, **changes)


def test_the_item_carries_the_logged_results_and_a_wrong_pick() -> None:
    item = build(_turn())
    assert item.state["reference"]["calls"][0]["result"] == SEARCH
    assert item.cards == [4107]
    # 6507 was returned and not offered: the variant recommends it instead.
    assert item.swap == (4107, 6507)
    assert "Recommended products: 6507." in item.state["answer_b"]
    assert "Recommended products: 4107." in item.state["answer_a"]


def test_a_product_page_turn_names_its_own_product_apart() -> None:
    item = build(_turn(page={"type": "product", "product_id": 4107}))
    assert "This page's product: 4107." in item.state["answer"]
    # The only card is the page itself: there is no recommendation to swap.
    assert item.swap is None


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"output": {}}, "no answer was shipped"),
        ({"question": None}, "without its question"),
        (
            {"tool_calls": [{"name": "linker/get-product", "arguments": {}}]},
            "tool results",
        ),
    ],
)
def test_turns_without_something_to_judge_are_skipped(
    changes: dict[str, Any], reason: str
) -> None:
    with pytest.raises(Skip, match=reason):
        build(_turn(**changes))


def test_the_rendered_answer_is_what_the_customer_read() -> None:
    text = rendered(
        {
            "blocks": [
                {"type": "text", "text": "Two options.", "refs": []},
                {"type": "ask", "field": "phase", "options": ["single", "three"]},
                {"type": "action", "name": "open_configurator", "args": {}},
                {"type": "handoff", "summary": "Please write to sales@de-linker.com."},
            ]
        }
    )
    assert text.splitlines()[0] == "Two options."
    assert "[Asks for phase: single, three]" in text
    assert "[Offers the action open_configurator]" in text
    assert text.endswith("Please write to sales@de-linker.com.")


# --- citations ---------------------------------------------------------------


def test_a_filled_answer_from_its_tools_passes_the_citation_check() -> None:
    assert citations.verify(_turn()) == []


def test_a_number_no_tool_returned_is_a_citation_failure() -> None:
    turn = _turn(
        output={
            "blocks": [
                {"type": "text", "text": "It is 15 kW, model GW10K.", "refs": []}
            ]
        }
    )
    # 15 is a number; GW10K is a model code and does not count.
    assert citations.verify(turn) == ["states 15, which no tool result contains"]


def test_a_number_inside_a_longer_one_does_not_count_as_found() -> None:
    turn = _turn(
        output={"blocks": [{"type": "text", "text": "Up to 1 unit.", "refs": []}]}
    )
    # "1" appears only inside 10 and 12.
    assert citations.verify(turn) == ["states 1, which no tool result contains"]


def test_refs_and_cards_beyond_the_tools_are_citation_failures() -> None:
    turn = _turn(
        output={
            "blocks": [
                {"type": "text", "text": "See this.", "refs": ["9999"]},
                {"type": "cards", "product_ids": [9999]},
            ]
        }
    )
    assert citations.verify(turn) == [
        "cites 9999, which no tool returned",
        "shows product 9999, which no tool returned",
    ]


# --- the production flags of 2026-10-18 (#258) ---------------------------------

FLAGGED: dict[str, dict[str, Any]] = json.loads(
    (
        Path(__file__).parent / "fixtures" / "quality" / "production-flags.json"
    ).read_text(encoding="utf-8")
)


def _logged(name: str) -> LoggedTurn:
    row = FLAGGED[name]
    return LoggedTurn(
        id=row["id"],
        conversation_id=row["conversation_id"],
        created_at=row["created_at"],
        locale=row["locale"],
        fallback=row["fallback"],
        tool_calls=row["tool_calls"],
        output=row["output"],
        question=row["question"],
        page=row["page"],
        approved=row.get("approved", False),
    )


def _said(turn: LoggedTurn, text: str) -> LoggedTurn:
    return replace(
        turn, output={"blocks": [{"type": "text", "text": text, "refs": []}]}
    )


def _sentence(text: str, phrase: str) -> str:
    """The one sentence or clause (split at `.`, `;`, `?`) holding `phrase`."""
    [sentence] = [part for part in re.split(r"[.;?] ", text) if phrase in part]
    return sentence


def test_turn_27_a_model_code_is_a_name_not_a_number() -> None:
    # Production flagged "states 5.0, which no tool result contains": the 5.0
    # of BU2-5.0-HV1. ground.py lets the code through; the re-check must too.
    assert citations.verify(_logged("t27")) == []


@pytest.mark.parametrize(
    "code", ["CB2-100.3-HV5", "BU2-5.0-HV1", "GW125/261-ESA-LCN-G10", "HS2-5K-T2-X"]
)
def test_whole_model_codes_carry_no_numbers(code: str) -> None:
    assert citations.verify(_said(_logged("t27"), f"Pair it with the {code}.")) == []


def test_a_number_beside_a_model_code_is_still_checked() -> None:
    turn = _logged("t27")
    # The tool returned 5.12 kWh for the BU2-5.0-HV1: that number is backed.
    assert citations.verify(_said(turn, "The BU2-5.0-HV1 holds 5.12 kWh.")) == []
    # The code's own digits back nothing written outside it.
    assert citations.verify(_said(turn, "The BU2-5.0-HV1 holds 5.0 kWh.")) == [
        "states 5.0, which no tool result contains"
    ]
    assert citations.verify(_said(turn, "The CB2-100.3-HV5 holds 100.3 kWh.")) == [
        "states 100.3, which no tool result contains"
    ]


@pytest.mark.parametrize("name", ["t33", "t36"])
def test_answers_from_our_manuals_pass_the_citation_check(name: str) -> None:
    assert citations.verify(_logged(name)) == []


def test_both_remit_questions_share_one_remit() -> None:
    # The spec says appropriate and better_pick share the remit: word for word.
    assert REMIT in APPROPRIATE.instructions
    assert REMIT in BETTER_PICK.instructions


def test_the_remit_keeps_document_answers_and_refers_service_requests() -> None:
    # Turns 33 (GoodWe warranty terms) and 36 (CB2 installation and clearances)
    # were judged out of remit because the remit sent warranty and
    # installation questions to the team. AGENTS.md §2 (2026-10-05) sends only
    # company, service and logistics questions there.
    within = _sentence(REMIT, "is within the remit")
    referral = _sentence(REMIT, "referral")
    for subject in ("warranty terms", "installation requirements", "clearances"):
        assert subject in within, subject
        assert subject not in referral, subject
    for request in (
        "making a warranty claim",
        "booking installation or commissioning",
        "delivery",
        "payment terms",
    ):
        assert request in referral, request


def test_the_remit_allows_both_stock_statuses_and_never_a_quantity() -> None:
    # AGENTS.md §2 2026-10-11: to the customer only the status, in stock or
    # temporarily out of stock, never the quantity.
    stock = _sentence(REMIT, "stock quantities")
    assert "in stock or temporarily out of stock" in stock
    assert "never gives stock quantities" in stock


def test_the_remit_allows_the_one_working_day_reply_promise() -> None:
    # AGENTS.md §2 2026-10-09: the team replies to an inquiry within one working
    # day, and Genie promises it (13-genie.md 目标 5, 6). Other dates and
    # commitments stay out.
    commitments = _sentence(REMIT, "commitment")
    assert "delivery times or dates" in commitments
    assert "service or appointment dates" in commitments
    assert "Incoterms" in commitments
    assert "except one" in commitments
    assert "replies to an inquiry within one working day" in _sentence(
        REMIT, "may promise"
    )
    assert "service commitments" not in REMIT


@pytest.mark.parametrize("name", ["t33", "t36"])
def test_turns_33_and_36_reach_the_judges_with_that_remit(
    name: str, judges: Judges
) -> None:
    status, record = judge_turn(_logged(name), JUDGES["jev"], JUDGES["deepseek"])
    assert status == "judged" and record["flags"] == []
    [state] = judges.states
    assert state["account"] == {"approved": False}
    assert state["reference"]["calls"][0]["name"] == "linker/search-knowledge"
    [asked] = judges.asked
    [appropriate] = [question for question in asked if question.name == "appropriate"]
    assert appropriate.instructions == APPROPRIATE.instructions
    assert "warranty terms" in appropriate.system_one()["instructions"]


def _priced(*, visible: bool, approved: bool) -> LoggedTurn:
    """The priced answer, its tool's price visible or withheld, for an
    approved account or not."""
    turn = _logged("price_approved")
    calls = copy.deepcopy(turn.tool_calls)
    if not visible:
        calls[0]["result"]["qualified"][0]["commerce"] = {
            "price_visible": False,
            "in_stock": True,
            "rfq_only": False,
        }
    return replace(turn, tool_calls=calls, approved=approved)


def test_the_judges_read_the_account_and_the_rule_needs_both_gates() -> None:
    assert build(_priced(visible=True, approved=True)).state["account"] == {
        "approved": True
    }
    assert build(_priced(visible=True, approved=False)).state["account"] == {
        "approved": False
    }
    rule = _sentence(REMIT, "may state a product price")
    assert "`price_visible` true" in rule and "`account.approved` is true" in rule
    other = _sentence(REMIT, "`account` is missing")
    assert "is false" in other and "states no price" in other
    # Telling an unapproved customer how to get a price is not a price.
    assert "inquiry" in _sentence(REMIT, "Proforma request")


def test_a_visible_price_for_an_approved_account_passes() -> None:
    assert citations.verify(_priced(visible=True, approved=True)) == []


def test_a_visible_price_for_an_account_not_approved_is_flagged() -> None:
    # The tool showed the price, but the account is a guest, pending or
    # restricted one (or the shell did not say: the default before #242).
    assert citations.verify(_priced(visible=True, approved=False)) == [
        "states the price of product 4109, and the account is not approved"
    ]


def test_a_price_the_tool_did_not_return_is_flagged_even_when_approved() -> None:
    # The account may see prices, but this turn's tool withheld it: nothing
    # backs the number (the tool output is the ground truth).
    for approved in (True, False):
        assert citations.verify(_priced(visible=False, approved=approved)) == [
            "states 1234.00, which no tool result contains"
        ]


# --- the cascade, as the worker drives it ---------------------------------------


class Judges:
    """Stands in for both judges at `linker_judges.cascade.call`."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.states: list[dict[str, Any]] = []
        self.asked: list[tuple[Question, ...]] = []
        self.jev: Callable[[tuple[Question, ...]], Verdict] = lambda qs: _verdict(
            {q.name: ("2" if q.name == "grounded" else _top(q), 0.95) for q in qs}
        )
        self.deepseek: Callable[[tuple[Question, ...]], Verdict] = lambda qs: _verdict(
            {q.name: ("2" if q.name == "grounded" else _top(q), 0.9) for q in qs},
            reason="checked against the reference",
        )

    def __call__(
        self, judge: Judge, state: dict[str, Any], questions: tuple[Question, ...]
    ) -> Verdict:
        self.calls.append(judge.name)
        self.states.append(state)
        self.asked.append(questions)
        return self.jev(questions) if judge.name == "jev" else self.deepseek(questions)


def _top(question: Question) -> str:
    return {"appropriate": "yes", "better_pick": "A"}[question.name]


def _verdict(
    answers: dict[str, tuple[str | None, float | None]],
    error: str | None = None,
    reason: str | None = None,
) -> Verdict:
    return Verdict(
        {
            name: Answer(label, confidence)
            for name, (label, confidence) in answers.items()
        },
        1.0,
        1,
        0.0,
        300,
        20,
        0.0001,
        "" if error else "typesafe/jev-1.13-20260917",
        reason,
        error,
    )


@pytest.fixture()
def judges(monkeypatch: pytest.MonkeyPatch) -> Judges:
    fake = Judges()
    monkeypatch.setattr(cascade_module, "call", fake)
    return fake


def test_a_confident_jev_verdict_stands_alone(judges: Judges) -> None:
    status, record = judge_turn(_turn(), JUDGES["jev"], JUDGES["deepseek"])
    assert status == "judged"
    assert judges.calls == ["jev"]
    assert record["labels"] == {
        "grounded": "2",
        "appropriate": "yes",
        "better_pick": "A",
    }
    assert record["flagged"] is False and record["escalated"] is False


def test_an_unsure_jev_escalates_and_says_why(judges: Judges) -> None:
    judges.jev = lambda qs: _verdict(
        {
            q.name: (
                "0" if q.name == "grounded" else _top(q),
                0.42 if q.name == "grounded" else 0.95,
            )
            for q in qs
        }
    )
    status, record = judge_turn(_turn(), JUDGES["jev"], JUDGES["deepseek"])
    assert status == "judged"
    assert judges.calls == ["jev", "deepseek"]
    assert record["escalated"] is True
    assert record["escalation"] == ["grounded 0.42 < 0.6"]
    assert record["sources"]["grounded"] == "deepseek"
    assert record["labels"]["grounded"] == "2"
    assert record["reasons"]["deepseek"] == "checked against the reference"


def test_a_failed_jev_call_is_reported_and_never_escalated(judges: Judges) -> None:
    judges.jev = lambda qs: _verdict(
        {q.name: (None, None) for q in qs},
        error="https://openrouter.ai/api/v1/systemone: HTTP 402: insufficient credits",
    )
    status, record = judge_turn(_turn(), JUDGES["jev"], JUDGES["deepseek"])
    assert status == "failed"
    # No silent model swap: deepseek-flash is not asked in Jev's place.
    assert judges.calls == ["jev"]
    assert record["error"].startswith("OpenRouter: first judge: https://openrouter.ai")
    assert "HTTP 402" in record["error"]
    assert record["labels"] == {
        "grounded": None,
        "appropriate": None,
        "better_pick": None,
    }


def test_a_failed_escalation_is_reported_as_deepseeks(judges: Judges) -> None:
    judges.jev = lambda qs: _verdict(
        {q.name: ("2" if q.name == "grounded" else _top(q), 0.1) for q in qs}
    )
    judges.deepseek = lambda qs: _verdict(
        {q.name: (None, None) for q in qs}, error="https://api.deepseek.com: HTTP 503"
    )
    status, record = judge_turn(_turn(), JUDGES["jev"], JUDGES["deepseek"])
    assert status == "failed"
    assert record["error"].startswith("api.deepseek.com: escalation judge:")


def test_the_flags_name_what_needs_a_look() -> None:
    clean = {"grounded": "2", "appropriate": "yes", "better_pick": "A"}
    assert flags_for(clean, []) == []
    assert flags_for({**clean, "grounded": "0"}, []) == ["contradicted"]
    assert flags_for({**clean, "grounded": "1"}, []) == ["unverifiable"]
    assert flags_for({**clean, "appropriate": "no"}, []) == ["out_of_remit"]
    assert flags_for({**clean, "better_pick": "B"}, []) == ["worse_pick"]
    assert flags_for(clean, ["states 15, …"]) == ["citation"]
    assert flags_for({**clean, "better_pick": None}, []) == ["unresolved"]


# --- the worker --------------------------------------------------------------


class Site:
    """The WordPress route, recording what it was sent."""

    def __init__(self) -> None:
        self.bodies: list[dict[str, Any]] = []
        self.headers: list[httpx.Headers] = []
        self.fail_with: int | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == ROUTE
        self.headers.append(request.headers)
        body = json.loads(request.content)
        self.bodies.append(body)
        if self.fail_with is not None:
            return httpx.Response(self.fail_with, text="down")
        return httpx.Response(
            200, json={"stored": [row["turn_id"] for row in body["judgments"]]}
        )


@pytest.fixture()
def site() -> Site:
    return Site()


def _worker(turns: Path, tmp_path: Path, site: Site) -> Worker:
    return Worker(
        TurnSource(turns),
        Store(tmp_path / "judgments.sqlite"),
        WordPress(
            "https://site.example",
            "token-123",
            transport=httpx.MockTransport(site.handler),
            sleep=lambda _: None,
        ),
    )


def test_the_first_start_judges_only_new_turns(
    turns: Path, tmp_path: Path, site: Site, judges: Judges
) -> None:
    _ask("an old question")
    worker = _worker(turns, tmp_path, site)
    assert worker.cycle(1000.0) == 0
    assert judges.calls == []

    _ask("10 kW three-phase?")
    assert worker.cycle(1030.0) == 1
    [pushed] = site.bodies[-1]["judgments"]
    assert pushed["question"] == "10 kW three-phase?"
    assert pushed["conversation_id"] == "812"
    assert pushed["status"] == "judged"
    assert pushed["answer"].startswith("This inverter is 10 kW.")
    assert site.headers[-1]["x-linker-judge-token"] == "token-123"
    assert "authorization" not in site.headers[-1]
    # Pushed once: the next cycle has nothing new and sends nothing.
    sent = len(site.bodies)
    worker.cycle(1060.0)
    assert len(site.bodies) == sent


def test_the_escalation_is_in_the_log(
    turns: Path,
    tmp_path: Path,
    site: Site,
    judges: Judges,
    caplog: pytest.LogCaptureFixture,
) -> None:
    worker = _worker(turns, tmp_path, site)
    worker.cycle(1000.0)
    judges.jev = lambda qs: _verdict(
        {q.name: ("2" if q.name == "grounded" else _top(q), 0.3) for q in qs}
    )
    _ask("10 kW?")
    with caplog.at_level(logging.INFO, logger="linker_genie.quality"):
        worker.cycle(1030.0)
    assert any(
        "escalated to deepseek-flash: grounded 0.30 < 0.6" in line
        for line in caplog.messages
    )


def test_an_openrouter_failure_is_loud_retried_and_then_given_up(
    turns: Path,
    tmp_path: Path,
    site: Site,
    judges: Judges,
    caplog: pytest.LogCaptureFixture,
) -> None:
    worker = _worker(turns, tmp_path, site)
    worker.cycle(1000.0)
    judges.jev = lambda qs: _verdict(
        {q.name: (None, None) for q in qs}, error="openrouter: HTTP 503: overloaded"
    )
    _ask("10 kW?")
    with caplog.at_level(logging.ERROR, logger="linker_genie.quality"):
        worker.cycle(1030.0)
    assert any(
        record.levelno == logging.ERROR
        and "not judged, attempt 1 of 3" in record.message
        for record in caplog.records
    )
    body = site.bodies[-1]
    assert body["judgments"][0]["status"] == "failed"
    assert "HTTP 503" in body["status"]["last_error"]
    assert body["status"]["retrying"] == 1

    # Not before the retry delay; then once per delay until the attempts run out.
    worker.cycle(1030.0 + RETRY_AFTER_SECONDS - 1)
    assert judges.calls.count("jev") == 1
    now = 1030.0
    for _ in range(MAX_ATTEMPTS - 1):
        now += RETRY_AFTER_SECONDS + 1
        worker.cycle(now)
    assert judges.calls.count("jev") == MAX_ATTEMPTS
    assert worker.status(now)["gave_up"] == 1
    worker.cycle(now + RETRY_AFTER_SECONDS + 1)
    assert judges.calls.count("jev") == MAX_ATTEMPTS
    assert "deepseek" not in judges.calls


def test_a_restarted_worker_still_reports_an_unresolved_failure(
    turns: Path, tmp_path: Path, site: Site, judges: Judges
) -> None:
    worker = _worker(turns, tmp_path, site)
    worker.cycle(1000.0)
    judges.jev = lambda qs: _verdict(
        {q.name: (None, None) for q in qs},
        error="openrouter: HTTP 401: User not found.",
    )
    _ask("10 kW?")
    worker.cycle(1030.0)

    restarted = _worker(turns, tmp_path, site)
    status = restarted.status(1060.0)
    assert status["last_error"] is not None and "HTTP 401" in status["last_error"]

    # Judged after all on the retry: the failure is no longer reported.
    judges.jev = Judges().jev
    restarted.cycle(1030.0 + RETRY_AFTER_SECONDS + 1)
    assert restarted.status(2000.0)["last_error"] is None


def test_a_site_that_refuses_keeps_the_verdicts_for_the_next_cycle(
    turns: Path,
    tmp_path: Path,
    site: Site,
    judges: Judges,
    caplog: pytest.LogCaptureFixture,
) -> None:
    worker = _worker(turns, tmp_path, site)
    worker.cycle(1000.0)
    before = len(site.bodies)
    _ask("10 kW?")
    site.fail_with = 503
    with caplog.at_level(logging.ERROR, logger="linker_genie.quality"):
        worker.cycle(1030.0)
    assert any("could not hand 1 verdict(s)" in line for line in caplog.messages)
    # 5xx is retried: three attempts in the one push.
    assert len(site.bodies) - before == 3

    site.fail_with = None
    worker.cycle(1060.0)
    assert [row["turn_id"] for row in site.bodies[-1]["judgments"]] == [1]


def test_an_idle_worker_still_reports_that_it_is_alive(
    turns: Path, tmp_path: Path, site: Site, judges: Judges
) -> None:
    worker = _worker(turns, tmp_path, site)
    worker.cycle(1000.0)
    first = len(site.bodies)
    worker.cycle(1030.0)
    assert len(site.bodies) == first
    worker.cycle(1000.0 + 601)
    assert len(site.bodies) == first + 1
    assert site.bodies[-1]["judgments"] == []
    assert site.bodies[-1]["status"]["judge"] == "typesafe/jev-1.13 (OpenRouter)"


def test_a_refused_token_is_not_retried_and_not_echoed(site: Site) -> None:
    site.fail_with = 401
    wordpress = WordPress(
        "https://site.example",
        "secret-token",
        transport=httpx.MockTransport(site.handler),
        sleep=lambda _: None,
    )
    with pytest.raises(PushError) as raised:
        wordpress.push([], {})
    assert len(site.bodies) == 1
    assert "secret-token" not in str(raised.value)


def test_turns_and_verdicts_past_retention_are_deleted_from_both_stores(
    turns: Path, tmp_path: Path, site: Site, judges: Judges
) -> None:
    worker = _worker(turns, tmp_path, site)
    worker.cycle(1000.0)
    _ask("old question")
    _ask("new question")
    # The log stamps turns with the real clock, so the sweep runs on it too.
    now = time.time()
    worker.cycle(now - 60)
    # Backdate the first turn past retention, as if logged 91 days ago.
    log = sqlite3.connect(turns)
    log.execute("UPDATE turns SET created_at = '2000-01-01 00:00:00' WHERE id = 1")
    log.commit()
    log.close()
    worker.store._db.execute("UPDATE judgments SET updated_at = 0 WHERE turn_id = 1")
    worker.store._db.execute(
        "UPDATE judgments SET updated_at = ? WHERE turn_id = 2", (now - 3600,)
    )
    worker.store._db.commit()

    worker.prune(now)

    assert [turn.id for turn in TurnSource(turns).after(0, 10)] == [2]
    left = [row[0] for row in worker.store._db.execute("SELECT turn_id FROM judgments")]
    assert left == [2]


def test_the_retention_sweep_runs_once_a_day(
    turns: Path,
    tmp_path: Path,
    site: Site,
    judges: Judges,
    caplog: pytest.LogCaptureFixture,
) -> None:
    worker = _worker(turns, tmp_path, site)
    with caplog.at_level(logging.INFO, logger="linker_genie.quality"):
        worker.cycle(PRUNE_EVERY_SECONDS)
        worker.cycle(PRUNE_EVERY_SECONDS + 30)
        worker.cycle(2 * PRUNE_EVERY_SECONDS)
    sweeps = [line for line in caplog.messages if line.startswith("retention:")]
    assert len(sweeps) == 2
    assert (
        sweeps[0] == "retention: deleted 0 turn(s) and 0 verdict(s) older than 90 days"
    )


def test_the_vps_keeps_turns_exactly_as_long_as_the_site_keeps_conversations() -> None:
    retention = (
        Path(__file__).resolve().parents[3]
        / "plugins/linker-tools/includes/Genie/Retention.php"
    ).read_text()
    match = re.search(r"const RETENTION_DAYS = (\d+);", retention)
    assert match is not None
    assert int(match.group(1)) == RETENTION_DAYS
