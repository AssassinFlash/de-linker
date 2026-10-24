"""Compile native multi-model tables into current-model answer units."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from index.chunking import Chunk, Tokenizer
from index.inventory import document_kind_of
from index.publication import ScopeProof, _recognized, scope_proofs
from linker_genie.family_scope import family_id
from linker_genie.publication import PublicationClient, Snapshot
from linker_genie.publication_scope import author_scope_allows
from linker_genie.source_models import (
    ENGINEERING,
    codes,
    family_labels,
    family_mentions,
    model_pattern,
    model_shapes,
    unknown_models,
)
from linker_genie.table_projection import (
    SourceCell,
    cells_digest,
    model_axis,
    projection_id,
    read_cells,
    render_projection,
    safe_rows,
)

SCOPE_DECLARATION = re.compile(
    r"\b(?:only|solely|exclusively|appl(?:y|ies|icable)|instructions?|procedures?"
    r"|models?|modelle?|nur|ausschließlich|gelten|gilt|anweisungen)\b",
    re.IGNORECASE,
)


def _author_contexts(
    chunks: list[Chunk], source: Snapshot, statuses: dict[str, str]
) -> dict[str, list[dict[str, Any]]]:
    """Keep narrower context until an explicit family-wide heading resets it.

    Docling's heading levels are not consistently available. A generic next
    heading therefore cannot prove that a narrow parent ended. This deliberately
    fails closed across that boundary instead of guessing a sibling hierarchy.
    """
    models = {str(p.get("model", "")).casefold() for p in source.products.values()}
    labels = models.union(statuses)
    families = family_labels(labels)
    shapes = model_shapes(labels)
    active: dict[str, list[dict[str, Any]]] = {}
    previous: dict[str, str] = {}
    paths: dict[str, tuple[int, ...]] = {}
    output = {}
    for chunk in chunks:
        sha = chunk.doc_sha256
        boundaries = list(active.get(sha, []))
        headings = chunk.source_headings
        if not headings and chunk.section != previous.get(sha):
            headings = (chunk.section,) if chunk.section else ()
        previous[sha] = chunk.section
        for kind, text in [
            *(("heading", h) for h in headings),
            ("declaration", chunk.text),
        ]:
            if kind == "declaration" and (
                chunk.kind != "text" or SCOPE_DECLARATION.search(text) is None
            ):
                continue
            if kind == "heading":
                numbered = re.match(r"^\s*(\d+(?:\.\d+)*)(?:[.)]\s*|\s+)", text)
                if numbered is not None:
                    path = tuple(int(part) for part in numbered[1].split("."))
                    # Original chapter numbers prove a sibling/ancestor boundary.
                    # Missing/flat parser levels and unnumbered child titles do not.
                    boundaries = [
                        boundary
                        for boundary in boundaries
                        if not boundary.get("heading_path")
                        or path[: len(boundary["heading_path"])]
                        == tuple(boundary["heading_path"])
                    ]
                    paths[sha] = path
                else:
                    # An unnumbered narrower heading has no proven level. It
                    # must not borrow the previous chapter's path and later be
                    # cleared as though it were a numbered sibling's child.
                    paths.pop(sha, None)
            # Standalone original family headings are explicit broader resets.
            # A child title merely mentioning a family ('ports of H2') is not.
            plain = re.sub(r"^\s*[\d.]+\s*", "", text).strip()
            if kind == "heading" and any(
                re.fullmatch(
                    re.escape(family) + r"[-\s]+(?:series?|serie)", plain, re.IGNORECASE
                )
                for family in families
            ):
                boundaries = []
                continue
            broad_family = (
                kind == "heading"
                and not re.search(
                    r"\b(?:only|nur|solely|exclusively)\b", text, re.IGNORECASE
                )
                and re.search(
                    r"\b(?:series?|serie|solutions?|systems?|inverters?|wechselrichter)\b",
                    text,
                    re.IGNORECASE,
                )
                and any(
                    re.search(
                        r"(?<![\w./-])" + re.escape(f) + r"(?=[/\s]|$)",
                        text,
                        re.IGNORECASE,
                    )
                    for f in families
                )
                and all(
                    ENGINEERING.fullmatch(token)
                    or all(
                        re.fullmatch(r"[A-Za-z]+\d+", part) for part in token.split("/")
                    )
                    for token in codes(text)
                )
            )
            contained = {
                label for label in labels if label and model_pattern(label).search(text)
            }
            if contained or (
                not broad_family
                and unknown_models(
                    text,
                    contained,
                    shapes,
                    section=kind == "heading",
                    families=families,
                )
            ):
                boundaries.append(
                    {
                        "kind": kind,
                        "quote": text,
                        "source_chunk_id": chunk.id,
                        "heading_path": list(paths.get(sha, ())),
                    }
                )
        active[sha] = boundaries
        if boundaries:
            output[chunk.id] = boundaries
    return output


def _constrain(proof: ScopeProof, boundaries: list[dict[str, Any]]) -> ScopeProof:
    return {
        **proof,
        "author_restrictions": boundaries,
        "source_chunk_ids": list(
            dict.fromkeys(
                [
                    *proof["source_chunk_ids"],
                    *(b["source_chunk_id"] for b in boundaries),
                ]
            )
        ),
    }


def _scope(source: Snapshot, sha: str, pid: int, *, manual: bool = False) -> ScopeProof:
    documents = [
        document
        for document in source.documents.values()
        if document["blob_sha256"] == sha
        and pid in document["product_ids"]
        and (
            not manual
            or document_kind_of(str(document["type"]), str(document.get("role", "")))
            == "manual"
        )
    ]
    return {
        "product_ids": [pid],
        "basis": "table_projection",
        "source_chunk_ids": [],
        "document_ids": sorted(d["document_id"] for d in documents),
        "associations": [
            {
                "document_id": document["document_id"],
                "document_revision": document["document_revision"],
                "blob_sha256": sha,
                "product_id": pid,
                "product_revision": source.products[pid]["product_revision"],
            }
            for document in documents
        ],
    }


def _family_units(
    chunks: list[Chunk],
    source: Snapshot,
    statuses: dict[str, str],
    tokenizer: Tokenizer,
    max_tokens: int,
    strict: dict[str, ScopeProof],
    contexts: dict[str, list[dict[str, Any]]],
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Literal family manual scope plus Woo associations, with finer overrides.

    A family title can support shared instructions, never an unnamed parameter
    table or another variant's explicit facts. Each current model gets its own
    answer unit so removing B does not revoke unchanged common instructions for A.
    """
    models = {
        pid: str(product.get("model", "")) for pid, product in source.products.items()
    }
    labels = {model.casefold() for model in models.values() if model}.union(statuses)
    families = family_labels(labels)
    shapes = model_shapes(labels)
    origins: dict[str, dict[str, tuple[str, str]]] = {}
    for chunk in chunks:
        named = family_mentions(chunk.section, families)
        if len(named) != 1 or unknown_models(
            chunk.section, set(), shapes, section=True, families=families
        ):
            continue
        family = next(iter(named))
        origins.setdefault(chunk.doc_sha256, {}).setdefault(
            family, (chunk.id, chunk.section)
        )
    output: list[Chunk] = []
    scopes: dict[str, ScopeProof] = {}
    for chunk in chunks:
        if chunk.kind != "text":
            continue
        if chunk.id in strict or chunk.id in contexts:
            # Existing finer authored evidence is authoritative. A generic
            # family pass never widens it, including same-section continuation.
            continue
        own = family_mentions(chunk.section, families)
        candidates = origins.get(chunk.doc_sha256, {})
        if len(own) == 1:
            family = next(iter(own))
            anchor = (chunk.id, chunk.section)
        elif own or len(candidates) != 1:
            continue
        else:
            family, anchor = next(iter(candidates.items()))
        if any(
            model_pattern(label).search(chunk.text) for label in labels
        ) or unknown_models(
            chunk.section + "\n" + chunk.text,
            set(),
            shapes,
            section=True,
            families=families,
        ):
            continue
        for pid, model in models.items():
            if not model.casefold().startswith(family + "-"):
                continue
            proof = _scope(source, chunk.doc_sha256, pid, manual=True)
            if not proof["associations"]:
                continue
            header = " | ".join(
                part
                for part in [model, family, chunk.section, f"p. {chunk.page}"]
                if part
            )
            tokens = tokenizer.count(header + "\n" + chunk.text)
            if tokens > max_tokens:
                continue
            cid = family_id(chunk.doc_sha256, chunk.page, model, chunk.id, chunk.text)
            output.append(replace(chunk, id=cid, header=header, tokens=tokens))
            scopes[cid] = {
                **proof,
                "basis": "family_manual",
                "source_chunk_ids": list(dict.fromkeys([anchor[0], chunk.id])),
                "family_scope": {
                    "family": family,
                    "quote": anchor[1],
                    "anchor_chunk_id": anchor[0],
                    "source_chunk_id": chunk.id,
                    "source_page": chunk.page,
                    "source_sha256": chunk.doc_sha256,
                    "product_id": pid,
                    "model": model,
                    "text_sha256": hashlib.sha256(chunk.text.encode()).hexdigest(),
                },
            }
    return output, scopes


