"""Continuous replay through one DC bus and one net bidirectional bridge.

NUMERICAL-MODELS.md §12 fixes the topology, source boundaries and priority.
Commands are battery-terminal kW. Only delivered power advances inventory;
PV can charge before clipping, and battery discharge shares PV's inverter.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import cast

from .dc_battery_model import DcBatteryModel, SharedBridge
from .dc_frame import DcFlows, DcFrame
from .dispatch_frame import Command
from .energy_origins import EnergyOrigins
from .errors import EvidenceMissing, InvalidInput

type DcPolicy = Callable[[DcFrame, DcBatteryModel, EnergyOrigins], Command]


def internal_losses(
    frame: DcFrame, model: DcBatteryModel, before: EnergyOrigins
) -> tuple[EnergyOrigins, EnergyOrigins, EnergyOrigins, float]:
    fraction = -math.expm1(-model.standing_loss_rate_per_hour * frame.interval.hours)
    state, standing = before.withdraw(before.total * fraction)
    demand = model.internal_aux_kw * frame.interval.hours
    state, aux = state.withdraw(demand)
    return state, standing, aux, max(demand - aux.total, 0.0)


def self_consumption(
    frame: DcFrame, model: DcBatteryModel, before: EnergyOrigins
) -> Command:
    bridge = model.bridge(frame.limits.mode)
    pv = (
        min(frame.pv_available_dc_kw, model.pv_input_dc_kw)
        if frame.limits.pv_enabled
        else 0.0
    )
    pv_after_aux = max(pv - frame.aux_dc_kw, 0.0)
    ac_need_dc = min(
        (frame.load_kw + frame.aux_ac_kw) / bridge.eta_forward,
        bridge.forward_limit_dc_kw,
    )
    charge_bus = max(pv_after_aux - ac_need_dc, 0.0)
    discharge_bus = max(frame.aux_dc_kw - pv, 0.0) + max(ac_need_dc - pv_after_aux, 0.0)
    return Command(
        charge_bus * model.eta_bus_to_battery, discharge_bus / model.eta_battery_to_bus
    )


def _reverse_dc(
    frame: DcFrame,
    bridge: SharedBridge,
    wanted_dc: float,
    occupied_grid_ac: float,
    occupied_reverse_dc: float,
) -> float:
    if (
        wanted_dc <= 0
        or frame.limits.mode == "outage"
        or frame.limits.import_cap_kw == 0
    ):
        return 0.0
    if (
        frame.limits.import_cap_kw is not None
        and occupied_grid_ac >= frame.limits.import_cap_kw
    ):
        return 0.0
    if bridge.reverse_supported is None:
        raise EvidenceMissing(
            "reverse_conversion: requested DC supply needs explicit reverse capability"
        )
    if not bridge.reverse_supported:
        return 0.0
    eta = cast(float, bridge.eta_reverse)
    reverse_cap = min(
        cast(float, bridge.reverse_dc_kw), cast(float, bridge.reverse_ac_kw) * eta
    )
    desired_dc = min(wanted_dc, max(reverse_cap - occupied_reverse_dc, 0.0))
    desired_ac = desired_dc / eta
    grid_room = max(
        frame.limits.import_limit(occupied_grid_ac + desired_ac) - occupied_grid_ac, 0.0
    )
    return min(desired_dc, grid_room * eta)


def step(
    frame: DcFrame, model: DcBatteryModel, before: EnergyOrigins, command: Command
) -> DcFlows:
    if (
        before.total > model.usable_window_kwh
        or frame.limits.reserve_kwh > model.usable_window_kwh
    ):
        raise InvalidInput(
            "inventory and reserve must fit the declared usable DC window"
        )
    bridge = model.bridge(frame.limits.mode)
    duration = frame.interval.hours
    state, standing, internal_aux, internal_unserved = internal_losses(
        frame, model, before
    )
    potential = frame.pv_available_dc_kw if frame.limits.pv_enabled else 0.0
    pv = min(potential, model.pv_input_dc_kw)
    pv_aux_dc = min(pv, frame.aux_dc_kw)
    pv_remaining = max(pv - pv_aux_dc, 0.0)
    dc_aux_deficit = max(frame.aux_dc_kw - pv_aux_dc, 0.0)
    ac_demand = frame.load_kw + frame.aux_ac_kw

    discharge_terminal = min(
        command.discharge_kw,
        model.discharge_terminal_kw,
        max(state.total - frame.limits.reserve_kwh, 0.0)
        * model.eta_store_discharge
        / duration,
    )
    discharge_bus = discharge_terminal * model.eta_battery_to_bus
    battery_aux_dc = min(discharge_bus, dc_aux_deficit)
    shared_headroom_dc = max(bridge.forward_limit_dc_kw - pv_remaining, 0.0)
    ac_deficit_dc = max(ac_demand / bridge.eta_forward - pv_remaining, 0.0)
    battery_inv_dc = min(
        max(discharge_bus - battery_aux_dc, 0.0), shared_headroom_dc, ac_deficit_dc
    )
    actual_bus = battery_aux_dc + battery_inv_dc
    state, removed = state.withdraw(
        actual_bus / model.eta_battery_to_bus * duration / model.eta_store_discharge
    )
    # Delivery follows the actual source withdrawal. Never withdraw a command
    # and subsequently throw its battery contribution away at the inverter cap.
    discharge_terminal = removed.total * model.eta_store_discharge / duration
    delivered_bus = discharge_terminal * model.eta_battery_to_bus
    battery_aux_dc = min(delivered_bus, dc_aux_deficit)
    battery_inv_dc = max(delivered_bus - battery_aux_dc, 0.0)

    charge_terminal_bound = min(
        command.charge_kw,
        model.charge_terminal_kw,
        max(model.usable_window_kwh - state.total, 0.0)
        / (model.eta_store_charge * duration),
    )
    charge_bus_bound = charge_terminal_bound / model.eta_bus_to_battery
    retained_pv_dc = min(
        ac_demand / bridge.eta_forward,
        bridge.forward_limit_dc_kw,
    )
    pv_charge = min(charge_bus_bound, max(pv_remaining - retained_pv_dc, 0.0))
    pv_remaining = max(pv_remaining - pv_charge, 0.0)

    allowed_export = frame.limits.export_limit(pv_remaining * bridge.eta_forward)
    pv_inv_dc = min(
        pv_remaining,
        bridge.forward_limit_dc_kw,
        (ac_demand + allowed_export) / bridge.eta_forward,
    )
    forward_dc = pv_inv_dc + battery_inv_dc
    forward_ac = forward_dc * bridge.eta_forward
    # One combined conversion, then proportional source attribution. Exports
    # contain PV only: battery power was bounded by the AC demand deficit.
    battery_forward_ac = forward_ac * battery_inv_dc / forward_dc if forward_dc else 0.0
    pv_forward_ac = max(forward_ac - battery_forward_ac, 0.0)
    generated_load = min(forward_ac, frame.load_kw)
    generated_aux = min(max(forward_ac - generated_load, 0.0), frame.aux_ac_kw)
    battery_load = (
        generated_load * battery_forward_ac / forward_ac if forward_ac else 0.0
    )
    battery_aux_ac = (
        generated_aux * battery_forward_ac / forward_ac if forward_ac else 0.0
    )
    pv_load = max(generated_load - battery_load, 0.0)
    pv_aux_ac = max(generated_aux - battery_aux_ac, 0.0)
    export = min(max(pv_forward_ac - pv_load - pv_aux_ac, 0.0), allowed_export)

    reverse_aux_dc = 0.0
    dc_aux_remaining = max(dc_aux_deficit - battery_aux_dc, 0.0)
    if forward_dc == 0:
        reverse_aux_dc = _reverse_dc(frame, bridge, dc_aux_remaining, 0.0, 0.0)
    reverse_aux_ac = (
        reverse_aux_dc / cast(float, bridge.eta_reverse) if reverse_aux_dc else 0.0
    )
    remaining_load = max(frame.load_kw - generated_load, 0.0)
    remaining_aux = max(frame.aux_ac_kw - generated_aux, 0.0)
    grid_base = max(
        frame.limits.import_limit(reverse_aux_ac + remaining_load + remaining_aux)
        - reverse_aux_ac,
        0.0,
    )
    grid_load = min(grid_base, remaining_load)
    grid_aux = min(max(grid_base - grid_load, 0.0), remaining_aux)
    grid_charge = 0.0
    if (
        frame.limits.allow_grid_charge
        and forward_dc == 0
        and grid_base >= remaining_load + remaining_aux
    ):
        grid_charge = _reverse_dc(
            frame,
            bridge,
            max(charge_bus_bound - pv_charge, 0.0),
            reverse_aux_ac + grid_base,
            reverse_aux_dc,
        )
    charge_terminal = (pv_charge + grid_charge) * model.eta_bus_to_battery
    state = state.plus(
        EnergyOrigins(
            pv_charge * model.eta_bus_to_battery * model.eta_store_charge * duration,
            grid_charge * model.eta_bus_to_battery * model.eta_store_charge * duration,
            0.0,
        )
    )
    discharged_to_load = removed.scaled(
        battery_load * duration / removed.total if removed.total else 0.0
    )
    reverse_dc = reverse_aux_dc + grid_charge
    reverse_ac = reverse_dc / cast(float, bridge.eta_reverse) if reverse_dc else 0.0
    return DcFlows(
        frame=frame,
        command=command,
        before=before,
        after=state,
        standing_loss=standing,
        internal_aux=internal_aux,
        internal_aux_unserved_kwh=internal_unserved,
        discharged_internal=removed,
        discharged_to_load_ac=discharged_to_load,
        pv_available_dc_kw=pv,
        pv_input_curtailed_dc_kw=potential - pv,
        pv_to_aux_dc_kw=pv_aux_dc,
        pv_charge_bus_dc_kw=pv_charge,
        pv_to_inverter_dc_kw=pv_inv_dc,
        pv_curtailed_dc_kw=max(pv_remaining - pv_inv_dc, 0.0),
        battery_to_aux_dc_kw=battery_aux_dc,
        battery_to_inverter_dc_kw=battery_inv_dc,
        grid_to_aux_dc_kw=reverse_aux_dc,
        grid_charge_bus_dc_kw=grid_charge,
        charge_terminal_dc_kw=charge_terminal,
        discharge_terminal_dc_kw=discharge_terminal,
        inverter_forward_dc_kw=forward_dc,
        inverter_forward_ac_kw=forward_ac,
        inverter_reverse_dc_kw=reverse_dc,
        inverter_reverse_ac_kw=reverse_ac,
        pv_to_load_ac_kw=pv_load,
        pv_to_aux_ac_kw=pv_aux_ac,
        battery_to_aux_ac_kw=battery_aux_ac,
        grid_to_load_ac_kw=grid_load,
        grid_to_aux_ac_kw=grid_aux,
        import_ac_kw=grid_base + reverse_ac,
        export_ac_kw=export,
        unserved_load_ac_kw=max(remaining_load - grid_load, 0.0),
        unserved_aux_ac_kw=max(remaining_aux - grid_aux, 0.0),
        unserved_aux_dc_kw=max(dc_aux_remaining - reverse_aux_dc, 0.0),
        charge_command_unmet_dc_kw=max(command.charge_kw - charge_terminal, 0.0),
        discharge_command_unmet_dc_kw=max(
            command.discharge_kw - discharge_terminal, 0.0
        ),
    )


def replay(
    frames: tuple[DcFrame, ...],
    model: DcBatteryModel,
    initial: EnergyOrigins,
    policy: DcPolicy,
    *,
    checkpoint: Callable[[], None],
) -> tuple[DcFlows, ...]:
    if not frames:
        raise InvalidInput("DC replay requires a nonempty horizon")
    result: list[DcFlows] = []
    state = initial
    previous: DcFrame | None = None
    for frame in frames:
        checkpoint()
        if previous is not None and previous.interval.end != frame.interval.start:
            raise InvalidInput("DC replay intervals must be continuous")
        flow = step(frame, model, state, policy(frame, model, state))
        result.append(flow)
        state = flow.after
        previous = frame
    return tuple(result)
