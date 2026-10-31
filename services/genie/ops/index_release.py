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
from datetime import UTC
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

INDEX_FILE = "index.sqlite"
# Releases kept on the host: the current one, the one a rollback returns to, and one
# more in case that one is bad too. Older releases are deleted when a new one goes live.
KEEP = 3
FENCE = ".activation.json"
UPLOAD_OWNER = ".upload-owner.json"
VERIFY_ATTEMPTS = 3
RETRY_AFTER_CAP = 2.0
VERIFY_REJECTION_EXIT = 72


class NativeVerifyFailure(RuntimeError):
    """A definite rejection before the activation journal is written."""

    def __init__(
        self, reason: str, status: int | None = None, transport: bool = False
    ) -> None:
        super().__init__("native Woo lease verification rejected")
        self.reason, self.status, self.transport = reason, status, transport


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


def _lease_expiry(activation: dict[str, Any]) -> int:
    expiry = activation.get("lease_expires_at")
    # Leave one second for the activation boundary; never start a request with
    # an already expired or malformed lease.
    if type(expiry) is not int or expiry <= time.time() + 1:
        raise NativeVerifyFailure("expired")
    return expiry


def _retry_after(error: HTTPError) -> float:
    raw = (error.headers.get("Retry-After", "") if error.headers else "").strip()
    delay = 0.0
    if raw.isascii() and raw.isdecimal() and len(raw) <= 8:
        delay = float(int(raw))
    elif 0 < len(raw) <= 128:
        try:
            when = parsedate_to_datetime(raw)
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            delay = max(0.0, when.timestamp() - time.time())
        except (TypeError, ValueError, OverflowError, IndexError):
            pass
    return min(RETRY_AFTER_CAP, delay)


