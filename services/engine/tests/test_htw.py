"""HTW Berlin's sizing rules and the Unabhängigkeitsrechner tables."""

import pytest

from linker_engine import htw


def test_the_three_rules() -> None:
    household = htw.consumption(4000, heat_pump=False, electric_vehicle=False)
    sizing = htw.size(10, household, reserve_kwh=0)
    # HTW's own example: 10 kW and 4,000 kWh -> at most 6 kWh usable.
    assert (sizing.recommended, sizing.low_kwh, sizing.high_kwh) == (True, 6.0, 6.0)
    small = htw.size(1.5, htw.consumption(5000, False, False), 0)
    assert small.recommended is False  # 0.3 kWp per MWh is below 0.5


def test_heat_pump_and_car_widen_the_consumption_and_the_limit() -> None:
    use = htw.consumption(4000, heat_pump=True, electric_vehicle=True)
    assert (use.low_kwh, use.high_kwh) == (4000 + 2664 + 1551, 4000 + 4011 + 3097)
    sizing = htw.size(15, use, reserve_kwh=0)
    assert sizing.low_kwh == pytest.approx(1.5 * 8.215, abs=0.01)
    assert sizing.high_kwh == pytest.approx(1.5 * 11.108, abs=0.01)


def test_the_backup_reserve_comes_on_top() -> None:
    assert htw.backup_reserve(2, 3) == pytest.approx(6 / 0.94, abs=0.01)
    sizing = htw.size(10, htw.consumption(5000, False, False), reserve_kwh=6.38)
    assert sizing.high_kwh == pytest.approx(7.5 + 6.38)


def test_the_lookup_reproduces_htws_published_anchor() -> None:
    # HTW's calculator shows 76 % for 5,000 kWh, 10 kW and 10 kWh usable.
    table = htw._table("tabelleAutarkie.json")
    assert htw.lookup(table, 2.0, 2.0) == pytest.approx(0.763, abs=0.002)
    # Tjaden et al. 2014, 1 kWp/MWh with 0, 1 and 2 kWh/MWh: 30, 56, 66 %.
    assert [htw.lookup(table, 1.0, s) for s in (0.0, 1.0, 2.0)] == pytest.approx(
        [0.30, 0.56, 0.66], abs=0.01
    )


def test_metrics_are_ranges_around_the_table() -> None:
    figures = htw.metrics(10, htw.consumption(5000, False, False), 10)
    low, high = figures.autarky
    assert high - low == pytest.approx(0.10, abs=1e-6)
    assert low < 0.763 < high
    assert figures.autarky_without[1] < low
