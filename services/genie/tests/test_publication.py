"""Real SQLite retrieval and HTTP permission changes, with no provider calls."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from test_chunking import Words

from index import corpus, store
from index.chunking import Chunk, DocumentMeta, chunk_document
from index.corpus import DocumentRow
from index.extract import Block, Page
from index.publication import applicability, scope_proofs
from index.publication import inventory as publication_inventory
from linker_genie.knowledge import KnowledgeSearch
from linker_genie.preparation import RUNTIME_SERVING_REVISION
from linker_genie.publication import (
    PublicationChanged,
    PublicationClient,
    PublicationUnavailable,
    Snapshot,
)
from linker_genie.retrieval import DocumentIndex
from publication_worker import Worker

SHA = "a" * 64


def manifest() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source_revision": "source-1",
        "model_identity_revision": "fixture-identity-1",
        "compatibility_revision": "compat-1",
        "products": [
            {
                "product_id": pid,
                "product_revision": f"p{pid}",
                "model": f"MODEL-{pid}",
                "published_locale_ids": [pid, pid + 100],
                "locale_product_ids": {"en": pid, "de": pid + 100},
                "documents": ["doc"],
                "ready": {"knowledge": True},
            }
            for pid in [1, 2]
        ],
        "documents": [
            {
                "document_id": "doc",
                "document_revision": "doc-1",
                "blob_sha256": SHA,
                "url": "https://site.test/shared.pdf",
                "aliases": ["https://site.test/alias.pdf"],
                "product_ids": [1, 2],
                "title": "Shared manual",
                "type": "datasheet",
                "lang": "en",
            }
        ],
    }


def authority(
    raw: dict[str, Any],
    *,
    valid: bool = True,
    extra_models: dict[str, str] | None = None,
) -> PublicationClient:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/manifest"):
            return httpx.Response(200, json=raw)
        if request.url.path.endswith("/identify"):
            import json

            supplied = json.loads(request.content)
            known = {
                **{
                    p["model"]: "unavailable"
                    if p.get("engineering_role") == "reference_pv_module"
                    else "published"
                    for p in raw["products"]
                },
                "MODEL-3": "unavailable",
                **(extra_models or {}),
            }
            models = supplied.get("models", [])
            if "text" in supplied:
                import re

                models = [
                    m
                    for m in known
                    if re.search(
                        r"(?<![^\W_])" + re.escape(m) + r"(?![^\W_])",
                        re.sub(r"\s+", " ", supplied["text"]),
                        re.IGNORECASE,
                    )
                ]
            return httpx.Response(
                200,
                json={
                    "model_identity_revision": raw.get("model_identity_revision", ""),
                    "models": [
                        {
                            "model": m,
                            "status": known.get(m, "unknown"),
                        }
                        for m in models
                    ],
                },
            )
        return httpx.Response(200, json={"valid": valid})

    return PublicationClient("https://site.test", httpx.MockTransport(handle))


def identification_lease(verify_url: str) -> dict[str, Any]:
    return {
        "verify_url": verify_url,
        "username": "fixture-worker",
        "password": "fixture-secret",
        "verify_body": {
            "consumer": "knowledge",
            "job_id": "fixture-job",
            "source_revision": "source",
            "recipe_revision": "recipe",
            "lease_token": "fixture-lease",
            "activation_epoch": 1,
            "model_identity_revision": "identity",
        },
    }


@pytest.mark.parametrize(
    "base_url,verify_url",
    [
        (
            "https://other.test",
            "https://site.test/wp-json/linker/v1/publication/jobs/claim",
        ),
        (
            "http://site.test",
            "https://site.test/wp-json/linker/v1/publication/jobs/claim",
        ),
        (
            "https://site.test:444",
            "https://site.test/wp-json/linker/v1/publication/jobs/claim",
        ),
        (
            "https://site.test",
            "https://site.test/wp-json/linker/v1/publication/identify",
        ),
    ],
)
def test_leased_batch_rejects_wrong_origin_or_claim_path_before_transport(
    base_url: str, verify_url: str
) -> None:
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, json={"models": [], "model_identity_revision": "identity"}
        )

    client = PublicationClient(
        base_url,
        httpx.MockTransport(handle),
        identify_deadline=int(time.time()) + 300,
        identify_lease=identification_lease(verify_url),
    )
    try:
        with pytest.raises(PublicationUnavailable, match="native lease origin"):
            client.identify_texts(["MODEL-1"], "identity")
        assert calls == []
    finally:
        client.close()


@pytest.mark.parametrize(
    "base_url,verify_origin",
    [
        ("https://SITE.test", "https://site.test:443"),
        ("http://127.0.0.1:8181", "http://127.0.0.1:8181"),
    ],
)
def test_leased_batch_keeps_same_origin_and_effective_default_port(
    base_url: str, verify_origin: str
) -> None:
    bodies: list[dict[str, Any]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/wp-json/linker/v1/publication/identify"
        assert request.headers["authorization"].startswith("Basic ")
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200, json={"models": [], "model_identity_revision": "identity"}
        )

    client = PublicationClient(
        base_url,
        httpx.MockTransport(handle),
        identify_deadline=int(time.time()) + 300,
        identify_lease=identification_lease(
            verify_origin + "/wp-json/linker/v1/publication/jobs/claim"
        ),
    )
    try:
        windows = [f"original-{n}" for n in range(21)]
        assert client.identify_texts(windows, "identity") == {}
        assert [body["texts"] for body in bodies] == [windows[:20], windows[20:]]
    finally:
        client.close()


def test_anonymous_identification_does_not_require_a_lease_origin() -> None:
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert "authorization" not in request.headers
        return httpx.Response(
            200, json={"models": [], "model_identity_revision": "identity"}
        )

    client = PublicationClient("http://site.test", httpx.MockTransport(handle))
    try:
        assert client.identify_text("MODEL-1", expected_revision="identity") == {}
        assert len(calls) == 1
    finally:
        client.close()


@pytest.mark.parametrize(
    "kind,role,language,expected_type,expected_language",
    [
        ("Datasheet", "", "EN", "datasheet", "en"),
        ("Datenblatt", "", "DE", "datasheet", "de"),
        ("Handbuch", "", "EN", "manual", "en"),
        ("Kompatibilität", "", "MUL", "compatibility", "mul"),
        ("Dokument", "quick_guide", "MULTI", "other", "mul"),
        ("certificate", "certificate", "EN/DE", "certificate", "mul"),
        ("certificate", "certificate", "DE/EN", "certificate", "mul"),
        ("manual", "", "", "manual", "und"),
        ("Datasheet", "user_manual", "en", "manual", "en"),
    ],
)
def test_manifest_build_normalizes_metadata_without_changing_woo_source(
    tmp_path: Path,
    kind: str,
    role: str,
    language: str,
    expected_type: str,
    expected_language: str,
) -> None:
    raw = manifest()
    pdf_bytes = b"verified cached PDF fixture"
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    raw["documents"][0].update(
        {"blob_sha256": sha, "type": kind, "role": role, "lang": language}
    )
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    (pdf_dir / f"{sha}.pdf").write_bytes(pdf_bytes)
    out = tmp_path / "inventory.json"
    documents = publication_inventory(
        SimpleNamespace(base="https://site.test"), out, pdf_dir, raw
    )
    assert len(documents) == 1
    assert (documents[0].doc_type, documents[0].lang) == (
        expected_type,
        expected_language,
    )
    assert json.loads(out.read_text())["publication_manifest"] == raw


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("lang", "unknown-language", "unknown Woo document language"),
        ("type", "unknown-purpose", "unknown Woo document purpose"),
    ],
)
def test_manifest_build_rejects_unknown_metadata_before_downloading(
    tmp_path: Path, field: str, value: str, reason: str
) -> None:
    raw = manifest()
    raw["documents"][0][field] = value
    with pytest.raises(ValueError, match=reason):
        publication_inventory(
            SimpleNamespace(base="https://site.test"),
            tmp_path / "inventory.json",
            tmp_path / "pdfs",
            raw,
        )
    assert not (tmp_path / "inventory.json").exists()
    assert not list((tmp_path / "pdfs").iterdir())


@pytest.fixture
def path(tmp_path: Path) -> Path:
    raw = manifest()
    chunks = [
        Chunk("A", SHA, 1, "", "text", "", "MODEL-1 stores nominal energy", "en", 10),
        Chunk("B", SHA, 1, "", "text", "", "MODEL-2 stores battery energy", "en", 10),
        Chunk(
            "AB", SHA, 2, "", "text", "", "MODEL-1 and MODEL-2 energy table", "en", 10
        ),
        Chunk(
            "unknown",
            SHA,
            2,
            "",
            "text",
            "",
            "Generic instructions without proven applicability",
            "en",
            10,
        ),
    ]
    document = DocumentRow(
        SHA,
        ("https://site.test/shared.pdf",),
        "Shared",
        "Gemeinsam",
        (),
        ("MODEL-1", "MODEL-2"),
        "datasheet",
        "en",
        2,
        "indexed",
    )
    source = tmp_path / "corpus"
    corpus.write(
        source,
        corpus.Meta(
            "build1",
            None,
            None,
            "fixture",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {"A": [1], "B": [2], "AB": [1, 2]},
                "chunk_scopes": scope_proofs(chunks, raw, authority(raw)),
            },
        ),
        [document],
        [(1, "MODEL-1"), (2, "MODEL-2")],
        chunks,
    )
    index_path = tmp_path / "index.sqlite"
    store.export(source, index_path)
    return index_path


def test_empty_product_scope_is_empty_not_whole_library(path: Path) -> None:
    index = DocumentIndex(path)
    assert index.scope([999], None) == []
    assert index.search("energy", "en", [], publication=Snapshot.read(manifest())) == []
    assert (
        index.search("energy", "en", [999], publication=Snapshot.read(manifest())) == []
    )


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("neighbours", [False, True])
def test_shared_manual_revocation_filters_fallback_and_same_page_neighbours(
    path: Path, lang: str, neighbours: bool
) -> None:
    raw = manifest()
    raw["products"] = raw["products"][:1]
    raw["documents"][0]["product_ids"] = [1]
    hits = DocumentIndex(path).search(
        "energy", lang, neighbours=neighbours, publication=Snapshot.read(raw)
    )
    assert [h.chunk_id for h in hits] == ["A"]
    assert hits[0].document_id == "doc"
    assert hits[0].document_revision == "doc-1"
    assert hits[0].product_ids == (1,)
    assert hits[0].doc_url == "https://site.test/shared.pdf"
    assert not any("MODEL-2" in h.text for h in hits)


def test_same_sha_another_permission_domain_does_not_authorize_old_chunks(
    path: Path,
) -> None:
    raw = manifest()
    raw["documents"][0]["document_id"] = "private-report-same-bytes"
    raw["documents"][0]["url"] = "https://site.test/private.pdf"
    assert (
        DocumentIndex(path).search("energy", "en", publication=Snapshot.read(raw)) == []
    )


@pytest.mark.parametrize(
    "key,value", [("blob_sha256", "b" * 64), ("document_revision", "doc-2")]
)
def test_same_url_new_content_revokes_loaded_proof(
    path: Path, key: str, value: str
) -> None:
    raw = manifest()
    raw["documents"][0][key] = value
    assert (
        DocumentIndex(path).search("energy", "en", publication=Snapshot.read(raw)) == []
    )


def test_changed_product_revision_excludes_its_loaded_chunks(path: Path) -> None:
    raw = manifest()
    raw["products"][0]["product_revision"] = "changed"
    assert {
        h.chunk_id
        for h in DocumentIndex(path).search(
            "energy", "en", publication=Snapshot.read(raw)
        )
    } == {"B"}


def test_inflight_revocation_discards_search_result(path: Path) -> None:
    search = KnowledgeSearch(
        lambda: DocumentIndex(path), authority(manifest(), valid=False)
    )
    with pytest.raises(PublicationChanged, match="changed"):
        search({"query": "energy", "lang": "en"})


def test_legacy_index_without_applicability_grants_nothing(path: Path) -> None:
    import sqlite3

    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE publication_documents")
    assert (
        DocumentIndex(path).search(
            "energy", "en", publication=Snapshot.read(manifest())
        )
        == []
    )


def test_current_permission_outage_never_uses_last_success() -> None:
    client = PublicationClient(
        "https://site.test", httpx.MockTransport(lambda r: httpx.Response(503))
    )
    with pytest.raises(PublicationUnavailable):
        client.snapshot()


def test_chunk_scope_requires_explicit_model_and_rejects_mixed_withdrawn_or_unknown_codes() -> (
    None
):
    raw = manifest()
    chunks = [
        Chunk(cid, SHA, 1, "", "text", "MODEL-1 MODEL-2", text, "en", 10)
        for cid, text in [
            ("A", "MODEL-1 energy is nominal"),
            ("mixed", "MODEL-1 and MODEL-3 technical table"),
            ("unknown", "MODEL-1 and Z999 energy ratings"),
            ("generic", "Nominal energy ratings and instructions"),
        ]
    ]
    assert applicability(chunks, raw, authority(raw)) == {"A": [1]}


@pytest.mark.parametrize(
    ("quantity", "model_variant"), [("10-min", "10-min-X"), ("30dB", "30dB-X")]
)
def test_engineering_tokens_do_not_become_unknown_models(
    quantity: str, model_variant: str
) -> None:
    raw = manifest()
    text = "| Model | MODEL-1 |\n| Protection | IP65 |\n| Frequency | 50Hz |\n| Power | 10kW |\n| Standard | IEC62109-1 |"
    chunk = Chunk("ratings", SHA, 1, quantity, "table", "", text, "en", 30)
    assert applicability([chunk], raw, authority(raw)) == {"ratings": [1]}
    # A model-like suffix does not inherit a physical quantity's exemption,
    # even when the passage itself also names a current product.
    foreign = Chunk("variant", SHA, 1, model_variant, "table", "", text, "en", 30)
    assert applicability([foreign], raw, authority(raw)) == {}


def test_single_authored_current_scope_propagates_without_using_generated_header() -> (
    None
):
    raw = manifest()
    chunks = [
        Chunk(
            "scope", SHA, 1, "", "text", "MODEL-2", "Instructions for MODEL-1", "en", 10
        ),
        Chunk(
            "rating",
            SHA,
            2,
            "",
            "table",
            "MODEL-2",
            "| Nominal power | 10kW |",
            "en",
            10,
        ),
    ]
    proof = scope_proofs(chunks, raw, authority(raw))
    assert {k: v for k, v in proof["rating"].items() if k != "associations"} == {
        "product_ids": [1],
        "basis": "document_model",
        "model_identity_revision": "fixture-identity-1",
        "source_chunk_ids": ["scope"],
        "document_ids": ["doc"],
    }
    assert proof["scope"]["basis"] == "passage"


@pytest.mark.parametrize("foreign", ["MODEL-3", "Z999"])
def test_mixed_file_cannot_assign_unnamed_parameter_table_to_remaining_product(
    foreign: str,
) -> None:
    raw = manifest()
    chunks = [
        Chunk("scope", SHA, 1, "", "text", "", "Instructions for MODEL-1", "en", 10),
        Chunk(
            "foreign",
            SHA,
            2,
            "",
            "table",
            "",
            f"| Model | {foreign} |\n| Power | 8kW |",
            "en",
            10,
        ),
        Chunk(
            "unnamed",
            SHA,
            3,
            "",
            "table",
            "MODEL-1",
            "| Nominal power | 8kW |",
            "en",
            10,
        ),
        Chunk(
            "scoped",
            SHA,
            4,
            "MODEL-1",
            "text",
            "",
            "Use the isolator before maintenance.",
            "en",
            10,
        ),
    ]
    proof = scope_proofs(chunks, raw, authority(raw))
    assert set(proof) == {"scope", "scoped"}
    assert proof["scoped"]["basis"] == "section"


def test_an_unambiguous_authored_section_can_supply_scope_in_a_mixed_file() -> None:
    raw = manifest()
    chunks = [
        Chunk(
            "A",
            SHA,
            1,
            "Installation",
            "text",
            "",
            "These instructions concern MODEL-1.",
            "en",
            10,
        ),
        Chunk(
            "method",
            SHA,
            1,
            "Installation",
            "text",
            "",
            "Open the isolator before connecting the cables.",
            "en",
            10,
        ),
        Chunk(
            "B",
            SHA,
            2,
            "Other equipment",
            "text",
            "",
            "MODEL-3 nominal power",
            "en",
            10,
        ),
        Chunk(
            "ambiguous",
            SHA,
            2,
            "Other equipment",
            "table",
            "",
            "| Nominal power | 8kW |",
            "en",
            10,
        ),
    ]
    proof = scope_proofs(chunks, raw, authority(raw))
    assert set(proof) == {"A", "method"}
    assert proof["method"]["basis"] == "section_model"
    assert proof["method"]["source_chunk_ids"] == ["A"]


@pytest.mark.parametrize("purpose", ["warranty", "certificate"])
def test_authored_common_terms_do_not_authorize_unnamed_technical_parameters(
    purpose: str,
) -> None:
    raw = manifest()
    raw["documents"][0]["type"] = purpose
    text = (
        "MODEL-1 and MODEL-3 are covered by these Warranty Terms and Conditions."
        if purpose == "warranty"
        else "This certificate refers to the above mentioned products MODEL-1 and MODEL-3."
    )
    chunks = [
        Chunk("declaration", SHA, 1, "", "text", "", text, "en", 20),
        Chunk(
            "terms",
            SHA,
            2,
            "Claims",
            "text",
            "",
            "Keep your proof of purchase when submitting a claim.",
            "en",
            10,
        ),
        Chunk("table", SHA, 2, "", "table", "", "| Nominal power | 8kW |", "en", 10),
        Chunk(
            "technical", SHA, 2, "", "text", "", "The nominal power is 8kW.", "en", 10
        ),
    ]
    proof = scope_proofs(chunks, raw, authority(raw))
    assert set(proof) == {"terms"}
    assert proof["terms"]["product_ids"] == [1]
    assert proof["terms"]["basis"] == "common_terms"
    assert proof["terms"]["source_chunk_ids"] == ["declaration"]


@pytest.mark.parametrize(
    "purpose", ["warranty", "certificate", "Garantie", "Zertifikat"]
)
def test_genuinely_model_free_general_document_uses_explicit_woo_purpose(
    purpose: str,
) -> None:
    raw = manifest()
    raw["documents"][0]["type"] = purpose
    chunks = [
        Chunk(
            "terms",
            SHA,
            1,
            "",
            "text",
            "MODEL-3",
            "The warranty requires proof of purchase.",
            "en",
            10,
        )
    ]
    proof = scope_proofs(chunks, raw, authority(raw))
    assert {k: v for k, v in proof["terms"].items() if k != "associations"} == {
        "product_ids": [1, 2],
        "basis": "woo_document",
        "model_identity_revision": "fixture-identity-1",
        "source_chunk_ids": [],
        "document_ids": ["doc"],
    }
    raw["documents"][0]["type"] = "datasheet"
    assert applicability(chunks, raw, authority(raw)) == {}


def test_certificate_report_and_standard_numbers_are_not_product_models() -> None:
    raw = manifest()
    raw["documents"][0]["type"] = "certificate"
    text = "Registration No.: A3 50696265 0001\nReport No.:\nCN2534ZQ 001\nEN 50549-2:2019+A1\nIEC62109-1\nThis certificate refers to the supplied equipment."
    chunk = Chunk("certificate", SHA, 1, "", "text", "", text, "en", 30)
    assert (
        scope_proofs([chunk], raw, authority(raw))["certificate"]["basis"]
        == "woo_document"
    )


def test_suffix_variant_cannot_borrow_shorter_published_model_scope() -> None:
    raw = manifest()
    chunk = Chunk("suffix", SHA, 1, "", "text", "", "MODEL-10 nominal power", "en", 10)
    assert applicability([chunk], raw, authority(raw)) == {}


def test_multiword_unavailable_model_is_detected_from_original_text_not_code_shape() -> (
    None
):
    raw = manifest()
    chunks = [
        Chunk(
            "A", SHA, 1, "", "text", "", "These instructions concern MODEL-1.", "en", 10
        ),
        Chunk("retired", SHA, 2, "", "text", "", "Retired system.", "en", 10),
        Chunk("unnamed", SHA, 3, "", "table", "", "| Nominal power | 8kW |", "en", 10),
    ]
    assert set(
        applicability(
            chunks, raw, authority(raw, extra_models={"Retired system": "unavailable"})
        )
    ) == {"A"}


def test_reference_module_never_enters_genie_snapshot_index_or_product_scope(
    tmp_path: Path,
) -> None:
    raw = manifest()
    raw["products"][1]["engineering_role"] = "reference_pv_module"
    raw["documents"][0]["type"] = "warranty"
    raw["documents"].append(
        {**raw["documents"][0], "document_id": "reference-only", "product_ids": [2]}
    )
    source = Snapshot.read(raw)
    assert set(source.products) == {1}
    assert set(source.documents) == {"doc"}
    assert source.documents["doc"]["product_ids"] == [1]
    with pytest.raises(PublicationChanged):
        source.require_products([2])
    chunk = Chunk(
        "terms",
        SHA,
        1,
        "",
        "text",
        "",
        "Warranty requires proof of purchase.",
        "en",
        10,
    )
    scopes = scope_proofs([chunk], raw, authority(raw))
    directory = tmp_path / "corpus"
    corpus.write(
        directory,
        corpus.Meta(
            "scope-fixture",
            None,
            None,
            "fixture",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {cid: p["product_ids"] for cid, p in scopes.items()},
                "chunk_scopes": scopes,
            },
        ),
        [
            DocumentRow(
                SHA,
                ("https://site.test/shared.pdf",),
                "Warranty",
                "Garantie",
                (),
                (),
                "warranty",
                "en",
                1,
                "indexed",
            )
        ],
        [(1, "MODEL-1")],
        [chunk],
    )
    target = tmp_path / "scoped.sqlite"
    store.export(directory, target)
    index = DocumentIndex(target)
    assert index.loaded()["products"] == [{"product_id": 1, "product_revision": "p1"}]
    assert index.search("warranty", "en", [2], publication=source) == []
    assert [
        h.chunk_id for h in index.search("warranty", "en", [1], publication=source)
    ] == ["terms"]
    assert (
        json.loads(
            index._db.execute(
                "SELECT proof FROM chunk_scopes WHERE chunk_id='terms'"
            ).fetchone()[0]
        )
        == scopes["terms"]
    )
    index.close()


def test_partial_safe_document_coverage_is_available_but_preparation_stays_incomplete(
    tmp_path: Path,
) -> None:
    raw = manifest()
    raw["products"] = raw["products"][:1]
    raw["documents"][0]["product_ids"] = [1]
    raw["products"][0]["documents"].append("unparsed")
    raw["documents"].append(
        {**raw["documents"][0], "document_id": "unparsed", "blob_sha256": "b" * 64}
    )
    chunk = Chunk(
        "safe", SHA, 1, "", "text", "", "MODEL-1 stores nominal energy.", "en", 10
    )
    scopes = scope_proofs([chunk], raw, authority(raw))
    directory = tmp_path / "corpus"
    corpus.write(
        directory,
        corpus.Meta(
            "partial",
            None,
            None,
            "fixture",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {cid: s["product_ids"] for cid, s in scopes.items()},
                "chunk_scopes": scopes,
            },
        ),
        [
            DocumentRow(
                SHA,
                ("https://site.test/shared.pdf",),
                "Manual",
                "Anleitung",
                (),
                (),
                "manual",
                "en",
                1,
                "indexed",
            ),
            DocumentRow(
                "b" * 64,
                ("https://site.test/new.pdf",),
                "New manual",
                "Neue Anleitung",
                (),
                (),
                "manual",
                "en",
                1,
                "failed",
                "fixture parse failure",
            ),
        ],
        [(1, "MODEL-1")],
        [chunk],
    )
    target = tmp_path / "partial.sqlite"
    store.export(directory, target)
    index = DocumentIndex(target)
    loaded = index.loaded()
    assert loaded["products"] == [{"product_id": 1, "product_revision": "p1"}]
    assert loaded["preparation_complete"] is False
    assert loaded["unprepared_documents"] == [
        {"document_id": "unparsed", "product_id": 1, "reason": "document_unparsed"}
    ]
    assert [
        h.chunk_id
        for h in index.search("energy", "en", [1], publication=Snapshot.read(raw))
    ] == ["safe"]
    index.close()


@pytest.mark.parametrize(
    "change",
    [
        "none",
        "withdraw_product",
        "reference_role",
        "product_revision",
        "remove_document",
        "document_revision",
        "remove_relation",
        "same_sha_replacement",
    ],
)
def test_joint_model_passage_requires_each_exact_current_document_relation(
    tmp_path: Path, change: str
) -> None:
    import copy

    raw = manifest()
    original = raw["documents"][0]
    raw["documents"] = [
        {
            **original,
            "document_id": "doc-A",
            "document_revision": "dA",
            "url": "https://site.test/A.pdf",
            "product_ids": [1],
        },
        {
            **original,
            "document_id": "doc-B",
            "document_revision": "dB",
            "url": "https://site.test/B.pdf",
            "product_ids": [2],
        },
    ]
    raw["products"][0]["documents"] = ["doc-A"]
    raw["products"][1]["documents"] = ["doc-B"]
    original_chunks = chunk_document(
        DocumentMeta(SHA, "Manual", "", (), ("MODEL-1", "MODEL-2"), "manual", "en"),
        [
            Page(
                1,
                "docling",
                [
                    Block(
                        "table",
                        rows=(
                            ("Model", "MODEL-1", "MODEL-2"),
                            ("Nominal power", "10kW", "8kW"),
                        ),
                        source_id="#/tables/0",
                    )
                ],
            )
        ],
        Words(),
        lambda _: "en",
    )
    assert len(original_chunks) == 1
    chunk = original_chunks[0]
    assert chunk.source_table == "docling:p1:#/tables/0"
    assert chunk.text == "| Model | MODEL-1 | MODEL-2 |\n| Nominal power | 10kW | 8kW |"
    proof = scope_proofs([chunk], raw, authority(raw))
    assert proof[chunk.id]["basis"] == "passage"
    assert proof[chunk.id]["product_ids"] == [1, 2]
    assert proof[chunk.id]["associations"] == [
        {
            "document_id": "doc-A",
            "document_revision": "dA",
            "blob_sha256": SHA,
            "product_id": 1,
            "product_revision": "p1",
        },
        {
            "document_id": "doc-B",
            "document_revision": "dB",
            "blob_sha256": SHA,
            "product_id": 2,
            "product_revision": "p2",
        },
    ]
    directory = tmp_path / "corpus"
    corpus.write(
        directory,
        corpus.Meta(
            "joint",
            None,
            None,
            "fixture",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {chunk.id: [1, 2]},
                "chunk_scopes": proof,
            },
        ),
        [
            DocumentRow(
                SHA,
                ("https://site.test/A.pdf", "https://site.test/B.pdf"),
                "Manual",
                "Anleitung",
                (),
                ("MODEL-1", "MODEL-2"),
                "manual",
                "en",
                1,
                "indexed",
            )
        ],
        [(1, "MODEL-1"), (2, "MODEL-2")],
        [chunk],
    )
    target = tmp_path / "joint.sqlite"
    store.export(directory, target)
    index = DocumentIndex(target)
    assert index.loaded()["products"] == [
        {"product_id": 1, "product_revision": "p1"},
        {"product_id": 2, "product_revision": "p2"},
    ]
    assert index.loaded()["preparation_complete"] is True
    current = copy.deepcopy(raw)
    if change == "withdraw_product":
        current["products"].pop()
    elif change == "reference_role":
        current["products"][1]["engineering_role"] = "reference_pv_module"
    elif change == "product_revision":
        current["products"][1]["product_revision"] = "p2-new"
    elif change == "remove_document":
        current["documents"].pop()
    elif change == "document_revision":
        current["documents"][1]["document_revision"] = "dB-new"
    elif change == "remove_relation":
        current["documents"][1]["product_ids"] = []
    elif change == "same_sha_replacement":
        current["documents"][1]["document_id"] = "another-public-identity"
        current["documents"][1]["url"] = "https://site.test/another.pdf"
    hits = index.search("power", "en", [1], publication=Snapshot.read(current))
    assert [h.chunk_id for h in hits] == ([chunk.id] if change == "none" else [])
    if hits:
        assert hits[0].product_ids == (1, 2)
        assert hits[0].text == chunk.text
        assert {
            item["product_id"]
            for item in Snapshot.read(raw).dependencies()["documents"]
        } == {1, 2}
    index.close()


def test_actual_resolved_current_is_reopened_after_switch(
    tmp_path: Path, path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil
    import sqlite3

    import linker_genie.retrieval as retrieval

    one, two = tmp_path / "one.sqlite", tmp_path / "two.sqlite"
    shutil.copyfile(path, one)
    shutil.copyfile(path, two)
    with sqlite3.connect(two) as db:
        db.execute("UPDATE meta SET value='build2' WHERE key='version'")
    link = tmp_path / "current.sqlite"
    link.symlink_to(one)
    monkeypatch.setenv("GENIE_INDEX", str(link))
    monkeypatch.setattr(retrieval, "_DEFAULT", None)
    search = KnowledgeSearch()
    assert search.loaded() == {
        "index_version": "build1",
        "source_revision": "source-1",
        "model_identity_revision": "fixture-identity-1",
        "recipe_revision": "",
        "expected_serving_revision": "",
        "serving_revision": RUNTIME_SERVING_REVISION,
        "activation_epoch": 0,
        "materialization_complete": True,
        "products": [
            {"product_id": 1, "product_revision": "p1"},
            {"product_id": 2, "product_revision": "p2"},
        ],
        "preparation_complete": True,
        "unprepared_documents": [],
    }
    link.unlink()
    link.symlink_to(two)
    assert search.loaded()["index_version"] == "build2"
    assert retrieval._DEFAULT is not None
    retrieval._DEFAULT.close()
    monkeypatch.setattr(retrieval, "_DEFAULT", None)


def test_worker_publishes_then_acknowledges_only_actual_loaded_generation() -> None:
    import json

    requests: list[dict[str, Any]] = []
    job = {
        "job_id": "j1",
        "lease_token": "lease",
        "source_revision": "source-1",
        "model_identity_revision": "fixture-identity-1",
        "manifest": manifest(),
    }

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"job": job}
            if request.url.path.endswith("claim")
            else {"accepted": True},
        )

    worker = Worker(
        "https://site.test/jobs",
        "fixture",
        "fixture",
        "mac",
        600,
        transport=httpx.MockTransport(handle),
        recipe="",
    )
    assert worker.one(
        lambda m: "build1",
        lambda: {
            "source_revision": "source-1",
            "model_identity_revision": "fixture-identity-1",
            "index_version": "build1",
        },
    )
    assert requests[-1]["status"] == "ready"
    assert requests[-1]["loaded_revision"] == "source-1"
    assert "password" not in requests[-1]


@pytest.mark.parametrize(
    "complete,issues,expected",
    [
        (True, [], True),
        (False, [], False),
        (None, [], False),
        (
            True,
            [{"document_id": "doc", "product_id": 1, "reason": "no_proven_passage"}],
            False,
        ),
    ],
)
def test_all_products_available_cannot_hide_unprepared_document_associations(
    complete: Any, issues: list[dict[str, Any]], expected: bool
) -> None:
    recorded = []
    raw = manifest()

    def handle(request: httpx.Request) -> httpx.Response:
        recorded.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "job": {
                    "job_id": "j",
                    "lease_token": "l",
                    "source_revision": "source-1",
                    "model_identity_revision": "fixture-identity-1",
                    "manifest": raw,
                }
            }
            if request.url.path.endswith("claim")
            else {"accepted": True},
        )

    worker = Worker(
        "https://site.test/jobs",
        "fixture",
        "fixture",
        "mac",
        600,
        transport=httpx.MockTransport(handle),
        recipe="",
    )
    products = [
        {"product_id": p["product_id"], "product_revision": p["product_revision"]}
        for p in raw["products"]
    ]
    assert worker.one(
        lambda _: "build1",
        lambda: {
            "source_revision": "source-1",
            "model_identity_revision": "fixture-identity-1",
            "index_version": "build1",
            "products": products,
            "preparation_complete": complete,
            "unprepared_documents": issues,
        },
    )
    assert recorded[-1]["prepared_products"] == products
    assert recorded[-1]["preparation_complete"] is expected
    assert recorded[-1]["unprepared_documents"] == issues
    assert bool(recorded[-1]["error"]) is not expected
    worker.close()


def test_worker_does_not_ack_ready_when_disk_changed_but_running_process_is_old() -> (
    None
):
    import json

    requests: list[dict[str, Any]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "job": {
                    "job_id": "j",
                    "lease_token": "l",
                    "source_revision": "source-1",
                    "model_identity_revision": "fixture-identity-1",
                    "manifest": manifest(),
                }
            }
            if request.url.path.endswith("claim")
            else {"accepted": True},
        )

    worker = Worker(
        "https://site.test/jobs",
        "fixture",
        "fixture",
        "mac",
        600,
        transport=httpx.MockTransport(handle),
        recipe="",
    )
    with pytest.raises(RuntimeError, match="has not loaded"):
        worker.one(
            lambda m: "new",
            lambda: {
                "source_revision": "source-1",
                "model_identity_revision": "fixture-identity-1",
                "index_version": "old",
            },
        )
    assert requests[-1]["status"] == "failed"


def test_locale_mirror_is_not_independent_permission() -> None:
    raw = manifest()
    Snapshot.read(raw).require_products([101])
    raw["products"] = raw["products"][1:]
    with pytest.raises(PublicationUnavailable):
        Snapshot.read(raw).require_products([101])


def test_new_turn_does_not_reinject_historical_assistant_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from conftest import SHELL
    from fastapi.testclient import TestClient

    import linker_genie.app as service
    from linker_genie.facts import TurnFacts
    from linker_genie.log import TurnLog
    from linker_genie.schema import TextBlock, TurnOutput
    from linker_genie.understand import nothing

    seen = []

    def generate(body: Any, retry: Any) -> Any:
        seen.extend(body.messages)
        return TurnOutput(
            language="en",
            blocks=[TextBlock(text="Please tell me which product you need.")],
        ), TurnFacts()

    permission = authority(manifest())
    monkeypatch.setattr(service.app.state, "publication", permission, raising=False)
    monkeypatch.setattr(service.app.state, "prepare", nothing, raising=False)
    monkeypatch.setattr(service.app.state, "generate", generate, raising=False)
    monkeypatch.setattr(
        service.app.state, "commerce", lambda ids: (TurnFacts(), []), raising=False
    )
    monkeypatch.setattr(service, "_log", TurnLog(tmp_path / "turns.sqlite"))
    response = TestClient(service.app, headers=SHELL).post(
        "/turn",
        json={
            "conversation_id": "old",
            "messages": [
                {"role": "user", "content": "I have an older system."},
                {
                    "role": "assistant",
                    "content": "MODEL-3 has secret old technical facts.",
                },
                {"role": "user", "content": "Tell me about current products."},
            ],
        },
    )
    assert response.status_code == 200
    assert seen and all(m.role == "user" for m in seen)
    assert "secret old" not in response.text


def test_upload_reading_of_withdrawn_photo_is_identification_only() -> None:
    from linker_genie.abilities import AbilityClient
    from linker_genie.schema import AttachmentReading, Rating, TurnMessage, TurnRequest
    from linker_genie.understand import Understander

    request = TurnRequest(
        conversation_id="old",
        messages=[TurnMessage(role="user", content="What is its capacity?")],
        readings=[
            AttachmentReading(
                id="att1",
                name="old.jpg",
                kind="photo",
                model="MODEL-3",
                text="Old technical instructions",
                ratings=[Rating(label="energy", value="99 kWh")],
            )
        ],
    )
    prepared = Understander(None, None, publication=authority(manifest())).prepare(
        request, AbilityClient("https://site.test")
    )
    assert prepared.route.name == "scripted"
    assert "current" in prepared.route.answer
    assert prepared.attachments == []
    assert not prepared.facts.facts
    assert "99" not in prepared.route.answer


def test_historical_solution_names_do_not_authorize_current_product_cards() -> None:
    from linker_genie import solution

    payload = solution.view(
        {
            "historical": True,
            "id": 7,
            "title": "Earlier design",
            "status": "solution",
            "items": [{"product_id": 3, "model": "MODEL-3", "quantity": 1}],
        }
    )
    assert "MODEL-" in payload["text"]
    assert payload["products"] == []
    assert not solution.collect(payload).product_ids


def test_worker_retention_removes_only_owned_obsolete_builds(tmp_path: Path) -> None:
    from publication_worker import retain_builds

    index = tmp_path / "index"
    root = index / "builds"
    root.mkdir(parents=True)
    first, second, current, reference = [
        root / name for name in ("a", "b", "c", "golden")
    ]
    external = tmp_path / "unique-evidence"
    for directory in (first, second, current, reference, external):
        directory.mkdir()
        (directory / "proof.txt").write_text("preserve")
    ledger = index / "publication-worker-releases.json"
    ledger.write_text(json.dumps([str(first), str(second), str(external)]))
    retain_builds(index, current)
    assert not first.exists()
    assert second.is_dir() and current.is_dir()
    assert reference.is_dir() and external.is_dir()
    assert json.loads(ledger.read_text()) == [str(second), str(current)]
    retain_builds(index, current)
    assert second.is_dir() and current.is_dir()


def test_loaded_process_readback_uses_same_ssh_alias_and_secret_only_on_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    from publication_worker import read_loaded

    calls: list[tuple[list[str], dict[str, Any]]] = []

    def run(command: list[str], **options: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, options))
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                {
                    "source_revision": "source-1",
                    "model_identity_revision": "fixture-identity-1",
                    "index_version": "build1",
                    "products": [],
                }
            ),
            "",
        )

    monkeypatch.setattr(subprocess, "run", run)
    result = read_loaded(
        "http://127.0.0.1:8902/knowledge/loaded",
        "fixture-private-service-token",
        "fixture-host",
    )
    assert result["index_version"] == "build1"
    command, options = calls[0]
    assert command[:5] == ["ssh", "-o", "BatchMode=yes", "--", "fixture-host"]
    assert command[5].startswith("python3 -c ")
    assert all("fixture-private-service-token" not in argument for argument in command)
    assert json.loads(options["input"])["token"] == "fixture-private-service-token"
    assert options["capture_output"] is True and options["timeout"] == 30
    with pytest.raises(ValueError, match="loopback"):
        read_loaded(
            "https://public.example/knowledge/loaded", "fixture", "fixture-host"
        )


@pytest.mark.parametrize("after", ["revoked", "outage", "malformed"])
def test_http_turn_distinguishes_authoritative_revocation_from_authority_failure(
    monkeypatch: pytest.MonkeyPatch, after: str
) -> None:
    from conftest import SHELL
    from fastapi.responses import StreamingResponse
    from fastapi.testclient import TestClient

    import linker_genie.app as service

    reads: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        reads.append(request.url.path)
        if request.url.path.endswith("manifest"):
            return httpx.Response(200, json=manifest())
        if after == "outage":
            return httpx.Response(503)
        return httpx.Response(200, json={"valid": False} if after == "revoked" else {})

    client = PublicationClient("https://site.test", httpx.MockTransport(handle))
    monkeypatch.setattr(service.app.state, "publication", client, raising=False)
    monkeypatch.setattr(
        service,
        "_compute_turn",
        lambda *args: StreamingResponse(iter(["never released"])),
    )
    response = TestClient(service.app, headers=SHELL).post(
        "/turn",
        json={
            "conversation_id": "fixture",
            "messages": [{"role": "user", "content": "Current product question"}],
        },
    )
    assert response.status_code == (409 if after == "revoked" else 503)
    assert response.json()["detail"] == (
        "publication_changed" if after == "revoked" else "publication_unavailable"
    )
    assert "never released" not in response.text
    assert reads == [
        "/wp-json/linker/v1/publication/manifest",
        "/wp-json/linker/v1/publication/validate",
    ]
    client.close()


@pytest.mark.parametrize("failure", ["build", "publish"])
def test_failed_worker_generation_is_removed_without_deleting_shared_builds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from types import SimpleNamespace

    from test_chunking import Words

    from index import build
    from publication_worker import record_build, run_job

    index_dir = tmp_path / "index"
    shared = index_dir / "builds" / "unique-shared-evidence"
    shared.mkdir(parents=True)
    (shared / "proof.txt").write_text("keep")
    replies: list[dict[str, Any]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("claim"):
            return httpx.Response(
                200,
                json={
                    "job": {
                        "job_id": "j",
                        "lease_token": "l",
                        "source_revision": "source-1",
                        "model_identity_revision": "fixture-identity-1",
                        "manifest": manifest(),
                    }
                },
            )
        replies.append(json.loads(request.content))
        return httpx.Response(200, json={"accepted": True})

    worker = Worker(
        "https://site.test/jobs",
        "fixture",
        "fixture",
        "mac",
        600,
        transport=httpx.MockTransport(handle),
        recipe="",
    )
    monkeypatch.setattr(
        build, "chunk_all", lambda *args: SimpleNamespace(chunks=[], documents=[])
    )

    def prepare(raw: dict[str, Any]) -> str:
        del raw
        if failure == "build":
            # Native builder creates a generation and calls its ownership hook
            # before this missing inventory source makes the build fail.
            build.build(
                tmp_path / "missing.json",
                tmp_path,
                tmp_path,
                index_dir,
                None,
                Words(),
                lambda text: "en",
                on_created=lambda path: record_build(index_dir, path),
            )
        else:
            directory = index_dir / "builds" / "new-worker-generation"
            directory.mkdir()
            record_build(index_dir, directory)
            raise RuntimeError("fixture publish failed")
        return "never"

    with pytest.raises((OSError, RuntimeError)):
        run_job(worker, prepare, lambda: {}, index_dir)
    worker.close()
    assert replies[-1]["status"] == "failed"
    assert list((index_dir / "builds").iterdir()) == [shared]
    assert not (index_dir / "publication-worker-pending.json").exists()


def test_worker_absolute_script_entry_starts_without_pythonpath(tmp_path: Path) -> None:
    import os
    import subprocess
    import sys

    script = Path(__file__).resolve().parents[1] / "ops" / "publication_worker.py"
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    process = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == 0, process.stderr
    assert "--loaded-url" in process.stdout


def test_installer_actual_program_arguments_start_child_without_pythonpath(
    tmp_path: Path,
) -> None:
    import os
    import plistlib
    import subprocess
    import sys

    installer = (
        Path(__file__).resolve().parents[1] / "ops" / "install_publication_worker.py"
    )
    private = tmp_path / "worker.env"
    private.write_text("# synthetic environment, --help performs no network work\n")
    private.chmod(0o600)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    rendered = subprocess.run(
        [
            sys.executable,
            str(installer),
            "--env-file",
            str(private),
            "--interval-seconds",
            "60",
            "--lease-seconds",
            "600",
            "--worker-id",
            "fixture",
            "--loaded-url",
            "http://127.0.0.1:8902/knowledge/loaded",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        timeout=30,
    )
    assert rendered.returncode == 0, rendered.stderr
    definition = plistlib.loads(rendered.stdout)
    child = subprocess.run(
        [*definition["ProgramArguments"], "--help"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert child.returncode == 0, child.stderr
    assert "--loaded-url" in child.stdout


def test_draft_only_identity_change_revokes_loaded_scope_without_source_change(
    path: Path,
) -> None:
    current = manifest()
    with_index = DocumentIndex(path)
    try:
        assert with_index.search(
            "energy", "en", [1], publication=Snapshot.read(current)
        )
        assert with_index.loaded()["model_identity_revision"] == "fixture-identity-1"
        current["model_identity_revision"] = "draft-model-added"
        assert current["source_revision"] == "source-1"
        assert (
            with_index.search("energy", "en", [1], publication=Snapshot.read(current))
            == []
        )
        import sqlite3

        with_index.close()
        with sqlite3.connect(path) as connection:
            connection.execute("DELETE FROM meta WHERE key='model_identity_revision'")
        with_index = DocumentIndex(path)
        assert with_index.loaded()["preparation_complete"] is False
        assert with_index.permissions(Snapshot.read(manifest()), [1]) == {}
    finally:
        with_index.close()
