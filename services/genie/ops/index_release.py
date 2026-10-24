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

import base64
import fcntl
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

INDEX_FILE = "index.sqlite"
# Releases kept on the host: the current one, the one a rollback returns to, and one
# more in case that one is bad too. Older releases are deleted when a new one goes live.
KEEP = 3
FENCE = ".activation.json"
UPLOAD_OWNER = ".upload-owner.json"


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
    _sync_directory(root)


def _sync_directory(root: Path) -> None:
    descriptor = os.open(root, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _journal(root: Path, value: dict[str, Any]) -> None:
    temporary = root / f".activation-{os.getpid()}.tmp"
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, root / FENCE)
    _sync_directory(root)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def _post(url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with build_opener(_NoRedirect()).open(request, timeout=30) as response:
            data = json.load(response)
        if not isinstance(data, dict):
            raise ValueError("invalid activation response")
        return data
    except (OSError, ValueError, HTTPError):
        # Do not expose authentication, response bodies or request arguments.
        raise RuntimeError(
            "activation authority or serving verification failed"
        ) from None


def _verify_activation(activation: dict[str, Any]) -> None:
    """Fresh native lease and actual imported serving rules; secrets stay in RAM."""
    verify_url = urlsplit(str(activation.get("verify_url", "")))
    loaded_url = urlsplit(str(activation.get("loaded_url", "")))
    if (
        (
            verify_url.scheme != "https"
            and not (
                verify_url.scheme == "http"
                and verify_url.hostname in {"127.0.0.1", "localhost", "::1"}
            )
        )
        or verify_url.username
        or verify_url.password
        or verify_url.query
        or verify_url.fragment
        or verify_url.path != "/wp-json/linker/v1/publication/jobs/claim"
        or loaded_url.scheme != "http"
        or loaded_url.hostname not in {"127.0.0.1", "localhost", "::1"}
        or loaded_url.path != "/knowledge/loaded"
        or loaded_url.username
        or loaded_url.password
        or loaded_url.query
        or loaded_url.fragment
    ):
        raise ValueError(
            "activation requires the native Woo origin and private service loopback"
        )
    body = activation.get("verify_body", {})
    if (
        not isinstance(body, dict)
        or body.get("operation") != "verify"
        or body.get("consumer") != "knowledge"
    ):
        raise ValueError("activation requires a native knowledge lease")
    for name in ("job_id", "source_revision", "recipe_revision"):
        if body.get(name) != activation.get(name):
            raise ValueError("activation lease identities differ")
    if body.get("activation_epoch") != activation.get("epoch") or not body.get(
        "lease_token"
    ):
        raise ValueError("activation lease epoch differs")
    credential = f"{activation['username']}:{activation['password']}".encode()
    verified = _post(
        str(activation["verify_url"]),
        body,
        {
            "Authorization": "Basic " + base64.b64encode(credential).decode(),
            "Cache-Control": "no-cache",
        },
    )
    if verified.get("verified") is not True:
        raise RuntimeError("native Woo lease no longer authorizes activation")
    loaded = _post(
        str(activation["loaded_url"]),
        {},
        {
            "X-Linker-Service-Token": str(activation["service_token"]),
        },
    )
    if loaded.get("serving_revision") != activation.get("serving_revision"):
        raise RuntimeError("running Genie has incompatible knowledge serving rules")


def status(root: Path) -> dict[str, object]:
    """Which release is live, which exist, and what the live index says about itself."""
    live = current(root)
    report: dict[str, object] = {
        "root": str(root),
        "current": live,
        "releases": releases(root),
    }
    if (root / FENCE).is_file():
        report["activation"] = json.loads((root / FENCE).read_text())
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


def _prune_expired_uploads(root: Path) -> None:
    """Only our recorded expired leases; keep the journal's recoverable target."""
    recovery = (
        json.loads((root / FENCE).read_text()).get("index_version")
        if (root / FENCE).is_file()
        else None
    )
    for stage in root.glob(".incoming-*"):
        if stage.is_symlink() or stage.name == f".incoming-{recovery}":
            continue
        marker = stage / UPLOAD_OWNER
        if not marker.is_file():
            continue
        try:
            owner = json.loads(marker.read_text())
        except (OSError, ValueError):
            continue
        expires = owner.get("lease_expires_at")
        if (
            owner.get("managed_knowledge_upload") is True
            and type(expires) is int
            and 0 < expires <= time.time()
        ):
            shutil.rmtree(stage)


def prepare(
    root: Path, version: str, activation: dict[str, Any] | None = None
) -> dict[str, object]:
    """An empty upload directory for one release."""
    if not version or Path(version).name != version or version.startswith("."):
        raise ValueError("invalid index version")
    incoming = root / f".incoming-{version}"
    if (root / version).exists():
        raise SystemExit(f"release {version} already exists under {root}")
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".activation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _prune_expired_uploads(root)
        incoming.mkdir(exist_ok=False)
        owner_token = secrets.token_hex(16)
        owner = {
            "owner_token": owner_token,
            "managed_knowledge_upload": activation is not None,
            "lease_expires_at": activation.get("lease_expires_at")
            if activation
            else None,
        }
        (incoming / UPLOAD_OWNER).write_text(json.dumps(owner))
    return {"incoming": str(incoming), "owner_token": owner_token}


def discard(root: Path, version: str, owner_token: str) -> dict[str, object]:
    """Reclaim only this invocation's failed upload, never a recoverable winner."""
    if not version or Path(version).name != version or version.startswith("."):
        raise ValueError("invalid index version")
    with (root / ".activation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        stage = root / f".incoming-{version}"
        recovery = (
            json.loads((root / FENCE).read_text()).get("index_version")
            if (root / FENCE).is_file()
            else None
        )
        if stage.is_symlink() or not stage.is_dir() or recovery == version:
            return {"discarded": False}
        owner = json.loads((stage / UPLOAD_OWNER).read_text())
        if not owner_token or owner.get("owner_token") != owner_token:
            raise RuntimeError("upload ownership differs")
        shutil.rmtree(stage)
        return {"discarded": True}


def activate(
    root: Path, version: str, sha256: str, activation: dict[str, Any] | None = None
) -> dict[str, object]:
    """Check the uploaded release, put it in place, make it current, prune old ones."""
    with (root / ".activation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        incoming = root / f".incoming-{version}"
        candidate = incoming if incoming.is_dir() else root / version
        actual = _sha256(candidate / INDEX_FILE)
        if actual != sha256:
            raise SystemExit(f"uploaded {INDEX_FILE} differs from the manifest sha256")
        previous = (
            json.loads((root / FENCE).read_text()) if (root / FENCE).is_file() else None
        )
        if activation is None:
            if previous is not None:
                raise RuntimeError(
                    "managed knowledge activation requires a current fenced lease"
                )
        else:
            epoch = activation.get("epoch")
            if type(epoch) is not int or epoch < 1:
                raise ValueError("activation requires a positive native lease epoch")
            identity = {
                "site": str(activation.get("verify_url", "")),
                "consumer": "knowledge",
                "epoch": epoch,
                "job_id": activation.get("job_id"),
                "source_revision": activation.get("source_revision"),
                "recipe_revision": activation.get("recipe_revision"),
                "serving_revision": activation.get("serving_revision"),
                "index_version": version,
                "sha256": sha256,
            }
            if previous is not None and (
                previous["site"] != identity["site"]
                or epoch < previous["epoch"]
                or (epoch == previous["epoch"] and previous != identity)
            ):
                raise RuntimeError(
                    "stale knowledge activation epoch or conflicting generation"
                )
            db = sqlite3.connect(f"file:{candidate / INDEX_FILE}?mode=ro", uri=True)
            try:
                meta = dict(db.execute("SELECT key,value FROM meta"))
            finally:
                db.close()
            if any(
                meta.get(name) != str(value)
                for name, value in (
                    ("version", version),
                    ("source_revision", identity["source_revision"]),
                    ("recipe_revision", identity["recipe_revision"]),
                    ("serving_revision", identity["serving_revision"]),
                    ("activation_epoch", epoch),
                )
            ):
                raise RuntimeError(
                    "candidate index does not match its native activation lease"
                )
            _verify_activation(activation)
            _journal(root, identity)
        if incoming.is_dir():
            incoming.rename(root / version)
            _sync_directory(root)
        _switch(root, version)
        # A newer journal releases the old crashed upload's recovery hold.
        # Collect it now even if the settled Woo queue never prepares again.
        _prune_expired_uploads(root)
        for old in releases(root)[:-KEEP]:
            if old != current(root):
                shutil.rmtree(root / old)
        return status(root)


def rollback(root: Path) -> dict[str, object]:
    """Point `current` at the newest release older than the current one."""
    if (root / FENCE).exists():
        raise RuntimeError(
            "managed rollback must prepare the verified prior recipe with a new native lease epoch"
        )
    live = current(root)
    older = [version for version in releases(root) if live is None or version < live]
    if not older:
        raise SystemExit(f"no release older than {live} under {root}")
    _switch(root, older[-1])
    return status(root)


def main(argv: list[str]) -> int:
    command, root = argv[0], Path(argv[1])
    if command == "prepare":
        activation = json.load(sys.stdin) if "--activation-stdin" in argv else None
        result = prepare(root, argv[2], activation)
    elif command == "discard":
        result = discard(root, argv[2], argv[3])
    elif command == "activate":
        activation = json.load(sys.stdin) if "--activation-stdin" in argv else None
        result = activate(root, argv[2], argv[3], activation)
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
