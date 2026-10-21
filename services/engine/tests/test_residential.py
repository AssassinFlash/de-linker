"""Residential designs: the ticket's acceptance cases on the real product fixture."""

import pytest

from linker_engine import eligibility, residential
from linker_engine.engine import Engine
from linker_engine.models import BatteryChoice, ResidentialInput

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


def battery_shape(
    choice: BatteryChoice | None,
) -> tuple[str, int, float, bool] | None:
    """The part of a battery choice these regressions pin."""
    if choice is None:
        return None
    return (
        choice.product.model,
        choice.quantity,
        choice.usable_kwh,
        choice.above_upper_limit,
    )


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


# #478 C17: 80538, 5,000 kWh, 10 kWp, three-phase, backup 3 kW for 4 h.
C17 = {
    "annual_kwh": 5000,
    "pv_kwp": 10,
    "phase": 3,
    "backup": "needed",
    "backup_load_kw": 3,
    "backup_hours": 4,
}


def test_backup_storage_without_a_released_configuration_is_unknown() -> None:
    """No released battery is not a 0 kWh battery: the rule stays unknown."""
    check = eligibility.backup_storage(None, 12.77)
    assert check.passed is None
    assert check.value is None
    assert check.limit == pytest.approx(12.77)


def test_backup_needed_keeps_candidates_without_backup_figures(
    engine_without_backup: Engine,
) -> None:
    """#483: the live feed carries no backup output for the home inverters.

    The reserve is a sizing input (spec 14), so missing capability figures
    must not empty the candidate list. A released battery that can hold the
    reserve is the gate; the caps are the datasheet stacking figures.
    """
    result = design(engine_without_backup, **C17)
    assert result.selected is not None
    assert result.sizing.reserve_kwh == pytest.approx(12.77, abs=0.01)
    assert result.sizing.high_kwh == pytest.approx(20.27, abs=0.01)
    battery = result.selected.battery
    assert battery is not None
    assert battery.product.model == "GW5.1-BAT-D-G20"
    assert battery.quantity == 4
    assert battery.usable_kwh == pytest.approx(20.0)
    assert battery.usable_kwh >= result.sizing.reserve_kwh
    assert battery.above_upper_limit is False
    assert [c.product.id for c in result.candidates.inverters]
    storage_rule = next(
        rule for rule in result.selected.inverter_rules if rule.id == "backup_storage"
    )
    assert storage_rule.passed is True
    assert isinstance(storage_rule.value, float)
    assert storage_rule.value >= result.sizing.reserve_kwh
    assert storage_rule.limit == pytest.approx(12.77, abs=0.01)
    # The removed capability rule filtered every home inverter; it is gone.
    failed = {f.id for e in result.candidates.excluded for f in e.failed}
    assert "backup" not in failed


def test_backup_needed_checks_the_reserve_without_an_htw_recommendation(
    engine_without_backup: Engine,
) -> None:
    """#483: HTW not recommending storage does not skip the reserve check.

    Outer Spec review repro: 5000 kWh, 2 kWp, three-phase, backup 3 kW for
    4 h. The reserve is 12.77 kWh; before the fix this returned a solution
    with no battery at all.
    """
    result = design(
        engine_without_backup,
        annual_kwh=5000,
        pv_kwp=2,
        phase=3,
        backup="needed",
        backup_load_kw=3,
        backup_hours=4,
    )
    assert result.sizing.recommended is False
    assert result.sizing.reserve_kwh == pytest.approx(12.77, abs=0.01)
    assert result.selected is not None
    assert result.selected.inverter.model == "HS2-5K-T2-X"
    battery = result.selected.battery
    assert battery is not None
    assert battery.product.model == "BU2-5.0-HV1"
    assert battery.quantity == 3
    assert battery.usable_kwh == pytest.approx(13.5)
    assert battery.above_upper_limit is True
    assert battery.usable_kwh >= result.sizing.reserve_kwh
    storage_rule = next(
        rule for rule in result.selected.inverter_rules if rule.id == "backup_storage"
    )
    assert storage_rule.passed is True
    assert any("holds the backup reserve" in warning for warning in result.warnings)
    assert not any("HTW limit" in warning for warning in result.warnings)
    battery_line = next(
        line for line in result.selected.lines if line.role == "battery"
    )
    assert "backup reserve of 12.8 kWh" in " ".join(battery_line.basis)


