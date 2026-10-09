"""MariaDB store: a corpus directory (index.corpus) -> one SQL file for the shared host.

For the index locations that keep the index beside WordPress (docs/specs/
10-knowledge-index.md, "索引放在哪里": A with API vectors, C keywords only). The file
creates `<prefix>genie_*` tables - documents, document_models, products, meta and chunks
with a FULLTEXT key over header and text and, when the corpus has vectors, a
`VECTOR(N)` column under a cosine vector index - and inserts the corpus. The vector
syntax is MariaDB's (11.7+, "CREATE TABLE with Vectors"): the indexed column is NOT NULL,
one vector index per table, `DISTANCE=cosine` declared because the default is euclidean.
Loading it is `wp db query < file` on the host; nothing here connects to a database.
"""

from __future__ import annotations

import json
import struct
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

from index import corpus
from linker_genie.retrieval import SCHEMA_VERSION

# Rows per INSERT statement. One statement must fit max_allowed_packet, 16 MiB by
# default ("Server System Variables", MariaDB docs, read via Apify 2026-10-09): 100 chunks
# of at most 512 tokens (about 3 KB of text each) with a 3072-dimension vector written
# out (about 34 KB) come to about 3.7 MB.
ROWS_PER_INSERT = 100


def quote(value: str) -> str:
    """A MariaDB string literal: backslash and quote escaped (default sql_mode)."""
    return (
        "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("\0", "\\0") + "'"
    )


def vector_literal(vector: bytes) -> str:
    """`VEC_FromText('[...]')` of a float32 little-endian vector."""
    values = struct.unpack(f"<{len(vector) // 4}f", vector)
    return "VEC_FromText('[" + ",".join(f"{value:.7g}" for value in values) + "]')"


def _insert(out: TextIO, table: str, rows: Iterable[str]) -> None:
    batch: list[str] = []
    for row in rows:
        batch.append(row)
        if len(batch) == ROWS_PER_INSERT:
            out.write(f"INSERT INTO `{table}` VALUES\n" + ",\n".join(batch) + ";\n")
            batch = []
    if batch:
        out.write(f"INSERT INTO `{table}` VALUES\n" + ",\n".join(batch) + ";\n")


def export(directory: Path, path: Path, prefix: str = "wp_") -> None:
    """Write the corpus in `directory` as MariaDB SQL to `path`."""
    meta = corpus.read_meta(directory)
    t = f"{prefix}genie_"
    vector_column = (
        f",\n  `embedding` VECTOR({int(meta.dimensions)}) NOT NULL"
        if meta.dimensions
        else ""
    )
    vector_index = (
        ",\n  VECTOR INDEX (`embedding`) DISTANCE=cosine" if meta.dimensions else ""
    )
    charset = "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    with path.open("w", encoding="utf-8") as out:
        out.write("SET NAMES utf8mb4;\n")
        for table in ("chunks", "products", "document_models", "documents", "meta"):
            out.write(f"DROP TABLE IF EXISTS `{t}{table}`;\n")
        out.write(
            f"CREATE TABLE `{t}meta` (`key` VARCHAR(64) NOT NULL PRIMARY KEY, "
            f"`value` TEXT NOT NULL) {charset};\n"
            f"CREATE TABLE `{t}documents` (\n  `sha256` CHAR(64) NOT NULL PRIMARY KEY,\n"
            "  `url` VARCHAR(1024) NOT NULL,\n  `urls` JSON NOT NULL,\n"
            "  `title_en` VARCHAR(512) NOT NULL,\n  `title_de` VARCHAR(512) NOT NULL,\n"
            "  `brands` JSON NOT NULL,\n  `doc_type` VARCHAR(32) NOT NULL,\n"
            "  `lang` VARCHAR(16) NOT NULL,\n  `pages` INT NOT NULL,\n"
            f"  `status` VARCHAR(16) NOT NULL,\n  `error` TEXT NOT NULL\n) {charset};\n"
            f"CREATE TABLE `{t}document_models` (`doc_sha256` CHAR(64) NOT NULL, "
            f"`model` VARCHAR(191) NOT NULL, PRIMARY KEY (`doc_sha256`, `model`)) {charset};\n"
            f"CREATE TABLE `{t}products` (`product_id` BIGINT UNSIGNED NOT NULL, "
            f"`model` VARCHAR(191) NOT NULL, PRIMARY KEY (`product_id`, `model`)) {charset};\n"
            f"CREATE TABLE `{t}chunks` (\n  `rowid` INT UNSIGNED NOT NULL PRIMARY KEY,\n"
            "  `id` VARCHAR(64) NOT NULL UNIQUE,\n  `doc_sha256` CHAR(64) NOT NULL,\n"
            "  `page` INT NOT NULL,\n  `section` TEXT NOT NULL,\n  `kind` VARCHAR(8) NOT NULL,\n"
            "  `header` TEXT NOT NULL,\n  `text` MEDIUMTEXT NOT NULL,\n"
            f"  `lang` VARCHAR(16) NOT NULL,\n  `tokens` INT NOT NULL{vector_column},\n"
            "  KEY `by_document` (`doc_sha256`, `page`),\n"
            f"  FULLTEXT KEY `words` (`header`, `text`){vector_index}\n) {charset};\n"
        )
        values = corpus.meta_values(meta, SCHEMA_VERSION)
        _insert(
            out,
            f"{t}meta",
            (
                f"({quote(key)}, {quote(value)})"
                for key, value in sorted(values.items())
            ),
        )
        documents = corpus.read_documents(directory)
        _insert(
            out,
            f"{t}documents",
            (
                "("
                + ", ".join(
                    [
                        quote(document.sha256),
                        quote(document.urls[0]),
                        quote(json.dumps(list(document.urls))),
                        quote(document.title_en),
                        quote(document.title_de),
                        quote(json.dumps(list(document.brands))),
                        quote(document.doc_type),
                        quote(document.lang),
                        str(document.pages),
                        quote(document.status),
                        quote(document.error),
                    ]
                )
                + ")"
                for document in documents
            ),
        )
        _insert(
            out,
            f"{t}document_models",
            (
                f"({quote(document.sha256)}, {quote(model)})"
                for document in documents
                for model in document.models
            ),
        )
        _insert(
            out,
            f"{t}products",
            (
                f"({product_id}, {quote(model)})"
                for product_id, model in sorted(set(corpus.read_products(directory)))
            ),
        )

        def chunk_rows() -> Iterable[str]:
            for rowid, (chunk, vector) in enumerate(
                corpus.read_chunks(directory), start=1
            ):
                fields = [
                    str(rowid),
                    quote(chunk.id),
                    quote(chunk.doc_sha256),
                    str(chunk.page),
                    quote(chunk.section),
                    quote(chunk.kind),
                    quote(chunk.header),
                    quote(chunk.text),
                    quote(chunk.lang),
                    str(chunk.tokens),
                ]
                if meta.dimensions:
                    if vector is None:
                        raise ValueError(
                            f"chunk {chunk.id} has no vector, the corpus says {meta.dimensions}"
                        )
                    fields.append(vector_literal(vector))
                yield "(" + ", ".join(fields) + ")"

        _insert(out, f"{t}chunks", chunk_rows())
