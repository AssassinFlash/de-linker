"""Independent energy/power counterexamples, not copied old sizing functions."""

from __future__ import annotations

import math
import random
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from linker_engine.planning.battery_model import BatteryModel
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.dispatch import (
    Policy,
    replay,
    self_consumption_with_reserve,
)
from linker_engine.planning.dispatch_checks import Tolerance, Verification, verify
from linker_engine.planning.dispatch_frame import Command, Flows, Frame
from linker_engine.planning.energy_metrics import metrics
from linker_engine.planning.energy_origins import EnergyOrigins
from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.interval import Interval
from linker_engine.planning.operating_limits import OperatingLimits
from linker_engine.planning.worker import Control

# Numerical float64 fixture tolerances from the numerical contract §8. They
# neither describe meter precision nor relax engineering capacity/power facts.
TOLERANCE = Tolerance(absolute_kwh=1e-7, absolute_kw=1e-7, relative=1e-9)


def battery(
    capacity: float,
    power: float,
    *,
    eta: float = 1,
    standing_rate: float = 0,
    internal_aux: float = 0,
) -> BatteryModel:
    parameters: Object = {
        "usable_window_kwh": capacity,
        "charge_ac_kw": power,
        "discharge_ac_kw": power,
        "eta_charge": eta,
        "eta_discharge": eta,
        "internal_aux_kw": internal_aux,
        "standing_loss_rate_per_hour": standing_rate,
        "fixture_only": True,
    }
    return BatteryModel(
        capacity,
        power,
        power,
        eta,
        eta,
        internal_aux,
        standing_rate,
        digest(encode(parameters)),
    )


def frame(
    index: int,
    *,
    load: float,
    pv: float = 0,
    reserve: float = 0,
    import_cap: float | None = None,
    outage: bool = False,
    pv_enabled: bool = True,
    grid_charge: bool = False,
    aux: float = 0,
) -> Frame:
    start = datetime(2024, 1, 1, 20, tzinfo=UTC) + timedelta(hours=index)
    limits = OperatingLimits(
        "outage" if outage else "connected",
        reserve,
        import_cap,
        0,
        pv_enabled,
        grid_charge,
    )
    return Frame(Interval(start, start + timedelta(hours=1)), load, pv, aux, limits)


def run(
    frames: tuple[Frame, ...],
    model: BatteryModel,
    initial: EnergyOrigins,
    policy: Policy = self_consumption_with_reserve,
) -> tuple[Flows, ...]:
    return replay(frames, model, initial, policy, checkpoint=Control().checkpoint)


def checks(
    flows: tuple[Flows, ...], model: BatteryModel, terminal: float | None = None
) -> Verification:
    return verify(flows, model, TOLERANCE, terminal_min_kwh=terminal)


def ratio(result: Object, name: str) -> float:
    item = result[name]
    assert isinstance(item, dict) and isinstance(item["value"], (int, float))
    return float(item["value"])


def test_pv_charge_losses_and_actual_solar_contribution() -> None:
    model = battery(20, 20, eta=0.9)
    flows = run(
        (frame(0, load=0, pv=10), frame(1, load=10)), model, EnergyOrigins(0, 0, 0)
    )
    assert checks(flows, model, terminal=0).passed
    assert flows[0].after.pv_kwh == pytest.approx(9)
    assert flows[1].discharge_kw == pytest.approx(8.1)
    assert flows[1].import_kw == pytest.approx(1.9)
    assert flows[-1].after.total == pytest.approx(0)
    result = metrics(flows, model)
    assert ratio(result, "solar_autarky") == pytest.approx(0.81)
    assert ratio(result, "pv_input_self_use") == pytest.approx(1)
    assert result["charge_conversion_loss_kwh"] == pytest.approx(1)
    assert result["discharge_conversion_loss_kwh"] == pytest.approx(0.9)


def test_grid_charging_never_becomes_solar() -> None:
    model = battery(5, 5)
    commands = iter((Command(5, 0), Command(0, 5)))

    def policy(_: Frame, __: BatteryModel, ___: EnergyOrigins) -> Command:
        return next(commands)

    flows = run(
        (frame(0, load=0, grid_charge=True), frame(1, load=5)),
        model,
        EnergyOrigins(0, 0, 0),
        policy,
    )
    assert checks(flows, model, terminal=0).passed
    result = metrics(flows, model)
    assert (
        result["grid_charge_ac_kwh"] == result["grid_origin_battery_to_load_kwh"] == 5
    )
    assert ratio(result, "solar_autarky") == 0
    assert result["pv_input_self_use"] == {
        "value": None,
        "undefined_reason": "pv_generation_is_zero",
    }


def test_initial_unknown_inventory_is_not_a_repeatable_solar_source() -> None:
    model = battery(5, 5)
    flows = run((frame(0, load=5, outage=True),), model, EnergyOrigins(0, 0, 5))
    assert checks(flows, model).passed
    assert not checks(flows, model, terminal=5).passed
    assert flows[-1].after.total == pytest.approx(0)
    result = metrics(flows, model)
    assert result["initial_unknown_battery_to_load_kwh"] == 5
    assert ratio(result, "solar_autarky") == 0


