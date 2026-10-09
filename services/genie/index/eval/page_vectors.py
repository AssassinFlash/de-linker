"""OCR page text (index.eval.page_text) -> page vectors of one text model, for the bake-off.

`python -m index.eval.page_vectors MODEL` embeds every page's OCR text as a passage
(title: the document's; text: the page) with the same embedder the build uses for
chunks, and writes `<INDEX_DIR>/page-text/<model>.sqlite` (pages: doc, page, vector)
beside a `.json` naming the model. Pages without text get no vector.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence

from index import inventory
from index.build import EmbeddingCache, document_embedder
from index.eval.page_text import STORE
from index.paths import INDEX_DIR, INVENTORY_PATH
from linker_genie.embedding import MODELS, Passage


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Embed the OCR page text with one model."
    )
    parser.add_argument("model", choices=MODELS)
    args = parser.parse_args(argv)
    titles = {
        document.sha256: document.title_en
        for document in inventory.load(INVENTORY_PATH)
    }
    db = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    rows = [
        row
        for row in db.execute(
            "SELECT doc_sha256, page, text FROM pages ORDER BY doc_sha256, page"
        )
        if row[2].strip()
    ]
    db.close()
    embedder = document_embedder(args.model)
    cache = EmbeddingCache(INDEX_DIR / "embedding-cache.sqlite", embedder.model)
    try:
        vectors = cache.embed(
            embedder, [Passage(titles.get(sha, ""), text) for sha, _, text in rows]
        )
    finally:
        cache.close()
    slug = args.model.replace("/", "__")
    out = INDEX_DIR / "page-text" / f"{slug}.sqlite"
    out.unlink(missing_ok=True)
    target = sqlite3.connect(out)
    target.execute(
        "CREATE TABLE pages (doc_sha256 TEXT NOT NULL, page INTEGER NOT NULL, vector BLOB NOT NULL, PRIMARY KEY (doc_sha256, page))"
    )
    target.executemany(
        "INSERT INTO pages VALUES (?, ?, ?)",
        [
            (sha, page, vector)
            for (sha, page, _), vector in zip(rows, vectors, strict=True)
        ],
    )
    target.commit()
    target.close()
    out.with_suffix(".json").write_text(
        json.dumps({"model": args.model, "pages": len(rows)}), encoding="utf-8"
    )
    print(f"{len(rows)} page vectors -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