def _post_verify(
    activation: dict[str, Any], body: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    """Retry only native read-only verification, inside activate's lock."""
    for attempt in range(VERIFY_ATTEMPTS):
        expiry = _lease_expiry(activation)
        remaining = expiry - time.time() - 1
        if remaining <= 0:
            raise NativeVerifyFailure("expired")
        request = Request(
            str(activation["verify_url"]),
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        suggested = 0.0
        status: int | None = None
        transport = False
        try:
            with build_opener(_NoRedirect()).open(
                request, timeout=min(30.0, remaining)
            ) as response:
                result = json.load(response)
            _lease_expiry(activation)
            if (
                not isinstance(result, dict)
                or result.get("verified") is not True
                or any(
                    result.get(name) != activation.get(name)
                    for name in (
                        "job_id",
                        "source_revision",
                        "recipe_revision",
                        "model_identity_revision",
                    )
                )
                or type(result.get("activation_epoch")) is not int
                or result.get("activation_epoch") != activation.get("epoch")
            ):
                raise NativeVerifyFailure("response_identity")
            return result
        except HTTPError as error:
            if error.code != 503:
                raise NativeVerifyFailure("http_rejected", status=error.code) from None
            status = 503
            suggested = _retry_after(error)
        except (URLError, TimeoutError, ConnectionError, OSError, HTTPException):
            transport = True
        except (ValueError, TypeError):
            raise NativeVerifyFailure("invalid_response") from None
        if attempt + 1 == VERIFY_ATTEMPTS:
            raise NativeVerifyFailure("retry_exhausted", status, transport)
        delay = max(float(2**attempt), suggested)
        if time.time() + delay + 1 >= expiry:
            # The authority failed and no further retry fits within this lease.
            raise NativeVerifyFailure("retry_exhausted", status, transport)
        time.sleep(delay)
    raise NativeVerifyFailure("retry_exhausted")


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
    for name in (
        "job_id",
        "source_revision",
        "recipe_revision",
        "model_identity_revision",
    ):
        if (
            not isinstance(activation.get(name), str)
            or not activation[name]
            or body.get(name) != activation[name]
        ):
            raise ValueError("activation lease identities differ")
    if (
        type(activation.get("epoch")) is not int
        or activation["epoch"] < 1
        or type(body.get("activation_epoch")) is not int
        or body.get("activation_epoch") != activation["epoch"]
        or not isinstance(body.get("lease_token"), str)
        or not body["lease_token"]
    ):
        raise ValueError("activation lease epoch differs")
    _lease_expiry(activation)
    credential = f"{activation['username']}:{activation['password']}".encode()
    _post_verify(
        activation,
        body,
        {
            "Authorization": "Basic " + base64.b64encode(credential).decode(),
            "Cache-Control": "no-cache",
        },
    )
    loaded = _post(
        str(activation["loaded_url"]),
        {},
        {
            "X-Linker-Service-Token": str(activation["service_token"]),
        },
    )
    if loaded.get("serving_revision") != activation.get("serving_revision"):
        raise RuntimeError("running Genie has incompatible knowledge serving rules")
    _lease_expiry(activation)


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
        report["sha256"] = _sha256(index)
        report["sha256_ok"] = report["sha256"] == manifest["file"]["sha256"]
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


def _delta_basis(root: Path) -> tuple[str | None, str]:
    """A verified immutable current file is bytes only, including legacy indexes."""
    live = current(root)
    if live is None:
        return None, "no_current"
    if Path(live).name != live or live.startswith("."):
        return None, "uncontrolled_current_path"
    directory = root / live
    paths = (directory / INDEX_FILE, directory / "manifest.json")
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or any(path.is_symlink() or not path.is_file() for path in paths)
    ):
        return None, "unavailable_current_files"
    try:
        manifest = json.loads(paths[1].read_text(encoding="utf-8"))
        if (
            not isinstance(manifest, dict)
            or manifest.get("version") != live
            or not isinstance(manifest.get("file"), dict)
            or manifest["file"].get("name") != INDEX_FILE
        ):
            return None, "invalid_current_manifest"
        if _sha256(paths[0]) != manifest["file"].get("sha256"):
            return None, "current_checksum_mismatch"
        db = sqlite3.connect(f"file:{paths[0]}?mode=ro", uri=True)
        try:
            version = db.execute(
                "SELECT value FROM meta WHERE key='version'"
            ).fetchone()
        finally:
            db.close()
        if version != (live,):
            return None, "current_version_mismatch"
    except (OSError, ValueError, sqlite3.Error):
        return None, "unreadable_current"
    # No source/model/permission identity is inherited. The new candidate is
    # independently checked in full by validate()/activate(), after rsync.
    return str(directory.resolve()), "verified_current_bytes"


def prepare(
    root: Path,
    version: str,
    activation: dict[str, Any] | None = None,
    *,
    reuse_basis: bool = False,
) -> dict[str, object]:
    """Own one upload; optionally seed its independent file from current bytes."""
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
        basis, basis_reason = (
            _delta_basis(root) if reuse_basis else (None, "not_requested")
        )
        if basis is not None:
            try:
                # openrsync's copy-dest does not delta-match a changed absent
                # target. A private independent copy enables its normal delta
                # algorithm, without linking or editing the loaded generation.
                shutil.copyfile(Path(basis) / INDEX_FILE, incoming / INDEX_FILE)
            except OSError:
                (incoming / INDEX_FILE).unlink(missing_ok=True)
                basis, basis_reason = None, "independent_basis_copy_unavailable"
    return {
        "incoming": str(incoming),
        "owner_token": owner_token,
        "basis": basis,
        "basis_reason": basis_reason,
    }


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


def _validate_candidate(
    root: Path,
    candidate: Path,
    version: str,
    sha256: str,
    activation: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Static candidate/fence proof, shared before and after a runtime switch."""
    actual = _sha256(candidate / INDEX_FILE)
    if actual != sha256:
        raise SystemExit(f"uploaded {INDEX_FILE} differs from the manifest sha256")
    manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("version") != version
        or not isinstance(manifest.get("file"), dict)
        or manifest["file"].get("name") != INDEX_FILE
        or manifest["file"].get("sha256") != actual
    ):
        raise RuntimeError("uploaded index manifest differs from candidate")
    previous = (
        json.loads((root / FENCE).read_text()) if (root / FENCE).is_file() else None
    )
    if activation is None:
        if previous is not None:
            raise RuntimeError(
                "managed knowledge activation requires a current fenced lease"
            )
        return None
    epoch = activation.get("epoch")
    if type(epoch) is not int or epoch < 1:
        raise ValueError("activation requires a positive native lease epoch")
    identity = {
        "site": str(activation.get("verify_url", "")),
        "consumer": "knowledge",
        "epoch": epoch,
        "job_id": activation.get("job_id"),
        "source_revision": activation.get("source_revision"),
        "model_identity_revision": activation.get("model_identity_revision"),
        "recipe_revision": activation.get("recipe_revision"),
        "serving_revision": activation.get("serving_revision"),
        "index_version": version,
        "sha256": sha256,
    }
    if (
        type(manifest.get("activation_epoch")) is not int
        or manifest.get("activation_epoch") != epoch
        or any(
            manifest.get(name) != identity[name]
            for name in (
                "source_revision",
                "model_identity_revision",
                "recipe_revision",
                "serving_revision",
            )
        )
    ):
        raise RuntimeError("candidate manifest does not match its native lease")
    if previous is not None and (
        previous["site"] != identity["site"]
        or epoch < previous["epoch"]
        or (epoch == previous["epoch"] and previous != identity)
    ):
        raise RuntimeError("stale knowledge activation epoch or conflicting generation")
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
            ("model_identity_revision", identity["model_identity_revision"]),
            ("recipe_revision", identity["recipe_revision"]),
            ("serving_revision", identity["serving_revision"]),
            ("activation_epoch", epoch),
        )
    ):
        raise RuntimeError("candidate index does not match its native activation lease")
    return identity


def validate(
    root: Path,
    version: str,
    sha256: str,
    owner_token: str,
    activation: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Read the actual owned upload before its caller changes the serving runtime."""
    if not version or Path(version).name != version or version.startswith("."):
        raise ValueError("invalid index version")
    with (root / ".activation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        stage = root / f".incoming-{version}"
        if stage.is_symlink() or not stage.is_dir():
            raise RuntimeError("owned index upload is missing")
        owner = json.loads((stage / UPLOAD_OWNER).read_text())
        if not owner_token or owner.get("owner_token") != owner_token:
            raise RuntimeError("upload ownership differs")
        if any(
            path.is_symlink() or not path.is_file()
            for path in (stage / INDEX_FILE, stage / "manifest.json")
        ):
            raise RuntimeError("uploaded index files are incomplete or not regular")
        _validate_candidate(root, stage, version, sha256, activation)
        if activation is not None:
            _lease_expiry(activation)
        else:
            # Even a first unmanaged local publication must be a readable SQLite
            # generation before an optional runtime hook may run.
            db = sqlite3.connect(f"file:{stage / INDEX_FILE}?mode=ro", uri=True)
            try:
                actual_version = db.execute(
                    "SELECT value FROM meta WHERE key='version'"
                ).fetchone()
            finally:
                db.close()
            if actual_version != (version,):
                raise RuntimeError("uploaded SQLite version differs from candidate")
    return {"validated": True, "index_version": version, "sha256": sha256}


def activate(
    root: Path, version: str, sha256: str, activation: dict[str, Any] | None = None
) -> dict[str, object]:
    """Check the uploaded release, put it in place, make it current, prune old ones."""
    with (root / ".activation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        incoming = root / f".incoming-{version}"
        candidate = incoming if incoming.is_dir() else root / version
        identity = _validate_candidate(root, candidate, version, sha256, activation)
        if activation is not None:
            _verify_activation(activation)
            assert identity is not None
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
        result = prepare(root, argv[2], activation, reuse_basis="--reuse-basis" in argv)
    elif command == "discard":
        if len(argv) != 4 or argv[3] != "--owner-stdin":
            raise ValueError("discard requires an owner token on stdin")
        owner = json.load(sys.stdin)
        if not isinstance(owner, dict) or not isinstance(owner.get("owner_token"), str):
            raise ValueError("invalid discard owner")
        result = discard(root, argv[2], owner["owner_token"])
    elif command == "validate":
        if len(argv) != 5 or argv[4] != "--owner-stdin":
            raise ValueError("upload validation requires an owner token on stdin")
        owner = json.load(sys.stdin)
        if not isinstance(owner, dict) or not isinstance(owner.get("owner_token"), str):
            raise ValueError("invalid upload validation owner")
        activation = owner.get("activation")
        if activation is not None and not isinstance(activation, dict):
            raise ValueError("invalid upload validation activation")
        result = validate(root, argv[2], argv[3], owner["owner_token"], activation)
    elif command == "activate":
        activation = json.load(sys.stdin) if "--activation-stdin" in argv else None
        try:
            result = activate(root, argv[2], argv[3], activation)
        except NativeVerifyFailure as error:
            if not isinstance(activation, dict):
                raise
            print(
                json.dumps(
                    {
                        "result": "native_verify_rejected",
                        "reason": error.reason,
                        "http_status": error.status,
                        "transport": error.transport,
                        "job_id": activation.get("job_id"),
                        "source_revision": activation.get("source_revision"),
                        "model_identity_revision": activation.get(
                            "model_identity_revision"
                        ),
                        "recipe_revision": activation.get("recipe_revision"),
                        "epoch": activation.get("epoch"),
                    }
                ),
                file=sys.stderr,
            )
            return VERIFY_REJECTION_EXIT
    elif command == "rollback":
        result = rollback(root)
    elif command == "status":
        if "--locked" in argv:
            # A publisher resolving an ambiguous SSH outcome must observe the
            # journal and current link after any active switch has finished.
            with (root / ".activation.lock").open("r") as lock:
                fcntl.flock(lock, fcntl.LOCK_SH)
                result = status(root)
        else:
            result = status(root)
    else:
        raise SystemExit(f"unknown command {command}")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
