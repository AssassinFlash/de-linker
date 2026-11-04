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
    PARSE_DAMAGED,
    TABLE_GATE_MIN_COLUMNS,
    TABLE_GATE_MIN_ROWS,
    audit,
    b_content_reason,
    gate_fails,
)
from linker_genie.table_projection import SourceCell

PRODUCTS = {
    1: {"model": "GW10K-ET-G10"},
    2: {"model": "GW15K-ET-G10"},
    3: {"model": "CU2-11K-T-I"},
}


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
        axis_labels=[],
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


def _axis_group(labels: list[str]) -> Any:
    from index.table_gate import TableGroup

    return TableGroup(
        chunks=[],
        rows=6,
        columns=1 + len(labels),
        parameter_prose=True,
        axis_proven=True,
        axis_labels=labels,
    )


def test_b_content_rule_exempts_only_foreign_devices() -> None:
    # The table's axis names only devices that are not this document's
    # products (spec 609 B-content). BC3-TV is not carried by Woo at all.
    assert (
        b_content_reason(_axis_group(["BC3-TV"]), {1}, PRODUCTS)
        == "device_not_published"
    )
    # A device Woo carries under another document is a missing-link signal.
    assert (
        b_content_reason(_axis_group(["CU2-11K-T-I"]), {1}, PRODUCTS)
        == "device_not_associated"
    )
    # The document's own model must never be exempted.
    assert b_content_reason(_axis_group(["GW10K-ET-G10"]), {1}, PRODUCTS) is None
    assert (
        b_content_reason(_axis_group(["GW10K-ET-G10", "CU2-11K-T-I"]), {1}, PRODUCTS)
        is None
    )
    # Aliased document labels resolve to the document's own model first.
    assert (
        b_content_reason(
            _axis_group(["CH2-30K-T4"]), {1959}, {1959: {"model": "CHS2-30K-T4-X"}}
        )
        is None
    )
    # Without a proven axis there is no B-content evidence.
    assert b_content_reason(_group(6, 3), {1}, PRODUCTS) is None


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
    covered = audit(
        [datasheet],
        {"derived": [1]},
        scopes,
        {"d1" * 32: "datasheet"},
        PRODUCTS,
        {"d1" * 32: {1}},
    )
    assert not covered.bare
    assert covered.coverage["datasheet"]["tables"] == 1
    assert covered.coverage["datasheet"]["with_scope"] == 1
    # The same projection whose derived chunk carries no product grant does
    # not cover the table (store-level authorization refused it).
    refused = audit(
        [datasheet], {}, scopes, {"d1" * 32: "datasheet"}, PRODUCTS, {"d1" * 32: {1}}
    )
    assert refused.bare == {("d1" * 32, "docling:p2:#/tables/0")}
    bare = audit(
        [datasheet], {}, {}, {"d1" * 32: "datasheet"}, PRODUCTS, {"d1" * 32: {1}}
    )
    assert bare.bare == {("d1" * 32, "docling:p2:#/tables/0")}
    assert bare.coverage["datasheet"]["bare_parameter_tables"] == 1


def test_parse_damaged_entry_needs_sibling_table_scope() -> None:
    sha, table = next(iter(PARSE_DAMAGED))
    damaged = _table_chunk(sha, table, 4, PARAMETER_TEXT)
    doc_types = {sha: "datasheet"}
    # No sibling document provides proven table scope: the entry is inert and
    # the gate blocks.
    blocked = audit([damaged], {}, {}, doc_types, PRODUCTS, {sha: {1}})
    assert blocked.bare == {(sha, table)}
    # A different document's proven table scope for every product exempts it.
    scopes = {
        "sibling": {
            "basis": "table_projection",
            "table_projection": {
                "source_sha256": "f" * 32,
                "source_table": "docling:p1:#/tables/0",
            },
        }
    }
    exempted = audit(
        [damaged],
        {"sibling": [1]},
        scopes,
        doc_types,
        PRODUCTS,
        {sha: {1}},
    )
    assert not exempted.bare
    assert exempted.exempted[(sha, table)] == PARSE_DAMAGED[(sha, table)]
    assert (
        exempted.coverage["datasheet"]["exempted_bare_tables"][
            PARSE_DAMAGED[(sha, table)]
        ]
        == 1
    )
    # A sibling that covers only part of the products does not exempt.
    partial = audit(
        [damaged],
        {"sibling": [1]},
        scopes,
        doc_types,
        PRODUCTS,
        {sha: {1, 2}},
    )
    assert partial.bare == {(sha, table)}


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