def test_power_limit_can_fail_a_large_capacity_outage() -> None:
    model = battery(20, 5)
    flows = run((frame(0, load=10, outage=True),), model, EnergyOrigins(0, 0, 20))
    assert flows[0].discharge_kw == 5
    assert flows[0].unserved_load_kw == 5
    assert flows[0].after.total == 15
    assert not checks(flows, model).passed
    balances = {item.code: item for item in checks(flows, model).checks}
    assert balances["ac_energy_balance"].passed and not balances["load_supplied"].passed


@pytest.mark.parametrize("capacity,feasible", [(42.6, False), (85.1063829787234, True)])
def test_eight_hour_cross_midnight_deficit_is_continuous(
    capacity: float, feasible: bool
) -> None:
    model = battery(capacity, 10, eta=0.94)
    frames = tuple(frame(index, load=20, import_cap=10) for index in range(8))
    flows = run(frames, model, EnergyOrigins(0, 0, capacity))
    assert checks(flows, model).passed is feasible
    assert flows[3].frame.interval.start.date() != flows[4].frame.interval.start.date()
    assert flows[4].before == flows[3].after
    if feasible:
        assert math.fsum(flow.discharge_kw for flow in flows) == pytest.approx(80)
        assert flows[-1].after.total == pytest.approx(0, abs=1e-9)
    else:
        assert math.fsum(flow.unserved_load_kw for flow in flows) > 39


@pytest.mark.parametrize(
    "recharge,feasible", [(10.0, False), (11.317338162064282, True)]
)
def test_conversion_losses_must_be_replenished(recharge: float, feasible: bool) -> None:
    initial = 10 / 0.94
    model = battery(20, 20, eta=0.94)
    commands = iter((Command(0, 10), Command(recharge, 0)))

    def policy(_: Frame, __: BatteryModel, ___: EnergyOrigins) -> Command:
        return next(commands)

    flows = run(
        (
            frame(0, load=20, import_cap=10),
            frame(1, load=0, import_cap=20, grid_charge=True),
        ),
        model,
        EnergyOrigins(0, 0, initial),
        policy,
    )
    assert checks(flows, model, terminal=initial).passed is feasible
    assert flows[-1].after.total == pytest.approx(recharge * 0.94)


def test_available_pv_limits_solar_autarky() -> None:
    model = battery(10, 10)
    flows = run(
        (frame(0, load=0, pv=2.208), frame(1, load=4)), model, EnergyOrigins(0, 0, 0)
    )
    assert checks(flows, model).passed
    assert ratio(metrics(flows, model), "solar_autarky") == pytest.approx(0.552)


def test_greedy_policy_failure_is_distinct_from_a_feasible_schedule() -> None:
    model = battery(6, 6)
    frames = (frame(0, load=3, import_cap=4), frame(1, load=8, import_cap=4))
    initial = EnergyOrigins(6, 0, 0)
    greedy = run(frames, model, initial)
    assert not checks(greedy, model).passed
    assert greedy[1].unserved_load_kw == pytest.approx(1)
    commands = iter((Command(0, 2), Command(0, 4)))

    def forecast_schedule(_: Frame, __: BatteryModel, ___: EnergyOrigins) -> Command:
        return next(commands)

    witness = run(frames, model, initial, forecast_schedule)
    assert checks(witness, model).passed
    assert tuple(flow.import_kw for flow in witness) == pytest.approx((1, 4))
    # A manually supplied feasible witness is not a claim that a particular
    # EMS implements it or that the greedy controller met the same task.


@pytest.mark.parametrize("initial,feasible", [(6, False), (8, True)])
def test_backup_reserve_cannot_be_spent_twice(initial: float, feasible: bool) -> None:
    model = battery(8, 8)
    commands = iter((Command(0, 0), Command(0, 4)))

    def forecast_schedule(_: Frame, __: BatteryModel, ___: EnergyOrigins) -> Command:
        return next(commands)

    flows = run(
        (
            frame(0, load=3, import_cap=4, reserve=4),
            frame(1, load=8, import_cap=4, reserve=4),
        ),
        model,
        EnergyOrigins(initial, 0, 0),
        forecast_schedule,
    )
    assert checks(flows, model).passed is feasible
    assert flows[-1].after.total >= 4


def test_internal_and_ac_aux_losses_and_source_mixing_close() -> None:
    model = battery(20, 10, eta=0.9, standing_rate=math.log(2), internal_aux=1)
    initial = EnergyOrigins(4, 4, 2)
    flows = run((frame(0, load=1, aux=0.8, outage=True),), model, initial)
    assert checks(flows, model).passed
    flow = flows[0]
    assert flow.standing_loss.total == pytest.approx(5)
    assert flow.internal_aux.total == pytest.approx(1)
    assert flow.discharged_internal.total == pytest.approx(2)
    assert flow.after.total == pytest.approx(2)
    assert flow.after.pv_kwh == pytest.approx(0.8)
    assert flow.after.grid_kwh == pytest.approx(0.8)
    assert flow.after.initial_unknown_kwh == pytest.approx(0.4)
    assert flow.discharged_to_load_ac.pv_kwh == pytest.approx(0.4)
    assert ratio(metrics(flows, model), "solar_autarky") == pytest.approx(0.4)


