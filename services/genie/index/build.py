"""Build: inventory -> parse -> chunk -> embed -> store (`just index`).

Runs on the Mac, offline except for reading the media library and products (GET),
downloading our own PDFs and, for an API model, embedding. Writes
`<INDEX_DIR>/builds/<version>/` with
- `corpus/`: the intermediate JSONL every store is made from (index.corpus);
- `index.sqlite` (index.store) and, with `--mariadb`, `index-mariadb.sql` (index.mariadb);
- `manifest.json`: what was built from what, sizes, timings, failures;
- `coverage.json`: per document, pages, pages with chunks, and why each page without
  a chunk has none.
`ops/publish_index.py` ships `index.sqlite` with its manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from index import corpus, extract, inventory, mariadb, parse, store
from index.chunking import MAX_TOKENS, Chunk, DocumentMeta, Tokenizer, chunk_document
from index.corpus import DocumentRow
from index.paths import INDEX_DIR, INVENTORY_PATH, PARSED_DIR, PDF_DIR
from index.preparation import recipe_revision
from linker_genie.embedding import (
    BGE_M3,
    MODELS,
    OPEN_MODELS,
    Embedder,
    OnnxEmbedder,
    Passage,
    gemini_from_env,
    sha256_of,
)
from linker_genie.preparation import serving_revision

INDEX_FILE = "index.sqlite"
# Chunk sizes are counted in XLM-RoBERTa tokens, the tokenizer of BGE-M3 and of
# multilingual-e5, for every model: all models then embed identical chunks, which the
# bake-off needs (docs/research/2026-10-09/embedding-bakeoff.md).
CHUNK_TOKENIZER = "BAAI/bge-m3"
# The model `just index` builds with: the bake-off's choice. gemini-embedding-2 beat
# the best open model by 13.0 points of recall@5 (docs/research/2026-10-09/
# embedding-bakeoff.md), so the index ships with API vectors (location A); building
# needs OPENROUTER_API_KEY/OPENROUTER_BASE_URL (the model routing law: aihubmix
# serves only behind LINKER_EMBEDDING_PROVIDER=aihubmix, never as an automatic
# fallback). The open models remain one flag away
# (--model) for a VPS-only index.
DEFAULT_MODEL = "gemini-embedding-2"


@dataclass
class Coverage:
    """How much of one document reached the index."""

    sha256: str
    url: str
    status: str
    pages: int
    pages_with_chunks: int
    chunks: int
    empty_pages: dict[int, str]
    error: str = ""


def empty_page_reasons(pdf_path: Path, pages: Iterable[int]) -> dict[int, str]:
    """Why each page that yielded no chunk has none, from its text layer and images."""
    import pypdfium2

    reasons: dict[int, str] = {}
    pdf = pypdfium2.PdfDocument(str(pdf_path))
    try:
        for number in pages:
            page = pdf[number - 1]
            chars = len(page.get_textpage().get_text_range().strip())
            images = sum(
                1
                for item in page.get_objects()
                if item.type == pypdfium2.raw.FPDF_PAGEOBJ_IMAGE
            )
            if chars:
                reasons[number] = (
                    f"text layer of {chars} characters, none of it body text: Docling classed it "
                    "as page header or footer"
                )
            elif images:
                reasons[number] = (
                    f"no text layer; OCR of its {images} image(s) found no text"
                )
            else:
                reasons[number] = "blank: no text layer and no image"
    finally:
        pdf.close()
    return reasons


def failure_reason(pdf_path: Path, errors: Sequence[str]) -> str:
    """Why a document could not be parsed at all."""
    tail = pdf_path.read_bytes()[-1024:]
    if b"%%EOF" not in tail:
        return (
            "hosted file is truncated: it ends without the %%EOF trailer, so PDF readers "
            f"(PDFium, Poppler) cannot open it; {'; '.join(errors)}"
        )
    return "; ".join(errors) or "Docling produced no document"


class EmbeddingCache:
    """Vectors already computed for one encoder fingerprint and a text, across builds.

    The key carries the whole fingerprint (model, revision, ONNX and tokenizer hashes,
    input format), the same identity `DocumentIndex` checks a query encoder against:
    a rebuilt model under the same name - a new revision, a re-exported ONNX file -
    never reuses the old vectors.
    """

    def __init__(self, path: Path) -> None:
        # Several builds may fill the cache at once (one per model): wait for the lock.
        self._db = sqlite3.connect(path, timeout=300)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, vector BLOB NOT NULL)"
        )

    def _key(self, fingerprint: str, passage: Passage) -> str:
        return hashlib.sha256(
            f"{fingerprint}\0{passage.title}\0{passage.text}".encode()
        ).hexdigest()

    def embed(
        self, embedder: Embedder, passages: Sequence[Passage], batch: int = 256
    ) -> list[bytes]:
        fingerprint = json.dumps(embedder.fingerprint, sort_keys=True)
        keys = [self._key(fingerprint, passage) for passage in passages]
        found: dict[str, bytes] = {}
        for start in range(0, len(keys), 900):
            part = keys[start : start + 900]
            marks = ",".join("?" * len(part))
            found.update(
                self._db.execute(
                    f"SELECT key, vector FROM vectors WHERE key IN ({marks})", part
                )
            )
        missing = [index for index, key in enumerate(keys) if key not in found]
        print(
            f"embedding: {len(passages) - len(missing)} cached, {len(missing)} to compute",
            flush=True,
        )
        for start in range(0, len(missing), batch):
            indices = missing[start : start + batch]
            vectors = embedder.embed_documents([passages[index] for index in indices])
            rows = [
                (keys[index], vector)
                for index, vector in zip(indices, vectors, strict=True)
            ]
            self._db.executemany("INSERT OR REPLACE INTO vectors VALUES (?, ?)", rows)
            self._db.commit()
            found.update(rows)
            print(
                f"  embedded {min(start + batch, len(missing))}/{len(missing)}",
                flush=True,
            )
        return [found[key] for key in keys]

    def close(self) -> None:
        self._db.close()


def passage(chunk: Chunk, title: str) -> Passage:
    """What a model sees of a chunk: its document's title, its context header and text."""
    return Passage(title=title, text=f"{chunk.header}\n{chunk.text}")


