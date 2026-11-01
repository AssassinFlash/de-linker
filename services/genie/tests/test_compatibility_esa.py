"""ESA IoT relations retain source conditions and both current grants."""

from __future__ import annotations

import gzip
import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from test_chunking import Words
from test_publication import authority

from index import corpus, store
from index.chunking import Chunk
from index.compatibility_esa import extract_esa_evidence
from index.corpus import DocumentRow
from index.physical_evidence import attach_physical_evidence
from index.publication import compile_publication
from index.table_compiler import external_axis_anchors
from linker_genie.compatibility_esa import (
    IOT,
    IOT_9,
    IOT_13,
    MANUAL,
    MANUAL_METER,
    METER_CT,
    METER_PARALLEL,
    MODEL,
    P6,
    P9,
    P13,
    row_key,
    valid_row,
)
from linker_genie.hydrate import cited_documents, hydrate
from linker_genie.knowledge import KnowledgeSearch, record
from linker_genie.publication import Snapshot
from linker_genie.retrieval import DocumentIndex
from linker_genie.schema import DocumentBlock, TextBlock, TurnOutput

FIXTURE = (
    Path(__file__).parent / "fixtures/publication-compiler/compatibility-esa.json.gz"
)


def fixture() -> tuple[dict[str, Any], list[Chunk], list[dict[str, object]]]:
    data = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    return data["manifest"], [Chunk(**row) for row in data["chunks"]], data["evidence"]


def compile_fixture(
    raw: dict[str, Any], chunks: list[Chunk]
) -> tuple[list[Chunk], dict[str, Any]]:
    client = authority(raw)
    try:
        return compile_publication(chunks, raw, client, Words())
    finally:
        client.close()


def test_original_pdf_physical_extraction_when_available() -> None:
    import pypdfium2

    original = Path.home() / "de-linker-data/pdf" / f"{IOT}.pdf"
    if not original.exists():
        pytest.skip("manufacturer original is not installed")
    _, chunks, expected = fixture()
    pdf = pypdfium2.PdfDocument(original)
    try:
        assert extract_esa_evidence(pdf, IOT, chunks) == expected
    finally:
        pdf.close()


def test_each_relation_requires_its_own_physical_rows_and_exact_model() -> None:
    raw, original, evidence = fixture()
    chunks = attach_physical_evidence(original, evidence)
    anchors = external_axis_anchors(chunks)
    for page, cid in ((6, P6), (9, P9), (13, P13)):
        row = anchors[row_key(cid)]
        assert row["source_page"] == page
        assert valid_row(row, IOT, cid, row["source_text"])
        changed = deepcopy(row)
        changed["row_text"] += " changed"
        assert not valid_row(changed, IOT, cid, row["source_text"])
    assert IOT_13.removeprefix("*2: ") == anchors[row_key(P13)]["row_text"]
    assert (
        IOT_9.removeprefix("*1: ")
        == anchors[row_key(P9)]["row_text"].rsplit("*1 ", 1)[1]
    )
    manual = next(c.text for c in original if c.id == MANUAL_METER)
    assert METER_CT.removeprefix("*1: ") in manual
    assert METER_PARALLEL.removeprefix("*2: ") in manual
    compiled, scopes = compile_fixture(raw, chunks)
    units = {
        scopes[c.id]["product_ids"][0]: c
        for c in compiled
        if scopes.get(c.id, {}).get("basis") == "compatibility_esa"
    }
    assert set(units) == {2397, 2415}
    assert MODEL in units[2397].text and "120A:40mA" in units[2397].text
    assert "more than 2 Inverters" in units[2397].text
    assert "DCDC-08" in units[2415].text and "BMS-06" in units[2415].text
    assert "For the HEMS parallel configuration" in units[2415].text
    assert "In total ≤4" in units[2415].text and "version）≥05" in units[2415].text
    assert "4+4" not in units[2397].text and "G11" not in units[2397].text
    assert "G11" not in units[2415].text
    for removed, surviving in ((6, {2415}), (9, {2397}), (13, {2397})):
        surviving_evidence = [row for row in evidence if row["source_page"] != removed]
        remaining = attach_physical_evidence(original, surviving_evidence)
        result, remaining_scopes = compile_fixture(raw, remaining)
        assert {
            remaining_scopes[c.id]["product_ids"][0]
            for c in result
            if remaining_scopes.get(c.id, {}).get("basis") == "compatibility_esa"
        } == surviving
    wrong_model = deepcopy(raw)
    next(p for p in wrong_model["products"] if p["product_id"] == 3556)["model"] = (
        "GW10K-ETA-G21"
    )
    result, remaining_scopes = compile_fixture(wrong_model, chunks)
    assert not any(
        remaining_scopes.get(c.id, {}).get("basis") == "compatibility_esa"
        for c in result
    )


