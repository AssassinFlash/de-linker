"""Transactional queue-kind migration with exact old rows and child references."""

from __future__ import annotations

import sqlite3

from .errors import VersionUnavailable
from .schema import EVALUATION_ROUTES_TABLE, JOBS_COLUMNS


def upgrade_jobs(connection: sqlite3.Connection, current: int) -> None:
    if current not in (1, 2, 3):
        return
    existing = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='jobs'"
    ).fetchone()
    if existing is None:
        return
    # Preserve the child before replacing its parent. Deferring a parent DROP
    # alone leaves a deferred SQLite violation even if foreign_key_check then
    # sees matching new rows. Keep foreign_keys ON throughout this migration.
    routes = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='evaluation_routes'"
    ).fetchone()
    if routes is not None:
        connection.execute(
            "CREATE TEMP TABLE queue_routes_backup AS SELECT * FROM evaluation_routes"
        )
        connection.execute("DROP TABLE evaluation_routes")
    connection.execute(f"CREATE TABLE jobs_upgrade ({JOBS_COLUMNS})")
    connection.execute("INSERT INTO jobs_upgrade SELECT * FROM jobs")
    connection.execute("DROP TABLE jobs")
    connection.execute("ALTER TABLE jobs_upgrade RENAME TO jobs")
    if routes is not None:
        connection.execute(EVALUATION_ROUTES_TABLE)
        connection.execute(
            "INSERT INTO evaluation_routes SELECT * FROM queue_routes_backup"
        )
        connection.execute("DROP TABLE queue_routes_backup")
    if connection.execute("PRAGMA foreign_key_check").fetchall():
        raise VersionUnavailable("queue migration did not preserve its references")
