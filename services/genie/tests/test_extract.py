"""Page blocks from real Docling output (tests/fixtures/parsed, parsed with index.parse)."""

import gzip
import hashlib
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from index.extract import Block, Page, clean, enrich_model_axes, extract
from linker_genie.table_projection import SourceCell, model_axis, render_projection

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


@pytest.mark.parametrize(
    ("neighbour_suffix", "mismatched_row", "complete_header"),
    [
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (False, True, True),
    ],
)
def test_wrapped_pdf_model_needs_its_own_physical_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    neighbour_suffix: bool,
    mismatched_row: bool,
    complete_header: bool,
) -> None:
    # ESA p.2's PDFium U+FFFE joins two visible lines; Docling splits the
    # first model's suffix into the next native cell. Reading order alone
    # cannot distinguish this from a suffix physically in the next column.
    raw = "GW5K￾ETA-G20\r\nGW6K￾ETA-G20\r\n"
    body_boxes = {}
    for bottom, parts in [
        (73.0, [("Max. Input Power (kW)", 40.0), ("10", 190.0), ("12", 224.0)]),
        (
            60.0,
            [
                ("Max. Continuous Charging Current (A)", 40.0),
                ("6.7", 190.0),
                ("8.1", 224.0),
            ],
        ),
        (
            51.0,
            [
                ("Max. Continuous Discharging Current (A)", 40.0),
                ("7.4", 190.0),
                ("8.9", 224.0),
            ],
        ),
        (42.0, [("Max. Charging Power (kW)", 40.0), ("5.0", 190.0), ("6.0", 224.0)]),
    ]:
        for text, left in parts:
            glyph_bottom = (
                bottom - 9.0 if mismatched_row and text in {"10", "12"} else bottom
            )
            for offset, char in enumerate(text):
                body_boxes[len(raw)] = (
                    left + offset * 2.0,
                    glyph_bottom,
                    left + (offset + 1) * 2.0,
                    glyph_bottom + 7.0,
                )
                raw += char
            raw += " "
        raw += "\r\n"

    def charbox(index: int) -> tuple[float, float, float, float]:
        if index >= 28:
            return body_boxes.get(index, (0.0, 0.0, 0.0, 0.0))
        model, offset = divmod(index, 14)
        left = 182.0 + model * 34.0
        if offset < 5:
            return left + 2.6 + offset * 4.4, 105.0, left + 6.6 + offset * 4.4, 112.0
        if neighbour_suffix and model == 0:
            left += 34.0
        return left + (offset - 5) * 3.9, 96.0, left + (offset - 4) * 3.9, 103.0

    text_page = MagicMock()
    text_page.get_text_range.return_value = raw
    text_page.count_chars.return_value = len(raw)
    text_page.get_charbox.side_effect = charbox
    page = MagicMock()
    page.get_rotation.return_value = 0
    page.get_bbox.return_value = (0.0, 0.0, 595.0, 200.0)
    page.get_textpage.return_value = text_page
    document = MagicMock()
    document.__getitem__.return_value = page
    monkeypatch.setattr("pypdfium2.PdfDocument", lambda _path: document)
    content = b"physical model-axis fixture"
    pdf = tmp_path / f"{hashlib.sha256(content).hexdigest()}.pdf"
    pdf.write_bytes(content)
    cells = tuple(
        SourceCell(
            row_start=row,
            row_end=row + 1,
            col_start=col,
            col_end=col + 1,
            # Native Docling may already spell the model in full even though
            # its PDF proof is newly recovered from a physical U+FFFE wrap.
            text=("GW5K-ETA-G20" if col == 1 else "GW6K-ETA-G20")
            if complete_header and row == 0 and col > 0
            else text,
            column_header=row == 0,
            row_header=False,
            row_section=False,
            # A parser's identical large boxes cannot turn adjacent physical
            # label/value lines into one correctly paired parameter row.
            bbox=(box[0], 120.0, box[2], 136.0) if mismatched_row and row == 1 else box,
            bbox_origin="TOPLEFT",
        )
        for row, col, text, box in [
            (0, 0, "Technical Data", (40.0, 88.0, 140.0, 105.0)),
            (0, 1, "GW5K-", (167.0, 87.0, 219.0, 105.0)),
            (0, 2, "ETA-G20 GW6K- ETA-G20", (185.0, 88.0, 237.0, 106.0)),
            (1, 0, "Max. Input Power (kW)", (40.0, 120.0, 140.0, 127.0)),
            (1, 1, "10", (190.0, 120.0, 200.0, 127.0)),
            (1, 2, "12", (224.0, 120.0, 234.0, 127.0)),
            (
                2,
                0,
                "Max. Continuous Charging Current (A) Max. Continuous Discharging Current (A)",
                (40.0, 133.0, 180.0, 149.0),
            ),
            (2, 1, "6.7", (190.0, 133.0, 200.0, 140.0)),
            (2, 2, "8.1 8.9", (224.0, 133.0, 234.0, 149.0)),
            (3, 0, "Max. Charging Power (kW)", (40.0, 151.0, 140.0, 158.0)),
            (3, 1, "7.4 5.0", (190.0, 142.0, 200.0, 158.0)),
            (3, 2, "6.0", (224.0, 151.0, 234.0, 158.0)),
        ]
    )
    block = Block("table", source_cells=cells)

    enriched = enrich_model_axes([Page(2, "docling", [block])], pdf)[0].blocks[0]

    assert block.source_cells == cells
    assert enriched.rows == block.rows
    if neighbour_suffix:
        assert model_axis(enriched.source_cells) is None
    else:
        assert model_axis(enriched.source_cells) == ["GW5K-ETA-G20", "GW6K-ETA-G20"]
        if mismatched_row:
            assert render_projection(enriched.source_cells, 1, [1]) is None
            assert render_projection(enriched.source_cells, 2, [1]) is None
        else:
            assert render_projection(enriched.source_cells, 1, [1]) == (
                "| Technical Data | GW5K-ETA-G20 |\n| Max. Input Power (kW) | 10 |"
            )
            assert render_projection(enriched.source_cells, 2, [1]) == (
                "| Technical Data | GW6K-ETA-G20 |\n| Max. Input Power (kW) | 12 |"
            )
        assert render_projection(enriched.source_cells, 1, [2]) is None
        assert render_projection(enriched.source_cells, 2, [2]) is None
        assert render_projection(enriched.source_cells, 1, [3]) is None
        span = enriched.source_cells[1]["model_spans"][0]
        assert span["char_start"] == 0 and span["char_end"] == 12
        assert span["page"] == 2 and span["source_sha256"] == pdf.stem
