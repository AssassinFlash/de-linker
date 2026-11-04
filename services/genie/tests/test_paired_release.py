"""Paired selector and activation failures, with synthetic source and no services."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import paired_release as paired
import publication_worker
import publish_index

OLD = "20261031T101504329272Z"
NEW = "20261101T101504329272Z"


def prepared(root: Path) -> dict[str, Any]:
    for name in (OLD, NEW):
        source = root / name
        for relative, text in {
            "index/preparation.py": "def recipe_revision(root): return 'a' * 64\n",
            "src/linker_genie/preparation.py": "def serving_revision(root): return 'b' * 64\n",
            ".venv/bin/python": "synthetic interpreter",
        }.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    (root / "current").symlink_to(OLD)
    return {
        "runtime_root": str(root),
        "candidate": NEW,
        "previous": OLD,
        "identity": {"recipe": "a" * 64, "serving": "b" * 64},
        "action": "status",
    }


def test_real_python_c_remote_dispatch_has_no_file_dependency(tmp_path: Path) -> None:
    request = prepared(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", Path(paired.__file__).read_text(), "--remote"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["current"] == OLD
    assert sorted(p.name for p in tmp_path.iterdir()) == [OLD, NEW, "current"]


def test_same_runtime_checks_processes_without_switching_units(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = prepared(tmp_path)
    request["candidate"] = OLD
    request["identity"]["recipe"] = "c" * 64  # The Mac worker recipe may change.
    monkeypatch.setattr(paired, "running", lambda root, version: {"fixture": 7})
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: pytest.fail("no service switch")
    )
    for action in ("status", "activate", "restore"):
        assert paired.remote({**request, "action": action})["current"] == OLD
    assert (tmp_path / "current").resolve().name == OLD
    request["identity"]["serving"] = "d" * 64
    with pytest.raises(ValueError, match="runtime differs"):
        paired.remote({**request, "action": "status"})


@pytest.mark.parametrize("failure", ["stop", "start"])
def test_restore_recovers_stopped_units_and_old_selector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    request = prepared(tmp_path)
    events = []
    failed = False

    def systemctl(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        nonlocal failed
        action = command[1]
        events.append(action)
        if action == failure and not failed:
            failed = True
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(
            command, 0, stdout=str(tmp_path / "current/.venv/bin/python")
        )

    monkeypatch.setattr(subprocess, "run", systemctl)
    monkeypatch.setattr(paired, "running", lambda root, version: {"verified": 1})
    with pytest.raises(subprocess.CalledProcessError):
        paired.remote({**request, "action": "activate"})
    result = paired.remote({**request, "action": "restore"})
    assert result["current"] == OLD
    assert (tmp_path / "current").resolve().name == OLD
    assert events[-4:] == ["start", "is-active", "is-active", "--fail"]


@pytest.mark.parametrize(
    "error,restore",
    [
        (ValueError("before upload"), True),
        (publish_index.ActivationOutcomeUnconfirmed("lost reply"), False),
        (publish_index.NativeVerificationRejected("expired", None, False, {}), True),
    ],
)
def test_publisher_restores_only_when_activation_is_definitely_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception, restore: bool
) -> None:
    calls = []

    class Runtime:
        def call(self, action: str) -> dict[str, Any]:
            calls.append(action)
            return {}

    (tmp_path / "manifest.json").write_text(
        json.dumps({"version": "new-index", "file": {"sha256": "f" * 64}})
    )
    state: dict[str, Any] = {"before_loaded": {"version": "old-index"}}

    def publish(*args: Any, **kwargs: Any) -> Any:
        if not isinstance(error, ValueError):
            kwargs["before_activate"]()
        raise error

    monkeypatch.setattr(publish_index, "publish", publish)
    publisher = paired.PairedPublisher(
        Runtime(), tmp_path / "journal", state, lambda: state["before_loaded"]
    )
    with pytest.raises(type(error)):
        publisher(tmp_path, "/index", "host")
    assert ("restore" in calls) is restore
    assert state["phase"] == (
        "restored_before_activation" if restore else "activation_possible"
    )
    assert (tmp_path / "journal").stat().st_mode & 0o077 == 0


def test_hook_lost_response_restores_pair_before_any_index_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    class Runtime:
        def call(self, action: str) -> dict[str, Any]:
            calls.append(action)
            if action == "activate":
                raise RuntimeError("response lost")
            return {}

    (tmp_path / "manifest.json").write_text(
        json.dumps({"version": "new-index", "file": {"sha256": "f" * 64}})
    )
    state: dict[str, Any] = {"before_loaded": {}}

    def publish(*args: Any, **kwargs: Any) -> Any:
        kwargs["before_activate"]()
        pytest.fail("activation must not run")

    monkeypatch.setattr(publish_index, "publish", publish)
    with pytest.raises(RuntimeError):
        paired.PairedPublisher(Runtime(), tmp_path / "journal", state, lambda: {})(
            tmp_path, "/index", "host"
        )
    assert calls == ["activate", "restore"]


def test_runtime_failure_restores_old_pair_without_deferring_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    class Runtime:
        def call(self, action: str) -> dict[str, Any]:
            calls.append(action)
            if action == "activate":
                raise RuntimeError("guard refused")
            return {}

    (tmp_path / "manifest.json").write_text(
        json.dumps({"version": "new-index", "file": {"sha256": "f" * 64}})
    )
    state: dict[str, Any] = {
        "before_loaded": {"version": "old"},
        "job": {"lease_expires_at": 9999999999},
    }

    def publish(*args: Any, **kwargs: Any) -> Any:
        kwargs["before_activate"]()
        pytest.fail("index activation must not run")

    monkeypatch.setattr(publish_index, "publish", publish)
    with pytest.raises(RuntimeError, match="guard refused"):
        paired.PairedPublisher(
            Runtime(), tmp_path / "journal", state, lambda: {"version": "old"}
        )(tmp_path, "/index", "host")
    assert calls == ["activate", "restore"]
    assert state["phase"] == "restored_before_activation"


def test_reused_candidate_runs_the_guard_again_before_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = []

    class Runtime:
        def call(self, action: str) -> dict[str, Any]:
            calls.append(action)
            return {}

    (tmp_path / "manifest.json").write_text(
        json.dumps({"version": "same-index", "file": {"sha256": "f" * 64}})
    )
    state: dict[str, Any] = {
        "before_loaded": {},
        "job": {"lease_expires_at": 9999999999, "activation_epoch": 51},
    }

    def publish(*args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs["before_activate"]()
        calls.append("index activation")
        return {"index_version": "same-index"}

    def guard(path: Path, loaded: dict[str, Any], epoch: int) -> None:
        assert path == tmp_path and loaded == {} and epoch == 51
        calls.append("guard")
        if calls.count("guard") == 1:
            raise RuntimeError("private diagnostic details")

    monkeypatch.setattr(publish_index, "publish", publish)
    publisher = paired.PairedPublisher(
        Runtime(), tmp_path / "journal", state, lambda: {}, guard=guard
    )
    assert (
        vars(publication_worker)["PreActivationDeferred"]
        is publish_index.PreActivationDeferred
    )
    with pytest.raises(publish_index.PreActivationDeferred):
        publisher(tmp_path, "/index", "host")
    diagnostic = capsys.readouterr().err
    assert "RuntimeError at test_paired_release.py:" in diagnostic
    assert "private diagnostic details" not in diagnostic
    assert publisher(tmp_path, "/index", "host")["index_version"] == "same-index"
    assert calls == ["guard", "restore", "guard", "activate", "index activation"]


def test_resume_never_activates_when_old_pair_changes_before_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    reads = iter([{"version": "changed"}, {"version": "old"}])

    class Runtime:
        def call(self, action: str) -> dict[str, Any]:
            calls.append(action)
            return {}

    (tmp_path / "manifest.json").write_text(
        json.dumps({"version": "idx", "file": {"sha256": "f" * 64}})
    )
    state: dict[str, Any] = {
        "before_loaded": {"version": "old"},
        "job": {"lease_expires_at": 9999999999, "activation_epoch": 51},
    }

    def publish(*args: Any, **kwargs: Any) -> Any:
        kwargs["before_activate"]()
        pytest.fail("activation must not be reached")

    monkeypatch.setattr(publish_index, "publish", publish)
    with pytest.raises(
        RuntimeError, match="original loaded pair changed before review"
    ):
        paired.PairedPublisher(
            Runtime(),
            tmp_path / "journal",
            state,
            lambda: next(reads),
            guard=lambda *_: pytest.fail("guard must not run"),
        )(tmp_path, "/index", "host")
    assert calls == ["restore"]


def test_no_job_exit_zero_is_not_paired_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path.chmod(0o700)
    monkeypatch.setattr(paired.Runtime, "call", lambda self, action: {"current": OLD})
    monkeypatch.setattr(publication_worker, "main", lambda *args, **kwargs: 0)
    result = paired.main(
        [
            "publish",
            "--host",
            "synthetic",
            "--candidate",
            NEW,
            "--previous",
            OLD,
            "--journal",
            str(tmp_path / "journal"),
            "--loaded-url",
            "http://127.0.0.1:8902/knowledge/loaded",
            "--worker-id",
            "fixture",
        ]
    )
    assert result == 1


def test_published_generation_journal_failure_preserves_native_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    class Runtime:
        def call(self, action: str) -> dict[str, Any]:
            calls.append(action)
            return {}

    (tmp_path / "manifest.json").write_text(
        json.dumps({"version": "new", "file": {"sha256": "f" * 64}})
    )
    original_save = paired.save

    def save(path: Path, state: dict[str, Any]) -> None:
        if state.get("phase") == "activated":
            raise OSError("disk unavailable")
        original_save(path, state)

    def publish(*args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs["before_activate"]()
        return {"current": "new"}

    monkeypatch.setattr(paired, "save", save)
    monkeypatch.setattr(publish_index, "publish", publish)
    with pytest.raises(publish_index.ActivationOutcomeUnconfirmed):
        paired.PairedPublisher(Runtime(), tmp_path / "journal", {}, lambda: {})(
            tmp_path, "/index", "host"
        )
    assert calls == ["activate"]
    assert (
        json.loads((tmp_path / "journal").read_text())["phase"] == "activation_possible"
    )


def test_hook_journal_failure_restores_before_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    class Runtime:
        def call(self, action: str) -> dict[str, Any]:
            calls.append(action)
            return {}

    (tmp_path / "manifest.json").write_text(
        json.dumps({"version": "new", "file": {"sha256": "f" * 64}})
    )
    original_save = paired.save

    def save(path: Path, state: dict[str, Any]) -> None:
        if state.get("phase") == "activation_possible":
            raise OSError("disk unavailable")
        original_save(path, state)

    def publish(*args: Any, **kwargs: Any) -> Any:
        kwargs["before_activate"]()
        pytest.fail("activation was not reached")

    monkeypatch.setattr(paired, "save", save)
    monkeypatch.setattr(publish_index, "publish", publish)
    with pytest.raises(OSError):
        paired.PairedPublisher(
            Runtime(), tmp_path / "journal", {"before_loaded": {}}, lambda: {}
        )(tmp_path, "/index", "host")
    assert calls == ["activate", "restore"]


@pytest.mark.parametrize("command", ["resume-ack", "resume-candidate"])
def test_resume_uses_exact_verify_and_never_claims_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    import httpx

    tmp_path.chmod(0o700)
    source = Path(paired.__file__).resolve().parents[1]
    request = {
        "runtime_root": "/opt/linker-genie",
        "candidate": NEW,
        "previous": OLD,
        "identity": paired.identity(source),
    }
    job = {
        "activation_epoch": 51,
        "lease_expires_at": 9999999999,
        "job_id": "job",
        "source_revision": "s",
        "model_identity_revision": "m",
        "lease_token": "synthetic-lease",
    }
    journal = tmp_path / "journal"
    paired.save(
        journal,
        {
            "request": request,
            "host": "synthetic",
            "worker_id": "fixture",
            "phase": "restored_before_activation"
            if command == "resume-candidate"
            else "activation_possible",
            "job": job,
            "before_loaded": {},
            "index": {"version": "idx", "sha256": "f" * 64},
        },
    )
    bodies = []

    def invoke(*args: Any, **kwargs: Any) -> int:
        if command == "resume-candidate":
            assert kwargs["resume_index"] == {"version": "idx", "sha256": "f" * 64}

        def transport(req: httpx.Request) -> httpx.Response:
            bodies.append(json.loads(req.content))
            return httpx.Response(409, json={"code": "stale_job"})

        worker = kwargs["worker_factory"](
            "https://example.test/wp-json/linker/v1/publication/jobs",
            "u",
            "p",
            "fixture",
            7200,
            transport=httpx.MockTransport(transport),
        )
        try:
            with pytest.raises(httpx.HTTPStatusError):
                worker.claim({})
        finally:
            worker.close()
        return 1

    monkeypatch.setattr(
        paired.Runtime,
        "call",
        lambda self, action: {"current": OLD if command == "resume-candidate" else NEW},
    )
    monkeypatch.setattr(publication_worker, "main", invoke)
    assert (
        paired.main(
            [
                command,
                "--host",
                "synthetic",
                "--candidate",
                NEW,
                "--previous",
                OLD,
                "--journal",
                str(journal),
                "--loaded-url",
                "http://127.0.0.1:8902/knowledge/loaded",
                "--worker-id",
                "fixture",
            ],
            guard=lambda *_: None,
        )
        == 1
    )
    assert len(bodies) == 1
    assert bodies[0]["operation"] == "verify"
    assert bodies[0]["lease_token"] == "synthetic-lease"
    assert journal.exists()


@pytest.mark.parametrize("candidate", [OLD, NEW])
def test_resume_candidate_rejects_missing_guard(candidate: str) -> None:
    with pytest.raises(
        ValueError, match="requires the operator's pre-activation guard"
    ):
        paired.main(
            [
                "resume-candidate",
                "--host",
                "synthetic",
                "--candidate",
                candidate,
                "--previous",
                OLD,
                "--journal",
                "/tmp/unused",
                "--loaded-url",
                "http://localhost",
                "--worker-id",
                "fixture",
            ]
        )


def test_same_runtime_publish_requires_guard() -> None:
    with pytest.raises(ValueError, match="index-only publication requires"):
        paired.main(
            [
                "publish",
                "--host",
                "synthetic",
                "--candidate",
                OLD,
                "--previous",
                OLD,
                "--journal",
                "/tmp/unused",
                "--loaded-url",
                "http://localhost",
                "--worker-id",
                "fixture",
            ]
        )


def test_same_runtime_uses_native_partial_ack_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path.chmod(0o700)
    calls: list[bool] = []

    def ack(self: Any, job: Any, loaded: str, *args: Any, **kwargs: Any) -> None:
        calls.append(kwargs["require_complete"])

    def worker_main(*args: Any, **kwargs: Any) -> int:
        worker = kwargs["worker_factory"](
            "https://example.test/jobs", "u", "p", "fixture", 7200
        )
        try:
            worker.ack({}, "loaded")
        finally:
            worker.close()
        return 0

    monkeypatch.setattr(publication_worker.Worker, "ack", ack)
    monkeypatch.setattr(publication_worker, "main", worker_main)
    monkeypatch.setattr(paired.Runtime, "call", lambda self, action: {"current": OLD})
    result = paired.main(
        [
            "publish",
            "--host",
            "synthetic",
            "--candidate",
            OLD,
            "--previous",
            OLD,
            "--journal",
            str(tmp_path / "journal"),
            "--loaded-url",
            "http://localhost",
            "--worker-id",
            "fixture",
        ],
        guard=lambda *_: None,
    )
    assert result == 0 and calls == [False]
    assert not (tmp_path / "journal").exists()


@pytest.mark.parametrize("same_pair", [True, False])
@pytest.mark.parametrize("index_only", [True, False])
def test_resume_candidate_requires_same_live_lease_and_original_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, same_pair: bool, index_only: bool
) -> None:
    import httpx

    tmp_path.chmod(0o700)
    request = {
        "runtime_root": "/opt/linker-genie",
        "candidate": OLD if index_only else NEW,
        "previous": OLD,
        "identity": paired.identity(Path(paired.__file__).resolve().parents[1]),
    }
    job = {
        "activation_epoch": 51,
        "lease_expires_at": 9999999999,
        "job_id": "job",
        "source_revision": "s",
        "model_identity_revision": "m",
        "lease_token": "synthetic-lease",
    }
    journal = tmp_path / "journal"
    paired.save(
        journal,
        {
            "request": request,
            "host": "synthetic",
            "worker_id": "fixture",
            "phase": "restored_before_activation",
            "job": job,
            "before_loaded": {"index": "old"},
            "index": {"version": "idx", "sha256": "f" * 64},
        },
    )
    operations: list[str] = []

    def invoke(*args: Any, **kwargs: Any) -> int:
        def transport(req: httpx.Request) -> httpx.Response:
            operations.append(json.loads(req.content)["operation"])
            return httpx.Response(200, json={"verified": True})

        worker = kwargs["worker_factory"](
            "https://example.test/jobs",
            "u",
            "p",
            "fixture",
            7200,
            transport=httpx.MockTransport(transport),
        )
        try:
            if same_pair:
                assert worker.claim({"index": "old"}) == job
            else:
                with pytest.raises(RuntimeError, match="original loaded pair changed"):
                    worker.claim({"index": "different"})
        finally:
            worker.close()
        return 1

    monkeypatch.setattr(paired.Runtime, "call", lambda self, action: {"current": OLD})
    monkeypatch.setattr(publication_worker, "main", invoke)
    assert (
        paired.main(
            [
                "resume-candidate",
                "--host",
                "synthetic",
                "--candidate",
                OLD if index_only else NEW,
                "--previous",
                OLD,
                "--journal",
                str(journal),
                "--loaded-url",
                "http://localhost",
                "--worker-id",
                "fixture",
            ],
            guard=lambda *_: None,
        )
        == 1
    )
    assert operations == ["verify"] and journal.exists()


def test_cached_only_release_never_delegates_missing_vectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from index import build

    tmp_path.chmod(0o700)
    delegated = []
    underlying = SimpleNamespace(
        fingerprint={"model": "same-existing-model"},
        model="same-existing-model",
        dimensions=3072,
        embed_documents=lambda rows: delegated.append(rows),
    )
    monkeypatch.setattr(build, "document_embedder", lambda model: underlying)
    monkeypatch.setattr(paired.Runtime, "call", lambda self, action: {"current": OLD})

    def invoke(*args: Any, **kwargs: Any) -> int:
        embedder = kwargs["embedding_factory"]("same-existing-model")
        assert embedder.fingerprint == underlying.fingerprint
        with pytest.raises(RuntimeError, match="refused missing embeddings"):
            embedder.embed_documents(["a missing passage"])
        return 1

    monkeypatch.setattr(publication_worker, "main", invoke)
    assert (
        paired.main(
            [
                "publish",
                "--host",
                "synthetic",
                "--candidate",
                NEW,
                "--previous",
                OLD,
                "--journal",
                str(tmp_path / "journal"),
                "--loaded-url",
                "http://127.0.0.1:8902/knowledge/loaded",
                "--worker-id",
                "fixture",
            ]
        )
        == 1
    )
    assert delegated == []
    assert json.loads((tmp_path / "journal").read_text())["phase"] == "prepared"


def ready_receipts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    state = {
        "request": {"identity": {"recipe": "r", "serving": "v"}},
        "worker_id": "fixture",
        "job": {
            "job_id": "job",
            "activation_epoch": 51,
            "source_revision": "s",
            "model_identity_revision": "m",
        },
        "index": {"version": "idx"},
    }
    loaded = {
        "source_revision": "s",
        "model_identity_revision": "m",
        "recipe_revision": "r",
        "expected_serving_revision": "v",
        "serving_revision": "v",
        "activation_epoch": 51,
        "index_version": "idx",
        "products": [{"product_id": 7, "product_revision": "p"}],
        "materialization_complete": True,
        "preparation_complete": False,
        "unprepared_documents": [
            {"document_id": "d", "product_id": 7, "reason": "no_proven_passage"}
        ],
    }
    native = {
        "job": {
            **loaded,
            "job_id": "job",
            "worker_id": "fixture",
            "status": "ready",
            "loaded_revision": "s",
            "loaded_model_identity_revision": "m",
            "loaded_recipe_revision": "r",
            "loaded_activation_epoch": 51,
            "lease_expires_at": 0,
            "loaded_products": {"7": "p"},
        },
        "lease_token_present": False,
        "current_source": "s",
        "current_model_identity": "m",
    }
    return state, native, loaded


def test_lost_accepted_ack_matches_durable_ready_loaded_and_original_journal() -> None:
    state, native, loaded = ready_receipts()
    paired.validate_ready(state, native, loaded)


@pytest.mark.parametrize(
    "axis",
    [
        "job_id",
        "worker_id",
        "status",
        "source_revision",
        "model_identity_revision",
        "recipe_revision",
        "serving_revision",
        "index_version",
        "activation_epoch",
        "loaded_products",
        "lease_expires_at",
        "preparation_complete",
        "unprepared_documents",
    ],
)
def test_ready_confirmation_refuses_a_different_native_ack(axis: str) -> None:
    state, native, loaded = ready_receipts()
    native["job"][axis] = "different"
    with pytest.raises(RuntimeError):
        paired.validate_ready(state, native, loaded)


def test_ready_confirmation_refuses_new_source_or_live_lease() -> None:
    for axis, value in [
        ("lease_token_present", True),
        ("current_source", "new-source"),
    ]:
        state, native, loaded = ready_receipts()
        native[axis] = value
        with pytest.raises(RuntimeError):
            paired.validate_ready(state, native, loaded)


@pytest.mark.parametrize("complete", [False, None, True])
def test_paired_requires_native_ack_complete_before_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, complete: bool | None
) -> None:
    import httpx

    tmp_path.chmod(0o700)
    journal = tmp_path / "journal"
    observed = []
    selections = iter([OLD, NEW])
    monkeypatch.setattr(
        paired.Runtime, "call", lambda self, action: {"current": next(selections)}
    )

    def invoke(*args: Any, **kwargs: Any) -> int:
        def transport(request: httpx.Request) -> httpx.Response:
            observed.append(request.url.path)
            response: dict[str, Any] = {"accepted": True}
            if complete is not None:
                response["complete"] = complete
            return httpx.Response(200, json=response)

        worker = kwargs["worker_factory"](
            "https://example.test/wp-json/linker/v1/publication/jobs",
            "u",
            "p",
            "fixture",
            7200,
            transport=httpx.MockTransport(transport),
        )
        try:
            try:
                worker.ack(
                    {
                        "job_id": "job",
                        "lease_token": "synthetic",
                        "source_revision": "s",
                        "lease_expires_at": 9999999999,
                    },
                    "s",
                )
            except RuntimeError:
                return 1
            return 0
        finally:
            worker.close()

    monkeypatch.setattr(publication_worker, "main", invoke)
    result = paired.main(
        [
            "publish",
            "--host",
            "synthetic",
            "--candidate",
            NEW,
            "--previous",
            OLD,
            "--journal",
            str(journal),
            "--loaded-url",
            "http://127.0.0.1:8902/knowledge/loaded",
            "--worker-id",
            "fixture",
        ]
    )
    assert result == (0 if complete is True else 1)
    assert journal.exists() is (complete is not True)
    assert observed == ["/wp-json/linker/v1/publication/jobs/ack"]


def test_cached_adapter_builds_and_reads_the_native_store_from_hits(
    tmp_path: Path,
) -> None:
    import sqlite3

    from test_build import CountingEmbedder, corpus
    from test_chunking import Words

    from index.build import build
    from index.corpus import read_chunks, read_meta
    from linker_genie.embedding import Embedder

    inventory, pdfs, parsed = corpus(tmp_path)
    out = tmp_path / "out"
    warm = CountingEmbedder()
    original = build(inventory, pdfs, parsed, out, warm, Words(), lambda text: "en")
    assert warm.embedded > 0
    underlying = CountingEmbedder()
    cached: Embedder = paired.CachedEmbedder(underlying)
    result = build(inventory, pdfs, parsed, out, cached, Words(), lambda text: "en")
    assert underlying.embedded == 0
    assert read_meta(result / "corpus").dimensions == underlying.dimensions
    before = list(read_chunks(original / "corpus"))
    after = list(read_chunks(result / "corpus"))
    assert after == before
    assert all(vector is not None for _, vector in after)
    with sqlite3.connect(
        (result / "index.sqlite").as_uri() + "?mode=ro", uri=True
    ) as db:
        assert db.execute(
            "SELECT value FROM meta WHERE key='dimensions'"
        ).fetchone() == ("2",)
        assert db.execute("SELECT count(*) FROM chunks").fetchone() == (len(after),)
    with pytest.raises(RuntimeError, match="query embedding"):
        cached.embed_query("a query must never be computed")


def test_cached_adapter_native_build_miss_has_zero_provider_calls(
    tmp_path: Path,
) -> None:
    from test_build import CountingEmbedder, corpus
    from test_chunking import Words

    from index.build import build
    from linker_genie.embedding import Embedder

    inventory, pdfs, parsed = corpus(tmp_path)
    underlying = CountingEmbedder()
    cached: Embedder = paired.CachedEmbedder(underlying)
    with pytest.raises(RuntimeError, match="refused missing embeddings"):
        build(
            inventory,
            pdfs,
            parsed,
            tmp_path / "out",
            cached,
            Words(),
            lambda text: "en",
        )
    assert underlying.embedded == 0
    assert not list((tmp_path / "out" / "builds").glob("*/index.sqlite"))


def test_activation_refuses_an_unimportable_candidate_before_stopping_units(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = prepared(tmp_path)
    calls = []

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[:2] == [str(tmp_path / NEW / ".venv/bin/python"), "-c"]:
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(
            command, 0, stdout=str(tmp_path / "current/.venv/bin/python")
        )

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        paired.remote({**request, "action": "activate"})
    assert not any(
        len(command) > 1 and command[:2] == ["systemctl", "stop"] for command in calls
    )


def test_activation_fails_when_application_health_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = prepared(tmp_path)

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[0] == "curl":
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(
            command, 0, stdout=str(tmp_path / "current/.venv/bin/python")
        )

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(paired, "running", lambda root, version: {"verified": 1})
    with pytest.raises(subprocess.CalledProcessError):
        paired.remote({**request, "action": "activate"})
