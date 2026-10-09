"""The design report: one model for the screen and the PDF, in English and German."""

import io

import pytest
from pypdf import PdfReader

from linker_engine import pdf, report, residential
from linker_engine.models import Report, ResidentialInput
from linker_engine.residential import Engine

# A 2 x 1 px PNG, written by hand so the test needs no image tool.
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAIAAAB7QOjdAAAAEElEQVR4nGNgYGD4z8DAwMAAAAf/Af5gV1sAAAAASUVORK5CYII="


def build(engine: Engine, locale: str) -> Report:
    request = ResidentialInput.model_validate(
        {"plz": "80538", "annual_kwh": 5000, "pv_kwp": 10, "phase": 3, "locale": locale}
    )
    return report.residential(
        residential.design(engine, request), "2026-10-09T12:00:00Z"
    )


def text_of(document: bytes) -> str:
    return "\n".join(
        page.extract_text() for page in PdfReader(io.BytesIO(document)).pages
    )


def test_sections_follow_the_ticket(engine: Engine) -> None:
    sections = [section.id for section in build(engine, "en").sections]
    assert sections == [
        "site",
        "yield",
        "storage",
        "metrics",
        "basis",
        "releases",
        "bom",
        "assumptions",
        "next",
    ]


def test_no_economics_anywhere(engine: Engine) -> None:
    for locale in ("en", "de"):
        written = build(engine, locale).model_dump_json().lower()
        for word in ("payback period of", "€", " eur", "cash flow of", "rendite"):
            assert word not in written


@pytest.mark.parametrize(
    ("locale", "words"),
    [
        (
            "en",
            [
                "Design report",
                "Bill of materials",
                "Self-sufficiency with storage",
                "GW10K-ETA-G20",
            ],
        ),
        (
            "de",
            [
                "Auslegungsbericht",
                "Stückliste",
                "Autarkiegrad mit Speicher",
                "GW10K-ETA-G20",
            ],
        ),
    ],
)
def test_pdf_in_both_languages_with_a_logo(
    engine: Engine, locale: str, words: list[str]
) -> None:
    document = pdf.render(build(engine, locale), f"data:image/png;base64,{PNG}")
    assert document.startswith(b"%PDF")
    text = text_of(document)
    for word in words:
        assert word in text


def test_a_logo_that_is_no_image_is_refused() -> None:
    with pytest.raises(pdf.LogoError):
        pdf.logo_image("data:image/png;base64,bm90IGFuIGltYWdl")
    with pytest.raises(pdf.LogoError):
        pdf.logo_image("data:image/svg+xml;base64,PHN2Zy8+")
