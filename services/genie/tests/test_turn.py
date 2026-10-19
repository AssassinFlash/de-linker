"""POST /assistant/turn streams SSE; /turn is the same route; votes land."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import SHELL
from fastapi.testclient import TestClient

import linker_genie.app as app_module
from linker_genie.app import app
from linker_genie.facts import Fact, TurnFacts
from linker_genie.log import TurnLog
from linker_genie.schema import CardsBlock, TextBlock, TurnOutput, TurnRequest
from linker_genie.understand import nothing


@pytest.fixture(autouse=True)
def no_understanding() -> Iterator[None]:
    """The turn tests inject the generator; the understanding layer has its own
    tests (test_understand.py), so these never reach the Store API or Jev."""
    app.state.prepare = nothing
    yield
    del app.state.prepare


@pytest.fixture()
def log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TurnLog]:
    """A turn log in a temp dir, so tests never touch the real cache."""
    log = TurnLog(tmp_path / "turns.sqlite")
    monkeypatch.setattr(app_module, "_log", log)
    yield log
    log.close()


def _generate(request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
    facts = TurnFacts()
    facts.product_ids = {4107}
    facts.qualified_ids = {4107}
    facts.add(Fact(id="p4107.ac_power_kw", value="10", source="selection-facts"))
    return (
        TurnOutput(
            language=request.locale,
            blocks=[
                TextBlock(
                    text="This inverter is {fact:p4107.ac_power_kw} kW.",
                    refs=["4107"],
                ),
                CardsBlock(product_ids=[4107]),
            ],
        ),
        facts,
    )


def test_assistant_turn_streams_blocks(log: TurnLog) -> None:
    app.state.generate = _generate
    client = TestClient(app, headers=SHELL)
    response = client.post(
        "/assistant/turn",
        json={
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "10 kWp three-phase"}],
            "locale": "en",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: meta" in body
    assert "event: block" in body
    assert "event: done" in body
    assert "10 kW" in body


def test_turn_alias_is_the_same_handler(log: TurnLog) -> None:
    app.state.generate = _generate
    client = TestClient(app, headers=SHELL)
    response = client.post(
        "/turn",
        json={
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "hello"}],
            "locale": "de",
        },
    )
    assert response.status_code == 200
    assert "event: done" in response.text


def _meta(body: str) -> dict[str, Any]:
    for event in body.split("\n\n"):
        if "event: meta" in event:
            for line in event.splitlines():
                if line.startswith("data: "):
                    data: dict[str, Any] = json.loads(line[len("data: ") :])
                    return data
    raise AssertionError("no meta event in stream")


def test_meta_carries_the_logged_turn_id(log: TurnLog) -> None:
    app.state.generate = _generate
    client = TestClient(app, headers=SHELL)
    response = client.post(
        "/assistant/turn",
        json={
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    meta = _meta(response.text)
    assert isinstance(meta["turn_id"], int)
    assert meta["turn_id"] >= 1
    assert log.vote(meta["turn_id"], 1)


def test_vote_stores_a_thumbs_up_or_down(log: TurnLog) -> None:
    app.state.generate = _generate
    client = TestClient(app, headers=SHELL)
    body = client.post(
        "/assistant/turn",
        json={
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "hello"}],
        },
    ).text
    turn_id = _meta(body)["turn_id"]

    assert client.post(f"/turn/{turn_id}/vote", json={"vote": -1}).json() == {
        "ok": True
    }
    assert client.post(f"/assistant/turn/{turn_id}/vote", json={"vote": 1}).json() == {
        "ok": True
    }

    row = log._db.execute("SELECT vote FROM turns WHERE id = ?", (turn_id,)).fetchone()
    assert row == (1,)


def test_vote_on_an_unknown_turn_is_404(log: TurnLog) -> None:
    client = TestClient(app, headers=SHELL)
    assert client.post("/turn/999999/vote", json={"vote": 1}).status_code == 404


def test_a_vote_outside_the_scale_is_refused(log: TurnLog) -> None:
    client = TestClient(app, headers=SHELL)
    assert client.post("/turn/1/vote", json={"vote": 5}).status_code == 422


def test_an_internal_failure_is_logged_and_raised(log: TurnLog) -> None:
    def broken(request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        raise KeyError("model backend exploded")

    app.state.generate = broken
    client = TestClient(app, headers=SHELL)
    with pytest.raises(KeyError):
        client.post(
            "/assistant/turn",
            json={
                "conversation_id": "c1",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    row = log._db.execute("SELECT grounded, fallback, failures FROM turns").fetchone()
    assert row is not None
    assert row[0] == 0 and row[1] == 1
    assert "internal" in row[2]


def test_a_jev_failure_is_visible_in_the_stream_and_the_log(log: TurnLog) -> None:
    from linker_genie.route import Route
    from linker_genie.understand import Prepared

    def prepare(request: TurnRequest) -> Prepared:
        return Prepared(
            route=Route("model", reasons=("jev unavailable",)),
            log={
                "jev_error": "jev failed after 3 attempts: http 503",
                "route": "model",
            },
        )

    app.state.prepare = prepare
    app.state.generate = _generate
    response = TestClient(app, headers=SHELL).post(
        "/turn",
        json={
            "conversation_id": "c9",
            "messages": [{"role": "user", "content": "hi"}],
            "locale": "en",
        },
    )
    meta = json.loads(response.text.split("data: ", 1)[1].split("\n", 1)[0])
    assert meta["route"] == "model"
    assert meta["jev_error"] == "jev failed after 3 attempts: http 503"
    row = log._db.execute(
        "SELECT understanding FROM turns WHERE conversation_id = 'c9'"
    ).fetchone()
    assert json.loads(row[0])["jev_error"] == "jev failed after 3 attempts: http 503"


def test_an_old_log_gains_the_understanding_column(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "old.sqlite"
    old = sqlite3.connect(path)
    old.execute(
        "CREATE TABLE turns (id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL,"
        " created_at TEXT NOT NULL DEFAULT (datetime('now')), locale TEXT NOT NULL,"
        " grounded INTEGER NOT NULL, failures TEXT NOT NULL, fallback INTEGER NOT NULL,"
        " provider TEXT NOT NULL, model TEXT NOT NULL, tool_calls TEXT NOT NULL,"
        " output TEXT NOT NULL, vote INTEGER)"
    )
    old.commit()
    old.close()
    upgraded = TurnLog(path)
    upgraded.record("c", "en", True, (), False, "deepseek", "deepseek-flash", [], {})
    columns = [r[1] for r in upgraded._db.execute("PRAGMA table_info(turns)")]
    upgraded.close()
    # #258 adds the account flag after it.
    assert columns[-3:] == ["understanding", "approved", "contact"]


def _blocks(body: str) -> list[dict[str, Any]]:
    return [
        json.loads(event.split("data: ", 1)[1])
        for event in body.split("\n\n")
        if event.startswith("event: block")
    ]


def _post(conversation: str, *customer: str, locale: str = "en") -> str:
    messages: list[dict[str, str]] = []
    for text in customer:
        if messages:
            messages.append({"role": "assistant", "content": "An answer."})
        messages.append({"role": "user", "content": text})
    response = TestClient(app, headers=SHELL).post(
        "/assistant/turn",
        json={"conversation_id": conversation, "messages": messages, "locale": locale},
    )
    assert response.status_code == 200
    return response.text


@pytest.mark.parametrize(
    ("message", "locale", "sentence"),
    [
        (
            "Can I talk to a person?",
            "en",
            "Someone from the Linker team can get in touch with you by email.",
        ),
        (
            "Ich möchte mit einem Mitarbeiter sprechen",
            "de",
            "Jemand aus dem Linker-Team kann sich per E-Mail bei Ihnen melden.",
        ),
    ],
)
def test_a_request_for_a_person_is_answered_without_the_model(
    log: TurnLog, message: str, locale: str, sentence: str
) -> None:
    from linker_genie.understand import Understander

    def no_model(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        raise AssertionError("the model must not run for a request for a person")

    app.state.prepare = lambda body: Understander(None, None).prepare(body, None)  # type: ignore[arg-type]
    app.state.generate = no_model
    body = _post("p1", message, locale=locale)
    assert _blocks(body) == [
        {"type": "text", "text": sentence, "refs": []},
        {"type": "contact", "reason": "asked"},
    ]
    row = log._db.execute("SELECT output, model, contact FROM turns").fetchone()
    assert json.loads(row[0])["blocks"][-1] == {"type": "contact", "reason": "asked"}
    # No model ran: model-routing audits read this field (review round 1 of #243).
    assert row[1] == "none"
    assert row[2] == "asked"


def _frustrated(request: TurnRequest) -> Any:
    from linker_genie.jev import Reading
    from linker_genie.route import Route
    from linker_genie.understand import Prepared

    return Prepared(
        route=Route("model"), reading=Reading("other", 0.9, 0.1, 0.93, 0.1, 2.0, 0.0)
    )


def test_frustration_keeps_the_answer_and_adds_the_offer(log: TurnLog) -> None:
    app.state.prepare = _frustrated
    app.state.generate = _generate
    blocks = _blocks(_post("f1", "This is useless."))
    assert [b["type"] for b in blocks] == ["text", "cards", "contact"]
    assert blocks[-1]["reason"] == "dissatisfied"


def test_the_offer_never_comes_on_two_turns_in_a_row(log: TurnLog) -> None:
    app.state.prepare = _frustrated
    app.state.generate = _generate
    first = _blocks(_post("f2", "This is useless."))
    second = _blocks(_post("f2", "This is useless.", "Still useless!"))
    third = _blocks(_post("f2", "This is useless.", "Still useless!", "Nope."))
    assert [b["type"] for b in first][-1] == "contact"
    assert "contact" not in [b["type"] for b in second]
    assert [b["type"] for b in third][-1] == "contact"
    # Another conversation is not this one's history.
    assert _blocks(_post("f3", "This is useless."))[-1]["type"] == "contact"


def test_the_third_round_of_one_question_offers_once(log: TurnLog) -> None:
    app.state.generate = _generate
    question = "Which battery fits the SAJ H2-10K-T3?"
    rounds = [
        [b["type"] for b in _blocks(_post("r1", *([question] * n)))]
        for n in (1, 2, 3, 4, 5)
    ]
    assert ["contact" in shown for shown in rounds] == [
        False,
        False,
        True,
        False,
        False,
    ]


def test_the_log_keeps_the_offer_as_a_plain_field(tmp_path: Path) -> None:
    log = TurnLog(tmp_path / "turns.sqlite")
    common: dict[str, Any] = {
        "locale": "en",
        "grounded": True,
        "failures": (),
        "fallback": False,
        "provider": "deepseek",
        "model": "deepseek-flash",
        "tool_calls": [],
        "output": {},
    }
    log.record(conversation_id="c", contact=None, **common)
    log.record(conversation_id="c", contact="repeat", **common)
    log.record(conversation_id="d", contact="asked", **common)
    assert log.offers("c", 5) == [True, False]
    log.close()


def test_a_parts_turn_streams_its_card_and_no_model_writes(
    log: TurnLog, vocabulary: Any
) -> None:
    """#251: the service writes a parts turn; the card carries rows and the write."""
    from linker_genie import parts
    from linker_genie.route import Route
    from linker_genie.understand import Prepared

    source = parts.Source(
        "text",
        tuple(
            parts.parse_text(
                "2x SAJ H2-10K-T3\n3 x GoodWe GW10K-ETA-G20\n1 x SMA Sunny Boy 5.0"
            )
        ),
        since=0,
    )
    result = parts.build(source, [], vocabulary)

    def prepare(request: TurnRequest) -> Prepared:
        del request
        return Prepared(
            route=Route("parts", no_cards=True, no_handoff=True), parts_list=result
        )

    app.state.prepare = prepare
    client = TestClient(app, headers=SHELL)
    response = client.post(
        "/assistant/turn",
        json={
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "2x SAJ H2-10K-T3"}],
            "locale": "en",
        },
    )
    assert response.status_code == 200
    body = response.text
    meta = _meta(body)
    assert meta["route"] == "parts"
    assert meta["grounded"] and not meta["fallback"]
    assert '"type": "parts"' in body
    assert '"product_id": 4107' in body
    assert '"quantity": 2' in body
    assert "not in our product range" in body
    assert '"provider"' not in body
    # The turn log says the service wrote it (no model, no tool calls).
    row = log._db.execute("SELECT provider, model, tool_calls FROM turns").fetchone()
    assert row is not None and (row[0], row[1]) == ("service", "none")
    assert row[2] in ("[]", None)


