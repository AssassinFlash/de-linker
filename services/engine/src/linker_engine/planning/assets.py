"""Owned, immutable assets whose source permits permanent private retention.

Temporary provider content needs its own expiring cache/backup policy. It is
deliberately not accepted into this permanent CAS. This class is a trusted
server interface; an HTTP upload must not choose arbitrary provider rights.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from uuid import uuid4

from . import commands
from .access import project_row
from .canonical import Object, digest
from .dependencies import verify_dependencies
from .errors import InvalidInput, NotFound
from .records import Actor
from .workspace import Workspace


@dataclass(frozen=True)
class Asset:
    id: str
    project_id: str
    content_sha256: str
    media_type: str
    purpose: str
    metadata_sha256: str
    metadata: Object


class Assets:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def _record(self, row: sqlite3.Row) -> Asset:
        return Asset(
            row["id"],
            row["project_id"],
            row["content_sha256"],
            row["media_type"],
            row["purpose"],
            row["metadata_sha256"],
            self.workspace.blobs.object(row["metadata_sha256"]),
        )

    def get(self, actor: Actor, project_id: str, asset_id: str) -> Asset:
        with self.workspace.database.read() as connection:
            project_row(connection, actor, project_id)
            row = connection.execute(
                "SELECT * FROM project_assets WHERE project_id=? AND id=?",
                (project_id, asset_id),
            ).fetchone()
            if row is None:
                raise NotFound("asset not found")
            return self._record(row)

    def content(self, actor: Actor, project_id: str, asset_id: str) -> bytes:
        asset = self.get(actor, project_id, asset_id)
        return self.workspace.blobs.read(asset.content_sha256)

    def check_write(self, actor: Actor, project_id: str) -> None:
        with self.workspace.database.read() as connection:
            project_row(connection, actor, project_id, write=True)

    def receipt(
        self, actor: Actor, project_id: str, key: str, command: Object
    ) -> Asset | None:
        """Trusted intake may look up a retry before recapturing host TZif data."""
        command_sha256 = commands.command_hash(command, key)
        with self.workspace.database.read() as connection:
            project_row(connection, actor, project_id, write=True)
            receipt = commands.replay(
                connection,
                self.workspace.blobs,
                actor,
                f"asset:{project_id}",
                key,
                command_sha256,
            )
            if receipt is None:
                return None
            row = connection.execute(
                "SELECT * FROM project_assets WHERE project_id=? AND id=?",
                (project_id, commands.receipt_string(receipt, "asset_id")),
            ).fetchone()
            if row is None:
                raise NotFound("asset not found")
            asset = self._record(row)
            self.workspace.blobs.read(asset.content_sha256)
            verify_dependencies(self.workspace.blobs, asset.metadata)
            return asset

    def add(
        self,
        actor: Actor,
        project_id: str,
        content: bytes,
        media_type: str,
        purpose: str,
        metadata: Object,
        *,
        key: str,
        logical_metadata: Object | None = None,
    ) -> Asset:
        if not content or not media_type.strip() or not purpose.strip():
            raise InvalidInput("nonempty asset, media type and purpose required")
        if metadata.get("retention") != "permanent":
            raise InvalidInput("this source needs a compliant temporary asset store")
        provenance = metadata.get("provenance")
        if not isinstance(provenance, dict) or any(
            not isinstance(provenance.get(name), str)
            or not str(provenance[name]).strip()
            for name in ("label", "basis", "rights_basis")
        ):
            raise InvalidInput("source label, fact basis and retention rights required")
        content_sha256 = digest(content)
        command = commands.command_hash(
            {
                "content_sha256": content_sha256,
                "media_type": media_type,
                "purpose": purpose,
                # Only a trusted intake adapter supplies logical_metadata:
                # server-captured dependencies belong to the first receipt,
                # not to a new user command on a retry after an OS update.
                "metadata": metadata if logical_metadata is None else logical_metadata,
            },
            key,
        )
        # Reject foreign writers before publishing even unreferenced bytes.
        self.check_write(actor, project_id)
        verify_dependencies(self.workspace.blobs, metadata)
        self.workspace.blobs.put(content)
        metadata_sha256 = self.workspace.blobs.put_object(metadata)
        scope = f"asset:{project_id}"
        with self.workspace.database.transaction() as connection:
            project_row(connection, actor, project_id, write=True)
            receipt = commands.replay(
                connection, self.workspace.blobs, actor, scope, key, command
            )
            if receipt is not None:
                asset_id = commands.receipt_string(receipt, "asset_id")
            else:
                asset_id = uuid4().hex
                now = self.workspace.clock()
                connection.execute(
                    "INSERT INTO project_assets "
                    "(id, project_id, content_sha256, media_type, purpose, "
                    "metadata_sha256, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        asset_id,
                        project_id,
                        content_sha256,
                        media_type,
                        purpose,
                        metadata_sha256,
                        now,
                    ),
                )
                commands.remember(
                    connection,
                    self.workspace.blobs,
                    actor,
                    scope,
                    key,
                    command,
                    {"asset_id": asset_id},
                    now,
                )
            row = connection.execute(
                "SELECT * FROM project_assets WHERE project_id=? AND id=?",
                (project_id, asset_id),
            ).fetchone()
            if row is None:
                raise NotFound("asset not found")
            return self._record(row)
