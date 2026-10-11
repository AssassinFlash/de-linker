"""The design report: one model for the screen and the PDF, in English and German."""

import io

import pytest
from pypdf import PdfReader

from linker_engine import pdf, report, residential, rules
from linker_engine.engine import Engine
from linker_engine.models import Report, ResidentialInput
from linker_engine.roof.service import ROOF_ASSUMPTIONS

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


def test_every_rule_without_a_source_is_disclosed_somewhere() -> None:
    """A rule the report's assumptions do not name is either operational or
    disclosed with the roof planes; nothing unverified is silent."""
    reported = {rule.id for rule in report.UNVERIFIED}
    for rule in rules.ALL:
        if rule.verified:
            assert rule.id not in reported, rule.id
        else:
            assert rule.id in reported or rule.id in report.NOT_REPORTED, rule.id
    # The exclusions are the roof step's own disclosure and the one operational limit.
    assert set(report.NOT_REPORTED) == {"pvgis_timeout", *ROOF_ASSUMPTIONS}


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


@pytest.mark.parametrize(
    ("locale", "inverter", "phase", "first_line", "datasheet"),
    [
        (
            "en",
            ("Inverter", "GoodWe GW10K-ETA-G20"),
            "3-phase, as selected · met",
            "1 pc",
            "GW_ESA-5-30kW_Datasheet-EN.pdf",
        ),
        (
            "de",
            ("Wechselrichter", "GoodWe GW10K-ETA-G20"),
            "3-phasig, wie gewählt · erfüllt",
            "1 Stk.",
            "GW_ESA-5-30kW_Datasheet-EN.pdf",
        ),
    ],
)
def test_rows_name_the_inverter_link_the_documents_and_count_in_words(
    engine: Engine,
    locale: str,
    inverter: tuple[str, str],
    phase: str,
    first_line: str,
    datasheet: str,
) -> None:
    sections = {section.id: section for section in build(engine, locale).sections}
    basis = sections["basis"]
    assert (basis.rows[0].label, basis.rows[0].value) == inverter
    assert phase in [row.value for row in basis.rows]
    assert basis.paragraphs == []
    documents = [row for row in sections["releases"].rows if row.href]
    assert documents[0].value == datasheet
    assert (
        documents[0].href
        == f"https://de-linker.com/wp-content/uploads/2026/09/{datasheet}"
    )
    table = sections["bom"].table
    assert table is not None
    assert table.rows[0][0] == first_line


def test_the_pdf_prints_the_address_of_each_linked_document(engine: Engine) -> None:
    text = text_of(pdf.render(build(engine, "en")))
    assert "GW_ESA-5-30kW_Datasheet-EN.pdf" in text
    assert "https://de-linker.com/wp-content/uploads/2026/09/" in text.replace("\n", "")


def test_roof_planes_from_lod2_are_credited_under_the_states_licence(
    engine: Engine,
) -> None:
    request = ResidentialInput.model_validate(
        {
            "plz": "80538",
            "annual_kwh": 5000,
            "pv_kwp": 6.44,
            "phase": 3,
            # One plane at the cached PVGIS orientation: the row, not the yield, is tested.
            "planes": [{"kwp": 6.44, "tilt_deg": 35, "azimuth_deg": 180}],
            "roof_source": "lod2",
        }
    )
    built = report.residential(
        residential.design(engine, request), "2026-10-09T12:00:00Z"
    )
    site = {row.label: row.value for row in built.sections[0].rows}
    assert site["Roof planes"] == (
        "From the state's official LoD2 building model, "
        "CC BY 4.0 (Bayerische Vermessungsverwaltung)"
    )


def test_roof_source_needs_planes() -> None:
    with pytest.raises(ValueError, match="roof_source"):
        ResidentialInput.model_validate(
            {
                "plz": "80538",
                "annual_kwh": 5000,
                "pv_kwp": 10,
                "phase": 3,
                "roof_source": "lod2",
            }
        )
