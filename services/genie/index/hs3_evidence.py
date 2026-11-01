"""Compile the reviewed HS3 conditional statement from three current originals."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

from index.chunking import Chunk, Tokenizer
from linker_genie.hs3_evidence import (
    CERTIFICATE,
    DATA_MODELS,
    DATASHEET,
    MANUAL,
    SOURCE_GROUPS,
    datasheet_axis,
    evidence_id,
    has_purpose,
    hs3_anchors,
    source_text,
    valid_hs3_scope,
    variants,
)
from linker_genie.publication import Snapshot

if TYPE_CHECKING:
    from index.publication import ScopeProof


def compile_hs3_evidence(
    chunks: list[Chunk],
    source: Snapshot,
    statuses: dict[str, str],
    tokenizer: Tokenizer,
    max_tokens: int,
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """One conditional passage per associated product and actual declaration."""
    originals = {chunk.id: chunk for chunk in chunks}
    groups = [
        group
        for group in SOURCE_GROUPS
        if all(cid in originals and not originals[cid].source_picture for cid in group)
    ]
    if len(groups) != 1:
        return [], {}
    group = groups[0]
    positions = {chunk.id: position for position, chunk in enumerate(chunks)}
    if [positions[cid] for cid in group[:3]] != sorted(
        positions[cid] for cid in group[:3]
    ):
        return [], {}
    anchors = hs3_anchors(
        (chunk.id, chunk.doc_sha256, chunk.page, chunk.kind, chunk.text)
        for chunk in chunks
        if chunk.id in group
    )
    if len(anchors) != len(group):
        return [], {}
    original = originals[group[2]]
    output: list[Chunk] = []
    proofs: dict[str, ScopeProof] = {}
    for pid, product in source.products.items():
        model = str(product.get("model", ""))
        text = source_text(model)
        if (
            variants(model) is None
            or text is None
            or statuses.get(model.casefold()) != "published"
        ):
            continue
        data_table = originals[DATA_MODELS]
        axis = datasheet_axis(model, data_table.source_cells)
        if data_table.source_table != "docling:p2:#/tables/0" or axis is None:
            continue
        # Each supporting source must itself be currently associated with this
        # product. SHA alone never substitutes for the document identity.
        choices: dict[str, list[dict[str, Any]]] = {}
        for role, sha in (
            ("certificate", CERTIFICATE),
            ("datasheet", DATASHEET),
            ("manual", MANUAL),
        ):
            choices[role] = sorted(
                (
                    doc
                    for doc in source.documents.values()
                    if doc.get("blob_sha256") == sha
                    and has_purpose(doc, role)
                    and pid in doc.get("product_ids", [])
                    and doc["document_id"] in product.get("documents", [])
                ),
                key=lambda doc: str(doc["document_id"]),
            )
        if any(not choices[role] for role in choices):
            continue
        # A proof binds these exact document identities and revisions; a removed
        # support invalidates it until a fresh build proves a replacement.
        supports = {role: choices[role][0] for role in ("datasheet", "manual")}
        for declaration in choices["certificate"]:
            selected = {"certificate": declaration, **supports}
            refs = {
                role: {
                    "document_id": doc["document_id"],
                    "document_revision": doc["document_revision"],
                    "blob_sha256": doc["blob_sha256"],
                }
                for role, doc in selected.items()
            }
            did = str(declaration["document_id"])
            cid = evidence_id(model, did, text)
            header = f"{model} | EU Declaration of Conformity | p. 1"
            tokens = tokenizer.count(header + "\n" + text)
            if tokens > max_tokens:
                continue
            proof: dict[str, Any] = {
                "product_ids": [pid],
                "basis": "hs3_conditional_certificate",
                "source_chunk_ids": list(group),
                "document_ids": [did],
                "associations": [
                    {
                        "document_id": did,
                        "document_revision": declaration["document_revision"],
                        "blob_sha256": CERTIFICATE,
                        "product_id": pid,
                        "product_revision": product["product_revision"],
                    }
                ],
                "hs3_conditional_certificate": {
                    "product_id": pid,
                    "product_revision": product["product_revision"],
                    "model": model,
                    "source_documents": refs,
                    "datasheet_axis": axis,
                },
            }
            if not valid_hs3_scope(
                proof,
                [pid],
                source.products,
                source.documents,
                sha=CERTIFICATE,
                chunk_id=cid,
                text=text,
                anchors=anchors,
            ):
                continue
            output.append(
                replace(
                    original,
                    id=cid,
                    page=1,
                    section="EU Declaration of Conformity",
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
            proofs[cid] = cast("ScopeProof", proof)
    return output, proofs