def model_identity(embedder: Embedder) -> str:
    """The name the index records for `embedder`: its fingerprint's, not its wire name.

    GeminiEmbedder's `model` is what the provider's API expects - google/gemini-embedding-2
    on OpenRouter - while the fingerprint carries the provider-neutral name the index was
    built under (linker_genie.embedding.GeminiEmbedder). `retrieval.query_encoder` resolves
    a stored index by that identity, so recording the wire name would open the index with
    no query encoder and silently degrade every search to keywords.
    """
    return str(embedder.fingerprint.get("model") or embedder.model)


def _meta(document: inventory.Document) -> DocumentMeta:
    return DocumentMeta(
        sha256=document.sha256,
        title_en=document.title_en,
        title_de=document.title_de,
        brands=tuple(document.brands),
        models=tuple(document.models),
        doc_type=document.doc_type,
        lang=document.lang,
    )


def _row(
    document: inventory.Document, pages: int, status: str, error: str = ""
) -> DocumentRow:
    return DocumentRow(
        sha256=document.sha256,
        urls=tuple(document.urls),
        title_en=document.title_en,
        title_de=document.title_de,
        brands=tuple(document.brands),
        models=tuple(document.models),
        doc_type=document.doc_type,
        lang=document.lang,
        pages=pages,
        status=status,
        error=error,
    )


@dataclass
class Chunked:
    """Every document chunked, with what the manifest reports about the chunking."""

    documents: list[DocumentRow]
    products: list[tuple[int, str]]
    chunks: list[Chunk]
    coverage: list[Coverage]
    parsers: set[str]
    parse_seconds: float


