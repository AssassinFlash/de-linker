"""Compile the reviewed HS3 standard warranty from three current originals."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

from index.chunking import Chunk, Tokenizer
from linker_genie.hs3_evidence import (
    DATA_MODELS,
    DATASHEET,
    MANUAL,
    MANUAL_MODEL,
    datasheet_axis,
    has_purpose,
    hs3_anchors,
    variants,
)
from linker_genie.hs3_warranty_terms import (
    FORMAT,
    POLICY,
    ROW,
    SOURCES,
    anchor_key,
    anchors,
    evidence_id,
    rendered,
    valid_scope,
)
from linker_genie.publication import Snapshot

if TYPE_CHECKING:
    from index.publication import ScopeProof


def compile_hs3_warranty_terms(
    chunks: list[Chunk],
    source: Snapshot,
    statuses: dict[str, str],
    tokenizer: Tokenizer,
    max_tokens: int,
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    originals = {chunk.id: chunk for chunk in chunks}
    if any(
        cid not in originals or originals[cid].source_picture
        for cid in (*SOURCES, DATA_MODELS, MANUAL_MODEL)
    ):
        return [], {}
    source_rows = [(c.id, c.doc_sha256, c.page, c.kind, c.text) for c in chunks]
    policy_anchors = anchors(source_rows)
    model_anchors = hs3_anchors(source_rows)
    if len(policy_anchors) != len(SOURCES) or not all(
        "hs3:" + cid in model_anchors for cid in (DATA_MODELS, MANUAL_MODEL)
    ):
        return [], {}
    all_anchors = {**policy_anchors, **model_anchors}
    data = originals[DATA_MODELS]
    if data.source_table != "docling:p2:#/tables/0":
        return [], {}
    output: list[Chunk] = []
    scopes: dict[str, ScopeProof] = {}
    for pid, product in source.products.items():
        model = str(product.get("model", ""))
        rendered_terms = rendered(model)
        axis = datasheet_axis(model, data.source_cells)
        if (
            variants(model) is None
            or rendered_terms is None
            or axis is None
            or statuses.get(model.casefold()) != "published"
        ):
            continue
        choices: dict[str, list[dict[str, Any]]] = {}
        for role, sha in (
            ("policy", POLICY),
            ("datasheet", DATASHEET),
            ("manual", MANUAL),
        ):
            purpose = "warranty" if role == "policy" else role
            choices[role] = sorted(
                (
                    d
                    for d in source.documents.values()
                    if d.get("blob_sha256") == sha
                    and has_purpose(d, purpose)
                    and pid in d.get("product_ids", [])
                    and d["document_id"] in product.get("documents", [])
                ),
                key=lambda d: str(d["document_id"]),
            )
        if any(not choices[role] for role in choices):
            continue
        for policy in choices["policy"]:
            selected = {
                "policy": policy,
                "datasheet": choices["datasheet"][0],
                "manual": choices["manual"][0],
            }
            refs = {
                role: {
                    "document_id": d["document_id"],
                    "document_revision": d["document_revision"],
                    "blob_sha256": d["blob_sha256"],
                }
                for role, d in selected.items()
            }
            did, text = str(policy["document_id"]), rendered_terms[0]
            cid = evidence_id(model, did, text)
            header = f"{model} | SAJ HS3 limited warranty | p. 1"
            tokens = tokenizer.count(header + "\n" + text)
            if tokens > max_tokens:
                continue
            proof: dict[str, Any] = {
                "product_ids": [pid],
                "basis": "warranty_terms",
                "source_chunk_ids": [*SOURCES, DATA_MODELS, MANUAL_MODEL],
                "document_ids": [did],
                "associations": [
                    {
                        "document_id": did,
                        "document_revision": policy["document_revision"],
                        "blob_sha256": POLICY,
                        "product_id": pid,
                        "product_revision": product["product_revision"],
                    }
                ],
                "warranty_scope": {
                    "product_id": pid,
                    "product_revision": product["product_revision"],
                    "model": model,
                    "source_documents": refs,
                    "datasheet_axis": axis,
                    "policy": {
                        "format": FORMAT,
                        "sources": {
                            cid: policy_anchors[anchor_key(cid)] for cid in SOURCES
                        },
                    },
                },
            }
            if not valid_scope(
                proof,
                [pid],
                source.products,
                source.documents,
                sha=POLICY,
                chunk_id=cid,
                text=text,
                external_axis_anchors=all_anchors,
            ):
                continue
            output.append(
                replace(
                    originals[ROW],
                    id=cid,
                    page=1,
                    section="HS3 standard limited warranty",
                    kind="text",
                    header=header,
                    text=text,
                    lang="en",
                    tokens=tokens,
                    source_table="",
                    preceding_text=(),
                    source_rows=(),
                    source_cells=(),
                    source_headings=(),
                    source_picture="",
                    source_pdf_cover=None,
                    source_certificate_evidence=(),
                    source_physical_evidence=(),
                )
            )
            scopes[cid] = cast("ScopeProof", proof)
    return output, scopes
