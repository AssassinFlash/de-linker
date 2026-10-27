"""A prepared owned asset, published only with its successful durable task."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from uuid import uuid4

from .asset_validation import validate_asset
from .canonical import Object
from .dependencies import verify_dependencies
from .errors import Conflict, InvalidInput, VersionUnavailable
from .storage import Blobs


@dataclass(frozen=True)
class AssetPublication:
    id: str
    project_id: str
    content_sha256: str
    media_type: str
    purpose: str
    metadata_sha256: str

    @classmethod
    def prepare(
        cls,
        blobs: Blobs,
        project_id: str,
        content: bytes,
        media_type: str,
        purpose: str,
        metadata: Object,
    ) -> AssetPublication:
        validate_asset(content, media_type, purpose, metadata)
        verify_dependencies(blobs, metadata)
        return cls(
            uuid4().hex,
            project_id,
            blobs.put(content),
            media_type,
            purpose,
            blobs.put_object(metadata),
        )

    def document(self, blobs: Blobs) -> Object:
        metadata = blobs.object(self.metadata_sha256)
        validate_asset(
            blobs.read(self.content_sha256), self.media_type, self.purpose, metadata
        )
        verify_dependencies(blobs, metadata)
        return {
            "id": self.id,
            "project_id": self.project_id,
            "content_sha256": self.content_sha256,
            "media_type": self.media_type,
            "purpose": self.purpose,
            "metadata_sha256": self.metadata_sha256,
            "metadata": metadata,
        }

    def _exists(self, connection: sqlite3.Connection) -> bool:
        existing = connection.execute(
            "SELECT * FROM project_assets WHERE id=?", (self.id,)
        ).fetchone()
        fields = (
            self.project_id,
            self.content_sha256,
            self.media_type,
            self.purpose,
            self.metadata_sha256,
        )
        if existing is not None:
            if (
                tuple(
                    existing[name]
                    for name in (
                        "project_id",
                        "content_sha256",
                        "media_type",
                        "purpose",
                        "metadata_sha256",
                    )
                )
                != fields
            ):
                raise Conflict("prepared asset ID already has different content")
            return True
        return False

    def verify_published(self, connection: sqlite3.Connection) -> None:
        if not self._exists(connection):
            raise VersionUnavailable("completed task's prepared asset is unavailable")

    def publish(self, connection: sqlite3.Connection, run_id: str, now: float) -> None:
        row = connection.execute(
            "SELECT project_id FROM runs WHERE id=?", (run_id,)
        ).fetchone()
        if row is None or row["project_id"] != self.project_id:
            raise InvalidInput("prepared asset does not belong to the task's project")
        if self._exists(connection):
            return
        connection.execute(
            "INSERT INTO project_assets (id, project_id, content_sha256, media_type, purpose, metadata_sha256, created_at) VALUES (?,?,?,?,?,?,?)",
            (
                self.id,
                self.project_id,
                self.content_sha256,
                self.media_type,
                self.purpose,
                self.metadata_sha256,
                now,
            ),
        )


@dataclass(frozen=True)
class AssetResult:
    result: Object
    asset: AssetPublication
    attachments: dict[str, AssetPublication] = field(default_factory=dict)
