"""The design report: one model for the screen and the PDF, in English and German."""

import io
from typing import Any, cast

import pytest
from pypdf import PdfReader
from pypdf.generic import DictionaryObject
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from linker_engine import pdf, report, residential, rules
from linker_engine.engine import Engine
from linker_engine.models import (
    Report,
    ReportRow,
    ReportSection,
    ReportTable,
    ResidentialInput,
)
from linker_engine.planning import report_model
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


def unselected(engine: Engine, locale: str = "en") -> Report:
    """A design with no released system: the state the live review feed produces."""
    request = ResidentialInput.model_validate(
        {
            "plz": "80538",
            "annual_kwh": 5000,
            "pv_kwp": 10,
            "phase": 3,
            "locale": locale,
            "existing_inverter": "Unknown 9K",
        }
    )
    return report.residential(
        residential.design(engine, request), "2026-10-09T12:00:00Z"
    )


def test_self_sufficiency_and_self_consumption_survive_without_a_selection(
    engine: Engine,
) -> None:
    """HTW figures follow from array, consumption and capacity, not from a chosen
    inverter; a design with no released system still states them."""
    built = unselected(engine)
    metrics = {section.id: section for section in built.sections}["metrics"]
    values = {row.label: row.value for row in metrics.rows}
    assert values["Self-sufficiency with storage"].endswith("%")
    assert values["Self-consumption with storage"].endswith("%")
    # The assumed capacity is the sizing's own upper limit, named as an assumption.
    assert values["Storage capacity in these figures"] == "7.5 kWh"
    assert "7.5 kWh" in " ".join(metrics.paragraphs)


def test_metrics_name_the_capacity_they_assume(engine: Engine) -> None:
    """Two no-selection states differ: a sizing upper limit, or no storage at all."""
    sizing = unselected(engine)
    metrics = {section.id: section for section in sizing.sections}["metrics"]
    assert "upper limit of 7.5 kWh" in metrics.paragraphs[0]

    # 1 kWp is below HTW's 0.5 kWp per MWh: no battery is recommended at all, so
    # the figures describe the system without storage and must not claim a capacity.
    bare = report.residential(
        residential.design(
            engine,
            ResidentialInput.model_validate(
                {
                    "plz": "80538",
                    "annual_kwh": 5000,
                    "pv_kwp": 1,
                    "phase": 3,
                    "existing_inverter": "Unknown 1K",
                }
            ),
        ),
        "2026-10-09T12:00:00Z",
    )
    bare_metrics = {section.id: section for section in bare.sections}["metrics"]
    assert "without storage" in bare_metrics.paragraphs[0]
    values = {row.label: row.value for row in bare_metrics.rows}
    assert values["Storage capacity in these figures"] == "0 kWh"


def test_the_bill_of_materials_states_that_no_system_was_selected(
    engine: Engine,
) -> None:
    """The section is present and explains itself; a missing section reads as an
    oversight, a stated one as a verdict."""
    sections = {section.id: section for section in unselected(engine).sections}
    bom = sections["bom"]
    assert bom.table is None
    assert bom.paragraphs[0].startswith("No bill of materials yet")
    assert "What would change the result:" in bom.paragraphs


def test_the_report_names_the_generation_it_was_built_from(engine: Engine) -> None:
    built = report.residential(
        residential.design(
            engine,
            ResidentialInput.model_validate(
                {"plz": "80538", "annual_kwh": 5000, "pv_kwp": 10, "phase": 3}
            ),
        ),
        "2026-10-09T12:00:00Z",
        "9a687023a7b7b5ab769878739277eca058e1879f3a5cca7c12f9ef9968eee89c",
        "e90acaa602fd9b0e23eb24696e48667f81a2cab9ff2c5f409c9ab1706221aa2c",
    )
    site = {row.label: row.value for row in built.sections[0].rows}
    # Short prefixes: the printed sheet must stay readable; the engine's own
    # /resource/version readback compares the same twelve characters.
    assert site["Revision"] == ("Design data 9a687023a7b7 · compatibility e90acaa602fd")


def test_the_pdf_carries_the_linker_mark_without_an_uploaded_logo(
    engine: Engine,
) -> None:
    """The tool's own document carries the brand; the installer logo is optional."""
    document = pdf.render(build(engine, "en"))
    reader = PdfReader(io.BytesIO(document))
    resources = cast(DictionaryObject, reader.pages[0]["/Resources"].get_object())
    assert len(cast(DictionaryObject, resources["/XObject"].get_object())) >= 1
    with_logo = pdf.render(build(engine, "en"), f"data:image/png;base64,{PNG}")
    both = PdfReader(io.BytesIO(with_logo))
    more = cast(
        DictionaryObject,
        cast(DictionaryObject, both.pages[0]["/Resources"].get_object())[
            "/XObject"
        ].get_object(),
    )
    assert len(more) > len(cast(DictionaryObject, resources["/XObject"].get_object()))


