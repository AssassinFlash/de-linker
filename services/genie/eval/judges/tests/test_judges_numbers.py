"""Answer values: exact rewrites, German formats, and tampering that cannot hit a real value."""

from decimal import Decimal

from linker_judges.numbers import Quantity, parse_cell, rewrite, show, tamper


def test_cells_keep_printed_decimals_and_drop_footnote_marks() -> None:
    assert parse_cell("8.7*2", "kWh") == Quantity("8.7", "kWh")
    assert show(Quantity("8.7", "kWh"), "de") == "8,7 kWh"
    assert show(Quantity("15000", "Wp"), "de", thousands=True) == "15.000 Wp"


def test_rewrites_are_exact() -> None:
    assert rewrite(Quantity("15000", "Wp"), "en") == "15 kWp"
    assert rewrite(Quantity("124.99", "kW"), "en") == "124,990 W"
    assert rewrite(Quantity("5", ""), "de") == "fünf"


def test_tampered_value_avoids_every_value_in_the_row() -> None:
    row = {Decimal("10000"), Decimal("12000"), Decimal("15000"), Decimal("18000")}

    wrong = tamper(Quantity("15000", "Wp"), row)

    assert wrong.value not in row
    assert wrong.unit == "Wp"
