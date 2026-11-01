"""Certificate passages compiled from frozen indexed manufacturer pages."""

from __future__ import annotations

import gzip
import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_chunking import Words

from index import corpus, store
from index.build import attach_certificate_evidence
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.extract import certificate_physical_evidence
from index.publication import ScopeProof, compile_certificate_subjects
from index.table_compiler import _author_contexts
from linker_genie.certificate_scope import certificate_text
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex, is_passage
from linker_genie.table_projection import cells_digest

FIXTURE = (
    Path(__file__).parent / "fixtures/publication-compiler/certificate-batch.json.gz"
)


@pytest.fixture(scope="module")
def prepared() -> tuple[dict[str, Any], list[Chunk], dict[str, ScopeProof]]:
    fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    raw = fixture["manifest"]
    source = Snapshot.read(raw)
    originals = [
        Chunk(
            **{
                **row,
                "preceding_text": tuple(row.get("preceding_text", ())),
                "source_rows": tuple(row.get("source_rows", ())),
                "source_headings": tuple(row.get("source_headings", ())),
            }
        )
        for row in fixture["chunks"]
    ]
    statuses = {
        str(product["model"]).casefold(): "published"
        for product in source.products.values()
        if product.get("model")
    }
    chunks, scopes = compile_certificate_subjects(
        originals, source, Words(), 512, _author_contexts(originals, source, statuses)
    )
    for scope in scopes.values():
        scope["model_identity_revision"] = source.model_identity_revision
    return fixture, chunks, scopes


def _target(
    prepared: tuple[dict[str, Any], list[Chunk], dict[str, ScopeProof]],
    sha_prefix: str,
    model: str,
) -> tuple[Chunk, ScopeProof]:
    fixture, chunks, scopes = prepared
    products = Snapshot.read(fixture["manifest"]).products
    pid = next(pid for pid, product in products.items() if product["model"] == model)
    chunk = next(
        chunk
        for chunk in chunks
        if chunk.doc_sha256.startswith(sha_prefix)
        and scopes[chunk.id]["product_ids"] == [pid]
    )
    return chunk, scopes[chunk.id]


def _authorized(chunk: Chunk, scope: ScopeProof, source: Snapshot) -> bool:
    return bool(
        authorize_chunk(
            chunk.doc_sha256,
            scope["product_ids"],
            scope["associations"],
            scope,
            products=source.products,
            documents=source.documents,
            chunk_id=chunk.id,
            text=chunk.text,
        )
    )


