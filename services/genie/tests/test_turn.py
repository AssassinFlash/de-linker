"""POST /assistant/turn streams SSE; /turn is the same route; votes land."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import linker_genie.app as app_module
from linker_genie.app import app
from linker_genie.facts import Fact, TurnFacts
from linker_genie.log import TurnLog
from linker_genie.schema import CardsBlock, TextBlock, TurnOutput, TurnRequest


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
    client = TestClient(app)
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
    client = TestClient(app)
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
    client = TestClient(app)
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
    client = TestClient(app)
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
    client = TestClient(app)
    assert client.post("/turn/999999/vote", json={"vote": 1}).status_code == 404


def test_a_vote_outside_the_scale_is_refused(log: TurnLog) -> None:
    client = TestClient(app)
    assert client.post("/turn/1/vote", json={"vote": 5}).status_code == 422


def test_an_internal_failure_is_logged_and_raised(log: TurnLog) -> None:
    def broken(request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        raise KeyError("model backend exploded")

    app.state.generate = broken
    client = TestClient(app)
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
