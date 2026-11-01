"""Compile reviewed source passages with the current manual associations."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import replace
from typing import Any, cast

from index.chunking import Chunk, Tokenizer
from index.inventory import document_kind_of
from index.publication import ScopeProof
from linker_genie.manual_diagram import model_list_descriptor, physical_descriptor
from linker_genie.manual_diagram_records import DIAGRAMS
from linker_genie.manual_evidence import evidence_id, subject_matches
from linker_genie.manual_evidence_records import RECORDS
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import author_scope_allows


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def compile_manual_evidence(
    chunks: list[Chunk],
    source: Snapshot,
    tokenizer: Tokenizer,
    max_tokens: int,
    *,
    restricted_contexts: Mapping[str, list[dict[str, Any]]],
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Use literal, reviewed paragraphs, never an inferred whole-document grant."""
    by_id = {chunk.id: chunk for chunk in chunks}
    positions = {chunk.id: i for i, chunk in enumerate(chunks)}
    output: list[Chunk] = []
    proofs: dict[str, ScopeProof] = {}
    for record in [*RECORDS, *DIAGRAMS]:
        anchor = by_id.get(record["anchor_id"])
        body = by_id.get(record["source_id"])
        anchor_text = (
            "\n".join(anchor.source_headings)
            if anchor is not None and record.get("anchor_field") == "headings"
            else anchor.text
            if anchor is not None
            else ""
        )
        if (
            anchor is None
            or body is None
            or anchor.doc_sha256 != record["sha256"]
            or body.doc_sha256 != record["sha256"]
            or body.kind != "text"
            or body.source_picture != record["source_picture"]
            or body.page != record["source_page"]
            or body.section != record["source_section"]
            or record.get("anchor_field", "text") not in {"text", "headings"}
            or _digest(anchor_text) != record["anchor_sha256"]
            or _digest(body.text) != record["source_sha256"]
            or record["anchor_quote"] not in anchor_text
            or (
                (
                    physical_descriptor(record) not in body.source_physical_evidence
                    or model_list_descriptor(record)
                    not in anchor.source_physical_evidence
                )
                if "figure" in record
                else record["excerpt"] not in body.text
            )
        ):
            continue
        for pid, product in source.products.items():
            model = str(product.get("model", ""))
            if not subject_matches(record, model):
                continue
            documents = [
                document
                for document in source.documents.values()
                if document["blob_sha256"] == record["sha256"]
                and pid in document["product_ids"]
                and document_kind_of(
                    str(document["type"]), str(document.get("role", ""))
                )
                == "manual"
            ]
            if not documents:
                continue
            origins = list(dict.fromkeys([anchor.id, body.id]))
            boundaries = restricted_contexts.get(body.id, [])
            reset = record.get("reviewed_reset")
            clearance: dict[str, Any] | None = None
            if reset:
                reset_chunk = by_id.get(reset["id"])
                cleared = reset["cleared"]
                if (
                    reset_chunk is None
                    or reset_chunk.doc_sha256 != body.doc_sha256
                    or reset_chunk.section != reset["section"]
                    or reset["heading"] not in reset_chunk.source_headings
                    or _digest(reset_chunk.text) != reset["text_sha256"]
                    or positions[reset_chunk.id] > positions[body.id]
                ):
                    continue
                remaining = list(boundaries)
                for item in cleared:
                    if item["boundary"] not in remaining:
                        break
                    remaining.remove(item["boundary"])
                else:
                    boundaries = remaining
                if len(remaining) != len(restricted_contexts.get(body.id, [])) - len(
                    cleared
                ):
                    continue
                cleared_texts = []
                for item in cleared:
                    previous = by_id.get(item["boundary"]["source_chunk_id"])
                    if (
                        previous is None
                        or previous.doc_sha256 != body.doc_sha256
                        or positions[previous.id] >= positions[reset_chunk.id]
                        or _digest(previous.text) != item["source_text_sha256"]
                    ):
                        break
                    cleared_texts.append(previous.text)
                else:
                    clearance = {
                        "reset_id": reset_chunk.id,
                        "reset_text": reset_chunk.text,
                        "cleared_texts": cleared_texts,
                    }
                    origins = list(
                        dict.fromkeys(
                            [
                                *origins,
                                reset_chunk.id,
                                *(
                                    item["boundary"]["source_chunk_id"]
                                    for item in cleared
                                ),
                            ]
                        )
                    )
                if clearance is None:
                    continue
            if boundaries:
                # A reported finer boundary must itself exist in the original
                # source, even when it happens to name the requested model.
                valid_boundaries = True
                for boundary in boundaries:
                    prior = by_id.get(str(boundary.get("source_chunk_id", "")))
                    quote = boundary.get("quote")
                    if (
                        prior is None
                        or prior.doc_sha256 != body.doc_sha256
                        or positions[prior.id] > positions[body.id]
                        or not isinstance(quote, str)
                        or not quote
                        or quote
                        not in "\n".join(
                            [prior.section, prior.text, *prior.source_headings]
                        )
                    ):
                        valid_boundaries = False
                        break
                if not valid_boundaries:
                    continue
                origins = list(
                    dict.fromkeys(
                        [*origins, *(str(b["source_chunk_id"]) for b in boundaries)]
                    )
                )
            proof: dict[str, Any] = {
                "product_ids": [pid],
                "basis": "reviewed_manual",
                "source_chunk_ids": origins,
                "document_ids": sorted(d["document_id"] for d in documents),
                "associations": [
                    {
                        "document_id": d["document_id"],
                        "document_revision": d["document_revision"],
                        "blob_sha256": record["sha256"],
                        "product_id": pid,
                        "product_revision": product["product_revision"],
                    }
                    for d in documents
                ],
                "reviewed_manual": {
                    "product_id": pid,
                    "model": model,
                    "source_sha256": record["sha256"],
                    "source_page": body.page,
                    "source_section": body.section,
                    "source_id": body.id,
                    "source_text": body.text,
                    "anchor_id": anchor.id,
                    "anchor_text": anchor_text,
                    **(
                        {"physical_evidence": physical_descriptor(record)}
                        if "figure" in record
                        else {}
                    ),
                    **(
                        {"physical_model_evidence": model_list_descriptor(record)}
                        if "figure" in record
                        else {}
                    ),
                    **({"clearance": clearance} if clearance is not None else {}),
                },
            }
            if boundaries:
                proof["author_restrictions"] = boundaries
                if not author_scope_allows(proof, {pid}, source.products):
                    continue
            text = str(record["excerpt"])
            section = str(record.get("display_section", body.section))
            header = f"{model} | {section} | p. {body.page}"
            tokens = tokenizer.count(header + "\n" + text)
            if tokens > max_tokens:
                continue
            cid = evidence_id(record["sha256"], body.page, model, body.id, text)
            if cid in proofs:
                continue
            output.append(
                replace(
                    body,
                    id=cid,
                    section=section,
                    header=header,
                    text=text,
                    tokens=tokens,
                )
            )
            proofs[cid] = cast(ScopeProof, proof)
    return output, proofs
