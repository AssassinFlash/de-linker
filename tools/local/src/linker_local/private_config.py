"""Publish one private operator policy without replacing an existing choice."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .processes import ProcessError

# A policy bound, not a measurement: it must cover one finishing sibling — the
# longest single holder this tool creates is a whole `wp` passthrough — while
# still surfacing true contention (a second manager, a stuck serve) instead of
# serializing behind it. Hosts with slower WP-CLI boots override it.
DEFAULT_LOCK_WAIT_SECONDS = 10.0


def lock_wait_seconds() -> float:
    raw = os.environ.get("LINKER_LOCAL_LOCK_WAIT")
    if raw is None:
        return DEFAULT_LOCK_WAIT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_LOCK_WAIT_SECONDS
    return value if value > 0 else DEFAULT_LOCK_WAIT_SECONDS


@contextmanager
def lifecycle_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.monotonic() + lock_wait_seconds()
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as error:
                if time.monotonic() >= deadline:
                    raise ProcessError(
                        "this instance's services are already being managed"
                    ) from error
                time.sleep(0.1)
        yield
    finally:
        os.close(descriptor)


def publish_once(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix="." + path.name + ".incoming-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(payload, indent=2).encode())
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path
