from __future__ import annotations

import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import stack


def test_clean_env_strips_fault_keys_and_keeps_an_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GENIE_BASE_URL", "http://stub")
    monkeypatch.setenv("GENIE_INDEX", "/tmp/old")
    monkeypatch.setenv("PATH", os.environ.get("PATH", ""))
    cleaned = stack.clean_env()
    assert "GENIE_BASE_URL" not in cleaned
    assert "GENIE_INDEX" not in cleaned
    assert cleaned["PATH"]
    replaced = stack.clean_env({"GENIE_INDEX": "/tmp/real"})
    assert replaced["GENIE_INDEX"] == "/tmp/real"
    monkeypatch.delenv("GENIE_BASE_URL", raising=False)


def test_health_is_false_when_the_port_does_not_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.URLError("down")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert stack.health() is False


def test_turn_log_reads_are_scoped_to_the_question(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "turns.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE turns ("
        "id INTEGER, question TEXT, provider TEXT, model TEXT, "
        "fallback INTEGER, failures TEXT, grounded INTEGER, understanding TEXT)"
    )
    connection.execute(
        "INSERT INTO turns VALUES (4, ?, ?, ?, 0, '[]', 1, ?)",
        ("Do you stock it?", "deepseek", "deepseek-flash", "{}"),
    )
    connection.commit()
    connection.close()
    monkeypatch.setattr(stack, "TURN_LOG", database)
    assert stack.max_turn_id() == 4
    found = stack.latest_turn("Do you stock it?", 0)
    assert found["log_id"] == 4
    assert found["provider"] == "deepseek"
    assert stack.latest_turn("Do you stock it?", 4) == {}
    assert stack.latest_turn("other", 0) == {}


def test_missing_turn_log_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stack, "TURN_LOG", tmp_path / "absent.sqlite")
    assert stack.max_turn_id() == 0
    assert stack.latest_turn("q") == {}


def test_stop_genie_with_no_pid_file_does_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stack, "PID", tmp_path / "genie.pid")
    stack.stop_genie()
    assert not (tmp_path / "genie.pid").exists()


def test_alive_knows_this_process_and_a_pid_that_cannot_exist() -> None:
    assert stack._alive(os.getpid()) is True
    assert stack._alive(2_000_000_000) is False
