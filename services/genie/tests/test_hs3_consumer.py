"""The conditional three-source HS3 proof through the SQLite consumer."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

import pytest
from test_chunking import Words
from test_hs3_evidence import corrected_title_inputs, inputs
from test_publication import authority

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.hs3_evidence import compile_hs3_evidence
from index.publication import compile_publication
from linker_genie.ground import check
from linker_genie.hs3_evidence import (
    DATA_MODELS,
    DATASHEET,
    DE_DATASHEET,
    DE_DATASHEET_GROUP,
    MANUAL_MODEL,
    SOURCE_GROUPS,
    SOURCES,
    de_datasheet_id,
    de_datasheet_text,
    hs3_anchor_key,
    hs3_anchors,
    valid_hs3_datasheet_scope,
)
from linker_genie.hydrate import hydrate
from linker_genie.knowledge import KnowledgeSearch, model_view, record
from linker_genie.publication import Snapshot
from linker_genie.retrieval import DocumentIndex
from linker_genie.schema import DocumentBlock, TextBlock, TurnOutput


@pytest.mark.parametrize("corrected_title", [False, True])
def test_hs3_conditional_sources_reach_the_consumer_and_revoke(
    tmp_path: Path, corrected_title: bool
) -> None:
    chunks, raw, _ = corrected_title_inputs() if corrected_title else inputs()
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
        main_doc = next(
            d for d in raw["documents"] if d["document_id"] == hit["document_id"]
        )
        assert hit["title"] == main_doc["title"]
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
        localized_main = next(
            d for d in localized["documents"] if d["document_id"] == hit["document_id"]
        )
        localized_main["title_de"] = "EU-Konformitätserklärung für HS3"
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
        languages: tuple[Literal["en", "de"], ...] = ("en", "de")
        for language in languages:
            localized_hit, localized_facts = search(
                Snapshot.read(localized), pid, language
            )
            localized_hit = next(
                h for h in localized_hit["hits"] if h.get("conditional_certificate")
            )
            expected_main = (
                localized_main["title_de"]
                if language == "de"
                else localized_main["title"]
            )
            assert localized_hit["title"] == expected_main
            assert (
                localized_hit["chunk_id"]
                in localized_facts.conditional_certificate_answers
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
                b.ref: b.label
                for b in rendered.blocks
                if isinstance(b, DocumentBlock) and b.label is not None
            }
            assert labels[localized_hit["chunk_id"]].startswith(expected_main)
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
        for language in languages:
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
        assert not any(
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
        source = SOURCE_GROUPS[1 if corrected_title else 0][1]
        assert source in SOURCES
        db.execute("DELETE FROM chunks WHERE id = ?", (source,))
    index = DocumentIndex(target, encoder=None)
    try:
        result, _ = search(snap, pid)
        assert all(h.get("conditional_certificate") is not True for h in result["hits"])
    finally:
        index.close()


# The three complete original chunks of the German datasheet (e00f9645d187),
# digested in SOURCES; each text must hash to its pinned original.
DE_DOCUMENT: dict[str, Any] = {
    "document_id": "doc-e00f9645d187c241570a4037afa6a1dd54c23cd3d41b18",
    "blob_sha256": DE_DATASHEET,
    "url": "https://de-linker.com/wp-content/uploads/2026/10/SAJ_HS3_5-12K-T2_Datasheet_DE.pdf",
    "aliases": [
        "https://de-linker.com/wp-content/uploads/2026/10/SAJ_HS3_5-12K-T2_Datasheet_DE.pdf"
    ],
    "product_ids": [1185, 1186, 1187, 2198, 2199],
    "title": "SAJ HS3 5–12 kW T2 Datenblatt (DE)",
    "type": "datasheet",
    "lang": "de",
    "role": "",
    "citation_aliases": [],
    "document_revision": "e00f9645d187c241570a4037afa6a1dd54c23cd3d41b189bc44a0e0b24e4f7b3",
}
DE_ORIGINALS: dict[str, tuple[int, Literal["text", "table"], str]] = {
    "e00f9645d187-p1-59c4601a": (
        1,
        "text",
        "SAJs neueste All-in-one-Lösung für Energiespeichersysteme für Wohngebäude, "
        "integriertes PCS, BMS, EMS, Ladegerät für Elektrofahrzeuge und Akku, mit "
        "Plug-and-Play-Design, IP65-Design und nur 12 Schrauben, was die Installation "
        "erheblich erleichtert. HS3 deckt einen Bereich von 5 bis 12 kW, 2 MPPTs und "
        "ein dreiphasiges Netz ab.",
    ),
    "e00f9645d187-p2-fce1bab4": (
        2,
        "table",
        "| Modul DC-Eingang Max. Leistung der PV-Anlage [Wp]@ STC Max. DC-Spannung [V] "
        "MPPT Spannungsbereich [V] Nennspannung DC [V] Startspannung [V] Max. "
        "DC-Eingangsstrom [A] Max. DC-Kurzschluss-Strom [A] Anzahl der MPPT "
        "AC-Ausgang/Eingang [Netzgekoppelt] Nennleistung AC [W] Max. Scheinleistung "
        "[VA] Ausgangs-Nennstrom [A]@230 V AC | 1030*695*170 HS3-5K-T2-W/G-P 10000 | "
        "1400*695*170 | 1000 180～900 600 180 20/20 25/25 2 HS3-8K-T2-W/G-P 12000 |  | "
        "1770*695*170 890*695*170 15000 |",
    ),
    "e00f9645d187-p2-b28e1a1b": (
        2,
        "table",
        "| AC-Nennspannung/Bereich [V] Nennausgangsfrequenz/Bereich [Hz] Leistungsfaktor "
        "[cos φ] Gesamtklirrfaktor [THDi] AC-Ausgang [Backup] Nennausgangsleistung [W] "
        "Spitzenleistung des Ausgangs [VA] AC-Nennspannung/Bereich [V] "
        "Nennausgangsfrequenz/Bereich [Hz] Ausgang THDv (@ bei linearer Last) "
        "Wirkungsgrad Max. Wirkungsgrad Euro-Wirkungsgrad | 30/15.8 7500,60s | 3L+N+PE, "
        "30/18.4 | 29.0 230/400, 240/415; 50, 60/45～55, 55～65 0.8 kapazitativ～0.8 <3% "
        "LiFePO4 380~500 (bis zu 8 8000 8800 11.6 12.8 30/25 | HS3-10K-T2-W/G-P 15000 | "
        "HS3-12K-T2-W/G-P |\n"
        "| Max. Ausgangsstrom [A] Max. Eingangsstrom [A]@230 V AC Akku-Parameter "
        "Akkutyp Akku-Spannungsbereich [V] Max. Lade-/Entladestrom [A] Skalierbarkeit | "
        "5000 5500 7.2 8.0 5000 | HS3-6K-T2-W/G-P 12000 6000 6600 8.7 9.6 | 220/380, "
        "180～280/312～485 induktiv | 180～280/312～485 10000 11000 14.5 15.9 30/30 10000 "
        "15000,60s | 12000 12000 17.4 17.4 30/30 12000 15000,60s |",
    ),
}


def german_inputs() -> tuple[list[Chunk], dict[str, Any], dict[str, str]]:
    """Associate the reviewed German datasheet with all five HS3 products."""
    chunks, raw, statuses = inputs()
    raw = deepcopy(raw)
    raw["documents"].append(deepcopy(DE_DOCUMENT))
    for product in raw["products"]:
        product["documents"].append(DE_DOCUMENT["document_id"])
    chunks = [
        *chunks,
        *(
            Chunk(
                id=cid,
                doc_sha256=DE_DATASHEET,
                page=page,
                section="HS3 Dreiphasige Komplettlösung",
                kind=kind,
                header=(
                    f"SAJ | HS3 | datasheet | {DE_DOCUMENT['title']} | "
                    f"HS3 Dreiphasige Komplettlösung | p. {page}"
                ),
                text=text,
                lang="de",
                tokens=len(text.split()),
            )
            for cid, (page, kind, text) in DE_ORIGINALS.items()
        ),
    ]
    return chunks, raw, statuses


def test_german_datasheet_compiles_for_all_five_models_and_authorizes() -> None:
    chunks, raw, statuses = german_inputs()
    source = Snapshot.read(raw)
    anchors = hs3_anchors((c.id, c.doc_sha256, c.page, c.kind, c.text) for c in chunks)
    assert {hs3_anchor_key(cid) for cid in DE_DATASHEET_GROUP} <= set(anchors)
    units, scopes = compile_hs3_evidence(chunks, source, statuses, Words(), 512)
    german = [c for c in units if scopes[c.id]["basis"] == "hs3_datasheet_de"]
    assert len(german) == 5
    did = str(DE_DOCUMENT["document_id"])
    de_tables = (
        DE_ORIGINALS["e00f9645d187-p2-fce1bab4"][2]
        + "\n"
        + DE_ORIGINALS["e00f9645d187-p2-b28e1a1b"][2]
    )
    for unit in german:
        proof = scopes[unit.id]
        pid = proof["product_ids"][0]
        model = str(source.products[pid]["model"])
        assert unit.lang == "de" and unit.text == de_datasheet_text(model)
        assert unit.id == de_datasheet_id(model, did, unit.text)
        # The German tables print the -P inverter prefix, never the -PX model.
        assert model not in de_tables and model[:-1] in de_tables
        assert proof["hs3_datasheet_de"]["source_documents"]["datasheet_de"] == {
            "document_id": did,
            "document_revision": DE_DOCUMENT["document_revision"],
            "blob_sha256": DE_DATASHEET,
        }
        assert valid_hs3_datasheet_scope(
            proof,
            [pid],
            source.products,
            source.documents,
            sha=DE_DATASHEET,
            chunk_id=unit.id,
            text=unit.text,
            anchors=anchors,
        )
    assert {scopes[c.id]["product_ids"][0] for c in german} == {
        1185,
        1186,
        1187,
        2198,
        2199,
    }
    assert sum(1 for c in units if "hs3_conditional_certificate" in scopes[c.id]) == 5


@pytest.mark.parametrize("tampered", DE_DATASHEET_GROUP)
def test_german_datasheet_requires_every_untampered_anchor(tampered: str) -> None:
    chunks, raw, statuses = german_inputs()
    source = Snapshot.read(raw)
    units, scopes = compile_hs3_evidence(chunks, source, statuses, Words(), 512)
    unit = next(c for c in units if scopes[c.id]["basis"] == "hs3_datasheet_de")
    proof = scopes[unit.id]
    changed = [
        replace(c, text=c.text + " geändert") if c.id == tampered else c for c in chunks
    ]
    out, out_scopes = compile_hs3_evidence(changed, source, statuses, Words(), 512)
    assert not any(s["basis"] == "hs3_datasheet_de" for s in out_scopes.values())
    if tampered not in (DATA_MODELS, MANUAL_MODEL):
        # Tampering a German-only anchor leaves the English proof intact.
        assert (
            sum(1 for s in out_scopes.values() if "hs3_conditional_certificate" in s)
            == 5
        )
    assert not valid_hs3_datasheet_scope(
        proof,
        proof["product_ids"],
        source.products,
        source.documents,
        sha=DE_DATASHEET,
        chunk_id=unit.id,
        text=unit.text,
        anchors=hs3_anchors(
            (c.id, c.doc_sha256, c.page, c.kind, c.text) for c in changed
        ),
    )


@pytest.mark.parametrize("role", ["datasheet_de", "datasheet", "manual"])
@pytest.mark.parametrize(
    "change", ["removed", "revision", "association", "product_link", "role"]
)
def test_german_datasheet_needs_all_three_current_associations(
    role: str, change: str
) -> None:
    chunks, raw, statuses = german_inputs()
    source = Snapshot.read(raw)
    units, scopes = compile_hs3_evidence(chunks, source, statuses, Words(), 512)
    unit = next(c for c in units if scopes[c.id]["basis"] == "hs3_datasheet_de")
    proof = scopes[unit.id]
    pid = proof["product_ids"][0]
    did = proof["hs3_datasheet_de"]["source_documents"][role]["document_id"]
    docs, products = deepcopy(source.documents), deepcopy(source.products)
    if change == "removed":
        del docs[did]
    elif change == "revision":
        docs[did]["document_revision"] = "changed"
    elif change == "association":
        docs[did]["product_ids"].remove(pid)
    elif change == "role":
        docs[did]["role"] = "unrelated_purpose"
    else:
        products[pid]["documents"].remove(did)
    assert not valid_hs3_datasheet_scope(
        proof,
        [pid],
        products,
        docs,
        sha=DE_DATASHEET,
        chunk_id=unit.id,
        text=unit.text,
        anchors=hs3_anchors(
            (c.id, c.doc_sha256, c.page, c.kind, c.text) for c in chunks
        ),
    )