def test_insufficient_internal_aux_is_recorded_instead_of_free_energy() -> None:
    model = battery(5, 5, internal_aux=1)
    flows = run((frame(0, load=0),), model, EnergyOrigins(0, 0, 0.25))
    assert flows[0].internal_aux.total == 0.25
    assert flows[0].internal_aux_unserved_kwh == 0.75
    assert not checks(flows, model).passed


def test_outage_uses_inherited_state_and_mode_specific_pv() -> None:
    model = battery(5, 5)
    frames = (
        frame(0, load=0, pv=2),
        frame(1, load=5, pv=20, outage=True, pv_enabled=False),
    )
    flows = run(frames, model, EnergyOrigins(0, 0, 0))
    assert flows[1].before.total == 2
    assert flows[1].pv_available_kw == 0
    assert flows[1].import_kw == flows[1].export_kw == 0
    assert flows[1].unserved_load_kw == 3
    assert not checks(flows, model).passed


def test_full_curtailment_and_zero_load_have_explicit_undefined_ratios() -> None:
    model = battery(0, 0)
    flows = run((frame(0, load=0, pv=10),), model, EnergyOrigins(0, 0, 0))
    assert checks(flows, model).passed
    result = metrics(flows, model)
    assert result["pv_generated_ac_kwh"] == 0
    assert result["pv_curtailed_kwh"] == 10
    assert result["solar_autarky"] == {
        "value": None,
        "undefined_reason": "gross_load_is_zero",
    }
    assert result["pv_input_self_use"] == {
        "value": None,
        "undefined_reason": "pv_generation_is_zero",
    }
    encode(result)


def test_controller_cannot_issue_simultaneous_directions_or_reset_time() -> None:
    with pytest.raises(InvalidInput):
        Command(1, 1)
    model = battery(5, 5)
    with pytest.raises(InvalidInput, match="continuous"):
        run((frame(0, load=1), frame(2, load=1)), model, EnergyOrigins(0, 0, 5))


def test_independent_verifier_detects_fabricated_supply_and_reset() -> None:
    model = battery(10, 10)
    flows = run((frame(0, load=3), frame(1, load=3)), model, EnergyOrigins(0, 0, 6))
    assert checks(flows, model).passed
    fabricated = (replace(flows[0], import_kw=10), flows[1])
    assert not checks(fabricated, model).passed
    reset = (flows[0], replace(flows[1], before=EnergyOrigins(0, 0, 6)))
    assert not checks(reset, model).passed


def test_many_irregular_intervals_preserve_ledger_and_limits() -> None:
    generator = random.Random(548)
    intervals: list[Frame] = []
    start = datetime(2024, 1, 1, tzinfo=UTC)
    for _ in range(500):
        end = start + timedelta(minutes=generator.choice((5, 15, 30, 60)))
        conditions = OperatingLimits("connected", 2.5, 100, 2, True, False)
        intervals.append(
            Frame(
                Interval(start, end),
                generator.random() * 20,
                generator.random() * 30,
                generator.random(),
                conditions,
            )
        )
        start = end
    model = battery(30, 10, eta=0.94)
    flows = run(tuple(intervals), model, EnergyOrigins(10, 10, 5))
    verification = checks(flows, model)
    assert verification.passed, [
        item.document() for item in verification.checks if not item.passed
    ]
    encode(verification.document())
    encode(metrics(flows, model))


def test_complete_synthetic_year_matches_independent_daily_energy_totals() -> None:
    # An analytic volume fixture, not a claimed European PV weather pattern:
    # daily AC PV=10 at one hour; direct load=1; 5 internal kWh charges at .9,
    # delivering 4.5 later. Thus solar load=5.5/day and grid=18.5/day.
    start = datetime(2023, 1, 1, tzinfo=UTC)
    conditions = OperatingLimits("connected", 0, None, 0, True, False)
    frames = tuple(
        Frame(
            Interval(
                start + timedelta(hours=index), start + timedelta(hours=index + 1)
            ),
            1,
            10 if index % 24 == 12 else 0,
            0,
            conditions,
        )
        for index in range(8760)
    )
    model = battery(5, 10, eta=0.9)
    flows = run(frames, model, EnergyOrigins(0, 0, 0))
    verified = checks(flows, model, terminal=0)
    assert verified.passed, [
        item.document() for item in verified.checks if not item.passed
    ]
    result = metrics(flows, model)
    assert result["gross_load_kwh"] == 8760
    assert result["solar_load_kwh"] == pytest.approx(2007.5)
    assert result["grid_import_kwh"] == pytest.approx(6752.5)
    assert ratio(result, "solar_autarky") == pytest.approx(0.22916666666666666)
    assert flows[-1].after.total == pytest.approx(0)
