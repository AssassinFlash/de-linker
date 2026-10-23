"""Document search: `search_documents` over the index that `services/genie/index` builds.

Document search over the built index (docs/specs/10-knowledge-index.md, Retrieval):
when product IDs are given, the search first narrows to the documents tagged with
those products' models (the whole library when none are tagged, or when the narrowed
search finds nothing). The vector ranking (sqlite-vec KNN over the query encoded by
the index's model) stands alone: the embedding bake-off measured that fusing it with
BM25 loses 11.6 points of recall@5 (docs/research/2026-10-09/embedding-bakeoff.md).
Without a query encoder for the index's model on this host (no API key for a
gemini-embedding-2 index; no ONNX model files, as on the VPS) BM25 over FTS5 is the
ranking, and every such search says so in the log (AGENTS.md §4). With an encoder a
failed encoding raises `EmbeddingError`: it never falls back to BM25 (the model
routing law: OpenRouter failures are loud).

This index is Genie's one document source (docs/specs/10-knowledge-index.md, "唯一检索源").

A hit is a chunk: its ID is what an answer cites, and `link` is the document URL with
the page fragment the citation opens.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from linker_genie.publication import Snapshot

import sqlite_vec

from linker_genie.embedding import Embedder, query_encoder

# The release layout of ops/publish_index.py: /opt/linker-genie/index/<version>/ and a
# `current` link. GENIE_INDEX points elsewhere (a local build, a test fixture).
DEFAULT_INDEX = Path("/opt/linker-genie/index/current/index.sqlite")
# The index layout this module reads; index/store.py writes the same number.
SCHEMA_VERSION = 2
# How deep each ranking reads: the vector ranking's KNN window, and BM25's when it
# stands in for it. The spec's top-30 survived the bake-off's fusion experiments:
# fusing the two at this depth still lost to the vector ranking alone
# (docs/research/2026-10-09/embedding-bakeoff.md §2).
CANDIDATES = 30
# Reciprocal rank fusion constant. 60 is the value of the method's paper (Cormack,
# Clarke and Büttcher, SIGIR 2009); LanceDB's RRF docs: "k = 60 was near-optimal, but
# ... the choice is not critical" (docs/research/2026-10-09/knowledge-audit.md B3).
RRF_K = 60
# Spec signature: search_documents(..., k=8).
DEFAULT_K = 8
LANGS = ("en", "de")
# A prose chunk with fewer than three words is a parsing scrap, not a passage: icon
# labels read as text ("SAND", "SAFI", "GOODWE"), lone step numbers ("3."), drawing
# callouts. 2,266 of the 33,172 chunks of index 20261016T072222Z are such scraps and
# they took up to four of the eight hits of the trial questions (issue #257); a table
# chunk stays whatever its word count, a compatibility matrix of "●" marks is data.
MIN_WORDS = 3
_WORD = re.compile(r"[^\W\d_]{2,}")
# A page's other passages come with its hits, up to this many hits in all. A table
# is chunked by rows with the header repeated, so one page can hold the answer in a
# chunk ranked below the cut: the GoodWe warranty table's 2026 row ranked 12th for
# the German trial question while two rows of the same page ranked in the top 8
# (issue #257). Twice the spec's k keeps a turn's document text near 8k tokens
# (chunks are at most 512 tokens, docs/specs/10-knowledge-index.md).
MAX_HITS = 2 * DEFAULT_K
# A short datasheet comes whole: its first page is the overview and the parameter
# table follows (the L260-OMNI datasheet's p. 1 ranked 2nd for the trial question,
# its p. 2 "Nominal Capacity (kWh) | 260 / Depth of Discharge | 98%" below the top 30
# once the 44-page Pylontech portfolio shared the scope, issue #257). 79 of the 88
# datasheets of index 20261016T072222Z have at most four pages.
SHORT_DATASHEET_PAGES = 4
# A model code in a question: letters and digits in one token (L260, H2-10K-T3,
# CB2-100.3-HV5), the way document_models writes the models a document covers.
_CODE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.\-/]*[A-Za-z0-9])?")

log = logging.getLogger(__name__)

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
    document_id: str = ""
    document_revision: str = ""
    product_ids: tuple[int, ...] = ()

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


def is_passage(text: str) -> bool:
    """Whether a chunk is worth a hit: a table, or prose of at least MIN_WORDS words."""
    return "|" in text or len(_WORD.findall(text)) >= MIN_WORDS


def rrf(rankings: Sequence[Sequence[int]], k: int = RRF_K) -> list[tuple[int, float]]:
    """Reciprocal rank fusion of ranked ID lists: (id, score), best first."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))


