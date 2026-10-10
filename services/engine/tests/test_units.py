"""Datasheet spellings as they are stored in the figures (#8 keeps them; the engine reads them)."""

import pytest

from linker_engine import units


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10", 10.0),
        ("57.5±1", 57.5),
        ("29,999", 29.999),
        (12, 12.0),
        ("n/a", None),
        (None, None),
    ],
)
def test_number(value: object, expected: float | None) -> None:
    assert units.number(value) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("120~950", (120.0, 950.0)),
        ("160 ~ 1000", (160.0, 1000.0)),
        ("180-900", (180.0, 900.0)),
        ("40~560", (40.0, 560.0)),
        ("1000", None),
    ],
)
def test_number_range(value: str, expected: tuple[float, float] | None) -> None:
    assert units.number_range(value) == expected


@pytest.mark.parametrize(
    ("value", "count", "expected"),
    [
        ("21/21/42/42", 4, [21.0, 21.0, 42.0, 42.0]),
        ("42 × 8", 8, [42.0] * 8),
        ("40", 3, [40.0, 40.0, 40.0]),
        ("1/1/2/2", None, [1.0, 1.0, 2.0, 2.0]),
    ],
)
def test_per_input(value: str, count: int | None, expected: list[float]) -> None:
    assert units.per_input(value, count) == expected


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        ("10", "kW", 10.0),
        ("10000", "W", 10.0),
        ("7500", "Wp", 7.5),
        ("10", "kVA", 10.0),
        ("10", None, None),
    ],
)
def test_kilo_follows_the_unit_only(
    value: str, unit: str | None, expected: float | None
) -> None:
    assert units.kilo(value, unit) == expected


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [("5120", "Wh", 5.12), ("5.12", "kWh", 5.12), ("5", "V", None)],
)
def test_kwh(value: str, unit: str, expected: float | None) -> None:
    assert units.kwh(value, unit) == expected


def test_count_takes_the_first_option() -> None:
    assert units.count("6 (Floor mounted) / 3 (Wall mounted)") == 6
    assert units.count("2.5") is None