def test_the_pdf_prints_the_revision_it_was_built_from(engine: Engine) -> None:
    built = report.residential(
        residential.design(
            engine,
            ResidentialInput.model_validate(
                {"plz": "80538", "annual_kwh": 5000, "pv_kwp": 10, "phase": 3}
            ),
        ),
        "2026-10-09T12:00:00Z",
        "9a687023a7b7b5ab769878739277eca058e1879f3a5cca7c12f9ef9968eee89c",
    )
    assert "Design data 9a687023a7b7" in text_of(pdf.render(built))


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


@pytest.mark.parametrize("locale", ["en", "de"])
def test_pdf_renders_the_cold_voc_beta_with_its_native_symbol_glyph(
    locale: str,
) -> None:
    from linker_engine.planning.report_copy import text

    formula = text("linear_cold_voc_at_declared_ambient", locale)
    source_url = "https://de-linker.com/βVoc.pdf"
    report = Report.model_validate(
        {
            "title": "βVoc",
            "subtitle": "Cold voltage formula",
            "generated_at": "2026-10-31T00:00:00Z",
            "locale": locale,
            "sections": [
                ReportSection(
                    id="formula",
                    title="Cold Voc",
                    paragraphs=[formula, source_url],
                    rows=[
                        ReportRow(
                            label="βVoc",
                            value="βVoc",
                            href=source_url,
                        )
                    ],
                    table=ReportTable(columns=["βVoc"], rows=[["βVoc"]]),
                )
            ],
        }
    )
    original = report.model_dump()
    document = pdf.render(report)
    # The shipped Latin faces have no U+03B2; the native Symbol encoding names
    # the actual beta glyph. An ASCII b substitute is not the same character.
    for name in ("Vera", "Vera-Bold"):
        assert ord("β") not in cast(TTFont, pdfmetrics.getFont(name)).face.charToGlyph
    assert pdfmetrics.getEncoding("SymbolEncoding").vector[98] == "beta"
    extracted = text_of(document)
    assert " ".join(formula.split()) in " ".join(extracted.split())
    assert extracted.count("β") == 9
    assert "\x00" not in extracted and "■" not in extracted
    reader = PdfReader(io.BytesIO(document))
    fonts: set[str] = set()
    for page in reader.pages:
        resources = cast(DictionaryObject, page["/Resources"].get_object())
        for font in cast(DictionaryObject, resources["/Font"].get_object()).values():
            fonts.add(str(cast(DictionaryObject, font.get_object())["/BaseFont"]))
    assert "/Symbol" in fonts and "/ZapfDingbats" not in fonts
    assert {
        annotation.get_object()["/A"]["/URI"]
        for page in reader.pages
        for annotation in page.get("/Annots", [])
    } == {source_url}
    assert report.model_dump() == original
    assert pdf.render(report) == document


def test_a_site_row_the_visitor_never_declared_is_left_out() -> None:
    """The sheet must not print a dash for a field nobody was asked to fill.

    Production 2026-11-14: the one-screen start named a postcode, so the
    printed site block read "Location 10115 Berlin / Country — / Time zone —".
    A dash reads as a field the report failed to fill, and a postcode does not
    establish a country or a time zone on its own. The declared rows print and
    the undeclared ones disappear.
    """
    source: dict[str, Any] = {
        "title": "Residential · 10 kWp · 10115 Berlin",
        "project_id": "0" * 32,
        "revision": 2,
        "input_sha256": "1" * 64,
        "locale": "en",
        "generated_at": "2026-11-14T08:00:00+00:00",
        "source_runs": [],
        "brief": {
            "site": {
                "location_label": "10115 Berlin",
                "country_code": None,
                "timezone": None,
            },
            "project_note": "Planned orientation: South-facing, 30°",
        },
    }

    built = report_model.build_report(source)
    sections = {section.id: section for section in built.sections}
    rows = {row.label: row.value for row in sections["site"].rows}
    assert rows["Location"] == "10115 Berlin"
    assert "Country" not in rows
    assert "Time zone" not in rows
    assert "—" not in rows.values()

    cast(dict[str, Any], cast(dict[str, Any], source["brief"])["site"])[
        "country_code"
    ] = "DE"
    built = report_model.build_report(source)
    sections = {section.id: section for section in built.sections}
    rows = {row.label: row.value for row in sections["site"].rows}
    assert rows["Country"] == "DE"
    assert "Time zone" not in rows