def test_actual_certificate_batch_has_substantive_exact_model_evidence(
    prepared: tuple[dict[str, Any], list[Chunk], dict[str, ScopeProof]],
) -> None:
    fixture, chunks, scopes = prepared
    source = Snapshot.read(fixture["manifest"])
    missing = {(row["document_id"], row["product_id"]) for row in fixture["unprepared"]}
    pairs = {
        (scopes[c.id]["document_ids"][0], scopes[c.id]["product_ids"][0])
        for c in chunks
    }
    assert len(missing) == 78
    assert len(chunks) == len(pairs) == len(missing & pairs) == 71
    assert all(
        is_passage(c.text) and _authorized(c, scopes[c.id], source) for c in chunks
    )

    etr, etr_proof = _target(prepared, "6820813acbec", "GW99.99K-ETR-G10")
    assert etr.page == 1 and "the specimen is in conformity" in etr.text
    assert "does not imply assessment of the production" in etr.text
    assert (
        etr_proof["certificate_scope"]["source_chunk_id"] == "6820813acbec-p1-de43c81e"
    )
    hs2, _ = _target(prepared, "75a3a83432a9", "HS2-10K-T2-X")
    assert "X=2, 3, 4, 5 (Number of Modules)" in hs2.text
    unit, _ = _target(prepared, "da4d0f336bb0", "GW80K-ET-G10")
    assert "4110" in unit.text and "4120" in unit.text
    assert "does not provide test terminal" in unit.text
    report, report_scope = _target(prepared, "000592098663", "GW112.6-BAT-AC-G10")
    assert report.page == 2 and "The sample has passed" in report.text
    assert "563.2V" not in report.text
    evidence = report_scope["certificate_scope"]["report_table"]
    assert evidence["source_table"] == "docling:p2:#/tables/0"
    assert {1, 3, 10, 13}.issubset(
        {row for fragment in evidence["fragments"] for row in fragment["source_rows"]}
    )
    appendix, appendix_proof = _target(prepared, "c0aa75c957e2", "SEC3000C")
    assert appendix.page == 2 and "IEC 61010-1:2010+A1" in appendix.text
    assert "additional requirements in countries" in appendix.text
    assert all(
        anchor["page"] == 1
        for anchor in appendix_proof["certificate_scope"]["appendix_anchors"].values()
    )
    wrapped, wrapped_proof = _target(prepared, "d80f9722131d", "GW125/261-ESA-LCN-G10")
    assert "4130" in wrapped.text and "does not provide test terminal" in wrapped.text
    physical = wrapped_proof["certificate_scope"]["unit_table"]["model_wrap"]
    assert physical["line_break"] == "\r\n" and physical["source_page"] == 1
    red, red_proof = _target(prepared, "8158c2cc2ff1", "GW7K-HCA-20")
    assert (
        "EN 18031-1:2024" in red.text
        and "validity of the present certificate" in red.text
    )
    assert (
        red_proof["certificate_scope"]["red_anchors"]["page_marker"]["source_page"] == 2
    )
    assert not any(
        chunk.doc_sha256.startswith("8158c2cc2ff1")
        and source.products[scopes[chunk.id]["product_ids"][0]]["model"]
        == "GW11K-HCA-20"
        for chunk in chunks
    )


def test_each_new_form_denies_scope_only_wrong_model_and_missing_conditions(
    prepared: tuple[dict[str, Any], list[Chunk], dict[str, ScopeProof]],
) -> None:
    fixture, _, _ = prepared
    originals = {c["id"]: c for c in fixture["chunks"]}
    shared = originals["6820813acbec-p1-de43c81e"]["text"]
    assert certificate_text(shared, "GW99.99K-ETR-G10")
    assert certificate_text(shared, "GW99.98K-ETR-G10") is None
    assert (
        certificate_text(
            shared.replace("(yy=75,80,99.99,100,110,124.99,125)", "(yy=75-125)"),
            "GW80K-ETR-G10",
        )
        is None
    )
    assert (
        certificate_text(
            shared.replace(
                "This is to certify that the specimen is in conformity with the assessment requirement mentioned above.",
                "",
            ),
            "GW80K-ETR-G10",
        )
        is None
    )

    declaration = originals["75a3a83432a9-p1-4b8c9326"]["text"]
    saj = originals["75a3a83432a9-p1-cb461cb5"]["text"]
    assert certificate_text(saj, "HS2-10K-T2-X", declaration_text=declaration)
    assert certificate_text(saj, "HS2-10K-T2-X") is None
    assert certificate_text(saj, "HS2-11K-T2-X", declaration_text=declaration) is None
    assert (
        certificate_text(
            saj.replace("(X=2, 3, 4, 5 (Number of Modules))", ""),
            "HS2-10K-T2-X",
            declaration_text=declaration,
        )
        is None
    )
    assert (
        certificate_text(
            "EU Declaration of Conformity\nHS2-10K-T2-X",
            "HS2-10K-T2-X",
            declaration_text=declaration,
        )
        is None
    )

    goodwe = originals["0d33ea23ff2d-p1-e8f6ff8f"]["text"]
    assert certificate_text(goodwe, "GW261.2-BAT-LCD-G10")
    assert certificate_text(goodwe, "GW261.2-BAT-LCD-G11") is None
    assert (
        certificate_text(
            goodwe.replace(
                "are in conformity with the following Union harmonisation legislation and directives:",
                "",
            ),
            "GW261.2-BAT-LCD-G10",
        )
        is None
    )
    cb = originals["f4de612e4a7c-p1-2aa52d23"]["text"]
    assert certificate_text(cb, "GW5.1-BAT-D-G21")
    assert certificate_text(cb, "GW5.1-BAT-D-G22") is None
    assert (
        certificate_text(
            cb.replace(
                "A sample of the product was tested and found to be in conformity with",
                "",
            ),
            "GW5.1-BAT-D-G21",
        )
        is None
    )


