"""The .xlsx probes of the parts-list boundary cases (stdlib only).

Minimal Office Open XML workbooks: what parts._xlsx_rows reads (workbook,
first-sheet relationship, shared strings, inline strings). The two hostile
shapes regress the reader's own ceilings: a sheet entry that decompresses past
MAX_XLSX_ENTRY (8 MiB) and an XML entity declaration ("billion laughs"),
which _xml refuses before parsing.
"""

from __future__ import annotations

import io
import zipfile

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _column_letters(number: int) -> str:
    """1 -> A, 27 -> AA: the column half of an A1 cell reference."""
    letters = ""
    while number:
        number, rest = divmod(number - 1, 26)
        letters = chr(ord("A") + rest) + letters
    return letters


def workbook(
    rows: list[list[str]], huge_sheet: str | None = None, doctype: str | None = None
) -> bytes:
    """A one-sheet workbook of string cells; `huge_sheet`/`doctype` replace the
    sheet part with the hostile forms."""
    shared: list[str] = []
    index_of: dict[str, int] = {}
    sheet_rows: list[str] = []
    for row_number, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column, value in enumerate(row, start=1):
            if value not in index_of:
                index_of[value] = len(shared)
                shared.append(value)
            reference = f"{_column_letters(column)}{row_number}"
            cells.append(f'<c r="{reference}" t="s"><v>{index_of[value]}</v></c>')
        sheet_rows.append(f'<row r="{row_number}">' + "".join(cells) + "</row>")
    sheet = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<worksheet xmlns="{_NS_MAIN}"><sheetData>'
        + "".join(sheet_rows)
        + "</sheetData></worksheet>"
    )
    if huge_sheet is not None:
        sheet = huge_sheet
    if doctype is not None:
        sheet = doctype
    strings = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<sst xmlns="{_NS_MAIN}" count="{len(shared)}" uniqueCount="{len(shared)}">'
        + "".join(f"<si><t>{_escape(value)}</t></si>" for value in shared)
        + "</sst>"
    )
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Types "
            'xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
            'package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
            'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.'
            'openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<Relationships xmlns="{_NS_PKG}">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<workbook xmlns="{_NS_MAIN}" xmlns:r="{_NS_REL}">'
            "<sheets>"
            f'<sheet name="Sheet1" sheetId="1" r:id="rId1"/>'
            "</sheets></workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<Relationships xmlns="{_NS_PKG}">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/sharedStrings" '
            'Target="sharedStrings.xml"/>'
            "</Relationships>"
        ),
        "xl/worksheets/sheet1.xml": sheet,
        "xl/sharedStrings.xml": strings,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as book:
        for name, data in parts.items():
            book.writestr(name, data)
    return buffer.getvalue()


def build(kind: str) -> tuple[str, bytes]:
    """The probe named by a case's `file`: its file name and bytes."""
    if kind == "normal":
        rows = [
            ["Model", "Qty"],
            ["H2-10K-T3", "2"],
            ["GW5K-ETA-G20", "1"],
            ["B2-5.0-HV1", "4"],
        ]
        return ("parts.xlsx", workbook(rows))
    if kind == "normal_de":
        rows = [
            ["Modell", "Anzahl"],
            ["H2-10K-T3", "2"],
            ["GW5K-ETA-G20", "1"],
            ["B2-5.0-HV1", "4"],
        ]
        return ("stueckliste.xlsx", workbook(rows))
    if kind == "empty":
        rows = [["Model", "Qty"]]
        return ("empty.xlsx", workbook(rows))
    if kind == "duplicates":
        rows = [
            ["Model", "Qty"],
            ["H2-10K-T3", "1"],
            ["H2-10K-T3", "1"],
            ["H2-10K-T3", "1"],
        ]
        return ("duplicates.xlsx", workbook(rows))
    if kind == "long_rows":
        filler = "overflow note: " + "x" * 400
        rows = [
            ["Model", "Qty", "Note"],
            ["H2-10K-T3", "2", filler],
            ["GW5K-ETA-G20", "1", filler],
        ]
        return ("long-rows.xlsx", workbook(rows))
    if kind == "many_rows":
        rows = [["Model", "Qty"]]
        models = ["GW3K-EHA-G20", "GW5K-EHA-G20", "H2-10K-T3", "B2-5.0-HV1"]
        for index in range(250):
            rows.append([models[index % len(models)], "1"])
        return ("many-rows.xlsx", workbook(rows))
    if kind == "zip_bomb":
        # ~10 MiB of decompressed repetitive sheet in a tiny archive; the
        # reader's 8 MiB streamed-read ceiling must refuse it.
        huge = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<worksheet xmlns="{_NS_MAIN}"><sheetData>'
            + (
                '<row r="1"><c t="inlineStr"><is><t>H2-10K-T3 padding padding '
                "padding padding padding padding padding</t></is></c></row>" * 90000
            )
            + "</sheetData></worksheet>"
        )
        assert len(huge) > 8 * 1024 * 1024, len(huge)
        return ("bomb.xlsx", workbook([["Model"]], huge_sheet=huge))
    if kind == "billion_laughs":
        evil = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<!DOCTYPE worksheet [<!ENTITY x0 "HA">'
            '<!ENTITY x1 "&x0;&x0;&x0;&x0;&x0;&x0;&x0;&x0;&x0;&x0;">'
            '<!ENTITY x2 "&x1;&x1;&x1;&x1;&x1;&x1;&x1;&x1;&x1;&x1;">]>'
            f'<worksheet xmlns="{_NS_MAIN}"><sheetData>'
            '<row r="1"><c t="inlineStr"><is><t>H2-10K-T3 &x2;</t></is></c></row>'
            "</sheetData></worksheet>"
        )
        return ("laughs.xlsx", workbook([["Model"]], doctype=evil))
    raise ValueError(f"unknown probe {kind}")