def test_the_backup_no_candidate_does_not_claim_a_proposal(
    engine_without_backup: Engine,
) -> None:
    """No candidate: the no-storage warning must not name a proposal or battery."""
    result = design(
        engine_without_backup,
        annual_kwh=5000,
        pv_kwp=2,
        phase=3,
        backup="needed",
        backup_load_kw=50,
        backup_hours=72,
    )
    assert result.selected is None
    assert result.sizing.recommended is False
    assert any("advises against a battery" in warning for warning in result.warnings)
    assert not any("proposal" in warning for warning in result.warnings)
    assert not any("holds the backup reserve" in warning for warning in result.warnings)

    german = design(
        engine_without_backup,
        locale="de",
        annual_kwh=5000,
        pv_kwp=2,
        phase=3,
        backup="needed",
        backup_load_kw=50,
        backup_hours=72,
    )
    assert german.selected is None
    assert any("rät die HTW Berlin" in warning for warning in german.warnings)
    assert not any("Vorschlag" in warning for warning in german.warnings)


def test_backup_accessory_ok_keeps_candidates_without_backup_figures(
    engine_without_backup: Engine,
) -> None:
    """#483: `needed_accessory_ok` must not be a dead input either."""
    result = design(engine_without_backup, **(C17 | {"backup": "needed_accessory_ok"}))
    assert result.selected is not None
    assert result.sizing.reserve_kwh == pytest.approx(12.77, abs=0.01)


def test_backup_accessory_ok_selects_on_the_shipping_contract(
    shipping_engine: Engine,
) -> None:
    """#483 on the contract the plugin ships: at least one system is selected."""
    result = design(shipping_engine, **(C17 | {"backup": "needed_accessory_ok"}))
    assert result.selected is not None
    assert result.sizing.reserve_kwh == pytest.approx(12.77, abs=0.01)
    assert result.selected.battery is not None
    assert result.selected.battery.usable_kwh >= result.sizing.reserve_kwh


def test_backup_reserve_beyond_every_released_battery_is_truthful(
    engine_without_backup: Engine,
) -> None:
    """No released home battery holds this reserve: say so, do not crash."""
    result = design(
        engine_without_backup,
        annual_kwh=5000,
        pv_kwp=10,
        phase=3,
        backup="needed",
        backup_load_kw=50,
        backup_hours=72,
    )
    assert result.selected is None
    assert result.sizing.reserve_kwh == pytest.approx(50 * 72 / 0.94, abs=0.1)
    failed = {f.id for e in result.candidates.excluded for f in e.failed}
    assert "backup_storage" in failed
    assert any("Less backup reserve" in r for r in result.relaxations)
    assert any("holds 186.2 kWh" in r for r in result.relaxations)
    assert "Plan without backup supply." in result.relaxations
    assert residential.storage_result(result).backup_reserve_kwh == pytest.approx(
        50 * 72 / 0.94, abs=0.1
    )


def test_the_truthful_backup_no_candidate_speaks_german(
    engine_without_backup: Engine,
) -> None:
    """The same no-candidate state in German, not a crash or a dead input."""
    result = design(
        engine_without_backup,
        locale="de",
        annual_kwh=5000,
        pv_kwp=10,
        phase=3,
        backup="needed",
        backup_load_kw=50,
        backup_hours=72,
    )
    assert result.selected is None
    assert any("Kleinere Notstromreserve" in r for r in result.relaxations)
    assert "Ohne Notstrom planen." in result.relaxations


def test_backup_regression_speaks_german(engine_without_backup: Engine) -> None:
    """The C17 result carries German copy for the reserve rule."""
    result = design(engine_without_backup, locale="de", **C17)
    assert result.selected is not None
    storage_rule = next(
        rule for rule in result.selected.inverter_rules if rule.id == "backup_storage"
    )
    assert (
        storage_rule.label
        == "Freigegebene Batteriekonfiguration deckt die Notstromreserve"
    )
    assert "Reserve" in storage_rule.text