def test_certificate_proofs_reject_altered_rows_and_revoked_relations(
    prepared: tuple[dict[str, Any], list[Chunk], dict[str, ScopeProof]],
) -> None:
    fixture, _, _ = prepared
    source = Snapshot.read(fixture["manifest"])
    report, scope = _target(prepared, "000592098663", "GW112.6-BAT-AC-G10")
    assert _authorized(report, scope, source)
    changed = deepcopy(scope)
    fragments = changed["certificate_scope"]["report_table"]["fragments"]
    next(fragment for fragment in fragments if 13 in fragment["source_rows"])[
        "source_rows"
    ].remove(13)
    assert not _authorized(report, changed, source)
    changed = deepcopy(scope)
    table = changed["certificate_scope"]["report_table"]
    next(
        cell
        for cell in table["source_cells"]
        if cell["row_start"] == 13 and cell["col_start"] == 1
    )["text"] = "The sample failed."
    table["cells_sha256"] = cells_digest(table["source_cells"])
    assert not _authorized(report, changed, source)

    attestation, scope = _target(prepared, "f43c5fe00fda", "GW7K-HCA-20")
    assert _authorized(attestation, scope, source)
    changed = deepcopy(scope)
    table = changed["certificate_scope"]["statement_table"]
    assert table["source_rows"] == [0, 1]
    table["source_rows"] = [0, 2]
    assert not _authorized(attestation, changed, source)
    changed = deepcopy(scope)
    changed["certificate_scope"]["limitation_anchor"]["text"] += " altered"
    assert not _authorized(attestation, changed, source)

    revoked = deepcopy(fixture["manifest"])
    did = scope["document_ids"][0]
    pid = scope["product_ids"][0]
    next(d for d in revoked["documents"] if d["document_id"] == did)[
        "product_ids"
    ].remove(pid)
    assert not _authorized(attestation, scope, Snapshot.read(revoked))

    appendix, scope = _target(prepared, "c0aa75c957e2", "SEC3000C")
    assert _authorized(appendix, scope, source)
    changed = deepcopy(scope)
    changed["certificate_scope"]["appendix_anchors"]["identity"]["text"] = changed[
        "certificate_scope"
    ]["appendix_anchors"]["identity"]["text"].replace("50647608", "50647609")
    assert not _authorized(appendix, changed, source)
    wrapped, scope = _target(prepared, "d80f9722131d", "GW125/261-ESA-LCN-G10")
    assert _authorized(wrapped, scope, source)
    changed = deepcopy(scope)
    changed["certificate_scope"]["unit_table"]["model_wrap"]["fragments"][1]["bbox"][
        0
    ] = 1
    assert not _authorized(wrapped, changed, source)
    red, scope = _target(prepared, "8158c2cc2ff1", "GW7K-HCA-20")
    assert _authorized(red, scope, source)
    changed = deepcopy(scope)
    changed["certificate_scope"]["red_anchors"]["page_marker"]["page_count"] = 3
    assert not _authorized(red, changed, source)
    changed = deepcopy(scope)
    changed["certificate_scope"]["red_anchors"]["table"]["source_rows"] = [0, 2]
    assert not _authorized(red, changed, source)