def test_forget_purges_the_rows_a_file_parts_list_read(log: TurnLog) -> None:
    """#251: a list read from a file is the file's words; deleting the
    conversation takes its row texts, as it takes the reading (#236)."""
    log.record(
        conversation_id="c1",
        locale="en",
        grounded=True,
        failures=(),
        fallback=False,
        provider="service",
        model="none",
        tool_calls=[
            {
                "name": "linker/read-attachment",
                "arguments": {"id": "att1"},
                "ok": True,
                "result": {
                    "id": "att1",
                    "kind": "list",
                    "text": "SAJ H2-10K-T3\t2",
                },
            }
        ],
        output={
            "language": "en",
            "blocks": [
                {"type": "text", "text": "I checked your list.", "refs": []},
                {
                    "type": "parts",
                    "rows": [
                        {
                            "line": 1,
                            "text": "SAJ H2-10K-T3",
                            "quantity": 2,
                            "status": "matched",
                            "product_id": 4107,
                            "label": "H2-10K-T3",
                            "options": [],
                        }
                    ],
                    "ask_line": None,
                    "add": None,
                    "truncated": False,
                },
            ],
        },
        question="Attached: list.csv",
        understanding={"parts": {"kind": "table", "reading": "att1", "rows": 1}},
    )
    assert log.forget("c1") == 1
    row = log._db.execute("SELECT output, question FROM turns").fetchone()
    assert row is not None
    output = json.loads(row[0])
    block = next(b for b in output["blocks"] if b["type"] == "parts")
    assert block["rows"][0]["text"] == ""
    assert block["rows"][0]["purged"] is True
    # The customer's own message stays; it names the file, not its rows.
    assert row[1] == "Attached: list.csv"