def test_sqlite_consumer_citations_conditions_and_current_ownership(
    tmp_path: Path,
) -> None:
    raw, original, evidence = fixture()
    chunks = attach_physical_evidence(original, evidence)
    compiled, scopes = compile_fixture(raw, chunks)
    snap = Snapshot.read(raw)
    folder = tmp_path / "corpus"
    documents = [
        DocumentRow(
            d["blob_sha256"],
            (d["url"],),
            d["title"],
            "",
            (),
            tuple(
                p["model"]
                for p in raw["products"]
                if p["product_id"] in d["product_ids"]
            ),
            "manual" if d["blob_sha256"] == MANUAL else "compatibility",
            d["lang"],
            max(c.page for c in chunks if c.doc_sha256 == d["blob_sha256"]),
            "indexed",
        )
        for d in raw["documents"]
    ]
    corpus.write(
        folder,
        corpus.Meta(
            "esa-iot",
            None,
            None,
            "original",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {cid: p["product_ids"] for cid, p in scopes.items()},
                "chunk_scopes": scopes,
            },
            model_identity_revision=snap.model_identity_revision,
        ),
        documents,
        [(p["product_id"], p["model"]) for p in raw["products"]],
        compiled,
    )
    path = tmp_path / "index.sqlite"
    store.export(folder, path)
    loaded = DocumentIndex(path, encoder=None)

    class Authority:
        def __init__(self, current: Snapshot) -> None:
            self.current = current

        def snapshot(self) -> Snapshot:
            return self.current

        def identify_text(self, _: str) -> dict[str, str]:
            return {}

        def validate(self, current: Snapshot) -> None:
            assert current is self.current

    def search(
        current: dict[str, Any], pid: int, lang: str = "en"
    ) -> tuple[dict[str, Any], Any]:
        name = "GMK330" if pid == 2397 else "EzManager3000"
        return record(
            KnowledgeSearch(lambda: loaded, Authority(Snapshot.read(current))),  # type: ignore[arg-type]
            {
                "query": f"{name} {MODEL} compatibility firmware",
                "lang": lang,
                "product_ids": [pid],
            },
            lang,
        )

    try:
        for pid in (2397, 2415):
            payload, facts = search(raw, pid)
            hit = next(h for h in payload["hits"] if "-esa-iot-" in h["chunk_id"])
            assert hit["qualification_required"]
            assert any(d["page"] == 4 for d in hit["supporting_documents"])
            assert [x["page"] for x in hit["qualifications"]] == (
                [35, 35] if pid == 2397 else [9, 13]
            )
            turn = TurnOutput(
                language="en",
                blocks=[TextBlock(text="Compatible", refs=[hit["chunk_id"]])],
            )
            result = hydrate(turn, facts)
            assert isinstance(result.blocks[0], TextBlock)
            assert ("more than 2" if pid == 2397 else "DCDC-08") in result.blocks[
                0
            ].text
            refs = cited_documents(turn, facts)
            assert any(
                d.ref == hit["supporting_documents"][0]["chunk_id"] for d in refs
            )
            assert any(facts.documents[d.ref].page == 4 for d in refs)
            if pid == 2397:
                manual_condition = hit["qualifications"][0]["chunk_id"]
                manual_support = next(
                    item for item in hit["supporting_documents"] if item["page"] == 35
                )
                assert (
                    facts.documents[manual_condition].url == manual_support["doc_url"]
                )
                assert facts.documents[manual_condition].url != hit["doc_url"]
            german, german_facts = search(raw, pid, "de")
            de_hit = next(h for h in german["hits"] if h["chunk_id"] == hit["chunk_id"])
            translated = hydrate(
                TurnOutput(
                    language="de",
                    blocks=[TextBlock(text="Kompatibel", refs=[de_hit["chunk_id"]])],
                ),
                german_facts,
            )
            assert isinstance(translated.blocks[0], TextBlock)
            assert (
                "nicht austauschbar" if pid == 2397 else "dreiphasigen Parallelbetrieb"
            ) in translated.blocks[0].text
            assert any(isinstance(block, DocumentBlock) for block in translated.blocks)
            for prefix, owner in (("6f33b836", pid), ("67a7f715", 3556)):
                for mutation in (
                    "doc_association",
                    "product_association",
                    "revision",
                    "product_revision",
                    "role",
                    "file",
                ):
                    changed = deepcopy(raw)
                    doc = next(
                        d
                        for d in changed["documents"]
                        if d["blob_sha256"].startswith(prefix)
                    )
                    product = next(
                        p for p in changed["products"] if p["product_id"] == owner
                    )
                    if mutation == "doc_association":
                        doc["product_ids"].remove(owner)
                    elif mutation == "product_association":
                        product["documents"].remove(doc["document_id"])
                    elif mutation == "revision":
                        doc["document_revision"] += "-changed"
                    elif mutation == "product_revision":
                        product["product_revision"] += "-changed"
                    elif mutation == "role":
                        doc["role"] = "certificate"
                    else:
                        changed["documents"].remove(doc)
                    current_result, _ = search(changed, pid)
                    assert all(
                        h["chunk_id"] != hit["chunk_id"] for h in current_result["hits"]
                    ), (pid, prefix, mutation)
            changed = deepcopy(raw)
            changed["products"] = [
                p for p in changed["products"] if p["product_id"] != 3556
            ]
            current_result, _ = search(changed, pid)
            assert all(h["chunk_id"] != hit["chunk_id"] for h in current_result["hits"])
    finally:
        loaded.close()


