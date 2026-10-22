"""Safety regressions for the actual MFA runner and PHP fixture, fully offline."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from linker_local.cli import require_php

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "admin_mfa_safety", REPO / "tools/checks/admin-mfa.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("prepare", [False, True])
@pytest.mark.parametrize("failure", [None, "version", "inactive", "checksum"])
def test_every_entry_path_verifies_dependency_before_fixture_writes(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    prepare: bool,
    failure: str | None,
) -> None:
    events: list[str] = []

    class Wp:
        def __init__(self, *_: object) -> None:
            self.instance = SimpleNamespace(url="http://127.0.0.1:9332")

        def run(self, *args: str) -> str:
            if args[0] == "eval":
                return "true"
            if args[:2] == ("plugin", "get"):
                events.append("metadata")
                return json.dumps(
                    {
                        "version": "0.16.0" if failure == "version" else "0.17.0",
                        "status": "inactive" if failure == "inactive" else "active",
                    }
                )
            if args[:2] == ("plugin", "verify-checksums"):
                events.append("strict-checksum")
                assert args == ("plugin", "verify-checksums", "two-factor", "--strict")
                if failure == "checksum":
                    raise RuntimeError("Injected official checksum failure")
                return "Success: Verified 1 of 1 plugins."
            raise AssertionError(args)

    class Registry:
        def __init__(self, *_: object) -> None:
            pass

        def get(self, _: str) -> object:
            return object()

    def preparation(_: Any) -> dict[str, str]:
        events.append("prepare")
        return {"archive_sha256": "offline"}

    def write_fixture(_: Any) -> None:
        events.append("fixture-write")
        (tmp_path / "fixture-written").write_text("owned")

    monkeypatch.setattr(runner, "WpCli", Wp)
    monkeypatch.setattr(runner, "Registry", Registry)
    monkeypatch.setattr(runner, "require_php", lambda: Path("unused"))
    monkeypatch.setattr(runner, "prepare", preparation)
    monkeypatch.setattr(runner.Acceptance, "run", write_fixture)
    evidence = tmp_path / "report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["admin-mfa", "offline", "--evidence", str(evidence)]
        + (["--prepare"] if prepare else []),
    )
    assert runner.main() == (0 if failure is None else 1)
    report = json.loads(evidence.read_text())
    assert (tmp_path / "fixture-written").exists() is (failure is None)
    assert ("prepare" in events) is prepare
    if failure is None:
        assert events[-3:] == ["metadata", "strict-checksum", "fixture-write"]
        assert report["dependency"]["version"] == "0.17.0"
        assert report["dependency"]["status"] == "active"
    else:
        assert "fixture-write" not in events


def test_partial_php_setup_failure_finally_cleans_only_owned_objects(
    tmp_path: Path,
) -> None:
    includes = tmp_path / "wp-admin/includes"
    includes.mkdir(parents=True)
    (includes / "user.php").write_text("<?php // Offline include only.\n")
    result = subprocess.run(
        [
            str(require_php()),
            str(Path(__file__).parent / "fixtures/admin_mfa_failures.php"),
            str(REPO / "tests/e2e/fixtures/admin-mfa.php"),
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    cases = json.loads(result.stdout)
    assert len(cases) == 10
    assert all(case["passed"] and case["preexisting_preserved"] for case in cases)
    assert sum(case["baseline_restored"] for case in cases) == 9
    assert cases[-1]["manual_cleanup_required_reported"] is True
