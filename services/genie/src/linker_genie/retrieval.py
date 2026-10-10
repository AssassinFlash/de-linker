"""Document search: `search_documents` over the index that `services/genie/index` builds.

Document search over the built index (docs/specs/10-knowledge-index.md, Retrieval):
when product IDs are given, the search first narrows to the documents tagged with
those products' models (the whole library when none are tagged, or when the narrowed
search finds nothing). The vector ranking (sqlite-vec KNN over the query encoded by
the index's model) stands alone: the embedding bake-off measured that fusing it with
BM25 loses 11.6 points of recall@5 (docs/research/2026-10-09/embedding-bakeoff.md).
Without a query encoder for the index's model on this host (no API key for a
gemini-embedding-2 index; no ONNX model files, as on the VPS) BM25 over FTS5 is the
ranking.

A hit is a chunk: its ID is what an answer cites, and `link` is the document URL with
the page fragment the citation opens.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import sqlite_vec

from linker_genie.embedding import Embedder, query_encoder

# The release layout of ops/publish_index.py: /opt/linker-genie/index/<version>/ and a
# `current` link. GENIE_INDEX points elsewhere (a local build, a test fixture).
DEFAULT_INDEX = Path("/opt/linker-genie/index/current/index.sqlite")
# The index layout this module reads; index/store.py writes the same number.
SCHEMA_VERSION = 1
# Spec (Retrieval): FTS5 and the vectors each contribute their top 30.
CANDIDATES = 30
# Reciprocal rank fusion constant. 60 is the value of the method's paper (Cormack,
# Clarke and Büttcher, SIGIR 2009); LanceDB's RRF docs: "k = 60 was near-optimal, but
# ... the choice is not critical" (docs/research/2026-10-09/knowledge-audit.md B3).
RRF_K = 60
# Spec signature: search_documents(..., k=8).
DEFAULT_K = 8
LANGS = ("en", "de")

# A query term: letters or digits, with the dots, hyphens and slashes inside model
# codes and numbers (GW10K-ET, 29.9K, 5.0-10, L1/L2) kept in the same term.
_TERM = re.compile(r"\w(?:[\w./-]*\w)?")


@dataclass(frozen=True)
class DocumentHit:
    """One retrieved chunk and the document page it comes from."""

    chunk_id: str
    doc_sha256: str
    doc_url: str
    title: str
    doc_type: str
    page: int
    section: str
    text: str
    lang: str
    score: float

    @property
    def link(self) -> str:
        """The document URL opened at the chunk's page."""
        return f"{self.doc_url}#page={self.page}"


def fts_query(query: str) -> str:
    """An FTS5 query that matches any term of `query`, each term as a quoted phrase.

    Quoting keeps a model code together: FTS5 tokenizes "GW10K-ET" into the phrase
    `gw10k et`, which only matches the two tokens in that order.
    """
    terms = dict.fromkeys(term.lower() for term in _TERM.findall(query))
    return " OR ".join(f'"{term}"' for term in terms)


def rrf(rankings: Sequence[Sequence[int]], k: int = RRF_K) -> list[tuple[int, float]]:
    """Reciprocal rank fusion of ranked ID lists: (id, score), best first."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))


class _Auto:
    """Marker: pick the query encoder from the index's recorded model."""


AUTO = _Auto()


