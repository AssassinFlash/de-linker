"""The conditional three-source HS3 proof through the SQLite consumer."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any

from test_chunking import Words
from test_hs3_evidence import inputs
from test_publication import authority

from index import corpus, store
from index.corpus import DocumentRow
from index.publication import compile_publication
from linker_genie.ground import check
from linker_genie.hs3_evidence import (
    DATA_MODELS,
    DATASHEET,
    MANUAL_MODEL,
    SOURCES,
    hs3_anchor_key,
)
from linker_genie.hydrate import hydrate
from linker_genie.knowledge import KnowledgeSearch, model_view, record
from linker_genie.publication import Snapshot
from linker_genie.retrieval import DocumentIndex
from linker_genie.schema import DocumentBlock, TextBlock, TurnOutput


def test_hs3_conditional_sources_reach_the_consumer_and_revoke(tmp_path: Path) -> None:
    chunks, raw, _ = inputs()
    snap = Snapshot.read(raw)
    client = authority(raw)
    try:
        compiled, scopes = compile_publication(chunks, raw, client, Words())
    finally:
        client.close()
    proofs = [s for s in scopes.values() if s["basis"] == "hs3_conditional_certificate"]
    assert len(proofs) == 5
    folder = tmp_path / "corpus"
    rows = [
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
    corpus.write(
        folder,
        corpus.Meta(
            "hs3-consumer",
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
        rows,
        [(p["product_id"], p["model"]) for p in raw["products"]],
        compiled,
    )
    target = tmp_path / "index.sqlite"
    store.export(folder, target)
    index = DocumentIndex(target, encoder=None)

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
        current: Snapshot, pid: int, lang: str = "en"
    ) -> tuple[dict[str, Any], Any]:
        return record(
            KnowledgeSearch(lambda: index, Authority(current)),  # type: ignore[arg-type]
            {
                "query": "HS3-12K-T2-W/G-PX EU declaration battery modules",
                "lang": lang,
                "product_ids": [pid],
            },
        )

    try:
        # The same original datasheet table supports ordinary model-specific
        # projections and the conditional certificate. Both must survive the
        # index build and the runtime's independent source recheck.
        expected_power = {2198: 5000, 1186: 6000, 1187: 8000, 2199: 10000, 1185: 12000}
        datasheet = next(d for d in raw["documents"] if d["blob_sha256"] == DATASHEET)
        for product_id, power in expected_power.items():
            assert not any(
                row["product_id"] == product_id
                and row["document_id"] == datasheet["document_id"]
                for row in index.loaded()["unprepared_documents"]
            )
            model = snap.products[product_id]["model"]
            hits = index.search(
                f"{model} Rated Output Power",
                "en",
                [product_id],
                doc_types=["datasheet"],
                publication=snap,
            )
            assert any(
                hit.doc_sha256 == DATASHEET
                and hit.product_ids == (product_id,)
                and f"| Rated Output Power [W] | {power} |" in hit.text
                for hit in hits
            )
            conditional = index.search(
                f"{model} EU declaration battery modules",
                "en",
                [product_id],
                publication=snap,
            )
            assert any(hit.conditional_certificate for hit in conditional)

        pid = next(
            p["product_id"]
            for p in raw["products"]
            if p["model"] == "HS3-12K-T2-W/G-PX"
        )
        payload, facts = search(snap, pid)
        hit = next(
            h for h in payload["hits"] if h.get("conditional_certificate") is True
        )
        assert hit["title"] == "EU Declaration of Conformity"
        assert hit["product_models"] == ["HS3-12K-T2-W/G-PX"]
        assert hit["figures"] == {
            f"{hit['chunk_id']}.n{i}": str(i) for i in range(1, 9)
        }
        assert {s["chunk_id"] for s in hit["supporting_documents"]} == {
            DATA_MODELS,
            MANUAL_MODEL,
        }
        assert set(facts.supporting_documents[hit["chunk_id"]]) == {
            DATA_MODELS,
            MANUAL_MODEL,
        }
        # Each supporting source gets its own current reviewed title; an
        # unmapped source retains its own English title. No index rebuild.
        localized = deepcopy(raw)
        first_support, second_support = hit["supporting_documents"]
        first_doc = next(
            d
            for d in localized["documents"]
            if d["document_id"] == first_support["document_id"]
        )
        second_doc = next(
            d
            for d in localized["documents"]
            if d["document_id"] == second_support["document_id"]
        )
        first_doc["title_de"] = "Geprüfter deutscher Titel"
        second_doc["title_de"] = ""
        for language in ("en", "de"):
            localized_hit, localized_facts = search(
                Snapshot.read(localized), pid, language
            )
            localized_hit = next(
                h for h in localized_hit["hits"] if h.get("conditional_certificate")
            )
            sources = {
                s["document_id"]: s for s in localized_hit["supporting_documents"]
            }
            expected_first = (
                first_doc["title_de"] if language == "de" else first_doc["title"]
            )
            assert sources[first_doc["document_id"]]["title"] == expected_first
            assert sources[second_doc["document_id"]]["title"] == second_doc["title"]
            rendered = hydrate(
                TurnOutput(
                    language=language,
                    blocks=[TextBlock(text="", refs=[localized_hit["chunk_id"]])],
                ),
                localized_facts,
            )
            labels = {
                b.ref: b.label for b in rendered.blocks if isinstance(b, DocumentBlock)
            }
            assert labels[first_support["chunk_id"]].startswith(expected_first)
            assert labels[second_support["chunk_id"]].startswith(second_doc["title"])
        model_hit = next(
            h for h in model_view(payload)["hits"] if h["chunk_id"] == hit["chunk_id"]
        )
        assert (
            model_hit["conditional_certificate_answers"]
            == hit["conditional_certificate_answers"]
        )
        assert (
            "do not infer an unconditional certificate"
            in model_hit["conditional_instruction"]
        )
        assert (
            facts.conditional_certificate_answers[hit["chunk_id"]]
            == hit["conditional_certificate_answers"]
        )
        for language in ("en", "de"):
            answer = TurnOutput(
                language=language,
                blocks=[
                    TextBlock(
                        text=hit["conditional_certificate_answers"][language],
                        refs=[hit["chunk_id"]],
                    )
                ],
            )
            assert check(answer, facts).ok
            rendered = hydrate(answer, facts)
            assert isinstance(rendered.blocks[0], TextBlock)
            assert "{fact:" not in rendered.blocks[0].text
            links = {
                block.url
                for block in rendered.blocks
                if isinstance(block, DocumentBlock)
            }
            assert links == {
                hit["doc_url"] + "#page=1",
                *(
                    item["doc_url"] + f"#page={item['page']}"
                    for item in hit["supporting_documents"]
                ),
            }
        unqualified = TurnOutput(
            language="en",
            blocks=[TextBlock(text="This model is certified.", refs=[hit["chunk_id"]])],
        )
        assert not check(unqualified, facts).ok
        certificate = hit["document_id"]
        assert any(
            x["product_id"] == pid and x["document_id"] == certificate
            for x in index.loaded()["unprepared_documents"]
        )

        for ref in (
            certificate,
            *(s["document_id"] for s in hit["supporting_documents"]),
        ):
            changed = deepcopy(raw)
            next(d for d in changed["documents"] if d["document_id"] == ref)[
                "product_ids"
            ].remove(pid)
            result, _ = search(Snapshot.read(changed), pid)
            assert all(h["chunk_id"] != hit["chunk_id"] for h in result["hits"])
            if ref == datasheet["document_id"]:
                withdrawn = index.search(
                    "Rated Output Power",
                    "en",
                    [pid],
                    doc_types=["datasheet"],
                    publication=Snapshot.read(changed),
                )
                assert all(item.doc_sha256 != DATASHEET for item in withdrawn)
    finally:
        index.close()

    # Removing the native table digest must deny projections even though the
    # separately verified HS3 source text can still support the certificate.
    with sqlite3.connect(target) as db:
        (serialized,) = db.execute(
            "SELECT value FROM meta WHERE key = 'external_axis_anchors'"
        ).fetchone()
        anchors = json.loads(serialized)
        assert anchors[DATA_MODELS]["source_table"] == "docling:p2:#/tables/0"
        assert anchors[DATA_MODELS]["source_cells_sha256"]
        assert anchors[hs3_anchor_key(DATA_MODELS)]["text"]
        del anchors[DATA_MODELS]
        db.execute(
            "UPDATE meta SET value = ? WHERE key = 'external_axis_anchors'",
            (json.dumps(anchors),),
        )
    index = DocumentIndex(target, encoder=None)
    try:
        assert not index.search(
            "Rated Output Power",
            "en",
            [pid],
            doc_types=["datasheet"],
            publication=snap,
        )
        result, _ = search(snap, pid)
        assert any(h.get("conditional_certificate") is True for h in result["hits"])
    finally:
        index.close()

    # Runtime must inspect the retained originals, not just the serialized proof.
    with sqlite3.connect(target) as db:
        db.execute("DELETE FROM chunks WHERE id = ?", (next(iter(SOURCES)),))
    index = DocumentIndex(target, encoder=None)
    try:
        result, _ = search(snap, pid)
        assert all(h.get("conditional_certificate") is not True for h in result["hits"])
    finally:
        index.close()
