"""Real executable inspection must never migrate the referenced old database."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from linker_engine.planning.runtime_snapshot import RuntimeSnapshot
from linker_engine.planning.schema import SCHEMA_VERSION


def test_real_release_command_needs_no_policy_secrets_or_workspace(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "protected"
    directory.mkdir()
    database = directory / "workspace.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE projects(id TEXT)")
        connection.execute("INSERT INTO projects VALUES ('retained')")
        connection.execute("PRAGMA user_version=2")
    policy = tmp_path / "invalid-policy.json"
    policy.write_text(json.dumps({"directory": str(directory)}))
    before = database.read_bytes()
    expected = RuntimeSnapshot.capture().sha256
    for selected in (policy, tmp_path / "absent-policy.json"):
        result = subprocess.run(
            [sys.executable, "-m", "linker_engine.planning.worker_host", "release"],
            env={
                "PATH": os.environ.get("PATH", os.defpath),
                "PYTHONDONTWRITEBYTECODE": "1",
                "LINKER_PLANNER_CONFIG": str(selected),
            },
            capture_output=True,
            text=True,
            check=True,
            timeout=15,  # Isolated CLI deadline, not a physical-model tolerance.
        )
        assert json.loads(result.stdout) == {
            "schema_version": 1,
            "runtime_sha256": expected,
            "storage_schema_version": SCHEMA_VERSION,
        }
        assert result.stderr == ""
        assert database.read_bytes() == before
        assert sorted(path.name for path in directory.iterdir()) == ["workspace.sqlite"]
    assert not (tmp_path / "absent-policy.json").exists()
