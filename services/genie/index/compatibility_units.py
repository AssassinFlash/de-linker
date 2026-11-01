"""Compile source-bound model/series and physically recovered IoT relations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, cast

from index.chunking import Chunk, Tokenizer
from index.inventory import document_kind_of
from index.publication import ScopeProof
from linker_genie.compatibility_physical import (
    _axis_contains,
    inverter_text,
    iot_text,
    source_id,
)
from linker_genie.publication import Snapshot
from linker_genie.table_projection import overview_row, read_cells


def _links(
    source: Snapshot, sha: str, ids: list[int]
) -> tuple[list[str], list[dict[str, Any]]]:
    documents = [
        doc
        for doc in source.documents.values()
        if doc["blob_sha256"] == sha
        and document_kind_of(str(doc["type"]), str(doc.get("role", "")))
        == "compatibility"
        and all(
            pid in doc["product_ids"]
            and doc["document_id"] in source.products[pid].get("documents", [])
            for pid in ids
        )
    ]
    if not documents:
        return [], []
    document = min(documents, key=lambda item: item["document_id"])
    did = document["document_id"]
    return [did], [
        {
            "document_id": did,
            "document_revision": document["document_revision"],
            "blob_sha256": sha,
            "product_id": pid,
            "product_revision": source.products[pid]["product_revision"],
        }
        for pid in ids
    ]


def compile_physical_compatibility(
    original: list[Chunk],
    overviews: list[Chunk],
    overview_scopes: Mapping[str, ScopeProof],
    source: Snapshot,
    statuses: Mapping[str, str],
    tokenizer: Tokenizer,
    max_tokens: int,
    anchors: Mapping[str, Any],
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    output: list[Chunk] = []
    scopes: dict[str, ScopeProof] = {}
    product_by_model = {
        str(product.get("model", "")): pid for pid, product in source.products.items()
    }
    axes = [
        a
        for a in anchors.values()
        if isinstance(a, dict) and a.get("kind") == "series_axis"
    ]
    for base in overviews:
        base_scope = overview_scopes[base.id]
        part = base_scope.get("compatibility_series")
        if not isinstance(part, dict):
            continue
        cells = read_cells(part.get("source_cells"))
        row, column, lang = (
            part.get("source_row"),
            part.get("source_column"),
            part.get("lang"),
        )
        native = (
            overview_row(cells, row, column, lang)
            if cells is not None
            and type(row) is int
            and type(column) is int
            and isinstance(lang, str)
            else None
        )
        if native is None:
            continue
        _, series = native
        battery = part["product_id"]
        for axis in axes:
            axis_sha = str(axis["source_sha256"])
            for item in axis.get("models", []):
                if not isinstance(item, dict) or not isinstance(item.get("text"), str):
                    continue
                model = item["text"]
                inverter = product_by_model.get(model)
                if (
                    inverter is None
                    or inverter == battery
                    or statuses.get(model.casefold()) != "published"
                    or not _axis_contains(axis, model, series)
                ):
                    continue
                sheets = [
                    doc
                    for doc in source.documents.values()
                    if doc["blob_sha256"] == axis_sha
                    and inverter in doc["product_ids"]
                    and doc["document_id"]
                    in source.products[inverter].get("documents", [])
                    and document_kind_of(str(doc["type"]), str(doc.get("role", "")))
                    == "datasheet"
                ]
                ids = sorted([battery, inverter])
                document_ids, associations = _links(source, base.doc_sha256, ids)
                if len(sheets) != 1 or not associations:
                    continue
                sheet = sheets[0]
                rendered = inverter_text(model, series, base.text, str(part["lang"]))
                if not rendered:
                    continue
                cid = source_id(base.doc_sha256, base.page, "inverter-series", rendered)
                header = f"{model} | p. {base.page}"
                tokens = tokenizer.count(header + "\n" + rendered)
                if tokens > max_tokens or cid in scopes:
                    continue
                source_ids = list(
                    dict.fromkeys(
                        [*base_scope["source_chunk_ids"], axis["target_chunk_id"]]
                    )
                )
                proof = {
                    "product_ids": ids,
                    "basis": "compatibility_inverter",
                    "source_chunk_ids": source_ids,
                    "document_ids": document_ids,
                    "associations": associations,
                    "compatibility_inverter": {
                        "inverter_id": inverter,
                        "battery_id": battery,
                        "model": model,
                        "series": series,
                        "lang": part["lang"],
                        "source_sha256": base.doc_sha256,
                        "source_page": base.page,
                        "base_chunk_id": base.id,
                        "base_text": base.text,
                        "base_scope": base_scope,
                        "axis_chunk_id": axis["target_chunk_id"],
                        "support_document": {
                            "document_id": sheet["document_id"],
                            "document_revision": sheet["document_revision"],
                            "source_sha256": axis_sha,
                            "product_revision": source.products[inverter][
                                "product_revision"
                            ],
                        },
                    },
                }
                scopes[cid] = cast(ScopeProof, proof)
                output.append(
                    replace(base, id=cid, header=header, text=rendered, tokens=tokens)
                )

    iot = [
        a
        for a in anchors.values()
        if isinstance(a, dict) and a.get("kind") == "iot_matrix"
    ]
    first = [a for a in iot if a.get("source_page") == 7]
    second = [a for a in iot if a.get("source_page") == 9]
    names = ("GM330", "SEC3000C", "GW125/261-ESA-LCN-G10")
    if (
        len(first) != 1
        or len(second) != 1
        or any(name not in product_by_model for name in names)
    ):
        return output, scopes
    a, b = first[0], second[0]
    sha = str(a["source_sha256"])
    if b.get("source_sha256") != sha or any(
        statuses.get(name.casefold()) != "published" for name in names
    ):
        return output, scopes
    ids = sorted(product_by_model[name] for name in names)
    document_ids, associations = _links(source, sha, ids)
    target = next(
        (chunk for chunk in original if chunk.id == a["target_chunk_id"]), None
    )
    if not associations or target is None:
        return output, scopes
    text = iot_text(str(a["row_text"]), str(b["row_text"]))
    if not text:
        return output, scopes
    cid = source_id(sha, 7, "iot", text)
    header = "GW125/261-ESA-LCN-G10 | GM330 | SEC3000C | pp. 7, 9"
    tokens = tokenizer.count(header + "\n" + text)
    if tokens > max_tokens:
        return output, scopes
    proof = {
        "product_ids": ids,
        "basis": "compatibility_iot",
        "source_chunk_ids": [a["target_chunk_id"], b["target_chunk_id"]],
        "document_ids": document_ids,
        "associations": associations,
        "compatibility_iot": {
            "subjects": [
                {"product_id": product_by_model[name], "model": name} for name in names
            ],
            "first_chunk_id": a["target_chunk_id"],
            "second_chunk_id": b["target_chunk_id"],
        },
    }
    scopes[cid] = cast(ScopeProof, proof)
    output.append(
        replace(
            target,
            id=cid,
            kind="text",
            header=header,
            text=text,
            tokens=tokens,
            source_table="",
            source_rows=(),
            source_cells=(),
            source_headings=(),
            preceding_text=(),
            source_physical_evidence=(),
        )
    )
    return output, scopes
