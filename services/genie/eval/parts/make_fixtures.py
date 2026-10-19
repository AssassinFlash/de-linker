"""The parts-list fixtures of ticket #251, regenerated with `uv run python`.

- `list.xlsx`: the 20-row acceptance list as an Excel workbook (first sheet,
  shared strings), what a customer exports from a spreadsheet.
- `list-handwritten.png`: six lines of the same range, written in a handwriting
  font (Bradley Hand Bold, macOS) on a white page, what a customer photographs.

No third-party data: both files are generated here. Run from this directory:

    uv run --locked python make_fixtures.py
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

ROWS = [
    ("SAJ H2-10K-T3", "2"),
    ("S.A.J. H2-12K-T3", "1"),
    ("GoodWe GW10K-ETA-G20", "3"),
    ("SAJ H2-15K-T3", "2"),
    ("SAJ H2-20K T3", "1"),
    ("GoodWe GW5.1-BAT-D-G21", "4"),
    ("SAJ B2-10.0-HV1", "2"),
    ("EcoFlow EF BD-8-S2", "1"),
    ("EcoFlow EF BD-5-S2", "2"),
    ("GoodWe GM330", "10"),
    ("Chint DTSU666", "1"),
    ("Pylontech L260-OMNI", "2"),
    ("GoodWe GW7K-HCA-20", "1"),
    ("SAJ eSolar AIO3", "3"),
    ("SAJ BC2-HV1", "1"),
    ("SAJ BU2-5.0-HV1", "2"),
    ("GoodWe HCA", "2"),
    ("SAJ H2", "4"),
    ("SMA Sunny Boy 5.0", "2"),
    ("Fronius Symo 10", "1"),
]

HANDWRITTEN = [
    "2x SAJ H2-10K-T3",
    "1 x GoodWe GW10K-ETA-G20",
    "3 x SAJ H2",
    "2 x SMA Sunny Boy 5.0",
    "1 x Chint DTSU666",
    "4 x GoodWe HCA",
]


def xlsx() -> None:
    shared: list[str] = []
    rows_xml = []
    for number, row in enumerate([("Item", "Qty"), *ROWS], start=1):
        cells = []
        for index, value in enumerate(row):
            shared.append(value)
            cells.append(
                f'<c r="{chr(ord("A") + index)}{number}" t="s"><v>{len(shared) - 1}</v></c>'
            )
        rows_xml.append(f'<row r="{number}">{"".join(cells)}</row>')
    files = {
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Liste" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/></Relationships>'
        ),
        "xl/sharedStrings.xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            + "".join(f"<si><t>{value}</t></si>" for value in shared)
            + "</sst>"
        ),
        "xl/worksheets/sheet1.xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{''.join(rows_xml)}</sheetData></worksheet>"
        ),
    }
    with zipfile.ZipFile(HERE / "list.xlsx", "w", zipfile.ZIP_DEFLATED) as book:
        for name, content in files.items():
            book.writestr(name, content)


def handwritten() -> None:
    font = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf", 48
    )
    image = Image.new("RGB", (1400, 900), "white")
    draw = ImageDraw.Draw(image)
    for number, line in enumerate(HANDWRITTEN):
        draw.text((80, 60 + number * 120), line, font=font, fill=(20, 30, 70))
    image.save(HERE / "list-handwritten.png", "PNG")


if __name__ == "__main__":
    xlsx()
    handwritten()
    print("wrote list.xlsx and list-handwritten.png")
