"""Compile only conditional claims procedures with a manufacturer series chain."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from index.chunking import Chunk, Tokenizer
from index.inventory import document_kind_of
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.source_models import model_pattern
from linker_genie.table_projection import model_axis, read_cells
from linker_genie.warranty_scope import (
    FAMILY,
    POWER_RANGE,
    claims_procedure,
    exclusion_category,
    family_signature,
    procedure_id,
    series_matches,
    terms_id,
    terms_text,
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


def _family_cover(parts: list[Chunk]) -> tuple[Chunk, tuple[str, str, str]] | None:
    """Resolve a cover title and its range across chunks of the same page.

    Chunking repeats a section heading even where only the first chunk carries
    the range. Those repetitions do not contradict the ranged cover. A distinct
    explicit range or a second title still prevents a grant.
    """
    candidates: list[tuple[Chunk, tuple[str, str, str]]] = []
    for chunk in parts:
        if chunk.page != 1 or chunk.kind != "text" or chunk.source_picture:
            continue
        context = chunk.section + "\n" + chunk.text
        names = {name.casefold() for name in FAMILY.findall(context)}
        ranges = {
            tuple(str(Decimal(value.replace(",", ".")).normalize()) for value in pair)
            for pair in POWER_RANGE.findall(context)
        }
        if len(names) == 1 and len(ranges) > 1:
            return None
        family = family_signature(context)
        if family is not None:
            candidates.append((chunk, family))
    if not candidates:
        # A cover sentence can describe the named inverter and mention a battery
        # family later. Select only an explicit, adjacent series-and-range phrase;
        # two distinct ranged phrases remain ambiguous.
        for chunk in parts:
            if chunk.page != 1 or chunk.kind != "text" or chunk.source_picture:
                continue
            ranges = {
                tuple(
                    str(Decimal(value.replace(",", ".")).normalize()) for value in pair
                )
                for pair in POWER_RANGE.findall(chunk.section + "\n" + chunk.text)
            }
            if len(ranges) > 1:
                continue
            for match in re.finditer(
                r"\b[a-z][a-z0-9]*[-\s]+(?:series|serie)\s+"
                r"\d+(?:[.,]\d+)?\s*[-–]\s*\d+(?:[.,]\d+)?\s*kW\b",
                chunk.text,
                re.I,
            ):
                quote = match.group(0)
                signature = family_signature(quote)
                if signature is not None:
                    candidates.append(
                        (replace(chunk, section="", text=quote), signature)
                    )
    titles = {
        f[0]
        for c, f in candidates
        if re.fullmatch(r"\s*[a-z][a-z0-9]*[-\s]+(?:series|serie)\s*", c.section, re.I)
        or re.fullmatch(r"\s*[a-z][a-z0-9]*[-\s]+(?:series|serie)\s*", c.text, re.I)
    }
    if len(titles) > 1:
        return None
    if titles:
        name = next(iter(titles))
        # The named cover takes precedence over prose mentioning another system.
        candidates = [(c, f) for c, f in candidates if f[0] == name]
    elif len({f[0] for _, f in candidates}) != 1:
        return None
    ranged = {(f[1], f[2]) for _, f in candidates if f[1] or f[2]}
    if len(ranged) > 1:
        return None
    if ranged:
        signature = (candidates[0][1][0], *next(iter(ranged)))
        return next((c, f) for c, f in candidates if f == signature)
    return candidates[0] if candidates else None


def _unique_text(chunks: list[Chunk], *patterns: str) -> Chunk | None:
    matches = [
        c
        for c in chunks
        if all(re.search(pattern, c.text, re.I) for pattern in patterns)
    ]
    return matches[0] if len(matches) == 1 else None


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
        cover_result = _family_cover(
            [c for c in by_sha.get(sha, []) if c.id not in restricted_contexts]
        )
        if cover_result is None:
            continue
        cover, family = cover_result
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
                        **(
                            {"cover_pdf": cover.source_pdf_cover}
                            if cover.source_pdf_cover
                            else {}
                        ),
                        **(
                            {"cover_source_text": by_id[cover.id].text}
                            if cover.text != by_id[cover.id].text
                            else {}
                        ),
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


def compile_terms(
    original: list[Chunk],
    procedures: list[Chunk],
    proofs: Mapping[str, ScopeProof],
    tokenizer: Tokenizer,
    max_tokens: int,
    *,
    restricted_contexts: Mapping[str, list[dict[str, Any]]],
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Compile conditional policy rows only when every qualifying source exists."""
    by_sha: dict[str, list[Chunk]] = {}
    for chunk in original:
        by_sha.setdefault(chunk.doc_sha256, []).append(chunk)
    output: list[Chunk] = []
    added: dict[str, ScopeProof] = {}
    for procedure in procedures:
        proof = proofs.get(procedure.id)
        if proof is None or proof.get("basis") != "warranty_procedure":
            continue
        value = proof["warranty_scope"]
        parts = by_sha.get(procedure.doc_sha256, [])
        # Terms may not escape an authored model-specific section.
        usable = [
            c
            for c in parts
            if c.kind == "text"
            and c.id not in restricted_contexts
            and not c.source_picture
        ]

        if procedure.lang == "de":
            selected = {
                "overview": _unique_text(
                    usable,
                    r"ursprünglichen Käufer",
                    r"nicht übertragbar",
                    r"Ausschlüssen",
                ),
                "start": _unique_text(
                    usable, r"früheren", r"installiert", r"Herstellungsdatum", r"Monate"
                ),
                "effective": _unique_text(
                    usable,
                    r"Diese beschränkte Garantie gilt",
                    r"installiert",
                    r"es sei denn",
                    r"neuere",
                ),
                "geography": _unique_text(
                    usable, r"autorisierten", r"installiert", r"Norwegen", r"Schweiz"
                ),
                "exclusions": _unique_text(
                    usable, r"Herstellungs- und Materialfehler", r"Normaler Verschleiß"
                ),
            }
        else:
            selected = {
                "overview": _unique_text(
                    usable, r"original purchaser", r"non-transferable", r"exclusions"
                ),
                "start": _unique_text(
                    usable, r"earlier", r"first installed", r"production", r"months"
                ),
                "effective": _unique_text(
                    usable,
                    r"This Limited Warranty is effective",
                    r"installed",
                    r"unless",
                    r"newer",
                ),
                "geography": _unique_text(
                    usable, r"authorized", r"installed", r"Norway", r"Switzerland"
                ),
                "exclusions": _unique_text(
                    usable,
                    r"manufacturing and material defects",
                    r"Normal wear and tear",
                ),
            }
        if any(c is None for c in selected.values()):
            continue
        term_sources = {
            kind: {"chunk_id": c.id, "page": c.page, "lang": c.lang, "text": c.text}
            for kind, c in selected.items()
            if c is not None
        }
        native = {c.source_table: c for c in parts if c.source_cells}
        for chunk in parts:
            if (
                chunk.kind != "table"
                or chunk.id in restricted_contexts
                or not chunk.source_table
            ):
                continue
            table_anchor = native.get(chunk.source_table)
            cells = read_cells(table_anchor.source_cells if table_anchor else ())
            if cells is None:
                continue
            for row_index in chunk.source_rows:
                series_cells = [
                    c
                    for c in cells
                    if not c["column_header"]
                    and c["row_start"] == row_index
                    and c["col_start"] == 3
                    and c["col_end"] == 4
                ]
                if len(series_cells) != 1 or not series_matches(
                    series_cells[0]["text"], value["family"]
                ):
                    continue
                scoped = deepcopy(proof)
                scoped["basis"] = "warranty_terms"
                evidence = scoped["warranty_scope"]
                evidence["source_page"] = chunk.page
                evidence["source_chunk_id"] = chunk.id
                policy = evidence["policy"]
                policy["row_chunk_id"] = chunk.id
                policy["series_cell"] = series_cells[0]["text"]
                policy["row_quote"] = " | ".join(
                    c["text"]
                    for c in cells
                    if not c["column_header"]
                    and c["row_start"] <= row_index < c["row_end"]
                )
                policy["term_sources"] = term_sources
                policy["term_row"] = {
                    "row": row_index,
                    "cells": list(cells),
                    "source_table": chunk.source_table,
                    "table_anchor_id": table_anchor.id if table_anchor else "",
                    "source": {
                        "chunk_id": chunk.id,
                        "page": chunk.page,
                        "text": chunk.text,
                    },
                }
                scoped["source_chunk_ids"] = list(
                    dict.fromkeys(
                        [
                            *scoped["source_chunk_ids"],
                            chunk.id,
                            table_anchor.id if table_anchor else "",
                            *(str(c["chunk_id"]) for c in term_sources.values()),
                        ]
                    )
                )
                rendered = terms_text(evidence, scoped["source_chunk_ids"])
                if rendered is None:
                    continue
                text, _ = rendered
                cid = terms_id(
                    chunk.doc_sha256, chunk.page, evidence["model"], chunk.id, text
                )
                if cid in added:
                    continue
                header = f"{evidence['model']} | conditional warranty period, conditions and exclusions | p. {chunk.page}"
                tokens = tokenizer.count(header + "\n" + text)
                if tokens > max_tokens:
                    continue
                evidence["text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
                output.append(
                    replace(
                        chunk,
                        id=cid,
                        kind="text",
                        header=header,
                        text=text,
                        tokens=tokens,
                        source_cells=(),
                        source_rows=(),
                        source_table="",
                    )
                )
                added[cid] = scoped
    # Additional complete exclusion paragraphs remain separately retrievable,
    # each carrying the same purchaser, production, start and policy conditions.
    for base in list(output):
        original_proof = added[base.id]
        seen: set[str] = set()
        for chunk in by_sha.get(base.doc_sha256, []):
            if (
                chunk.kind != "text"
                or chunk.id in restricted_contexts
                or chunk.source_picture
                or chunk.section not in {"WARRANTY EXCEPTIONS", "AUSSCHLUSSBEDINGUNGEN"}
                or chunk.lang != base.lang
            ):
                continue
            for line in range(len(chunk.text.splitlines())):
                category = exclusion_category(chunk.text.splitlines()[line])
                if not category or category in seen:
                    continue
                scoped = deepcopy(original_proof)
                evidence = scoped["warranty_scope"]
                evidence["policy"]["additional_exclusion"] = {
                    "chunk_id": chunk.id,
                    "page": chunk.page,
                    "lang": chunk.lang,
                    "section": chunk.section,
                    "text": chunk.text,
                    "line": line,
                }
                scoped["source_chunk_ids"] = list(
                    dict.fromkeys([*scoped["source_chunk_ids"], chunk.id])
                )
                rendered = terms_text(evidence, scoped["source_chunk_ids"])
                if rendered is None:
                    continue
                text, _ = rendered
                cid = terms_id(
                    base.doc_sha256,
                    base.page,
                    evidence["model"],
                    evidence["source_chunk_id"],
                    text,
                )
                if cid in added:
                    continue
                header = f"{evidence['model']} | conditional warranty exclusions | p. {base.page}"
                tokens = tokenizer.count(header + "\n" + text)
                if tokens > max_tokens:
                    continue
                seen.add(category)
                evidence["text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
                output.append(
                    replace(base, id=cid, header=header, text=text, tokens=tokens)
                )
                added[cid] = scoped
    return output, added
