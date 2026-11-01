"""Compile explicit-model warranty passages with source-complete conditions."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import replace
from typing import Any, cast

from index.chunking import Chunk, Tokenizer
from index.inventory import document_kind_of
from index.publication import ScopeProof
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import author_scope_allows
from linker_genie.warranty_named import (
    EXCLUSION_INTRO,
    FORMAT,
    LATEST,
    LEGAL,
    LOCAL,
    is_named_policy_overview,
    render_named_terms,
)
from linker_genie.warranty_named_de import EXCLUSIONS
from linker_genie.warranty_scope import terms_id


def _one(
    parts: list[Chunk], section: str, page: int, contains: str = ""
) -> Chunk | None:
    matches = [
        chunk
        for chunk in parts
        if chunk.page == page
        and chunk.section == section
        and chunk.kind == "text"
        and chunk.lang == "en"
        and not chunk.source_picture
        and contains in chunk.text
    ]
    return matches[0] if len(matches) == 1 else None


def compile_named_terms(
    original: list[Chunk],
    source: Snapshot,
    tokenizer: Tokenizer,
    max_tokens: int,
    *,
    restricted_contexts: Mapping[str, list[dict[str, Any]]],
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Compile only complete explicit-model rows under a current Woo association."""
    by_sha: dict[str, list[Chunk]] = {}
    by_id = {chunk.id: chunk for chunk in original}
    for chunk in original:
        by_sha.setdefault(chunk.doc_sha256, []).append(chunk)
    output: list[Chunk] = []
    scopes: dict[str, ScopeProof] = {}
    for document in source.documents.values():
        if (
            document_kind_of(str(document["type"]), str(document.get("role", "")))
            != "warranty"
        ):
            continue
        sha = str(document["blob_sha256"])
        parts = by_sha.get(sha, [])
        selected = {
            "overview": _one(parts, "OVERVIEW", 1),
            "coverage": _one(parts, "WHAT IS COVERED AND NOT COVERED?", 1),
            "geography": _one(parts, "GEOGRAPHICAL SCOPE", 3),
            "effective": _one(
                parts,
                "LIMITATION OF GOODWE's LIABILITY",
                3,
                "This limited warranty applies to the product which is sold and installed",
            ),
            "legal": _one(parts, "LIMITATION OF GOODWE's LIABILITY", 3, LEGAL),
            "local": _one(parts, "LIMITATION OF GOODWE's LIABILITY", 3, LOCAL),
            "latest": _one(parts, "LIMITATION OF GOODWE's LIABILITY", 3, LATEST),
        }
        if any(chunk is None for chunk in selected.values()):
            continue
        chosen = {key: chunk for key, chunk in selected.items() if chunk is not None}
        overview = chosen["overview"]
        if not is_named_policy_overview(overview.text):
            continue
        exclusions = [
            chunk
            for chunk in parts
            if chunk.page == 2
            and chunk.section == "WARRANTY EXCEPTIONS"
            and chunk.kind == "text"
            and chunk.lang == "en"
            and not chunk.source_picture
        ]
        exclusion_lines = [
            (chunk, index, line.strip())
            for chunk in exclusions
            for index, line in enumerate(chunk.text.splitlines())
            if line.strip()
        ]
        if sum(line == EXCLUSION_INTRO for _, _, line in exclusion_lines) != 1 or [
            line for _, _, line in exclusion_lines if line != EXCLUSION_INTRO
        ] != list(EXCLUSIONS):
            continue
        boundaries: list[dict[str, Any]] = []
        for chunk in [*chosen.values(), *exclusions]:
            for boundary in restricted_contexts.get(chunk.id, []):
                # The full overview is handled by this parser: it distinguishes
                # exact model lists and the explicit UK/non-UK policy rows.
                if (
                    boundary.get("kind") == "declaration"
                    and boundary.get("source_chunk_id") == overview.id
                    and boundary.get("quote") == overview.text
                ):
                    continue
                if boundary not in boundaries:
                    boundaries.append(boundary)
        if any(
            (prior := by_id.get(str(boundary.get("source_chunk_id", "")))) is None
            or prior.doc_sha256 != sha
            or not isinstance(boundary.get("quote"), str)
            or not boundary["quote"]
            or boundary["quote"]
            not in "\n".join([prior.text, prior.section, *prior.source_headings])
            for boundary in boundaries
        ):
            continue
        origins = list(
            dict.fromkeys(
                [
                    *(chunk.id for chunk in [*chosen.values(), *exclusions]),
                    *(str(b["source_chunk_id"]) for b in boundaries),
                ]
            )
        )
        source_rows: dict[str, Any] = {
            key: {
                "chunk_id": chunk.id,
                "page": chunk.page,
                "section": chunk.section,
                "lang": chunk.lang,
                "text": chunk.text,
            }
            for key, chunk in chosen.items()
        }
        source_rows["exclusions"] = [
            {
                "chunk_id": chunk.id,
                "page": chunk.page,
                "section": chunk.section,
                "lang": chunk.lang,
                "text": chunk.text,
            }
            for chunk in exclusions
        ]
        for pid in document["product_ids"]:
            product = source.products.get(pid)
            if not product or document["document_id"] not in product.get(
                "documents", []
            ):
                continue
            model = str(product.get("model", ""))
            if not model:
                continue
            proof: dict[str, Any] = {
                "product_ids": [pid],
                "basis": "warranty_terms",
                "source_chunk_ids": origins,
                "document_ids": [document["document_id"]],
                "associations": [
                    {
                        "document_id": document["document_id"],
                        "document_revision": document["document_revision"],
                        "blob_sha256": sha,
                        "product_id": pid,
                        "product_revision": product["product_revision"],
                    }
                ],
                "warranty_scope": {
                    "product_id": pid,
                    "model": model,
                    "conditional": True,
                    "source_sha256": sha,
                    "source_page": 1,
                    "source_chunk_id": overview.id,
                    "policy": {
                        "format": FORMAT,
                        "document_id": document["document_id"],
                        "document_revision": document["document_revision"],
                        "blob_sha256": sha,
                        "sources": source_rows,
                    },
                },
            }
            if boundaries:
                proof["author_restrictions"] = boundaries
                if not author_scope_allows(proof, {pid}, source.products):
                    continue
            for exclusion_chunk, index, line in exclusion_lines:
                if line == EXCLUSION_INTRO:
                    continue
                evidence = proof["warranty_scope"]
                evidence["policy"]["exclusion_index"] = index
                evidence["policy"]["exclusion_source_id"] = exclusion_chunk.id
                rendered = render_named_terms(evidence, origins)
                if rendered is None:
                    continue
                text, _notes = rendered
                header = f"{model} | warranty | p. 1"
                tokens = tokenizer.count(header + "\n" + text)
                if tokens > max_tokens:
                    continue
                cid = terms_id(sha, 1, model, overview.id, text)
                if cid in scopes:
                    continue
                scoped = {
                    **proof,
                    "warranty_scope": {
                        **evidence,
                        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "policy": {**evidence["policy"]},
                    },
                }
                output.append(
                    replace(overview, id=cid, header=header, text=text, tokens=tokens)
                )
                scopes[cid] = cast(ScopeProof, scoped)
    return output, scopes
