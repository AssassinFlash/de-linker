"""One display format for the report, in each locale's own convention."""

from __future__ import annotations

import pytest

from linker_engine.planning.report_numbers import number, percent, significant, span


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # A quantity keeps the report's established three decimals, and a value
        # that has none loses its trailing zeros instead of growing them.
        (9315.200808684325, "9,315.201"),
        (2943.945050162976, "2,943.945"),
        (6.0, "6"),
        (0.0, "0"),
        (10416.666666666666, "10,416.667"),
        # A coefficient keeps its own digits: three decimals would erase it.
        (0.0029, "0.0029"),
        (-0.0029, "-0.0029"),
        (0.1805, "0.1805"),
        (0.9637, "0.9637"),
        (0.0001234, "0.0001234"),
        # Beyond what plain decimals can show, the exponent stays.
        (1e-12, "1e-12"),
    ],
)
def test_one_number_has_one_display_whatever_its_magnitude(
    value: float, expected: str
) -> None:
    assert significant(value, "en") == expected


def test_a_count_is_grouped_like_the_report_always_grouped_it() -> None:
    # Counts follow the quantity convention the report already used for them.
    assert significant(20, "en") == "20"
    assert significant(8760, "en") == "8,760"
    assert significant(8760, "de") == "8.760"
    # A year is an identifier, not a quantity, so the sections that show one
    # render it as stored (`str`) instead of passing it through this format.
    assert significant(2023, "en") == "2,023"


def test_german_uses_its_own_thousands_and_decimal_marks() -> None:
    assert significant(9315.200808684325, "de") == "9.315,201"
    assert significant(0.1805, "de") == "0,1805"
    assert significant(1234567.891, "de") == "1.234.567,891"


def test_a_percentage_keeps_its_established_resolution() -> None:
    assert percent(81.4494, "de") == "81,449 %"
    assert percent(100.0, "en") == "100 %"
    assert percent(14, "de") == "14 %"


def test_a_unit_is_attached_only_to_a_real_value() -> None:
    assert number(9200.0, "en", "W") == "9,200 W"
    assert number(8760, "de", "kWh") == "8.760 kWh"
    assert number(None, "en", "kWh") == "—"


def test_a_range_shares_one_convention_but_timestamps_stay_verbatim() -> None:
    assert span(1.5, 2.5, "de") == "1,5 – 2,5"
    # A timestamp separator is not a decimal point and must not be rewritten.
    assert span("2023-01-01T00:00:00+00:00", "2024-01-01T00:00:00+00:00", "de") == (
        "2023-01-01T00:00:00+00:00 – 2024-01-01T00:00:00+00:00"
    )
