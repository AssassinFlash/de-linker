"""Unreadable text detection and automatic retry of incomplete parser caches."""

import gzip
import json
from concurrent.futures import Future
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from docling_core.types.doc.document import DoclingDocument

from index import inventory, parse
from index.parse import ParseStatus, garbled_pages

# The text layer of the OCEAN 2 single-phase datasheet, p.2 (PDFium, 2026-10-09).
GARBLED = (
    'EcoFlow OCEAN 2 Hybrid Inverter Single-Phase\r\n!"\r\n!"#$%&#\'()*\'+\',"-"+.\r\n'
    "!\"#$%&#'()/'+',\"-\"+. 01)234*54\r\n67489\r\n01)234*54\r\n67:;489\r\n3?)@%/A￾B*CD\r\n"
    "!\"#$%&%'()'(*+,-'./0 1222 1342 52322 55222 55222 56222"
)
# Readable pages with the most punctuation in the corpus: a table of contents with dot
# leaders and a harmonics table of numbers.
CONTENTS = (
    "Contents\r\n1. Safety instructions"
    + "." * 120
    + " 3\r\n2. Installation"
    + "." * 120
    + " 9"
)
NUMBERS = "Seite 5 von 7\r\n16 0,008 0,006 0,006 0,007 0,004 0,004\r\n17 0,072 0,041 0,132 0,193 (A) [%]"


def test_a_garbled_text_layer_is_detected_by_page_number() -> None:
    assert garbled_pages([CONTENTS, GARBLED, NUMBERS]) == [2]


def test_readable_and_empty_pages_are_not_flagged() -> None:
    assert garbled_pages([CONTENTS, NUMBERS, "", "   "]) == []


SHA = "1b7e18cd26ff29b57f8cc5cc827249d56624a6c1a048588d5ec5c80080538663"
FIXTURE = Path(__file__).parent / "fixtures/parsed" / SHA


