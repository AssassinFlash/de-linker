"""Chronological multi-unit replay at a single point of common coupling.

The declared baseline shares available power proportionally. It has no
forecast, optimality or manufacturer-controller-execution claim. The step
also permits different units to charge and discharge together; source energy
can cross the common bus without changing its origin. Device losses and
inventories remain distinct and grid limits are applied once for the site.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from .dispatch_frame import Command
from .energy_origins import EnergyOrigins
from .errors import InvalidInput
from .numerical_tolerance import Tolerance
from .plant_energy_model import PlantFlow, PlantFrame, StorageFlow, StorageUnit

type States = dict[str, EnergyOrigins]
type Commands = dict[str, Command]
type Policy = Callable[[PlantFrame, tuple[StorageUnit, ...], States], Commands]


def _sum(values: tuple[float, ...] | list[float]) -> float:
    try:
        value = math.fsum(values)
    except OverflowError as error:
        raise InvalidInput("plant energy exceeds finite arithmetic") from error
    if not math.isfinite(value):
        raise InvalidInput("plant energy exceeds finite arithmetic")
    return value


def _shares(bounds: dict[str, float], available: float) -> dict[str, float]:
    total = _sum(list(bounds.values()))
    fraction = min(available / total, 1.0) if total else 0.0
    return {key: value * fraction for key, value in bounds.items()}


def _idle(
    frame: PlantFrame, unit: StorageUnit, before: EnergyOrigins
) -> tuple[EnergyOrigins, EnergyOrigins, EnergyOrigins, float]:
    model = unit.for_mode(frame.site.limits.mode)
    duration = frame.site.interval.hours
    fraction = -math.expm1(-model.standing_loss_rate_per_hour * duration)
    state, standing = before.withdraw(before.total * fraction)
    need = model.internal_aux_kw * duration
    state, internal = state.withdraw(need)
    return state, standing, internal, max(need - internal.total, 0.0)


def _validate(
    frame: PlantFrame,
    units: tuple[StorageUnit, ...],
    states: States,
    tolerance: Tolerance | None = None,
) -> None:
    ids = {unit.id for unit in units}
    if (
        not units
        or len(ids) != len(units)
        or ids != set(states)
        or ids != set(frame.reserves_kwh)
    ):
        raise InvalidInput("plant states and reserves need every distinct unit")
    for unit in units:
        allowance = (
            tolerance.absolute_kwh
            + tolerance.relative
            * max(
                states[unit.id].total,
                unit.for_mode(frame.site.limits.mode).usable_window_kwh,
            )
            if tolerance is not None
            else 0.0
        )
        if not math.isfinite(allowance):
            raise InvalidInput("plant tolerance exceeds finite arithmetic")
        if (
            not unit.id
            or states[unit.id].total
            - unit.for_mode(frame.site.limits.mode).usable_window_kwh
            > allowance
        ):
            raise InvalidInput("initial unit inventory exceeds its usable window")
        if (
            frame.reserves_kwh[unit.id]
            > unit.for_mode(frame.site.limits.mode).usable_window_kwh
        ):
            raise InvalidInput("unit reserve exceeds its own usable window")


def self_consumption(
    frame: PlantFrame, units: tuple[StorageUnit, ...], states: States
) -> Commands:
    """Share actual post-loss headroom; never borrow another unit's inventory."""
    duration = frame.site.interval.hours
    pv = frame.site.pv_potential_kw if frame.site.limits.pv_enabled else 0.0
    balance = pv - frame.site.load_kw - frame.site.aux_ac_kw
    charge: dict[str, float] = {}
    discharge: dict[str, float] = {}
    for unit in units:
        state, _, _, _ = _idle(frame, unit, states[unit.id])
        model = unit.for_mode(frame.site.limits.mode)
        charge[unit.id] = min(
            model.charge_ac_kw,
            max(model.usable_window_kwh - state.total, 0.0)
            / (model.eta_charge * duration),
        )
        discharge[unit.id] = min(
            model.discharge_ac_kw,
            max(state.total - frame.reserves_kwh[unit.id], 0.0)
            * model.eta_discharge
            / duration,
        )
    charging = _shares(charge, max(balance, 0.0))
    discharging = _shares(discharge, max(-balance, 0.0))
    return {unit.id: Command(charging[unit.id], discharging[unit.id]) for unit in units}


