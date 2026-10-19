"""Nearest-rank p95, and parity counted beside pass and defect."""

from __future__ import annotations

import math
from typing import Any

from summary import grade_of, nearest_rank, render


def test_nearest_rank_matches_ceil() -> None:
    values = [float(index) for index in range(111)]
    assert nearest_rank(values, 0.95) == float(math.ceil(0.95 * 111) - 1)
    # The old index `int(n * 0.95) - 1` is one rank low on this n.
    old = values[max(0, int(111 * 0.95) - 1)]
    assert old == 104.0
    assert nearest_rank(values, 0.95) == 105.0
    assert nearest_rank([], 0.95) == 0.0


def test_grade_of_keeps_triage_defect_as_review() -> None:
    assert grade_of({"verdict": "TRIAGE_PASS"}) == "pass"
    assert grade_of({"verdict": "TRIAGE_ERROR"}) == "defect"
    assert grade_of({"verdict": "TRIAGE_DEFECT"}) == "review"
    assert grade_of({"verdict": "TRIAGE_REVIEW"}) == "review"
    assert grade_of({"grade": "parity", "verdict": "TRIAGE_PASS"}) == "parity"


def test_render_counts_parity() -> None:
    rows = [
        {"class": "units", "lang": "en", "grade": "parity", "duration_s": 1.0},
        {"class": "units", "lang": "de", "grade": "pass", "duration_s": 3.0},
        {"class": "units", "lang": "en", "grade": "defect", "duration_s": 2.0},
    ]
    text = render(rows)
    assert "| class | EN | DE | pass | defect | parity | obs |" in text
    assert "| 数量/单位 | 2 | 1 | 1 | 1 | 1 | 0 |" in text
    assert "p95 3.0s" in text
    assert "'parity': 1" in text
    assert "'pass': 1" in text
    assert "'defect': 1" in text


def test_missing_duration_is_left_out() -> None:
    rows: list[dict[str, Any]] = [
        {"class": "units", "lang": "en", "grade": "pass", "duration_s": 4.0},
        {"class": "units", "lang": "de", "grade": "pass"},
    ]
    text = render(rows)
    assert "p50 4.0s" in text
    assert "p95 4.0s" in text
    assert "max 4.0s" in text


def test_no_durations_do_not_invent_a_zero_percentile() -> None:
    text = render([{"class": "units", "lang": "en", "grade": "pass"}])
    assert "p95" not in text
    assert "0.0s" not in text
