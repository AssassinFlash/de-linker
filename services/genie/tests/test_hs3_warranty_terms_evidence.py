"""Source, scope and actual consumer checks for SAJ HS3 standard warranty."""

from __future__ import annotations

import gzip
import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from test_chunking import Words
from test_publication import authority

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.publication import compile_publication
from index.table_compiler import external_axis_anchors
from linker_genie.figures import localize, tag
from linker_genie.ground import check
from linker_genie.hs3_evidence import (
    DATA_MODELS,
    DATASHEET,
    MANUAL,
    MANUAL_MODEL,
    hs3_anchors,
)
from linker_genie.hs3_warranty_terms import (
    INTERNET,
    MINIMUM,
    POLICY,
    PREFIX,
    ROW,
    SOURCES,
    anchors,
    valid_scope,
)
from linker_genie.hydrate import hydrate
from linker_genie.knowledge import KnowledgeSearch, record
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex
from linker_genie.schema import DocumentBlock, TextBlock, TurnOutput

FIXTURE = (
    Path(__file__).parent / "fixtures/publication-compiler/hs3-warranty-terms.json.gz"
)


def inputs() -> tuple[list[Chunk], dict[str, Any]]:
    data = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    return [Chunk(**item) for item in data["chunks"]], data["manifest"]


def compile_fixture(
    chunks: list[Chunk], raw: dict[str, Any]
) -> tuple[list[Chunk], dict[str, Any]]:
    client = authority(raw)
    try:
        return compile_publication(chunks, raw, client, Words())
    finally:
        client.close()


def all_anchors(chunks: list[Chunk]) -> dict[str, dict[str, Any]]:
    rows = [(c.id, c.doc_sha256, c.page, c.kind, c.text) for c in chunks]
    return {**anchors(rows), **hs3_anchors(rows)}


def test_exact_five_models_and_source_bound_conditions() -> None:
    chunks, raw = inputs()
    source = Snapshot.read(raw)
    compiled, scopes = compile_fixture(chunks, raw)
    units = [c for c in compiled if c.id.startswith(PREFIX)]
    assert {scopes[c.id]["product_ids"][0] for c in units} == {
        1185,
        1186,
        1187,
        2198,
        2199,
    }
    assert len(units) == 5
    for c in units:
        proof = scopes[c.id]
        assert "Ten years" in c.text and "Six months" in c.text
        assert (
            "| HS3 | 5.5 |" in c.text
            and "from the date of product shipment from SAJ" in c.text
        )
        assert (
            "has not been registered with SAJ" in c.text
            and "not connected to internet" in c.text
        )
        assert valid_scope(
            proof,
            proof["product_ids"],
            source.products,
            source.documents,
            sha=POLICY,
            chunk_id=c.id,
            text=c.text,
            external_axis_anchors=all_anchors(chunks),
        )
    original = next(c for c in chunks if c.id == ROW)
    assert not any(
        value in {"Ten years", "Six months"}
        for value in tag(original.id, original.text).figures.values()
    )
    assert localize("Ten years", "de") == "Ten years"
    assert localize("Six months", "de") == "Six months"
    assert localize("Ten years", "de", source_id=units[0].id + ".n1") == "zehn Jahre"
    assert localize("Six months", "de", source_id=units[0].id + ".n2") == "sechs Monate"


@pytest.mark.parametrize("role", ["policy", "datasheet", "manual"])
@pytest.mark.parametrize(
    "change", ["removed", "revision", "association", "product_link", "role"]
)
def test_each_document_and_both_association_directions_are_current(
    role: str, change: str
) -> None:
    chunks, raw = inputs()
    source = Snapshot.read(raw)
    compiled, scopes = compile_fixture(chunks, raw)
    unit = next(c for c in compiled if c.id.startswith(PREFIX))
    proof = scopes[unit.id]
    pid = proof["product_ids"][0]
    did = proof["warranty_scope"]["source_documents"][role]["document_id"]
    docs, products = deepcopy(source.documents), deepcopy(source.products)
    if change == "removed":
        del docs[did]
    elif change == "revision":
        docs[did]["document_revision"] += "-changed"
    elif change == "association":
        docs[did]["product_ids"].remove(pid)
    elif change == "product_link":
        products[pid]["documents"].remove(did)
    else:
        docs[did]["role"] = "document"
    assert not valid_scope(
        proof,
        [pid],
        products,
        docs,
        sha=POLICY,
        chunk_id=unit.id,
        text=unit.text,
        external_axis_anchors=all_anchors(chunks),
    )