def test_missing_footnote_leaves_the_association_unprepared(tmp_path: Path) -> None:
    raw, original, evidence = fixture()
    chunks = attach_physical_evidence(
        original, [row for row in evidence if row["source_page"] != 13]
    )
    compiled, scopes = compile_fixture(raw, chunks)
    documents = [
        DocumentRow(
            d["blob_sha256"],
            (d["url"],),
            d["title"],
            "",
            (),
            tuple(
                p["model"]
                for p in raw["products"]
                if p["product_id"] in d["product_ids"]
            ),
            "manual" if d["blob_sha256"] == MANUAL else "compatibility",
            d["lang"],
            max(c.page for c in chunks if c.doc_sha256 == d["blob_sha256"]),
            "indexed",
        )
        for d in raw["documents"]
    ]
    folder, path = tmp_path / "corpus", tmp_path / "index.sqlite"
    corpus.write(
        folder,
        corpus.Meta(
            "esa-iot",
            None,
            None,
            "original",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {cid: p["product_ids"] for cid, p in scopes.items()},
                "chunk_scopes": scopes,
            },
            model_identity_revision=raw["model_identity_revision"],
        ),
        documents,
        [(p["product_id"], p["model"]) for p in raw["products"]],
        compiled,
    )
    store.export(folder, path)
    with sqlite3.connect(path) as db:
        pending = json.loads(
            db.execute(
                "SELECT value FROM meta WHERE key='unprepared_documents'"
            ).fetchone()[0]
        )
    iot = next(d["document_id"] for d in raw["documents"] if d["blob_sha256"] == IOT)
    assert {
        "document_id": iot,
        "product_id": 2415,
        "reason": "no_proven_passage",
    } in pending
    assert not any(
        item["document_id"] == iot and item["product_id"] == 2397 for item in pending
    )
