"""A process snapshot of source plus the exact data bytes its Engine loaded."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path


def source_bytes(directory: Path) -> tuple[bytes, ...]:
    """Capture immutable release source once, never re-read changed disk for a live engine."""
    return tuple(path.read_bytes() for path in sorted(directory.rglob("*.py")))


def digest(source: Iterable[bytes], feed: bytes, compatibility: bytes) -> str:
    """Same source/feed/contract byte order as the local release stamp (#521)."""
    result = hashlib.sha256()
    for part in source:
        result.update(part)
    result.update(feed)
    result.update(compatibility)
    return result.hexdigest()