def _pack_rows(
    cells: Sequence[SourceCell],
    column: int,
    rows: Sequence[int],
    header: str,
    tokenizer: Tokenizer,
    max_tokens: int,
) -> list[list[int]]:
    """Keep source row boundaries; an oversized field is never silently cut."""
    groups: list[list[int]] = []
    current: list[int] = []
    for row in rows:
        text = render_projection(cells, column, [*current, row])
        assert text is not None
        if tokenizer.count(header + "\n" + text) > max_tokens:
            if current:
                groups.append(current)
                current = []
            text = render_projection(cells, column, [row])
            assert text is not None
            if tokenizer.count(header + "\n" + text) > max_tokens:
                continue
        current.append(row)
    if current:
        groups.append(current)
    return groups


def compile_scopes(
    chunks: list[Chunk],
    manifest: dict[str, Any],
    authority: PublicationClient,
    tokenizer: Tokenizer,
    max_tokens: int,
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Reuse original parses, binding each derived unit to its own Woo links."""
    source = Snapshot.read(manifest)
    shas = {document["blob_sha256"] for document in source.documents.values()}
    relevant = [chunk for chunk in chunks if chunk.doc_sha256 in shas]
    statuses = _recognized(relevant, authority)
    result = scope_proofs(chunks, manifest, authority, _statuses=statuses)
    contexts = _author_contexts(relevant, source, statuses)
    for cid in list(result):
        if cid not in contexts:
            continue
        constrained = _constrain(result[cid], contexts[cid])
        if author_scope_allows(
            constrained, set(constrained["product_ids"]), source.products
        ):
            result[cid] = constrained
        else:
            del result[cid]
    output = list(chunks)
    groups: dict[tuple[str, str], list[Chunk]] = {}
    for chunk in relevant:
        if chunk.kind == "table" and chunk.source_table:
            groups.setdefault((chunk.doc_sha256, chunk.source_table), []).append(chunk)
    current = {
        str(product.get("model", "")).casefold(): pid
        for pid, product in source.products.items()
        if product.get("model")
    }
    for (sha, table), parts in groups.items():
        first = parts[0]
        cells = read_cells(first.source_cells)
        if (
            cells is None
            or any(part.source_cells for part in parts[1:])
            or any(part.page != first.page for part in parts)
        ):
            continue
        axis = model_axis(cells)
        if axis is None:
            continue
        # Keep proven legacy whole passages in place. A projection does not
        # weaken their all-column current-association rule or reuse their IDs.
        known = [*current, *statuses, *axis]
        native_rows = sorted(
            {
                row
                for cell in cells
                for row in range(cell["row_start"], cell["row_end"])
                if row > 0
            }
        )
        for column, label in enumerate(axis, 1):
            pid = current.get(label.casefold())
            if (
                pid is None
                or statuses.get(label.casefold(), "published") != "published"
            ):
                continue
            proof = _scope(source, sha, pid)
            if not proof["associations"]:
                continue
            if first.id in contexts:
                proof = _constrain(proof, contexts[first.id])
                if not author_scope_allows(proof, {pid}, source.products):
                    continue
            model = str(source.products[pid]["model"])
            header = f"{model} | p. {first.page}"
            safe = [
                row
                for row in native_rows
                if render_projection(cells, column, [row]) is not None
                and safe_rows(cells, column, [row], model, known)
            ]
            for rows in _pack_rows(cells, column, safe, header, tokenizer, max_tokens):
                text = render_projection(cells, column, rows)
                assert text is not None
                cid = projection_id(sha, first.page, table, model, text)
                output.append(
                    replace(
                        first,
                        id=cid,
                        header=header,
                        text=text,
                        tokens=tokenizer.count(header + "\n" + text),
                        source_rows=tuple(rows),
                        source_cells=(),
                    )
                )
                result[cid] = {
                    **proof,
                    "source_chunk_ids": list(
                        dict.fromkeys(
                            [*proof["source_chunk_ids"], *(part.id for part in parts)]
                        )
                    ),
                    "table_projection": {
                        "source_sha256": sha,
                        "source_table": table,
                        "source_page": first.page,
                        "source_cells": list(cells),
                        "source_cells_sha256": cells_digest(cells),
                        "source_rows": rows,
                        "model_column": column,
                        "product_id": pid,
                        "model": model,
                        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    },
                }
    manual_units, manual_scopes = _family_units(
        relevant, source, statuses, tokenizer, max_tokens, result, contexts
    )
    output.extend(manual_units)
    result.update(manual_scopes)
    return output, result
