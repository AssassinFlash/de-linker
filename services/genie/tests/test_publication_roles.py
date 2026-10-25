"""Authored current-system rows and an explicitly named manual peripheral."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from test_chunking import Words
from test_publication import authority
from test_publication_columns import manifest, pages

from index import corpus, store
from index.chunking import Chunk, DocumentMeta, chunk_document
from index.corpus import DocumentRow
from index.extract import Block, Page
from index.publication import scope_proofs
from linker_genie.publication import Snapshot
from linker_genie.retrieval import DocumentIndex

BAT = "027415a66a00234f03d1268e180129fa016e601aaf1ecb7cda643a24aecb7d38"
CHS = "92b45188a10eac6d72eefc0345165b3c6ade83316555ddd6fdcf6c46cd67a262"
COMBINED_FAILURES = [
    "reverse_unknown_later",
    "normal_missing_rows",
    "normal_missing_column_later",
    "normal_unknown_declaration",
    "normal_missing_preceding",
    "normal_invalid_rows",
]


def source_chunks(sha: str, source: list[Page] | None = None) -> list[Chunk]:
    raw = manifest()
    doc = next(d for d in raw["documents"] if d["blob_sha256"] == sha)
    return chunk_document(
        DocumentMeta(
            sha,
            doc["title"],
            "",
            (),
            tuple(
                p["model"]
                for p in raw["products"]
                if p["product_id"] in doc["product_ids"]
            ),
            "manual" if sha == CHS else "datasheet",
            "en",
        ),
        source if source is not None else pages(sha),
        Words(),
        lambda _: "en",
    )


def loaded_index(path: Path, sha: str, chunks: list[Chunk]) -> DocumentIndex:
    raw = manifest()
    scopes = scope_proofs(chunks, raw, authority(raw))
    doc = next(d for d in raw["documents"] if d["blob_sha256"] == sha)
    source = path / "corpus"
    corpus.write(
        source,
        corpus.Meta(
            "source-roles",
            None,
            None,
            "cached Docling",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {cid: p["product_ids"] for cid, p in scopes.items()},
                "chunk_scopes": scopes,
            },
        ),
        [
            DocumentRow(
                sha,
                (doc["url"],),
                doc["title"],
                "",
                (),
                (),
                "manual" if sha == CHS else "datasheet",
                "en",
                max(c.page for c in chunks),
                "indexed",
            )
        ],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        chunks,
    )
    target = path / "index.sqlite"
    store.export(source, target)
    return DocumentIndex(target, encoder=None)


def test_original_current_system_row_is_retrievable_without_unknown_pack_row(
    tmp_path: Path,
) -> None:
    selected = source_chunks(BAT)
    scopes = scope_proofs(selected, manifest(), authority(manifest()))
    unknown = next(c for c in selected if "GW52.2-PACK-LC-G10" in c.text)
    assert unknown.id not in scopes
    target = next(c for c in selected if "180 / 180" in c.text)
    assert target.id in scopes
    columns = scopes[target.id]["table_columns"]
    assert columns["source_table"] == "docling:p2:#/tables/0"
    assert columns["product_ids"] == [1956, 1958]
    assert 14 in target.source_rows
    assert 3 not in target.source_rows
    assert columns["source_rows"] == list(target.source_rows)
    assert columns["excluded_role_rows"][0]["source_chunk_id"] == unknown.id
    assert columns["excluded_role_rows"][0]["role"] == "pack_model"
    loaded = loaded_index(tmp_path, BAT, selected)
    try:
        hits = loaded.search(
            "Max. Input / Output Current",
            "en",
            [1958],
            publication=Snapshot.read(manifest()),
        )
        answer = next(h for h in hits if "180 / 180" in h.text)
        assert answer.text.startswith(
            "| Technical Data | GW208.9-BAT-LC-G10 | GW261.2-BAT-LCD-G10 |\n"
        )
        assert "| Max. Input / Output Current (A) | - | 180 / 180 |" in answer.text
        assert all("GW52.2-PACK-LC-G10" not in h.text for h in hits)
    finally:
        loaded.close()


def test_original_manual_role_is_host_fact_with_separate_current_peripheral(
    tmp_path: Path,
) -> None:
    selected = source_chunks(CHS)
    scopes = scope_proofs(selected, manifest(), authority(manifest()))
    target = next(c for c in selected if "meter CHINT's DTSU666" in c.text)
    assert target.id in scopes
    proof = scopes[target.id]
    assert proof["basis"] == "manual_peripheral"
    assert set(proof["product_ids"]) == {1959, 1960, 1961}
    reference = proof["referenced_products"][0]
    assert reference["product_id"] == 2281
    assert reference["role"] == "meter"
    assert reference["source_chunk_id"] == target.id
    assert reference["quote"] == "meter CHINT's DTSU666"
    assert proof["manual_scope"]["source_chunk_ids"]
    assert "following CHS2 Energy Storage Systems" in proof["manual_scope"]["quote"]
    loaded = loaded_index(tmp_path, CHS, selected)
    try:
        hits = loaded.search(
            "DTSU666 meter", "en", [1959], publication=Snapshot.read(manifest())
        )
        assert any(h.chunk_id == target.id for h in hits)
        assert all(2281 not in h.product_ids for h in hits)
        assert not loaded.search(
            "DTSU666 meter", "en", [2281], publication=Snapshot.read(manifest())
        )
    finally:
        loaded.close()


@pytest.mark.parametrize("change", ["unknown_axis", "reversed_axis", "missing_rows"])
def test_component_property_never_excuses_an_unproven_system_axis(change: str) -> None:
    source = deepcopy(pages(BAT))
    page = next(p for p in source if p.number == 2)
    position = next(i for i, block in enumerate(page.blocks) if block.kind == "table")
    table = page.blocks[position]
    if change == "missing_rows":
        selected = [replace(c, source_rows=()) for c in source_chunks(BAT, source)]
    else:
        axis = (
            ("Model", "GW261.2-BAT-LCD-G10", "GW208.9-BAT-LC-G10")
            if change == "reversed_axis"
            else ("Model", "GW208.9-BAT-LC-G10", "GW125/261-ESA-LCN-G11")
        )
        page.blocks[position] = replace(
            table,
            rows=(axis, *table.rows),
            row_indices=tuple(range(len(table.rows) + 1)),
        )
        selected = source_chunks(BAT, source)
    scopes = scope_proofs(selected, manifest(), authority(manifest()))
    assert all(c.id not in scopes for c in selected if c.kind == "table")


def combined_table_failure(mode: str) -> list[Chunk]:
    """The late conflict must not be packed together with the explicit first axis."""
    source = deepcopy(pages(BAT))
    page = next(p for p in source if p.number == 2)
    position = next(i for i, block in enumerate(page.blocks) if block.kind == "table")
    original = page.blocks[position]
    labels = ["GW208.9-BAT-LC-G10", "GW261.2-BAT-LCD-G10"]
    if mode == "reverse_unknown_later":
        labels.reverse()
    rows = (
        ("Model", *labels),
        *original.rows,
        *((("Model", "Z999", ""),) if mode == "reverse_unknown_later" else ()),
        *((("Parameter", "10"),) if mode == "normal_missing_column_later" else ()),
    )
    page.blocks[position] = replace(
        original,
        rows=rows,
        header_rows=0,
        row_indices=tuple(range(len(rows))),
    )
    if mode == "normal_unknown_declaration":
        page.blocks.insert(position, Block("text", "Z999"))
    selected = source_chunks(BAT, source)
    if mode == "normal_missing_rows":
        selected = [replace(c, source_rows=()) for c in selected]
    if mode == "normal_missing_preceding":
        last = next(c for c in reversed(selected) if c.kind == "table")
        selected = [
            replace(c, preceding_text=()) if c.id == last.id else c for c in selected
        ]
    if mode == "normal_invalid_rows":
        first = next(c for c in selected if c.kind == "table")
        selected = [
            replace(c, source_rows=(0,) * len(c.source_rows)) if c.id == first.id else c
            for c in selected
        ]
    return selected


@pytest.mark.parametrize("mode", COMBINED_FAILURES)
def test_combined_table_failure_refuses_even_the_explicit_current_model_first_chunk(
    mode: str,
) -> None:
    selected = combined_table_failure(mode)
    tables = [c for c in selected if c.source_table == "docling:p2:#/tables/0"]
    assert len(tables) >= 3
    assert tables[0].text.startswith("| Model |")
    scopes = scope_proofs(selected, manifest(), authority(manifest()))
    assert not [c.id for c in tables if c.id in scopes]


@pytest.mark.parametrize("mode", COMBINED_FAILURES)
def test_combined_table_failure_cannot_release_the_first_chunk_through_sqlite(
    tmp_path: Path, mode: str
) -> None:
    selected = combined_table_failure(mode)
    table_ids = {c.id for c in selected if c.source_table == "docling:p2:#/tables/0"}
    loaded = loaded_index(tmp_path, BAT, selected)
    try:
        hits = loaded.search(
            "Model Battery Type", "en", [1958], publication=Snapshot.read(manifest())
        )
        assert not [h.chunk_id for h in hits if h.chunk_id in table_ids]
    finally:
        loaded.close()


@pytest.mark.parametrize("change", ["withdrawn", "revision", "host_relation"])
def test_manual_peripheral_or_host_withdrawal_revokes_the_complete_passage(
    tmp_path: Path, change: str
) -> None:
    selected = source_chunks(CHS)
    target = next(c for c in selected if "meter CHINT's DTSU666" in c.text)
    loaded = loaded_index(tmp_path, CHS, selected)
    raw = manifest()
    if change == "withdrawn":
        raw["products"] = [p for p in raw["products"] if p["product_id"] != 2281]
    elif change == "revision":
        next(p for p in raw["products"] if p["product_id"] == 2281)[
            "product_revision"
        ] = "changed"
    else:
        doc = next(d for d in raw["documents"] if d["blob_sha256"] == CHS)
        doc["product_ids"].remove(1959)
    try:
        assert not any(
            h.chunk_id == target.id
            for h in loaded.search(
                "DTSU666 meter", "en", [1959], publication=Snapshot.read(raw)
            )
        )
    finally:
        loaded.close()


@pytest.mark.parametrize("part", ["quote", "source_chunk_id", "role", "declaration"])
def test_runtime_manual_reference_requires_its_original_role_anchor(
    tmp_path: Path, part: str
) -> None:
    selected = source_chunks(CHS)
    target = next(c for c in selected if "meter CHINT's DTSU666" in c.text)
    loaded = loaded_index(tmp_path, CHS, selected)
    try:
        with sqlite3.connect(loaded.path) as db:
            row = db.execute(
                "SELECT proof FROM chunk_scopes WHERE chunk_id=?", (target.id,)
            ).fetchone()
            assert row is not None
            proof = json.loads(row[0])
            if part == "declaration":
                proof["manual_scope"]["quote"] = "An unrelated MODEL-3 manual"
            else:
                proof["referenced_products"][0][part] = "unproven"
            db.execute(
                "UPDATE chunk_scopes SET proof=? WHERE chunk_id=?",
                (json.dumps(proof), target.id),
            )
        assert not any(
            h.chunk_id == target.id
            for h in loaded.search(
                "DTSU666 meter", "en", [1959], publication=Snapshot.read(manifest())
            )
        )
    finally:
        loaded.close()


@pytest.mark.parametrize("part", ["source_rows", "text_sha256", "excluded_role_rows"])
def test_runtime_table_row_proof_rejects_missing_or_changed_native_evidence(
    tmp_path: Path, part: str
) -> None:
    selected = source_chunks(BAT)
    target = next(c for c in selected if "180 / 180" in c.text)
    loaded = loaded_index(tmp_path, BAT, selected)
    try:
        with sqlite3.connect(loaded.path) as db:
            row = db.execute(
                "SELECT proof FROM chunk_scopes WHERE chunk_id=?", (target.id,)
            ).fetchone()
            assert row is not None
            proof = json.loads(row[0])
            proof["table_columns"][part] = "changed" if part == "text_sha256" else []
            db.execute(
                "UPDATE chunk_scopes SET proof=? WHERE chunk_id=?",
                (json.dumps(proof), target.id),
            )
        assert not any(
            "180 / 180" in h.text
            for h in loaded.search(
                "Max. Input / Output Current",
                "en",
                [1958],
                publication=Snapshot.read(manifest()),
            )
        )
    finally:
        loaded.close()


@pytest.mark.parametrize(
    "boundary",
    [
        "no_role",
        "unknown_peripheral",
        "extra_unknown",
        "local_model",
        "unknown_section",
        "parameter",
        "no_declaration",
    ],
)
def test_manual_reference_needs_original_role_and_scope_without_local_override(
    boundary: str,
) -> None:
    raw = manifest()
    label = "DTSU666" if boundary != "unknown_peripheral" else "DTSU999"
    sentence = f"The METER.485 port can connect with meter CHINT's {label} to provide RS485 communication."
    if boundary == "no_role":
        sentence = sentence.replace("meter CHINT's", "device CHINT's")
    if boundary == "parameter":
        sentence += " Its rated current is 40 A."
    if boundary == "extra_unknown":
        sentence += " Use adapter Z999."
    source = deepcopy(pages(CHS))
    target_page = next(p for p in source if p.number == 27)
    target_page.blocks = [Block("heading", "Meter connection"), Block("text", sentence)]
    if boundary == "unknown_section":
        target_page.blocks[0] = Block("heading", "Z999 installation")
    if boundary == "local_model":
        target_page.blocks.insert(
            1, Block("text", "GW125/261-ESA-LCN-G10 technical parameters")
        )
    if boundary == "no_declaration":
        source = [p for p in source if p.number == 27]
    selected = source_chunks(CHS, source)
    target = next(c for c in selected if label in c.text and c.page == 27)
    scopes = scope_proofs(selected, raw, authority(raw))
    assert target.id not in scopes