def chunk_all(
    inventory_path: Path,
    pdf_dir: Path,
    parsed_dir: Path,
    tokenizer: Tokenizer,
    detect_lang: Callable[[str], str],
) -> Chunked:
    """Chunk every inventory document from its cached parse."""
    result = Chunked([], [], [], [], set(), 0.0)
    # Archived bake-off corpora can contain only Docling fixtures. Current Woo
    # publication builds always have the SHA-verified originals from inventory.
    source_geometry = "publication_manifest" in json.loads(inventory_path.read_text())
    result.products = [
        (product.id, product.model)
        for product in inventory.load_products(inventory_path)
        if product.model
    ]
    for document in inventory.load(inventory_path):
        doc_dir = parsed_dir / document.sha256
        status = (
            parse.cached_status(doc_dir)
            if source_geometry
            else parse.complete_status(doc_dir)
        )
        pdf_path = pdf_dir / f"{document.sha256}.pdf"
        if status is None or not (doc_dir / "docling.json").is_file():
            error = failure_reason(
                pdf_path, status.errors if status else ["not parsed"]
            )
            result.documents.append(
                _row(document, status.pages if status else 0, "failed", error)
            )
            result.coverage.append(
                Coverage(
                    document.sha256, document.urls[0], "failed", 0, 0, 0, {}, error
                )
            )
            continue
        result.parse_seconds += status.seconds
        result.parsers.add(status.docling)
        pages = extract.extract(
            doc_dir,
            status.pages,
            status.garbled_pages,
            pdf_path=pdf_path if source_geometry else None,
        )
        chunks = chunk_document(_meta(document), pages, tokenizer, detect_lang)
        result.chunks.extend(chunks)
        with_chunks = {chunk.page for chunk in chunks}
        empty = [
            number for number in range(1, status.pages + 1) if number not in with_chunks
        ]
        result.coverage.append(
            Coverage(
                sha256=document.sha256,
                url=document.urls[0],
                status="indexed",
                pages=status.pages,
                pages_with_chunks=len(with_chunks),
                chunks=len(chunks),
                empty_pages=empty_page_reasons(pdf_path, empty) if empty else {},
            )
        )
        result.documents.append(_row(document, status.pages, "indexed"))
    return result


