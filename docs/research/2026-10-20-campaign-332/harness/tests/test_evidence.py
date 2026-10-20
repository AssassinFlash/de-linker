"""The committed verdict file carries the published judgment."""

from __future__ import annotations

import json
from pathlib import Path

VERDICTS = Path(__file__).resolve().parents[2] / "verdicts.jsonl"

# The service recorded this on the second AB-500 turn, in understanding.call_failures.
# It is the injected 500. The customer-facing failures[] line is the handoff text.
AB_500_INJECTED = (
    "linker/search-products returned 500 for "
    "{'input[series]': 'saj-h2', 'input[lang]': 'en', 'input[limit]': 6}"
)


def _rows() -> list[dict[str, object]]:
    return [
        json.loads(line) for line in VERDICTS.read_text().splitlines() if line.strip()
    ]


def test_every_row_has_a_published_verdict_and_reasons() -> None:
    rows = _rows()
    assert {row["id"] for row in rows} >= {
        "AB-500",
        "RATE-BURST",
        "VPS-DOWN",
        "VPS-KILL",
    }
    for row in rows:
        assert row["verdict"] in {"pass", "defect"}
        assert isinstance(row["reasons"], list)
        assert row["verdict"] == row["hand"]
        assert row["auto"] == row["verdict"]
        if row["verdict"] == "pass":
            assert row["reasons"] == []


def test_the_replayed_cuts_and_empty_stream_are_recorded() -> None:
    rows = {row["id"]: row for row in _rows()}
    for case_id in ("SSE-PARTIAL", "SSE-ATTACHMENT", "SSE-READING", "M-EMPTY-STREAM"):
        row = rows[case_id]
        assert row["verdict"] == "defect"
        assert row["evidence"] == f"cases.jsonl#{case_id}"
    partial = rows["SSE-PARTIAL"]["cut_observed"]
    assert isinstance(partial, dict)
    assert partial["where"] == "partial-block"
    assert partial["marker_present"] is True
    assert partial["done_in_shortened"] is False
    attachment = rows["SSE-ATTACHMENT"]["cut_observed"]
    assert isinstance(attachment, dict)
    assert attachment["where"] == "attachment"
    assert attachment["marker_present"] is True
    assert "reading" not in attachment["shortened_events"]
    reading = rows["SSE-READING"]["cut_observed"]
    assert isinstance(reading, dict)
    assert reading["marker_present"] is True
    assert "reading" in reading["shortened_events"]
    assert reading["done_in_shortened"] is False
    empty = rows["M-EMPTY-STREAM"]
    failures = empty["failures"]
    assert empty["done"] is True
    assert empty["fallback"] is True
    assert isinstance(failures, list)
    assert any("JSON" in str(item) for item in failures)


def test_ab_500_records_the_injected_500() -> None:
    row = next(item for item in _rows() if item["id"] == "AB-500")
    assert row["injected_error"] == AB_500_INJECTED
    reasons = row["reasons"]
    assert isinstance(reasons, list)
    assert any("500" in str(reason) for reason in reasons)
