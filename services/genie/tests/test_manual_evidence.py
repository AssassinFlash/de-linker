"""Real cached manufacturer excerpts, current associations and retrieval fences."""

from __future__ import annotations

import gzip
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from test_chunking import Words

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.manual_evidence import compile_manual_evidence
from linker_genie.manual_evidence import valid_reviewed_manual
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex

FIXTURE = (
    Path(__file__).parent
    / "fixtures/publication-compiler/reviewed-manual-evidence.json.gz"
)


def fixture() -> tuple[dict[str, Any], list[Chunk], dict[str, list[dict[str, Any]]]]:
    value = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    chunks = [Chunk(**item) for item in value["chunks"]]
    return value["manifest"], chunks, value["contexts"]


def selected() -> tuple[dict[str, Any], list[Chunk], dict[str, Any]]:
    raw, original, contexts = fixture()
    units, proofs = compile_manual_evidence(
        original, Snapshot.read(raw), Words(), 512, restricted_contexts=contexts
    )
    for proof in proofs.values():
        proof["model_identity_revision"] = raw["model_identity_revision"]
    return raw, units, proofs


def test_reviewed_sources_obey_exact_model_and_finer_section_boundaries() -> None:
    raw, original, contexts = fixture()
    wrong = {
        "product_id": 999999,
        "product_revision": "foreign-revision",
        "model": "GW80K-ETR-G10",
        "documents": [],
    }
    raw["products"].append(wrong)
    german = next(d for d in raw["documents"] if d["blob_sha256"].startswith("26a505"))
    german["product_ids"].append(wrong["product_id"])
    units, proofs = compile_manual_evidence(
        original, Snapshot.read(raw), Words(), 512, restricted_contexts=contexts
    )
    assert any(
        proof["product_ids"] == [1946] and "Netz verbunden" in unit.text
        for unit in units
        for proof in [proofs[unit.id]]
    )
    assert not any(999999 in proof["product_ids"] for proof in proofs.values())
    assert any(
        proof["product_ids"] == [1185] and "elekeeper" in unit.text
        for unit in units
        for proof in [proofs[unit.id]]
    )
    assert any(
        proof["product_ids"] == [3573] and "fasten the hexagon nut" in unit.text
        for unit in units
        for proof in [proofs[unit.id]]
    )
    assert any(
        proof["product_ids"] == [6321] and "Locate the fault position" in unit.text
        for unit in units
        for proof in [proofs[unit.id]]
    )

    # An unreviewed, finer author restriction cannot borrow a known reset.
    altered = deepcopy(contexts)
    altered["a470d6e1be68-p34-0abaea56"].append(
        {
            "kind": "declaration",
            "quote": "Only HS3-8K-T2-W/G-PX can use this procedure.",
            "source_chunk_id": "unreviewed-narrow-heading",
        }
    )
    _, constrained = compile_manual_evidence(
        original, Snapshot.read(raw), Words(), 512, restricted_contexts=altered
    )
    assert not any(
        proof["reviewed_manual"]["source_id"] == "a470d6e1be68-p34-0abaea56"
        for proof in constrained.values()
    )


def test_original_source_and_chapter_evidence_are_not_replaceable() -> None:
    raw, original, contexts = fixture()
    source = Snapshot.read(raw)
    source_id = "5cd104b9e006-p57-c749de81"
    altered = [
        replace(c, text=c.text + " Additional foreign-variant instruction.")
        if c.id == source_id
        else c
        for c in original
    ]
    _, scopes = compile_manual_evidence(
        altered, source, Words(), 512, restricted_contexts=contexts
    )
    assert not any(
        p["reviewed_manual"]["source_id"] == source_id for p in scopes.values()
    )
    altered = [
        replace(c, source_headings=("2.4 other subject",))
        if c.id == "5cd104b9e006-p57-3a05a42c"
        else c
        for c in original
    ]
    _, scopes = compile_manual_evidence(
        altered, source, Words(), 512, restricted_contexts=contexts
    )
    assert not any(
        p["reviewed_manual"]["source_id"] == source_id for p in scopes.values()
    )


def test_runtime_rejects_tampered_source_proof_and_revoked_association() -> None:
    raw, units, proofs = selected()
    unit = next(
        c
        for c in units
        if c.id.startswith("26a5052fc859") and "Netz verbunden" in c.text
    )
    proof = proofs[unit.id]
    source = Snapshot.read(raw)
    args = {
        "sha": unit.doc_sha256,
        "chunk_id": unit.id,
        "text": unit.text,
    }
    assert valid_reviewed_manual(proof, proof["product_ids"], source.products, **args)
    assert authorize_chunk(
        unit.doc_sha256,
        proof["product_ids"],
        proof["associations"],
        proof,
        products=source.products,
        documents=source.documents,
        chunk_id=unit.id,
        text=unit.text,
    )
    altered = deepcopy(proof)
    altered["reviewed_manual"]["anchor_text"] += " GW80K-ETR-G10"
    assert not valid_reviewed_manual(
        altered, proof["product_ids"], source.products, **args
    )
    assert not authorize_chunk(
        unit.doc_sha256,
        proof["product_ids"],
        [],
        proof,
        products=source.products,
        documents=source.documents,
        chunk_id=unit.id,
        text=unit.text,
    )


def test_sqlite_search_returns_the_manual_passage_then_honours_withdrawal(
    tmp_path: Path,
) -> None:
    raw, units, proofs = selected()
    source_dir = tmp_path / "corpus"
    corpus.write(
        source_dir,
        corpus.Meta(
            "reviewed-manual",
            None,
            None,
            "cached manufacturer source",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {
                    cid: proof["product_ids"] for cid, proof in proofs.items()
                },
                "chunk_scopes": proofs,
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
                "manual",
                "en",
                100,
                "indexed",
            )
            for d in raw["documents"]
        ],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        units,
    )
    target = tmp_path / "index.sqlite"
    store.export(source_dir, target)
    loaded = DocumentIndex(target, encoder=None)
    try:
        hits = loaded.search(
            "Netzeinspeisung Eigenverbrauch",
            "de",
            [1946],
            publication=Snapshot.read(raw),
        )
        assert any("Netz verbunden" in hit.text and hit.page == 7 for hit in hits)
        hits = loaded.search(
            "elekeeper monitoring", "en", [1185], publication=Snapshot.read(raw)
        )
        assert any("elekeeper" in hit.text and hit.page == 34 for hit in hits)
        hits = loaded.search(
            "fault localization alarm", "en", [6321], publication=Snapshot.read(raw)
        )
        assert any(
            "Locate the fault position" in hit.text and hit.page == 16 for hit in hits
        )
        revoked = deepcopy(raw)
        for document in revoked["documents"]:
            if document["blob_sha256"].startswith("26a5052fc859"):
                document["product_ids"].remove(1946)
        assert not loaded.search(
            "Netzeinspeisung Eigenverbrauch",
            "de",
            [1946],
            publication=Snapshot.read(revoked),
        )
    finally:
        loaded.close()
