"""Per-table preparation gate: a bare parameter table must not read as prepared.

#900: the readiness check ran at (product_id, document_id) granularity, so one
approved marketing passage filled the pair while every parameter table of the
document stayed unauthorized (production epoch 86: 6321's 212 retrievable
chunks carried exactly one specification term). This module supplies the
per-table judgment behind the `table_without_scope` reason and the manifest's
`table_coverage`, with doc_type-specific standards (#900 report §9.7).

Exemptions are evidence-backed, never blanket (#900 round 2):
- Spec 609 "共用资料" explicitly allows a published PDF to contain content for
  devices that are not current products of that document ("工具只使用 A 适用
  内容，不将 B 作为当前产品"). A bare table whose physically proven axis
  names only such devices is B-content: reported, never blocking. The rule is
  re-derived from the live corpus and Woo product set every build, so listing
  a device or linking a document turns the alarm back into a requirement.
- Two datasheets' tables are parse-structure-damaged beyond the authorization
  rules (measured in #900; see PARSE_DAMAGED). They are excluded by name and
  only while a different current published document provides proven table
  scope for every product of the damaged one.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NamedTuple

from index.chunking import Chunk
from index.publication import PARAMETER_PROSE
from linker_genie.model_aliases import woo_model
from linker_genie.table_projection import model_axis, read_cells

# A gate-relevant parameter table spans at least this many native rows
# (#900 report §7.2: the parameter-table criterion used to measure the 969
# parameter-table groups was >= 4 rows, >= 2 columns, unit or engineering text).
TABLE_GATE_MIN_ROWS = 4
TABLE_GATE_MIN_COLUMNS = 2

# Tables whose parse structure is damaged beyond the authorization rules.
# Both conditions are re-verified on every audit; a table that gains scope,
# or a product that loses its sibling coverage, makes the entry inert and
# the gate blocking again.
#   4adebe72eb25 GoodWe ET 80-100 kW DE datasheet p.2: Docling 2.136 collapses
#   the four-column body to three and drops the 'Technische Daten' header line
#   (measured across all four TableFormer configurations, #900 §4.4). The
#   products' tables come from the EN twin (4f7178042e8f, six table grants).
#   e00f9645d187 SAJ HS3 5-12K DE datasheet p.2: a two-page spread whose body
#   cells collapse to stray fragments (#900 round 2). The five products'
#   tables come from the EN twin (b4a653fd2c0b).
# Both are withdrawal candidates per spec 609 if the German variants stay
# unparseable; the Woo-side decision belongs to the main line.
PARSE_DAMAGED: dict[tuple[str, str], str] = {
    (
        "4adebe72eb25f3bc8c23ec468cfdf6f9059f9aac52585ad492ed6a6dd9aaf9e2",
        "docling:p2:#/tables/0",
    ): "parse_structure_damaged_sibling_covered",
    (
        "e00f9645d187c241570a4037afa6a1dd54c23cd3d41b189bc44a0e0b24e4f7b3",
        "docling:p2:#/tables/0",
    ): "parse_structure_damaged_sibling_covered",
}


class TableGroup(NamedTuple):
    """One native parsed table: its fragments and the physical facts of the grid."""

    chunks: list[Chunk]
    rows: int
    columns: int
    parameter_prose: bool
    axis_proven: bool
    axis_labels: list[str]


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
    axis = model_axis(cells) if cells is not None else None
    return TableGroup(
        chunks=list(fragments),
        rows=len(rows),
        columns=columns,
        parameter_prose=any(PARAMETER_PROSE.search(part.text) for part in fragments),
        axis_proven=axis is not None,
        axis_labels=list(axis or []),
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


def b_content_reason(
    group: TableGroup,
    document_products: set[int],
    products: Mapping[int, Mapping[str, Any]],
) -> str | None:
    """Why a bare table can never gain this document's product scope (spec 609).

    '工具只使用 A 适用内容，不将 B 作为当前产品回答': a table whose physically
    proven axis names only devices that are not current products associated
    with this document is B-content. `device_not_associated` additionally
    signals that the device exists in Woo under another document — a missing
    Woo link, for the main line to decide — while `device_not_published`
    names a device Woo does not carry at all.
    """
    if not group.axis_labels:
        return None
    own = {
        str(products[pid].get("model", "")).casefold()
        for pid in document_products
        if pid in products and products[pid].get("model")
    }
    woo_models = {
        str(product.get("model", "")).casefold()
        for product in products.values()
        if product.get("model")
    }
    resolved = [woo_model(label) for label in group.axis_labels]
    if any(label in own for label in resolved):
        return None
    if any(label in woo_models for label in resolved):
        return "device_not_associated"
    return "device_not_published"


class TableAudit(NamedTuple):
    """The gate outcome: blocking bare groups, exemptions, coverage counts."""

    bare: set[tuple[str, str]]
    exempted: dict[tuple[str, str], str]
    coverage: dict[str, dict[str, Any]]


def audit(
    chunks: Iterable[Chunk],
    chunk_products: Mapping[str, Sequence[int]],
    chunk_scopes: Mapping[str, Mapping[str, Any]],
    doc_types: Mapping[str, str],
    products: Mapping[int, Mapping[str, Any]],
    document_products: Mapping[str, set[int]],
) -> TableAudit:
    """Judge every table group of the corpus against its doc_type standard."""
    authorized = authorized_tables(chunk_products, chunk_scopes)
    # Proven table scope per document, for the sibling-coverage condition.
    # table_columns grants live on the native fragments themselves, so their
    # document comes from the chunk list.
    chunk_docs = {
        chunk.id: chunk.doc_sha256
        for chunk in chunks
        if chunk.kind == "table" and chunk.source_table
    }
    scoped_products: dict[str, set[int]] = {}
    for cid, scope in chunk_scopes.items():
        if not isinstance(scope, dict) or cid not in chunk_products:
            continue
        for key in ("table_projection", "single_model_projection"):
            value = scope.get(key)
            if isinstance(value, dict) and isinstance(value.get("source_sha256"), str):
                scoped_products.setdefault(value["source_sha256"], set()).update(
                    chunk_products[cid]
                )
        columns = scope.get("table_columns")
        if (
            isinstance(columns, dict)
            and isinstance(columns.get("source_table"), str)
            and cid in chunk_docs
        ):
            scoped_products.setdefault(chunk_docs[cid], set()).update(
                chunk_products[cid]
            )
    bare: set[tuple[str, str]] = set()
    exempted: dict[tuple[str, str], str] = {}
    coverage: dict[str, dict[str, Any]] = {}
    for (sha, table), fragments in table_groups(chunks).items():
        info = group_info(fragments)
        if info is None:
            continue
        doc_type = doc_types.get(sha, "other")
        counts = coverage.setdefault(
            doc_type,
            {
                "tables": 0,
                "with_scope": 0,
                "bare_parameter_tables": 0,
                "exempted_bare_tables": {},
            },
        )
        counts["tables"] += 1
        if (sha, table) in authorized or any(
            part.id in chunk_products for part in fragments
        ):
            counts["with_scope"] += 1
            continue
        if not gate_fails(doc_type, info):
            continue
        reason = b_content_reason(info, document_products.get(sha, set()), products)
        if reason is None and (sha, table) in PARSE_DAMAGED:
            siblings = {
                pid
                for other_sha, pids in scoped_products.items()
                if other_sha != sha
                for pid in pids
            }
            if document_products.get(sha, set()) and document_products[sha] <= siblings:
                reason = PARSE_DAMAGED[(sha, table)]
        if reason is not None:
            exempted[(sha, table)] = reason
            reasons = counts["exempted_bare_tables"]
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        bare.add((sha, table))
        counts["bare_parameter_tables"] += 1
    return TableAudit(bare=bare, exempted=exempted, coverage=coverage)
