"""A cover anchor must be supported by text actually visible on the PDF page."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pypdfium2
import pypdfium2.raw as pdfium
import pytest

from index.extract import pdf_series_cover

LINE = "ESA Series Residential Energy Storage System I 3-10kW / 5-108kWh"


def _pdf(tmp_path: Path, commands: str, page_attributes: bytes = b"") -> Path:
    stream = commands.encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 808] "
        + page_attributes
        + b" "
        b"/Resources << /Font << /F1 4 0 R >> "
        b"/ExtGState << /Zero << /Type /ExtGState /ca 0 /CA 0 >> >> >> "
        b"/Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    )
    path = tmp_path / f"{hashlib.sha256(data).hexdigest()}.pdf"
    path.write_bytes(data)
    return path


def _text(state: str = "") -> str:
    return f"BT /F1 12 Tf 40 40 Td {state} ({LINE}) Tj ET"


def test_same_text_layer_is_accepted_only_when_rendered(tmp_path: Path) -> None:
    path = _pdf(tmp_path, _text())
    visible = pdf_series_cover(path)
    assert visible is not None and visible["text"] == LINE
    assert visible["source_sha256"] == path.stem
    assert visible["source_page"] == 1
    assert visible["page_size"] == [595, 808]
    assert visible["line_end"] - visible["line_start"] == len(LINE)
    assert visible["family"]["text"] == "ESA Series"
    assert visible["power"]["text"] == "3-10kW"
    assert pdf_series_cover(_pdf(tmp_path, _text("3 Tr"))) is None


def test_white_letters_on_a_dark_background_are_visible(tmp_path: Path) -> None:
    commands = "0.65 0 0 rg 30 30 500 20 re f\n" + _text("1 1 1 rg")
    cover = pdf_series_cover(_pdf(tmp_path, commands))
    assert cover is not None and cover["text"] == LINE


def test_physical_page_bounds_and_rotation_are_respected(tmp_path: Path) -> None:
    cropped = _pdf(tmp_path, _text(), b"/CropBox [20 20 500 700]")
    cover = pdf_series_cover(cropped)
    assert cover is not None and cover["page_size"] == [480, 680]
    assert pdf_series_cover(_pdf(tmp_path, _text(), b"/Rotate 90")) is None
    off_page = _text().replace("40 40 Td", "-5 40 Td")
    assert pdf_series_cover(_pdf(tmp_path, off_page)) is None


@pytest.mark.parametrize(
    "commands",
    [
        _text("/Zero gs"),  # Transparent text.
        _text("1 1 1 rg"),  # White text on white page.
        _text("0.95 0.95 0.95 rg"),  # Insufficient contrast on white.
        "q 0 0 10 10 re W n " + _text() + " Q",  # Clipped out.
        "q 40 30 170 20 re W n " + _text() + " Q",  # Partly clipped.
        _text() + "\n1 1 1 rg 30 30 500 20 re f",  # Covered afterwards.
        _text() + "\n1 1 1 rg 47 35 9 12 re f",  # One glyph covered.
        # Only the product-family letters are hidden.
        "BT /F1 12 Tf 40 40 Td 3 Tr (ESA Series) Tj 0 Tr "
        "( Residential Energy Storage System I 3-10kW / 5-108kWh) Tj ET",
        # Only the power-range characters are hidden.
        "BT /F1 12 Tf 40 40 Td "
        "(ESA Series Residential Energy Storage System I ) Tj 3 Tr "
        "(3-10kW) Tj 0 Tr ( / 5-108kWh) Tj ET",
        # The family and power are visible, but the intervening title is not.
        "BT /F1 12 Tf 40 40 Td (ESA Series ) Tj 3 Tr "
        "(Residential Energy Storage System I ) Tj 0 Tr "
        "(3-10kW / 5-108kWh) Tj ET",
    ],
    ids=[
        "transparent",
        "white-on-white",
        "low-contrast",
        "clipped",
        "partly-clipped",
        "covered",
        "single-glyph-covered",
        "family",
        "power",
        "title",
    ],
)
def test_invisible_or_partly_invisible_line_is_not_an_anchor(
    tmp_path: Path, commands: str
) -> None:
    assert pdf_series_cover(_pdf(tmp_path, commands)) is None


@pytest.mark.parametrize(
    ("function", "result"),
    [
        ("FPDFPage_GetAnnotCount", -1),
        ("FPDFPage_GetAnnotCount", 1),
        ("FPDFText_GetUnicode", 0),
        ("FPDFText_IsGenerated", -1),
        ("FPDFText_GetTextObject", None),
        ("FPDFTextObj_GetTextRenderMode", -1),
        ("FPDFPageObj_GetIsActive", 0),
        ("FPDFPageObj_GetClipPath", None),
        ("FPDFClipPath_CountPaths", -2),
        ("FPDFPageObj_GetBounds", 0),
        ("FPDFTextObj_GetRenderedBitmap", None),
        ("FPDFPageObj_SetIsActive", 0),
    ],
)
def test_unknown_pdfium_state_does_not_produce_an_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, function: str, result: int | None
) -> None:
    path = _pdf(tmp_path, _text())
    monkeypatch.setattr(pdfium, function, lambda *_: result)
    assert pdf_series_cover(path) is None


def test_render_failure_does_not_produce_an_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _pdf(tmp_path, _text())

    def fail(*_: object, **__: object) -> None:
        raise RuntimeError("render unavailable")

    monkeypatch.setattr(pypdfium2.PdfPage, "render", fail)
    assert pdf_series_cover(path) is None


def test_render_failure_restores_the_disabled_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _pdf(tmp_path, _text())
    render = pypdfium2.PdfPage.render
    set_active = pdfium.FPDFPageObj_SetIsActive
    calls: list[bool] = []
    render_calls = 0

    def fail_second_render(page: object, *args: object, **kwargs: object) -> object:
        nonlocal render_calls
        render_calls += 1
        if render_calls == 2:
            raise RuntimeError("render unavailable")
        return render(page, *args, **kwargs)

    def record_set_active(obj: object, active: bool) -> int:
        calls.append(active)
        return set_active(obj, active)

    monkeypatch.setattr(pypdfium2.PdfPage, "render", fail_second_render)
    monkeypatch.setattr(pdfium, "FPDFPageObj_SetIsActive", record_set_active)
    assert pdf_series_cover(path) is None
    assert calls == [False, True]
