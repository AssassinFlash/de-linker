"""Private SQLite transactions and immutable bytes for the workspace.

SQLite is local to HTTP and worker processes. No network request or numerical
calculation runs inside a write transaction. Blob publication precedes database
references, so interrupted writes can leave unreferenced bytes, not broken refs.
"""

from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from .canonical import Object, decode_object, digest, encode
from .errors import InvalidInput, VersionUnavailable
from .schema import SCHEMA, SCHEMA_VERSION


class Blobs:
    """Content-addressed private storage; callers must check project ownership."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _path(self, sha256: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{64}", sha256):
            raise InvalidInput("invalid content hash")
        return self.directory / sha256[:2] / sha256

    def put(self, content: bytes) -> str:
        sha256 = digest(content)
        destination = self._path(sha256)
        try:
            destination.parent.mkdir(mode=0o700)
        except FileExistsError:
            pass
        else:
            # The new prefix directory itself must survive a host interruption.
            descriptor = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        if destination.exists():
            if self.read(sha256) != content:
                raise VersionUnavailable("pinned bytes conflict")
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
            descriptor = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
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
        connection = self.connect()
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            current = connection.execute("PRAGMA user_version").fetchone()[0]
            if current not in (0, SCHEMA_VERSION):
                raise VersionUnavailable("unsupported planning database version")
            connection.executescript(SCHEMA)
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        finally:
            connection.close()
        path.chmod(0o600)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
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
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
