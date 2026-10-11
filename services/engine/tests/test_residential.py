"""Residential designs: the ticket's acceptance cases on the real product fixture."""

import pytest

from linker_engine import residential
from linker_engine.engine import Engine
from linker_engine.models import ResidentialInput

# planner-methods.md section 4.1: the eight typical households (kWp, kWh per year).
HOUSEHOLDS = [
    (5, 3000),
    (6, 2500),
    (8, 4000),
    (10, 4000),
    (10, 5000),
    (12, 6000),
    (15, 8000),
    (10, 10000),
]


def design(engine: Engine, **fields: object) -> residential.Design:
    values: dict[str, object] = {
        "plz": "80538",
        "annual_kwh": 5000,
        "pv_kwp": 10,
        "phase": 3,
    }
    values.update(fields)
    return residential.design(engine, ResidentialInput.model_validate(values))


@pytest.mark.parametrize(("kwp", "kwh"), HOUSEHOLDS)
def test_typical_households_stay_within_htw_and_get_ranges(
    engine: Engine, kwp: float, kwh: float
) -> None:
    result = design(engine, pv_kwp=kwp, annual_kwh=kwh)
    cap = min(1.5 * kwp, 1.5 * kwh / 1000)
    assert result.sizing.recommended
    assert result.sizing.high_kwh == pytest.approx(cap)
    assert result.selected is not None and result.selected.battery is not None
    battery = result.selected.battery
    if battery.above_upper_limit:
        # Product steps too coarse: the smallest released configuration, marked (spec: "取上一档并标注").
        smallest = min(
            c.battery.usable_kwh for c in result.candidates.inverters if c.battery
        )
        assert battery.usable_kwh == smallest
        assert any("HTW" in w for w in result.warnings)
    else:
        assert battery.usable_kwh <= cap
    assert result.yield_.kwh_year_range.low < result.yield_.kwh_year_range.high
    assert result.metrics is not None
    for span in (result.metrics.autarky_range, result.metrics.self_consumption_range):
        assert 0 <= span.low < span.high <= 1


def test_three_phase_ten_kwp_is_a_complete_released_system(engine: Engine) -> None:
    result = design(engine)
    selected = result.selected
    assert selected is not None
    inverter = engine.products.by_id[selected.inverter.id]
    assert (inverter.application, inverter.phase) == ("home", 3)
    assert selected.battery is not None
    assert selected.battery.release.verdict in ("released", "released_with_accessory")
    assert selected.battery.release.documents
    roles = [line.role for line in selected.lines]
    assert roles[:2] == ["inverter", "battery"]
    ours = [line for line in selected.lines if line.product]
    assert all(line.quantity >= 1 for line in ours)
    # Nothing commercial, nothing single-phase, nothing above the HTW limit was proposed.
    for candidate in result.candidates.inverters:
        product = engine.products.by_id[candidate.product.id]
        assert (product.application, product.phase) == ("home", 3)


def test_single_phase_six_kw_is_excluded(engine: Engine) -> None:
    result = design(engine, phase=1, pv_kwp=6, annual_kwh=4000)
    excluded = {
        e.product.model: {f.id for f in e.failed} for e in result.candidates.excluded
    }
    for model in ("EF HD-P1-6K0-S2", "GW6K-EHA-G20"):
        assert "single_phase_limit" in excluded[model]
    assert all(
        (engine.products.by_id[c.product.id].ac_power_kw or 0) <= 4.6
        for c in result.candidates.inverters
    )


def test_insufficient_pv_input_is_excluded(engine: Engine) -> None:
    result = design(engine)
    excluded = {
        e.product.model: {f.id for f in e.failed} for e in result.candidates.excluded
    }
    # HS2-5K takes 7.5 kWp and HS2-6K 9 kWp: both too little for 10 kWp.
    assert {"pv_input", "dc_ac_ratio"} <= excluded["HS2-5K-T2-X"]
    assert {"pv_input", "dc_ac_ratio"} <= excluded["HS2-6K-T2-X"]
    assert "HS3-5K-T2-W/G-PX" not in excluded  # 10 kWp is exactly its limit


def test_a_swap_keeps_the_chosen_inverter_and_battery(engine: Engine) -> None:
    first = design(engine)
    assert first.selected is not None
    other = next(
        c
        for c in first.candidates.inverters
        if c.product.id != first.selected.inverter.id
    )
    swapped = design(engine, inverter_id=other.product.id)
    assert (
        swapped.selected is not None
        and swapped.selected.inverter.id == other.product.id
    )
    batteries = swapped.candidates.batteries
    if len(batteries) > 1:
        again = design(
            engine, inverter_id=other.product.id, battery_id=batteries[1].product.id
        )
        assert again.selected is not None and again.selected.battery is not None
        assert again.selected.battery.product.id == batteries[1].product.id


def test_retrofit_lists_only_released_batteries(engine: Engine) -> None:
    result = design(engine, existing_inverter="H2-10K-T3")
    assert result.selected is not None
    assert result.selected.strings is None  # the array is already there
    assert [line.role for line in result.selected.lines] == ["battery"]
    for battery in result.candidates.batteries:
        assert battery.release.verdict in ("released", "released_with_accessory")


def test_an_unknown_existing_inverter_asks_for_the_team(engine: Engine) -> None:
    result = design(engine, existing_inverter="SMA Sunny Tripower 10.0")
    assert result.selected is None
    assert any("SMA Sunny Tripower 10.0" in w for w in result.warnings)
    assert result.relaxations


def test_no_candidate_names_what_to_relax(engine: Engine) -> None:
    result = design(engine, phase=1, pv_kwp=12, annual_kwh=6000, backup="needed")
    assert result.selected is None
    assert result.relaxations


def test_backup_reserve_and_heat_pump_widen_the_range(engine: Engine) -> None:
    result = design(
        engine, heat_pump=True, backup="needed", backup_load_kw=2, backup_hours=3
    )
    assert result.sizing.reserve_kwh == pytest.approx(6.38, abs=0.01)
    assert result.sizing.low_kwh < result.sizing.high_kwh
    assert any("Wärmepumpe" in w or "heat pump" in w for w in result.warnings)


def test_german_wording(engine: Engine) -> None:
    result = design(engine, locale="de")
    assert result.selected is not None
    assert result.selected.lines[0].label == "Hybridwechselrichter"
    assert all(rule.label for rule in result.rules)
