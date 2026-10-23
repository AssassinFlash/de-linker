"""Durable, leased work with atomic publication and stale-worker fencing.

Durations and retry counts are explicit operator policy, never hidden engine
defaults. A task completing is only a persistence state; engineering feasibility
and evidence remain part of its frozen result.
"""

from __future__ import annotations

import math
import sqlite3
from typing import cast
from uuid import uuid4

from .canonical import Object
from .dependencies import verify_dependencies
from .errors import Conflict, InvalidInput, LeaseLost, VersionUnavailable
from .evaluation_routes import EvaluationRoutes
from .execution_identity import EvaluationRouting
from .records import JobKind, Lease
from .workspace import Workspace


def _duration(value: float, name: str, *, zero: bool = False) -> None:
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or value < 0
        or (not zero and value == 0)
    ):
        raise InvalidInput(
            f"{name} must be finite and {'nonnegative' if zero else 'positive'}"
        )


class Jobs:
    """Private worker operations; never exposed as browser-selected identities."""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self._routes = EvaluationRoutes(workspace)

    def claim(
        self,
        worker: str,
        *,
        kinds: tuple[JobKind, ...],
        lease_seconds: float,
        routing: EvaluationRouting | None = None,
    ) -> Lease | None:
        if (
            not worker.strip()
            or not kinds
            or any(kind not in ("evaluate", "render_report") for kind in kinds)
        ):
            raise InvalidInput("worker and supported job kinds required")
        _duration(lease_seconds, "lease duration")
        workspace = self.workspace
        routes = self._routes if routing is not None else None
        if routes is not None:
            if kinds != ("evaluate",):
                raise InvalidInput("execution routing currently covers evaluation only")
            assert routing is not None
            routes.index_pending(routing.batch_size)
        with workspace.database.transaction() as connection:
            now = workspace.clock()
            # Only the placeholder count is interpolated; values are bound.
            placeholders = ",".join("?" for _ in kinds)
            while True:
                routing_join = (
                    "JOIN evaluation_routes ON evaluation_routes.job_id=jobs.id "
                    "AND evaluation_routes.schema_version=1 "
                    "AND evaluation_routes.execution_sha256=? "
                    if routing is not None
                    else ""
                )
                row = connection.execute(
                    "SELECT jobs.*, runs.manifest_sha256 AS run_manifest "
                    "FROM jobs JOIN runs ON runs.id=jobs.run_id "
                    + routing_join
                    + f"WHERE jobs.kind IN ({placeholders}) AND "
                    "((jobs.state IN ('queued', 'retry_wait') AND jobs.available_at<=?) "
                    "OR (jobs.state='running' AND jobs.lease_until<=?)) "
                    "ORDER BY jobs.available_at, jobs.created_at, jobs.id LIMIT 1",
                    (
                        *((routing.key,) if routing is not None else ()),
                        *kinds,
                        now,
                        now,
                    ),
                ).fetchone()
                if row is None:
                    return None
                if row["attempt"] >= row["max_attempts"]:
                    error = workspace.blobs.put_object(
                        {"code": "attempts_exhausted", "retryable": False}
                    )
                    connection.execute(
                        "UPDATE jobs SET state='failed', error_sha256=?, updated_at=? "
                        "WHERE id=?",
                        (error, now, row["id"]),
                    )
                    continue
                try:
                    request = workspace.blobs.object(row["request_sha256"])
                    if routes is not None and routing is not None:
                        actual = routes.request_key(request, row["run_manifest"])
                        if actual != routing.key:
                            # A derived cache cannot make this executable own
                            # another runtime's job or spend one of its attempts.
                            connection.execute(
                                "UPDATE evaluation_routes SET execution_sha256=? "
                                "WHERE job_id=?",
                                (actual, row["id"]),
                            )
                            continue
                except (VersionUnavailable, InvalidInput):
                    error = workspace.blobs.put_object(
                        {"code": "version_unavailable", "retryable": False}
                    )
                    connection.execute(
                        "UPDATE jobs SET state='failed', error_sha256=?, updated_at=? "
                        "WHERE id=?",
                        (error, now, row["id"]),
                    )
                    continue
                token = uuid4().hex
                attempt = row["attempt"] + 1
                until = now + lease_seconds
                connection.execute(
                    "UPDATE jobs SET state='running', attempt=?, worker=?, "
                    "lease_token=?, lease_until=?, updated_at=? WHERE id=?",
                    (attempt, worker, token, until, now, row["id"]),
                )
                return Lease(
                    id=row["id"],
                    run_id=row["run_id"],
                    kind=cast(JobKind, row["kind"]),
                    attempt=attempt,
                    worker=worker,
                    token=token,
                    until=until,
                    request=request,
                )

    @staticmethod
    def _identity(row: sqlite3.Row | None, lease: Lease) -> bool:
        return row is not None and (
            row["run_id"],
            row["kind"],
            row["attempt"],
            row["worker"],
            row["lease_token"],
        ) == (lease.run_id, lease.kind, lease.attempt, lease.worker, lease.token)

    def _active(
        self, connection: sqlite3.Connection, lease: Lease, now: float
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM jobs WHERE id=?", (lease.id,)
        ).fetchone()
        if (
            not self._identity(row, lease)
            or row is None
            or row["state"] != "running"
            or row["lease_until"] <= now
        ):
            raise LeaseLost("worker lease is no longer current")
        return cast(sqlite3.Row, row)

    def heartbeat(self, lease: Lease, *, lease_seconds: float) -> float:
        _duration(lease_seconds, "lease duration")
        with self.workspace.database.transaction() as connection:
            now = self.workspace.clock()
            self._active(connection, lease, now)
            until = now + lease_seconds
            connection.execute(
                "UPDATE jobs SET lease_until=?, updated_at=? WHERE id=?",
                (until, now, lease.id),
            )
            return until

    def complete(self, lease: Lease, result: Object) -> str:
        """Publish bytes and success together; late or cancelled attempts lose."""
        workspace = self.workspace
        verify_dependencies(workspace.blobs, result)
        output = workspace.blobs.put_object(result)
        with workspace.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id=?", (lease.id,)
            ).fetchone()
            # Repeating an acknowledged completion returns the same bytes. A
            # different generation, even with equal output, never owns it.
            if (
                self._identity(row, lease)
                and row is not None
                and row["state"] == "succeeded"
            ):
                if row["output_sha256"] != output:
                    raise Conflict("completed attempt has a different result")
                return output
            now = workspace.clock()
            self._active(connection, lease, now)
            if lease.kind == "evaluate":
                changed = connection.execute(
                    "UPDATE runs SET result_sha256=? "
                    "WHERE id=? AND result_sha256 IS NULL",
                    (output, lease.run_id),
                ).rowcount
                if changed != 1:
                    raise Conflict("run already has a frozen result")
            connection.execute(
                "UPDATE jobs SET state='succeeded', output_sha256=?, "
                "error_sha256=NULL, updated_at=? WHERE id=?",
                (output, now, lease.id),
            )
        return output

    def fail(self, lease: Lease, error: Object, *, retry_after: float | None) -> None:
        """Persist a typed error; only explicitly retryable attempts re-enter."""
        code = error.get("code")
        if not isinstance(code, str) or not code.strip():
            raise InvalidInput("named failure code required")
        if retry_after is not None:
            _duration(retry_after, "retry delay", zero=True)
        workspace = self.workspace
        content = workspace.blobs.put_object(error)
        with workspace.database.transaction() as connection:
            now = workspace.clock()
            row = self._active(connection, lease, now)
            retry = retry_after is not None and row["attempt"] < row["max_attempts"]
            available = now + retry_after if retry and retry_after is not None else now
            connection.execute(
                "UPDATE jobs SET state=?, error_sha256=?, available_at=?, updated_at=? "
                "WHERE id=?",
                (
                    "retry_wait" if retry else "failed",
                    content,
                    available,
                    now,
                    lease.id,
                ),
            )
