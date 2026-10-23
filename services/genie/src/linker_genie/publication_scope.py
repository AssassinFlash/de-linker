"""A whole passage needs every model's own current document association.

Equal SHA only selects reusable parsed bytes. It never substitutes another
document identity, relation, content revision or product revision for a grant.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from linker_genie.source_roles import (
    manual_scope_models,
    meter_references,
    pack_model_row,
)


def binding(association: Mapping[str, Any]) -> tuple[str, str, str, int, str]:
    """The source facts which jointly grant one model's passage permission."""
    return (
        str(association["document_id"]),
        str(association["document_revision"]),
        str(association["blob_sha256"]),
        int(association["product_id"]),
        str(association["product_revision"]),
    )


def authorize_chunk(
    sha: str,
    product_ids: Sequence[int],
    associations: Sequence[dict[str, Any]],
    scope: Mapping[str, Any] | None = None,
    *,
    products: Mapping[int, Mapping[str, Any]] | None = None,
    chunk_id: str = "",
    text: str = "",
) -> list[dict[str, Any]]:
    """Authorize the complete model set with its explicit association group.

    Callers supply only links whose loaded and current identities/revisions match.
    A new proof also binds the exact group at build time: losing any recorded
    link rejects the whole chunk, even if another same-SHA URL remains public.
    Earlier proofs remain bounded by their recorded document IDs and every
    loaded/current association; old indexes without those links grant nothing.
    """
    wanted = set(product_ids)
    if not wanted:
        return []
    if scope is not None and (
        scope.get("basis") == "manual_peripheral" or "referenced_products" in scope
    ):
        references = scope.get("referenced_products")
        declaration = scope.get("manual_scope")
        if (
            products is None
            or not isinstance(references, list)
            or not references
            or not isinstance(declaration, dict)
            or set(declaration.get("product_ids", [])) != wanted
            or not all(
                pid in products
                and str(products[pid].get("model", "")).casefold()
                in manual_scope_models(str(declaration.get("quote", "")))
                for pid in wanted
            )
            or not declaration.get("source_chunk_ids")
            or not set(declaration["source_chunk_ids"]).issubset(
                scope["source_chunk_ids"]
            )
        ):
            return []
        authored = {
            (model.casefold(), quote) for model, quote in meter_references(text)
        }
        for ref in references:
            if not isinstance(ref, dict):
                return []
            pid = ref.get("product_id")
            current = products.get(pid) if type(pid) is int else None
            if (
                current is None
                or pid in wanted
                or ref.get("product_revision") != current.get("product_revision")
                or ref.get("model") != current.get("model")
                or ref.get("role") != "meter"
                or not isinstance(ref.get("quote"), str)
                or ref.get("source_chunk_id") != chunk_id
                or chunk_id not in scope["source_chunk_ids"]
                or (str(ref.get("model", "")).casefold(), ref.get("quote"))
                not in authored
            ):
                return []
    document_ids = set(scope["document_ids"]) if scope is not None else None
    available = [
        item
        for item in associations
        if item["blob_sha256"] == sha
        and item["product_id"] in wanted
        and (document_ids is None or item["document_id"] in document_ids)
    ]
    if scope is not None and "associations" in scope:
        required = {binding(item) for item in scope["associations"]}
        if not required or not required.issubset({binding(item) for item in available}):
            return []
        available = [item for item in available if binding(item) in required]
    if {item["product_id"] for item in available} != wanted:
        return []
    return sorted(available, key=binding)


def table_header(
    scope: Mapping[str, Any] | None,
    product_ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    *,
    chunk_id: str = "",
    text: str = "",
) -> str | None:
    """Restore the proven original table columns in order, or refuse invalid proof."""
    if scope is None:
        return ""
    if "table_columns" not in scope:
        return None if scope.get("basis") == "table_columns" else ""
    columns = scope["table_columns"]
    if not isinstance(columns, dict):
        return None
    ids, labels, heading = (
        columns.get("product_ids"),
        columns.get("labels"),
        columns.get("heading"),
    )
    if (
        not isinstance(ids, list)
        or len(ids) < 2
        or not all(type(pid) is int for pid in ids)
        or len(ids) != len(set(ids))
        or set(ids) != set(product_ids)
        or not isinstance(labels, list)
        or len(labels) != len(ids)
        or not isinstance(heading, str)
        or heading.casefold() not in {"technical data", "technische daten"}
        or not columns.get("source_table")
        or not columns.get("header_chunk_ids")
    ):
        return None
    for pid, label in zip(ids, labels, strict=True):
        if (
            pid not in products
            or not isinstance(label, str)
            or "|" in label
            or " ".join(label.split()).casefold()
            != " ".join(str(products[pid].get("model", "")).split()).casefold()
        ):
            return None
    if "excluded_role_rows" in columns:
        rows, excluded = columns.get("source_rows"), columns["excluded_role_rows"]
        if (
            columns.get("source_chunk_id") != chunk_id
            or columns.get("text_sha256") != hashlib.sha256(text.encode()).hexdigest()
            or not isinstance(rows, list)
            or not rows
            or any(type(row) is not int or row < 0 for row in rows)
            or rows != sorted(set(rows))
            or len(rows) != len(text.splitlines())
            or not isinstance(excluded, list)
            or not excluded
        ):
            return None
        for anchor in excluded:
            if (
                not isinstance(anchor, dict)
                or anchor.get("role") != "pack_model"
                or not anchor.get("source_chunk_id")
                or not pack_model_row(str(anchor.get("quote", "")))
                or not isinstance(anchor.get("source_rows"), list)
                or len(anchor["source_rows"]) != 1
                or type(anchor["source_rows"][0]) is not int
                or anchor["source_rows"][0] < 0
                or anchor["source_chunk_id"] == chunk_id
                or anchor["source_rows"][0] in rows
            ):
                return None
    return "| " + " | ".join([heading, *labels]) + " |"
