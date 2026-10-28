"""Recipe-aware preparation receipts preserve coverage and actual loaded identity."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import syslog
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from linker_genie.preparation import RUNTIME_SERVING_REVISION
from linker_genie.publication import PublicationClient, PublicationUnavailable
from publication_worker import Worker, record_build, report_failure, run_job
from publish_index import ActivationOutcomeUnconfirmed, NativeVerificationRejected

RECIPE = "a" * 64


@pytest.fixture(autouse=True)
def no_real_system_log(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(syslog, "syslog", lambda *_args: None)


def source(revision: str = "source-1") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source_revision": revision,
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
            actual = data.get("loaded_receipt") or {}
            if self.ready and (
                data.get("loaded_unavailable")
                or actual.get("index_version") != self.receipts[-1]["index_version"]
                or actual.get("activation_epoch")
                != self.receipts[-1]["activation_epoch"]
                or actual.get("products") != self.receipts[-1]["prepared_products"]
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
    assert queue.receipts[-1]["status"] == "failed"
    assert queue.receipts[-1]["materialization_complete"] is False
    assert queue.receipts[-1]["prepared_products"] == []
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
    assert queue.receipts[-1]["status"] == "failed"
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
