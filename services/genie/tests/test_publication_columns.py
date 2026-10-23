"""Original cached Docling table columns, current Woo bindings and real SQLite."""

from __future__ import annotations

import gzip
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from docling_core.types.doc.document import DoclingDocument
from test_chunking import Words
from test_publication import authority

from index import corpus, store
from index.chunking import Chunk, DocumentMeta, chunk_document
from index.corpus import DocumentRow
from index.extract import Block, Page, pages_of
from index.publication import scope_proofs
from linker_genie.publication import Snapshot
from linker_genie.retrieval import DocumentIndex

FIXTURES = Path(__file__).parent / "fixtures" / "publication-columns"
HCA = "0fdeaf90548f35e00a605e8ae538c24f89f745be5195e85dbf466c2a7d2d9178"
ESA = "c95aef48b1ea4fbd0ae8729c104774ce2b5ee7137809fc8fe20642be2780bbfe"
ORDER = [3586, 3557, 3587]
LABELS = ["GW7K-HCA-20", "GW11K-HCA-20", "GW22K-HCA-20"]


def manifest() -> dict[str, Any]:
    return json.loads(gzip.decompress((FIXTURES / "manifest.json.gz").read_bytes()))


def pages(sha: str) -> list[Page]:
    document = DoclingDocument.model_validate_json(
        gzip.decompress((FIXTURES / f"{sha}.json.gz").read_bytes())
    )
    return [
        Page(number, "docling", blocks) for number, blocks in pages_of(document).items()
    ]


def chunks(sha: str = HCA, source: list[Page] | None = None) -> list[Chunk]:
    raw = manifest()
    document = next(d for d in raw["documents"] if d["blob_sha256"] == sha)
    models = tuple(
        p["model"]
        for p in raw["products"]
        if p["product_id"] in document["product_ids"]
    )
    return chunk_document(
        DocumentMeta(
            sha, document["title"], "", ("GoodWe",), models, "datasheet", "en"
        ),
        source if source is not None else pages(sha),
        Words(),
        lambda _: "en",
        max_tokens=120,
    )


def index(path: Path, selected: list[Chunk]) -> DocumentIndex:
    raw = manifest()
    scopes = scope_proofs(selected, raw, authority(raw))
    source = path / "corpus"
    corpus.write(
        source,
        corpus.Meta(
            "source-columns",
            None,
            None,
            "cached Docling",
            120,
            publication={
                "manifest": raw,
                "chunk_products": {
                    cid: proof["product_ids"] for cid, proof in scopes.items()
                },
                "chunk_scopes": scopes,
            },
        ),
        [
            DocumentRow(
                HCA,
                ("https://site.test/hca.pdf",),
                "HCA datasheet",
                "HCA Datenblatt",
                ("GoodWe",),
                tuple(LABELS),
                "datasheet",
                "en",
                2,
                "indexed",
            )
        ],
        [(pid, label) for pid, label in zip(ORDER, LABELS, strict=True)],
        selected,
    )
    target = path / "index.sqlite"
    store.export(source, target)
    return DocumentIndex(target, encoder=None)


def test_actual_table_uses_original_columns_and_native_structure_without_generic_heading_authority() -> (
    None
):
    selected = chunks()
    proof = scope_proofs(selected, manifest(), authority(manifest()))
    tables = [chunk for chunk in selected if chunk.kind == "table"]
    assert len(tables) > 1
    for chunk in tables:
        assert chunk.source_table == "docling:p2:#/tables/0"
        assert proof[chunk.id]["basis"] == "table_columns"
        columns = proof[chunk.id]["table_columns"]
        assert columns["product_ids"] == ORDER
        assert columns["labels"] == LABELS
        assert all(
            cid in {c.id for c in selected} for cid in columns["header_chunk_ids"]
        )
        assert {a["product_id"] for a in proof[chunk.id]["associations"]} == set(ORDER)
    # A generic source heading never broadcasts the column scope backwards.
    intro = next(c for c in selected if c.section.startswith("Smart and flexible"))
    assert intro.id not in proof


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("neighbours", [False, True])
def test_actual_grid_type_table_is_retrievable_with_all_three_columns_in_source_order(
    tmp_path: Path, lang: str, neighbours: bool
) -> None:
    loaded = index(tmp_path, chunks())
    try:
        hits = loaded.search(
            "Nominal Input Voltage",
            lang,
            [3586],
            neighbours=neighbours,
            publication=Snapshot.read(manifest()),
        )
        voltage = next(h for h in hits if "Nominal Input Voltage" in h.text)
        header = "| Technical Data | GW7K-HCA-20 | GW11K-HCA-20 | GW22K-HCA-20 |"
        assert voltage.text.startswith(header + "\n")
        assert voltage.text.count(header) == 1
        assert (
            "| Nominal Input Voltage (V) | 230, L / N / PE | 400, 3L / N / PE | 400, 3L / N / PE |"
            in voltage.text
        )
        assert set(voltage.product_ids) == set(ORDER)
        revoked = manifest()
        revoked["products"] = [
            p for p in revoked["products"] if p["product_id"] != 3557
        ]
        for document in revoked["documents"]:
            document["product_ids"] = [
                pid for pid in document["product_ids"] if pid != 3557
            ]
        revoked["documents"] = [d for d in revoked["documents"] if d["product_ids"]]
        assert not any(
            "Nominal Input Voltage" in h.text
            for h in loaded.search(
                "Nominal Input Voltage",
                lang,
                [3586],
                publication=Snapshot.read(revoked),
            )
        )
    finally:
        loaded.close()


