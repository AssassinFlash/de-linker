from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import run_faults
import stack


def test_ask_proxy_has_no_token_parameter() -> None:
    assert "token" not in inspect.signature(run_faults.ask_proxy).parameters


def test_retry_record_is_the_one_shape() -> None:
    ok = run_faults.retry_record({"http": 200, "done": True, "answer_text": "Listed."})
    assert ok == {"ok": True, "http": 200, "answer_text": "Listed."}
    failed = run_faults.retry_record({"http": 502, "done": False, "answer_text": ""})
    assert failed["ok"] is False


def test_only_runs_the_named_case_and_writes_a_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stack, "service_token", lambda: "ab" * 32)
    monkeypatch.setattr(stack, "restore", lambda: None)
    seen: list[str] = []

    def fake_control(
        case_id: str,
        question: str,
        locale: str,
        allow_measurements: bool = False,
    ) -> dict[str, object]:
        seen.append(case_id)
        return {
            "id": case_id,
            "kind": "control",
            "http": 200,
            "done": True,
            "answer_text": "Listed.",
            "question": question,
            "locale": locale,
            "allow_measurements": allow_measurements,
        }

    monkeypatch.setattr(run_faults, "control", fake_control)
    code = run_faults.main([str(tmp_path), "--only", "BASE-EN"])
    assert code == 0
    assert seen == ["BASE-EN"]
    rows = [
        json.loads(line) for line in (tmp_path / "cases.jsonl").read_text().splitlines()
    ]
    assert rows[0]["id"] == "BASE-EN"
    assert rows[0]["verdict"] == "pass"
    assert rows[0]["reasons"] == []
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary == {"pass": 1, "defect": 0, "defects": []}


def test_only_runs_the_new_sse_cuts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stack, "service_token", lambda: "ab" * 32)
    monkeypatch.setattr(stack, "restore", lambda: None)
    monkeypatch.setattr(stack, "clear_upload_limit", lambda: None)
    seen: list[tuple[str, str, bool]] = []

    def fake_sse(
        case_id: str,
        cut: str,
        attachment: dict[str, str] | None = None,
    ) -> dict[str, object]:
        seen.append((case_id, cut, attachment is not None))
        return {
            "id": case_id,
            "kind": "fault",
            "http": 502,
            "done": False,
            "answer_text": "",
            "error_message": "Genie did not answer.",
            "explicit_channel": "customer",
            "question": "q",
        }

    monkeypatch.setattr(run_faults, "sse_case", fake_sse)
    code = run_faults.main(
        [str(tmp_path), "--only", "SSE-PARTIAL,SSE-ATTACHMENT,SSE-READING"]
    )
    assert code == 0
    assert seen == [
        ("SSE-PARTIAL", "partial-block", False),
        ("SSE-ATTACHMENT", "attachment", True),
        ("SSE-READING", "reading", True),
    ]
