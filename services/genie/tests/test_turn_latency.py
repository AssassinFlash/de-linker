"""ops/turn_latency.py: completed/incomplete/unfinished, percentiles, filters."""

import re
import sqlite3
from pathlib import Path
from typing import Any

import pytest

import turn_latency
from linker_genie.log import TurnLog

COMMON: dict[str, Any] = {
    "locale": "en",
    "grounded": True,
    "failures": (),
    "fallback": False,
    "provider": "deepseek",
    "model": "deepseek-flash",
    "tool_calls": [],
    "output": {},
}


def _log(tmp_path: Path, rows: list[tuple[str, dict[str, float] | None]]) -> TurnLog:
    """A turn log with one row per (conversation, timing record). A dict is a
    record the service wrote (complete with `total`, or the INSERT shape without
    it); None is a turn logged before #336 (no record at all)."""
    log = TurnLog(tmp_path / "turns.sqlite")
    for conversation, timing in rows:
        log.record(conversation_id=conversation, contact=None, timing=timing, **COMMON)
    return log


def _db(log: TurnLog) -> sqlite3.Connection:
    return log._db


def _line(out: str, key: str) -> str:
    """One summary line, by the phase key it starts with."""
    return next(line for line in out.splitlines() if line.startswith(key))


def _counts(out: str) -> dict[str, int]:
    first = out.splitlines()[0]
    return {
        name: int(value)
        for name, value in re.findall(r"(completed|incomplete|unfinished)=(\d+)", first)
    }


def test_percentiles_are_nearest_rank_measured_turns() -> None:
    assert turn_latency._percentile([1.0, 2.0, 3.0, 4.0], 0.50) == 2.0  # ceil(0.5*4)
    assert turn_latency._percentile([1.0, 2.0, 3.0, 4.0], 0.95) == 4.0  # ceil(0.95*4)
    assert turn_latency._percentile([], 0.50) == 0.0


