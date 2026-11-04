"""Per-table preparation gate: a bare parameter table must not read as prepared.

#900: the readiness check ran at (product_id, document_id) granularity, so one
approved marketing passage filled the pair while every parameter table of the
document stayed unauthorized (production epoch 86: 6321's 212 retrievable
chunks carried exactly one specification term). This module supplies the
per-table judgment behind the `table_without_scope` reason and the manifest's
`table_coverage`, with doc_type-specific standards (#900 report §9.7).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NamedTuple

from index.chunking import Chunk
from index.publication import PARAMETER_PROSE
from linker_genie.table_projection import model_axis, read_cells

# A gate-relevant parameter table spans at least this many native rows
# (#900 report §7.2: the parameter-table criterion used to measure the 969
# parameter-table groups was >= 4 rows, >= 2 columns, unit or engineering text).
TABLE_GATE_MIN_ROWS = 4
TABLE_GATE_MIN_COLUMNS = 2


class TableGroup(NamedTuple):
    """One native parsed table: its fragments and the physical facts of the grid."""

    chunks: list[Chunk]
    rows: int
    columns: int
    parameter_prose: bool
    axis_proven: bool


def table_groups(chunks: Iterable[Chunk]) -> dict[tuple[str, str], list[Chunk]]:
    """Fragments grouped by their original parsed TableItem."""
    groups: dict[tuple[str, str], list[Chunk]] = {}
    for chunk in chunks:
        if chunk.kind == "table" and chunk.source_table:
            groups.setdefault((chunk.doc_sha256, chunk.source_table), []).append(chunk)
    return groups


def authorized_tables(
    chunk_products: Mapping[str, Sequence[int]],
    chunk_scopes: Mapping[str, Mapping[str, Any]],
) -> set[tuple[str, str]]:
    """Tables proven by a projection stored under its own derived chunk id.

    A projection's native fragments keep no product rows of their own, so the
    table it proves is reachable only through the scope's recorded source
    identity (#900 decision note: table grants must be judged per (document,
    source_table), never by a native chunk's own product rows alone). A
    projection only covers its table while its derived chunk itself carries a
    product grant in `chunk_products` — at store level that mapping contains
    exactly the chunks that passed authorization, so a proof rejected there
    can never silently cover a bare table.
    """
    authorized: set[tuple[str, str]] = set()
    for cid, scope in chunk_scopes.items():
        if not isinstance(scope, dict) or cid not in chunk_products:
            continue
        for key in (
            "table_projection",
            "single_model_projection",
            "compatibility_pair",
            "compatibility_series",
        ):
            value = scope.get(key)
            if (
                isinstance(value, dict)
                and isinstance(value.get("source_sha256"), str)
                and isinstance(value.get("source_table"), str)
            ):
                authorized.add((value["source_sha256"], value["source_table"]))
    return authorized


def group_info(fragments: Sequence[Chunk]) -> TableGroup | None:
    rows = {row for part in fragments for row in part.source_rows}
    first = fragments[0]
    cells = read_cells(first.source_cells) if first.source_cells else None
    columns = max((cell["col_end"] for cell in cells), default=0) if cells else 0
    return TableGroup(
        chunks=list(fragments),
        rows=len(rows),
        columns=columns,
        parameter_prose=any(PARAMETER_PROSE.search(part.text) for part in fragments),
        axis_proven=model_axis(cells) is not None if cells is not None else False,
    )


def gate_fails(doc_type: str, group: TableGroup) -> bool:
    """doc_type-specific standard for one bare table (#900 report §9.7).

    - datasheet: any parameter table (>= TABLE_GATE_MIN_ROWS rows,
      >= TABLE_GATE_MIN_COLUMNS columns, unit/engineering text) must carry scope;
    - compatibility: every table must carry a scope (production stood at 0/266);
    - certificate: layout tables dominate, nothing is required;
    - manual and the rest: only a physically proven model axis obliges a scope,
      so generic warning/symbol/checklist tables stay exempt while a compile-side
      veto of a proven axis is always a defect.
    """
    if doc_type == "datasheet":
        return (
            group.rows >= TABLE_GATE_MIN_ROWS
            and group.columns >= TABLE_GATE_MIN_COLUMNS
            and group.parameter_prose
        )
    if doc_type == "compatibility":
        return True
    if doc_type == "certificate":
        return False
    return group.axis_proven


class TableAudit(NamedTuple):
    """The gate outcome: bare groups per standard, and manifest coverage counts."""

    bare: set[tuple[str, str]]
    coverage: dict[str, dict[str, int]]


def audit(
    chunks: Iterable[Chunk],
    chunk_products: Mapping[str, Sequence[int]],
    chunk_scopes: Mapping[str, Mapping[str, Any]],
    doc_types: Mapping[str, str],
) -> TableAudit:
    """Judge every table group of the corpus against its doc_type standard."""
    authorized = authorized_tables(chunk_products, chunk_scopes)
    bare: set[tuple[str, str]] = set()
    coverage: dict[str, dict[str, int]] = {}
    for (sha, table), fragments in table_groups(chunks).items():
        info = group_info(fragments)
        if info is None:
            continue
        doc_type = doc_types.get(sha, "other")
        counts = coverage.setdefault(
            doc_type, {"tables": 0, "with_scope": 0, "bare_parameter_tables": 0}
        )
        counts["tables"] += 1
        if (sha, table) in authorized or any(
            part.id in chunk_products for part in fragments
        ):
            counts["with_scope"] += 1
            continue
        if gate_fails(doc_type, info):
            bare.add((sha, table))
            counts["bare_parameter_tables"] += 1
    return TableAudit(bare=bare, coverage=coverage)