class DocumentIndex:
    """A read-only connection to one built index."""

    def __init__(self, path: Path, encoder: Embedder | None | _Auto = AUTO) -> None:
        self.path = path
        self._db = sqlite3.connect(
            f"file:{path}?mode=ro", uri=True, check_same_thread=False
        )
        self._db.enable_load_extension(True)
        sqlite_vec.load(self._db)
        self._db.enable_load_extension(False)
        meta = dict(self._db.execute("SELECT key, value FROM meta").fetchall())
        if int(meta.get("schema_version", "0")) != SCHEMA_VERSION:
            raise RuntimeError(
                f"{path}: schema {meta.get('schema_version')}, this code reads {SCHEMA_VERSION}"
            )
        self.version = str(meta.get("version", ""))
        self.embedding_model = str(meta.get("embedding_model", ""))
        self.encoder: Embedder | None
        if int(meta.get("dimensions", "0")) == 0:
            # A keywords-only index has no vector table to search.
            self.encoder = None
        elif isinstance(encoder, _Auto):
            self.encoder = query_encoder(self.embedding_model)
        else:
            self.encoder = encoder
        recorded = json.loads(meta.get("embedding_fingerprint", "{}"))
        if (
            self.encoder is not None
            and recorded
            and self.encoder.fingerprint != recorded
        ):
            # Vectors of a different model, file, tokenizer or input format would rank
            # nonsense; the index states what built it and nothing else may query it.
            raise RuntimeError(
                f"{path}: query encoder {self.encoder.fingerprint} differs from the "
                f"encoder that built the index {recorded}"
            )

    def close(self) -> None:
        self._db.close()

    def scope(
        self, product_ids: Sequence[int] | None, doc_types: Sequence[str] | None
    ) -> list[int] | None:
        """Chunk rowids allowed by the filters, or None for the whole index."""
        conditions: list[str] = []
        params: list[str] = []
        if product_ids:
            shas = [
                row[0]
                for row in self._db.execute(
                    "SELECT DISTINCT dm.doc_sha256 FROM document_models dm"
                    " JOIN products p ON p.model = dm.model"
                    " WHERE p.product_id IN (SELECT value FROM json_each(?))",
                    (json.dumps(list(product_ids)),),
                )
            ]
            if shas:
                conditions.append("c.doc_sha256 IN (SELECT value FROM json_each(?))")
                params.append(json.dumps(shas))
        if doc_types:
            conditions.append("d.doc_type IN (SELECT value FROM json_each(?))")
            params.append(json.dumps(list(doc_types)))
        if not conditions:
            return None
        sql = (
            "SELECT c.rowid FROM chunks c JOIN documents d ON d.sha256 = c.doc_sha256 WHERE "
            + " AND ".join(conditions)
        )
        return [row[0] for row in self._db.execute(sql, params)]

    def keyword_ranking(self, query: str, scope: list[int] | None) -> list[int]:
        """The best CANDIDATES chunk rowids by BM25 over header and text."""
        match = fts_query(query)
        if not match:
            return []
        sql = "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ?"
        params: list[str | int] = [match]
        if scope is not None:
            sql += " AND rowid IN (SELECT value FROM json_each(?))"
            params.append(json.dumps(scope))
        sql += " ORDER BY bm25(chunks_fts) LIMIT ?"
        params.append(CANDIDATES)
        return [row[0] for row in self._db.execute(sql, params)]

    def vector_ranking(
        self, query: str, scope: list[int] | None, vector: bytes | None = None
    ) -> list[int]:
        """The best CANDIDATES chunk rowids by cosine distance to the query's vector.

        `vector` is the query already encoded; without it the index's encoder encodes
        the query, and an index without an encoder ranks nothing.
        """
        if vector is None:
            if self.encoder is None:
                return []
            vector = self.encoder.embed_query(query)
        sql = "SELECT rowid FROM chunks_vec WHERE embedding MATCH ? AND k = ?"
        params: list[bytes | str | int] = [vector, CANDIDATES]
        if scope is not None:
            sql += " AND rowid IN (SELECT value FROM json_each(?))"
            params.append(json.dumps(scope))
        sql += " ORDER BY distance"
        return [row[0] for row in self._db.execute(sql, params)]

    def hits(self, scored: Sequence[tuple[int, float]], lang: str) -> list[DocumentHit]:
        """The chunks of (rowid, score) pairs, in that order."""
        if not scored:
            return []
        rows = {
            row[0]: row[1:]
            for row in self._db.execute(
                "SELECT c.rowid, c.id, c.doc_sha256, d.url, d.title_en, d.title_de, d.doc_type,"
                " c.page, c.section, c.text, c.lang"
                " FROM chunks c JOIN documents d ON d.sha256 = c.doc_sha256"
                " WHERE c.rowid IN (SELECT value FROM json_each(?))",
                (json.dumps([rowid for rowid, _ in scored]),),
            )
        }
        hits = []
        for rowid, score in scored:
            (
                chunk_id,
                sha,
                url,
                title_en,
                title_de,
                doc_type,
                page,
                section,
                text,
                chunk_lang,
            ) = rows[rowid]
            hits.append(
                DocumentHit(
                    chunk_id=chunk_id,
                    doc_sha256=sha,
                    doc_url=url,
                    title=title_de if lang == "de" and title_de else title_en,
                    doc_type=doc_type,
                    page=page,
                    section=section,
                    text=text,
                    lang=chunk_lang,
                    score=score,
                )
            )
        return hits

    def search(
        self,
        query: str,
        lang: str,
        product_ids: Sequence[int] | None = None,
        doc_types: Sequence[str] | None = None,
        k: int = DEFAULT_K,
    ) -> list[DocumentHit]:
        """The k best chunks for `query`; `lang` (en|de) picks the title language.

        The vector ranking stands alone when a query encoder is available: fusing it
        with BM25 by reciprocal rank fusion cost the bake-off's best model 11.6 points
        of recall@5 and 2.9 points of citation page accuracy (docs/research/
        2026-10-09/embedding-bakeoff.md), because pages of other models' parameter
        tables match the query's words just as well. BM25 is what remains when this
        host has no encoder for the index's model, exactly the fallback the spec names.
        """
        if lang not in LANGS:
            raise ValueError(f"lang must be one of {LANGS}, not {lang!r}")
        # First the products' documents, then - only when they hold nothing for the
        # query - the whole library (spec, Retrieval).
        scopes = (product_ids, None) if product_ids else (None,)
        for scoped_ids in scopes:
            scope = self.scope(scoped_ids, doc_types)
            ranked = self.vector_ranking(query, scope)
            if not ranked:
                ranked = self.keyword_ranking(query, scope)
            if ranked:
                return self.hits(
                    [(rowid, float(-position)) for position, rowid in enumerate(ranked)][
                        :k
                    ],
                    lang,
                )
        return []

    def chunks(self, chunk_ids: Sequence[str], lang: str) -> list[DocumentHit]:
        """The chunks with these IDs, in the order given; unknown IDs are left out."""
        rowids = dict(
            self._db.execute(
                "SELECT id, rowid FROM chunks WHERE id IN (SELECT value FROM json_each(?))",
                (json.dumps(list(chunk_ids)),),
            ).fetchall()
        )
        return self.hits([(rowids[i], 0.0) for i in chunk_ids if i in rowids], lang)


_DEFAULT: DocumentIndex | None = None


def default_index() -> DocumentIndex:
    """The published index (GENIE_INDEX, else the `current` release), opened once."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = DocumentIndex(
            Path(os.environ.get("GENIE_INDEX", str(DEFAULT_INDEX)))
        )
    return _DEFAULT


def search_documents(
    query: str,
    lang: str,
    product_ids: Sequence[int] | None = None,
    doc_types: Sequence[str] | None = None,
    k: int = DEFAULT_K,
) -> list[DocumentHit]:
    """Search the published index; see `DocumentIndex.search`."""
    return default_index().search(query, lang, product_ids, doc_types, k)
