"""SQLite store: a corpus directory (index.corpus) -> one SQLite file.

Tables (docs/specs/10-knowledge-index.md, Build 4):
- `meta`: schema version, index version, embedding model and dimensions;
- `documents`: one row per unique PDF, `status` indexed | failed (with the reason);
- `document_models`: the model tags of each document, from the products that link it;
- `products`: product ID -> model, so a search can be narrowed by product IDs;
- `chunks`: the passages; `chunks_fts` (FTS5, unicode61; German compounds are not
  split) indexes header and text; `chunks_vec` (sqlite-vec, when the corpus has
  vectors) holds one vector per chunk under the same rowid.
`linker_genie.retrieval` reads this layout; SCHEMA_VERSION is the contract between them.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import sqlite_vec

from index import corpus
from index.table_compiler import external_axis_anchors
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk, table_header
from linker_genie.retrieval import SCHEMA_VERSION, is_passage
from linker_genie.table_projection import unqualified_table_columns

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE documents (
    sha256 TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    urls TEXT NOT NULL,
    title_en TEXT NOT NULL,
    title_de TEXT NOT NULL,
    brands TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    lang TEXT NOT NULL,
    pages INTEGER NOT NULL,
    status TEXT NOT NULL,
    error TEXT NOT NULL
);
CREATE TABLE document_models (
    doc_sha256 TEXT NOT NULL REFERENCES documents(sha256),
    model TEXT NOT NULL,
    PRIMARY KEY (doc_sha256, model)
);
CREATE TABLE products (
    product_id INTEGER NOT NULL,
    model TEXT NOT NULL,
    PRIMARY KEY (product_id, model)
);
CREATE TABLE publication_ready_products (product_id INTEGER PRIMARY KEY, product_revision TEXT NOT NULL);
CREATE TABLE publication_products (product_id INTEGER PRIMARY KEY, product_revision TEXT NOT NULL);
CREATE TABLE publication_documents (document_id TEXT NOT NULL, document_revision TEXT NOT NULL, blob_sha256 TEXT NOT NULL, product_id INTEGER NOT NULL, PRIMARY KEY(document_id,product_id));
CREATE TABLE chunk_products (chunk_id TEXT PRIMARY KEY, product_ids TEXT NOT NULL);
CREATE TABLE chunk_scopes (chunk_id TEXT PRIMARY KEY, proof TEXT NOT NULL);
CREATE TABLE chunks (
    rowid INTEGER PRIMARY KEY,
    id TEXT NOT NULL UNIQUE,
    doc_sha256 TEXT NOT NULL REFERENCES documents(sha256),
    page INTEGER NOT NULL,
    section TEXT NOT NULL,
    kind TEXT NOT NULL,
    header TEXT NOT NULL,
    text TEXT NOT NULL,
    lang TEXT NOT NULL,
    tokens INTEGER NOT NULL
);
CREATE INDEX chunks_by_document ON chunks(doc_sha256, page);
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    header, text, content='chunks', content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);
"""
# One vector per chunk, under the chunk's rowid; the width is the model's.
VECTORS = "CREATE VIRTUAL TABLE chunks_vec USING vec0(embedding float[{dimensions}] distance_metric=cosine)"


