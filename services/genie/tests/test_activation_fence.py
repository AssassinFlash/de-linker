"""Real release directories preserve the newest native lease across late workers."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

import pytest

import index_release
import publish_index


def candidate(
    root: Path, epoch: int, version: str, recipe: str = "b" * 64
) -> tuple[str, dict[str, Any]]:
    stage = Path(str(index_release.prepare(root, version)["incoming"]))
    db = sqlite3.connect(stage / "index.sqlite")
    db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    meta = {
        "version": version,
        "source_revision": "a" * 64,
        "recipe_revision": recipe,
        "serving_revision": "c" * 64,
        "activation_epoch": str(epoch),
    }
    db.executemany("INSERT INTO meta VALUES (?,?)", meta.items())
    db.commit()
    db.close()
    digest = hashlib.sha256((stage / "index.sqlite").read_bytes()).hexdigest()
    (stage / "manifest.json").write_text(
        json.dumps({"version": version, "file": {"sha256": digest}})
    )
    activation = {
        "epoch": epoch,
        "job_id": f"job-{epoch}",
        "source_revision": meta["source_revision"],
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


def test_activation_calls_native_verify_and_actual_serving_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _, activation = candidate(tmp_path, 1, "20261024T100000Z")
    calls = []

    def post(url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        calls.append((url, body, headers))
        return (
            {"verified": True}
            if url == activation["verify_url"]
            else {"serving_revision": activation["serving_revision"]}
        )

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
        lambda url, *_: (
            {"verified": True}
            if url == activation["verify_url"]
            else {"serving_revision": "c" * 64}
        ),
    )
    with pytest.raises(RuntimeError, match="incompatible"):
        index_release._verify_activation(activation)
