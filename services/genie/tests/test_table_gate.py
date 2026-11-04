"""The per-table preparation gate (#900): bare parameter tables must alarm."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from test_publication import authority
from test_publication_columns import ESA, HCA, chunks, manifest

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.publication import scope_proofs
from index.table_gate import (
    TABLE_GATE_MIN_COLUMNS,
    TABLE_GATE_MIN_ROWS,
    audit,
    gate_fails,
)
from linker_genie.table_projection import SourceCell


def _table_chunk(sha: str, table: str, rows: int, text: str) -> Chunk:
    def cell(row: int, col: int, content: str) -> SourceCell:
        return SourceCell(
            row_start=row,
            row_end=row + 1,
            col_start=col,
            col_end=col + 1,
            column_header=row == 0,
            row_header=False,
            row_section=False,
            text=content,
            bbox=None,
            bbox_origin="",
        )

    return Chunk(
        id=f"{sha[:6]}-{table[-1]}",
        doc_sha256=sha,
        page=2,
        section="Technical Data",
        kind="table",
        header="",
        text=text,
        lang="en",
        tokens=10 * rows,
        source_table=table,
        source_rows=tuple(range(rows + 1)),
        source_cells=(
            cell(0, 0, "Battery Data"),
            cell(0, 1, "Model"),
        ),
    )


PARAMETER_TEXT = "\n".join(
    [
        "| Battery Data | Model |",
        "| Nominal Energy (kWh) | 261 |",
        "| Weight (kg) | 900 |",
        "| IP Rating | IP65 |",
    ]
)


def _group(rows: int, columns: int, prose: bool = True, axis: bool = False) -> Any:
    from index.table_gate import TableGroup

    return TableGroup(
        chunks=[],
        rows=rows,
        columns=columns,
        parameter_prose=prose,
        axis_proven=axis,
    )


def test_datasheet_standard_matches_the_report_parameter_table_criterion() -> None:
    assert TABLE_GATE_MIN_ROWS == 4
    assert TABLE_GATE_MIN_COLUMNS == 2
    assert gate_fails("datasheet", _group(4, 2, prose=True))
    assert not gate_fails("datasheet", _group(3, 2, prose=True))
    assert not gate_fails("datasheet", _group(4, 1, prose=True))
    assert not gate_fails("datasheet", _group(4, 2, prose=False))


def test_compatibility_is_strictest_certificate_exempt_manual_needs_axis() -> None:
    assert gate_fails("compatibility", _group(1, 1, prose=False))
    assert not gate_fails("certificate", _group(9, 3, prose=True))
    assert gate_fails("manual", _group(9, 3, axis=True))
    assert not gate_fails("manual", _group(9, 3, axis=False))


def test_audit_marks_bare_parameter_tables_and_accepts_authorized_ones() -> None:
    datasheet = _table_chunk("d1" * 32, "docling:p2:#/tables/0", 4, PARAMETER_TEXT)
    scopes = {
        "derived": {
            "basis": "table_single_model",
            "single_model_projection": {
                "source_sha256": "d1" * 32,
                "source_table": "docling:p2:#/tables/0",
            },
        }
    }
    covered = audit([datasheet], {"derived": [1954]}, scopes, {"d1" * 32: "datasheet"})
    assert not covered.bare
    assert covered.coverage["datasheet"]["tables"] == 1
    assert covered.coverage["datasheet"]["with_scope"] == 1
    # The same projection whose derived chunk carries no product grant does
    # not cover the table (store-level authorization refused it).
    refused = audit([datasheet], {}, scopes, {"d1" * 32: "datasheet"})
    assert refused.bare == {("d1" * 32, "docling:p2:#/tables/0")}
    bare = audit([datasheet], {}, {}, {"d1" * 32: "datasheet"})
    assert bare.bare == {("d1" * 32, "docling:p2:#/tables/0")}
    assert bare.coverage["datasheet"]["bare_parameter_tables"] == 1


def _export(tmp_path: Path, sha: str, selected: list[Chunk]) -> Path:
    raw = manifest()
    doc = next(d for d in raw["documents"] if d["blob_sha256"] == sha)
    scopes = scope_proofs(selected, raw, authority(raw))
    source = tmp_path / "corpus"
    corpus.write(
        source,
        corpus.Meta(
            "gate-test",
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
                ("GoodWe",),
                (),
                "datasheet",
                "en",
                2,
                "indexed",
            )
        ],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        selected,
    )
    target = tmp_path / "index.sqlite"
    store.export(source, target)
    return target


def test_bare_datasheet_tables_read_as_unprepared_table_without_scope(
    tmp_path: Path,
) -> None:
    """#900 §6: p.1 marketing passages filled the pair while every table stayed bare."""
    target = _export(tmp_path, ESA, chunks(ESA))
    db = sqlite3.connect(target)
    try:
        rows = json.loads(
            db.execute(
                "select value from meta where key='unprepared_documents'"
            ).fetchone()[0]
        )
        complete = json.loads(
            db.execute(
                "select value from meta where key='preparation_complete'"
            ).fetchone()[0]
        )
    finally:
        db.close()
    assert any(row["reason"] == "table_without_scope" for row in rows)
    assert complete is False


def test_datasheet_with_table_scope_prepares_normally(tmp_path: Path) -> None:
    """The HCA twin carries table_columns grants; the gate stays silent."""
    target = _export(tmp_path, HCA, chunks(HCA))
    db = sqlite3.connect(target)
    try:
        rows = json.loads(
            db.execute(
                "select value from meta where key='unprepared_documents'"
            ).fetchone()[0]
        )
    finally:
        db.close()
    assert all(row["reason"] != "table_without_scope" for row in rows)


def test_publish_refuses_bare_datasheet_tables() -> None:
    import publish_index

    manifest_with_bare = {
        "table_coverage": {"datasheet": {"bare_parameter_tables": 2}},
    }
    with pytest.raises(SystemExit, match="2 datasheet"):
        publish_index.refuse_bare_datasheet_tables(manifest_with_bare, Path("/tmp/x"))
    publish_index.refuse_bare_datasheet_tables(
        {"table_coverage": {"datasheet": {"bare_parameter_tables": 0}}}, Path("/tmp/x")
    )
    publish_index.refuse_bare_datasheet_tables({}, Path("/tmp/x"))
