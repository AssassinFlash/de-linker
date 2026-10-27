"""Verify explicitly declared child bytes in server-owned persistent documents."""

from __future__ import annotations

from .canonical import Object
from .errors import VersionUnavailable
from .storage import Blobs


def verify_dependencies(blobs: Blobs, document: Object) -> None:
    children = document.get("dependencies")
    if children is None:
        return
    if not isinstance(children, dict):
        raise VersionUnavailable("invalid dependency declaration")
    for name, sha256 in children.items():
        if not name.strip() or not isinstance(sha256, str):
            raise VersionUnavailable("named pinned child assets required")
        blobs.read(sha256)