def test_real_fts_preparation_and_product_permissions(
    prepared: tuple[dict[str, Any], list[Chunk], dict[str, ScopeProof]], tmp_path: Path
) -> None:
    fixture, chunks, scopes = prepared
    raw = fixture["manifest"]
    source = Snapshot.read(raw)
    corpus_dir = tmp_path / "corpus"
    corpus.write(
        corpus_dir,
        corpus.Meta(
            "certificate-batch",
            None,
            None,
            "actual indexed originals",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {
                    key: value["product_ids"] for key, value in scopes.items()
                },
                "chunk_scopes": scopes,
            },
        ),
        [
            DocumentRow(
                d["blob_sha256"],
                (d["url"],),
                d["title"],
                "",
                (),
                (),
                "certificate",
                d["lang"],
                2,
                "indexed",
            )
            for d in raw["documents"]
        ],
        [(pid, str(p["model"])) for pid, p in source.products.items()],
        chunks,
    )
    target = tmp_path / "index.sqlite"
    store.export(corpus_dir, target)
    with sqlite3.connect(target) as db:
        unprepared = json.loads(
            db.execute(
                "SELECT value FROM meta WHERE key='unprepared_documents'"
            ).fetchone()[0]
        )
    assert len(unprepared) == 7
    assert all(row["reason"] == "no_proven_passage" for row in unprepared)
    report, proof = _target(prepared, "000592098663", "GW112.6-BAT-AC-G10")
    pid = proof["product_ids"][0]
    loaded = DocumentIndex(target, encoder=None)
    try:
        hits = loaded.search(
            "GW112.6-BAT-AC-G10 sample UN",
            "en",
            [pid],
            k=50,
            neighbours=True,
            publication=source,
        )
        assert any(hit.chunk_id == report.id and hit.page == 2 for hit in hits)
        wrong_pid = next(
            pid
            for pid, item in source.products.items()
            if item["model"] == "ATS1-T63-A"
        )
        assert all(
            hit.doc_sha256 != report.doc_sha256
            for hit in loaded.search(
                "GW112.6-BAT-AC-G10 sample UN",
                "en",
                [wrong_pid],
                k=50,
                neighbours=True,
                publication=source,
            )
        )
        revoked = deepcopy(raw)
        next(item for item in revoked["products"] if item["product_id"] == pid)[
            "product_revision"
        ] += "-changed"
        assert not any(
            hit.doc_sha256 == report.doc_sha256
            for hit in loaded.search(
                "GW112.6-BAT-AC-G10 sample UN",
                "en",
                [pid],
                k=50,
                neighbours=True,
                publication=Snapshot.read(revoked),
            )
        )
    finally:
        loaded.close()


def test_physical_wrap_rejects_invisible_or_unreadable_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pypdfium2.raw as pdfium
    from test_pdf_cover_visibility import _pdf

    model = "GW125/261-ESA-LCN-G10"
    commands = "BT /F1 14 Tf 40 500 Td (GW125/261-) Tj 0 -16 Td (ESA-LCN-G10) Tj ET"
    original = _pdf(tmp_path, commands)
    assert any(
        item["model"] == model
        for item in certificate_physical_evidence(original, [model])
    )
    hidden = _pdf(tmp_path, commands.replace("40 500 Td", "40 500 Td 3 Tr"))
    assert certificate_physical_evidence(hidden, [model]) == []
    monkeypatch.setattr(pdfium, "FPDFPage_GetAnnotCount", lambda *_: -1)
    assert certificate_physical_evidence(original, [model]) == []


def test_build_attaches_only_unique_matching_physical_source(
    prepared: tuple[dict[str, Any], list[Chunk], dict[str, ScopeProof]],
) -> None:
    fixture, _, _ = prepared
    originals = [
        Chunk(**row)
        for row in fixture["chunks"]
        if row.get("source_certificate_evidence")
    ]
    assert len(originals) == 2
    stripped = [replace(chunk, source_certificate_evidence=()) for chunk in originals]
    evidence = [
        item for chunk in originals for item in chunk.source_certificate_evidence
    ]
    attached = attach_certificate_evidence(stripped, evidence)
    assert {chunk.id for chunk in attached if chunk.source_certificate_evidence} == {
        chunk.id for chunk in originals
    }
    assert [chunk.text for chunk in attached] == [chunk.text for chunk in originals]
    duplicate = attach_certificate_evidence([stripped[0], stripped[0]], evidence)
    assert all(not chunk.source_certificate_evidence for chunk in duplicate)
