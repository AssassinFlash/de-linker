"""Local contract tests for the guarded #548 installation-facts migration."""

from __future__ import annotations

import importlib.util
import json
import stat
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

HERE = Path(__file__).resolve().parent


def load_script() -> ModuleType:
    """Load the ticket-named migration as the CLI itself does."""
    spec = importlib.util.spec_from_file_location(
        "installation_facts_migration", HERE.parent / "548-installation-facts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = load_script()


def plan() -> dict[str, object]:
    return {
        "schema_version": 1,
        "products": {
            "6506": {
                "model": "GW75K-ET-G10",
                "product_revision": "a" * 64,
                "items": [{"id": "synthetic-installation-fact"}],
            }
        },
    }


def receipt() -> dict[str, object]:
    after = {"schema_version": 1, "items": [{"id": "synthetic-installation-fact"}]}
    return {
        "schema_version": 1,
        "site": "https://de-linker.test",
        "source_revision": "b" * 64,
        "changes": 1,
        "products": {
            "6506": {
                "model": "GW75K-ET-G10",
                "product_revision": "a" * 64,
                "before_exists": False,
                "before": None,
                "after": after,
                "after_hash": "c" * 64,
                "protected": "d" * 64,
                "documents": {},
                "product_documents": {},
                "sources": [],
            }
        },
    }


def test_temporary_minimal_plan_contract(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan()))

    loaded = migration.load_plan(path)

    assert loaded == plan()
    assert migration.build_request("preview", plan=loaded) == {
        "action": "preview",
        "plan": plan(),
    }


def test_plan_rejects_extra_fields_and_empty_products(tmp_path: Path) -> None:
    changed = plan()
    changed["purpose"] = "not part of the transport contract"
    path = tmp_path / "extra.json"
    path.write_text(json.dumps(changed))
    with pytest.raises(migration.MigrationError, match="only schema_version"):
        migration.load_plan(path)

    path.write_text(json.dumps({"schema_version": 1, "products": {}}))
    with pytest.raises(migration.MigrationError, match="no products"):
        migration.load_plan(path)


def test_receipt_is_exclusive_and_private(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    migration.write_receipt(path, receipt())

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert migration.load_receipt(path) == receipt()
    with pytest.raises(FileExistsError):
        migration.write_receipt(path, receipt())


def test_receipt_rejects_group_access(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    migration.write_receipt(path, receipt())
    path.chmod(0o640)

    with pytest.raises(migration.MigrationError, match="0600"):
        migration.load_receipt(path)


def test_stable_marker_is_unique() -> None:
    output = "noise\n" + migration.MARKER + json.dumps({"status": "ok"}) + "\n"

    assert migration.parse_marker(output) == {"status": "ok"}
    with pytest.raises(migration.MigrationError, match="found 2"):
        migration.parse_marker(output + output)


def test_invoke_keeps_verify_result_from_nonzero_php(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def run(
        command: list[str], *, input: str, capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        observed.update(
            command=command,
            input=input,
            capture_output=capture_output,
            text=text,
            check=check,
        )
        output = migration.MARKER + json.dumps(
            {**receipt(), "products": [{"status": "failed"}]}
        )
        return subprocess.CompletedProcess(command, 1, output, "verification failed")

    monkeypatch.setattr(migration.subprocess, "run", run)
    site = migration.Target(
        label="local:fixture",
        root="/tmp/fixture",
        base_url="http://fixture.invalid",
        prefix=("wp",),
        shell_prefix=None,
        rsync_remote=None,
    )

    code, error, result = migration.invoke(
        site, migration.build_request("verify", receipt=receipt())
    )

    assert code == 1
    assert error == "verification failed"
    assert result is not None and result["products"] == [{"status": "failed"}]
    assert observed["check"] is False
    assert "eval-file" in str(observed["command"])
    assert str(observed["input"]).startswith("<?php")
