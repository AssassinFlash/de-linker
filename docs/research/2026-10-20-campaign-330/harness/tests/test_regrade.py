"""Round-2 overturns are importable without the evidence file."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import regrade


def test_overturns_are_six_defects_and_four_parity() -> None:
    assert len(regrade.OVERTURNS) == 10
    grades = Counter(item["grade"] for item in regrade.OVERTURNS.values())
    assert grades["defect"] == 6
    assert grades["parity"] == 4
    assert regrade.OVERTURNS["H4-DE"]["grade"] == "parity"
    assert regrade.OVERTURNS["G5-DE"]["grade"] == "parity"
    assert set(
        regrade.NUMBER_CHECKS
    )  # recorded, and import did not need the evidence file
    assert regrade.NUMBER_CHECKS["A4-EN"]["status"] == "fabricated"


def test_verdict_drops_the_stream_and_applies_the_overturn() -> None:
    row = {
        "case": "A4-EN",
        "class": "misspelling",
        "lang": "en",
        "request": "what is the output of the GooodWe GW5K-ETA-G2O?",
        "grade": "pass",
        "stream": "raw sse that must not be committed",
        "flags": ["numbers to verify: 11"],
        "meta": {"turn_id": 8},
        "blocks": [{"type": "text", "text": "10 / 30 V"}],
        "duration_s": 12.3,
        "verdict": "TRIAGE_REVIEW",
    }
    out = regrade.verdict_of(row)
    assert "stream" not in out
    assert "raw sse" not in json.dumps(out)
    assert out["grade"] == "defect"
    assert out["defect"] == "D12"
    assert out["regrade"] == "round-2"
    assert out["request"] == row["request"]
    assert out["numbers_verification"]["status"] == "fabricated"
    assert out["evidence"].endswith("#A4-EN")


def test_parity_is_not_a_pass() -> None:
    row = {
        "case": "F1-DE",
        "class": "brand-conflict",
        "lang": "de",
        "request": "Ist der SAJ GW10K-ETA-G20 auf Lager?",
        "grade": "pass",
        "flags": [],
        "meta": {},
        "blocks": [],
        "duration_s": 1,
        "verdict": "TRIAGE_PASS",
    }
    out = regrade.verdict_of(row)
    assert out["grade"] == "parity"
    assert out["defect"] == "parity"
    assert out["pair"] == "F1"


def test_committed_verdicts_match_the_recount() -> None:
    path = Path(__file__).resolve().parents[2] / "verdicts.jsonl"
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 111
    grades = Counter(str(row["grade"]) for row in rows)
    assert grades["pass"] == 92
    assert grades["defect"] == 15
    assert grades["parity"] == 4
    by_id = {str(row["case"]): row for row in rows}
    for case_id, over in regrade.OVERTURNS.items():
        assert by_id[case_id]["grade"] == over["grade"]
        assert by_id[case_id]["defect"] == over["defect"]
        assert by_id[case_id]["request"]
        assert "stream" not in by_id[case_id]
        assert str(by_id[case_id]["evidence"]).endswith("#" + case_id)
    flagged = {
        case_id for case_id, row in by_id.items() if regrade.flagged_numbers(row)
    }
    assert flagged == set(regrade.NUMBER_CHECKS)
    assert "220/380" in by_id["A4-EN"]["numbers_verification"]["record"]
    assert by_id["A4-EN"]["numbers_verification"].get("pdf_reread") is True
    assert "220/380" in by_id["A4-EN"]["numbers_verification"].get("pdf_line", "")
    assert by_id["H4-DE"]["grade"] == "parity"
    assert by_id["G5-DE"]["grade"] == "parity"


def test_cited_numbers_were_reread_and_the_certificate_fixture_stands_in() -> None:
    cited = regrade.load_cited()
    for case_id, check in regrade.NUMBER_CHECKS.items():
        if check["status"] != "cited-document":
            continue
        assert "not re-read" not in check["method"]
        assert case_id in cited
        assert cited[case_id]["line"]
    missing = Path("/no/such-certificate.pdf")
    line, read_now = regrade.certificate_voltage_line(missing)
    assert read_now is False
    assert line == regrade.vendored_voltage_line()
    assert "220/380" in line and "230/400" in line
    if regrade.CERTIFICATE.is_file():
        live, read_pdf = regrade.certificate_voltage_line()
        assert read_pdf is True
        assert live == regrade.vendored_voltage_line()
