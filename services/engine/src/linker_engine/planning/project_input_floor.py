"""Inspect every retained input without constructing or migrating a workspace."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .project_input_contracts import required_contracts


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("retained input has duplicate JSON keys")
        value[key] = item
    return value


def _read_project_input_floor(directory: Path) -> dict[str, Any]:
    """Read one SQLite snapshot and hash-check each unique referenced CAS object.

    Missing storage is not an empty history. The release caller separately
    admits an entirely new, unselected and empty deployment before first start.
    No Database/Workspace constructor, schema upgrade or writable connection is
    used here; SQLite must include committed WAL records in its read snapshot.
    """
    directory = directory.absolute()
    database = directory / "workspace.sqlite"
    if directory.resolve() != directory or not database.is_file():
        raise ValueError("retained project input store is unavailable")
    for path in (database, directory / "blobs"):
        if path.is_symlink() or path.resolve() != path:
            raise ValueError("retained project input store follows symbolic links")
    contracts: set[str] = set()
    inputs: set[str] = set()
    inventory: list[tuple[str, int, str]] = []
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        for project, revision, sha in db.execute(
            "SELECT project_id, number, input_sha256 FROM revisions "
            "ORDER BY project_id, number"
        ):
            if (
                not isinstance(project, str)
                or re.fullmatch(r"[a-f0-9]{32}", project) is None
                or type(revision) is not int
                or revision < 1
                or not isinstance(sha, str)
                or re.fullmatch(r"[a-f0-9]{64}", sha) is None
            ):
                raise ValueError("retained project input reference is invalid")
            inventory.append((project, revision, sha))
            if sha in inputs:
                continue
            path = directory / "blobs" / sha[:2] / sha
            if path.is_symlink() or path.resolve() != path:
                raise ValueError("retained project input blob follows symbolic links")
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != sha:
                raise ValueError("retained project input blob hash differs")
            value = json.loads(content, object_pairs_hook=_object)
            if not isinstance(value, dict):
                raise ValueError("retained project input must be an object")
            # Match the persisted JSON domain: finite values and valid UTF-8,
            # without importing a storage constructor or normalizing the bytes.
            json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
            contracts.update(required_contracts(value))
            inputs.add(sha)
        # A missing current revision must not be mistaken for an empty floor.
        if db.execute(
            "SELECT 1 FROM projects p LEFT JOIN revisions r "
            "ON r.project_id=p.id AND r.number=p.revision "
            "WHERE r.project_id IS NULL LIMIT 1"
        ).fetchone():
            raise ValueError("retained project revision is missing")
    return {
        "schema_version": 1,
        "required_input_contracts": sorted(contracts),
        "input_inventory_sha256": hashlib.sha256(
            json.dumps(inventory, separators=(",", ":")).encode()
        ).hexdigest(),
        "retained_revision_count": len(inventory),
        "retained_input_count": len(inputs),
    }


def read_project_input_floor(directory: Path) -> dict[str, Any]:
    """Expose one safe failure type to the private operational endpoint."""
    try:
        return _read_project_input_floor(directory)
    except (OSError, ValueError, UnicodeError, sqlite3.Error) as error:
        raise ValueError(
            "retained project input floor could not be verified"
        ) from error


def check_project_input_contracts(directory: Path, supported: object) -> dict[str, Any]:
    """Absence is handled by callers as an empty capability declaration."""
    if (
        not isinstance(supported, list)
        or any(
            not isinstance(item, str) or re.fullmatch(r"[a-z][a-z0-9_]*", item) is None
            for item in supported
        )
        or len(set(supported)) != len(supported)
    ):
        raise ValueError("invalid project input capability declaration")
    floor = read_project_input_floor(directory)
    if not set(floor["required_input_contracts"]).issubset(supported):
        raise ValueError("executable does not support retained project input contracts")
    return floor