def test_a_backup_swap_only_offers_configurations_that_hold_the_reserve(
    engine_without_backup: Engine,
) -> None:
    """A swap cannot undercut the reserve the design was checked against."""
    h2 = next(
        p for p in engine_without_backup.products.products if p.model == "H2-10K-T3"
    )
    small = next(
        p for p in engine_without_backup.products.products if p.model == "B2-10.0-HV1"
    )
    result = design(engine_without_backup, **(C17 | {"inverter_id": h2.id}))
    assert result.selected is not None
    assert result.candidates.batteries
    assert all(
        battery.usable_kwh >= result.sizing.reserve_kwh
        for battery in result.candidates.batteries
    )
    assert small.id not in [b.product.id for b in result.candidates.batteries]
    swapped = design(
        engine_without_backup,
        **(C17 | {"inverter_id": h2.id, "battery_id": small.id}),
    )
    assert swapped.selected is not None
    assert swapped.selected.battery is not None
    assert swapped.selected.battery.usable_kwh >= swapped.sizing.reserve_kwh
    assert swapped.selected.battery.product.id != small.id


def test_a_backup_reserve_offers_the_above_limit_configuration_that_covers_it(
    engine_without_backup: Engine,
) -> None:
    """A covering configuration above the HTW limit stays as a marked option.

    HS2-10K x BU2-5.0 at a 9.19 kWh reserve: the largest configuration within
    the 10.69 kWh upper limit is 9 kWh and cannot hold the reserve; the next
    step, 13.5 kWh, is above the limit and can. Dropping it with the battery
    would turn a solvable backup request into a false no_candidate.
    """
    hs2 = next(
        p for p in engine_without_backup.products.products if p.model == "HS2-10K-T2-X"
    )
    result = design(
        engine_without_backup,
        annual_kwh=1000,
        pv_kwp=10,
        phase=3,
        backup="needed",
        backup_load_kw=2.16,
        backup_hours=4,
        inverter_id=hs2.id,
    )
    assert result.selected is not None
    assert result.sizing.reserve_kwh == pytest.approx(9.19, abs=0.01)
    assert result.sizing.high_kwh == pytest.approx(10.69, abs=0.01)
    battery = result.selected.battery
    assert battery is not None
    assert battery.usable_kwh == pytest.approx(13.5)
    assert battery.above_upper_limit is True
    assert battery.usable_kwh >= result.sizing.reserve_kwh
    assert any(
        battery.usable_kwh >= result.sizing.reserve_kwh
        for battery in result.candidates.batteries
    )


def test_a_documented_backup_accessory_joins_the_bill_of_materials(
    engine: Engine,
) -> None:
    """`needed_accessory_ok` adds the transfer switch the contract names."""
    inverter = next(p for p in engine.products.products if p.model == "HS2-10K-T2-X")
    result = design(
        engine,
        **(C17 | {"backup": "needed_accessory_ok", "inverter_id": inverter.id}),
    )
    assert result.selected is not None
    assert result.selected.inverter.model == "HS2-10K-T2-X"
    backup = [line for line in result.selected.lines if line.role == "backup"]
    assert [line.product.model for line in backup if line.product] == ["ATS1-T63-A"]


# #482: the shipping contract, not the fixture, decides the meter lines.
def test_the_h2_bill_of_materials_has_no_second_meter(
    shipping_engine: Engine,
) -> None:
    """The H2 T3 ships with a smart meter, three CTs and a 10 m cable.

    The contract must not also list a DTSU666 beside the box: the manual's
    Unpacking section names the meter as delivered, and the SAJ configuration
    instructions describe that meter, not a second purchase.
    """
    inverter = next(
        p for p in shipping_engine.products.products if p.model == "H2-10K-T3"
    )
    result = design(shipping_engine, inverter_id=inverter.id)
    assert result.selected is not None
    assert result.selected.inverter.model == "H2-10K-T3"
    assert "meter" not in [line.role for line in result.selected.lines]
    inverter_line = next(
        line for line in result.selected.lines if line.role == "inverter"
    )
    basis = " ".join(inverter_line.basis)
    assert "Ships with its meter" in basis
    assert "section 2.2 Unpacking" in basis


