"""The real Trina reference facts need current Woo source and PDF permission.

The reference's synthetic Woo identity is never a saleable candidate. These
HTTP tests use the existing product, Munich PVGIS and LoD2 fixtures; no model,
network authority, copied reference product facts or production write is used.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, NoReturn

import pytest
from conftest import TRIFTSTRASSE_5, publication_manifest
from fastapi.testclient import TestClient

from linker_engine.publication import Publication

INPUT = {"plz": "80538", "annual_kwh": 5000, "pv_kwp": 10, "phase": 3}
COMMERCIAL = {
    "plz": "80538",
    "grid_connection_kva": 100,
    "annual_kwh": 150000,
    "goals": ["self_consumption"],
}
POLYGON = [
    [11.58836, 48.14024],
    [11.58850, 48.14024],
    [11.58850, 48.14030],
    [11.58836, 48.14030],
]
OPERATIONS = [
    ("/design/residential", INPUT),
    (
        "/roof/outline",
        {
            "plz": "80538",
            "location": {
                "latitude": TRIFTSTRASSE_5[0],
                "longitude": TRIFTSTRASSE_5[1],
            },
        },
    ),
    ("/roof/pack", {"polygon": POLYGON, "tilt_deg": 30, "azimuth_deg": 180}),
]


def withdraw(data: dict[str, Any], case: str) -> None:
    reference = next(p for p in data["products"] if p.get("engineering_role"))
    canonical = reference["product_id"]
    document = next(d for d in data["documents"] if canonical in d["product_ids"])
    if case == "product_draft":
        data["products"].remove(reference)
    elif case == "reference_revision":
        reference["product_revision"] = "a" * 64
    elif case == "role_removed":
        reference.pop("engineering_role")
    elif case == "document_withdrawn":
        data["documents"].remove(document)
    elif case == "association_removed":
        document["product_ids"].remove(canonical)
    elif case == "same_url_version":
        document["document_revision"] = "b" * 64
    elif case == "same_url_bytes":
        document["blob_sha256"] = "c" * 64
    else:
        raise AssertionError(case)


def never_calculate(*args: Any, **kwargs: Any) -> NoReturn:
    raise AssertionError("unpermitted reference facts must not reach calculation")


@pytest.mark.parametrize(("path", "input_"), OPERATIONS)
def test_reference_scope_carries_source_and_all_pdfs(
    client: TestClient, path: str, input_: dict[str, Any]
) -> None:
    response = client.post(path, json=input_)
    assert response.status_code == 200, response.text
    scope = response.json()["publication"]
    assert scope["engineering_contract"] == 2
    assert len(scope["reference_inputs"]) == 1
    reference = scope["reference_inputs"][0]
    assert reference["reference_input_id"] == "mat_trina_solar_tsm_460neg9r_28"
    assert reference["reference_revision"] == reference["product_revision"]
    assert {
        "product_id": reference["product_id"],
        "product_revision": reference["product_revision"],
    } in scope["products"]
    evidence = [
        d for d in scope["documents"] if d["product_id"] == reference["product_id"]
    ]
    assert len(evidence) == 2  # Both real EN/DE reference PDFs are output evidence.
    assert all(len(d["blob_sha256"]) == 64 for d in evidence)
    if path == "/design/residential":
        body = response.json()
        assert all(
            c["product"]["id"] != reference["product_id"]
            for c in body["candidates"]["inverters"]
        )
        assert body["selected"]["strings"]["module_wp"] == 460
    else:
        assert len(scope["products"]) == 1  # No unrelated saleable dependency.


@pytest.mark.parametrize(("path", "input_"), OPERATIONS)
@pytest.mark.parametrize(
    "case",
    [
        "product_draft",
        "reference_revision",
        "role_removed",
        "document_withdrawn",
        "association_removed",
        "same_url_version",
        "same_url_bytes",
    ],
)
def test_unprepared_reference_fails_before_affected_calculation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    input_: dict[str, Any],
    case: str,
) -> None:
    def current(self: Publication) -> dict[str, Any]:
        data = publication_manifest(self.feed)
        withdraw(data, case)
        return data

    monkeypatch.setattr(Publication, "read", current)
    monkeypatch.setattr("linker_engine.residential.design", never_calculate)
    monkeypatch.setattr(
        "linker_engine.roof.service.RoofService.outline", never_calculate
    )
    monkeypatch.setattr("linker_engine.roof.service.pack_drawn", never_calculate)
    response = client.post(path, json=input_)
    assert response.status_code == 503, response.text
    assert response.json()["detail"]["error"] == "publication_unavailable"
    assert response.json()["detail"]["reason"] == "reference_evidence_unavailable"
    assert "Trina" not in response.text and "240831" not in response.text


@pytest.mark.parametrize(("path", "input_"), OPERATIONS)
@pytest.mark.parametrize(
    "case", ["product_draft", "association_removed", "same_url_bytes"]
)
def test_inflight_reference_change_refuses_complete_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    input_: dict[str, Any],
    case: str,
) -> None:
    calls = 0

    def current(self: Publication) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        data = publication_manifest(self.feed)
        if calls > 1:
            withdraw(data, case)
        return data

    monkeypatch.setattr(Publication, "read", current)
    response = client.post(path, json=input_)
    assert calls == 2
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["error"] == "publication_changed"
    assert "module_wp" not in response.text and "publication" not in response.json()


def test_withdrawn_reference_does_not_block_unused_commercial_or_retrofit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = client.post("/design/residential", json=INPUT).json()
    existing = first["selected"]["inverter"]["model"]

    def current(self: Publication) -> dict[str, Any]:
        data = publication_manifest(self.feed)
        withdraw(data, "document_withdrawn")
        return data

    monkeypatch.setattr(Publication, "read", current)
    for path, input_ in [
        ("/design/commercial", COMMERCIAL),
        ("/design/residential", {**INPUT, "existing_inverter": existing}),
    ]:
        response = client.post(path, json=input_)
        assert response.status_code == 200, response.text
        assert response.json()["publication"]["reference_inputs"] == []
        assert 90000001 not in {
            p["product_id"] for p in response.json()["publication"]["products"]
        }


def test_prepared_readback_only_confirms_the_valid_reference(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "reference-readback-test")
    headers = {"X-Linker-Service-Token": "reference-readback-test"}
    first = client.get("/resource/version?ready=1", headers=headers)
    assert first.status_code == 200
    prepared = first.json()["prepared_products"]
    assert 90000001 in {p["product_id"] for p in prepared}

    def current(self: Publication) -> dict[str, Any]:
        data = publication_manifest(self.feed)
        withdraw(data, "same_url_version")
        return data

    monkeypatch.setattr(Publication, "read", current)
    second = client.get("/resource/version?ready=1", headers=headers)
    assert second.status_code == 200
    assert second.json()["prepared_products"] == [
        p for p in prepared if p["product_id"] != 90000001
    ]


@pytest.mark.parametrize("path", ["/selection/validate", "/report/pdf"])
@pytest.mark.parametrize(
    "proof", ["old_contract", "missing_reference", "missing_document"]
)
def test_saved_receipt_needs_complete_reference_proof_without_recomputation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    path: str,
    proof: str,
) -> None:
    first = client.post("/design/residential", json=INPUT).json()
    receipt = tmp_path / "cache" / "private" / "selections.sqlite"
    with sqlite3.connect(receipt) as database:
        row = database.execute("SELECT result FROM selections").fetchone()
        assert row is not None
        result = json.loads(row[0])
        scope = result["publication"]
        if proof == "old_contract":
            scope.pop("engineering_contract")
        elif proof == "missing_reference":
            scope["reference_inputs"] = []
        else:
            scope["documents"] = [
                d for d in scope["documents"] if d["product_id"] != 90000001
            ]
        database.execute("UPDATE selections SET result=?", (json.dumps(result),))
    monkeypatch.setattr("linker_engine.residential.design", never_calculate)
    monkeypatch.setattr("linker_engine.pdf.render", never_calculate)
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "reference-receipt-test")
    response = client.post(
        path,
        json={
            **({"kind": "residential"} if path == "/selection/validate" else {}),
            "input": INPUT,
            "selection_fingerprint": first["selection_fingerprint"],
        },
        headers={"X-Linker-Service-Token": "reference-receipt-test"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["error"] == "publication_changed"


@pytest.mark.parametrize("path", ["/selection/validate", "/report/pdf"])
@pytest.mark.parametrize(
    "case", ["product_draft", "document_withdrawn", "same_url_bytes"]
)
def test_current_reference_withdrawal_closes_confirmed_actions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, path: str, case: str
) -> None:
    first = client.post("/design/residential", json=INPUT).json()

    def current(self: Publication) -> dict[str, Any]:
        data = publication_manifest(self.feed)
        withdraw(data, case)
        return data

    monkeypatch.setattr(Publication, "read", current)
    monkeypatch.setattr("linker_engine.residential.design", never_calculate)
    monkeypatch.setattr("linker_engine.pdf.render", never_calculate)
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "reference-receipt-test")
    response = client.post(
        path,
        json={
            **({"kind": "residential"} if path == "/selection/validate" else {}),
            "input": INPUT,
            "selection_fingerprint": first["selection_fingerprint"],
        },
        headers={"X-Linker-Service-Token": "reference-receipt-test"},
    )
    assert response.status_code == 409


def test_reference_bytes_replaced_during_pdf_render_refuses_bytes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = client.post("/design/residential", json=INPUT).json()
    rendered = False

    def render(*args: Any, **kwargs: Any) -> bytes:
        nonlocal rendered
        rendered = True
        return b"%PDF-never-release"

    def current(self: Publication) -> dict[str, Any]:
        data = publication_manifest(self.feed)
        if rendered:
            withdraw(data, "same_url_bytes")
        return data

    monkeypatch.setattr("linker_engine.pdf.render", render)
    monkeypatch.setattr(Publication, "read", current)
    response = client.post(
        "/report/pdf",
        json={"input": INPUT, "selection_fingerprint": first["selection_fingerprint"]},
    )
    assert rendered
    assert response.status_code == 409
    assert not response.content.startswith(b"%PDF")


@pytest.mark.parametrize("reference", ["absent", "unversioned"])
def test_missing_reference_can_load_a_generation_without_granting_permission(
    client: TestClient, tmp_path: Path, reference: str
) -> None:
    # Services load lazily. Alter this isolated generated feed before first use.
    feed_path = tmp_path / "published-feed.json"
    feed = json.loads(feed_path.read_text())
    if reference == "absent":
        feed["overlay"] = []
    else:
        for field in ("canonical_product_id", "product_revision", "reference_revision"):
            feed["overlay"][0].pop(field)
    feed_path.write_text(json.dumps(feed))
    commercial = client.post("/design/commercial", json=COMMERCIAL)
    assert commercial.status_code == 200, commercial.text
    assert commercial.json()["publication"]["reference_inputs"] == []
    for path, input_ in OPERATIONS:
        response = client.post(path, json=input_)
        assert response.status_code == 503, response.text
        assert response.json()["detail"]["reason"] == "reference_evidence_unavailable"


def test_unbound_reference_citation_is_not_authorized_by_another_product(
    client: TestClient, tmp_path: Path
) -> None:
    feed_path = tmp_path / "published-feed.json"
    feed = json.loads(feed_path.read_text())
    feed["overlay"][0]["figures"]["voc_v"]["citation"]["url"] = feed["products"][0][
        "documents"
    ][0]["url"]
    feed_path.write_text(json.dumps(feed))
    response = client.post("/design/residential", json=INPUT)
    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == "reference_evidence_unavailable"


def test_reference_source_cannot_enter_saleable_candidates_even_in_a_bad_feed(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feed_path = tmp_path / "published-feed.json"
    feed = json.loads(feed_path.read_text())
    product = next(p for p in feed["products"] if p["device_class"] == "inverters")
    original_id = product["id"]
    # Simulate a producer accidentally using the Woo reference as a candidate's
    # authority. The current role and reference identity still exclude it.
    product["canonical_product_id"] = feed["overlay"][0]["canonical_product_id"]
    product["product_revision"] = feed["overlay"][0]["product_revision"]
    feed_path.write_text(json.dumps(feed))

    def current(self: Publication) -> dict[str, Any]:
        data = publication_manifest(self.feed)
        # Woo has one canonical row, independent of the malformed feed entry.
        data["products"] = list({p["product_id"]: p for p in data["products"]}.values())
        return data

    monkeypatch.setattr(Publication, "read", current)
    response = client.post("/design/residential", json=INPUT)
    assert response.status_code == 200, response.text
    candidates = response.json()["candidates"]
    assert original_id not in {
        c["product"]["id"] for c in candidates["inverters"] + candidates["excluded"]
    }


@pytest.mark.parametrize(
    "origin", ["http://reference.test", "http://unrelated.invalid"]
)
def test_reference_url_mapping_requires_the_configured_authority_origin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv(
        "LINKER_PUBLICATION_URL",
        "http://reference.test/wp-json/linker/v1/publication/manifest",
    )

    def current(self: Publication) -> dict[str, Any]:
        data = publication_manifest(self.feed)
        for document in data["documents"]:
            if 90000001 in document["product_ids"]:
                document["url"] = document["url"].replace(
                    "https://de-linker.com", origin
                )
                document["aliases"] = [document["url"]]
        return data

    monkeypatch.setattr(Publication, "read", current)
    response = client.post("/design/residential", json=INPUT)
    assert response.status_code == (200 if origin == "http://reference.test" else 503)