@pytest.mark.parametrize(
    "boundary",
    [
        "unknown_model",
        "unknown_axis",
        "table_unknown_model",
        "new_table",
        "new_section",
        "missing_column",
    ],
)
def test_table_column_scope_stops_at_actual_structure_or_unproven_model(
    boundary: str,
) -> None:
    source = pages(HCA)
    target = next(
        i for i, block in enumerate(source[1].blocks) if block.kind == "table"
    )
    original = source[1].blocks[target]
    if boundary == "unknown_model":
        source[1].blocks.insert(target, Block("text", text="GW125/261-ESA-LCN-G11"))
    elif boundary == "unknown_axis":
        source[1].blocks.insert(target, Block("text", text="Z999"))
    elif boundary == "table_unknown_model":
        source[1].blocks[target] = replace(
            original, rows=original.rows + (("Model", "GW125/261-ESA-LCN-G11", "", ""),)
        )
    elif boundary == "new_section":
        source[1].blocks.insert(target, Block("heading", text="GOODWE"))
    elif boundary == "new_table":
        source[1].blocks.insert(
            target,
            replace(original, rows=(("Input", "", "", ""),), source_id="#/tables/new"),
        )
    else:
        source[1].blocks[target] = replace(
            original, rows=tuple(row[:-1] for row in original.rows)
        )
    selected = chunks(source=source)
    proof = scope_proofs(selected, manifest(), authority(manifest()))
    assert all(
        c.id not in proof
        for c in selected
        if c.kind == "table" and c.source_table == "docling:p2:#/tables/0"
    )


def test_actual_unknown_g11_cannot_supply_g10_current_table_values() -> None:
    selected = chunks(ESA)
    proof = scope_proofs(selected, manifest(), authority(manifest()))
    assert any("GW125/261-ESA-LCN-G11" in c.text for c in selected)
    ac = [c for c in selected if "Max. AC Output Current" in c.text]
    assert ac
    assert all(c.id not in proof for c in ac)


@pytest.mark.parametrize("reverse", [False, True])
def test_original_table_model_axis_must_match_preceding_column_order(
    reverse: bool,
) -> None:
    source = pages(HCA)
    position = next(
        i for i, block in enumerate(source[1].blocks) if block.kind == "table"
    )
    original = source[1].blocks[position]
    local_labels = list(reversed(LABELS)) if reverse else LABELS
    source[1].blocks[position] = replace(
        original, rows=(("Model", *local_labels), *original.rows), header_rows=0
    )
    selected = chunks(source=source)
    proof = scope_proofs(selected, manifest(), authority(manifest()))
    tables = [c for c in selected if c.source_table == "docling:p2:#/tables/0"]
    assert len(tables) > 1
    if reverse:
        assert all(c.id not in proof for c in tables)
    else:
        assert all(c.id in proof for c in tables)
        continued = [c for c in tables if "table_columns" in proof[c.id]]
        assert continued
        assert all(
            proof[c.id]["table_columns"]["product_ids"] == ORDER for c in continued
        )


def test_different_current_associated_local_axis_refuses_whole_original_table() -> None:
    raw = manifest()
    document = next(d for d in raw["documents"] if d["blob_sha256"] == HCA)
    other = next(p for p in raw["products"] if p["product_id"] == 3611)
    document["product_ids"].append(other["product_id"])
    other["documents"].append(document["document_id"])
    source = pages(HCA)
    position = next(
        i for i, block in enumerate(source[1].blocks) if block.kind == "table"
    )
    original = source[1].blocks[position]
    source[1].blocks[position] = replace(
        original,
        rows=(("Model", LABELS[0], LABELS[1], other["model"]), *original.rows),
        header_rows=0,
    )
    selected = chunks(source=source)
    proof = scope_proofs(selected, raw, authority(raw))
    tables = [c for c in selected if c.source_table == "docling:p2:#/tables/0"]
    assert len(tables) > 1
    assert all(c.id not in proof for c in tables)


def test_local_explicit_model_remains_narrower_than_the_previous_column_group() -> None:
    source = pages(HCA)
    source[1].blocks.append(
        Block(
            "table",
            rows=(("Model", "GW11K-HCA-20"), ("Power (W)", "11000")),
            header_rows=1,
            source_id="#/tables/local-model",
        )
    )
    selected = chunks(source=source)
    proof = scope_proofs(selected, manifest(), authority(manifest()))
    local = next(
        c for c in selected if c.source_table == "docling:p2:#/tables/local-model"
    )
    assert proof[local.id]["product_ids"] == [3557]
    assert "table_columns" not in proof[local.id]


@pytest.mark.parametrize("tamper", ["reverse_labels", "missing_columns"])
def test_wrong_column_order_labels_are_refused_by_loaded_runtime(
    tmp_path: Path, tamper: str
) -> None:
    loaded = index(tmp_path, chunks())
    loaded.close()
    with sqlite3.connect(tmp_path / "index.sqlite") as db:
        rows = list(db.execute("SELECT chunk_id,proof FROM chunk_scopes"))
        for cid, encoded in rows:
            proof = json.loads(encoded)
            if "table_columns" in proof:
                if tamper == "missing_columns":
                    del proof["table_columns"]
                else:
                    proof["table_columns"]["labels"] = list(
                        reversed(proof["table_columns"]["labels"])
                    )
                db.execute(
                    "UPDATE chunk_scopes SET proof=? WHERE chunk_id=?",
                    (json.dumps(proof), cid),
                )
    loaded = DocumentIndex(tmp_path / "index.sqlite", encoder=None)
    try:
        assert not any(
            "Nominal Input Voltage" in h.text
            for h in loaded.search(
                "Nominal Input Voltage",
                "en",
                [3586],
                publication=Snapshot.read(manifest()),
            )
        )
    finally:
        loaded.close()