def test_the_gw10k_and_hs2_meter_lines_are_unchanged(
    shipping_engine: Engine,
) -> None:
    """A meter in the box stays off the Stückliste; a meter beside it stays on."""
    gw10k = next(
        p for p in shipping_engine.products.products if p.model == "GW10K-ETA-G20"
    )
    gw_result = design(shipping_engine, inverter_id=gw10k.id)
    assert gw_result.selected is not None
    assert "meter" not in [line.role for line in gw_result.selected.lines]

    hs2 = next(
        p for p in shipping_engine.products.products if p.model == "HS2-10K-T2-X"
    )
    hs2_result = design(shipping_engine, inverter_id=hs2.id)
    assert hs2_result.selected is not None
    meters = [line for line in hs2_result.selected.lines if line.role == "meter"]
    assert [line.product.model for line in meters if line.product] == ["DTSU666"]


def test_german_wording(engine: Engine) -> None:
    result = design(engine, locale="de")
    assert result.selected is not None
    inverter_line = next(
        line for line in result.selected.lines if line.role == "inverter"
    )
    assert inverter_line.label == "Hybridwechselrichter"
    assert all(rule.label for rule in result.rules)


def test_the_shipped_contract_gives_the_hs2_two_modules(
    shipped_engine: Engine,
) -> None:
    """#489: the 0.9 kWh cap takes 2 x 4.5 kWh on the HS2-5K, never one module.

    The walked small household (600 kWh, 4 kWp) selected the HS2-5K at the
    0.9 kWh cap. One BU2-5.0 module is not a released configuration, so its
    smallest released configuration above the cap is 9.0 kWh, marked.
    """
    hs2 = next(
        product
        for product in shipped_engine.products.in_class("inverters")
        if product.model == "HS2-5K-T2-X"
    )
    result = design(shipped_engine, annual_kwh=600, pv_kwp=4, inverter_id=hs2.id)
    battery = result.selected.battery if result.selected else None
    assert battery_shape(battery) == ("BU2-5.0-HV1", 2, 9.0, True)
    assert all(
        quantity >= 2
        for quantity in (
            candidate.quantity
            for candidate in result.candidates.batteries
            if candidate.product.model.startswith("BU2-5.0-")
        )
    )
    assert any("9 kWh" in warning for warning in result.warnings)


def test_the_shipped_contract_keeps_the_one_module_b2_out_of_the_h2_system(
    shipped_engine: Engine,
) -> None:
    """#481: the H2-10K at 10 kWp no longer proposes the one-module B2-5.0."""
    h2 = next(
        product
        for product in shipped_engine.products.in_class("inverters")
        if product.model == "H2-10K-T3"
    )
    result = design(shipped_engine, inverter_id=h2.id)
    chosen = result.selected
    assert chosen is not None and chosen.battery is not None
    assert battery_shape(chosen.battery) == ("B2-10.0-HV1", 1, 9.0, True)
    assert chosen.battery.release.verdict == "released_with_accessory"
    models = [candidate.product.model for candidate in result.candidates.batteries]
    assert "B2-5.0-HV1" not in models and "B2-5.0-HV5" not in models
    for candidate in result.candidates.batteries:
        if candidate.product.model.startswith("BU2-5.0-"):
            assert candidate.quantity >= 2
    assert "B2-5.0-HV1" not in [
        line.product.model for line in chosen.lines if line.product is not None
    ]


def test_the_small_household_takes_the_smallest_released_configuration(
    shipped_engine: Engine,
) -> None:
    """#489: with the one-module answers gone, 4.8 kWh is the smallest above 0.9."""
    result = design(shipped_engine, annual_kwh=600, pv_kwp=4)
    chosen = result.selected
    assert chosen is not None and chosen.battery is not None
    assert chosen.inverter.model == "HS3-5K-T2-W/G-PX"
    assert battery_shape(chosen.battery) == ("BU3-5.0-TV2-PRO", 1, 4.8, True)
    for inverter in result.candidates.inverters:
        battery = inverter.battery
        if battery and battery.product.model.startswith("BU2-5.0-"):
            assert battery.quantity >= 2
