"""Recipe-aware preparation receipts preserve coverage and actual loaded identity."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import syslog
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from linker_genie.preparation import RUNTIME_SERVING_REVISION
from linker_genie.publication import PublicationClient, PublicationUnavailable
from publication_worker import (
    Worker,
    record_build,
    report_failure,
    run_job,
    validated_pending,
)
from publish_index import (
    ActivationOutcomeUnconfirmed,
    NativeVerificationRejected,
    PreActivationDeferred,
)

RECIPE = "a" * 64


def test_pre_activation_review_keeps_one_candidate_until_same_lease_or_expiry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "index"
    directory = root / "builds" / "generation"
    calls: list[str] = []

    class DeferredWorker:
        def one(self, prepare: Any, loaded: Any) -> bool:
            calls.append("attempt")
            directory.mkdir(parents=True)
            record_build(root, directory)
            raise PreActivationDeferred(200)

    monkeypatch.setattr("publication_worker.time.time", lambda: 100)
    with pytest.raises(PreActivationDeferred):
        run_job(DeferredWorker(), lambda _: "", lambda: {}, root)  # type: ignore[arg-type]
    assert directory.exists()
    with pytest.raises(RuntimeError, match="awaits same-lease review"):
        run_job(DeferredWorker(), lambda _: "", lambda: {}, root)  # type: ignore[arg-type]
    assert calls == ["attempt"] and directory.exists()
    monkeypatch.setattr("publication_worker.time.time", lambda: 201)

    class NoJob:
        def one(self, prepare: Any, loaded: Any) -> bool:
            return False

    assert not run_job(NoJob(), lambda _: "", lambda: {}, root)  # type: ignore[arg-type]
    assert not directory.exists()


@pytest.mark.parametrize("change", ["none", "bytes", "epoch", "source", "recipe"])
def test_resumed_candidate_checks_exact_index_and_lease_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    root = tmp_path / "index"
    directory = root / "builds" / "generation"
    directory.mkdir(parents=True)
    record_build(root, directory)
    expected = {
        "version": "generation",
        "source_revision": "source",
        "model_identity_revision": "model",
        "recipe_revision": "recipe",
        "serving_revision": "serving",
        "activation_epoch": 42,
    }
    with sqlite3.connect(directory / "index.sqlite") as db:
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.executemany(
            "INSERT INTO meta VALUES (?, ?)", [(k, str(v)) for k, v in expected.items()]
        )
    digest = hashlib.sha256((directory / "index.sqlite").read_bytes()).hexdigest()
    (directory / "manifest.json").write_text(
        json.dumps({**expected, "file": {"name": "index.sqlite", "sha256": digest}})
    )
    activation = {
        "source_revision": "source",
        "model_identity_revision": "model",
        "recipe_revision": "recipe",
        "serving_revision": "serving",
        "epoch": 42,
    }
    if change == "bytes":
        with (directory / "index.sqlite").open("ab") as out:
            out.write(b"changed")
    elif change == "epoch":
        activation["epoch"] = 43
    elif change == "source":
        activation["source_revision"] = "other"
    elif change == "recipe":
        activation["recipe_revision"] = "other"
    if change == "none":
        assert (
            validated_pending(
                root, activation, {"version": "generation", "sha256": digest}
            )
            == directory
        )
        calls: list[str] = []

        class ResumeWorker:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def one(self, prepare: Any, loaded: Any) -> bool:
                return str(prepare({})) == "generation"

            def activation(self) -> dict[str, Any]:
                return dict(activation)

            def publication_confirmed(self) -> None:
                calls.append("confirmed")

            def close(self) -> None:
                calls.append("closed")

        def publisher(path: Path, *args: Any, **kwargs: Any) -> dict[str, str]:
            assert path == directory
            calls.append("publish-existing-index")
            return {"index_version": path.name}

        import publication_worker

        monkeypatch.setattr(publication_worker, "INDEX_DIR", root)
        monkeypatch.setattr("publication_worker.sys.platform", "darwin")
        monkeypatch.setattr(
            "publication_worker.build.build",
            lambda *a, **k: pytest.fail("rebuild occurred"),
        )
        for key in (
            "LINKER_PUBLICATION_JOBS_URL",
            "LINKER_PUBLICATION_USER",
            "LINKER_PUBLICATION_PASSWORD",
            "GENIE_SERVICE_TOKEN",
        ):
            monkeypatch.setenv(key, "fixture")
        assert (
            publication_worker.main(
                [
                    "--worker-id",
                    "fixture",
                    "--lease-seconds",
                    "300",
                    "--loaded-url",
                    "http://localhost",
                ],
                publisher=publisher,
                worker_factory=ResumeWorker,
                resume_index={"version": "generation", "sha256": digest},
            )
            == 0
        )
        assert calls == ["publish-existing-index", "confirmed", "closed"]
        assert (
            directory.exists()
            and not (root / "publication-worker-pending.json").exists()
        )
    else:
        with pytest.raises(RuntimeError, match="identity or checksum differs"):
            validated_pending(
                root, activation, {"version": "generation", "sha256": digest}
            )


@pytest.mark.parametrize("mode", ["enabled", "disabled", "wrong_host"])
def test_worker_site_bypass_keeps_other_effective_proxy_routes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    import install_publication_worker as installer

    keys = [
        name + suffix
        for name, suffix in (
            ("HTTP", "_PROXY"),
            ("HTTPS", "_PROXY"),
            ("ALL", "_PROXY"),
            ("NO", "_PROXY"),
            ("http", "_proxy"),
            ("https", "_proxy"),
            ("all", "_proxy"),
            ("no", "_proxy"),
        )
    ]
    for key in keys:
        monkeypatch.setenv(key, "original-" + key)
    before = {key: os.environ[key] for key in keys}
    direct = (
        ""
        if mode == "disabled"
        else "other.test"
        if mode == "wrong_host"
        else "site.test"
    )
    for key in ("LINKER_PUBLICATION_JOBS_URL", "LINKER_PUBLICATION_DIRECT_HOST"):
        monkeypatch.setenv(key, "")
    environment = tmp_path / "private.env"
    environment.write_text(
        "LINKER_PUBLICATION_JOBS_URL=https://site.test/jobs\n"
        + "LINKER_PUBLICATION_DIRECT_HOST="
        + direct
        + "\n"
    )
    environment.chmod(0o600)
    proxies = {
        "http": "http://proxy.test:8080",
        "https": "http://proxy.test:8080",
        "all": "socks5://proxy.test:1080",
        "no": "localhost,already.test",
    }
    reads: list[bool] = []
    children: list[dict[str, str]] = []

    def system_routes() -> dict[str, str]:
        reads.append(True)
        return proxies

    def child(_command: list[str], **_kwargs: Any) -> int:
        children.append({key: os.environ[key] for key in keys})
        return 23

    monkeypatch.setattr(installer, "getproxies", system_routes)
    monkeypatch.setattr(subprocess, "call", child)
    if mode == "wrong_host":
        with pytest.raises(ValueError, match="differs from configured site"):
            installer.run_private(environment, ["--worker-id", "fixture"])
        assert not children and not reads
    else:
        assert installer.run_private(environment, ["--worker-id", "fixture"]) == 23
        assert len(children) == 1
        if mode == "disabled":
            assert children[0] == before and not reads
        else:
            assert len(reads) == 1
            for scheme in ("http", "https", "all"):
                assert children[0][scheme.upper() + "_PROXY"] == proxies[scheme]
                assert children[0][scheme + "_proxy"] == proxies[scheme]
            assert (
                children[0]["NO_PROXY"]
                == children[0]["no_proxy"]
                == "localhost,already.test,site.test"
            )


def source(revision: str = "source-1") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source_revision": revision,
        "model_identity_revision": "fixture-identity-1",
        "products": [
            {"product_id": 1, "product_revision": "p1", "documents": ["doc"]},
            {"product_id": 2, "product_revision": "p2", "documents": ["doc"]},
        ],
        "documents": [
            {
                "document_id": "doc",
                "document_revision": "d1",
                "blob_sha256": "b" * 64,
                "product_ids": [1, 2],
            }
        ],
    }


class Queue:
    def __init__(self) -> None:
        self.source = source()
        self.recipe = ""
        self.ready = False
        self.epoch = 0
        self.receipts: list[dict[str, Any]] = []
        self.claims: list[dict[str, Any]] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content)
        if request.url.path.endswith("claim"):
            self.claims.append(data)
            if self.recipe != data["recipe_revision"]:
                self.recipe, self.ready = data["recipe_revision"], False
            actual = data.get("loaded_receipt")
            if self.ready and actual is not None:
                receipt = self.receipts[-1]
                identities = {
                    "source_revision": "loaded_revision",
                    "model_identity_revision": "loaded_model_identity_revision",
                    "recipe_revision": "loaded_recipe_revision",
                    "expected_serving_revision": "expected_serving_revision",
                    "serving_revision": "serving_revision",
                    "index_version": "index_version",
                    "activation_epoch": "activation_epoch",
                }
                observed_products = {
                    row["product_id"]: row["product_revision"]
                    for row in actual["products"]
                }
                trusted_products = {
                    row["product_id"]: row["product_revision"]
                    for row in receipt["prepared_products"]
                }
                if (
                    any(
                        actual.get(key) != receipt[stored]
                        for key, stored in identities.items()
                    )
                    or observed_products != trusted_products
                ):
                    self.ready = False
            if not self.ready:
                self.epoch += 1
            return httpx.Response(
                200,
                json={
                    "job": None
                    if self.ready
                    else {
                        "job_id": "job-" + self.recipe,
                        "source_revision": self.source["source_revision"],
                        "model_identity_revision": "fixture-identity-1",
                        "recipe_revision": self.recipe,
                        "activation_epoch": self.epoch,
                        "lease_expires_at": int(time.time()) + 600,
                        "lease_token": "lease",
                        "manifest": self.source,
                    }
                },
            )
        self.receipts.append(data)
        self.ready = (
            data["status"] == "ready" and data["materialization_complete"] is True
        )
        return httpx.Response(200, json={"accepted": True, "complete": self.ready})

    def worker(self, recipe: str = RECIPE) -> Worker:
        return Worker(
            "https://site.test/jobs",
            "fixture",
            "fixture",
            "mac",
            600,
            recipe=recipe,
            transport=httpx.MockTransport(self.handle),
        )


def loaded(**changes: Any) -> dict[str, Any]:
    return {
        "source_revision": "source-1",
        "model_identity_revision": "fixture-identity-1",
        "recipe_revision": RECIPE,
        "expected_serving_revision": RUNTIME_SERVING_REVISION,
        "serving_revision": RUNTIME_SERVING_REVISION,
        "activation_epoch": 1,
        "index_version": "build1",
        "products": [{"product_id": 1, "product_revision": "p1"}],
        "materialization_complete": True,
        "preparation_complete": False,
        "unprepared_documents": [
            {"document_id": "doc", "product_id": 2, "reason": "no_proven_passage"}
        ],
        **changes,
    }


def test_pre_activation_review_does_not_fail_the_original_lease() -> None:
    queue = Queue()
    worker = queue.worker()
    try:
        with pytest.raises(PreActivationDeferred):
            worker.one(
                lambda _: (_ for _ in ()).throw(
                    PreActivationDeferred(int(time.time()) + 60)
                ),
                loaded,
            )
        assert len(queue.claims) == 1 and queue.receipts == []
    finally:
        worker.close()


def test_materialized_semantic_warning_does_not_repeat_same_recipe_build() -> None:
    queue, calls = Queue(), []
    worker = queue.worker()

    def prepare(manifest: dict[str, Any]) -> str:
        calls.append(manifest)
        return "build1"

    assert worker.one(prepare, loaded)
    assert not worker.one(prepare, loaded)
    assert len(calls) == 1
    receipt = queue.receipts[-1]
    assert receipt["materialization_complete"] is True
    assert receipt["preparation_complete"] is False
    assert receipt["prepared_products"] == loaded()["products"]
    assert receipt["unprepared_documents"] == loaded()["unprepared_documents"]
    assert receipt["recipe_revision"] == receipt["loaded_recipe_revision"] == RECIPE
    assert receipt["index_version"] == "build1"
    assert (
        receipt["expected_serving_revision"]
        == receipt["serving_revision"]
        == RUNTIME_SERVING_REVISION
    )
    assert receipt["error"]
    worker.close()


def test_unknown_loaded_observation_reports_failure_without_rebuilding_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = Queue()
    worker = queue.worker()
    assert worker.one(lambda _: "build1", loaded)
    reports: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "publication_worker.report_failure",
        lambda phase, error: reports.append((phase, type(error).__name__)),
    )

    def unavailable() -> dict[str, Any]:
        raise OSError("one loopback SSH observation failed")

    def no_rebuild(_: dict[str, Any]) -> str:
        pytest.fail(
            "an unknown observation must not rebuild the acknowledged generation"
        )

    try:
        assert not worker.one(no_rebuild, unavailable)
        assert queue.ready and queue.epoch == 1
        assert len(queue.receipts) == 1
        assert queue.claims[-1]["loaded_receipt"] is None
        assert queue.claims[-1]["loaded_unavailable"] is True
        assert reports == [("loaded_observation", "OSError")]
    finally:
        worker.close()


def test_malformed_loaded_observation_is_reported_and_does_not_rebuild_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = Queue()
    worker = queue.worker()
    assert worker.one(lambda _: "build1", loaded)
    failures: list[str] = []
    monkeypatch.setattr(
        "publication_worker.report_failure",
        lambda phase, _error: failures.append(phase),
    )
    try:
        assert not worker.one(
            lambda _: pytest.fail("partial observation cannot revoke ready"),
            lambda: {"index_version": "partial-response"},
        )
        assert queue.ready and queue.epoch == 1
        assert failures == ["loaded_observation"]
    finally:
        worker.close()


def test_unknown_bootstrap_still_claims_and_prepares_a_real_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = Queue()
    worker = queue.worker()
    failures: list[str] = []
    monkeypatch.setattr(
        "publication_worker.report_failure",
        lambda phase, _error: failures.append(phase),
    )
    observations = 0

    def current() -> dict[str, Any]:
        nonlocal observations
        observations += 1
        if observations == 1:
            raise OSError("no serving process at bootstrap")
        return loaded()

    try:
        assert worker.one(lambda _: "build1", current)
        assert queue.ready and queue.epoch == 1
        assert len(queue.receipts) == 1
        assert failures == ["loaded_observation"]
    finally:
        worker.close()


def test_document_parse_failure_retries_even_with_false_materialization_claim() -> None:
    queue = Queue()
    worker = queue.worker()

    def failure() -> dict[str, Any]:
        return loaded(
            activation_epoch=queue.epoch,
            unprepared_documents=[
                {"document_id": "doc", "product_id": 2, "reason": "document_unparsed"}
            ],
        )

    assert worker.one(lambda _: "build1", failure)
    assert queue.receipts[-1]["materialization_complete"] is False
    assert worker.one(lambda _: "build1", failure)
    assert len(queue.receipts) == 2
    worker.close()


def test_recipe_only_upgrade_reprocesses_unchanged_woo_source() -> None:
    queue = Queue()
    worker = queue.worker()
    assert worker.one(lambda _: "build1", loaded)
    worker.close()
    upgraded = queue.worker("c" * 64)
    assert upgraded.one(
        lambda _: "build2",
        lambda: loaded(
            recipe_revision="c" * 64,
            index_version="build2",
            activation_epoch=queue.epoch,
        ),
    )
    assert queue.receipts[-1]["source_revision"] == "source-1"
    assert queue.receipts[-1]["index_version"] == "build2"
    upgraded.close()


@pytest.mark.parametrize(
    "changes",
    [
        {"recipe_revision": "old-recipe"},
        {"recipe_revision": ""},
        {"source_revision": "old-source"},
        {"index_version": "old-index"},
        {"expected_serving_revision": "old-serving-expectation"},
        {"serving_revision": "old-running-proof-code"},
        {"activation_epoch": 0},
    ],
)
def test_serving_identity_mismatch_never_acknowledges_ready(
    changes: dict[str, Any],
) -> None:
    queue = Queue()
    worker = queue.worker()
    with pytest.raises(RuntimeError, match="has not loaded"):
        worker.one(lambda _: "build1", lambda: loaded(**changes))
    assert queue.receipts == [] and not queue.ready
    worker.close()


@pytest.mark.parametrize(
    "products",
    [
        [{"product_id": 3, "product_revision": "private"}],
        [{"product_id": 1, "product_revision": "old"}],
        [{"product_id": True, "product_revision": "p1"}],
        [{"product_id": 1, "product_revision": "p1"}] * 2,
    ],
)
def test_prepared_products_must_be_an_exact_current_subset(
    products: list[dict[str, Any]],
) -> None:
    queue = Queue()
    worker = queue.worker()
    with pytest.raises(RuntimeError, match="invalid prepared"):
        worker.one(lambda _: "build1", lambda: loaded(products=products))
    assert queue.receipts == [] and not queue.ready
    worker.close()


def test_worker_preflights_ready_receipt_and_rebuilds_after_actual_switch() -> None:
    queue = Queue()
    worker = queue.worker()
    actual = loaded()
    assert worker.one(lambda _: "build1", lambda: actual)
    actual["index_version"] = "unacknowledged-foreign-index"

    def repair(_: dict[str, Any]) -> str:
        actual.update(index_version="build2", activation_epoch=queue.epoch)
        return "build2"

    assert worker.one(repair, lambda: actual)
    assert (
        queue.claims[-1]["loaded_receipt"]["index_version"]
        == "unacknowledged-foreign-index"
    )
    assert queue.receipts[-1]["index_version"] == "build2"
    assert queue.receipts[-1]["activation_epoch"] == 2
    assert not worker.one(repair, lambda: actual)
    worker.close()


def test_activation_context_is_bound_to_current_lease_and_cleared_after_ack() -> None:
    queue = Queue()
    worker = queue.worker()
    with pytest.raises(RuntimeError, match="current native lease"):
        worker.activation()

    def prepare(_: dict[str, Any]) -> str:
        context = worker.activation()
        assert context["epoch"] == 1
        assert context["verify_url"] == "https://site.test/jobs/claim"
        assert context["verify_body"]["operation"] == "verify"
        assert context["verify_body"]["lease_token"] == "lease"
        assert context["verify_body"]["activation_epoch"] == 1
        assert context["serving_revision"] == RUNTIME_SERVING_REVISION
        assert worker.lease_expiry() == context["lease_expires_at"]
        return "build1"

    assert worker.one(prepare, loaded)
    with pytest.raises(RuntimeError, match="current native lease"):
        worker.activation()
    worker.close()


def test_prepare_and_failed_ack_keep_distinct_safe_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed receipt must not hide the failure that left a job preparing."""
    queue = Queue()
    events: list[str] = []
    monkeypatch.setattr(
        syslog, "syslog", lambda _priority, message: events.append(message)
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ack"):
            return httpx.Response(503, request=request)
        return queue.handle(request)

    worker = Worker(
        "https://site.test/jobs",
        "fixture",
        "fixture",
        "mac",
        600,
        recipe=RECIPE,
        transport=httpx.MockTransport(handler),
    )

    def prepare(_manifest: dict[str, Any]) -> str:
        raise ValueError("private fixture detail must not be logged")

    with pytest.raises(ValueError, match="private fixture detail"):
        worker.one(prepare, loaded)
    assert any(
        "phase=prepare" in event and "error=ValueError" in event for event in events
    )
    assert any(
        "phase=failure_ack" in event
        and "error=HTTPStatusError" in event
        and "http_status=503" in event
        for event in events
    )
    assert all("private fixture detail" not in event for event in events)
    assert all("site.test" not in event and "lease" not in event for event in events)
    worker.close()


def test_unconfirmed_activation_does_not_release_the_native_lease() -> None:
    queue = Queue()
    worker = queue.worker()

    def prepare(_manifest: dict[str, Any]) -> str:
        raise ActivationOutcomeUnconfirmed("index activation outcome unconfirmed")

    try:
        with pytest.raises(ActivationOutcomeUnconfirmed):
            worker.one(prepare, loaded)
        assert len(queue.claims) == 1
        assert queue.receipts == []
    finally:
        worker.close()


def test_ready_ack_transport_failure_keeps_same_lease_for_ack_only_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = Queue()
    attempts: list[dict[str, Any]] = []
    sleeps: list[float] = []
    job: dict[str, Any] | None = None
    recover = False

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal job
        if request.url.path.endswith("/ack"):
            body = json.loads(request.content)
            attempts.append(body)
            if not recover:
                raise httpx.ProxyError("fixture transport failure")
            return queue.handle(request)
        if recover:
            assert job is not None
            data = json.loads(request.content)
            assert data["ack_recovery_protocol"] == "native-knowledge-ack-recovery-v1"
            return httpx.Response(200, json={"job": {**job, "ack_only": True}})
        response = queue.handle(request)
        job = response.json()["job"]
        return response

    monkeypatch.setattr("publication_worker.time.sleep", sleeps.append)
    worker = Worker(
        "https://site.test/jobs",
        "fixture",
        "fixture",
        "mac",
        600,
        recipe=RECIPE,
        transport=httpx.MockTransport(handle),
    )
    try:
        with pytest.raises(httpx.ProxyError):
            worker.one(lambda _: "build1", loaded)
        assert len(attempts) == 3
        assert all(row == attempts[0] and row["status"] == "ready" for row in attempts)
        assert sleeps == [1, 2]
        assert queue.receipts == [] and queue.epoch == 1
        recover = True
        worker.close()
        worker = Worker(
            "https://site.test/jobs",
            "fixture",
            "fixture",
            "mac",
            600,
            recipe=RECIPE,
            transport=httpx.MockTransport(handle),
        )
        assert worker.one(
            lambda _: pytest.fail("ACK recovery must not rebuild"), loaded
        )
        assert queue.ready and queue.epoch == 1
        assert queue.receipts[-1]["preparation_complete"] is False
    finally:
        worker.close()


def test_loaded_transport_failure_after_publish_never_sends_failed_ack() -> None:
    queue = Queue()
    worker = queue.worker()
    reads = 0

    def read() -> dict[str, Any]:
        nonlocal reads
        reads += 1
        if reads > 1:
            raise httpx.ProxyError("post-activation readback unavailable")
        return loaded()

    try:
        with pytest.raises(httpx.ProxyError):
            worker.one(lambda _: "build1", read)
        assert queue.receipts == [] and queue.epoch == 1
    finally:
        worker.close()


def test_confirmed_publish_survives_completion_progress_failure() -> None:
    queue = Queue()
    worker = queue.worker()

    def prepare(_manifest: dict[str, Any]) -> str:
        # Mirrors the real publish return seam before completion progress output.
        worker.publication_confirmed()
        raise BrokenPipeError("completion progress sink unavailable")

    try:
        with pytest.raises(BrokenPipeError):
            worker.one(prepare, loaded)
        assert queue.receipts == [] and queue.epoch == 1
    finally:
        worker.close()


def test_committed_ack_with_lost_response_is_never_replaced_by_failed_ack() -> None:
    queue = Queue()
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path.endswith("/ack"):
            calls += 1
            if calls == 1:
                queue.handle(request)
                raise httpx.ProxyError("ACK committed before lost response")
            return httpx.Response(409, json={"code": "stale_job"})
        return queue.handle(request)

    worker = Worker(
        "https://site.test/jobs",
        "fixture",
        "fixture",
        "mac",
        600,
        recipe=RECIPE,
        transport=httpx.MockTransport(handle),
    )
    try:
        with pytest.raises(httpx.HTTPStatusError):
            worker.one(lambda _: "build1", loaded)
        assert calls == 2 and len(queue.receipts) == 1
        assert queue.receipts[0]["status"] == "ready" and queue.ready
        assert not worker.one(
            lambda _: pytest.fail("already ACKed must not rebuild"), loaded
        )
        assert queue.epoch == 1
    finally:
        worker.close()


@pytest.mark.parametrize("status", [400, 409])
def test_ready_ack_explicit_rejection_does_not_retry_or_cancel_lease(
    status: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = Queue()
    attempts: list[dict[str, Any]] = []
    sleeps: list[float] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ack"):
            attempts.append(json.loads(request.content))
            return httpx.Response(status)
        return queue.handle(request)

    monkeypatch.setattr("publication_worker.time.sleep", sleeps.append)
    worker = Worker(
        "https://site.test/jobs",
        "fixture",
        "fixture",
        "mac",
        600,
        recipe=RECIPE,
        transport=httpx.MockTransport(handle),
    )
    try:
        with pytest.raises(httpx.HTTPStatusError):
            worker.one(lambda _: "build1", loaded)
        assert len(attempts) == 1 and attempts[0]["status"] == "ready"
        assert sleeps == [] and queue.receipts == []
    finally:
        worker.close()


def test_ack_retry_never_runs_past_original_lease(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = Queue()
    clock = [1000.0]
    attempts: list[str] = []
    sleeps: list[float] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ack"):
            attempts.append("ready")
            clock[0] += 2
            raise httpx.ProxyError("reply unavailable at lease expiry")
        job = queue.handle(request).json()["job"]
        job["lease_expires_at"] = 1002
        return httpx.Response(200, json={"job": job})

    monkeypatch.setattr("publication_worker.time.time", lambda: clock[0])
    monkeypatch.setattr("publication_worker.time.sleep", sleeps.append)
    worker = Worker(
        "https://site.test/jobs",
        "fixture",
        "fixture",
        "mac",
        600,
        recipe=RECIPE,
        transport=httpx.MockTransport(handle),
    )
    try:
        with pytest.raises(RuntimeError, match="expires before ACK retry"):
            worker.one(lambda _: "build1", loaded)
        assert attempts == ["ready"] and sleeps == [] and queue.receipts == []
    finally:
        worker.close()


@pytest.mark.parametrize("case", ["valid", "bad_manifest", "occupied_slot"])
def test_retry_exhaustion_retains_only_one_validated_review_build(
    tmp_path: Path, case: str
) -> None:
    queue = Queue()
    worker = queue.worker()
    index_dir = tmp_path / "index"
    review = index_dir / "publication-review-builds"
    if case == "occupied_slot":
        review.mkdir(parents=True, mode=0o700)
        (review / "prior-evidence").write_text("keep")

    def prepare(_manifest: dict[str, Any]) -> str:
        activation = worker.activation()
        version = "20261024T100100Z"
        directory = index_dir / "builds" / version
        directory.mkdir(parents=True)
        record_build(index_dir, directory)
        meta = {
            "version": version,
            "source_revision": activation["source_revision"],
            "model_identity_revision": "fixture-identity-1",
            "recipe_revision": activation["recipe_revision"],
            "serving_revision": activation["serving_revision"],
            "activation_epoch": str(activation["epoch"]),
        }
        with sqlite3.connect(directory / "index.sqlite") as db:
            db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.executemany("INSERT INTO meta VALUES (?, ?)", meta.items())
        with (directory / "index.sqlite").open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        identity = {
            **meta,
            "activation_epoch": activation["epoch"],
            "job_id": activation["job_id"],
            "sha256": digest,
        }
        manifest = {
            **identity,
            "file": {"name": "index.sqlite", "sha256": digest},
        }
        if case == "bad_manifest":
            manifest["source_revision"] = "different-source"
        (directory / "manifest.json").write_text(json.dumps(manifest))
        raise NativeVerificationRejected("retry_exhausted", 503, False, identity)

    try:
        with pytest.raises(NativeVerificationRejected):
            run_job(worker, prepare, loaded, index_dir)
    finally:
        worker.close()
    assert queue.receipts[-1]["status"] == "failed"
    assert not (index_dir / "publication-worker-pending.json").exists()
    assert not list((index_dir / "builds").iterdir())
    if case == "valid":
        retained = review / "20261024T100100Z"
        assert (retained / "index.sqlite").is_file()
        marker = json.loads((retained / ".publication-review.json").read_text())
        assert marker["job_id"] == queue.receipts[-1]["job_id"]
        assert marker["activation_epoch"] == queue.receipts[-1]["activation_epoch"]
        assert marker["usage"].startswith("review only")
    elif case == "occupied_slot":
        assert (review / "prior-evidence").read_text() == "keep"
    else:
        assert not review.exists()


def test_unsupported_manifest_with_valid_claim_is_acknowledged_as_failed() -> None:
    queue = Queue()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ack"):
            receipt = json.loads(request.content)
            identity = {
                "job_id": "job-" + queue.recipe,
                "lease_token": "lease",
                "source_revision": queue.source["source_revision"],
                "model_identity_revision": "fixture-identity-1",
                "recipe_revision": queue.recipe,
                "activation_epoch": queue.epoch,
            }
            if (
                any(receipt.get(key) != value for key, value in identity.items())
                or type(receipt.get("activation_epoch")) is not int
                or queue.epoch < 1
            ):
                return httpx.Response(409, json={"code": "stale_job"})
        response = queue.handle(request)
        if request.url.path.endswith("/claim"):
            body = response.json()
            body["job"]["manifest"]["schema_version"] = 2
            return httpx.Response(200, json=body)
        return response

    worker = Worker(
        "https://site.test/jobs",
        "fixture",
        "fixture",
        "mac",
        600,
        recipe=RECIPE,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(PublicationUnavailable, match="unsupported"):
        worker.one(lambda _: "unused", loaded)
    assert queue.receipts[-1]["status"] == "failed"
    assert queue.receipts[-1]["source_revision"] == queue.source["source_revision"]
    worker.close()


def test_leased_compiler_retries_only_identification_503_and_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[str] = []
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if len(requests) == 1:
            return httpx.Response(503)
        if len(requests) == 2:
            raise httpx.ReadTimeout("private fixture", request=request)
        return httpx.Response(
            200, json={"models": [{"model": "A", "status": "published"}]}
        )

    client = PublicationClient(
        "https://site.test",
        httpx.MockTransport(handle),
        identify_deadline=int(time.time()) + 300,
    )
    try:
        assert client.identify(["A"]) == {"a": "published"}
        assert requests == ["/wp-json/linker/v1/publication/identify"] * 3
        assert sleeps == [1.0, 2.0]
    finally:
        client.close()


@pytest.mark.parametrize(
    ("method", "path", "status", "deadline", "expected_calls"),
    [
        ("POST", "/identify", 404, True, 1),
        ("POST", "/identify", 409, True, 1),
        ("POST", "/identify", 503, True, 3),
        ("POST", "/identify", 503, False, 1),
        ("POST", "/validate", 503, True, 1),
        ("GET", "/manifest", 503, True, 1),
    ],
)
def test_identification_retry_scope_and_failure_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    status: int,
    deadline: bool,
    expected_calls: int,
) -> None:
    calls: list[str] = []
    events: list[str] = []
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monkeypatch.setattr(
        syslog, "syslog", lambda _priority, message: events.append(message)
    )

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(status, json={"private": "do-not-log"})

    client = PublicationClient(
        "https://secret-site.test",
        httpx.MockTransport(handle),
        identify_deadline=int(time.time()) + 300 if deadline else None,
    )
    try:
        with pytest.raises(PublicationUnavailable) as failure:
            client._request(method, path, {"private": "do-not-log"})
        assert len(calls) == expected_calls
        report_failure("prepare.build", failure.value)
        assert "cause=HTTPStatusError" in events[-1]
        assert f"http_status={status}" in events[-1]
        assert "do-not-log" not in events[-1] and "secret-site" not in events[-1]
    finally:
        client.close()


def test_identification_transport_diagnostic_does_not_expose_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    calls: list[str] = []
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monkeypatch.setattr(
        syslog, "syslog", lambda _priority, message: events.append(message)
    )

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        raise httpx.ConnectError("private-fixture-detail", request=request)

    client = PublicationClient(
        "https://secret-site.test",
        httpx.MockTransport(handle),
        identify_deadline=int(time.time()) + 300,
    )
    try:
        with pytest.raises(PublicationUnavailable) as failure:
            client.identify_text("private-fixture-content")
        report_failure("prepare.build", failure.value)
        assert len(calls) == 3
        assert "transport=ConnectError" in events[-1]
        assert "private-fixture" not in events[-1] and "secret-site" not in events[-1]
    finally:
        client.close()


@pytest.mark.parametrize("when", ["before", "after_response", "before_retry"])
def test_leased_identification_stops_at_expiry(
    monkeypatch: pytest.MonkeyPatch, when: str
) -> None:
    clock = [1000.0]
    calls: list[str] = []
    monkeypatch.setattr(time, "time", lambda: clock[0])
    monkeypatch.setattr(time, "sleep", lambda _: None)
    expiry = 1001 if when == "before" else 1003

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if when == "after_response":
            clock[0] = 1003.0
            return httpx.Response(200, json={"models": []})
        return httpx.Response(503, headers={"Retry-After": "300"})

    client = PublicationClient(
        "https://site.test", httpx.MockTransport(handle), identify_deadline=expiry
    )
    try:
        with pytest.raises(PublicationUnavailable, match="lease expired"):
            client.identify(["A"])
        assert len(calls) == (0 if when == "before" else 1)
    finally:
        client.close()


def test_leased_identification_batches_independent_windows_and_records_cost(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No cross-window model phrase can be synthesized by batching."""
    payloads: list[dict[str, Any]] = []
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    system_events: list[str] = []
    monkeypatch.setattr(
        syslog, "syslog", lambda _priority, message: system_events.append(message)
    )
    lease = {
        "verify_url": "https://site.test/wp-json/linker/v1/publication/jobs/claim",
        "username": "fixture-worker",
        "password": "fixture-secret",
        "verify_body": {
            "operation": "verify",
            "consumer": "knowledge",
            "job_id": "job",
            "lease_token": "lease",
            "activation_epoch": 7,
            "source_revision": "same-published-source",
            "recipe_revision": RECIPE,
            "model_identity_revision": "opaque-draft-map-v2",
        },
    }

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"].startswith("Basic ")
        body = json.loads(request.content)
        payloads.append(body)
        assert "text" not in body and "operation" not in body
        assert body["lease_token"] == "lease" and body["activation_epoch"] == 7
        if len(payloads) == 1:
            return httpx.Response(503, headers={"Retry-After": "2"})
        # A whole model must occur inside one original window.
        models = (
            [{"model": "MODEL A", "status": "unavailable"}]
            if any("MODEL A" in text for text in body["texts"])
            else []
        )
        return httpx.Response(
            200,
            json={
                "models": models,
                "model_identity_revision": "opaque-draft-map-v2",
                "metrics": {"identity_reads": 1},
            },
        )

    client = PublicationClient(
        "https://site.test",
        httpx.MockTransport(handle),
        identify_deadline=int(time.time()) + 300,
        identify_lease=lease,
    )
    windows = ["MODEL", "A", *(f"original-{n}" for n in range(19))]
    try:
        assert client.identify_texts(windows, "opaque-draft-map-v2") == {}
        assert [len(p["texts"]) for p in payloads] == [20, 20, 1]
        assert payloads[0] == payloads[1]
        assert payloads[1]["texts"] + payloads[2]["texts"] == windows
        assert client.identification["windows"] == 21
        assert client.identification["batches"] == 2
        assert client.identification["attempts"] == 3
        assert client.identification["backoff_seconds"] == 2
        assert client.identification["identity_reads"] == 2
        assert sleeps == [2.0]
        output = capsys.readouterr().out
        events = [json.loads(line) for line in output.splitlines()]
        assert [event["event"] for event in events] == [
            "attempt",
            "backoff",
            "attempt",
            "batch_done",
            "attempt",
            "batch_done",
        ]
        assert events[-1]["batches"] == 2 and events[-1]["attempts"] == 3
        assert "fixture-secret" not in output and "MODEL" not in output
        assert [
            json.loads(line.removeprefix("linker-knowledge-publication "))
            for line in system_events
        ] == events
    finally:
        client.close()


@pytest.mark.parametrize("reply", ["wrong-identity", "revoked"])
def test_leased_batch_never_uses_stale_identity_or_revoked_lease(reply: str) -> None:
    calls: list[httpx.Request] = []
    lease = {
        "verify_url": "https://site.test/wp-json/linker/v1/publication/jobs/claim",
        "username": "fixture",
        "password": "fixture",
        "verify_body": {
            "consumer": "knowledge",
            "job_id": "job",
            "source_revision": "source",
            "recipe_revision": RECIPE,
            "lease_token": "lease",
            "activation_epoch": 1,
            "model_identity_revision": "identity-before-draft-edit",
        },
    }

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return (
            httpx.Response(409, json={"code": "identity_changed"})
            if reply == "revoked"
            else httpx.Response(
                200,
                json={
                    "models": [],
                    "model_identity_revision": "identity-after-draft-edit",
                },
            )
        )

    client = PublicationClient(
        "https://site.test",
        httpx.MockTransport(handle),
        identify_deadline=int(time.time()) + 300,
        identify_lease=lease,
    )
    try:
        with pytest.raises(PublicationUnavailable):
            client.identify_texts(["MODEL-1"], "identity-before-draft-edit")
        assert len(calls) == 1
    finally:
        client.close()


@pytest.mark.parametrize("identity", ["", "draft-only-map-change"])
def test_worker_never_acks_ready_for_missing_or_changed_loaded_identity(
    identity: str,
) -> None:
    queue = Queue()
    worker = queue.worker()
    try:
        with pytest.raises(RuntimeError, match="not loaded"):
            worker.one(
                lambda _: "build1", lambda: loaded(model_identity_revision=identity)
            )
        assert queue.receipts == [] and not queue.ready
    finally:
        worker.client.close()


def test_compiler_batches_original_packed_windows_not_each_authored_part() -> None:
    from index.chunking import Chunk
    from index.publication import _recognized

    # Forty source parts historically fit inside one 16k request. They must
    # still be one original window, rather than two HTTP batches of 20 parts.
    chunks = [
        Chunk(str(i), "a" * 64, 1, "", "text", "", f"original part {i}", "en", 4)
        for i in range(40)
    ]
    payloads: list[dict[str, Any]] = []
    lease = {
        "verify_url": "https://site.test/wp-json/linker/v1/publication/jobs/claim",
        "username": "fixture",
        "password": "fixture",
        "verify_body": {
            "consumer": "knowledge",
            "job_id": "job",
            "source_revision": "source",
            "recipe_revision": RECIPE,
            "lease_token": "lease",
            "activation_epoch": 1,
            "model_identity_revision": "identity",
        },
    }

    def handle(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content))
        return httpx.Response(
            200, json={"models": [], "model_identity_revision": "identity"}
        )

    client = PublicationClient(
        "https://site.test",
        httpx.MockTransport(handle),
        identify_deadline=int(time.time()) + 300,
        identify_lease=lease,
    )
    try:
        assert _recognized(chunks, client, "identity") == {}
        assert len(payloads) == 1 and len(payloads[0]["texts"]) == 1
        assert all(f"original part {i}" in payloads[0]["texts"][0] for i in range(40))
        assert client.identification["windows"] == 1
    finally:
        client.close()
