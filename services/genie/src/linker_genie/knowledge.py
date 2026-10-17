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
import sqlite3
import threading
from collections.abc import Callable
from typing import Any

from linker_genie.embedding import EmbeddingError
from linker_genie.facts import TurnFacts, collect
from linker_genie.figures import tag
from linker_genie.retrieval import LANGS, DocumentIndex, default_index

NAME = "linker/search-knowledge"
# The input the model is told about (agent.INPUT_DOCS); `validate` reads the same shape.
INPUT_DOC = "{query: string, lang: 'en'|'de', product_ids?: [int]}"

log = logging.getLogger(__name__)


class KnowledgeUnavailable(RuntimeError):
    """The document index could not be opened or read."""


class KnowledgeSearch:
    """Searches the published index; one search at a time on its one connection."""

    def __init__(self, index: Callable[[], DocumentIndex] = default_index) -> None:
        self._index = index
        self._lock = threading.Lock()

    def __call__(self, arguments: dict[str, Any] | None) -> dict[str, Any]:
        """The tool result for `arguments`, or `{"error": …}` for an invalid input."""
        try:
            query, lang, product_ids = validate(arguments or {})
        except ValueError as error:
            return {"error": str(error)}
        with self._lock:
            try:
                index = self._index()
                hits = index.search(query, lang, product_ids or None)
            except EmbeddingError as error:
                log.error("document search failed: %s", error)
                raise
            except (sqlite3.Error, OSError) as error:
                log.error("document index unavailable: %s", error)
                raise KnowledgeUnavailable(
                    f"document index unavailable: {error}"
                ) from error
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
            tagged = tag(hit.chunk_id, hit.text)
            payload_hits.append(
                {
                    "chunk_id": hit.chunk_id,
                    "doc_url": hit.doc_url,
                    "title": hit.title,
                    "page": hit.page,
                    "section": hit.section,
                    "text": tagged.text,
                    "figures": tagged.figures,
                }
            )
        return {
            "ranking": index.ranking,
            "encoder": encoder,
            "index_version": index.version,
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
    payload = search(arguments)
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
            for hit in payload["hits"]
            if isinstance(hit, dict)
        ]
    }


# The service's search: one index connection and one lock for every turn, shared by
# the route and the model's tool. The index opens on the first search.
SEARCH = KnowledgeSearch()
