"""Rebuildable execution routing; immutable run/request bytes remain authority."""

from __future__ import annotations

from .canonical import Object
from .errors import InvalidInput, VersionUnavailable
from .execution_identity import request_execution_key
from .workspace import Workspace


class EvaluationRoutes:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self._cursor: tuple[float, float, str] | None = None

    def request_key(self, request: Object, manifest_sha256: str) -> str:
        manifest = self.workspace.blobs.object(manifest_sha256)
        return request_execution_key(request, manifest, manifest_sha256)

    def index_pending(self, batch_size: int) -> None:
        workspace = self.workspace
        with workspace.database.read() as connection:
            query = (
                "SELECT jobs.id, jobs.request_sha256, jobs.available_at, "
                "jobs.created_at, runs.manifest_sha256 "
                "FROM jobs JOIN runs ON runs.id=jobs.run_id "
                "WHERE jobs.kind='evaluate' "
                "AND (jobs.state IN ('queued','retry_wait') "
                "OR (jobs.state='running' AND jobs.lease_until<=?)) "
            )
            order = "ORDER BY jobs.available_at, jobs.created_at, jobs.id LIMIT ?"
            rows = connection.execute(
                query
                + (
                    "AND (jobs.available_at,jobs.created_at,jobs.id)>(?,?,?) "
                    if self._cursor is not None
                    else ""
                )
                + order,
                (workspace.clock(), *(self._cursor or ()), batch_size),
            ).fetchall()
            if not rows and self._cursor is not None:
                # Rotate through all pending rows, including present cache
                # entries: a nonexistent cached key cannot strand valid work.
                self._cursor = None
                rows = connection.execute(
                    query + order, (workspace.clock(), batch_size)
                ).fetchall()
        for row in rows:
            self._cursor = (row["available_at"], row["created_at"], row["id"])
            key: str | None = None
            failure: str | None = None
            # Hash verification and immutable-manifest reads are outside the
            # write transaction. Missing and present routes have the same
            # authority: only these verified immutable bytes determine routing.
            try:
                request = workspace.blobs.object(row["request_sha256"])
                key = self.request_key(request, row["manifest_sha256"])
            except (VersionUnavailable, InvalidInput):
                failure = workspace.blobs.put_object(
                    {
                        "code": "version_unavailable",
                        "retryable": False,
                    }
                )
            with workspace.database.transaction() as connection:
                current = connection.execute(
                    "SELECT request_sha256 FROM jobs WHERE id=? "
                    "AND (state IN ('queued','retry_wait') "
                    "OR (state='running' AND lease_until<=?))",
                    (row["id"], workspace.clock()),
                ).fetchone()
                if (
                    current is None
                    or current["request_sha256"] != row["request_sha256"]
                ):
                    continue
                if failure is not None:
                    connection.execute(
                        "UPDATE jobs SET state='failed', error_sha256=?, updated_at=? "
                        "WHERE id=?",
                        (failure, workspace.clock(), row["id"]),
                    )
                elif key is not None:
                    connection.execute(
                        "INSERT INTO evaluation_routes "
                        "(job_id, schema_version, execution_sha256) VALUES (?,1,?) "
                        "ON CONFLICT(job_id) DO UPDATE SET schema_version=1, "
                        "execution_sha256=excluded.execution_sha256",
                        (row["id"], key),
                    )
