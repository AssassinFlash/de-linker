"""A whole passage needs every model's own current document association.

Equal SHA only selects reusable parsed bytes. It never substitutes another
document identity, relation, content revision or product revision for a grant.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


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
    return "| " + " | ".join([heading, *labels]) + " |"
