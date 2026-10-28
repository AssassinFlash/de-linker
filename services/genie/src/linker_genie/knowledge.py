"""The `linker/search-knowledge` tool: Genie's document search, run in this process.

The index is the SQLite build published to the VPS (`retrieval.default_index`), Genie's
one document source (docs/specs/10-knowledge-index.md, "唯一检索源"); the WordPress copy
and its ability are retired. The tool keeps the ability's name and input so the model
and the code routing that calls it see the same tool as before.

What the model reads differs from what the turn keeps. The model reads each hit's text
with its figures tagged (`figures.tag`) and without the document URL: it cites a figure
as `{fact:CHUNK_ID.nK}` and a passage by its chunk ID, and hydration writes the value
and the "title, page" citation. The full result, URL and figure table included, goes to
`facts.collect`.

A search that cannot run fails loudly: a query the encoder cannot encode raises
`EmbeddingError` (after its retries, `embedding.QUERY_ATTEMPTS`), an index that cannot
be read raises `KnowledgeUnavailable`; both are logged here and surface in the turn's
failures. Which ranking served each search, and which encoder, is logged and recorded
on the turn's tool call.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
from collections.abc import Callable
from typing import Any

from linker_genie.embedding import EmbeddingError
from linker_genie.facts import TurnFacts, collect, knowledge_qualifications
from linker_genie.figures import tag
from linker_genie.publication import (
    PublicationChanged,
    PublicationClient,
    PublicationUnavailable,
    current,
)
from linker_genie.retrieval import LANGS, DocumentIndex, ServingMismatch, default_index

NAME = "linker/search-knowledge"
# The input the model is told about (agent.INPUT_DOCS); `validate` reads the same shape.
INPUT_DOC = "{query: string, lang: 'en'|'de', product_ids?: [int]}"

log = logging.getLogger(__name__)


class KnowledgeUnavailable(RuntimeError):
    """The document index could not be opened or read.

    `failure_kind` is the class the turn records (#410).
    """

    failure_kind = "retrieval"


# The sentence `KnowledgeSearch` raises. `is_index_failure` reads the same
# words, for a probe that kept the message and lost the exception.
INDEX_UNAVAILABLE = "document index unavailable"


def is_index_failure(text: str) -> bool:
    """True when `text` is this module's index sentence."""
    return INDEX_UNAVAILABLE in text


class KnowledgeSearch:
    """Searches the published index; one search at a time on its one connection."""

    def __init__(
        self,
        index: Callable[[], DocumentIndex] = default_index,
        publication: PublicationClient | None = None,
    ) -> None:
        self._index = index
        self._publication = publication
        self._lock = threading.Lock()

    def loaded(self) -> dict[str, Any]:
        with self._lock:
            return self._index().loaded()

    def __call__(self, arguments: dict[str, Any] | None) -> dict[str, Any]:
        """The tool result for `arguments`, or `{"error": …}` for an invalid input."""
        try:
            query, lang, product_ids = validate(arguments or {})
        except ValueError as error:
            return {"error": str(error)}
        with self._lock:
            try:
                index = self._index()
                authority = self._publication or current()
                snapshot = authority.snapshot()
                if "unavailable" in authority.identify_text(query).values():
                    raise PublicationChanged("supplied model is no longer published")
                if product_ids:
                    snapshot.require_products(product_ids)
                hits = index.search(
                    query,
                    lang,
                    product_ids if product_ids else None,
                    publication=snapshot,
                )
                authority.validate(snapshot)
            except PublicationChanged:
                raise
            except PublicationUnavailable as error:
                raise KnowledgeUnavailable(str(error)) from error
            except EmbeddingError as error:
                log.error("document search failed: %s", error)
                raise
            except (sqlite3.Error, OSError, ServingMismatch) as error:
                log.error("document index unavailable: %s", error)
                raise KnowledgeUnavailable(f"{INDEX_UNAVAILABLE}: {error}") from error
        encoder = index.encoder.model if index.encoder is not None else None
        log.info(
            "document search ranking=%s encoder=%s index=%s hits=%d",
            index.ranking,
            encoder,
            index.version,
            len(hits),
        )
        payload_hits = []
        for hit in hits:
            if bool(hit.qualifications) != hit.qualification_required:
                continue
            entry: dict[str, Any] = {
                "chunk_id": hit.chunk_id,
                "document_id": hit.document_id,
                "document_revision": hit.document_revision,
                "product_ids": list(hit.product_ids),
                "doc_url": hit.doc_url,
                "title": hit.title,
                "page": hit.page,
                "section": hit.section,
                "text": hit.text,
                **({"warranty_terms": True} if hit.warranty_terms else {}),
                **({"warranty_procedure": True} if hit.warranty_procedure else {}),
                **(
                    {"product_models": list(hit.product_models)}
                    if hit.warranty_terms or hit.warranty_procedure
                    else {}
                ),
                **({"scope_note": hit.scope_note} if hit.scope_note else {}),
                **(
                    {
                        "qualification_required": True,
                        "qualifications": list(hit.qualifications),
                    }
                    if hit.qualification_required
                    else {}
                ),
            }
            notes = knowledge_qualifications(entry)
            if notes is None or bool(notes) != hit.qualification_required:
                continue
            protected: list[tuple[int, int]] = []
            for note in notes:
                annotation = f"{note.quote} (p. {note.page})"
                start = hit.text.index(annotation)
                # The condition itself can contain the customer's requested
                # date or duration. Only its marker and page label are not facts.
                protected.append((start + len(note.quote), start + len(annotation)))
                marker = note.quote.split(":", 1)[0]
                protected.extend(
                    match.span()
                    for match in re.finditer(re.escape(marker) + r"(?!\d)", hit.text)
                )
                # An original ordered-list marker is not a duration.
                for match in re.finditer(
                    r"(?<!\w)\d{1,2}\.(?=\s+\d+\s+(?:months?|Monate\w*)\b)",
                    note.quote,
                    re.I,
                ):
                    protected.append((start + match.start(), start + match.end()))
            tagged = tag(hit.chunk_id, hit.text, excluded_spans=tuple(protected))
            entry["text"] = tagged.text
            entry["figures"] = tagged.figures
            payload_hits.append(entry)
        return {
            "ranking": index.ranking,
            "encoder": encoder,
            "index_version": index.version,
            "source_revision": index.source_revision,
            "hits": payload_hits,
        }


Search = Callable[[dict[str, Any] | None], dict[str, Any]]


def record(
    search: Search, arguments: dict[str, Any] | None, locale: str = "en"
) -> tuple[dict[str, Any], TurnFacts]:
    """Run a search and collect its facts, the tool call logged with its result.

    The one way a turn runs this tool, whether the route calls it before the model
    (understand.py) or the model calls it (agent.py). The logged result is whole,
    figure table and URLs included: the quality check rebuilds the turn's facts
    from the log (quality.citations).
    """
    payload = _qualified_hits(search(arguments))
    gathered = collect(NAME, payload, locale)
    gathered.tool_calls.append(
        {
            "name": NAME,
            "arguments": arguments or {},
            "ok": "error" not in payload,
            "ranking": payload.get("ranking"),
            "encoder": payload.get("encoder"),
            "index_version": payload.get("index_version"),
            "result": payload,
        }
    )
    return payload, gathered


def _qualified_hits(payload: dict[str, Any]) -> dict[str, Any]:
    """Reject incomplete projections while preserving retrieval order.

    Equal values and footnote markers do not establish that two language
    variants describe the same parameter. An other-language source remains
    usable with an explicitly labelled original quote.
    """
    if not isinstance(payload.get("hits"), list):
        return payload
    hits = [
        hit
        for hit in payload["hits"]
        if isinstance(hit, dict) and knowledge_qualifications(hit) is not None
    ]
    return {**payload, "hits": hits}


def validate(arguments: dict[str, Any]) -> tuple[str, str, list[int]]:
    """(query, lang, product_ids) of a tool input, or ValueError naming the mistake."""
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    lang = arguments.get("lang", "en")
    if lang not in LANGS:
        raise ValueError(f"lang must be one of {LANGS}")
    raw_ids = arguments.get("product_ids") or []
    if not isinstance(raw_ids, list) or not all(
        isinstance(item, int) and not isinstance(item, bool) and item >= 1
        for item in raw_ids
    ):
        raise ValueError("product_ids must be a list of integers >= 1")
    return query.strip(), str(lang), list(dict.fromkeys(raw_ids))


def model_view(payload: dict[str, Any]) -> dict[str, Any]:
    """The result as the model reads it: tagged text, no URL, no figure table."""
    if "hits" not in payload:
        return payload
    return {
        "hits": [
            {
                key: hit[key]
                for key in ("chunk_id", "title", "page", "section", "text")
                if key in hit
            }
            | (
                {
                    "product_ids": hit.get("product_ids", []),
                    "product_models": hit.get("product_models", []),
                    "warranty_terms": True,
                }
                if hit.get("warranty_terms") is True
                else {}
            )
            | (
                {
                    "product_ids": hit.get("product_ids", []),
                    "product_models": hit.get("product_models", []),
                    "warranty_procedure": True,
                    "scope_note": hit.get("scope_note", ""),
                }
                if hit.get("warranty_procedure") is True
                else {}
            )
            for hit in payload["hits"]
            if isinstance(hit, dict)
        ]
    }


# The service's search: one index connection and one lock for every turn, shared by
# the route and the model's tool. The index opens on the first search.
SEARCH = KnowledgeSearch()
