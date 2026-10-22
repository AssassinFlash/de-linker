"""Idempotent command receipts, committed with the state they acknowledge."""

from __future__ import annotations

import sqlite3

from .canonical import Object, digest, encode
from .errors import Conflict, InvalidInput, VersionUnavailable
from .records import Actor
from .storage import Blobs


def command_hash(command: Object, key: str) -> str:
    if not key.strip():
        raise InvalidInput("idempotency key required")
    return digest(encode(command))


def replay(
    connection: sqlite3.Connection,
    blobs: Blobs,
    actor: Actor,
    scope: str,
    key: str,
    command_sha256: str,
) -> Object | None:
    row = connection.execute(
        "SELECT command_sha256, receipt_sha256 FROM idempotency "
        "WHERE actor=? AND scope=? AND key=?",
        (actor.key, scope, key),
    ).fetchone()
    if row is None:
        return None
    if row["command_sha256"] != command_sha256:
        raise Conflict("idempotency key already used for a different command")
    return blobs.object(row["receipt_sha256"])


def remember(
    connection: sqlite3.Connection,
    blobs: Blobs,
    actor: Actor,
    scope: str,
    key: str,
    command_sha256: str,
    receipt: Object,
    now: float,
) -> None:
    connection.execute(
        "INSERT INTO idempotency "
        "(actor, scope, key, command_sha256, receipt_sha256, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (actor.key, scope, key, command_sha256, blobs.put_object(receipt), now),
    )


def receipt_string(receipt: Object, key: str) -> str:
    value = receipt.get(key)
    if not isinstance(value, str):
        raise VersionUnavailable("invalid command receipt")
    return value


def receipt_number(receipt: Object, key: str) -> int:
    value = receipt.get(key)
    if type(value) is not int:
        raise VersionUnavailable("invalid command receipt")
    return value
