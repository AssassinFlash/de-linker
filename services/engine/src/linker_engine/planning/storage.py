"""Private SQLite transactions and immutable bytes for the workspace.

SQLite is local to HTTP and worker processes. No network request or numerical
calculation runs inside a write transaction. Blob publication precedes database
references, so interrupted writes can leave unreferenced bytes, not broken refs.
"""

from __future__ import annotations

import mmap
import os
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from .canonical import Object, decode_object, digest, encode
from .errors import InvalidInput, VersionUnavailable
from .schema import READABLE_SCHEMA_VERSIONS, SCHEMA, SCHEMA_VERSION
from .schema_upgrade import upgrade_jobs


def _sync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class Blobs:
    """Content-addressed private storage; callers must check project ownership."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _path(self, sha256: str) -> Path:
        if not isinstance(sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", sha256):
            raise InvalidInput("invalid content hash")
        return self.directory / sha256[:2] / sha256

    def put(self, content: bytes) -> str:
        sha256 = digest(content)
        destination = self._path(sha256)
        try:
            destination.parent.mkdir(mode=0o700)
        except FileExistsError:
            pass
        # Reconfirm the prefix even on retries. An existing entry may have
        # survived a previous caller's failed fsync, without being durable yet.
        _sync_directory(self.directory)
        if destination.exists():
            if self.read(sha256) != content:
                raise VersionUnavailable("pinned bytes conflict")
            _sync_directory(destination.parent)
            return sha256
        temporary = destination.parent / (".incoming-" + uuid4().hex)
        try:
            descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                # link, not replace: concurrent writers cannot overwrite a blob.
                os.link(temporary, destination)
            except FileExistsError:
                if self.read(sha256) != content:
                    raise VersionUnavailable("pinned bytes conflict") from None
            _sync_directory(destination.parent)
        finally:
            temporary.unlink(missing_ok=True)
        return sha256

    def put_object(self, value: Object) -> str:
        return self.put(encode(value))

    def read(self, sha256: str) -> bytes:
        try:
            content = self._path(sha256).read_bytes()
        except OSError as error:
            raise VersionUnavailable("pinned content unavailable") from error
        if digest(content) != sha256:
            raise VersionUnavailable("pinned content hash mismatch")
        return content

    def size(self, sha256: str) -> int:
        try:
            return self._path(sha256).stat().st_size
        except OSError as error:
            raise VersionUnavailable("pinned content unavailable") from error

    @contextmanager
    def mapped(self, sha256: str) -> Iterator[mmap.mmap]:
        """Read a large immutable blob without copying all its bytes to Python."""
        try:
            with self._path(sha256).open("rb") as stream:
                with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as view:
                    if digest(view) != sha256:  # type: ignore[arg-type]
                        raise VersionUnavailable("pinned content hash mismatch")
                    yield view
                    if digest(view) != sha256:  # type: ignore[arg-type]
                        raise VersionUnavailable("pinned content hash mismatch")
        except (OSError, ValueError) as error:
            raise VersionUnavailable("pinned content unavailable") from error

    def object(self, sha256: str) -> Object:
        return decode_object(self.read(sha256))


class Database:
    """Short connection-per-operation transactions on a same-host WAL database."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        path.chmod(0o600)
        # The default is sqlite3.connect's documented five-second busy timeout,
        # not a promise that a production queue will meet a five-second SLA.
        connection = self._open_connection()
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute("PRAGMA user_version").fetchone()[0]
            if current not in (0, *READABLE_SCHEMA_VERSIONS):
                raise VersionUnavailable("unsupported planning database version")
            upgrade_jobs(connection, current)
            # SQLite recognises complete trigger bodies. executescript would
            # release the already-held migration lock before running DDL.
            statement = ""
            for line in SCHEMA.splitlines(keepends=True):
                statement += line
                if sqlite3.complete_statement(statement):
                    connection.execute(statement)
                    statement = ""
            if statement.strip():
                raise VersionUnavailable("incomplete planning schema")
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
        path.chmod(0o600)

    def _open_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    @staticmethod
    def _require_schema(connection: sqlite3.Connection) -> None:
        if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise VersionUnavailable("planning database version changed")

    def connect(self) -> sqlite3.Connection:
        connection = self._open_connection()
        try:
            self._require_schema(connection)
        except BaseException:
            connection.close()
            raise
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._require_schema(connection)
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN")
            self._require_schema(connection)
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
