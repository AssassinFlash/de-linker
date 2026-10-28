"""Compile only conditional claims procedures with a manufacturer series chain."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from index.chunking import Chunk, Tokenizer
from index.inventory import document_kind_of
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.source_models import model_pattern
from linker_genie.table_projection import model_axis, read_cells
from linker_genie.warranty_scope import (
    claims_procedure,
    family_signature,
    procedure_id,
    series_matches,
)

if TYPE_CHECKING:
    from index.publication import ScopeProof


def _rows(chunk: Chunk) -> list[tuple[str, str]]:
    """Series cell and complete original row, never an adjacent row's terms."""
    cells = read_cells(chunk.source_cells)
    if cells is None or not chunk.source_rows:
        return []
    columns = {
        c["col_start"]
        for c in cells
        if c["column_header"] and c["text"].strip().casefold() in {"series", "serien"}
    }
    if len(columns) != 1:
        return []
    column = next(iter(columns))
    output = []
    for cell in cells:
        if (
            cell["row_start"] not in chunk.source_rows
            or cell["column_header"]
            or cell["col_start"] != column
            or cell["col_end"] != column + 1
        ):
            continue
        row = sorted(
            [c for c in cells if c["row_start"] == cell["row_start"]],
            key=lambda c: c["col_start"],
        )
        output.append((cell["text"], " | ".join(c["text"] for c in row)))
    return output


