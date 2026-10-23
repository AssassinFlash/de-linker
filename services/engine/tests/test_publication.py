"""Woo withdrawal against the real engineering fixture, without network/models."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from conftest import publication_manifest
from fastapi.testclient import TestClient

from linker_engine.publication import Publication, PublicationUnavailable

INPUT = {"plz": "80538", "annual_kwh": 5000, "pv_kwp": 10, "phase": 3}


def ids(value: Any) -> set[int]:
    if isinstance(value, dict):
        found = {value["id"]} if isinstance(value.get("id"), int) else set()
        return found | set().union(*(ids(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(ids(v) for v in value))
    return set()


@pytest.mark.parametrize("mode", ["off", "enforce"])
def test_withdrawal_before_feed_sync(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path, mode: str
) -> None:
    monkeypatch.setenv("LINKER_ENGINE_GATE_MODE", mode)
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "test-service")
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(tmp_path))
    withdrawn: set[int] = set()

    def current(self):
        data = publication_manifest(self.feed)
        withdrawn.update(
            p["id"] for p in self.feed["products"] if p["brand"] == "EcoFlow"
        )
        data["products"] = [
            p for p in data["products"] if p["product_id"] not in withdrawn
        ]
        return data

    monkeypatch.setattr(Publication, "read", current)
    headers = {
        "X-Linker-Service-Token": "test-service",
        "X-Linker-Resource-Subject": "a" * 64,
    }
    result = client.post("/design/residential", json=INPUT, headers=headers)
    assert result.status_code == 200, result.text
    assert withdrawn and ids(result.json()).isdisjoint(withdrawn)
    assert not withdrawn.intersection(
        p["product_id"] for p in result.json()["publication"]["products"]
    )


def test_inflight_withdrawal_invalidates_every_candidate(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def current(self):
        nonlocal calls
        calls += 1
        data = publication_manifest(self.feed)
        if calls > 1:
            data["products"] = data["products"][1:]
        return data

    monkeypatch.setattr(Publication, "read", current)
    response = client.post("/design/residential", json=INPUT)
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "publication_changed"


def test_unready_new_product_does_not_close_prepared_products(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def current(self):
        data = publication_manifest(self.feed)
        data["source_revision"] = "f" * 64
        data["products"].append(
            {
                "product_id": 99999999,
                "product_revision": "a" * 64,
                "documents": [],
                "ready": {"engineering": False},
            }
        )
        return data

    monkeypatch.setattr(Publication, "read", current)
    response = client.post("/design/residential", json=INPUT)
    assert response.status_code == 200
    assert response.json()["selected"] is not None
    assert 99999999 not in ids(response.json())


def test_empty_current_set_is_normal_no_candidate(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        Publication,
        "read",
        lambda self: {
            **publication_manifest(self.feed),
            "products": [],
            "documents": [],
        },
    )
    result = client.post("/design/residential", json=INPUT)
    assert result.status_code == 200
    assert result.json()["status"] == "no_candidate"


def test_source_failure_closes_current_work(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(self):
        raise PublicationUnavailable("synthetic failure")

    monkeypatch.setattr(Publication, "read", unavailable)
    assert client.post("/design/residential", json=INPUT).status_code == 503


@pytest.mark.parametrize("field", ["battery_id", "inverter_id"])
def test_explicit_old_id_never_silently_replaces(
    client: TestClient, field: str
) -> None:
    reply = client.post("/design/residential", json={**INPUT, field: 99999999})
    assert reply.status_code == 422
    assert reply.json()["detail"]["field"] == field


def test_pdf_and_trusted_selection_require_confirmed_result(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = client.post("/design/residential", json=INPUT).json()
    proof = first["selection_fingerprint"]
    assert len(proof) == 64
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "selection-test")
    payload = {"kind": "residential", "input": INPUT, "selection_fingerprint": proof}
    assert client.post("/selection/validate", json=payload).status_code == 401
    verified = client.post(
        "/selection/validate",
        json=payload,
        headers={"X-Linker-Service-Token": "selection-test"},
    )
    assert verified.status_code == 200
    assert verified.json()["selected"]["lines"] == first["selected"]["lines"]
    assert client.post("/report/pdf", json={"input": INPUT}).status_code == 422
    assert (
        client.post(
            "/report/pdf", json={"input": INPUT, "selection_fingerprint": "0" * 64}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/report/pdf",
            json={
                "input": {**INPUT, "annual_kwh": 6000},
                "selection_fingerprint": proof,
            },
        ).status_code
        == 409
    )
    selected = first["selected"]["inverter"]["id"]

    def withdrawn(self):
        data = publication_manifest(self.feed)
        data["products"] = [p for p in data["products"] if p["product_id"] != selected]
        return data

    monkeypatch.setattr(Publication, "read", withdrawn)
    assert (
        client.post(
            "/report/pdf", json={"input": INPUT, "selection_fingerprint": proof}
        ).status_code
        == 409
    )


def test_replaced_document_excludes_only_dependents(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    affected: set[int] = set()

    def current(self):
        data = copy.deepcopy(publication_manifest(self.feed))
        changed = data["documents"][0]
        affected.update(changed["product_ids"])
        changed["document_revision"] = "c" * 64
        return data

    monkeypatch.setattr(Publication, "read", current)
    result = client.post("/design/residential", json=INPUT)
    assert result.status_code == 200
    assert affected.isdisjoint(
        p["product_id"] for p in result.json()["publication"]["products"]
    )


def test_confirm_pdf_and_save_do_not_recompute(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("LINKER_ENGINE_GATE_MODE", "enforce")
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "confirmed-test")
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(tmp_path))
    headers = {
        "X-Linker-Service-Token": "confirmed-test",
        "X-Linker-Resource-Subject": "b" * 64,
    }
    design = client.post("/design/residential", json=INPUT, headers=headers)
    assert design.status_code == 200
    result = design.json()

    def never_recompute(*args, **kwargs):
        raise AssertionError("a confirmed result must never silently reselect")

    monkeypatch.setattr("linker_engine.residential.design", never_recompute)
    payload = {
        "kind": "residential",
        "input": INPUT,
        "selection_fingerprint": result["selection_fingerprint"],
    }
    for _ in range(2):
        reply = client.post("/selection/validate", json=payload, headers=headers)
        assert reply.status_code == 200
        assert reply.json()["selected"] == result["selected"]
    pdf = client.post(
        "/report/pdf",
        json={"input": INPUT, "selection_fingerprint": result["selection_fingerprint"]},
        headers=headers,
    )
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
