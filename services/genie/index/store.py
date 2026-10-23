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
from linker_genie.retrieval import SCHEMA_VERSION

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
        # A product becomes prepared only after each associated document has
        # at least one proven passage for it. Failures and ambiguous text stay pending.
        chunks_by_id = {chunk.id: chunk for chunk, _ in corpus.read_chunks(directory)}
        covered: dict[int, set[str]] = {}
        for cid, ids in proof.get("chunk_products", {}).items():
            chunk = chunks_by_id.get(cid)
            if chunk is not None:
                for pid in ids:
                    covered.setdefault(pid, set()).add(chunk.doc_sha256)
        by_id = {d["document_id"]: d for d in manifest.get("documents", [])}
        ready = []
        for product in manifest.get("products", []):
            required = {
                by_id[did]["blob_sha256"]
                for did in product["documents"]
                if did in by_id
            }
            if required and required.issubset(
                covered.get(product["product_id"], set())
            ):
                ready.append((product["product_id"], product["product_revision"]))
        db.executemany("INSERT INTO publication_ready_products VALUES (?, ?)", ready)
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
