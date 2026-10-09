"""Page blocks from real Docling output (tests/fixtures/parsed, parsed with index.parse)."""

import gzip
import shutil
from pathlib import Path

import pytest

from index.extract import Block, clean, extract

FIXTURES = Path(__file__).parent / "fixtures" / "parsed"
STS = "1b7e18cd26ff29b57f8cc5cc827249d56624a6c1a048588d5ec5c80080538663"
OCEAN2 = "b296b6142e93eedb93fd4595a42be69da999fdeb1ab394d4c64307ca879beaed"


def unpack(sha: str, tmp_path: Path) -> Path:
    target = tmp_path / sha
    target.mkdir()
    for source in (FIXTURES / sha).iterdir():
        if source.suffix == ".gz":
            with (
                gzip.open(source, "rb") as packed,
                (target / source.stem).open("wb") as plain,
            ):
                shutil.copyfileobj(packed, plain)
        else:
            shutil.copy(source, target / source.name)
    return target


def test_every_physical_page_is_returned_in_order(tmp_path: Path) -> None:
    pages = extract(unpack(STS, tmp_path), page_count=2, garbled=[])

    assert [page.number for page in pages] == [1, 2]
    assert all(page.source == "docling" for page in pages)


def test_a_datasheet_table_keeps_its_rows_and_page(tmp_path: Path) -> None:
    pages = extract(unpack(STS, tmp_path), page_count=2, garbled=[])

    tables = [block for block in pages[1].blocks if block.kind == "table"]
    assert len(tables) == 1
    rows = tables[0].rows
    assert ("Nominal Frequency (Hz)", "50 / 60", "50 / 60") in rows
    assert all(len(row) == 3 for row in rows)


def test_headings_are_their_own_blocks(tmp_path: Path) -> None:
    pages = extract(unpack(STS, tmp_path), page_count=2, garbled=[])

    assert pages[0].blocks[0] == Block(kind="heading", text="STS Series")


def test_an_unreadable_page_takes_the_ocr_of_its_rendered_image(tmp_path: Path) -> None:
    # OCEAN 2 datasheet p.2: its text layer extracts as `!"#$%&...` (index.parse).
    pages = extract(unpack(OCEAN2, tmp_path), page_count=3, garbled=[2])

    assert [page.source for page in pages] == ["docling", "ocr", "docling"]
    table = next(block for block in pages[1].blocks if block.kind == "table")
    assert table.header_rows == 1
    assert (
        "Maximum PV Power (W)",
        "9000",
        "9680",
        "10600",
        "11000",
        "11000",
        "12000",
    ) in table.rows


def test_without_its_ocr_file_a_garbled_page_keeps_the_docling_blocks(
    tmp_path: Path,
) -> None:
    directory = unpack(OCEAN2, tmp_path)
    (directory / "ocr-p2.json").unlink()

    pages = extract(directory, page_count=3, garbled=[2])

    assert pages[1].source == "docling"


def test_a_document_without_docling_output_has_empty_pages(tmp_path: Path) -> None:
    pages = extract(tmp_path, page_count=2, garbled=[])

    assert [(page.number, page.blocks) for page in pages] == [(1, []), (2, [])]


@pytest.mark.parametrize(
    ("raw", "cleaned"),
    [
        ("  Max.\n Input   Power ", "Max. Input Power"),
        ("GW99.99K￾BTR-G10", "GW99.99K-BTR-G10"),
    ],
)
def test_clean_collapses_whitespace_and_restores_line_break_hyphens(
    raw: str, cleaned: str
) -> None:
    assert clean(raw) == cleaned