def compile_procedures(
    original: list[Chunk],
    compiled: list[Chunk],
    scopes: Mapping[str, ScopeProof],
    source: Snapshot,
    tokenizer: Tokenizer,
    max_tokens: int,
    *,
    restricted_contexts: Mapping[str, list[dict[str, Any]]],
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Leave existing grants intact and append individually bound procedure units."""
    from index.table_compiler import external_axis_anchors

    axis_anchors = external_axis_anchors(original)
    # Reuse the authority-aware compiler's context, including non-public model
    # labels. A public snapshot alone cannot reconstruct narrower boundaries.
    links = [
        {
            "document_id": d["document_id"],
            "document_revision": d["document_revision"],
            "blob_sha256": d["blob_sha256"],
            "product_id": pid,
            "product_revision": source.products[pid]["product_revision"],
        }
        for d in source.documents.values()
        for pid in d["product_ids"]
        if pid in source.products
    ]
    by_sha: dict[str, list[Chunk]] = {}
    by_id = {chunk.id: chunk for chunk in original}
    for chunk in original:
        by_sha.setdefault(chunk.doc_sha256, []).append(chunk)
    sheets: dict[int, list[dict[str, Any]]] = {}
    for document in source.documents.values():
        if (
            document_kind_of(str(document["type"]), str(document.get("role", "")))
            != "datasheet"
        ):
            continue
        sha = document["blob_sha256"]
        covers = [
            (c, family_signature(c.section + "\n" + c.text))
            for c in by_sha.get(sha, [])
            if c.page == 1 and c.kind == "text"
        ]
        covers = [(c, family) for c, family in covers if family is not None]
        if len({family for _, family in covers}) != 1:
            continue
        cover, family = covers[0]
        assert family is not None
        for chunk in compiled:
            proof = scopes.get(chunk.id)
            if chunk.doc_sha256 != sha or proof is None:
                continue
            if not authorize_chunk(
                sha,
                proof["product_ids"],
                links,
                proof,
                products=source.products,
                documents=source.documents,
                chunk_id=chunk.id,
                text=chunk.text,
                external_axis_anchors=axis_anchors,
                require_table_anchor=True,
            ):
                continue
            for pid in proof["product_ids"]:
                model = str(source.products[pid].get("model", ""))
                if pid not in document["product_ids"] or not model:
                    continue
                projection = proof.get("table_projection", {})
                cells = read_cells(projection.get("source_cells", []))
                header_cells = [c for c in cells or [] if c["row_start"] == 0]
                axis = model_axis(header_cells) if header_cells else None
                label = next(
                    (v for v in axis or [] if v.casefold() == model.casefold()), None
                )
                if label is not None:
                    model_id, model_quote, model_page = chunk.id, label, chunk.page
                else:
                    anchor = next(
                        (
                            c
                            for cid in [chunk.id, *proof["source_chunk_ids"]]
                            if (c := by_id.get(cid)) is not None
                            and c.doc_sha256 == sha
                            and model_pattern(model).search(c.section + "\n" + c.text)
                        ),
                        None,
                    )
                    if anchor is None:
                        continue
                    model_id, model_quote, model_page = (
                        anchor.id,
                        anchor.section + "\n" + anchor.text,
                        anchor.page,
                    )
                if any(
                    s["document_id"] == document["document_id"]
                    for s in sheets.get(pid, [])
                ):
                    continue
                sheets.setdefault(pid, []).append(
                    {
                        "document_id": document["document_id"],
                        "document_revision": document["document_revision"],
                        "blob_sha256": sha,
                        "cover_chunk_id": cover.id,
                        "cover_quote": cover.section + "\n" + cover.text,
                        "model_chunk_id": model_id,
                        "model_quote": model_quote,
                        "model_header_cells": header_cells if label else [],
                        "model_source_page": model_page,
                        "family": list(family),
                    }
                )
    output: list[Chunk] = []
    added: dict[str, ScopeProof] = {}
    for document in source.documents.values():
        if (
            document_kind_of(str(document["type"]), str(document.get("role", "")))
            != "warranty"
        ):
            continue
        sha = document["blob_sha256"]
        parts = by_sha.get(sha, [])
        # Cells are stored once per immutable native TableItem; later fragments
        # keep that table identity and their original row indices.
        native_cells = {c.source_table: c.source_cells for c in parts if c.source_cells}
        rows = [
            (c, cell, row)
            for c in parts
            if c.kind == "table"
            for cell, row in _rows(
                replace(
                    c, source_cells=native_cells.get(c.source_table, c.source_cells)
                )
            )
        ]
        conditions = [
            {"chunk_id": c.id, "page": c.page, "quote": c.text}
            for c in parts
            if c.kind == "text"
            and not claims_procedure(c.text)
            and re.search(
                r"purchas|Käufer|policy|Garantiebedingungen|authorized|authorised|install",
                c.text,
                re.I,
            )
        ]
        if not conditions:
            continue
        for chunk in parts:
            if (
                chunk.kind != "text"
                or chunk.id in scopes
                or chunk.id in restricted_contexts
                or not claims_procedure(chunk.text)
            ):
                continue
            for pid in document["product_ids"]:
                if pid not in source.products:
                    continue
                product = source.products[pid]
                brand = str(product.get("brand", ""))
                if not brand or not any(
                    re.search(rf"\b{re.escape(brand)}\b", str(c["quote"]), re.I)
                    for c in conditions
                ):
                    continue
                chain = next(
                    (
                        (sheet, row, cell, quote)
                        for sheet in sheets.get(pid, [])
                        for row, cell, quote in rows
                        if series_matches(cell, sheet["family"])
                    ),
                    None,
                )
                if chain is None:
                    continue
                sheet, row, cell, quote = chain
                model = str(product["model"])
                cid = procedure_id(sha, chunk.page, model, chunk.id, chunk.text)
                if cid in added:
                    continue
                header = f"{model} | conditional claims procedure; coverage and duration unverified | p. {chunk.page}"
                tokens = tokenizer.count(header + "\n" + chunk.text)
                if tokens > max_tokens:
                    continue
                output.append(replace(chunk, id=cid, header=header, tokens=tokens))
                evidence = {
                    "product_id": pid,
                    "model": model,
                    "conditional": True,
                    "source_sha256": sha,
                    "source_page": chunk.page,
                    "source_chunk_id": chunk.id,
                    "text_sha256": hashlib.sha256(chunk.text.encode()).hexdigest(),
                    "family": sheet["family"],
                    "datasheet": sheet,
                    "policy": {
                        "document_id": document["document_id"],
                        "document_revision": document["document_revision"],
                        "blob_sha256": sha,
                        "row_chunk_id": row.id,
                        "series_cell": cell,
                        "row_quote": quote,
                        "conditions": conditions,
                    },
                }
                added[cid] = {
                    "product_ids": [pid],
                    "basis": "warranty_procedure",
                    "source_chunk_ids": list(
                        dict.fromkeys(
                            [
                                chunk.id,
                                row.id,
                                sheet["cover_chunk_id"],
                                sheet["model_chunk_id"],
                                *(str(c["chunk_id"]) for c in conditions),
                            ]
                        )
                    ),
                    "document_ids": [document["document_id"]],
                    "associations": [
                        item
                        for item in links
                        if item["document_id"] == document["document_id"]
                        and item["product_id"] == pid
                    ],
                    "warranty_scope": evidence,
                }
    return output, added