def embed_corpus(
    source: Path, out_root: Path, embedder: Embedder, mariadb_prefix: str | None = None
) -> Path:
    """A new build from an earlier build's chunks, embedded with `embedder`.

    The bake-off builds every model from one chunking, so all models see identical chunks.
    `--mariadb` exports the same SQL the full build writes.
    """
    meta = corpus.read_meta(source)
    documents = corpus.read_documents(source)
    titles = {document.sha256: document.title_en for document in documents}
    chunks = [chunk for chunk, _ in corpus.read_chunks(source)]
    started = time.monotonic()
    out_root.mkdir(parents=True, exist_ok=True)
    cache = EmbeddingCache(out_root / "embedding-cache.sqlite")
    try:
        vectors = cache.embed(
            embedder, [passage(chunk, titles[chunk.doc_sha256]) for chunk in chunks]
        )
    finally:
        cache.close()
    embedded = time.monotonic()
    version = (
        time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        + f"-{time.time_ns() % 1_000_000_000:09d}"
    )
    build_dir = out_root / "builds" / version
    corpus_dir = build_dir / "corpus"
    new_meta = corpus.Meta(
        version,
        model_identity(embedder),
        embedder.dimensions,
        meta.parser,
        meta.max_tokens,
        embedding=embedder.fingerprint,
        publication=meta.publication,
        recipe_revision=meta.recipe_revision,
        serving_revision=meta.serving_revision,
    )
    products = corpus.read_products(source)
    corpus.write(corpus_dir, new_meta, documents, products, chunks, vectors)
    index_path = build_dir / INDEX_FILE
    store.export(corpus_dir, index_path)
    if mariadb_prefix is not None:
        mariadb.export(corpus_dir, build_dir / "index-mariadb.sql", mariadb_prefix)
    manifest = json.loads((source.parent / "manifest.json").read_text(encoding="utf-8"))
    manifest.update(
        version=version,
        embedding_model=model_identity(embedder),
        dimensions=embedder.dimensions,
        embedded_from=meta.version,
        file={
            "name": INDEX_FILE,
            "bytes": index_path.stat().st_size,
            "sha256": sha256_of(index_path),
        },
    )
    manifest["seconds"] = {**manifest["seconds"], "embed": round(embedded - started, 1)}
    (build_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    shutil.copy(source.parent / "coverage.json", build_dir / "coverage.json")
    summary = ("version", "file", "chunks", "seconds")
    print(json.dumps({key: manifest[key] for key in summary}, indent=1))
    return build_dir


def build(
    inventory_path: Path,
    pdf_dir: Path,
    parsed_dir: Path,
    out_root: Path,
    embedder: Embedder | None,
    tokenizer: Tokenizer,
    detect_lang: Callable[[str], str],
    mariadb_prefix: str | None = None,
    on_created: Callable[[Path], None] | None = None,
    activation_epoch: int = 0,
    publication_deadline: int | None = None,
) -> Path:
    """Chunk, embed and store; report the newly created generation before writing it."""
    started = time.monotonic()
    recipe = recipe_revision()
    serving = serving_revision()
    source = json.loads(inventory_path.read_text(encoding="utf-8"))
    chunked = chunk_all(inventory_path, pdf_dir, parsed_dir, tokenizer, detect_lang)
    after_chunking = time.monotonic()
    chunks = chunked.chunks
    proof: dict[str, Any] = {}
    if "publication_manifest" in source:
        from index.publication import compile_publication
        from linker_genie.publication import PublicationClient

        authority = (
            PublicationClient(str(source["source"]))
            if publication_deadline is None
            else PublicationClient(
                str(source["source"]), identify_deadline=publication_deadline
            )
        )
        try:
            chunks, scopes = compile_publication(
                chunks, source["publication_manifest"], authority, tokenizer
            )
            proof = {
                "manifest": source["publication_manifest"],
                "chunk_products": {
                    cid: scope["product_ids"] for cid, scope in scopes.items()
                },
                "chunk_scopes": scopes,
            }
        finally:
            authority.close()
    after_compilation = time.monotonic()
    print(
        f"{len(chunks)} chunks from {len(chunked.documents)} documents "
        f"({len(chunks) - len(chunked.chunks)} model projections)",
        flush=True,
    )
    vectors: list[bytes] | None = None
    if embedder is not None:
        titles = {document.sha256: document.title_en for document in chunked.documents}
        out_root.mkdir(parents=True, exist_ok=True)
        cache = EmbeddingCache(out_root / "embedding-cache.sqlite")
        try:
            vectors = cache.embed(
                embedder,
                [passage(chunk, titles[chunk.doc_sha256]) for chunk in chunks],
            )
        finally:
            cache.close()
    after_embedding = time.monotonic()

    version = (
        time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        + f"-{time.time_ns() % 1_000_000_000:09d}"
    )
    build_dir = out_root / "builds" / version
    build_dir.mkdir(parents=True)
    if on_created is not None:
        on_created(build_dir)
    meta = corpus.Meta(
        version=version,
        embedding_model=model_identity(embedder) if embedder else None,
        dimensions=embedder.dimensions if embedder else None,
        parser=", ".join(sorted(chunked.parsers)),
        max_tokens=MAX_TOKENS,
        embedding=embedder.fingerprint if embedder else None,
        publication=proof,
        recipe_revision=recipe,
        serving_revision=serving,
        activation_epoch=activation_epoch,
    )
    corpus_dir = build_dir / "corpus"
    corpus.write(corpus_dir, meta, chunked.documents, chunked.products, chunks, vectors)
    index_path = build_dir / INDEX_FILE
    store.export(corpus_dir, index_path)
    if mariadb_prefix is not None:
        mariadb.export(corpus_dir, build_dir / "index-mariadb.sql", mariadb_prefix)
    if recipe_revision() != recipe:
        raise RuntimeError("knowledge preparation code changed during this build")
    finished = time.monotonic()

    coverage = chunked.coverage
    failed = [asdict(item) for item in coverage if item.status == "failed"]
    manifest = {
        "version": version,
        "source_revision": str(
            source.get("publication_manifest", {}).get("source_revision", "")
        ),
        "recipe_revision": recipe,
        "serving_revision": serving,
        "activation_epoch": activation_epoch,
        "permission_coverage": {
            "proven_chunks": len(proof.get("chunk_products", {})),
            "total_chunks": len(chunks),
            "projected_chunks": len(chunks) - len(chunked.chunks),
        },
        "file": {
            "name": INDEX_FILE,
            "bytes": index_path.stat().st_size,
            "sha256": sha256_of(index_path),
        },
        "embedding_model": meta.embedding_model,
        "dimensions": meta.dimensions,
        "parser": meta.parser,
        "max_tokens": MAX_TOKENS,
        "source": source.get("source", ""),
        "documents": {
            "total": len(chunked.documents),
            "indexed": len(chunked.documents) - len(failed),
            "failed": len(failed),
        },
        "pages": {
            "total": sum(item.pages for item in coverage),
            "with_chunks": sum(item.pages_with_chunks for item in coverage),
        },
        "chunks": len(chunks),
        "seconds": {
            "parse_per_document_sum": round(chunked.parse_seconds, 1),
            "chunk": round(after_chunking - started, 1),
            "compile": round(after_compilation - after_chunking, 1),
            "embed": round(after_embedding - after_compilation, 1),
            "store": round(finished - after_embedding, 1),
        },
        "failures": failed,
    }
    (build_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    (build_dir / "coverage.json").write_text(
        json.dumps([asdict(item) for item in coverage], indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    summary = ("version", "file", "documents", "pages", "chunks", "seconds")
    print(json.dumps({key: manifest[key] for key in summary}, indent=1))
    return build_dir


def document_embedder(model: str) -> Embedder:
    """The embedder that builds an index with `model` on this machine."""
    if model == BGE_M3:
        from index.local_model import LocalEmbedder

        return LocalEmbedder(OPEN_MODELS[BGE_M3])
    if model in OPEN_MODELS:
        return OnnxEmbedder(OPEN_MODELS[model], threads=os.cpu_count() or 1)
    found = gemini_from_env()
    if found is None:
        raise SystemExit(
            "gemini-embedding-2 needs OPENROUTER_API_KEY/OPENROUTER_BASE_URL "
            "(env or ~/.config/terravolt-builder/openrouter.env); AIHubMix serves "
            "only behind LINKER_EMBEDDING_PROVIDER=aihubmix"
        )
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the document index.")
    parser.add_argument(
        "--rest-config", type=Path, default=inventory.DEFAULT_REST_CONFIG
    )
    parser.add_argument(
        "--skip-fetch", action="store_true", help="use the inventory and PDFs on disk"
    )
    parser.add_argument("--workers", type=int, default=parse.WORKERS)
    parser.add_argument(
        "--model",
        choices=[*MODELS, "none"],
        default=DEFAULT_MODEL,
        help="none: keywords only",
    )
    parser.add_argument(
        "--mariadb",
        metavar="PREFIX",
        help="also write index-mariadb.sql for WordPress tables PREFIX",
    )
    parser.add_argument(
        "--from-corpus",
        type=Path,
        metavar="DIR",
        help="embed the chunks of an earlier build's corpus instead of chunking again",
    )
    args = parser.parse_args(argv)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if args.from_corpus:
        if args.model == "none":
            parser.error("--from-corpus needs a model")
        embed_corpus(
            args.from_corpus,
            INDEX_DIR,
            document_embedder(args.model),
            mariadb_prefix=args.mariadb,
        )
        return 0
    if not args.skip_fetch:
        inventory.run(args.rest_config, INVENTORY_PATH, PDF_DIR)
    parse.run(INVENTORY_PATH, PDF_DIR, PARSED_DIR, args.workers)

    import py3langid

    from index.tokenizer import HFTokenizer

    embedder = None if args.model == "none" else document_embedder(args.model)

    def detect_lang(text: str) -> str:
        return str(py3langid.classify(text)[0])

    build(
        INVENTORY_PATH,
        PDF_DIR,
        PARSED_DIR,
        INDEX_DIR,
        embedder,
        HFTokenizer.from_pretrained(CHUNK_TOKENIZER),
        detect_lang,
        mariadb_prefix=args.mariadb,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
