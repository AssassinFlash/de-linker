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
    rows = connection.execute(
        "SELECT command_sha256, receipt_sha256 FROM idempotency "
        "WHERE actor=? AND scope=? AND key=?",
        (actor.key, scope, key),
    ).fetchall()
    # Native claim retires the guest, but its immutable command receipts remain
    # the proof of an uncertain request. This is not an ownership grant: every
    # caller still admits the actor and reads the current owned project/resource.
    # Claim-event receipts themselves never inherit another actor's authority.
    if actor.kind == "user" and (
        scope == "create" or scope.startswith(("revise:", "asset:", "evaluate:"))
    ):
        rows.extend(
            connection.execute(
                "SELECT i.command_sha256, i.receipt_sha256 FROM idempotency AS i "
                "JOIN principal_closures AS c ON c.guest=i.actor "
                "WHERE c.new_owner=? AND i.scope=? AND i.key=?",
                (actor.key, scope, key),
            ).fetchall()
        )
    if not rows:
        return None
    if any(row["command_sha256"] != command_sha256 for row in rows):
        raise Conflict("idempotency key already used for a different command")
    receipts = {row["receipt_sha256"] for row in rows}
    if len(receipts) != 1:
        raise Conflict("idempotency key has multiple original receipts")
    return blobs.object(rows[0]["receipt_sha256"])


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
