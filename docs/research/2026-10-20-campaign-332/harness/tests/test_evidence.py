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


def test_ab_500_records_the_injected_500() -> None:
    row = next(item for item in _rows() if item["id"] == "AB-500")
    assert row["injected_error"] == AB_500_INJECTED
    reasons = row["reasons"]
    assert isinstance(reasons, list)
    assert any("500" in str(reason) for reason in reasons)
