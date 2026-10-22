"""Bounded project navigation over the same authority, with no input blob load."""

from __future__ import annotations

from .access import positive_integer, project_row
from .canonical import Json, Object
from .errors import InvalidInput
from .http_documents import Cursor
from .records import Actor
from .workspace import Workspace


def project_page(
    workspace: Workspace, actor: Actor, size: int, after: Cursor | None
) -> Object:
    positive_integer(size, "project page size")
    parameters: list[str | float | int] = [actor.key]
    position = ""
    if after is not None:
        position = " AND (p.updated_at < ? OR (p.updated_at = ? AND p.id < ?))"
        parameters.extend((after.updated_at, after.updated_at, after.id))
    parameters.append(size + 1)
    with workspace.database.read() as connection:
        rows = connection.execute(
            "SELECT p.id, p.title, p.revision, p.updated_at, r.input_sha256 "
            "FROM projects p JOIN revisions r ON r.project_id=p.id AND r.number=p.revision "
            "WHERE p.owner=?"
            + position
            + " ORDER BY p.updated_at DESC, p.id DESC LIMIT ?",
            parameters,
        ).fetchall()
    items: list[Json] = [
        {
            "id": row["id"],
            "title": row["title"],
            "revision": row["revision"],
            "input_sha256": row["input_sha256"],
            "updated_at": row["updated_at"],
        }
        for row in rows[:size]
    ]
    last = rows[size - 1] if len(rows) > size else None
    return {
        "items": items,
        "next": None
        if last is None
        else {"updated_at": last["updated_at"], "id": last["id"]},
        "ordering": "updated_at_desc_id_desc; live_navigation_not_a_frozen_search",
    }


def run_page(
    workspace: Workspace,
    actor: Actor,
    project_id: str,
    size: int,
    before_created_at: float | None,
    before_id: str | None,
) -> Object:
    positive_integer(size, "run page size")
    if (before_created_at is None) != (before_id is None):
        raise InvalidInput("complete run cursor required")
    parameters: list[str | float | int] = [project_id]
    position = ""
    if before_created_at is not None:
        position = " AND (r.created_at < ? OR (r.created_at = ? AND r.id < ?))"
        assert before_id is not None
        parameters.extend((before_created_at, before_created_at, before_id))
    parameters.append(size + 1)
    with workspace.database.read() as connection:
        project = project_row(connection, actor, project_id)
        rows = connection.execute(
            "SELECT r.id, r.revision, r.created_at, r.manifest_sha256, r.result_sha256, j.state "
            "FROM runs r JOIN jobs j ON j.run_id=r.id AND j.kind='evaluate' "
            "WHERE r.project_id=?"
            + position
            + " ORDER BY r.created_at DESC, r.id DESC LIMIT ?",
            parameters,
        ).fetchall()
        current_revision = project["revision"]
    items: list[Json] = [
        {
            "id": row["id"],
            "project_id": project_id,
            "revision": row["revision"],
            "state": row["state"],
            "created_at": row["created_at"],
            "manifest_sha256": row["manifest_sha256"],
            "result_sha256": row["result_sha256"],
            "is_current": row["revision"] == current_revision,
        }
        for row in rows[:size]
    ]
    last = rows[size - 1] if len(rows) > size else None
    return {
        "items": items,
        "next": None
        if last is None
        else {"before_created_at": last["created_at"], "before_id": last["id"]},
    }
