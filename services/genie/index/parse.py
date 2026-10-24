"""Parse: each inventory PDF through Docling, cached by sha256 (`python -m index.parse`).

For every document the cache holds `<sha256>/docling.json` (the DoclingDocument),
`ocr-p<N>.json` for each page whose text layer is unreadable (rendered and OCRed
instead, see `garbled_pages`) and `status.json`. A document whose status records the
current successful parser recipe and complete outputs is not parsed again.
Failed or incomplete output is retried automatically on the next run. Extraction into page blocks is
`index.extract`; this module only runs the converter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import tempfile
import time
import traceback
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

from index import inventory
from index.paths import INVENTORY_PATH, PARSED_DIR, PDF_DIR

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter

# Characters that make up an unreadable text layer: a font without a usable Unicode
# map extracts as runs like `!"#$%&'()*+,-./0`. Full stop, comma and hyphen are left
# out because dot leaders and number formats use them heavily.
SYMBOLS = frozenset("!\"#$%&'()*+/:;<=>?@[\\]^_`{|}~")
# Measured 2026-10-09 over all 11,697 pages of the 383 documents: the two unreadable
# pages (the OCEAN 2 single-phase specification table, datasheet p.2 and brochure p.3)
# have a symbol share of 0.39; the highest share of any readable page is 0.16. The cut
# sits in that gap.
GARBLED_SYMBOL_SHARE = 0.25
# Render scale for re-OCRing an unreadable page (4.0 = 288 dpi). On the one
# unreadable table, scale 2.0 lost the model codes in the column headers that 4.0
# recovered (2026-10-09).
GARBLED_RENDER_SCALE = 4.0
# Worker processes, Docling threads in each, and the pages Docling queues between its
# stages. Measured on the build Mac (Apple M3 Pro, 11 cores, 18 GB) on 2026-10-09: with
# Docling's default queue of 100 pages, three workers grew to 8-10 GB each and swapped;
# with a queue of 4-8 one worker peaks at 4.1-4.8 GB and converts 0.67-0.74 pages/s,
# so two workers fit in memory and use the cores.
WORKERS = 2
THREADS_PER_WORKER = 4
QUEUE_MAX_SIZE = 4


@dataclass
class ParseStatus:
    """What happened to one document."""

    sha256: str
    docling: str
    status: str
    pages: int
    garbled_pages: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    seconds: float = 0.0
    parser_revision: str = ""


def docling_version() -> str:
    """The parser identity recorded with every cached parse."""
    return f"docling {version('docling')}"


def parser_revision() -> str:
    """Actual converter implementation and locked dependencies, independent of Woo."""
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in (Path(__file__).resolve(), root / "pyproject.toml", root / "uv.lock"):
        name, content = path.relative_to(root).as_posix().encode(), path.read_bytes()
        digest.update(len(name).to_bytes(8, "big") + name)
        digest.update(len(content).to_bytes(8, "big") + content)
    return digest.hexdigest()


def garbled_pages(page_texts: Sequence[str]) -> list[int]:
    """Physical page numbers (from 1) whose text layer is unreadable."""
    pages = []
    for number, text in enumerate(page_texts, start=1):
        chars = [char for char in text if not char.isspace()]
        if not chars:
            continue
        if sum(char in SYMBOLS for char in chars) / len(chars) >= GARBLED_SYMBOL_SHARE:
            pages.append(number)
    return pages


def _page_texts(pdf_path: Path) -> list[str]:
    import pypdfium2

    pdf = pypdfium2.PdfDocument(str(pdf_path))
    try:
        return [pdf[index].get_textpage().get_text_range() for index in range(len(pdf))]
    finally:
        pdf.close()


def _converter() -> DocumentConverter:
    from docling.datamodel.accelerator_options import AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import (
        DocumentConverter,
        ImageFormatOption,
        PdfFormatOption,
    )

    options = PdfPipelineOptions()
    options.accelerator_options = AcceleratorOptions(
        num_threads=THREADS_PER_WORKER, device="auto"
    )
    options.queue_max_size = QUEUE_MAX_SIZE
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.IMAGE],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=options),
            InputFormat.IMAGE: ImageFormatOption(pipeline_options=options),
        },
    )


def _write_json(path: Path, payload: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, suffix=".part", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(payload)
    Path(handle.name).replace(path)


def parse_one(
    converter: DocumentConverter, pdf_path: Path, out_dir: Path
) -> ParseStatus:
    """Convert one PDF into `out_dir`; never raises, failures go into the status."""
    import pypdfium2

    sha = pdf_path.stem
    started = time.monotonic()
    out_dir.mkdir(parents=True, exist_ok=True)
    status = ParseStatus(
        sha256=sha,
        docling=docling_version(),
        status="failed",
        pages=0,
        parser_revision=parser_revision(),
    )
    try:
        # These files are rebuildable parser outputs, never original PDFs. A
        # failed retry must not expose successful-looking output from an older run.
        for path in [out_dir / "docling.json", *out_dir.glob("ocr-p*.json")]:
            path.unlink(missing_ok=True)
        texts = _page_texts(pdf_path)
        status.pages = len(texts)
        status.garbled_pages = garbled_pages(texts)
        result = converter.convert(str(pdf_path), raises_on_error=False)
        status.errors = [
            f"{error.module_name}: {error.error_message}" for error in result.errors
        ]
        status.status = str(result.status.value)
        if result.document is not None and result.document.pages:
            _write_json(out_dir / "docling.json", result.document.model_dump_json())
        pdf = pypdfium2.PdfDocument(str(pdf_path))
        try:
            for page in status.garbled_pages:
                with tempfile.TemporaryDirectory() as scratch:
                    image = Path(scratch) / f"p{page}.png"
                    pdf[page - 1].render(scale=GARBLED_RENDER_SCALE).to_pil().save(
                        image
                    )
                    ocr = converter.convert(str(image), raises_on_error=False)
                    if ocr.document is None:
                        status.status = "failed"
                        status.errors.append(
                            f"page {page}: OCR of the rendered page failed"
                        )
                        continue
                    _write_json(
                        out_dir / f"ocr-p{page}.json", ocr.document.model_dump_json()
                    )
        finally:
            pdf.close()
    except Exception as error:  # noqa: BLE001 - recorded, the run continues
        status.status = "failed"
        status.errors.append("".join(traceback.format_exception_only(error)).strip())
    status.seconds = round(time.monotonic() - started, 1)
    _write_json(out_dir / "status.json", json.dumps(asdict(status), indent=1))
    return status


_WORKER: DocumentConverter | None = None


def _init_worker() -> None:
    global _WORKER
    logging.basicConfig(level=logging.ERROR)
    _WORKER = _converter()


def _work(pdf_path: Path, out_dir: Path) -> ParseStatus:
    assert _WORKER is not None
    return parse_one(_WORKER, pdf_path, out_dir)


def read_status(out_dir: Path) -> ParseStatus | None:
    """The status a parse wrote for one document, whichever Docling wrote it."""
    path = out_dir / "status.json"
    if not path.is_file():
        return None
    try:
        return ParseStatus(**json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return None


def complete_status(out_dir: Path) -> ParseStatus | None:
    """A successful parse with complete readable artifacts, including required OCR.

    Historical parser identity is allowed here for archived corpus fixtures.
    Cache reuse adds the current implementation/dependency identity separately.
    """
    from docling_core.types.doc.document import DoclingDocument

    status = read_status(out_dir)
    if (
        status is None
        or status.status != "success"
        or status.sha256 != out_dir.name
        or type(status.pages) is not int
        or status.pages < 1
        or not isinstance(status.garbled_pages, list)
        or any(
            type(page) is not int or not 1 <= page <= status.pages
            for page in status.garbled_pages
        )
    ):
        return None
    try:
        document = DoclingDocument.model_validate_json(
            (out_dir / "docling.json").read_bytes()
        )
        if set(document.pages) != set(range(1, status.pages + 1)):
            return None
        for page in status.garbled_pages:
            ocr = DoclingDocument.model_validate_json(
                (out_dir / f"ocr-p{page}.json").read_bytes()
            )
            if set(ocr.pages) != {1}:
                return None
    except (OSError, ValueError):
        return None
    return status


def cached_status(out_dir: Path) -> ParseStatus | None:
    """Only successful complete output from the actual current parser is reusable."""
    status = complete_status(out_dir)
    return (
        status
        if status is not None
        and status.docling == docling_version()
        and status.parser_revision == parser_revision()
        else None
    )


def run(
    inventory_path: Path, pdf_dir: Path, parsed_dir: Path, workers: int
) -> list[ParseStatus]:
    """Parse every inventory document not yet cached; largest first, `workers` at once."""
    documents = sorted(inventory.load(inventory_path), key=lambda doc: -doc.bytes)
    done: list[ParseStatus] = []
    todo: list[Path] = []
    for document in documents:
        cached = cached_status(parsed_dir / document.sha256)
        if cached is not None:
            done.append(cached)
        else:
            todo.append(pdf_dir / f"{document.sha256}.pdf")
    print(f"{len(done)} cached, {len(todo)} to parse", flush=True)
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker) as pool:
        futures = [pool.submit(_work, path, parsed_dir / path.stem) for path in todo]
        for count, future in enumerate(as_completed(futures), start=1):
            status = future.result()
            done.append(status)
            elapsed = round(time.monotonic() - started)
            print(
                f"[{count}/{len(todo)} {elapsed}s] {status.sha256[:12]} {status.status} "
                f"{status.pages}p {status.seconds}s",
                flush=True,
            )
    return done


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse the inventory PDFs with Docling."
    )
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--pdf-dir", type=Path, default=PDF_DIR)
    parser.add_argument("--parsed-dir", type=Path, default=PARSED_DIR)
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(argv)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    statuses = run(args.inventory, args.pdf_dir, args.parsed_dir, args.workers)
    failed = [status for status in statuses if status.status not in ("success",)]
    print(f"{len(statuses)} documents, {len(failed)} not fully successful", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
