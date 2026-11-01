"""Manufacturer-original matrix rows, supporting axes and consumer citations."""

from __future__ import annotations

import gzip
import json
import sqlite3
from copy import deepcopy
from functools import partial
from pathlib import Path
from typing import Any

from test_chunking import Words
from test_publication import authority
from test_table_compiler_axis import ETR_SHA, etr_source
from test_table_compiler_axis import FIXTURES as AXIS_FIXTURES

from index import corpus, store
from index.chunking import Chunk
from index.compatibility_physical import extract_compatibility_evidence
from index.corpus import DocumentRow
from index.physical_evidence import attach_physical_evidence
from index.publication import compile_publication
from index.table_compiler import external_axis_anchors
from linker_genie.compatibility_physical import physical_key, valid_physical_evidence
from linker_genie.facts import knowledge_qualifications
from linker_genie.hydrate import cited_documents, hydrate
from linker_genie.knowledge import KnowledgeSearch, model_view, record
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex
from linker_genie.schema import DocumentBlock, TextBlock, TurnOutput

FIXTURE = (
    Path(__file__).parent
    / "fixtures/publication-compiler/compatibility-physical.json.gz"
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


def test_physical_axis_replays_existing_original_pdf() -> None:
    import pypdfium2

    _, chunks = etr_source("en")
    pdf = pypdfium2.PdfDocument(AXIS_FIXTURES / f"{ETR_SHA}.pdf")
    try:
        found = extract_compatibility_evidence(pdf, ETR_SHA, chunks)
    finally:
        pdf.close()
    assert len(found) == 1
    evidence = found[0]
    assert valid_physical_evidence(
        evidence,
        ETR_SHA,
        str(evidence["target_chunk_id"]),
        str(evidence["source_text"]),
    )
    models = evidence["models"]
    assert isinstance(models, list)
    assert [item["text"] for item in models] == [
        "GW80K-ETR-G10",
        "GW99.99K-ETR-G10",
        "GW100K-ETR-G10",
        "GW110K-ETR-G10",
        "GW124.99K-ETR-G10",
        "GW125K-ETR-G10",
    ]


def test_original_pdf_axes_and_conditions_bind_both_subjects() -> None:
    raw, chunks, physical = fixture()
    chunks = attach_physical_evidence(chunks, physical)
    anchors = external_axis_anchors(chunks)
    compiled, scopes = compile_fixture(raw, chunks)
    inverter = [
        c
        for c in compiled
        if scopes.get(c.id, {}).get("basis") == "compatibility_inverter"
    ]
    iot = [
        c for c in compiled if scopes.get(c.id, {}).get("basis") == "compatibility_iot"
    ]
    assert len(inverter) == 30 and len(iot) == 1
    links = {
        (c.doc_sha256[:12], pid)
        for c in inverter
        for pid in scopes[c.id]["product_ids"]
    }
    assert {
        (prefix, pid)
        for prefix in ("8951dd1d8a64", "ea081f6f6fb2")
        for pid in (1946, 1947, 1948, 3595, 6507, 6508, 6509, 6510, 6511)
    } <= links
    assert all(6506 not in scopes[c.id]["product_ids"] for c in inverter)
    assert all(1957 not in scopes[c.id]["product_ids"] for c in inverter)
    assert scopes[iot[0].id]["product_ids"] == [2394, 2409, 6321]
    assert "SEC3000C version ≥03" in iot[0].text
    assert "single-unit anti-reflux" in iot[0].text
    assert "ARM：LC：410-02134-01(66)" in iot[0].text
    assert "DSP：master:410-04077-02(29)" in iot[0].text
    assert "DSP：slave：410-04078-01(06)" in iot[0].text
    assert "Control board:410-02193-01(14)" in iot[0].text
    assert "410-02174-01(14) Single network port" in iot[0].text
    assert "*For global, Can't parellel with ET50 and ESA261" in iot[0].text
    assert "G11" not in iot[0].text and "GMK330" not in iot[0].text

    snap = Snapshot.read(raw)
    for chunk in (inverter[0], iot[0]):
        proof = scopes[chunk.id]
        permitted = partial(
            authorize_chunk,
            products=snap.products,
            documents=snap.documents,
            chunk_id=chunk.id,
            text=chunk.text,
            external_axis_anchors=anchors,
            require_table_anchor=True,
        )
        assert permitted(
            chunk.doc_sha256,
            proof["product_ids"],
            proof["associations"],
            proof,
        )
        assert not permitted(
            chunk.doc_sha256,
            proof["product_ids"],
            proof["associations"][:-1],
            proof,
        )
        assert not permitted(
            chunk.doc_sha256,
            proof["product_ids"],
            proof["associations"],
            proof,
            external_axis_anchors={},
        )
    evidence = physical[0]
    changed = deepcopy(evidence)
    changed["models"][0]["text"] = "GW75K-ETR-G10"  # type: ignore[index]
    assert not valid_physical_evidence(
        changed,
        str(evidence["source_sha256"]),
        str(evidence["target_chunk_id"]),
        str(evidence["source_text"]),
    )
    iot_evidence = next(
        item
        for item in physical
        if item["kind"] == "iot_matrix" and item["source_page"] == 7
    )
    forged = deepcopy(iot_evidence)
    forged["row_text"] = str(forged["row_text"]).replace("version ≥03", "version ≥01")
    assert not valid_physical_evidence(
        forged,
        str(iot_evidence["source_sha256"]),
        str(iot_evidence["target_chunk_id"]),
        str(iot_evidence["source_text"]),
    )


def test_iot_requires_both_untampered_original_pages() -> None:
    raw, original, evidence = fixture()
    chunks = attach_physical_evidence(original, evidence)
    compiled, scopes = compile_fixture(raw, chunks)
    iot = next(
        c for c in compiled if scopes.get(c.id, {}).get("basis") == "compatibility_iot"
    )
    proof = scopes[iot.id]
    anchors = external_axis_anchors(chunks)
    snap = Snapshot.read(raw)
    permitted = partial(
        authorize_chunk,
        iot.doc_sha256,
        proof["product_ids"],
        proof["associations"],
        proof,
        products=snap.products,
        documents=snap.documents,
        chunk_id=iot.id,
        text=iot.text,
        require_table_anchor=True,
    )
    assert permitted(external_axis_anchors=anchors)
    for page in (7, 9):
        source = next(
            item
            for item in evidence
            if item["kind"] == "iot_matrix" and item["source_page"] == page
        )
        key = physical_key(str(source["target_chunk_id"]))
        missing = dict(anchors)
        del missing[key]
        assert not permitted(external_axis_anchors=missing)
        for field in ("row_text", "source_text"):
            altered = deepcopy(anchors)
            altered[key][field] += " altered"
            assert not permitted(external_axis_anchors=altered)
        absent = [item for item in evidence if item is not source]
        without_page = attach_physical_evidence(original, absent)
        output, remaining = compile_fixture(raw, without_page)
        assert not any(
            remaining.get(c.id, {}).get("basis") == "compatibility_iot" for c in output
        )
    assert not permitted(
        external_axis_anchors=anchors,
        text=iot.text.replace("*For global, Can't parellel with ET50 and ESA261", ""),
    )


def test_out_of_range_model_is_not_proven_even_if_woo_links_it() -> None:
    raw, original, evidence = fixture()
    for doc in raw["documents"]:
        if doc["blob_sha256"].startswith(("8951dd1d", "ea081f6f")):
            doc["product_ids"].append(
                6506
            )  # GW75K-ET-G10 is outside the 80–100 kW column.
            next(p for p in raw["products"] if p["product_id"] == 6506)[
                "documents"
            ].append(doc["document_id"])
    chunks = attach_physical_evidence(original, evidence)
    compiled, scopes = compile_fixture(raw, chunks)
    assert not any(
        6506 in scopes[c.id]["product_ids"]
        for c in compiled
        if c.id in scopes and scopes[c.id]["basis"] == "compatibility_inverter"
    )


def test_sqlite_consumer_cites_both_sources_and_fences_withdrawals(
    tmp_path: Path,
) -> None:
    raw, original, evidence = fixture()
    chunks = attach_physical_evidence(original, evidence)
    compiled, scopes = compile_fixture(raw, chunks)
    snap = Snapshot.read(raw)
    folder = tmp_path / "corpus"
    document_rows = []
    for doc in raw["documents"]:
        models = tuple(
            p["model"] for p in raw["products"] if p["product_id"] in doc["product_ids"]
        )
        document_rows.append(
            DocumentRow(
                doc["blob_sha256"],
                (doc["url"],),
                doc["title"],
                "",
                (),
                models,
                "datasheet"
                if doc["blob_sha256"].startswith(("4f717804", "76df70ea"))
                else "compatibility",
                doc["lang"],
                max(c.page for c in chunks if c.doc_sha256 == doc["blob_sha256"]),
                "indexed",
            )
        )
    corpus.write(
        folder,
        corpus.Meta(
            "physical-compatibility",
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
        document_rows,
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
        snapshot: Snapshot, pid: int, query: str, lang: str = "en"
    ) -> tuple[dict[str, Any], Any]:
        return record(
            KnowledgeSearch(lambda: loaded, Authority(snapshot)),  # type: ignore[arg-type]
            {"query": query, "lang": lang, "product_ids": [pid]},
            lang,
        )

    try:
        payload, facts = search(
            snap, 1946, "GW80K-ET-G10 GW61.4-BAT-AC-G10 compatibility"
        )
        match = next(
            h
            for h in payload["hits"]
            if "inverter-series" in h["chunk_id"] and "GW61.4-BAT-AC-G10" in h["text"]
        )
        assert match["supporting_documents"][0]["chunk_id"].startswith("4f717804")
        assert match["qualification_required"] is True
        answer = hydrate(
            TurnOutput(
                language="en",
                blocks=[TextBlock(text="Compatible", refs=[match["chunk_id"]])],
            ),
            facts,
        )
        assert isinstance(answer.blocks[0], TextBlock)
        assert "cannot achieve full power output" in answer.blocks[0].text
        assert "Battery Working Voltage" in answer.blocks[0].text
        assert any(
            h.get("supporting_sources")
            for h in model_view(payload)["hits"]
            if h["chunk_id"] == match["chunk_id"]
        )
        refs = [
            d.ref
            for d in cited_documents(
                TurnOutput(
                    language="en",
                    blocks=[TextBlock(text="Compatible", refs=[match["chunk_id"]])],
                ),
                facts,
            )
        ]
        assert (
            match["chunk_id"] in refs
            and match["supporting_documents"][0]["chunk_id"] in refs
        )
        assert facts.documents[refs[0]].url != facts.documents[refs[1]].url
        german, german_facts = search(
            snap, 1946, "GW80K-ET-G10 GW61.4-BAT-AC-G10 Kompatibilität", "de"
        )
        german_hit = next(
            h
            for h in german["hits"]
            if h["chunk_id"].startswith("ea081f6f")
            and "inverter-series" in h["chunk_id"]
            and "GW61.4-BAT-AC-G10" in h["text"]
        )
        german_answer = hydrate(
            TurnOutput(
                language="de",
                blocks=[TextBlock(text="Kompatibel", refs=[german_hit["chunk_id"]])],
            ),
            german_facts,
        )
        assert isinstance(german_answer.blocks[0], TextBlock)
        assert "nicht die volle Ausgangsleistung" in german_answer.blocks[0].text

        for prefix, pid in (("4f717804", 1946), ("8951dd1d", 1954)):
            changed = deepcopy(raw)
            next(
                d for d in changed["documents"] if d["blob_sha256"].startswith(prefix)
            )["product_ids"].remove(pid)
            result, _ = search(
                Snapshot.read(changed),
                1946,
                "GW80K-ET-G10 GW61.4-BAT-AC-G10 compatibility",
            )
            assert all(h["chunk_id"] != match["chunk_id"] for h in result["hits"])
        for prefix in ("4f717804", "8951dd1d"):
            changed = deepcopy(raw)
            next(
                d for d in changed["documents"] if d["blob_sha256"].startswith(prefix)
            )["role"] = "manual"
            result, _ = search(
                Snapshot.read(changed),
                1946,
                "GW80K-ET-G10 GW61.4-BAT-AC-G10 compatibility",
            )
            assert all(h["chunk_id"] != match["chunk_id"] for h in result["hits"])
        for pid in (2394, 2409, 6321):
            result, iot_facts = search(
                snap, pid, "GW125/261-ESA-LCN-G10 GM330 SEC3000C version"
            )
            assert any(
                "-iot-" in h["chunk_id"]
                and "version" in h["text"]
                and h.get("qualification_required") is True
                for h in result["hits"]
            )
            target = next(h for h in result["hits"] if "-iot-" in h["chunk_id"])
            assert [note["page"] for note in target["qualifications"]] == [7, 9]
            assert target["supporting_documents"][0]["page"] == 9
            model_hit = next(
                h
                for h in model_view(result)["hits"]
                if h["chunk_id"] == target["chunk_id"]
            )
            assert (
                "page 9 global statement concerns parallel operation"
                in model_hit["compatibility_instruction"]
            )
            assert model_hit["supporting_sources"][0]["page"] == 9
            assert "410-04077-02" in model_hit["text"]
            assert "Can't parellel with ET50 and ESA261" in model_hit["text"]
            for page in (7, 9):
                truncated = deepcopy(target)
                truncated["qualifications"] = [
                    note for note in target["qualifications"] if note["page"] != page
                ]
                truncated["text"] = "\n".join(
                    line
                    for line in target["text"].splitlines()
                    if not (line.startswith("*") and line.endswith(f"(p. {page})"))
                )
                assert knowledge_qualifications(truncated) is None
            conditional_answer = hydrate(
                TurnOutput(
                    language="en",
                    blocks=[TextBlock(text="Compatible", refs=[target["chunk_id"]])],
                ),
                iot_facts,
            )
            assert isinstance(conditional_answer.blocks[0], TextBlock)
            assert "single-unit anti-reflux" in conditional_answer.blocks[0].text
            assert "SEC3000C version ≥03" in conditional_answer.blocks[0].text
            assert "410-02134-01(66)" in conditional_answer.blocks[0].text
            assert "410-04077-02(29)" in conditional_answer.blocks[0].text
            assert "410-04078-01(06)" in conditional_answer.blocks[0].text
            assert "410-02193-01(14)" in conditional_answer.blocks[0].text
            assert "410-02174-01(14)" in conditional_answer.blocks[0].text
            assert (
                "Can't parellel with ET50 and ESA261"
                in conditional_answer.blocks[0].text
            )
            citations = [
                b for b in conditional_answer.blocks if isinstance(b, DocumentBlock)
            ]
            assert {b.url for b in citations} == {
                target["doc_url"] + "#page=7",
                target["doc_url"] + "#page=9",
            }
            assert {str(b.label).rsplit("\u00a0", 1)[-1] for b in citations} == {"7", "9"}

            revoked = deepcopy(raw)
            next(
                d
                for d in revoked["documents"]
                if d["blob_sha256"].startswith("6f33b836")
            )["product_ids"].remove(pid)
            after_revocation, _ = search(
                Snapshot.read(revoked),
                pid,
                "GW125/261-ESA-LCN-G10 GM330 SEC3000C version",
            )
            assert all(
                h["chunk_id"] != target["chunk_id"] for h in after_revocation["hits"]
            )

        german_result, german_facts = search(
            snap, 6321, "GW125/261-ESA-LCN-G10 GM330 SEC3000C version", "de"
        )
        german_iot = next(h for h in german_result["hits"] if "-iot-" in h["chunk_id"])
        german_answer = hydrate(
            TurnOutput(
                language="de",
                blocks=[TextBlock(text="Kompatibel", refs=[german_iot["chunk_id"]])],
            ),
            german_facts,
        )
        assert isinstance(german_answer.blocks[0], TextBlock)
        assert (
            "Herstellerbedingung (englisches Original):" in german_answer.blocks[0].text
        )
        assert "single-unit anti-reflux" in german_answer.blocks[0].text
        assert "Can't parellel with ET50 and ESA261" in german_answer.blocks[0].text
        assert {
            b.url for b in german_answer.blocks if isinstance(b, DocumentBlock)
        } == {german_iot["doc_url"] + "#page=7", german_iot["doc_url"] + "#page=9"}

        # Recheck authorization against each actual database source row on every
        # search, including a removed row and a changed row for each page.
        iot_scope = next(
            s for s in scopes.values() if s.get("basis") == "compatibility_iot"
        )
        relation = iot_scope["compatibility_iot"]
        with sqlite3.connect(path) as writer:
            for key in ("first_chunk_id", "second_chunk_id"):
                cid = relation[key]
                original_text = writer.execute(
                    "SELECT text FROM chunks WHERE id = ?", (cid,)
                ).fetchone()[0]
                for column, changed, restore in (
                    ("id", cid + "-missing", cid),
                    ("text", original_text + " altered", original_text),
                ):
                    writer.execute(
                        f"UPDATE chunks SET {column} = ? WHERE id = ?", (changed, cid)
                    )
                    writer.commit()
                    try:
                        changed_result, _ = search(
                            snap, 6321, "GW125/261-ESA-LCN-G10 GM330 SEC3000C version"
                        )
                        assert all(
                            h["chunk_id"] != target["chunk_id"]
                            for h in changed_result["hits"]
                        )
                    finally:
                        lookup = changed if column == "id" else cid
                        writer.execute(
                            f"UPDATE chunks SET {column} = ? WHERE id = ?",
                            (restore, lookup),
                        )
                        writer.commit()
        for pid in (2397, 2415):
            result, _ = search(
                snap, pid, "GW125/261-ESA-LCN-G10 GM330 SEC3000C version"
            )
            assert all("-iot-" not in h["chunk_id"] for h in result["hits"])
    finally:
        loaded.close()
