"""Index releases on the host that serves them: prepare, activate, roll back, report.

Standard library only: `publish_index.py` runs this same file on the Mac for a local
rehearsal and on the VPS through `ssh <host> python3 - <command> ...` (the file on
stdin), so both paths execute one implementation.

Layout under the root (docs/specs/10-knowledge-index.md, Build 5):
    <root>/<version>/index.sqlite, manifest.json   one directory per release
    <root>/current -> <version>                      what the service opens
A release is uploaded into `<root>/.incoming-<version>/`, checked against the sha256 of
its manifest, renamed into place, and `current` is switched by an atomic rename. Rolling
back points `current` at the newest release older than the current one.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

INDEX_FILE = "index.sqlite"
# Releases kept on the host: the current one, the one a rollback returns to, and one
# more in case that one is bad too. Older releases are deleted when a new one goes live.
KEEP = 3


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def releases(root: Path) -> list[str]:
    """Published versions, oldest first (versions are UTC timestamps)."""
    if not root.is_dir():
        # A root nothing was ever published to (status of a fresh host).
        return []
    return sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and not entry.is_symlink() and not entry.name.startswith(".")
    )


def current(root: Path) -> str | None:
    link = root / "current"
    return os.readlink(link) if link.is_symlink() else None


def _switch(root: Path, version: str) -> None:
    temporary = root / f".current-{os.getpid()}"
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(version)
    os.replace(temporary, root / "current")


def status(root: Path) -> dict[str, object]:
    """Which release is live, which exist, and what the live index says about itself."""
    live = current(root)
    report: dict[str, object] = {
        "root": str(root),
        "current": live,
        "releases": releases(root),
    }
    if live is not None:
        index = root / "current" / INDEX_FILE
        manifest = json.loads(
            (root / "current" / "manifest.json").read_text(encoding="utf-8")
        )
        db = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
        try:
            meta = dict(db.execute("SELECT key, value FROM meta").fetchall())
        finally:
            db.close()
        report["index_version"] = meta.get("version")
        report["sha256_ok"] = _sha256(index) == manifest["file"]["sha256"]
    return report


def prepare(root: Path, version: str) -> dict[str, object]:
    """An empty upload directory for one release."""
    incoming = root / f".incoming-{version}"
    if (root / version).exists():
        raise SystemExit(f"release {version} already exists under {root}")
    shutil.rmtree(incoming, ignore_errors=True)
    incoming.mkdir(parents=True)
    return {"incoming": str(incoming)}


def activate(root: Path, version: str, sha256: str) -> dict[str, object]:
    """Check the uploaded release, put it in place, make it current, prune old ones."""
    incoming = root / f".incoming-{version}"
    actual = _sha256(incoming / INDEX_FILE)
    if actual != sha256:
        raise SystemExit(
            f"uploaded {INDEX_FILE} has sha256 {actual}, the manifest says {sha256}"
        )
    incoming.rename(root / version)
    _switch(root, version)
    for old in releases(root)[:-KEEP]:
        if old != current(root):
            shutil.rmtree(root / old)
    return status(root)


def rollback(root: Path) -> dict[str, object]:
    """Point `current` at the newest release older than the current one."""
    live = current(root)
    older = [version for version in releases(root) if live is None or version < live]
    if not older:
        raise SystemExit(f"no release older than {live} under {root}")
    _switch(root, older[-1])
    return status(root)


def main(argv: list[str]) -> int:
    command, root = argv[0], Path(argv[1])
    if command == "prepare":
        result = prepare(root, argv[2])
    elif command == "activate":
        result = activate(root, argv[2], argv[3])
    elif command == "rollback":
        result = rollback(root)
    elif command == "status":
        result = status(root)
    else:
        raise SystemExit(f"unknown command {command}")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