def test_missing_or_tampered_original_never_grants_period() -> None:
    chunks, raw = inputs()
    for cid in (*SOURCES, DATA_MODELS, MANUAL_MODEL):
        altered = [
            replace(c, text=c.text + " altered") if c.id == cid else c for c in chunks
        ]
        output, scopes = compile_fixture(altered, raw)
        assert not any(c.id.startswith(PREFIX) for c in output), cid
        assert not any(
            s.get("basis") == "warranty_terms"
            and s.get("warranty_scope", {}).get("policy", {}).get("format")
            == "hs3_series_standard_warranty"
            for s in scopes.values()
        )
    for wrong in (
        "HS3-TenK-T2-W/G-PX",
        "HS3-10K-T2-W/G-BX",
        "HS3-10K-T2-W/G-PX-BE",
        "BU3-5.0-TV2-PRO",
    ):
        changed = deepcopy(raw)
        target = next(p for p in changed["products"] if p["product_id"] == 2199)
        target["model"] = wrong
        output, scopes = compile_fixture(chunks, changed)
        assert not any(
            c.id.startswith(PREFIX) and scopes[c.id]["product_ids"] == [2199]
            for c in output
        )
    changed = deepcopy(raw)
    policy = next(d for d in changed["documents"] if d["blob_sha256"] == POLICY)
    policy["type"], policy["role"] = "document", ""
    output, _ = compile_fixture(chunks, changed)
    assert not any(c.id.startswith(PREFIX) for c in output)


def test_previous_claims_procedure_stays_authorized() -> None:
    data = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    chunks, raw = inputs()
    with patch(
        "index.hs3_warranty_terms.compile_hs3_warranty_terms", return_value=([], {})
    ):
        baseline, baseline_scopes = compile_fixture(chunks, raw)
    updated, updated_scopes = compile_fixture(chunks, raw)
    assert {c.id for c in baseline} == {
        c.id for c in updated if not c.id.startswith(PREFIX)
    }
    assert baseline_scopes == {
        cid: scope
        for cid, scope in updated_scopes.items()
        if not cid.startswith(PREFIX)
    }
    previous, proof = Chunk(**data["previous_procedure"]), data["previous_scope"]
    source = Snapshot.read(raw)
    external = external_axis_anchors(chunks)
    external.update(all_anchors(chunks))
    assert authorize_chunk(
        previous.doc_sha256,
        proof["product_ids"],
        proof["associations"],
        proof,
        products=source.products,
        documents=source.documents,
        chunk_id=previous.id,
        text=previous.text,
        external_axis_anchors=external,
        require_table_anchor=True,
    )


