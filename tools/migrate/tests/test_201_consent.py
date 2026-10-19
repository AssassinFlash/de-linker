"""Standalone consent writes keep a backup and fail when the read-back drifts.

The deploy path is configure_consent, which relies on the cutover database
snapshot. This script is the other entry, so --write without --backup-dir
is refused before WordPress is called.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest


def load() -> ModuleType:
    path = Path(__file__).resolve().parent.parent / "201-consent.py"
    spec = importlib.util.spec_from_file_location("consent_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = load()


class Completed:
    def __init__(self, code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = code
        self.stdout = stdout
        self.stderr = stderr


def payload_of(source: str) -> dict[str, object]:
    found: dict[str, object] | None = None
    for match in re.finditer(r"'([A-Za-z0-9+/=]{20,})'", source):
        try:
            parsed = json.loads(base64.b64decode(match.group(1)))
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict) and "plan" in parsed:
            found = parsed
    assert found is not None
    return found


def test_write_without_backup_dir_is_refused() -> None:
    with pytest.raises(SystemExit) as caught:
        script.main(["--wp", "wp", "--write"])
    assert caught.value.code == 2


def test_dry_run_does_not_require_a_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def run(command: list[str], **kwargs: object) -> Completed:
        del kwargs
        calls.append(payload_of(command[-1]))
        return Completed(stdout='{"write": false, "drift": []}\n')

    monkeypatch.setattr(script.subprocess, "run", run)

    assert script.main(["--wp", "wp"]) == 0
    assert calls == [
        {
            "plan": json.loads(script.PLAN.read_text()),
            "write": False,
            "production": False,
        }
    ]


def test_write_backs_up_then_reads_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, object]] = []

    def run(command: list[str], **kwargs: object) -> Completed:
        del kwargs
        payload = payload_of(command[-1])
        calls.append(payload)
        if payload.get("export"):
            body = script.MARKER + json.dumps(
                {"home": "http://127.0.0.1:8910", "privacy": {"en": "old"}}
            )
            return Completed(stdout=body + "\n")
        if payload.get("write") is False:
            return Completed(1, stderr="Consent configuration differs from its plan.\n")
        return Completed(stdout='{"write": true, "drift": ["privacy"]}\n')

    monkeypatch.setattr(script.subprocess, "run", run)

    assert script.main(["--wp", "wp", "--write", "--backup-dir", str(tmp_path)]) == 1
    assert [call.get("export", False) for call in calls] == [True, False, False]
    assert [call["write"] for call in calls] == [False, True, False]
    backups = list(tmp_path.glob("201-consent-backup-*.json"))
    assert len(backups) == 1
    saved = json.loads(backups[0].read_text())
    assert saved["privacy"]["en"] == "old"


def test_a_failed_export_does_not_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []

    def run(command: list[str], **kwargs: object) -> Completed:
        del command, kwargs
        calls.append(True)
        return Completed(1, stderr="CookieYes and WP Consent API must be active.\n")

    monkeypatch.setattr(script.subprocess, "run", run)

    assert script.main(["--wp", "wp", "--write", "--backup-dir", str(tmp_path)]) == 1
    assert calls == [True]
    assert list(tmp_path.glob("201-consent-backup-*.json")) == []
