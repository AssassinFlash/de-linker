"""Atomic login ownership transfer and retirement of a verified guest session.

The trusted WP adapter must prove both subjects. Retiring the whole guest
closes the race where an already-admitted request creates a project after the
login transfer. No cookie, browser body or project ID establishes this proof.
"""

from __future__ import annotations

from . import commands
from .canonical import Object
from .errors import Conflict, InvalidInput
from .records import Actor
from .workspace import Workspace


class GuestClaims:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def claim(self, guest: Actor, user: Actor, *, key: str) -> Object:
        if guest.kind != "guest" or user.kind != "user":
            raise InvalidInput("verified guest and account required")
        command = commands.command_hash({"guest": guest.key, "user": user.key}, key)
        scope = f"claim-session:{guest.key}"
        with self.workspace.database.transaction() as connection:
            receipt = commands.replay(
                connection, self.workspace.blobs, user, scope, key, command
            )
            if receipt is not None:
                return receipt
            closed = connection.execute(
                "SELECT new_owner, receipt_sha256 FROM principal_closures WHERE guest=?",
                (guest.key,),
            ).fetchone()
            if closed is not None:
                if closed["new_owner"] != user.key:
                    raise Conflict("guest session already claimed")
                receipt = self.workspace.blobs.object(closed["receipt_sha256"])
            else:
                now = self.workspace.clock()
                connection.execute(
                    "INSERT INTO ownership_transfers "
                    "(project_id, previous_owner, new_owner, created_at) "
                    "SELECT id, owner, ?, ? FROM projects WHERE owner=?",
                    (user.key, now, guest.key),
                )
                changed = connection.execute(
                    "UPDATE projects SET owner=?, updated_at=? WHERE owner=?",
                    (user.key, now, guest.key),
                ).rowcount
                receipt = {
                    "schema_version": 1,
                    "status": "claimed",
                    "transferred_count": changed,
                    "guest_retired": True,
                }
                receipt_sha256 = self.workspace.blobs.put_object(receipt)
                connection.execute(
                    "INSERT INTO principal_closures "
                    "(guest, new_owner, receipt_sha256, created_at) VALUES (?, ?, ?, ?)",
                    (guest.key, user.key, receipt_sha256, now),
                )
            commands.remember(
                connection,
                self.workspace.blobs,
                user,
                scope,
                key,
                command,
                receipt,
                self.workspace.clock(),
            )
            return receipt