def step(
    frame: PlantFrame,
    units: tuple[StorageUnit, ...],
    before: States,
    commands: Commands,
    *,
    tolerance: Tolerance,
) -> PlantFlow:
    _validate(frame, units, before, tolerance)
    if set(commands) != set(before):
        raise InvalidInput("one command is required for every plant unit")
    duration = frame.site.interval.hours
    idle = {unit.id: _idle(frame, unit, before[unit.id]) for unit in units}
    charge: dict[str, float] = {}
    discharge: dict[str, float] = {}
    for unit in units:
        model, command, state = (
            unit.for_mode(frame.site.limits.mode),
            commands[unit.id],
            idle[unit.id][0],
        )
        charge[unit.id] = min(
            command.charge_kw,
            model.charge_ac_kw,
            max(model.usable_window_kwh - state.total, 0.0)
            / (model.eta_charge * duration),
        )
        discharge[unit.id] = min(
            command.discharge_kw,
            model.discharge_ac_kw,
            max(state.total - frame.reserves_kwh[unit.id], 0.0)
            * model.eta_discharge
            / duration,
        )
    site = frame.site
    pv = (site.pv_potential_kw if site.limits.pv_enabled else 0.0) * duration
    load, aux = site.load_kw * duration, site.aux_ac_kw * duration
    # Battery export is outside this model. Demand includes the other units'
    # requested charging, so real cross-unit transfer is not a global mode ban.
    wanted = max(load + aux + _sum(list(charge.values())) * duration - pv, 0.0)
    delivered = _shares(discharge, wanted / duration)
    withdrawals: States = {}
    emissions: States = {}
    states: States = {}
    pool = EnergyOrigins(pv, 0, 0)
    for unit in units:
        states[unit.id], withdrawals[unit.id] = idle[unit.id][0].withdraw(
            delivered[unit.id]
            * duration
            / unit.for_mode(frame.site.limits.mode).eta_discharge
        )
        emissions[unit.id] = withdrawals[unit.id].scaled(
            unit.for_mode(frame.site.limits.mode).eta_discharge
        )
        pool = pool.plus(emissions[unit.id])
    ac_supply = pool.total
    load_fraction = min(load / ac_supply, 1.0) if ac_supply else 0.0
    aux_fraction = (
        min(aux, max(ac_supply - load, 0.0)) / ac_supply if ac_supply else 0.0
    )
    battery_load = EnergyOrigins(
        _sum([value.pv_kwh for value in emissions.values()]),
        _sum([value.grid_kwh for value in emissions.values()]),
        _sum([value.initial_unknown_kwh for value in emissions.values()]),
    )
    pool, served_load = pool.withdraw(load)
    pool, served_aux = pool.withdraw(aux)
    missing_load = max(load - served_load.total, 0.0)
    missing_aux = max(aux - served_aux.total, 0.0)
    grid_base = (
        site.limits.import_limit((missing_load + missing_aux) / duration) * duration
    )
    grid_load = min(grid_base, missing_load)
    grid_aux = max(grid_base - grid_load, 0.0)
    served_load = served_load.plus(EnergyOrigins(0, grid_load, 0))
    served_aux = served_aux.plus(EnergyOrigins(0, grid_aux, 0))
    requested_charge = _sum(list(charge.values())) * duration
    grid_charge = 0.0
    if site.limits.allow_grid_charge:
        requested_import = grid_base + max(requested_charge - pool.total, 0.0)
        grid_charge = max(
            site.limits.import_limit(requested_import / duration) * duration
            - grid_base,
            0.0,
        )
    pool = pool.plus(EnergyOrigins(0, grid_charge, 0))
    received = _shares(charge, min(requested_charge, pool.total) / duration)
    direct_pv_charge = (
        pv
        * max(1 - load_fraction - aux_fraction, 0.0)
        * (_sum(list(received.values())) * duration / pool.total if pool.total else 0.0)
    )
    pool, charging_sources = pool.withdraw(_sum(list(received.values())) * duration)
    unit_flows: list[StorageFlow] = []
    total_received = _sum(list(received.values())) * duration
    for unit in units:
        unit_received = charging_sources.scaled(
            received[unit.id] * duration / total_received if total_received else 0.0
        )
        state = states[unit.id].plus(
            unit_received.scaled(unit.for_mode(frame.site.limits.mode).eta_charge)
        )
        unit_flows.append(
            StorageFlow(
                unit,
                frame.site.limits.mode,
                frame.reserves_kwh[unit.id],
                commands[unit.id],
                before[unit.id],
                state,
                idle[unit.id][1],
                idle[unit.id][2],
                idle[unit.id][3],
                withdrawals[unit.id],
                emissions[unit.id],
                unit_received,
            )
        )
    pool, exported = pool.withdraw(
        site.limits.export_limit(pool.total / duration) * duration
    )
    return PlantFlow(
        frame=frame,
        units=tuple(unit_flows),
        pv_available_kwh=pv,
        direct_pv_to_load_kwh=pv * load_fraction,
        direct_pv_to_aux_kwh=pv * aux_fraction,
        direct_pv_to_charge_kwh=direct_pv_charge,
        battery_to_load_ac=battery_load.scaled(load_fraction),
        battery_to_aux_ac=battery_load.scaled(aux_fraction),
        grid_to_load_kwh=grid_load,
        grid_to_aux_kwh=grid_aux,
        load_sources=served_load,
        aux_sources=served_aux,
        grid_import_kwh=grid_base + grid_charge,
        grid_charge_kwh=grid_charge,
        export_sources=exported,
        curtailed_sources=pool,
        unserved_load_kwh=max(missing_load - grid_load, 0.0),
        unserved_aux_kwh=max(missing_aux - grid_aux, 0.0),
    )


def replay(
    frames: tuple[PlantFrame, ...],
    units: tuple[StorageUnit, ...],
    initial: States,
    policy: Policy,
    *,
    checkpoint: Callable[[], None],
    tolerance: Tolerance,
) -> tuple[PlantFlow, ...]:
    if not frames:
        raise InvalidInput("joint replay requires a nonempty continuous horizon")
    states = initial
    _validate(frames[0], units, initial)
    flows: list[PlantFlow] = []
    for previous, current in zip(frames, frames[1:], strict=False):
        if previous.site.interval.end != current.site.interval.start:
            raise InvalidInput("joint replay cannot reset storage at a time gap")
    for frame in frames:
        checkpoint()
        flow = step(
            frame, units, states, policy(frame, units, states), tolerance=tolerance
        )
        flows.append(flow)
        states = {unit.unit.id: unit.after for unit in flow.units}
    return tuple(flows)
