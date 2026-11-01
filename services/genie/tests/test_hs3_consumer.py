"""The conditional three-source HS3 proof through the SQLite consumer."""

from __future__ import annotations

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
from linker_genie.hs3_evidence import DATA_MODELS, MANUAL_MODEL, SOURCES
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

    def search(current: Snapshot, pid: int) -> tuple[dict[str, Any], Any]:
        return record(
            KnowledgeSearch(lambda: index, Authority(current)),  # type: ignore[arg-type]
            {
                "query": "HS3-12K-T2-W/G-PX EU declaration battery modules",
                "lang": "en",
                "product_ids": [pid],
            },
        )

    try:
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
