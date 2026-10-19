"""The parts-list workbooks are real zip packages, including the hostile ones."""

from __future__ import annotations

import io
import zipfile

import xlsxgen


def _sheet(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        return book.read("xl/worksheets/sheet1.xml").decode("utf-8")


def test_normal_workbook_is_a_zip_of_the_sheet_parts() -> None:
    name, data = xlsxgen.build("normal")
    assert name == "parts.xlsx"
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        names = set(book.namelist())
    assert "[Content_Types].xml" in names
    assert "xl/worksheets/sheet1.xml" in names
    assert "xl/sharedStrings.xml" in names
    assert _sheet(data).count("<row ") == 4


def test_empty_workbook_has_the_header_row_only() -> None:
    _name, data = xlsxgen.build("empty")
    assert _sheet(data).count("<row ") == 1


def test_zip_bomb_decompresses_past_eight_mib() -> None:
    _name, data = xlsxgen.build("zip_bomb")
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        sheet = book.read("xl/worksheets/sheet1.xml")
    assert len(sheet) > 8 * 1024 * 1024


def test_billion_laughs_declares_a_doctype() -> None:
    _name, data = xlsxgen.build("billion_laughs")
    assert "<!DOCTYPE" in _sheet(data)
