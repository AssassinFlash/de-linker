"""The baseline reads successful ability results from the same logged turn."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from linker_genie.facts import collect, merge
from linker_genie.hydrate import hydrate
from linker_genie.route import Route
from linker_genie.schema import CardsBlock, DocumentBlock, Locale, TextBlock
from linker_genie.template import prepared_answer


def pairing_prose(
    calls: Sequence[dict[str, Any]], blocks: Sequence[dict[str, Any]], lang: Locale
) -> str | None:
    """The complete native condition text, if its cards and PDF evidence shipped."""
    searches = [
        c
        for c in calls
        if c.get("ok") is True
        and c.get("name") == "linker/search-products"
        and (c.get("arguments") or {}).get("with_pairings")
    ]
    if not searches:
        return None
    facts = merge([collect(c["name"], c["result"], lang) for c in searches])
    facts.tool_calls = searches
    answer = prepared_answer(facts, Route("pairing", catalog_only=True), lang)
    if answer is None:
        return None
    text = next((b.text for b in answer.blocks if isinstance(b, TextBlock)), "")
    # A catalogue fallback or model-authored prose never licenses a figure.
    if not text or any(
        not (word.startswith("{fact:compat.condition.") and word.endswith("}"))
        for word in text.split()
    ):
        return None
    native = hydrate(answer, facts, lang)
    cards = {
        pid for b in native.blocks if isinstance(b, CardsBlock) for pid in b.product_ids
    }
    shown = {
        pid
        for b in blocks
        if b.get("type") == "cards"
        for pid in b.get("product_ids", [])
    }
    documents = [b for b in native.blocks if isinstance(b, DocumentBlock)]
    received = {
        (
            b.get("ref"),
            b.get("url"),
            b.get("document_id"),
            b.get("document_revision"),
            b.get("evidence_product_id"),
        )
        for b in blocks
        if b.get("type") == "document"
    }
    if cards != shown or not documents:
        return None
    for document in documents:
        source = facts.documents[document.ref].evidence
        if (
            source is None
            or (
                document.ref,
                document.url,
                source.document_id,
                source.document_revision,
                source.product_id,
            )
            not in received
        ):
            return None
    return next(b.text for b in native.blocks if isinstance(b, TextBlock))