def connect(path: Path) -> sqlite3.Connection:
    """A connection with sqlite-vec loaded."""
    db = sqlite3.connect(path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    return db


def export(directory: Path, path: Path) -> None:
    """Write the corpus in `directory` to a new SQLite file at `path`."""
    if path.exists():
        raise FileExistsError(path)
    meta = corpus.read_meta(directory)
    db = connect(path)
    try:
        db.executescript(SCHEMA)
        values = corpus.meta_values(meta, SCHEMA_VERSION)
        db.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)", sorted(values.items())
        )
        proof = meta.publication
        manifest = proof.get("manifest", {})
        if manifest:
            ordinary = Snapshot.read(manifest)
            manifest = {
                **manifest,
                "products": list(ordinary.products.values()),
                "documents": list(ordinary.documents.values()),
            }
        db.executemany(
            "INSERT INTO publication_products VALUES (?, ?)",
            [
                (p["product_id"], p["product_revision"])
                for p in manifest.get("products", [])
            ],
        )
        db.executemany(
            "INSERT INTO publication_documents VALUES (?, ?, ?, ?)",
            [
                (d["document_id"], d["document_revision"], d["blob_sha256"], pid)
                for d in manifest.get("documents", [])
                for pid in d["product_ids"]
            ],
        )
        db.executemany(
            "INSERT INTO chunk_products VALUES (?, ?)",
            [
                (cid, json.dumps(ids))
                for cid, ids in proof.get("chunk_products", {}).items()
            ],
        )
        db.executemany(
            "INSERT INTO chunk_scopes VALUES (?, ?)",
            [
                (cid, json.dumps(scope, sort_keys=True))
                for cid, scope in proof.get("chunk_scopes", {}).items()
            ],
        )
        # Availability means at least one passage the current retrieval guard can
        # release. Materialization success is independent of semantic coverage:
        # deterministic lack of a proven passage must not rebuild forever.
        chunks_by_id = {chunk.id: chunk for chunk, _ in corpus.read_chunks(directory)}
        column_texts = unqualified_table_columns(
            [
                (c.doc_sha256, c.page, c.kind, c.id, c.text)
                for c in chunks_by_id.values()
            ],
            proof.get("chunk_scopes", {}),
        )
        projected_tables = {
            (projection.get("source_sha256"), projection.get("source_table"))
            for scope in proof.get("chunk_scopes", {}).values()
            if isinstance(scope, dict)
            for projection in [scope.get("table_projection")]
            if isinstance(projection, dict)
            and isinstance(projection.get("source_sha256"), str)
            and isinstance(projection.get("source_table"), str)
        }
        warranty_sources = {
            cid
            for scope in proof.get("chunk_scopes", {}).values()
            if isinstance(scope, dict) and scope.get("basis") == "warranty_terms"
            for cid in scope.get("source_chunk_ids", [])
            if isinstance(cid, str)
        }
        axis_anchors = {
            cid: anchor
            for cid, anchor in external_axis_anchors(
                list(chunks_by_id.values())
            ).items()
            if anchor.get("kind") == "pdf_cover"
            or (
                anchor.get("kind") in {"policy_table", "policy_text"}
                and cid in warranty_sources
            )
            or (anchor.get("source_sha256"), anchor.get("source_table"))
            in projected_tables
        }
        if axis_anchors:
            db.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                ("external_axis_anchors", json.dumps(axis_anchors, sort_keys=True)),
            )
        covered: dict[int, set[str]] = {}
        prepared: dict[int, set[str]] = {}
        by_id = {d["document_id"]: d for d in manifest.get("documents", [])}
        revisions = {
            p["product_id"]: p["product_revision"] for p in manifest.get("products", [])
        }
        products = {p["product_id"]: p for p in manifest.get("products", [])}
        links = [
            {
                "document_id": d["document_id"],
                "document_revision": d["document_revision"],
                "blob_sha256": d["blob_sha256"],
                "product_id": pid,
                "product_revision": revisions[pid],
            }
            for d in by_id.values()
            for pid in d["product_ids"]
            if pid in revisions
        ]
        for cid, ids in proof.get("chunk_products", {}).items():
            chunk = chunks_by_id.get(cid)
            if chunk is not None and ids and is_passage(chunk.text):
                scope = proof.get("chunk_scopes", {}).get(cid)
                if cid in column_texts and not column_texts[cid]:
                    continue
                if (
                    table_header(scope, ids, products, chunk_id=cid, text=chunk.text)
                    is None
                ):
                    continue
                supported = authorize_chunk(
                    chunk.doc_sha256,
                    ids,
                    links,
                    scope,
                    products=products,
                    documents=by_id,
                    chunk_id=cid,
                    text=chunk.text,
                    external_axis_anchors=axis_anchors,
                    require_table_anchor=True,
                )
                for item in supported:
                    covered.setdefault(item["product_id"], set()).add(
                        item["document_id"]
                    )
                    # A first-contact procedure makes a passage available, but
                    # alone does not prepare the policy's duration or terms.
                    if not scope or scope.get("basis") != "warranty_procedure":
                        prepared.setdefault(item["product_id"], set()).add(
                            item["document_id"]
                        )
        ready = []
        unprepared = []
        document_status = {d.sha256: d.status for d in corpus.read_documents(directory)}
        for product in manifest.get("products", []):
            pid = product["product_id"]
            if covered.get(pid):
                ready.append((product["product_id"], product["product_revision"]))
            for did in product["documents"]:
                document = by_id.get(did)
                if (
                    document is None
                    or document_status.get(document["blob_sha256"]) != "indexed"
                ):
                    reason = "document_unparsed"
                elif did not in prepared.get(pid, set()):
                    reason = "no_proven_passage"
                else:
                    continue
                unprepared.append(
                    {"document_id": did, "product_id": pid, "reason": reason}
                )
        db.executemany("INSERT INTO publication_ready_products VALUES (?, ?)", ready)
        complete = not unprepared and len(ready) == len(manifest.get("products", []))
        materialized = all(
            document_status.get(document["blob_sha256"]) == "indexed"
            for document in by_id.values()
        ) and not any(row["reason"] == "document_unparsed" for row in unprepared)
        db.executemany(
            "INSERT INTO meta VALUES (?, ?)",
            [
                ("preparation_complete", json.dumps(complete)),
                ("materialization_complete", json.dumps(materialized)),
                ("unprepared_documents", json.dumps(unprepared, sort_keys=True)),
            ],
        )
        if meta.dimensions:
            db.execute(VECTORS.format(dimensions=int(meta.dimensions)))
        for document in corpus.read_documents(directory):
            db.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document.sha256,
                    document.urls[0],
                    json.dumps(list(document.urls)),
                    document.title_en,
                    document.title_de,
                    json.dumps(list(document.brands)),
                    document.doc_type,
                    document.lang,
                    document.pages,
                    document.status,
                    document.error,
                ),
            )
            db.executemany(
                "INSERT INTO document_models VALUES (?, ?)",
                [(document.sha256, model) for model in document.models],
            )
        db.executemany(
            "INSERT OR IGNORE INTO products VALUES (?, ?)",
            corpus.read_products(directory),
        )
        for rowid, (chunk, vector) in enumerate(corpus.read_chunks(directory), start=1):
            db.execute(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    rowid,
                    chunk.id,
                    chunk.doc_sha256,
                    chunk.page,
                    chunk.section,
                    chunk.kind,
                    chunk.header,
                    chunk.text,
                    chunk.lang,
                    chunk.tokens,
                ),
            )
            if meta.dimensions:
                if vector is None:
                    raise ValueError(
                        f"chunk {chunk.id} has no vector, the corpus says {meta.dimensions}"
                    )
                db.execute(
                    "INSERT INTO chunks_vec (rowid, embedding) VALUES (?, ?)",
                    (rowid, vector),
                )
        db.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('rebuild')")
        db.commit()
        db.execute("VACUUM")
    finally:
        db.close()
