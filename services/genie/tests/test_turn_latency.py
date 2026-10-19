"""ops/turn_latency.py: count/p50/p95 per phase from the turn log's timing records."""

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


def _log(tmp_path: Path, rows: list[tuple[str, dict[str, float] | None]]) -> Path:
    """A turn log with one row per (conversation, timing record); None = a turn
    whose stream never ended (the row keeps NULL, #336)."""
    log = TurnLog(tmp_path / "turns.sqlite")
    for conversation, timing in rows:
        log.record(conversation_id=conversation, contact=None, timing=timing, **COMMON)
    log.close()
    return tmp_path / "turns.sqlite"


def _line(out: str, key: str) -> str:
    """One summary line, by the phase key it starts with."""
    return next(line for line in out.splitlines() if line.startswith(key))


def test_percentiles_are_nearest_rank_measured_turns() -> None:
    assert (
        turn_latency._percentile([1.0, 2.0, 3.0, 4.0], 0.50) == 2.0
    )  # ceil(0.5*4)=2nd
    assert (
        turn_latency._percentile([1.0, 2.0, 3.0, 4.0], 0.95) == 4.0
    )  # ceil(0.95*4)=4th
    assert turn_latency._percentile([], 0.50) == 0.0


def test_every_phase_is_counted_and_summarized(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _log(
        tmp_path,
        [
            ("c1", {"total": 12.0, "understand": 3.0, "model": 8.0}),
            ("c1", {"total": 4.0, "understand": 1.0, "model": 2.0}),
            ("c2", {"total": 20.0, "understand": 5.0}),  # a turn without a model
            ("c3", None),  # no record: a turn logged before #336
        ],
    )
    assert turn_latency.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "4 timed turns" not in out  # the NULL row is not a timed turn
    assert "3 timed turns" in out
    # `total` first, then the phases sorted; n counts only the turns that ran
    # the phase, so the gate reads a phase's spread over its own turns.
    assert re.fullmatch(
        r"total\s+n=3\s+p50=\s*12\.000\s+p95=\s*20\.000\s+max=\s*20\.000",
        _line(out, "total"),
    )
    assert re.fullmatch(
        r"model\s+n=2\s+p50=\s*2\.000\s+p95=\s*8\.000\s+max=\s*8\.000",
        _line(out, "model"),
    )
    assert out.index("total") < out.index("model ") < out.index("understand")


def test_the_conversation_filter_reads_one_thread(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _log(
        tmp_path,
        [
            ("c1", {"total": 2.0}),
            ("c2", {"total": 9.0}),
        ],
    )
    assert turn_latency.main([str(path), "--conversation", "c2"]) == 0
    out = capsys.readouterr().out
    assert "1 timed turns" in out
    assert "p50=" in _line(out, "total") and "9.000" in _line(out, "total")


def test_a_log_without_records_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _log(tmp_path, [("c1", None)])
    assert turn_latency.main([str(path)]) == 1
    assert "no timing records" in capsys.readouterr().out


def test_a_malformed_record_is_skipped_never_raised(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _log(tmp_path, [("c1", {"total": 1.0})])
    db = sqlite3.connect(path)
    db.execute("UPDATE turns SET timing = '{not json' WHERE id = 1")
    db.commit()
    db.close()
    assert turn_latency.main([str(path)]) == 1
    assert "no timing records" in capsys.readouterr().out
