"""Continuous replay through one DC bus and one net bidirectional bridge.

NUMERICAL-MODELS.md §12 fixes the topology, source boundaries and priority.
Commands are battery-terminal kW. Only delivered power advances inventory;
PV can charge before clipping, and battery discharge shares PV's inverter.
"""

from __future__ import annotations

from collections.abc import Callable

from .dc_battery_model import DcBatteryModel
from .dc_frame import DcFlows, DcFrame
from .dc_port import DcPortFrame, plan, storage_internal_losses
from .dispatch_frame import Command
from .energy_origins import EnergyOrigins
from .errors import InvalidInput

type DcPolicy = Callable[[DcFrame, DcBatteryModel, EnergyOrigins], Command]


def internal_losses(
    frame: DcFrame, model: DcBatteryModel, before: EnergyOrigins
) -> tuple[EnergyOrigins, EnergyOrigins, EnergyOrigins, float]:
    return storage_internal_losses(frame.interval, model, before)


def self_consumption(
    frame: DcFrame, model: DcBatteryModel, before: EnergyOrigins
) -> Command:
    bridge = model.bridge(frame.limits.mode)
    pv = (
        (
            frame.pv_available_dc_kw
            if model.pv_input_dc_kw is None
            else min(frame.pv_available_dc_kw, model.pv_input_dc_kw)
        )
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


def step(
    frame: DcFrame, model: DcBatteryModel, before: EnergyOrigins, command: Command
) -> DcFlows:
    """Adapt one physical port to a single site's utility-meter allocation."""
    duration = frame.interval.hours
    limits = frame.limits
    port = plan(
        DcPortFrame(
            interval=frame.interval,
            pv_available_dc_kw=frame.pv_available_dc_kw,
            aux_dc_kw=frame.aux_dc_kw,
            mode=limits.mode,
            reserve_kwh=limits.reserve_kwh,
            pv_enabled=limits.pv_enabled,
            ac_delivery_kw=frame.load_kw + frame.aux_ac_kw,
            ac_excess_limit_kw=0.0 if limits.mode == "outage" else limits.export_cap_kw,
        ),
        model,
        before,
        command,
    )
    generated_load = min(port.forward_ac_kw, frame.load_kw)
    generated_aux = min(max(port.forward_ac_kw - generated_load, 0.0), frame.aux_ac_kw)
    battery_forward_ac = (
        port.forward_ac_kw * port.battery_to_inverter_dc_kw / port.forward_dc_kw
        if port.forward_dc_kw
        else 0.0
    )
    battery_load = (
        generated_load * battery_forward_ac / port.forward_ac_kw
        if port.forward_ac_kw
        else 0.0
    )
    battery_aux_ac = (
        generated_aux * battery_forward_ac / port.forward_ac_kw
        if port.forward_ac_kw
        else 0.0
    )
    pv_load = max(generated_load - battery_load, 0.0)
    pv_aux_ac = max(generated_aux - battery_aux_ac, 0.0)
    export = limits.export_limit(max(port.pv_forward_ac_kw - pv_load - pv_aux_ac, 0.0))

    available = 0.0 if limits.mode == "outage" else limits.import_cap_kw
    reverse_aux_ac = port.auxiliary_request_ac_kw(available)
    remaining_load = max(frame.load_kw - generated_load, 0.0)
    remaining_aux = max(frame.aux_ac_kw - generated_aux, 0.0)
    grid_base = max(
        limits.import_limit(reverse_aux_ac + remaining_load + remaining_aux)
        - reverse_aux_ac,
        0.0,
    )
    grid_load = min(grid_base, remaining_load)
    grid_aux = min(max(grid_base - grid_load, 0.0), remaining_aux)
    charging_ac = 0.0
    if limits.allow_grid_charge and grid_base >= remaining_load + remaining_aux:
        room = (
            None
            if available is None
            else max(available - reverse_aux_ac - grid_base, 0.0)
        )
        charging_ac = port.charging_request_ac_kw(room, reverse_aux_ac)
    completed = port.complete(
        EnergyOrigins(0, reverse_aux_ac * duration, 0),
        EnergyOrigins(0, charging_ac * duration, 0),
    )
    reverse_ac = (
        completed.incoming_aux_ac.total + completed.incoming_charge_ac.total
    ) / duration
    reverse_dc = (
        completed.incoming_aux_dc.total + completed.incoming_charge_dc.total
    ) / duration
    removed = port.discharged_internal
    return DcFlows(
        frame=frame,
        command=command,
        before=before,
        after=completed.after,
        standing_loss=port.standing_loss,
        internal_aux=port.internal_aux,
        internal_aux_unserved_kwh=port.internal_aux_unserved_kwh,
        discharged_internal=removed,
        discharged_to_load_ac=removed.scaled(
            battery_load * duration / removed.total if removed.total else 0.0
        ),
        pv_available_dc_kw=port.pv_available_dc_kw,
        pv_input_curtailed_dc_kw=port.pv_input_curtailed_dc_kw,
        pv_to_aux_dc_kw=port.pv_to_aux_dc_kw,
        pv_charge_bus_dc_kw=port.pv_charge_bus_dc_kw,
        pv_to_inverter_dc_kw=port.pv_to_inverter_dc_kw,
        pv_curtailed_dc_kw=port.pv_curtailed_dc_kw,
        battery_to_aux_dc_kw=port.battery_to_aux_dc_kw,
        battery_to_inverter_dc_kw=port.battery_to_inverter_dc_kw,
        grid_to_aux_dc_kw=completed.incoming_aux_dc.total / duration,
        grid_charge_bus_dc_kw=completed.incoming_charge_dc.total / duration,
        charge_terminal_dc_kw=completed.charge_terminal_dc_kw,
        discharge_terminal_dc_kw=port.discharge_terminal_dc_kw,
        inverter_forward_dc_kw=port.forward_dc_kw,
        inverter_forward_ac_kw=port.forward_ac_kw,
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
        unserved_aux_dc_kw=completed.unserved_aux_dc_kw,
        charge_command_unmet_dc_kw=max(
            command.charge_kw - completed.charge_terminal_dc_kw, 0.0
        ),
        discharge_command_unmet_dc_kw=max(
            command.discharge_kw - port.discharge_terminal_dc_kw, 0.0
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
