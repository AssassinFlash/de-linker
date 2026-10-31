"""Verify explicitly declared child bytes in server-owned persistent documents."""

from __future__ import annotations

import fcntl
import json
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .canonical import Object
from .errors import VersionUnavailable
from .frozen_documents import FrozenReader


def verify_dependencies(blobs: FrozenReader, document: Object) -> None:
    children = document.get("dependencies")
    if children is None:
        return
    if not isinstance(children, dict):
        raise VersionUnavailable("invalid dependency declaration")
    for name, sha256 in children.items():
        if not name.strip() or not isinstance(sha256, str):
            raise VersionUnavailable("named pinned child assets required")
        blobs.read(sha256)


@contextmanager
def cas_lock(directory: Path, *, exclusive: bool) -> Iterator[None]:
    """Backups share this lock; offline deletion requires exclusive ownership."""
    descriptor = os.open(
        directory.parent / ".cas.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        try:
            fcntl.flock(
                descriptor,
                (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB,
            )
        except BlockingIOError as error:
            raise VersionUnavailable(
                "CAS backup or maintenance is already active"
            ) from error
        yield
    finally:
        os.close(descriptor)


def reachable_blobs(blobs: FrozenReader, roots: set[str], directory: Path) -> set[str]:
    """Verify the full conservative JSON closure, including nested arrays.

    Software versions in runtime_snapshot.dependencies are not CAS references.
    Explicit document dependencies are checked by their existing callers; this
    traversal additionally retains any present CAS hash anywhere in JSON.
    """
    visited: set[str] = set()
    pending = list(roots)
    while pending:
        sha256 = pending.pop()
        if sha256 in visited:
            continue
        raw = blobs.read(sha256)
        visited.add(sha256)
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError) as error:
            # Binary/raw data is a leaf. Broken JSON-shaped documents cannot
            # establish a complete closure, so deletion must fail closed.
            if raw.lstrip().startswith((b"{", b"[")):
                raise VersionUnavailable(
                    "unreadable retained JSON reference graph"
                ) from error
            continue
        values = [value]
        while values:
            item = values.pop()
            if isinstance(item, dict):
                # Named child CAS references remain strict at every depth.
                # runtime_snapshot.dependencies contains package versions,
                # which are not 64-character CAS identifiers and stay leaves.
                children = item.get("dependencies")
                if isinstance(children, dict):
                    for child in children.values():
                        if isinstance(child, str) and re.fullmatch(
                            r"[a-f0-9]{64}", child
                        ):
                            blobs.read(child)
                            pending.append(child)
                values.extend(item.keys())
                values.extend(item.values())
            elif isinstance(item, list):
                values.extend(item)
            elif isinstance(item, str) and re.fullmatch(r"[a-f0-9]{64}", item):
                path = directory / item[:2] / item
                if path.exists():
                    if path.is_symlink() or path.resolve() != path:
                        raise VersionUnavailable(
                            "CAS references must not follow symbolic links"
                        )
                    pending.append(item)
    return visited
