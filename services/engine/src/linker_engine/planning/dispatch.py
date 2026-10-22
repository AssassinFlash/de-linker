"""Deterministic continuous energy replay on a single AC bus.

Equations and independent references: NUMERICAL-MODELS.md §§5–8. Physical
limits act before power is delivered. Missing supply stays in the ledger.
Policies, ideal feasibility, equipment release and country rules are separate.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from .battery_model import BatteryModel
from .dispatch_frame import Command, Flows, Frame
from .energy_origins import EnergyOrigins
from .errors import InvalidInput
from .numerical_tolerance import Tolerance

type Policy = Callable[[Frame, BatteryModel, EnergyOrigins], Command]


def _losses(
    frame: Frame,
    model: BatteryModel,
    before: EnergyOrigins,
) -> tuple[EnergyOrigins, EnergyOrigins, EnergyOrigins, float]:
    duration = frame.interval.hours
    fraction_lost = -math.expm1(-model.standing_loss_rate_per_hour * duration)
    state, standing_loss = before.withdraw(before.total * fraction_lost)
    aux_demand = model.internal_aux_kw * duration
    state, internal_aux = state.withdraw(aux_demand)
    return state, standing_loss, internal_aux, max(aux_demand - internal_aux.total, 0.0)


def self_consumption_with_reserve(
    frame: Frame, model: BatteryModel, state: EnergyOrigins
) -> Command:
    """Executable local policy, with no forecast or grid-recharge promise."""
    pv = frame.pv_potential_kw if frame.limits.pv_enabled else 0.0
    balance = pv - frame.load_kw - frame.aux_ac_kw
    state, _, _, _ = _losses(frame, model, state)
    duration = frame.interval.hours
    charge = min(
        max(balance, 0.0),
        model.charge_ac_kw,
        max(model.usable_window_kwh - state.total, 0.0) / (model.eta_charge * duration),
    )
    discharge = min(
        max(-balance, 0.0),
        model.discharge_ac_kw,
        max(state.total - frame.limits.reserve_kwh, 0.0)
        * model.eta_discharge
        / duration,
    )
    return Command(charge, discharge)


def step(
    frame: Frame,
    model: BatteryModel,
    before: EnergyOrigins,
    command: Command,
    *,
    tolerance: Tolerance,
) -> Flows:
    arithmetic_allowance = tolerance.absolute_kwh + tolerance.relative * max(
        before.total, model.usable_window_kwh
    )
    if not math.isfinite(arithmetic_allowance):
        raise InvalidInput("numerical tolerance exceeds finite domain")
    if (
        before.total - model.usable_window_kwh > arithmetic_allowance
        or frame.limits.reserve_kwh > model.usable_window_kwh
    ):
        raise InvalidInput("initial inventory and reserve must fit the usable window")
    duration = frame.interval.hours
    state, standing_loss, internal_aux, internal_aux_unserved = _losses(
        frame, model, before
    )
    available = frame.pv_potential_kw if frame.limits.pv_enabled else 0.0
    pv_load = min(available, frame.load_kw)
    pv_aux = min(available - pv_load, frame.aux_ac_kw)
    load_deficit = frame.load_kw - pv_load
    aux_deficit = frame.aux_ac_kw - pv_aux
    available_discharge = max(state.total - frame.limits.reserve_kwh, 0.0)
    discharge = min(
        command.discharge_kw,
        model.discharge_ac_kw,
        available_discharge * model.eta_discharge / duration,
        load_deficit + aux_deficit,
    )
    state, discharged_internal = state.withdraw(
        discharge * duration / model.eta_discharge
    )
    # Reconstruct delivery from actual removed energy, never from an unclipped
    # request. Any unavailable command remains visible in its unmet field.
    delivered = discharged_internal.scaled(model.eta_discharge)
    discharge = delivered.total / duration
    discharge_load = min(discharge, load_deficit)
    discharge_aux = max(discharge - discharge_load, 0.0)
    origins_to_load = delivered.scaled(discharge_load / discharge if discharge else 0.0)
    remaining_load = max(load_deficit - discharge_load, 0.0)
    remaining_aux = max(aux_deficit - discharge_aux, 0.0)
    grid_base = frame.limits.import_limit(remaining_load + remaining_aux)
    grid_load = min(grid_base, remaining_load)
    grid_aux = max(grid_base - grid_load, 0.0)
    surplus = max(available - pv_load - pv_aux, 0.0)
    charge_bound = min(
        command.charge_kw,
        model.charge_ac_kw,
        max(model.usable_window_kwh - state.total, 0.0) / (model.eta_charge * duration),
    )
    pv_charge = min(charge_bound, surplus)
    grid_charge = 0.0
    if frame.limits.allow_grid_charge:
        desired_import = grid_base + charge_bound - pv_charge
        grid_charge = max(frame.limits.import_limit(desired_import) - grid_base, 0.0)
    charge = pv_charge + grid_charge
    state = state.plus(
        EnergyOrigins(
            pv_charge * model.eta_charge * duration,
            grid_charge * model.eta_charge * duration,
            0.0,
        )
    )
    remaining_surplus = max(surplus - pv_charge, 0.0)
    export = frame.limits.export_limit(remaining_surplus)
    return Flows(
        frame=frame,
        command=command,
        before=before,
        after=state,
        standing_loss=standing_loss,
        internal_aux=internal_aux,
        internal_aux_unserved_kwh=internal_aux_unserved,
        discharged_internal=discharged_internal,
        discharged_to_load_ac=origins_to_load,
        pv_available_kw=available,
        pv_to_load_kw=pv_load,
        pv_to_aux_kw=pv_aux,
        pv_charge_kw=pv_charge,
        grid_charge_kw=grid_charge,
        discharge_kw=discharge,
        charge_kw=charge,
        grid_to_load_kw=grid_load,
        grid_to_aux_kw=grid_aux,
        import_kw=grid_base + grid_charge,
        export_kw=export,
        curtailed_kw=remaining_surplus - export,
        unserved_load_kw=max(remaining_load - grid_load, 0.0),
        unserved_aux_kw=max(remaining_aux - grid_aux, 0.0),
        charge_command_unmet_kw=max(command.charge_kw - charge, 0.0),
        discharge_command_unmet_kw=max(command.discharge_kw - discharge, 0.0),
    )


def replay(
    frames: tuple[Frame, ...],
    model: BatteryModel,
    initial: EnergyOrigins,
    policy: Policy,
    *,
    checkpoint: Callable[[], None],
    tolerance: Tolerance,
) -> tuple[Flows, ...]:
    if not frames:
        raise InvalidInput("replay requires a nonempty horizon")
    # Caller-supplied initial energy is a physical input. Subsequent float64
    # states may have arithmetic residuals within the recorded tolerance; no
    # inventory/source is clipped or erased, and the verifier retains them.
    if initial.total > model.usable_window_kwh:
        raise InvalidInput("initial inventory exceeds the usable window")
    for previous, current in zip(frames, frames[1:], strict=False):
        if previous.interval.end != current.interval.start:
            raise InvalidInput("replay requires a continuous ordered horizon")
    state = initial
    result: list[Flows] = []
    for frame in frames:
        checkpoint()
        flow = step(
            frame, model, state, policy(frame, model, state), tolerance=tolerance
        )
        result.append(flow)
        state = flow.after
    return tuple(result)
