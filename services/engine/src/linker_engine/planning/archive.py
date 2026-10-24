"""Whole-workspace online snapshots, independently verifiable before restore.

SQLite's backup API captures the database, including committed WAL content.
Only then are immutable blobs copied. Blob deletion/GC is deliberately absent:
writers may add bytes during a backup, but cannot remove its frozen references.
Unreferenced published bytes can be included safely. No live .sqlite file copy.
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

from .canonical import Object, decode_object, digest, encode
from .dependencies import verify_dependencies
from .errors import Conflict, InvalidInput, VersionUnavailable
from .schema import READABLE_SCHEMA_VERSIONS
from .storage import Blobs
from .workspace import Workspace


def _check_database(path: Path, blobs: Blobs) -> None:
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in READABLE_SCHEMA_VERSIONS:
            raise VersionUnavailable("unsupported archive schema")
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise VersionUnavailable("archive database integrity check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise VersionUnavailable("archive references are inconsistent")
        # All database-level byte references, including receipts/error records.
        references = connection.execute(
            "SELECT input_sha256 FROM revisions "
            "UNION SELECT manifest_sha256 FROM runs "
            "UNION SELECT result_sha256 FROM runs WHERE result_sha256 IS NOT NULL "
            "UNION SELECT request_sha256 FROM jobs "
            "UNION SELECT error_sha256 FROM jobs WHERE error_sha256 IS NOT NULL "
            "UNION SELECT output_sha256 FROM jobs WHERE output_sha256 IS NOT NULL "
            "UNION SELECT receipt_sha256 FROM idempotency "
            "UNION SELECT content_sha256 FROM project_assets "
            "UNION SELECT metadata_sha256 FROM project_assets "
            "UNION SELECT content_sha256 FROM artifacts "
            "UNION SELECT branding_sha256 FROM artifacts WHERE branding_sha256 IS NOT NULL "
            "UNION SELECT snapshot_sha256 FROM handoffs"
            + (
                " UNION SELECT receipt_sha256 FROM principal_closures"
                if version >= 2
                else ""
            )
        ).fetchall()
        for (sha256,) in references:
            blobs.read(sha256)
        documents = connection.execute(
            "SELECT metadata_sha256 FROM project_assets "
            "UNION SELECT result_sha256 FROM runs WHERE result_sha256 IS NOT NULL "
            "UNION SELECT output_sha256 FROM jobs WHERE output_sha256 IS NOT NULL"
        ).fetchall()
        for (sha256,) in documents:
            verify_dependencies(blobs, blobs.object(sha256))
        # This additive table is absent in older core-v2 archives. Its exact
        # source/progress refs and flattened capture children are authoritative
        # recovery data, including when a start response was lost.
        has_weather_journal = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='weather_acquisitions'"
        ).fetchone()
        if has_weather_journal:
            columns = (
                "manifest_sha256",
                "plan_sha256",
                "acknowledgement_sha256",
                "observation_sha256",
                "capture_sha256",
                "abort_sha256",
            )
            for row in connection.execute(
                "SELECT manifest_sha256,plan_sha256,acknowledgement_sha256,observation_sha256,capture_sha256,abort_sha256 "
                "FROM weather_acquisitions"
            ):
                for name, sha256 in zip(columns, row, strict=True):
                    if sha256 is not None:
                        blobs.read(sha256)
                        if name == "capture_sha256":
                            verify_dependencies(blobs, blobs.object(sha256))
        for (sha256,) in connection.execute("SELECT manifest_sha256 FROM runs"):
            manifest = blobs.object(sha256)
            context = manifest.get("context")
            assets = context.get("assets") if isinstance(context, dict) else None
            if not isinstance(assets, dict):
                raise VersionUnavailable("archive manifest has no pinned assets")
            for value in assets.values():
                if not isinstance(value, str):
                    raise VersionUnavailable("archive asset hash is invalid")
                blobs.read(value)
    except sqlite3.DatabaseError as error:
        raise VersionUnavailable("archive database is unreadable") from error
    finally:
        connection.close()


def verify(directory: Path) -> Object:
    """Verify bytes and every persisted reference; do not silently repair."""
    try:
        manifest = decode_object((directory / "backup.json").read_bytes())
        database = directory / "workspace.sqlite"
        if manifest.get("schema") != 1 or manifest.get("database_sha256") != digest(
            database.read_bytes()
        ):
            raise VersionUnavailable("archive database hash mismatch")
        hashes = manifest.get("blobs")
        if not isinstance(hashes, list) or any(
            not isinstance(item, str) for item in hashes
        ):
            raise VersionUnavailable("archive blob manifest is invalid")
        if not (directory / "blobs").is_dir():
            raise VersionUnavailable("archive blobs are absent")
        blobs = Blobs(directory / "blobs")
        for item in hashes:
            if not isinstance(item, str):
                raise VersionUnavailable("archive blob hash is invalid")
            blobs.read(item)
        _check_database(database, blobs)
        return manifest
    except (OSError, InvalidInput) as error:
        raise VersionUnavailable("archive files are unavailable") from error


def _publish(temporary: Path, destination: Path) -> None:
    # The target belongs to this invocation; replacing an existing workspace or
    # backup is forbidden. Parent creation is an operator responsibility.
    if destination.exists():
        raise Conflict("archive destination already exists")
    try:
        temporary.rename(destination)
    except OSError as error:
        if destination.exists():
            raise Conflict("archive destination already exists") from error
        raise
    descriptor = os.open(destination.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def backup(workspace: Workspace, destination: Path) -> Object:
    if destination.exists():
        raise Conflict("archive destination already exists")
    temporary = destination.parent / (".incoming-" + uuid4().hex)
    temporary.mkdir(mode=0o700)
    try:
        path = temporary / "workspace.sqlite"
        source = workspace.database.connect()
        target = sqlite3.connect(path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        path.chmod(0o600)
        blobs = Blobs(temporary / "blobs")
        hashes: list[str] = []
        # A new blob published after this enumeration is absent from the prior
        # DB snapshot, so no reference can be lost by concurrent additions.
        for prefix in sorted(workspace.blobs.directory.iterdir()):
            if not re.fullmatch(r"[a-f0-9]{2}", prefix.name) or not prefix.is_dir():
                continue
            for item in sorted(prefix.iterdir()):
                if re.fullmatch(r"[a-f0-9]{64}", item.name):
                    hashes.append(blobs.put(workspace.blobs.read(item.name)))
        _check_database(path, blobs)
        manifest: Object = {
            "schema": 1,
            "database_sha256": digest(path.read_bytes()),
            "blobs": list(hashes),
        }
        backup_path = temporary / "backup.json"
        with backup_path.open("xb") as stream:
            backup_path.chmod(0o600)
            stream.write(encode(manifest))
            stream.flush()
            os.fsync(stream.fileno())
        descriptor = os.open(temporary, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _publish(temporary, destination)
        return manifest
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def restore(archive: Path, destination: Path) -> Workspace:
    """Restore into a new private directory. Never overwrite a running store."""
    if destination.exists():
        raise Conflict("restore destination already exists")
    manifest = verify(archive)
    temporary = destination.parent / (".restoring-" + uuid4().hex)
    temporary.mkdir(mode=0o700)
    try:
        database = temporary / "workspace.sqlite"
        with database.open("xb") as stream:
            database.chmod(0o600)
            stream.write((archive / "workspace.sqlite").read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
        blobs = Blobs(temporary / "blobs")
        hashes = manifest["blobs"]
        if not isinstance(hashes, list):
            raise VersionUnavailable("archive blob manifest is invalid")
        source = Blobs(archive / "blobs")
        for item in hashes:
            if not isinstance(item, str):
                raise VersionUnavailable("archive blob hash is invalid")
            blobs.put(source.read(item))
        # Also catches a source archive changed between verify and copy.
        if digest(database.read_bytes()) != manifest["database_sha256"]:
            raise VersionUnavailable("archive changed during restore")
        _check_database(database, blobs)
        # Upgrade a verified legacy snapshot privately before publishing the
        # restored directory. The source archive and its hash stay unchanged.
        migrated = Workspace(temporary)
        _check_database(migrated.database.path, migrated.blobs)
        descriptor = os.open(temporary, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _publish(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return Workspace(destination)