def test_sqlite_real_consumer_ground_hydrate_and_revocation(tmp_path: Path) -> None:
    chunks, raw = inputs()
    snap = Snapshot.read(raw)
    compiled, scopes = compile_fixture(chunks, raw)
    previous = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    prior_chunk = Chunk(**previous["previous_procedure"])
    compiled.append(prior_chunk)
    scopes[prior_chunk.id] = previous["previous_scope"]
    documents = [
        DocumentRow(
            doc["blob_sha256"],
            (doc["url"],),
            doc["title"],
            "",
            (),
            tuple(
                p["model"]
                for p in raw["products"]
                if p["product_id"] in doc["product_ids"]
            ),
            doc["type"],
            doc["lang"],
            max(c.page for c in chunks if c.doc_sha256 == doc["blob_sha256"]),
            "indexed",
        )
        for doc in raw["documents"]
    ]
    folder, path = tmp_path / "corpus", tmp_path / "index.sqlite"
    corpus.write(
        folder,
        corpus.Meta(
            "hs3-warranty",
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
    store.export(folder, path)
    index = DocumentIndex(path, encoder=None)

    class Authority:
        def __init__(self, current: Snapshot) -> None:
            self.current = current

        def snapshot(self) -> Snapshot:
            return self.current

        def identify_text(self, _: str) -> dict[str, str]:
            return {}

        def validate(self, current: Snapshot) -> None:
            assert current is self.current

    def search(current: Snapshot, pid: int, lang: str) -> tuple[dict[str, Any], Any]:
        model = current.products[pid]["model"]
        return record(
            KnowledgeSearch(lambda: index, Authority(current)),  # type: ignore[arg-type]
            {
                "query": f"{model} standard warranty period start",
                "lang": lang,
                "product_ids": [pid],
            },
            lang,
        )

    try:
        previous_hits = index.search(
            "HS3-12K-T2-W/G-PX claim warranty distributor installer",
            "en",
            [1185],
            publication=snap,
        )
        assert any(
            hit.chunk_id == prior_chunk.id and hit.warranty_procedure
            for hit in previous_hits
        )
        for pid in (1185, 1186, 1187, 2198, 2199):
            for lang in ("en", "de"):
                payload, facts = search(snap, pid, lang)
                hit = next(
                    h for h in payload["hits"] if h["chunk_id"].startswith(PREFIX)
                )
                assert hit["warranty_terms"] and hit["qualification_required"]
                assert len(hit["qualifications"]) == 7
                assert [x["page"] for x in hit["supporting_documents"]] == [2, 18]
                body = hit["warranty_answers"]["period"]
                out = TurnOutput(
                    language=lang, blocks=[TextBlock(text=body, refs=[hit["chunk_id"]])]
                )
                verdict = check(
                    out, facts, question=f"{snap.products[pid]['model']} warranty"
                )
                assert verdict.ok, verdict.failures
                result = hydrate(out, facts)
                assert isinstance(result.blocks[0], TextBlock)
                rendered = result.blocks[0].text
                assert "{fact:" not in rendered
                assert ("Ten years" if lang == "en" else "zehn Jahre") in rendered
                assert ("Six months" if lang == "en" else "sechs Monate") in rendered
                assert ("5.5" if lang == "en" else "5,5") in rendered
                assert (
                    "from the date of product shipment from SAJ"
                    if lang == "en"
                    else "ab Versand durch SAJ"
                ) in rendered
                assert facts.documents[INTERNET].url == hit["doc_url"]
                assert facts.documents[INTERNET].page == 3
                assert facts.documents[MINIMUM].url == hit["doc_url"]
                assert facts.documents[MINIMUM].page == 3
                links = {b.url for b in result.blocks if isinstance(b, DocumentBlock)}
                assert any(link and "saj_hs3_warranty" in link for link in links)
                assert any(link and "datasheet" in link for link in links)
                assert any(link and "User-Manual" in link for link in links)
        pid = 1185
        payload, _ = search(snap, pid, "en")
        target = next(
            h["chunk_id"] for h in payload["hits"] if h["chunk_id"].startswith(PREFIX)
        )
        for sha in (POLICY, DATASHEET, MANUAL):
            for change in ("remove", "reverse", "revision", "role"):
                changed = deepcopy(raw)
                doc = next(d for d in changed["documents"] if d["blob_sha256"] == sha)
                product = next(p for p in changed["products"] if p["product_id"] == pid)
                if change == "remove":
                    doc["product_ids"].remove(pid)
                elif change == "reverse":
                    product["documents"].remove(doc["document_id"])
                elif change == "revision":
                    doc["document_revision"] += "-changed"
                else:
                    doc["role"] = "document"
                hits, _ = search(Snapshot.read(changed), pid, "en")
                assert all(h["chunk_id"] != target for h in hits["hits"]), (sha, change)
        for source_id in (ROW, INTERNET, MINIMUM, DATA_MODELS, MANUAL_MODEL):
            original_text = next(c.text for c in chunks if c.id == source_id)
            with sqlite3.connect(path) as db:
                db.execute(
                    "UPDATE chunks SET text = ? WHERE id = ?",
                    (original_text + " altered", source_id),
                )
            hits, _ = search(snap, pid, "en")
            assert all(h["chunk_id"] != target for h in hits["hits"]), source_id
            with sqlite3.connect(path) as db:
                db.execute(
                    "UPDATE chunks SET text = ? WHERE id = ?",
                    (original_text, source_id),
                )
    finally:
        index.close()