def successful_cache(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with gzip.open(FIXTURE / "docling.json.gz", "rb") as source:
        (directory / "docling.json").write_bytes(source.read())
    status = ParseStatus(
        SHA, "docling fixture", "success", 2, parser_revision=parse.parser_revision()
    )
    (directory / "status.json").write_text(json.dumps(asdict(status)))


@pytest.mark.parametrize(
    "defect",
    [
        "failed",
        "partial_success",
        "missing",
        "corrupt",
        "page_count",
        "ocr_missing",
        "status_corrupt",
        "wrong_sha",
    ],
)
def test_failed_or_incomplete_cache_is_not_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    directory = tmp_path / SHA
    successful_cache(directory)
    monkeypatch.setattr(parse, "docling_version", lambda: "docling fixture")
    assert parse.cached_status(directory) is not None
    status = json.loads((directory / "status.json").read_text())
    if defect in {"failed", "partial_success"}:
        status["status"] = defect
    elif defect == "missing":
        (directory / "docling.json").unlink()
    elif defect == "corrupt":
        (directory / "docling.json").write_text("{broken")
    elif defect == "page_count":
        status["pages"] = 3
    elif defect == "ocr_missing":
        status["garbled_pages"] = [2]
    elif defect == "wrong_sha":
        status["sha256"] = "wrong-source"
    if defect == "status_corrupt":
        (directory / "status.json").write_text("{broken")
    else:
        (directory / "status.json").write_text(json.dumps(status))
    assert parse.cached_status(directory) is None


def test_next_run_retries_same_pdf_after_transient_failure_then_reuses_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pypdfium2

    pdf_dir, parsed_dir = tmp_path / "pdf", tmp_path / "parsed"
    pdf_dir.mkdir()
    pdf = pdf_dir / f"{SHA}.pdf"
    pdf.write_bytes(b"same original PDF bytes throughout both timer invocations")
    document = inventory.Document(
        SHA,
        pdf.stat().st_size,
        ["https://site.test/manual.pdf"],
        [],
        "Manual",
        "Handbuch",
        [],
        [],
        [1],
        "manual",
        "en",
    )
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(
        json.dumps(
            {"source_revision": "same-woo-source", "documents": [asdict(document)]}
        )
    )
    original_inventory, original_pdf = inventory_path.read_bytes(), pdf.read_bytes()
    with gzip.open(FIXTURE / "docling.json.gz", "rb") as source:
        converted = DoclingDocument.model_validate_json(source.read())

    class Converter:
        calls = 0

        def convert(self, *args: Any, **kwargs: Any) -> Any:
            self.calls += 1
            if self.calls == 1:
                raise OSError("temporary converter failure")
            return SimpleNamespace(
                errors=[], status=SimpleNamespace(value="success"), document=converted
            )

    class Pdf:
        def close(self) -> None:
            pass

    class InlinePool:
        def __init__(self, *, max_workers: int, initializer: Any) -> None:
            self.initializer, self.initialized = initializer, False

        def __enter__(self) -> "InlinePool":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def submit(self, function: Any, *args: Any) -> Future[Any]:
            if not self.initialized:
                self.initializer()
                self.initialized = True
            future: Future[Any] = Future()
            try:
                future.set_result(function(*args))
            except Exception as error:
                future.set_exception(error)
            return future

    converter = Converter()
    monkeypatch.setattr(parse, "_WORKER", None)
    monkeypatch.setattr(parse, "ProcessPoolExecutor", InlinePool)
    monkeypatch.setattr(parse, "docling_version", lambda: "docling fixture")
    monkeypatch.setattr(parse, "_converter", lambda: converter)
    monkeypatch.setattr(parse, "_page_texts", lambda path: ["page one", "page two"])
    monkeypatch.setattr(pypdfium2, "PdfDocument", lambda path: Pdf())
    assert parse.run(inventory_path, pdf_dir, parsed_dir, 1)[0].status == "failed"
    assert parse.run(inventory_path, pdf_dir, parsed_dir, 1)[0].status == "success"
    assert converter.calls == 2
    assert parse.run(inventory_path, pdf_dir, parsed_dir, 1)[0].status == "success"
    assert converter.calls == 2
    assert inventory_path.read_bytes() == original_inventory
    assert pdf.read_bytes() == original_pdf


@pytest.mark.parametrize(
    "failure", ["partial_success", "errors", "two_pages", "main_errors"]
)
def test_partial_or_erroneous_ocr_retries_and_never_becomes_successful_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    import pypdfium2

    directory = tmp_path / SHA
    pdf = tmp_path / f"{SHA}.pdf"
    pdf.write_bytes(b"unchanged original PDF")
    with gzip.open(FIXTURE / "docling.json.gz", "rb") as source:
        main = DoclingDocument.model_validate_json(source.read())
    ocr_fixture = (
        FIXTURE.parent
        / "b296b6142e93eedb93fd4595a42be69da999fdeb1ab394d4c64307ca879beaed"
        / "ocr-p2.json.gz"
    )
    with gzip.open(ocr_fixture, "rb") as source:
        one_page = DoclingDocument.model_validate_json(source.read())
    assert set(one_page.pages) == {1}

    class Converter:
        failed_attempt = True
        calls = 0

        def convert(self, path: str, **kwargs: Any) -> Any:
            self.calls += 1
            is_ocr = path.endswith(".png")
            errors = []
            if self.failed_attempt and (
                (failure == "errors" and is_ocr)
                or (failure == "main_errors" and not is_ocr)
            ):
                errors = [
                    SimpleNamespace(
                        module_name="fixture",
                        error_message="transient extraction error",
                    )
                ]
            status = (
                "partial_success"
                if self.failed_attempt and is_ocr and failure == "partial_success"
                else "success"
            )
            document = (
                main
                if not is_ocr or (self.failed_attempt and failure == "two_pages")
                else one_page
            )
            return SimpleNamespace(
                document=document, errors=errors, status=SimpleNamespace(value=status)
            )

    class Pdf:
        def __getitem__(self, number: int) -> "Pdf":
            return self

        def render(self, **kwargs: Any) -> "Pdf":
            return self

        def to_pil(self) -> "Pdf":
            return self

        def save(self, path: Path) -> None:
            path.write_bytes(b"fixture rendered page")

        def close(self) -> None:
            pass

    converter = Converter()
    monkeypatch.setattr(parse, "docling_version", lambda: "docling fixture")
    monkeypatch.setattr(
        parse, "_page_texts", lambda path: ["readable page one", GARBLED]
    )
    monkeypatch.setattr(pypdfium2, "PdfDocument", lambda path: Pdf())
    first = parse.parse_one(converter, pdf, directory)
    assert first.status == "failed"
    assert first.errors
    assert parse.cached_status(directory) is None
    converter.failed_attempt = False
    second = parse.parse_one(converter, pdf, directory)
    assert second.status == "success"
    assert second.errors == []
    assert parse.cached_status(directory) == second
    assert pdf.read_bytes() == b"unchanged original PDF"


def test_parse_status_uses_import_captured_identity_not_later_disk_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / SHA
    successful_cache(directory)
    original = parse.parser_revision()
    monkeypatch.setattr(parse, "parser_revision", lambda: "later-edited-disk-source")
    monkeypatch.setattr(parse, "docling_version", lambda: "docling fixture")
    assert parse.cached_status(directory) is not None
    cached = parse.cached_status(directory)
    assert cached is not None
    assert cached.parser_revision == original

    class FailedConverter:
        def convert(self, *args: Any, **kwargs: Any) -> Any:
            raise OSError("task-owned converter failure")

    monkeypatch.setattr(parse, "_page_texts", lambda path: ["readable"])
    failed = parse.parse_one(FailedConverter(), tmp_path / f"{SHA}.pdf", directory)
    assert failed.parser_revision == original