class Permit(TypedDict):
    document_id: str
    document_revision: str
    url: str
    product_ids: list[int]


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
        if int(meta.get("schema_version", "0")) not in (1, SCHEMA_VERSION):
            raise RuntimeError(
                f"{path}: schema {meta.get('schema_version')}, this code reads {SCHEMA_VERSION}"
            )
        self.version = str(meta.get("version", ""))
        self.source_revision = str(meta.get("source_revision", ""))
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

    def loaded(self) -> dict[str, Any]:
        tables = {
            r[0]
            for r in self._db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        ready = (
            [
                {"product_id": pid, "product_revision": revision}
                for pid, revision in self._db.execute(
                    "SELECT product_id, product_revision FROM publication_ready_products ORDER BY product_id"
                )
            ]
            if "publication_ready_products" in tables
            else []
        )
        return {
            "index_version": self.version,
            "source_revision": self.source_revision,
            "products": ready,
        }

    def close(self) -> None:
        self._db.close()

    def documents_naming(self, query: str) -> list[str]:
        """The documents tagged with a model the query names by its code.

        A code token of the query (letters and digits together, two characters or
        more) names a model when, written without punctuation and in lower case, it
        is that model or its beginning, or the beginning of a word of it: "L260"
        names L260-OMNI, "H2" the H2 series, "CB2-100.3-HV5" itself, "F12.8-H" the
        LX F12.8-H. Words without digits name nothing.
        """
        codes = {
            re.sub(r"[^a-z0-9]", "", token.lower())
            for token in _CODE.findall(query)
            if re.search(r"[A-Za-z]", token) and re.search(r"\d", token)
        }
        codes.discard("")
        if not codes:
            return []
        shas: list[str] = []
        for sha, model in self._db.execute(
            "SELECT doc_sha256, model FROM document_models ORDER BY doc_sha256"
        ):
            forms = [str(model), *str(model).split()]
            written = [re.sub(r"[^a-z0-9]", "", form.lower()) for form in forms]
            if sha not in shas and any(
                form.startswith(code) for form in written for code in codes
            ):
                shas.append(sha)
        return shas

    def scope(
        self,
        product_ids: Sequence[int] | None,
        doc_types: Sequence[str] | None,
        doc_shas: Sequence[str] | None = None,
    ) -> list[int] | None:
        """Chunk rowids allowed by the filters, or None for the whole index."""
        conditions: list[str] = []
        params: list[str] = []
        if doc_shas is not None:
            conditions.append("c.doc_sha256 IN (SELECT value FROM json_each(?))")
            params.append(json.dumps(list(doc_shas)))
        if product_ids is not None:
            shas = [
                row[0]
                for row in self._db.execute(
                    "SELECT DISTINCT dm.doc_sha256 FROM document_models dm"
                    " JOIN products p ON p.model = dm.model"
                    " WHERE p.product_id IN (SELECT value FROM json_each(?))",
                    (json.dumps(list(product_ids)),),
                )
            ]
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

    @property
    def ranking(self) -> str:
        """`vector` when this host encodes queries for the index's model, else `keywords`."""
        return "vector" if self.encoder is not None else "keywords"

    def search(
        self,
        query: str,
        lang: str,
        product_ids: Sequence[int] | None = None,
        doc_types: Sequence[str] | None = None,
        k: int = DEFAULT_K,
        query_vector: bytes | None = None,
        neighbours: bool = True,
        publication: Snapshot | None = None,
    ) -> list[DocumentHit]:
        """The k best chunks for `query`; `lang` (en|de) picks the title language.

        The vector ranking stands alone when a query encoder is available: fusing it
        with BM25 by reciprocal rank fusion cost the bake-off's best model 11.6 points
        of recall@5 and 3.2 points of citation page accuracy (docs/research/
        2026-10-09/embedding-bakeoff.md), because pages of other models' parameter
        tables match the query's words just as well. BM25 is what remains when this
        host has no encoder for the index's model, exactly the fallback the spec names,
        and the log states it on every search. An encoder that fails raises
        `EmbeddingError` out of this method; nothing here retries it by keywords.
        `query_vector` is `query` already encoded by the index's model (`index.eval`
        encodes the golden set in batched requests instead of one request per
        question). Parsing scraps (`is_passage`) are left out of the hits. With
        `neighbours` the k hits come with their neighbours (`with_page_neighbours`);
        without, the result is the ranking alone, which the golden set scores.
        """
        if lang not in LANGS:
            raise ValueError(f"lang must be one of {LANGS}, not {lang!r}")
        permits = (
            self.permissions(publication, product_ids)
            if publication is not None
            else None
        )
        if permits == {} or product_ids == []:
            return []
        dense = query_vector is not None or self.encoder is not None
        if not dense:
            log.warning(
                "document search by BM25: no query encoder for %s on this host "
                "(index %s)",
                self.embedding_model or "a keywords-only index",
                self.version,
            )
        # First the products' documents - or, without products, the documents of the
        # models the question names - then, only when they hold nothing for the
        # query, the whole library (spec, Retrieval).
        named = [] if product_ids else self.documents_naming(query)
        scopes: list[tuple[Sequence[int] | None, Sequence[str] | None]] = [(None, None)]
        if product_ids:
            scopes.insert(0, (product_ids, None))
        elif named:
            scopes.insert(0, (None, named))
        for scoped_ids, scoped_shas in scopes:
            scope = self.scope(scoped_ids, doc_types, scoped_shas)
            if permits is not None:
                allowed = set(permits)
                scope = sorted(
                    allowed if scope is None else allowed.intersection(scope)
                )
            if scope == []:
                continue
            ranked = (
                self.vector_ranking(query, scope, query_vector)
                if dense
                else self.keyword_ranking(query, scope)
            )
            hits = [
                hit
                for hit in self.hits(
                    [
                        (rowid, float(-position))
                        for position, rowid in enumerate(ranked)
                    ],
                    lang,
                )
                if is_passage(hit.text)
            ]
            if permits is not None:
                hits = [
                    replace(
                        hit,
                        doc_url=permits[row]["url"],
                        document_id=permits[row]["document_id"],
                        document_revision=permits[row]["document_revision"],
                        product_ids=tuple(permits[row]["product_ids"]),
                    )
                    for hit in hits
                    for row in [
                        self._db.execute(
                            "SELECT rowid FROM chunks WHERE id=?", (hit.chunk_id,)
                        ).fetchone()[0]
                    ]
                    if row in permits
                ]
            if hits:
                if not neighbours:
                    return hits[:k]
                expanded = self.with_page_neighbours(
                    hits[:k],
                    lang,
                    allowed_rows=set(permits) if permits is not None else None,
                )
                if permits is not None:
                    expanded = [
                        replace(
                            hit,
                            doc_url=permits[row]["url"],
                            document_id=permits[row]["document_id"],
                            document_revision=permits[row]["document_revision"],
                            product_ids=tuple(permits[row]["product_ids"]),
                        )
                        for hit in expanded
                        for row in [
                            self._db.execute(
                                "SELECT rowid FROM chunks WHERE id=?", (hit.chunk_id,)
                            ).fetchone()[0]
                        ]
                        if row in permits
                    ]
                return expanded
        return []

    def with_page_neighbours(
        self,
        hits: Sequence[DocumentHit],
        lang: str,
        limit: int = MAX_HITS,
        allowed_rows: set[int] | None = None,
    ) -> list[DocumentHit]:
        """The hits with their neighbours, `limit` in all.

        A hit's neighbours are the other passages of its page and, for a short
        datasheet (SHORT_DATASHEET_PAGES), of the whole document, same page first,
        each in reading order. They follow the last hit already placed from that
        page; hits are visited in rank order. A neighbour carries its hit's score.
        """
        out = list(hits)
        seen = {hit.chunk_id for hit in hits}
        for hit in hits:
            if len(out) >= limit:
                break
            whole = self._db.execute(
                "SELECT 1 FROM documents WHERE sha256 = ? AND doc_type = 'datasheet'"
                " AND pages <= ?",
                (hit.doc_sha256, SHORT_DATASHEET_PAGES),
            ).fetchone()
            rows = self._db.execute(
                "SELECT c.rowid FROM chunks c WHERE c.doc_sha256 = ?"
                + ("" if whole else " AND c.page = ?")
                + " ORDER BY c.page != ?, c.page, c.rowid",
                (hit.doc_sha256, hit.page)
                if whole
                else (hit.doc_sha256, hit.page, hit.page),
            ).fetchall()
            neighbours = [
                neighbour
                for neighbour in self.hits(
                    [
                        (row[0], hit.score)
                        for row in rows
                        if allowed_rows is None or row[0] in allowed_rows
                    ],
                    lang,
                )
                if neighbour.chunk_id not in seen and is_passage(neighbour.text)
            ][: limit - len(out)]
            if not neighbours:
                continue
            seen.update(neighbour.chunk_id for neighbour in neighbours)
            position = max(
                index
                for index, placed in enumerate(out)
                if (placed.doc_sha256, placed.page) == (hit.doc_sha256, hit.page)
            )
            out[position + 1 : position + 1] = neighbours
        return out

    def permissions(
        self, snapshot: Snapshot, requested: Sequence[int] | None
    ) -> dict[int, Permit]:
        """Intersect loaded per-chunk applicability with current Woo associations.

        SHA only reuses parsing. An active association must match its own identity,
        content revision and product revision; another same-SHA URL grants nothing.
        A mixed-model chunk is released only while every model it contains is allowed.
        Old indexes have no proof tables and therefore authorize no chunks.
        """
        tables = {
            r[0]
            for r in self._db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "publication_documents" not in tables:
            return {}
        loaded_products = dict(
            self._db.execute(
                "SELECT product_id, product_revision FROM publication_products"
            )
        )
        allowed = {
            pid
            for pid, revision in loaded_products.items()
            if pid in snapshot.products
            and snapshot.products[pid]["product_revision"] == revision
        }
        wanted = (
            allowed
            if requested is None
            else {snapshot.canonical(pid) for pid in requested}.intersection(allowed)
        )
        associations: dict[str, list[dict[str, Any]]] = {}
        for did, revision, sha, pid in self._db.execute(
            "SELECT document_id, document_revision, blob_sha256, product_id FROM publication_documents"
        ):
            current = snapshot.documents.get(did)
            if (
                pid not in wanted
                or current is None
                or current["document_revision"] != revision
                or current["blob_sha256"] != sha
                or pid not in current["product_ids"]
            ):
                continue
            associations.setdefault(sha, []).append(
                {
                    "document_id": did,
                    "document_revision": revision,
                    "url": current["url"],
                    "product_id": pid,
                    "allowed_product_ids": current["product_ids"],
                }
            )
        output: dict[int, Permit] = {}
        for row, sha, raw_ids in self._db.execute(
            "SELECT c.rowid, c.doc_sha256, cp.product_ids FROM chunks c JOIN chunk_products cp ON cp.chunk_id=c.id"
        ):
            ids = set(json.loads(raw_ids))
            if not ids or not ids.issubset(allowed):
                continue
            for association in associations.get(sha, []):
                if association["product_id"] in ids and ids.issubset(
                    set(association["allowed_product_ids"])
                ):
                    output[row] = {
                        "document_id": str(association["document_id"]),
                        "document_revision": str(association["document_revision"]),
                        "url": str(association["url"]),
                        "product_ids": sorted(ids),
                    }
                    break
        return output

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
    path = Path(os.environ.get("GENIE_INDEX", str(DEFAULT_INDEX))).resolve(strict=True)
    # Resolve before comparing: switching `current` must reopen the actual file.
    if _DEFAULT is None or _DEFAULT.path != path:
        replacement = DocumentIndex(path)
        previous = _DEFAULT
        _DEFAULT = replacement
        if previous is not None:
            previous.close()
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
