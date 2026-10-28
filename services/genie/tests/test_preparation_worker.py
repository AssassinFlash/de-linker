"""Recipe-aware preparation receipts preserve coverage and actual loaded identity."""

from __future__ import annotations

import json
import syslog
from typing import Any

import httpx
import pytest

from linker_genie.preparation import RUNTIME_SERVING_REVISION
from linker_genie.publication import PublicationUnavailable
from publication_worker import Worker

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
