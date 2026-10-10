"""Page images -> gemini-embedding-2 page vectors, for the embedding bake-off.

Every page of every inventory PDF is rendered to PNG at 150 dpi and embedded with
gemini-embedding-2's multimodal input (AIHubMix's Gemini-native `embedContent`); a
query is searched against them with the same model's text vector. The vectors are
kept in `<INDEX_DIR>/page-vectors/gemini-embedding-2.sqlite`; a page already there is
not sent again (`python -m index.pages`). docs/research/2026-10-09/embedding-bakeoff.md
reports what they add over text chunks.

Rendering uses pypdfium2 (Apache-2.0, already Docling's PDF backend) rather than
PyMuPDF, which is AGPL-3.0 (docs/research/2026-10-09/knowledge-audit.md B1).
"""

from __future__ import annotations

import argparse
import base64
import http.client
import io
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from index import inventory
from index.paths import INDEX_DIR, INVENTORY_PATH, PDF_DIR
from linker_genie.embedding import GEMINI, pack

# The bake-off's page rendering (owner scope addition, 2026-10-09): PNG at 150 dpi.
RENDER_DPI = 150
# Requests in flight. Each takes about 4 s through AIHubMix (measured 2026-10-09);
# 16 at a time keeps the 11,697 pages near an hour.
WORKERS = 16
# Tries per page with exponential backoff (2, 4, 8, 16 s): rides out a dropped
# connection; the run of 2026-10-09 saw one (IncompleteRead), which the retry cleared.
ATTEMPTS = 5
PAGE_VECTORS = INDEX_DIR / "page-vectors" / f"{GEMINI}.sqlite"


def render(pdf: object, page: int) -> bytes:
    """One physical page (from 1) as PNG bytes."""
    import pypdfium2

    assert isinstance(pdf, pypdfium2.PdfDocument)
    image = pdf[page - 1].render(scale=RENDER_DPI / 72).to_pil()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class GeminiImages:
    """gemini-embedding-2 for one image per request (Gemini-native embedContent)."""

    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._url = (
            base_url.rstrip("/") + f"/gemini/v1beta/models/{GEMINI}:embedContent"
        )

    def embed(self, png: bytes) -> tuple[bytes, int]:
        """The page vector and the tokens the API counted for it."""
        body = json.dumps(
            {
                "content": {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(png).decode(),
                            }
                        }
                    ]
                }
            }
        ).encode()
        for attempt in range(ATTEMPTS):
            request = urllib.request.Request(
                self._url,
                data=body,
                headers={
                    "x-goog-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    payload = json.load(response)
                tokens = int(payload.get("usageMetadata", {}).get("totalTokenCount", 0))
                return pack(
                    [float(value) for value in payload["embedding"]["values"]]
                ), tokens
            except (
                urllib.error.URLError,
                http.client.HTTPException,
                TimeoutError,
                OSError,
                ValueError,
            ) as error:
                if attempt + 1 == ATTEMPTS:
                    raise RuntimeError(
                        f"{GEMINI} image embedding failed: {error}"
                    ) from error
                time.sleep(2 ** (attempt + 1))
        raise AssertionError("unreachable")


def open_store(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE IF NOT EXISTS pages (doc_sha256 TEXT NOT NULL, page INTEGER NOT NULL,"
        " tokens INTEGER NOT NULL, vector BLOB NOT NULL, PRIMARY KEY (doc_sha256, page))"
    )
    return db


def run(
    inventory_path: Path, pdf_dir: Path, store: Path, client: GeminiImages, workers: int
) -> None:
    import pypdfium2

    db = open_store(store)
    done = set(db.execute("SELECT doc_sha256, page FROM pages"))
    documents = inventory.load(inventory_path)
    started = time.monotonic()
    sent = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending: list[tuple[str, int, Future[tuple[bytes, int]]]] = []

        def drain(limit: int) -> None:
            nonlocal sent
            while len(pending) > limit:
                sha, page, future = pending.pop(0)
                try:
                    vector, tokens = future.result()
                except RuntimeError as error:
                    # Left out of the store: the next run sends this page again.
                    print(f"page {sha[:12]} p.{page}: {error}", flush=True)
                    continue
                db.execute(
                    "INSERT OR REPLACE INTO pages VALUES (?, ?, ?, ?)",
                    (sha, page, tokens, vector),
                )
                sent += 1
                if sent % 200 == 0:
                    db.commit()
                    rate = sent / (time.monotonic() - started)
                    print(f"{sent} pages embedded ({rate:.1f}/s)", flush=True)

        for document in documents:
            try:
                pdf = pypdfium2.PdfDocument(str(pdf_dir / f"{document.sha256}.pdf"))
            except pypdfium2.PdfiumError as error:
                print(f"skip {document.sha256[:12]}: {error}", flush=True)
                continue
            try:
                for page in range(1, len(pdf) + 1):
                    if (document.sha256, page) in done:
                        continue
                    pending.append(
                        (
                            document.sha256,
                            page,
                            pool.submit(client.embed, render(pdf, page)),
                        )
                    )
                    drain(workers * 2)
            finally:
                pdf.close()
        drain(0)
    db.commit()
    total = db.execute("SELECT count(*), sum(tokens) FROM pages").fetchone()
    print(f"{total[0]} page vectors, {total[1]} tokens -> {store}", flush=True)
    db.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Embed every page image with gemini-embedding-2."
    )
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(argv)
    key = os.environ.get("AIHUBMIX_API_KEY", "")
    base = os.environ.get("AIHUBMIX_BASE_URL", "")
    if not key or not base:
        raise SystemExit("AIHUBMIX_API_KEY and AIHUBMIX_BASE_URL must be set")
    run(INVENTORY_PATH, PDF_DIR, PAGE_VECTORS, GeminiImages(key, base), args.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
