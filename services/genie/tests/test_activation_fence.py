"""Real release directories preserve the newest native lease across late workers."""

from __future__ import annotations

import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

import pytest

import index_release
import publish_index


def native_publisher(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real local files/SQLite/rsync; only the SSH process boundary is in-process."""

    def release(_host: str | None, *args: str, **kwargs: Any) -> dict[str, object]:
        operation, root, *arguments = args
        target = Path(root)
        activation = kwargs.get("activation")
        if operation == "status":
            return index_release.status(target)
        version, *rest = arguments
        if operation == "prepare":
            return index_release.prepare(
                target, version, activation, reuse_basis="--reuse-basis" in rest
            )
        if operation == "validate":
            return index_release.validate(
                target, version, rest[0], kwargs["owner_token"], activation
            )
        if operation == "activate":
            return index_release.activate(target, version, rest[0], activation)
        if operation == "discard":
            return index_release.discard(target, version, kwargs["owner_token"])
        raise AssertionError(f"unexpected publication operation: {operation}")

    monkeypatch.setattr(publish_index, "release", release)


def candidate(
    root: Path, epoch: int, version: str, recipe: str = "b" * 64
) -> tuple[str, dict[str, Any]]:
    stage = Path(str(index_release.prepare(root, version)["incoming"]))
    db = sqlite3.connect(stage / "index.sqlite")
    db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    meta = {
        "version": version,
        "source_revision": "a" * 64,
        "model_identity_revision": "fixture-identity-1",
        "recipe_revision": recipe,
        "serving_revision": "c" * 64,
        "activation_epoch": str(epoch),
    }
    db.executemany("INSERT INTO meta VALUES (?,?)", meta.items())
    db.commit()
    db.close()
    digest = hashlib.sha256((stage / "index.sqlite").read_bytes()).hexdigest()
    (stage / "manifest.json").write_text(
        json.dumps(
            {
                **meta,
                "activation_epoch": epoch,
                "file": {"name": "index.sqlite", "sha256": digest},
            }
        )
    )
    activation = {
        "epoch": epoch,
        "lease_expires_at": int(time.time()) + 300,
        "job_id": f"job-{epoch}",
        "source_revision": meta["source_revision"],
        "model_identity_revision": "fixture-identity-1",
        "recipe_revision": recipe,
        "serving_revision": meta["serving_revision"],
        "verify_url": "https://site.test/wp-json/linker/v1/publication/jobs/claim",
        "username": "owned-worker",
        "password": "fixture-password",
        "loaded_url": "http://127.0.0.1:8000/knowledge/loaded",
        "service_token": "fixture-token",
        "verify_body": {
            "operation": "verify",
            "consumer": "knowledge",
            "job_id": f"job-{epoch}",
            "source_revision": meta["source_revision"],
            "model_identity_revision": "fixture-identity-1",
            "recipe_revision": recipe,
            "activation_epoch": epoch,
            "lease_token": f"lease-{epoch}",
        },
    }
    return digest, activation


def test_late_old_worker_cannot_replace_new_acknowledged_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sha1, first = candidate(tmp_path, 1, "20261024T100000Z")
    sha2, second = candidate(tmp_path, 2, "20261024T100100Z")
    verified = []
    monkeypatch.setattr(
        index_release,
        "_verify_activation",
        lambda value: verified.append(value["epoch"]),
    )
    index_release.activate(tmp_path, "20261024T100100Z", sha2, second)
    # The native acceptance fixture covers the corresponding successful receipt;
    # this schedule deliberately resumes the older publication *after* that point.
    accepted_epoch = 2
    with pytest.raises(RuntimeError, match="stale knowledge activation"):
        index_release.activate(tmp_path, "20261024T100000Z", sha1, first)
    assert index_release.current(tmp_path) == "20261024T100100Z"
    assert (
        json.loads((tmp_path / index_release.FENCE).read_text())["epoch"]
        == accepted_epoch
    )
    assert verified == [2]


def test_rejected_fresh_lease_or_runtime_leaves_previous_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sha1, first = candidate(tmp_path, 1, "20261024T100000Z")
    monkeypatch.setattr(index_release, "_verify_activation", lambda _: None)
    index_release.activate(tmp_path, "20261024T100000Z", sha1, first)
    sha2, second = candidate(tmp_path, 2, "20261024T100100Z")

    def refuse(_: Any) -> None:
        raise RuntimeError("native lease expired")

    monkeypatch.setattr(index_release, "_verify_activation", refuse)
    with pytest.raises(RuntimeError, match="expired"):
        index_release.activate(tmp_path, "20261024T100100Z", sha2, second)
    assert index_release.current(tmp_path) == "20261024T100000Z"
    assert json.loads((tmp_path / index_release.FENCE).read_text())["epoch"] == 1


def test_equal_epoch_is_idempotent_for_exact_target_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(index_release, "_verify_activation", lambda _: None)
    sha1, first = candidate(tmp_path, 1, "20261024T100000Z")
    index_release.activate(tmp_path, "20261024T100000Z", sha1, first)
    assert (
        index_release.activate(tmp_path, "20261024T100000Z", sha1, first)["current"]
        == "20261024T100000Z"
    )
    sha2, second = candidate(tmp_path, 1, "20261024T100100Z")
    with pytest.raises(RuntimeError, match="conflicting generation"):
        index_release.activate(tmp_path, "20261024T100100Z", sha2, second)


def test_crash_after_journal_before_switch_recovers_without_reopening_old_epoch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(index_release, "_verify_activation", lambda _: None)
    sha1, first = candidate(tmp_path, 1, "20261024T100000Z")
    sha2, second = candidate(tmp_path, 2, "20261024T100100Z")
    switch = index_release._switch

    def crash(_: Any, __: Any) -> None:
        raise RuntimeError("simulated process interruption")

    monkeypatch.setattr(index_release, "_switch", crash)
    with pytest.raises(RuntimeError, match="interruption"):
        index_release.activate(tmp_path, "20261024T100100Z", sha2, second)
    assert json.loads((tmp_path / index_release.FENCE).read_text())["epoch"] == 2
    with pytest.raises(RuntimeError, match="stale knowledge activation"):
        index_release.activate(tmp_path, "20261024T100000Z", sha1, first)
    monkeypatch.setattr(index_release, "_switch", switch)
    assert (
        index_release.activate(tmp_path, "20261024T100100Z", sha2, second)["current"]
        == "20261024T100100Z"
    )


def test_managed_rollback_requires_new_higher_native_epoch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(index_release, "_verify_activation", lambda _: None)
    sha1, first = candidate(tmp_path, 1, "20261024T100000Z")
    index_release.activate(tmp_path, "20261024T100000Z", sha1, first)
    with pytest.raises(RuntimeError, match="new native lease epoch"):
        index_release.rollback(tmp_path)
    # A verified prior recipe rebuilt against current Woo uses a new generation.
    sha2, rollback = candidate(tmp_path, 2, "20261024T100100Z", recipe="d" * 64)
    report = index_release.activate(tmp_path, "20261024T100100Z", sha2, rollback)
    fence = report["activation"]
    assert isinstance(fence, dict) and fence["epoch"] == 2
    sha3, _ = candidate(tmp_path, 3, "20261024T100200Z")
    with pytest.raises(RuntimeError, match="fenced lease"):
        index_release.activate(tmp_path, "20261024T100200Z", sha3)


def test_staging_collision_preserves_other_invocation_files(tmp_path: Path) -> None:
    stage = Path(str(index_release.prepare(tmp_path, "20261024T100000Z")["incoming"]))
    (stage / "keep").write_text("owned upload")
    with pytest.raises(FileExistsError):
        index_release.prepare(tmp_path, "20261024T100000Z")
    assert (stage / "keep").read_text() == "owned upload"


def test_failed_publish_reclaims_only_its_owned_incoming_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_publish import build

    source = build(tmp_path, "20261024T100000Z")
    root = tmp_path / "index"
    other = index_release.prepare(root, "20261024T095000Z")
    original = publish_index.release

    def release(host: str | None, *args: str, **kwargs: Any) -> dict[str, object]:
        if args[0] == "activate":
            raise RuntimeError("lease replaced after upload")
        return original(host, *args, **kwargs)

    monkeypatch.setattr(publish_index, "release", release)
    with pytest.raises(RuntimeError, match="lease replaced"):
        publish_index.publish(source, str(root), None)
    assert not (root / ".incoming-20261024T100000Z").exists()
    assert Path(str(other["incoming"])).exists()


def test_discard_refuses_other_owner_and_preserves_journal_recovery_target(
    tmp_path: Path,
) -> None:
    prepared = index_release.prepare(tmp_path, "20261024T100000Z")
    with pytest.raises(RuntimeError, match="ownership"):
        index_release.discard(tmp_path, "20261024T100000Z", "not-the-owner")
    index_release._journal(tmp_path, {"index_version": "20261024T100000Z"})
    assert index_release.discard(
        tmp_path, "20261024T100000Z", str(prepared["owner_token"])
    ) == {"discarded": False}
    assert Path(str(prepared["incoming"])).is_dir()


def test_next_prepare_collects_expired_owned_uploads_only(tmp_path: Path) -> None:
    import time

    expired = index_release.prepare(tmp_path, "expired", {"lease_expires_at": 1})
    live = index_release.prepare(
        tmp_path, "live", {"lease_expires_at": int(time.time()) + 7200}
    )
    # First prepare already collected the expired owned lease.
    assert not Path(str(expired["incoming"])).exists()
    unknown = tmp_path / ".incoming-unknown"
    unknown.mkdir()
    (unknown / "keep").write_text("no ownership proof")
    index_release.prepare(tmp_path, "next")
    assert Path(str(live["incoming"])).is_dir()
    assert (unknown / "keep").read_text() == "no ownership proof"


def test_success_reclaims_upload_after_superseding_its_journal_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(index_release, "_verify_activation", lambda _: None)
    first_version, next_version = "20261024T100000Z", "20261024T100100Z"
    first_sha, first = candidate(tmp_path, 1, first_version)
    journal = index_release._journal

    def crash_after_journal(root: Path, value: dict[str, Any]) -> None:
        journal(root, value)
        raise RuntimeError("interrupted before incoming rename")

    monkeypatch.setattr(index_release, "_journal", crash_after_journal)
    with pytest.raises(RuntimeError, match="before incoming rename"):
        index_release.activate(tmp_path, first_version, first_sha, first)
    abandoned = tmp_path / f".incoming-{first_version}"
    marker = abandoned / index_release.UPLOAD_OWNER
    owner = json.loads(marker.read_text())
    owner.update(managed_knowledge_upload=True, lease_expires_at=1)
    marker.write_text(json.dumps(owner))

    # Preparation preserves the only journal recovery target even when expired.
    next_sha, next_activation = candidate(tmp_path, 2, next_version)
    assert abandoned.is_dir()
    monkeypatch.setattr(index_release, "_journal", journal)
    report = index_release.activate(tmp_path, next_version, next_sha, next_activation)
    assert report["current"] == next_version
    assert not abandoned.exists()


def test_candidate_metadata_must_match_lease_before_native_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sha, activation = candidate(tmp_path, 1, "20261024T100000Z")
    activation["source_revision"] = "e" * 64
    calls = []
    monkeypatch.setattr(
        index_release, "_verify_activation", lambda _: calls.append(True)
    )
    with pytest.raises(RuntimeError, match="does not match"):
        index_release.activate(tmp_path, "20261024T100000Z", sha, activation)
    assert calls == []
    assert not (tmp_path / index_release.FENCE).exists()


@pytest.mark.parametrize(
    "field",
    [
        "sha256",
        "source_revision",
        "recipe_revision",
        "serving_revision",
        "activation_epoch",
    ],
)
def test_uploaded_manifest_mismatch_is_rejected_before_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    version = "20261024T100000Z"
    sha, activation = candidate(tmp_path, 1, version)
    path = tmp_path / f".incoming-{version}" / "manifest.json"
    manifest = json.loads(path.read_text())
    if field == "sha256":
        manifest["file"]["sha256"] = "0" * 64
    else:
        manifest[field] = 99 if field == "activation_epoch" else "wrong"
    path.write_text(json.dumps(manifest))
    calls: list[bool] = []
    monkeypatch.setattr(
        index_release, "_verify_activation", lambda _: calls.append(True)
    )
    with pytest.raises(RuntimeError, match="manifest"):
        index_release.activate(tmp_path, version, sha, activation)
    assert calls == []
    assert index_release.current(tmp_path) is None
    assert not (tmp_path / index_release.FENCE).exists()


def test_ssh_activation_keeps_all_credentials_only_in_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activation = {
        "password": "private-fixture-password",
        "service_token": "private-fixture-service-token",
    }

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert "private-fixture" not in " ".join(command)
        assert json.loads(kwargs["input"]) == activation
        assert command[0] == "ssh"
        return subprocess.CompletedProcess(
            command, 0, stdout='{"current":"target"}', stderr=""
        )

    monkeypatch.setattr(subprocess, "run", run)
    assert publish_index.release(
        "service-host", "activate", "/index", "target", "sha", activation=activation
    ) == {"current": "target"}


def test_ssh_discard_sends_owner_token_only_through_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert all("private-owner-token" not in item for item in command)
        assert "--owner-stdin" in command[-1]
        assert json.loads(kwargs["input"]) == {"owner_token": "private-owner-token"}
        return subprocess.CompletedProcess(
            command, 0, stdout='{"discarded":true}', stderr=""
        )

    monkeypatch.setattr(subprocess, "run", run)
    assert publish_index.release(
        "service-host", "discard", "/index", "target", owner_token="private-owner-token"
    ) == {"discarded": True}


def test_ssh_upload_validation_keeps_owner_and_activation_only_on_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activation = {
        "password": "private-fixture-password",
        "service_token": "private-fixture-service-token",
        "model_identity_revision": "fixture-identity-1",
    }

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert "private-" not in " ".join(command)
        assert "--owner-stdin" in command[-1]
        assert json.loads(kwargs["input"]) == {
            "owner_token": "private-owner-token",
            "activation": activation,
        }
        return subprocess.CompletedProcess(
            command, 0, stdout='{"validated":true}', stderr=""
        )

    monkeypatch.setattr(subprocess, "run", run)
    assert publish_index.release(
        "service-host",
        "validate",
        "/index",
        "target",
        "sha",
        activation=activation,
        owner_token="private-owner-token",
    ) == {"validated": True}


def test_discard_stdin_keeps_owner_check(tmp_path: Path) -> None:
    prepared = index_release.prepare(tmp_path, "owned")
    with pytest.raises(subprocess.CalledProcessError):
        publish_index.release(
            None, "discard", str(tmp_path), "owned", owner_token="wrong"
        )
    assert Path(str(prepared["incoming"])).is_dir()
    assert publish_index.release(
        None,
        "discard",
        str(tmp_path),
        "owned",
        owner_token=str(prepared["owner_token"]),
    ) == {"discarded": True}
    assert not Path(str(prepared["incoming"])).exists()


def test_managed_publish_returns_actual_hash_and_full_fence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    version = "20261024T100100Z"
    source_root = tmp_path / "source"
    digest, activation = candidate(source_root, 2, version)
    source = source_root / f".incoming-{version}"
    (source / "manifest.json").write_text(
        json.dumps(
            {
                "version": version,
                "source_revision": activation["source_revision"],
                "model_identity_revision": "fixture-identity-1",
                "recipe_revision": activation["recipe_revision"],
                "serving_revision": activation["serving_revision"],
                "activation_epoch": activation["epoch"],
                "file": {"name": "index.sqlite", "sha256": digest},
            }
        )
    )
    root = tmp_path / "target"
    calls: list[str] = []

    def release(host: str | None, *args: str, **kwargs: Any) -> dict[str, object]:
        assert host is None
        calls.append(args[0])
        if args[0] == "prepare":
            return index_release.prepare(root, version, kwargs["activation"])
        if args[0] == "activate":
            return index_release.activate(root, version, digest, kwargs["activation"])
        raise AssertionError("successful activation must not need upload cleanup")

    monkeypatch.setattr(publish_index, "release", release)
    monkeypatch.setattr(index_release, "_post_verify", lambda *_: {})
    monkeypatch.setattr(
        index_release,
        "_post",
        lambda *_: {"serving_revision": activation["serving_revision"]},
    )
    report = publish_index.publish(source, str(root), None, activation=activation)
    assert report["sha256"] == digest
    assert publish_index._confirmed_activation(report, version, digest, activation)
    assert calls == ["prepare", "activate"]
    assert not (root / f".incoming-{version}").exists()


def test_activation_calls_native_verify_and_actual_serving_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _, activation = candidate(tmp_path, 1, "20261024T100000Z")
    calls = []

    def verify(
        lease: dict[str, Any], body: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        assert lease is activation
        calls.append((lease["verify_url"], body, headers))
        return {"verified": True}

    def post(url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        calls.append((url, body, headers))
        return {"serving_revision": activation["serving_revision"]}

    monkeypatch.setattr(index_release, "_post_verify", verify)
    monkeypatch.setattr(index_release, "_post", post)
    index_release._verify_activation(activation)
    assert calls[0][1] == activation["verify_body"]
    assert calls[0][2]["Authorization"].startswith("Basic ")
    assert calls[1][2] == {"X-Linker-Service-Token": "fixture-token"}
    activation["serving_revision"] = "f" * 64
    # The running process still has the previously captured immutable code.
    monkeypatch.setattr(
        index_release,
        "_post",
        lambda *_: {"serving_revision": "c" * 64},
    )
    with pytest.raises(RuntimeError, match="incompatible"):
        index_release._verify_activation(activation)


def test_activation_retries_read_only_native_verification_under_its_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sha, activation = candidate(tmp_path, 2, "20261024T100100Z")
    calls: list[str] = []
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)

    class Opener:
        def open(self, request: Any, timeout: float) -> io.BytesIO:
            assert 0 < timeout <= 30
            with (tmp_path / ".activation.lock").open("r") as probe:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            calls.append(request.full_url)
            if request.full_url == activation["verify_url"]:
                assert json.loads(request.data) == activation["verify_body"]
                if len(calls) == 1:
                    raise HTTPError(
                        request.full_url, 503, "unavailable", Message(), None
                    )
                if len(calls) == 2:
                    raise URLError("private fixture")
                value = {
                    "verified": True,
                    "job_id": activation["job_id"],
                    "source_revision": activation["source_revision"],
                    "model_identity_revision": "fixture-identity-1",
                    "recipe_revision": activation["recipe_revision"],
                    "activation_epoch": activation["epoch"],
                }
            else:
                assert request.full_url == activation["loaded_url"]
                value = {"serving_revision": activation["serving_revision"]}
            return io.BytesIO(json.dumps(value).encode())

    monkeypatch.setattr(index_release, "build_opener", lambda *_: Opener())
    result = index_release.activate(tmp_path, "20261024T100100Z", sha, activation)
    assert result["current"] == "20261024T100100Z"
    assert calls == [activation["verify_url"]] * 3 + [activation["loaded_url"]]
    assert sleeps == [1.0, 2.0]


@pytest.mark.parametrize(
    ("failure", "expected_calls"),
    [
        ("404", 1),
        ("409", 1),
        ("job", 1),
        ("source", 1),
        ("recipe", 1),
        ("identity", 1),
        ("epoch", 1),
        ("unverified", 1),
        ("malformed", 1),
        ("expired", 0),
        ("expires_during_verify", 1),
        ("retry_cannot_fit", 1),
        ("expires_during_loaded", 2),
        ("503", 3),
        ("loaded_503", 2),
    ],
)
def test_rejected_or_expired_verification_preserves_old_fence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str, expected_calls: int
) -> None:
    old_sha, old = candidate(tmp_path, 1, "20261024T100000Z")
    with monkeypatch.context() as initial:
        initial.setattr(index_release, "_verify_activation", lambda _: None)
        index_release.activate(tmp_path, "20261024T100000Z", old_sha, old)
    sha, activation = candidate(tmp_path, 2, "20261024T100100Z")
    clock = [1000.0]
    activation["lease_expires_at"] = (
        1001
        if failure == "expired"
        else 1003
        if failure == "retry_cannot_fit"
        else 1300
    )
    calls: list[str] = []
    monkeypatch.setattr(time, "time", lambda: clock[0])
    monkeypatch.setattr(time, "sleep", lambda _: None)

    class Opener:
        def open(self, request: Any, timeout: float) -> io.BytesIO:
            del timeout
            calls.append(request.full_url)
            if request.full_url == activation["verify_url"]:
                if failure == "retry_cannot_fit":
                    headers = Message()
                    headers["Retry-After"] = "300"
                    raise HTTPError(request.full_url, 503, "fixture", headers, None)
                if failure in {"404", "409", "503"}:
                    raise HTTPError(
                        request.full_url, int(failure), "fixture", Message(), None
                    )
                if failure == "malformed":
                    return io.BytesIO(b"not-json")
                if failure == "expires_during_verify":
                    clock[0] = 1300
                value = {
                    "verified": failure != "unverified",
                    "model_identity_revision": "changed"
                    if failure == "identity"
                    else activation["model_identity_revision"],
                    "job_id": "wrong" if failure == "job" else activation["job_id"],
                    "source_revision": "wrong"
                    if failure == "source"
                    else activation["source_revision"],
                    "recipe_revision": "wrong"
                    if failure == "recipe"
                    else activation["recipe_revision"],
                    "activation_epoch": 999
                    if failure == "epoch"
                    else activation["epoch"],
                }
                return io.BytesIO(json.dumps(value).encode())
            if failure == "expires_during_loaded":
                clock[0] = 1300
                return io.BytesIO(
                    json.dumps(
                        {"serving_revision": activation["serving_revision"]}
                    ).encode()
                )
            raise HTTPError(request.full_url, 503, "fixture", Message(), None)

    monkeypatch.setattr(index_release, "build_opener", lambda *_: Opener())
    with pytest.raises(RuntimeError) as rejected:
        index_release.activate(tmp_path, "20261024T100100Z", sha, activation)
    if failure == "retry_cannot_fit":
        assert isinstance(rejected.value, index_release.NativeVerifyFailure)
        assert rejected.value.reason == "retry_exhausted"
        assert rejected.value.status == 503
    assert len(calls) == expected_calls
    assert index_release.current(tmp_path) == "20261024T100000Z"
    assert json.loads((tmp_path / index_release.FENCE).read_text())["epoch"] == 1


@pytest.mark.parametrize(
    "outcome",
    ["confirmed", "different_fence", "different_hash", "unavailable", "ssh_timeout"],
)
def test_lost_ssh_activation_checks_exact_locked_status_without_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    from test_publish import build

    version = "20261024T100100Z"
    source = build(tmp_path, version)
    manifest = json.loads((source / "manifest.json").read_text())
    digest = manifest["file"]["sha256"]
    _, activation = candidate(tmp_path / "identity", 2, version)
    calls: list[str] = []

    def release(host: str | None, *args: str, **kwargs: Any) -> dict[str, object]:
        assert host == "fixture-host"
        operation = args[0]
        calls.append(operation)
        if operation == "prepare":
            return {"incoming": "/private/incoming", "owner_token": "owner"}
        if operation == "activate":
            assert kwargs["timeout"] == publish_index.ACTIVATION_TIMEOUT
            if outcome == "ssh_timeout":
                raise subprocess.TimeoutExpired("ssh", kwargs["timeout"])
            raise subprocess.CalledProcessError(255, "ssh")
        if operation == "discard":
            return {"discarded": False}
        assert operation == "status" and args[-1] == "--locked"
        assert kwargs["timeout"] == 30
        if outcome == "unavailable":
            raise subprocess.TimeoutExpired("ssh", 30)
        return {
            "current": "older" if outcome == "ssh_timeout" else version,
            "index_version": version,
            "sha256_ok": True,
            "sha256": "other" if outcome == "different_hash" else digest,
            "activation": {
                "site": activation["verify_url"],
                "consumer": "knowledge",
                "epoch": activation["epoch"],
                "job_id": activation["job_id"],
                "source_revision": activation["source_revision"],
                "model_identity_revision": "fixture-identity-1",
                "recipe_revision": "wrong"
                if outcome == "different_fence"
                else activation["recipe_revision"],
                "serving_revision": activation["serving_revision"],
                "index_version": version,
                "sha256": digest,
            },
        }

    monkeypatch.setattr(publish_index, "release", release)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0),
    )
    if outcome == "confirmed":
        assert (
            publish_index.publish(
                source, "/index", "fixture-host", activation=activation
            )["current"]
            == version
        )
        assert calls == ["prepare", "activate", "status"]
    else:
        with pytest.raises(RuntimeError, match="outcome unconfirmed"):
            publish_index.publish(
                source, "/index", "fixture-host", activation=activation
            )
        assert calls == ["prepare", "activate", "status"]


def test_successful_ssh_with_mismatched_report_is_not_a_failed_ack_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_publish import build

    version = "20261024T100100Z"
    source = build(tmp_path, version)
    _, activation = candidate(tmp_path / "identity", 2, version)
    calls: list[str] = []

    def release(_host: str | None, *args: str, **_kwargs: Any) -> dict[str, object]:
        calls.append(args[0])
        if args[0] == "prepare":
            return {"incoming": "/private/incoming", "owner_token": "owner"}
        return {"current": version, "index_version": version, "sha256_ok": False}

    monkeypatch.setattr(publish_index, "release", release)
    monkeypatch.setattr(
        subprocess, "run", lambda command, **_: subprocess.CompletedProcess(command, 0)
    )
    with pytest.raises(publish_index.ActivationOutcomeUnconfirmed):
        publish_index.publish(source, "/index", "fixture-host", activation=activation)
    assert calls == ["prepare", "activate", "status"]


def test_locked_status_observes_under_activation_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".activation.lock").touch()

    def inspect(root: Path) -> dict[str, object]:
        with (root / ".activation.lock").open("r") as probe:
            with pytest.raises(BlockingIOError):
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return {"current": None}

    monkeypatch.setattr(index_release, "status", inspect)
    assert index_release.main(["status", str(tmp_path), "--locked"]) == 0


def test_native_verify_rejection_is_a_bounded_private_cli_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    version = "20261024T100100Z"
    digest, activation = candidate(tmp_path, 2, version)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(activation)))

    def reject(*_args: Any) -> None:
        raise index_release.NativeVerifyFailure("retry_exhausted", 503)

    monkeypatch.setattr(index_release, "_post_verify", reject)
    assert (
        index_release.main(
            ["activate", str(tmp_path), version, digest, "--activation-stdin"]
        )
        == 72
    )
    captured = capsys.readouterr()
    value = json.loads(captured.err)
    assert value == {
        "result": "native_verify_rejected",
        "reason": "retry_exhausted",
        "http_status": 503,
        "transport": False,
        "job_id": activation["job_id"],
        "source_revision": activation["source_revision"],
        "model_identity_revision": "fixture-identity-1",
        "recipe_revision": activation["recipe_revision"],
        "epoch": activation["epoch"],
    }
    assert "fixture-password" not in captured.err and "lease-2" not in captured.err
    assert index_release.current(tmp_path) is None
    assert not (tmp_path / index_release.FENCE).exists()


@pytest.mark.parametrize(
    "case", ["valid", "wrong_identity", "wrong_code", "bad_json", "unknown_reason"]
)
def test_only_exact_native_rejection_receipt_is_trusted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    version = "20261024T100100Z"
    digest, activation = candidate(tmp_path, 2, version)
    receipt = {
        "result": "native_verify_rejected",
        "reason": "retry_exhausted",
        "http_status": 503,
        "transport": False,
        "job_id": activation["job_id"],
        "source_revision": activation["source_revision"],
        "model_identity_revision": "fixture-identity-1",
        "recipe_revision": activation["recipe_revision"],
        "epoch": activation["epoch"],
    }
    if case == "wrong_identity":
        receipt["job_id"] = "other-job"
    if case == "unknown_reason":
        receipt["reason"] = "unknown"

    def run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        code = 1 if case == "wrong_code" else 72
        stderr = "{" if case == "bad_json" else json.dumps(receipt)
        raise subprocess.CalledProcessError(code, command, stderr=stderr)

    monkeypatch.setattr(subprocess, "run", run)
    expected = (
        publish_index.NativeVerificationRejected
        if case == "valid"
        else subprocess.CalledProcessError
    )
    with pytest.raises(expected) as failure:
        publish_index.release(
            "host", "activate", "/index", version, digest, activation=activation
        )
    if case == "valid":
        assert isinstance(failure.value, publish_index.NativeVerificationRejected)
        assert failure.value.reason == "retry_exhausted"
        assert failure.value.identity["sha256"] == digest
        assert failure.value.identity["job_id"] == activation["job_id"]


def test_lost_ssh_with_late_remote_verify_keeps_woo_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_preparation_worker import Queue, loaded

    version = "20261024T100100Z"
    source_root = tmp_path / "source"
    digest, activation = candidate(source_root, 2, version)
    source = source_root / f".incoming-{version}"
    (source / "manifest.json").write_text(
        json.dumps(
            {
                "version": version,
                "source_revision": activation["source_revision"],
                "model_identity_revision": "fixture-identity-1",
                "recipe_revision": activation["recipe_revision"],
                "serving_revision": activation["serving_revision"],
                "activation_epoch": activation["epoch"],
                "file": {"name": "index.sqlite", "sha256": digest},
            }
        )
    )
    root = tmp_path / "target"
    queue = Queue()
    worker = queue.worker()
    status_read, verified, finish = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    remote_errors: list[BaseException] = []

    def verify(_activation: dict[str, Any]) -> None:
        assert queue.receipts == []
        verified.set()
        if not finish.wait(5):
            raise TimeoutError("fixture did not release remote activation")

    def remote_activate() -> None:
        try:
            if not status_read.wait(5):
                raise TimeoutError("fixture did not inspect status")
            index_release.activate(root, version, digest, activation)
        except BaseException as error:
            remote_errors.append(error)

    thread = threading.Thread(target=remote_activate)

    def release(host: str | None, *args: str, **kwargs: Any) -> dict[str, object]:
        if args[0] == "prepare":
            return index_release.prepare(root, version, kwargs["activation"])
        if args[0] == "activate":
            thread.start()
            raise subprocess.CalledProcessError(255, "ssh")
        assert args[0] == "status" and args[-1] == "--locked"
        with (root / ".activation.lock").open("r") as lock:
            fcntl.flock(lock, fcntl.LOCK_SH)
            old_status = index_release.status(root)
        status_read.set()
        assert verified.wait(5)
        return old_status

    monkeypatch.setattr(publish_index, "release", release)
    monkeypatch.setattr(index_release, "_verify_activation", verify)
    try:
        with pytest.raises(publish_index.ActivationOutcomeUnconfirmed):
            worker.one(
                lambda _: str(
                    publish_index.publish(
                        source, str(root), None, activation=activation
                    )["index_version"]
                ),
                loaded,
            )
        assert queue.receipts == []
    finally:
        finish.set()
        thread.join(timeout=5)
        worker.close()
    assert not thread.is_alive() and not remote_errors
    assert index_release.current(root) == version


def test_runtime_hook_follows_verified_upload_and_keeps_identity_fence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "host"
    monkeypatch.setattr(index_release, "_verify_activation", lambda _: None)
    first_sha, first = candidate(root, 1, "20261024T100000Z")
    index_release.activate(root, "20261024T100000Z", first_sha, first)
    digest, activation = candidate(tmp_path / "source", 2, "20261024T100100Z")
    source = tmp_path / "source/.incoming-20261024T100100Z"
    native_publisher(monkeypatch)
    order: list[str] = []

    def runtime() -> None:
        uploaded = root / ".incoming-20261024T100100Z"
        assert index_release._sha256(uploaded / "index.sqlite") == digest
        with sqlite3.connect(
            f"file:{uploaded / 'index.sqlite'}?mode=ro", uri=True
        ) as db:
            assert (
                dict(db.execute("SELECT key,value FROM meta"))[
                    "model_identity_revision"
                ]
                == activation["model_identity_revision"]
            )
        assert index_release.current(root) == "20261024T100000Z"
        order.append("runtime")

    def verify(value: dict[str, Any]) -> None:
        assert order == ["runtime"]
        assert value["model_identity_revision"] == "fixture-identity-1"
        order.append("native_verify")

    monkeypatch.setattr(index_release, "_verify_activation", verify)
    report = publish_index.publish(
        source, str(root), None, activation=activation, before_activate=runtime
    )
    assert order == ["runtime", "native_verify"]
    fence = report["activation"]
    assert isinstance(fence, dict)
    assert fence["model_identity_revision"] == "fixture-identity-1"
    assert fence["epoch"] == 2
    assert report["current"] == "20261024T100100Z"
    assert not list(root.glob(".incoming-*"))


@pytest.mark.parametrize(
    "failure",
    ["checksum", "incomplete", "transfer", "model_identity", "model_index", "owner"],
)
def test_invalid_upload_never_runs_runtime_hook_and_cleans_only_its_upload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    root = tmp_path / "host"
    monkeypatch.setattr(index_release, "_verify_activation", lambda _: None)
    first_sha, first = candidate(root, 1, "20261024T100000Z")
    index_release.activate(root, "20261024T100000Z", first_sha, first)
    _, activation = candidate(tmp_path / "source", 2, "20261024T100100Z")
    source = tmp_path / "source/.incoming-20261024T100100Z"
    if failure == "model_index":
        with sqlite3.connect(source / "index.sqlite") as db:
            db.execute(
                "UPDATE meta SET value='different-model-index' WHERE key='model_identity_revision'"
            )
        manifest = json.loads((source / "manifest.json").read_text())
        manifest["file"]["sha256"] = index_release._sha256(source / "index.sqlite")
        (source / "manifest.json").write_text(json.dumps(manifest))
    native_publisher(monkeypatch)
    native_validate = index_release.validate

    def validate(*args: Any, **kwargs: Any) -> dict[str, object]:
        if failure == "owner":
            args = (*args[:3], "another-upload-owner", *args[4:])
        return native_validate(*args, **kwargs)

    monkeypatch.setattr(index_release, "validate", validate)

    def upload(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert argv[0] == "rsync"
        destination = root / ".incoming-20261024T100100Z"
        shutil.copy2(source / "index.sqlite", destination / "index.sqlite")
        if failure == "transfer":
            raise subprocess.CalledProcessError(23, argv)
        if failure != "incomplete":
            shutil.copy2(source / "manifest.json", destination / "manifest.json")
        if failure == "checksum":
            with (destination / "index.sqlite").open("ab") as output:
                output.write(b"truncated-or-corrupt-transfer")
        if failure == "model_identity":
            manifest = json.loads((destination / "manifest.json").read_text())
            manifest["model_identity_revision"] = "a-different-model-authority"
            (destination / "manifest.json").write_text(json.dumps(manifest))
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", upload)
    hooks: list[str] = []
    with pytest.raises((RuntimeError, SystemExit, subprocess.CalledProcessError)):
        publish_index.publish(
            source,
            str(root),
            None,
            activation=activation,
            before_activate=lambda: hooks.append("switched"),
        )
    assert hooks == []
    assert index_release.current(root) == "20261024T100000Z"
    assert json.loads((root / index_release.FENCE).read_text())["epoch"] == 1
    assert not (root / ".incoming-20261024T100100Z").exists()
    assert index_release._sha256(root / "current/index.sqlite") == first_sha


def test_cancelled_runtime_hook_discards_verified_upload_without_activating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, activation = candidate(tmp_path / "source", 1, "20261024T100000Z")
    source = tmp_path / "source/.incoming-20261024T100000Z"
    root = tmp_path / "host"
    native_publisher(monkeypatch)
    calls: list[str] = []

    def cancel() -> None:
        calls.append("hook")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        publish_index.publish(
            source, str(root), None, activation=activation, before_activate=cancel
        )
    assert calls == ["hook"]
    assert index_release.current(root) is None
    assert not (root / index_release.FENCE).exists()
    assert not list(root.glob(".incoming-*"))


def test_activation_after_hook_still_rechecks_actual_candidate_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, activation = candidate(tmp_path / "source", 1, "20261024T100000Z")
    root = tmp_path / "host"
    native_publisher(monkeypatch)
    verified: list[str] = []
    monkeypatch.setattr(
        index_release, "_verify_activation", lambda _: verified.append("native")
    )

    def change_after_validation() -> None:
        (root / ".incoming-20261024T100000Z/index.sqlite").write_bytes(b"changed")

    with pytest.raises(SystemExit, match="sha256"):
        publish_index.publish(
            tmp_path / "source/.incoming-20261024T100000Z",
            str(root),
            None,
            activation=activation,
            before_activate=change_after_validation,
        )
    assert verified == []
    assert index_release.current(root) is None
    assert not list(root.glob(".incoming-*"))


def test_runtime_hook_is_not_replayed_after_confirmed_lost_activation_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, activation = candidate(tmp_path / "source", 1, "20261024T100000Z")
    root = tmp_path / "host"
    native_publisher(monkeypatch)
    monkeypatch.setattr(index_release, "_verify_activation", lambda _: None)
    switch = index_release._switch
    hooks: list[str] = []

    def switched_without_response(*args: Any) -> None:
        switch(*args)
        raise OSError("SSH response lost after the switch")

    monkeypatch.setattr(index_release, "_switch", switched_without_response)
    report = publish_index.publish(
        tmp_path / "source/.incoming-20261024T100000Z",
        str(root),
        None,
        activation=activation,
        before_activate=lambda: hooks.append("runtime"),
    )
    assert hooks == ["runtime"]
    fence = report["activation"]
    assert isinstance(fence, dict)
    assert fence["epoch"] == 1
    assert fence["model_identity_revision"] == "fixture-identity-1"
    assert not list(root.glob(".incoming-*"))


def test_upload_validation_keeps_owner_and_native_context_on_stdin(
    tmp_path: Path,
) -> None:
    digest, activation = candidate(tmp_path, 1, "20261024T100000Z")
    owner = json.loads(
        (
            tmp_path / ".incoming-20261024T100000Z" / index_release.UPLOAD_OWNER
        ).read_text()
    )["owner_token"]
    report = publish_index.release(
        None,
        "validate",
        str(tmp_path),
        "20261024T100000Z",
        digest,
        activation=activation,
        owner_token=owner,
    )
    assert report == {
        "validated": True,
        "index_version": "20261024T100000Z",
        "sha256": digest,
    }


def test_legacy_basis_reuses_real_blocks_without_inheriting_its_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    record_property: Callable[[str, object], None],
) -> None:
    from test_publish import build

    actual_run = subprocess.run
    transfers: list[list[str]] = []

    def transfer(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        if argv[0] == "rsync":
            transfers.append(argv)
        return actual_run(argv, **kwargs)

    monkeypatch.setattr(subprocess, "run", transfer)
    root = tmp_path / "host"
    legacy = build(tmp_path / "legacy", "20261024T100000Z")
    _, activation = candidate(tmp_path / "source", 2, "20261024T100100Z")
    source = tmp_path / "source/.incoming-20261024T100100Z"
    # Two MiB of identical persisted payload and one small changed meta page.
    # Equal size/mtime deliberately cannot distinguish these candidate bytes.
    payload = bytes(range(256)) * 8192
    for directory in (legacy, source):
        with sqlite3.connect(directory / "index.sqlite") as db:
            db.execute("CREATE TABLE payload (value BLOB)")
            db.execute("INSERT INTO payload VALUES (?)", (payload,))
        manifest = json.loads((directory / "manifest.json").read_text())
        manifest["file"]["sha256"] = index_release._sha256(directory / "index.sqlite")
        (directory / "manifest.json").write_text(json.dumps(manifest))
    os.utime(source / "index.sqlite", ns=(1_700_000_000_000_000_000,) * 2)
    os.utime(legacy / "index.sqlite", ns=(1_700_000_000_000_000_000,) * 2)
    native_publisher(monkeypatch)
    publish_index.publish(legacy, str(root), None)
    basis = root / "20261024T100000Z/index.sqlite"
    before = basis.read_bytes()
    assert basis.stat().st_size == (source / "index.sqlite").stat().st_size
    monkeypatch.setattr(index_release, "_verify_activation", lambda _: None)
    monkeypatch.setenv("LC_ALL", "C")
    report = publish_index.publish(
        source, str(root), None, activation=activation, before_activate=lambda: None
    )
    captured = capfd.readouterr()
    output = captured.out + captured.err
    literal_stat = re.search(
        r"^(?:literal|unmatched) data:\s*([\d,]+)", output, re.I | re.M
    )
    matched_stat = re.search(r"^matched data:\s*([\d,]+)", output, re.I | re.M)
    assert literal_stat is not None and matched_stat is not None, output
    literal = int(literal_stat[1].replace(",", ""))
    matched = int(matched_stat[1].replace(",", ""))
    record_property("rsync_literal_bytes", literal)
    record_property("rsync_matched_bytes", matched)
    assert literal > 0 and matched > literal
    assert len(transfers) == 2
    assert all("--compress" in command for command in transfers)
    assert basis.read_bytes() == before
    assert (root / "current/index.sqlite").read_bytes() == (
        source / "index.sqlite"
    ).read_bytes()
    assert basis.stat().st_ino != (root / "current/index.sqlite").stat().st_ino
    assert report["transfer_basis"] == {
        "path": str(basis.parent),
        "reason": "verified_current_bytes",
    }
    fence = report["activation"]
    assert isinstance(fence, dict)
    assert fence["model_identity_revision"] == "fixture-identity-1"


def test_corrupt_current_basis_explicitly_falls_back_to_full_transfer(
    tmp_path: Path,
) -> None:
    from test_publish import build

    root = tmp_path / "host"
    publish_index.publish(build(tmp_path, "20261024T100000Z"), str(root), None)
    (root / "current/index.sqlite").write_bytes(b"bad-old-basis")
    source = build(tmp_path, "20261024T100100Z")
    report = publish_index.publish(
        source, str(root), None, before_activate=lambda: None
    )
    assert report["transfer_basis"] == {
        "path": None,
        "reason": "current_checksum_mismatch",
    }
    assert (root / "current/index.sqlite").read_bytes() == (
        source / "index.sqlite"
    ).read_bytes()
