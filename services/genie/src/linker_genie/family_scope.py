"""The shared build/runtime rule for literal family-manual instructions."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from linker_genie.source_models import (
    family_labels,
    family_mentions,
    model_pattern,
    model_shapes,
    unknown_models,
)


def family_id(sha: str, page: int, model: str, original: str, text: str) -> str:
    digest = hashlib.sha256(f"{model}\0{original}\0{text}".encode()).hexdigest()[:16]
    return f"{sha[:12]}-p{page}-family-{digest}"


def valid_family_scope(
    scope: Mapping[str, Any],
    product_ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    *,
    sha: str,
    chunk_id: str,
    text: str,
) -> bool:
    value = scope.get("family_scope")
    if not isinstance(value, dict) or scope.get("basis") != "family_manual":
        return False
    pid = value.get("product_id")
    labels = {str(p.get("model", "")).casefold() for p in products.values()}
    families = family_labels(labels)
    if (
        type(pid) is not int
        or list(product_ids) != [pid]
        or scope.get("product_ids") != [pid]
        or pid not in products
        or value.get("source_sha256") != sha
        or not isinstance(value.get("family"), str)
        or value["family"] not in families
        or not isinstance(value.get("quote"), str)
        or value["family"] not in family_mentions(value["quote"], families)
        or not isinstance(value.get("model"), str)
        or value["model"] != products[pid].get("model")
        or not value["model"].casefold().startswith(value["family"] + "-")
        or not isinstance(value.get("source_chunk_id"), str)
        or not value["source_chunk_id"]
        or value["source_chunk_id"] not in scope.get("source_chunk_ids", [])
        or not isinstance(value.get("anchor_chunk_id"), str)
        or value["anchor_chunk_id"] not in scope.get("source_chunk_ids", [])
        or type(value.get("source_page")) is not int
        or value["source_page"] <= 0
        or value.get("text_sha256") != hashlib.sha256(text.encode()).hexdigest()
    ):
        return False
    own = value["model"].casefold()
    if any(label != own and model_pattern(label).search(text) for label in labels):
        return False
    if unknown_models(
        value["quote"] + "\n" + text,
        {own},
        model_shapes(labels),
        section=True,
        families=families,
    ):
        return False
    return chunk_id == family_id(
        sha, value["source_page"], value["model"], value["source_chunk_id"], text
    )
