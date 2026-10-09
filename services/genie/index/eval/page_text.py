"""Page images -> text on the Mac (Apple Vision OCR), for the bake-off's page-text variant.

Every page of every inventory PDF is rendered to PNG at the bake-off's 150 dpi (the
resolution of the gemini page images) and read with Apple Vision through ocrmac, the
OCR engine Docling uses on macOS. The text, one row per page, goes to
`<INDEX_DIR>/page-text/ocr.sqlite`; a page already there is not read again
(`python -m index.eval.page_text`). The bake-off embeds it with the same text model as
the chunks and checks what it adds on the figure questions.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from index import inventory
from index.pages import RENDER_DPI
from index.paths import INDEX_DIR, INVENTORY_PATH, PDF_DIR

STORE = INDEX_DIR / "page-text" / "ocr.sqlite"
# Worker processes: Apple Vision runs on the Neural Engine; three keep it busy while
# the CPU renders, alongside a running Docling parse (measured 2026-10-09).
WORKERS = 3


def read_document(pdf_path: Path, pages: Sequence[int]) -> list[tuple[int, str]]:
    """OCR text of the given pages of one PDF."""
    import pypdfium2
    from ocrmac import ocrmac

    pdf = pypdfium2.PdfDocument(str(pdf_path))
    try:
        out = []
        for page in pages:
            image = pdf[page - 1].render(scale=RENDER_DPI / 72).to_pil()
            lines = ocrmac.OCR(
                image,
                recognition_level="accurate",
                language_preference=["en-US", "de-DE"],
            ).recognize()
            out.append(
                (page, "\n".join(str(text) for text, _confidence, _box in lines))
            )
        return out
    finally:
        pdf.close()


def _work(job: tuple[str, str, list[int]]) -> tuple[str, list[tuple[int, str]]]:
    sha, pdf_path, pages = job
    return sha, read_document(Path(pdf_path), pages)


def run(inventory_path: Path, pdf_dir: Path, store: Path, workers: int) -> None:
    import pypdfium2

    store.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(store)
    db.execute(
        "CREATE TABLE IF NOT EXISTS pages (doc_sha256 TEXT NOT NULL, page INTEGER NOT NULL,"
        " text TEXT NOT NULL, PRIMARY KEY (doc_sha256, page))"
    )
    done = set(db.execute("SELECT doc_sha256, page FROM pages"))
    jobs = []
    for document in inventory.load(inventory_path):
        path = pdf_dir / f"{document.sha256}.pdf"
        try:
            count = len(pypdfium2.PdfDocument(str(path)))
        except pypdfium2.PdfiumError:
            continue
        todo = [
            page for page in range(1, count + 1) if (document.sha256, page) not in done
        ]
        if todo:
            jobs.append((document.sha256, str(path), todo))
    started = time.monotonic()
    pages_done = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for sha, rows in pool.map(_work, jobs):
            db.executemany(
                "INSERT OR REPLACE INTO pages VALUES (?, ?, ?)",
                [(sha, page, text) for page, text in rows],
            )
            db.commit()
            pages_done += len(rows)
            print(
                f"{pages_done} pages read ({pages_done / (time.monotonic() - started):.1f}/s)",
                flush=True,
            )
    db.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OCR every page image with Apple Vision."
    )
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(argv)
    run(INVENTORY_PATH, PDF_DIR, STORE, args.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
