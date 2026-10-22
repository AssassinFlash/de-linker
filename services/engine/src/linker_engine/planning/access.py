"""Ownership is checked for reads, history, bytes and commands alike."""

from __future__ import annotations

import sqlite3
from typing import cast

from .errors import InvalidInput, NotFound
from .records import Actor


def project_row(
    connection: sqlite3.Connection, actor: Actor, project_id: str
) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM projects WHERE id=?", (project_id,)
    ).fetchone()
    if row is None or (row["owner"] != actor.key and actor.kind != "team"):
        raise NotFound("project not found")
    return cast(sqlite3.Row, row)


def positive_integer(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise InvalidInput(f"{name} must be a positive integer")
