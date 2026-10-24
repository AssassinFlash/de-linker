"""The build's intermediate format: one directory of JSONL that every store is made from.

    meta.json        version, embedding model and dimensions (or none), parser, limits
    documents.jsonl  one unique PDF per line (status indexed | failed, with the reason)
    products.jsonl   product ID and the model it sells
    chunks.jsonl     one chunk per line; `vector` (base64 of float32 little-endian) when
                     the build embedded it

Parsing and chunking end here, independent of storage (docs/specs/10-knowledge-index.md,
"索引放在哪里"): `index.store` exports it to SQLite (FTS5 + sqlite-vec) and
`index.mariadb` to SQL for the shared host's MariaDB.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from index.chunking import Chunk


@dataclass(frozen=True)
class DocumentRow:
    """One document as the index records it."""

    sha256: str
    urls: tuple[str, ...]
    title_en: str
    title_de: str
    brands: tuple[str, ...]
    models: tuple[str, ...]
    doc_type: str
    lang: str
    pages: int
    status: str
    error: str = ""


@dataclass(frozen=True)
class Meta:
    """What the corpus was built with."""

    version: str
    embedding_model: str | None
    dimensions: int | None
    parser: str
    max_tokens: int
    # The encoder's fingerprint (linker_genie.embedding.Embedder.fingerprint).
    embedding: dict[str, str] | None = None
    publication: dict[str, Any] = field(default_factory=dict)
    recipe_revision: str = ""
    serving_revision: str = ""
    activation_epoch: int = 0


def meta_values(meta: Meta, schema_version: int) -> dict[str, str]:
    """The key/value rows every store's `meta` table holds."""
    return {
        "schema_version": str(schema_version),
        "version": meta.version,
        "embedding_model": meta.embedding_model or "",
        "dimensions": str(meta.dimensions or 0),
        "embedding_fingerprint": json.dumps(meta.embedding or {}, sort_keys=True),
        "parser": meta.parser,
        "recipe_revision": meta.recipe_revision,
        "serving_revision": meta.serving_revision,
        "activation_epoch": str(meta.activation_epoch),
        "source_revision": str(
            meta.publication.get("manifest", {}).get("source_revision", "")
        ),
    }


def _write_lines(path: Path, rows: Iterator[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_lines(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def write(
    directory: Path,
    meta: Meta,
    documents: Sequence[DocumentRow],
    products: Sequence[tuple[int, str]],
    chunks: Sequence[Chunk],
    vectors: Sequence[bytes] | None = None,
) -> None:
    """Write one corpus directory; `vectors`, when given, align with `chunks`."""
    if vectors is not None and len(vectors) != len(chunks):
        raise ValueError(f"{len(chunks)} chunks but {len(vectors)} vectors")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "meta.json").write_text(
        json.dumps(asdict(meta), indent=1), encoding="utf-8"
    )
    _write_lines(
        directory / "documents.jsonl", (asdict(document) for document in documents)
    )
    _write_lines(
        directory / "products.jsonl",
        ({"product_id": product_id, "model": model} for product_id, model in products),
    )

    def chunk_rows() -> Iterator[dict[str, Any]]:
        for position, chunk in enumerate(chunks):
            row = asdict(chunk)
            if vectors is not None:
                row["vector"] = base64.b64encode(vectors[position]).decode()
            yield row

    _write_lines(directory / "chunks.jsonl", chunk_rows())


def read_meta(directory: Path) -> Meta:
    return Meta(**json.loads((directory / "meta.json").read_text(encoding="utf-8")))


def read_documents(directory: Path) -> list[DocumentRow]:
    return [
        DocumentRow(
            **{
                **row,
                "urls": tuple(row["urls"]),
                "brands": tuple(row["brands"]),
                "models": tuple(row["models"]),
            }
        )
        for row in _read_lines(directory / "documents.jsonl")
    ]


def read_products(directory: Path) -> list[tuple[int, str]]:
    return [
        (int(row["product_id"]), str(row["model"]))
        for row in _read_lines(directory / "products.jsonl")
    ]


def read_chunks(directory: Path) -> Iterator[tuple[Chunk, bytes | None]]:
    """Every chunk with its vector, or None when the corpus has no vectors."""
    for row in _read_lines(directory / "chunks.jsonl"):
        encoded = row.pop("vector", None)
        row["preceding_text"] = tuple(row.get("preceding_text", ()))
        row["source_rows"] = tuple(row.get("source_rows", ()))
        row["source_headings"] = tuple(row.get("source_headings", ()))
        yield Chunk(**row), base64.b64decode(encoded) if encoded is not None else None
