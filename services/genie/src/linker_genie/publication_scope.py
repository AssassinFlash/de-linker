"""A whole passage needs every model's own current document association.

Equal SHA only selects reusable parsed bytes. It never substitutes another
document identity, relation, content revision or product revision for a grant.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from linker_genie.certificate_scope import (
    certificate_document,
    has_explicit_exclusion,
    valid_certificate_fragment,
    valid_certificate_scope,
)
from linker_genie.family_scope import valid_family_scope
from linker_genie.source_models import model_pattern
from linker_genie.source_roles import (
    manual_scope_models,
    meter_references,
    pack_model_row,
)
from linker_genie.table_projection import external_axis_anchored, valid_projection
from linker_genie.warranty_scope import valid_warranty_scope


def binding(association: Mapping[str, Any]) -> tuple[str, str, str, int, str]:
    """The source facts which jointly grant one model's passage permission."""
    return (
        str(association["document_id"]),
        str(association["document_revision"]),
        str(association["blob_sha256"]),
        int(association["product_id"]),
        str(association["product_revision"]),
    )


def author_scope_allows(
    scope: Mapping[str, Any],
    wanted: set[int],
    products: Mapping[int, Mapping[str, Any]],
) -> bool:
    """A finer authored scope cannot be broadened by a later family fallback."""
    restrictions = scope.get("author_restrictions")
    if not isinstance(restrictions, list) or not restrictions:
        return False
    for boundary in restrictions:
        if (
            not isinstance(boundary, dict)
            or boundary.get("kind") not in {"heading", "declaration"}
            or not isinstance(boundary.get("quote"), str)
            or not boundary["quote"]
            or boundary.get("source_chunk_id") not in scope.get("source_chunk_ids", [])
        ):
            return False
        if has_explicit_exclusion(boundary["quote"]):
            return False
        subjects = {
            pid
            for pid, product in products.items()
            if product.get("model")
            and model_pattern(str(product["model"])).search(boundary["quote"])
        }
        if not wanted.issubset(subjects):
            return False
    return True


def _authorize_core(
    sha: str,
    product_ids: Sequence[int],
    associations: Sequence[dict[str, Any]],
    scope: Mapping[str, Any] | None = None,
    *,
    products: Mapping[int, Mapping[str, Any]] | None = None,
    documents: Mapping[str, Mapping[str, Any]] | None = None,
    chunk_id: str = "",
    text: str = "",
    external_axis_anchors: Mapping[str, Any] | None = None,
    require_table_anchor: bool = False,
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
        scope.get("basis") == "certificate_subject" or "certificate_scope" in scope
    ):
        if (
            products is None
            or documents is None
            or not valid_certificate_scope(
                scope,
                product_ids,
                products,
                documents,
                sha=sha,
                chunk_id=chunk_id,
                text=text,
            )
        ):
            return []
    if scope is not None and (
        scope.get("basis") == "warranty_procedure" or "warranty_scope" in scope
    ):
        if (
            products is None
            or documents is None
            or not valid_warranty_scope(
                scope,
                product_ids,
                products,
                documents,
                sha=sha,
                chunk_id=chunk_id,
                text=text,
            )
        ):
            return []
    if scope is not None and "author_restrictions" in scope:
        if products is None or not author_scope_allows(scope, wanted, products):
            return []
    if scope is not None and (
        scope.get("basis") == "family_manual" or "family_scope" in scope
    ):
        if products is None or not valid_family_scope(
            scope,
            product_ids,
            products,
            sha=sha,
            chunk_id=chunk_id,
            text=text,
        ):
            return []
    if scope is not None and (
        scope.get("basis") == "table_projection" or "table_projection" in scope
    ):
        if (
            products is None
            or not valid_projection(
                scope,
                product_ids,
                products,
                sha=sha,
                chunk_id=chunk_id,
                text=text,
            )
            or not external_axis_anchored(
                scope, external_axis_anchors, required=require_table_anchor
            )
        ):
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


def authorize_chunk(
    sha: str,
    product_ids: Sequence[int],
    associations: Sequence[dict[str, Any]],
    scope: Mapping[str, Any] | None = None,
    *,
    products: Mapping[int, Mapping[str, Any]] | None = None,
    documents: Mapping[str, Mapping[str, Any]] | None = None,
    chunk_id: str = "",
    text: str = "",
    external_axis_anchors: Mapping[str, Any] | None = None,
    require_table_anchor: bool = False,
) -> list[dict[str, Any]]:
    """Only verified subject or safe projections may use a certificate grant."""
    if documents is None:
        return []
    args: dict[str, Any] = {
        "products": products,
        "documents": documents,
        "external_axis_anchors": external_axis_anchors,
        "require_table_anchor": require_table_anchor,
    }
    basis = scope.get("basis") if scope is not None else None
    if basis == "certificate_fragment":
        if (
            products is None
            or scope is None
            or not valid_certificate_fragment(
                scope,
                product_ids,
                products,
                documents,
                sha=sha,
                chunk_id=chunk_id,
                text=text,
            )
        ):
            return []
        fragment = scope["certificate_fragment"]
        origin = fragment["origin_scope"]
        original = _authorize_core(
            sha,
            origin["product_ids"],
            associations,
            origin,
            chunk_id=fragment["source_chunk_id"],
            text=fragment["source_text"],
            **args,
        )
        if not any(
            item["document_id"] == fragment["document_id"]
            and item["product_id"] == fragment["product_id"]
            for item in original
        ):
            return []
        return _authorize_core(
            sha, product_ids, associations, scope, chunk_id=chunk_id, text=text, **args
        )
    available = _authorize_core(
        sha, product_ids, associations, scope, chunk_id=chunk_id, text=text, **args
    )
    if basis == "certificate_subject":
        return available
    # The complete original group is checked before choosing a non-certificate
    # relation. A certificate relation never carries raw technical source text.
    non_certificates = [
        item
        for item in available
        if item["document_id"] in documents
        and not certificate_document(documents[item["document_id"]])
    ]
    return (
        non_certificates
        if {item["product_id"] for item in non_certificates} == set(product_ids)
        else []
    )


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
    if scope.get("basis") == "table_projection" or "table_projection" in scope:
        projection = scope.get("table_projection")
        if not isinstance(projection, dict) or not valid_projection(
            scope,
            product_ids,
            products,
            sha=str(projection.get("source_sha256", "")),
            chunk_id=chunk_id,
            text=text,
        ):
            return None
        # The compiled answer unit already contains its exact source-model axis.
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
