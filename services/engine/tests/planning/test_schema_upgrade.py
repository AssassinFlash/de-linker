"""Nonempty core-v2 job/child rows migrate atomically; archives stay readable."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from linker_engine.planning import archive
from linker_engine.planning.canonical import digest
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.storage import Database
from linker_engine.planning.workspace import Workspace

LEGACY_JOBS = """
CREATE TABLE jobs_old (
id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
kind TEXT NOT NULL CHECK(kind IN ('evaluate','render_report')),
request_sha256 TEXT NOT NULL,
state TEXT NOT NULL CHECK(state IN ('queued','running','retry_wait','succeeded','failed','cancelled')),
attempt INTEGER NOT NULL DEFAULT 0 CHECK(attempt>=0),
max_attempts INTEGER NOT NULL CHECK(max_attempts>0),
worker TEXT, lease_token TEXT, lease_until REAL, available_at REAL NOT NULL,
error_sha256 TEXT, output_sha256 TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL
)
"""


def legacy(path: Path) -> None:
    # Construct the independent old CHECK contract in this isolated fixture.
    # Disabling FKs is fixture preparation only, never production migration.
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(LEGACY_JOBS)
        connection.execute("INSERT INTO jobs_old SELECT * FROM jobs")
        connection.execute("DROP TABLE jobs")
        connection.execute("ALTER TABLE jobs_old RENAME TO jobs")
        connection.execute(
            "CREATE UNIQUE INDEX evaluate_once ON jobs(run_id) WHERE kind='evaluate'"
        )
        connection.execute(
            "CREATE INDEX jobs_available ON jobs(state,available_at,lease_until)"
        )
        connection.execute("PRAGMA user_version=2")
        connection.commit()
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()


def rows(path: Path) -> dict:
    connection = sqlite3.connect(path)
    try:
        return {
            table: connection.execute(
                "SELECT * FROM " + table + " ORDER BY 1"
            ).fetchall()
            for table in (
                "projects",
                "revisions",
                "runs",
                "jobs",
                "evaluation_routes",
                "idempotency",
            )
        }
    finally:
        connection.close()


def populated(workspace: Workspace, owner: Actor, context: Context) -> None:
    project = workspace.create(owner, "Migration fixture", {}, key="project")
    workspace.evaluate(owner, project.id, 1, context, key="running", max_attempts=2)
    assert Jobs(workspace).claim("old-worker", kinds=("evaluate",), lease_seconds=300)
    workspace.evaluate(owner, project.id, 1, context, key="queued", max_attempts=3)


def test_nonempty_queue_upgrade_keeps_all_rows_leases_routes_and_receipts(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    populated(workspace, owner, context)
    before = rows(workspace.database.path)
    legacy(workspace.database.path)
    reopened = Workspace(workspace.database.path.parent, clock=workspace.clock)
    assert rows(reopened.database.path) == before
    with reopened.database.read() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name='weather_abort_once'"
            ).fetchone()[0]
            == 1
        )
    Workspace(workspace.database.path.parent, clock=workspace.clock)
    assert rows(reopened.database.path) == before


def test_failed_migration_after_parent_drop_rolls_back_original_version_and_rows(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    populated(workspace, owner, context)
    legacy(workspace.database.path)
    before = rows(workspace.database.path)

    class FailedConnection(sqlite3.Connection):
        def execute(self, sql: str, parameters=()):
            if sql == "ALTER TABLE jobs_upgrade RENAME TO jobs":
                raise sqlite3.OperationalError("fixture after parent drop")
            return super().execute(sql, parameters)

    def failing_open(self):
        connection = sqlite3.connect(
            self.path, isolation_level=None, factory=FailedConnection
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    with monkeypatch.context() as patch:
        patch.setattr(Database, "_open_connection", failing_open)
        with pytest.raises(sqlite3.OperationalError):
            Workspace(workspace.database.path.parent)
    assert rows(workspace.database.path) == before
    connection = sqlite3.connect(workspace.database.path)
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
    assert (
        connection.execute(
            "SELECT name FROM sqlite_master WHERE name='jobs_upgrade'"
        ).fetchall()
        == []
    )
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    connection.close()
    Workspace(workspace.database.path.parent, clock=workspace.clock)
    assert rows(workspace.database.path) == before


def test_old_archive_verifies_and_restores_into_migrated_schema(
    workspace: Workspace, owner: Actor, context: Context, tmp_path: Path
) -> None:
    populated(workspace, owner, context)
    snapshot = tmp_path / "archive"
    archive.backup(workspace, snapshot)
    legacy(snapshot / "workspace.sqlite")
    manifest = json.loads((snapshot / "backup.json").read_bytes())
    manifest["database_sha256"] = digest((snapshot / "workspace.sqlite").read_bytes())
    (snapshot / "backup.json").write_text(json.dumps(manifest))
    archive.verify(snapshot)
    before = rows(snapshot / "workspace.sqlite")
    restored = archive.restore(snapshot, tmp_path / "restored")
    assert rows(restored.database.path) == before
    with restored.database.read() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