def test_only_completed_turns_enter_the_percentiles(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """#336 review: the INSERT shape (phases, no `total`) is an incomplete turn;
    it is counted apart and never feeds a percentile."""
    log = _log(
        tmp_path,
        [
            ("c1", {"total": 12.0, "understand": 3.0, "model": 8.0}),
            ("c1", {"total": 4.0, "understand": 1.0, "model": 2.0}),
            ("c2", {"total": 20.0, "understand": 5.0}),  # a turn without a model
            ("c3", {"understand": 0.2}),  # the INSERT shape: stream never ran
            ("c4", None),  # a turn logged before #336: no record at all
        ],
    )
    log.close()
    assert turn_latency.main([str(tmp_path / "turns.sqlite")]) == 0
    out = capsys.readouterr().out
    assert _counts(out) == {"completed": 3, "incomplete": 1, "unfinished": 0}
    # `total` first, then the phases sorted; n counts only completed turns that
    # ran the phase, so the gate reads a phase's spread over its own turns.
    assert re.fullmatch(
        r"total\s+n=3\s+p50=\s*12\.000\s+p95=\s*20\.000\s+max=\s*20\.000",
        _line(out, "total"),
    )
    assert re.fullmatch(
        r"model\s+n=2\s+p50=\s*2\.000\s+p95=\s*8\.000\s+max=\s*8\.000",
        _line(out, "model"),
    )
    assert out.index("total") < out.index("model ") < out.index("understand")


def test_a_malformed_record_is_incomplete_never_a_percentile(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = _log(tmp_path, [("c1", {"total": 9.0}), ("c1", {"total": 5.0})])
    _db(log).execute("UPDATE turns SET timing = '{not json' WHERE id = 2")
    _db(log).commit()
    log.close()
    assert turn_latency.main([str(tmp_path / "turns.sqlite")]) == 0
    out = capsys.readouterr().out
    assert _counts(out) == {"completed": 1, "incomplete": 1, "unfinished": 0}
    assert re.fullmatch(
        r"total\s+n=1\s+p50=\s*9\.000\s+p95=\s*9\.000\s+max=\s*9\.000",
        _line(out, "total"),
    )


def test_a_start_note_left_by_an_unfinished_turn_is_counted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """#336 review: a turn that never answered has no `turns` row; its start note
    is the only trace, and it is reported — but a note young enough to be a turn
    still in flight is not."""
    log = _log(tmp_path, [("c1", {"total": 3.0})])
    in_flight = log.start("c1", "en")
    dead = log.start("c2", "de")
    # Age the dead turn's note past the grace window; the other stays fresh.
    _db(log).execute(
        "UPDATE turn_starts SET created_at = '2020-01-01 00:00:00' WHERE token = ?",
        (dead,),
    )
    _db(log).commit()
    assert in_flight != dead
    log.close()
    assert turn_latency.main([str(tmp_path / "turns.sqlite")]) == 0
    out = capsys.readouterr().out
    assert _counts(out) == {"completed": 1, "incomplete": 0, "unfinished": 1}


def test_the_filters_slice_one_log(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """#336 review: the 100-question run and EN/DE comparisons read one log, so
    the summary filters by conversation, locale and the created_at window."""
    log = _log(
        tmp_path,
        [
            ("c1", {"total": 1.0}),
            ("c2", {"total": 2.0}),
            ("c1", {"total": 3.0}),
        ],
    )
    db = _db(log)
    db.execute("UPDATE turns SET locale = 'de' WHERE id = 2")
    db.execute("UPDATE turns SET created_at = '2026-10-19 10:00:00' WHERE id <= 2")
    db.execute("UPDATE turns SET created_at = '2026-10-20 10:00:00' WHERE id = 3")
    db.commit()
    log.close()
    path = str(tmp_path / "turns.sqlite")

    def total_line(*argv: str) -> str:
        capsys.readouterr()  # clear what earlier calls printed
        assert turn_latency.main([path, *argv]) == 0
        return _line(capsys.readouterr().out, "total")

    assert "n=2" in total_line("--conversation", "c1")  # ids 1 and 3
    assert "n=1" in total_line("--conversation", "c1", "--until", "2026-10-20")
    assert "2.000" in total_line("--locale", "de")  # id 2 alone
    assert "n=1" in total_line("--since", "2026-10-20")
    assert "3.000" in total_line("--since", "2026-10-20")
    assert "n=2" in total_line("--until", "2026-10-20")


def test_a_log_without_completed_turns_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = _log(tmp_path, [("c1", {"understand": 1.0}), ("c2", None)])
    log.close()
    assert turn_latency.main([str(tmp_path / "turns.sqlite")]) == 1
    out = capsys.readouterr().out
    assert _counts(out) == {"completed": 0, "incomplete": 1, "unfinished": 0}
    assert "no completed turns" in out


def test_a_log_from_before_336_reads_unfinished_as_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """#336 review: an old log has no turn_starts table; the summary must not
    raise for it (the start notes are simply absent)."""
    path = tmp_path / "old.sqlite"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE turns (id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL,"
        " created_at TEXT NOT NULL DEFAULT (datetime('now')), locale TEXT NOT NULL,"
        " grounded INTEGER NOT NULL, failures TEXT NOT NULL, fallback INTEGER NOT NULL,"
        " provider TEXT NOT NULL, model TEXT NOT NULL, tool_calls TEXT NOT NULL,"
        " output TEXT NOT NULL, vote INTEGER, timing TEXT)"
    )
    db.execute(
        "INSERT INTO turns (conversation_id, locale, grounded, failures, fallback,"
        " provider, model, tool_calls, output, timing)"
        " VALUES ('c1', 'en', 1, '[]', 0, 'deepseek', 'deepseek-flash', '[]', '{}',"
        " '{\"total\": 2.0}')"
    )
    db.commit()
    db.close()
    assert turn_latency.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert _counts(out) == {"completed": 1, "incomplete": 0, "unfinished": 0}
