"""Figures of a document chunk: what is tagged, what stays a name, and their values."""

import pytest

from linker_genie.figures import borrow_units, chunk_of, figure_id, localize, tag


def test_each_cell_of_a_table_row_is_its_own_figure() -> None:
    tagged = tag("c1", "| No. of MPPT | 3 | 3 | 2 |")

    assert tagged.text == "| No. of MPPT | [n1=3] | [n2=3] | [n3=2] |"
    assert tagged.figures == {"c1.n1": "3", "c1.n2": "3", "c1.n3": "2"}


def test_model_codes_stay_names() -> None:
    text = "SAJ H2-10K-T3, CB2-100.3-HV5 and GW10K-ET"

    tagged = tag("c1", text)

    assert (tagged.text, tagged.figures) == (text, {})


@pytest.mark.parametrize(
    ("text", "values"),
    [
        ("Reserve ≥ 1500 mm here", ["1500 mm"]),
        ("supports 5-108kWh.", ["5", "108kWh"]),
        ("a warranty of 10 years, 95%.", ["10 years", "95%"]),
        ("range 180 - 900", ["180", "900"]),
        ("40/40/40", ["40", "40", "40"]),
        ("section 6.6 Export limit", ["6.6"]),
        ("capacity should reach 1.5 tons.", ["1.5 tons"]),
    ],
)
def test_a_figure_keeps_the_unit_written_next_to_it(
    text: str, values: list[str]
) -> None:
    assert list(tag("c", text).figures.values()) == values


def test_a_table_row_lends_its_unit_to_figures_without_one() -> None:
    text = (
        "| Nominal Capacity (kWh) | 260 |\n"
        "| AC Output (On-Grid) | Rated Input Power(W) | 6000 | 8000 |\n"
        "| PV | Number of MPP Trackers | 3 |\n"
        "| Humidity | 5%-95% |"
    )

    values = list(tag("c", text).figures.values())

    assert values == ["260 kWh", "6000 W", "8000 W", "3", "5%", "95%"]


@pytest.mark.parametrize(
    "date",
    [
        "2026-01-01",
        "01.01.2026",
        "1 st January 2026",
        "1. Januar 2026",
        "January 1, 2026",
    ],
)
def test_a_date_is_one_figure(date: str) -> None:
    assert list(tag("c", f"produced on/after {date} only").figures.values()) == [date]


def test_figure_ids_name_their_chunk() -> None:
    assert figure_id("0df5-p14-8b3f", 12) == "0df5-p14-8b3f.n12"
    assert chunk_of("0df5-p14-8b3f.n12") == "0df5-p14-8b3f"
    assert chunk_of("p4107.pv_input_kw") is None
    assert chunk_of("0df5-p14-8b3f") is None


@pytest.mark.parametrize(
    ("value", "locale", "expected"),
    [
        ("10 years", "de", "10 Jahre"),
        ("12 months", "de", "12 Monate"),
        ("5 Jahre", "en", "5 years"),
        ("1 st January 2026", "de", "1. Januar 2026"),
        ("1. Januar 2021", "en", "1 January 2021"),
        ("1500 mm", "de", "1500 mm"),
        ("1.5 tons", "de", "1.5 Tonnen"),
        ("10 years", "en", "10 years"),
    ],
)
def test_word_units_and_dates_follow_the_turn_language(
    value: str, locale: str, expected: str
) -> None:
    assert localize(value, locale) == expected


@pytest.mark.parametrize(
    ("text", "values"),
    [
        ("Operating temperature range -40℃~+60℃", ["-40℃", "+60℃"]),
        ("Storage temperature range -45℃~+90℃", ["-45℃", "+90℃"]),
        ("Betriebstemperatur −40 °C bis +60 °C", ["−40 °C", "+60 °C"]),
        ("Betriebstemperatur −40°C bis +60°C", ["−40°C", "+60°C"]),
        ("Temperature -40°C to +60°C", ["-40°C", "+60°C"]),
        ("range -40–+60℃", ["-40", "+60℃"]),
        ("range -40--20℃", ["-40", "-20℃"]),
        ("range 180-900 V", ["180", "900 V"]),
        ("| Temperature (°C) | -40 | −45 | +60 |", ["-40 °C", "−45 °C", "+60 °C"]),
        ("SAJ H2-10K-T3, CB2-100.3-HV5, GW10K-ET: -40℃~+60℃", ["-40℃", "+60℃"]),
    ],
)
def test_unary_signs_stay_in_facts_without_turning_range_separators_into_signs(
    text: str, values: list[str]
) -> None:
    assert list(tag("c", text).figures.values()) == values


def test_esolar_temperature_signs_hydrate_in_both_languages() -> None:
    # Hosted PDF, page 1: /uploads/2026/08/saj_esolar-aio3_datasheet_en.pdf.
    # The actual table writes Operating temperature range -40℃~+60℃.
    from linker_genie.facts import Fact, TurnFacts
    from linker_genie.hydrate import fill

    tagged = tag("aio3", "Operating temperature range -40℃~+60℃")
    facts = TurnFacts(
        facts={
            key: Fact(key, value, "search-knowledge")
            for key, value in tagged.figures.items()
        },
        chunk_ids={"aio3"},
    )
    for locale in ("en", "de"):
        assert fill("{fact:aio3.n1} / {fact:aio3.n2}", facts, locale) == "-40℃ / +60℃"


@pytest.mark.parametrize("lower", ["-40", "−40"])
def test_signed_attachment_figures_still_borrow_the_named_unit(lower: str) -> None:
    tagged = borrow_units(tag("c", f"Temperature (°C): {lower} to +60"))
    assert list(tagged.figures.values()) == [f"{lower} °C", "+60 °C"]


@pytest.mark.parametrize(
    ("text", "values"),
    [
        ("Temperature ≥-40℃", ["-40℃"]),
        ("Temperature ≤−20 °C", ["−20 °C"]),
        ("Temperature <-40°C", ["-40°C"]),
        ("Temperature >+60℃", ["+60℃"]),
        ("Temperature ≈−20°C", ["−20°C"]),
        ('Temperature "-40℃"', ["-40℃"]),
        ("Temperature '-40°C'", ["-40°C"]),
        ("Temperature “-40°C”", ["-40°C"]),
        ("Temperature ‘−20°C’", ["−20°C"]),
        ("Temperature «-40°C»", ["-40°C"]),
        ("Temperature -40°C,-20°C", ["-40°C", "-20°C"]),
        ("Temperature -40...-20℃", ["-40", "-20℃"]),
        ("Temperature -40…−20°C", ["-40", "−20°C"]),
        ("Temperature −40−−20 °C", ["−40", "−20 °C"]),
        ("Temperature −40−−20°C", ["−40", "−20°C"]),
        ("Voltage 180-900 V", ["180", "900 V"]),
        ("Voltage 180−900 V", ["180", "900 V"]),
        ("Temperature 40℃-60℃", ["40℃", "60℃"]),
    ],
)
def test_reviewed_sign_boundaries_preserve_unary_signs(
    text: str, values: list[str]
) -> None:
    assert list(tag("c", text).figures.values()) == values
