"""Ownership is checked for reads, history, bytes and commands alike."""

from __future__ import annotations

import sqlite3
from typing import cast

from .errors import InvalidInput, NotFound
from .records import Actor


def active_actor(connection: sqlite3.Connection, actor: Actor) -> None:
    if (
        actor.kind == "guest"
        and connection.execute(
            "SELECT 1 FROM principal_closures WHERE guest=?", (actor.key,)
        ).fetchone()
    ):
        raise NotFound("project not found")


def project_row(
    connection: sqlite3.Connection,
    actor: Actor,
    project_id: str,
    *,
    write: bool = False,
) -> sqlite3.Row:
    active_actor(connection, actor)
    if write and actor.kind == "team":
        raise NotFound("project not found")
    row = connection.execute(
        "SELECT * FROM projects WHERE id=?", (project_id,)
    ).fetchone()
    team_read = actor.kind == "team" and not write
    if row is None or (row["owner"] != actor.key and not team_read):
        raise NotFound("project not found")
    return cast(sqlite3.Row, row)


def positive_integer(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise InvalidInput(f"{name} must be a positive integer")
