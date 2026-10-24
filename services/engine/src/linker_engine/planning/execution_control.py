"""Private operator admission; the transaction fence is shared with enqueue."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from .canonical import Object
from .errors import ServiceDraining, VersionUnavailable
from .execution_identity import storage_binding
from .weather_remote_state import remote_weather_state

if TYPE_CHECKING:
    from .workspace import Workspace


def draining(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT schema_version, draining FROM execution_control WHERE id=1"
    ).fetchone()
    if row is None or row["schema_version"] != 1:
        raise VersionUnavailable("execution admission control is unavailable")
    return bool(row["draining"])


def require_accepting(connection: sqlite3.Connection) -> None:
    if draining(connection):
        raise ServiceDraining("new evaluations are temporarily closed for draining")


class ExecutionControl:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def set_draining(self, value: bool) -> None:
        if type(value) is not bool:
            raise ValueError("drain state must be boolean")
        with self.workspace.database.transaction() as connection:
            draining(connection)
            connection.execute(
                "UPDATE execution_control SET draining=? WHERE id=1", (int(value),)
            )

    def status(self) -> Object:
        with self.workspace.database.read() as connection:
            states = {
                row["state"]: row["count"]
                for row in connection.execute(
                    "SELECT state, COUNT(*) AS count FROM jobs "
                    "WHERE state IN ('queued','running','retry_wait') "
                    "GROUP BY state"
                )
            }
            closed = draining(connection)
            remote = remote_weather_state(connection, self.workspace.blobs)
            return {
                "schema_version": 1,
                "storage_binding": storage_binding(self.workspace.database.path),
                "draining": closed,
                "pending": sum(states.values()),
                "states": states,
                "remote_weather": remote,
                "quiescent": closed and not states and remote["unresolved"] == 0,
            }
