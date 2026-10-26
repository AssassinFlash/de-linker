"""One physical shared-DC converter port, independent of the utility meter.

NUMERICAL-MODELS section12 supplies the directional equations. Planning
returns the bounded forward offer; completion consumes explicitly sourced AC
packets for the remaining DC auxiliary demand and optional charging. Unused
packets are returned, never counted as delivered or used to patch inventory.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal, cast

from .battery_model import nonnegative
from .dc_battery_model import DcBatteryModel, SharedBridge
from .dispatch_frame import Command
from .energy_origins import EnergyOrigins
from .errors import EvidenceMissing, InvalidInput
from .interval import Interval


@dataclass(frozen=True)
class DcPortFrame:
    interval: Interval
    pv_available_dc_kw: float
    aux_dc_kw: float
    mode: Literal["connected", "outage"]
    reserve_kwh: float
    pv_enabled: bool
    ac_delivery_kw: float
    ac_excess_limit_kw: float | None

    def __post_init__(self) -> None:
        if (
            self.mode not in {"connected", "outage"}
            or type(self.pv_enabled) is not bool
        ):
            raise InvalidInput(
                "an explicit port operating mode and PV state are required"
            )
        for name in (
            "pv_available_dc_kw",
            "aux_dc_kw",
            "reserve_kwh",
            "ac_delivery_kw",
        ):
            nonnegative(getattr(self, name), name)
        if self.ac_excess_limit_kw is not None:
            nonnegative(self.ac_excess_limit_kw, "accepted excess AC injection")


@dataclass(frozen=True)
class DcPortFlow:
    plan: DcPortPlan
    after: EnergyOrigins
    incoming_aux_ac: EnergyOrigins
    incoming_charge_ac: EnergyOrigins
    unused_aux_ac: EnergyOrigins
    unused_charge_ac: EnergyOrigins
    incoming_aux_dc: EnergyOrigins
    incoming_charge_dc: EnergyOrigins

    @property
    def charge_terminal_dc_kw(self) -> float:
        p = self.plan
        return (
            p.pv_charge_bus_dc_kw
            + self.incoming_charge_dc.total / p.frame.interval.hours
        ) * p.model.eta_bus_to_battery

    @property
    def unserved_aux_dc_kw(self) -> float:
        return max(
            self.plan.aux_dc_remaining_kw
            - self.incoming_aux_dc.total / self.plan.frame.interval.hours,
            0.0,
        )


@dataclass(frozen=True)
class DcPortPlan:
    frame: DcPortFrame
    model: DcBatteryModel
    command: Command
    before: EnergyOrigins
    _state: EnergyOrigins
    standing_loss: EnergyOrigins
    internal_aux: EnergyOrigins
    internal_aux_unserved_kwh: float
    discharged_internal: EnergyOrigins
    pv_available_dc_kw: float
    pv_input_curtailed_dc_kw: float
    pv_to_aux_dc_kw: float
    pv_charge_bus_dc_kw: float
    pv_to_inverter_dc_kw: float
    pv_curtailed_dc_kw: float
    battery_to_aux_dc_kw: float
    battery_to_inverter_dc_kw: float
    discharge_terminal_dc_kw: float
    forward_dc_kw: float
    forward_ac_kw: float
    pv_forward_ac_kw: float
    battery_forward_ac: EnergyOrigins
    _charge_bus_bound_kw: float
    aux_dc_remaining_kw: float

    @property
    def bridge(self) -> SharedBridge:
        return self.model.bridge(self.frame.mode)

    def accept_forward_pv(self, accepted_ac_kw: float) -> DcPortPlan:
        """Back off unused PV before conversion; battery withdrawal stays distinct."""
        nonnegative(accepted_ac_kw, "accepted PV AC injection")
        if accepted_ac_kw > self.pv_forward_ac_kw:
            raise InvalidInput(
                "accepted PV injection exceeds the planned producer offer"
            )
        if accepted_ac_kw == self.pv_forward_ac_kw:
            return self
        pv_dc = min(self.pv_to_inverter_dc_kw, accepted_ac_kw / self.bridge.eta_forward)
        forward_dc = pv_dc + self.battery_to_inverter_dc_kw
        return replace(
            self,
            pv_to_inverter_dc_kw=pv_dc,
            pv_curtailed_dc_kw=self.pv_curtailed_dc_kw
            + self.pv_to_inverter_dc_kw
            - pv_dc,
            forward_dc_kw=forward_dc,
            forward_ac_kw=forward_dc * self.bridge.eta_forward,
            pv_forward_ac_kw=pv_dc * self.bridge.eta_forward,
        )

    def _reverse_dc(
        self,
        wanted_dc_kw: float,
        available_ac_kw: float | None,
        occupied_ac_kw: float = 0.0,
    ) -> float:
        if available_ac_kw is not None:
            nonnegative(available_ac_kw, "available incoming AC")
        if wanted_dc_kw <= 0 or available_ac_kw == 0 or self.forward_dc_kw > 0:
            return 0.0
        bridge = self.bridge
        if bridge.reverse_supported is None:
            raise EvidenceMissing(
                "reverse_conversion: requested DC supply needs explicit reverse capability",
                constraint_id="explicit_reverse_capability",
            )
        if not bridge.reverse_supported:
            return 0.0
        eta = cast(float, bridge.eta_reverse)
        cap_dc = cast(float, bridge.reverse_ac_kw) * eta
        if bridge.reverse_dc_kw is not None:
            cap_dc = min(cap_dc, bridge.reverse_dc_kw)
        wanted = min(wanted_dc_kw, max(cap_dc - occupied_ac_kw * eta, 0.0))
        return wanted if available_ac_kw is None else min(wanted, available_ac_kw * eta)

    def auxiliary_request_ac_kw(self, available_ac_kw: float | None) -> float:
        dc = self._reverse_dc(self.aux_dc_remaining_kw, available_ac_kw)
        return dc / cast(float, self.bridge.eta_reverse) if dc else 0.0

    def charging_request_ac_kw(
        self, available_ac_kw: float | None, auxiliary_ac_kw: float
    ) -> float:
        nonnegative(auxiliary_ac_kw, "occupied auxiliary AC input")
        dc = self._reverse_dc(
            max(self._charge_bus_bound_kw - self.pv_charge_bus_dc_kw, 0.0),
            available_ac_kw,
            auxiliary_ac_kw,
        )
        return dc / cast(float, self.bridge.eta_reverse) if dc else 0.0

    def complete(
        self, auxiliary_ac: EnergyOrigins, charging_ac: EnergyOrigins
    ) -> DcPortFlow:
        """Consume bounded packets at this AC terminal, preserving all origins."""
        dt = self.frame.interval.hours
        aux_cap = (
            self.auxiliary_request_ac_kw(auxiliary_ac.total / dt)
            if auxiliary_ac.total
            else 0.0
        )
        unused_aux, supplied_aux = auxiliary_ac.withdraw(aux_cap * dt)
        charge_cap = (
            self.charging_request_ac_kw(charging_ac.total / dt, supplied_aux.total / dt)
            if charging_ac.total
            else 0.0
        )
        unused_charge, supplied_charge = charging_ac.withdraw(charge_cap * dt)
        eta_reverse = (
            cast(float, self.bridge.eta_reverse)
            if supplied_aux.total or supplied_charge.total
            else 1.0
        )
        aux_dc = supplied_aux.scaled(eta_reverse)
        charge_dc = supplied_charge.scaled(eta_reverse)
        local_charge = EnergyOrigins(self.pv_charge_bus_dc_kw * dt, 0, 0)
        after = self._state.plus(
            local_charge.plus(charge_dc).scaled(
                self.model.eta_bus_to_battery * self.model.eta_store_charge
            )
        )
        return DcPortFlow(
            self,
            after,
            supplied_aux,
            supplied_charge,
            unused_aux,
            unused_charge,
            aux_dc,
            charge_dc,
        )


def storage_internal_losses(
    interval: Interval, model: DcBatteryModel, before: EnergyOrigins
) -> tuple[EnergyOrigins, EnergyOrigins, EnergyOrigins, float]:
    fraction = -math.expm1(-model.standing_loss_rate_per_hour * interval.hours)
    state, standing = before.withdraw(before.total * fraction)
    demand = model.internal_aux_kw * interval.hours
    state, aux = state.withdraw(demand)
    return state, standing, aux, max(demand - aux.total, 0.0)


def plan(
    frame: DcPortFrame, model: DcBatteryModel, before: EnergyOrigins, command: Command
) -> DcPortPlan:
    if (
        before.total > model.usable_window_kwh
        or frame.reserve_kwh > model.usable_window_kwh
    ):
        raise InvalidInput("inventory and reserve must fit the documented port window")
    bridge, dt = model.bridge(frame.mode), frame.interval.hours
    state, standing, internal_aux, unserved = storage_internal_losses(
        frame.interval, model, before
    )
    potential = frame.pv_available_dc_kw if frame.pv_enabled else 0.0
    pv = (
        potential
        if model.pv_input_dc_kw is None
        else min(potential, model.pv_input_dc_kw)
    )
    pv_aux = min(pv, frame.aux_dc_kw)
    remaining = max(pv - pv_aux, 0.0)
    aux_deficit = max(frame.aux_dc_kw - pv_aux, 0.0)
    discharge_terminal = min(
        command.discharge_kw,
        model.discharge_terminal_kw,
        max(state.total - frame.reserve_kwh, 0.0) * model.eta_store_discharge / dt,
    )
    discharge_bus = discharge_terminal * model.eta_battery_to_bus
    battery_aux = min(discharge_bus, aux_deficit)
    battery_forward = min(
        max(discharge_bus - battery_aux, 0.0),
        max(bridge.forward_limit_dc_kw - remaining, 0.0),
        max(frame.ac_delivery_kw / bridge.eta_forward - remaining, 0.0),
    )
    state, removed = state.withdraw(
        (battery_aux + battery_forward)
        / model.eta_battery_to_bus
        * dt
        / model.eta_store_discharge
    )
    discharge_terminal = removed.total * model.eta_store_discharge / dt
    delivered_bus = discharge_terminal * model.eta_battery_to_bus
    battery_aux = min(delivered_bus, aux_deficit)
    battery_forward = max(delivered_bus - battery_aux, 0.0)
    charge_terminal_bound = min(
        command.charge_kw,
        model.charge_terminal_kw,
        max(model.usable_window_kwh - state.total, 0.0) / (model.eta_store_charge * dt),
    )
    charge_bus_bound = charge_terminal_bound / model.eta_bus_to_battery
    retained_pv = min(
        frame.ac_delivery_kw / bridge.eta_forward, bridge.forward_limit_dc_kw
    )
    pv_charge = min(charge_bus_bound, max(remaining - retained_pv, 0.0))
    remaining = max(remaining - pv_charge, 0.0)
    extra = remaining * bridge.eta_forward
    if frame.ac_excess_limit_kw is not None:
        extra = min(extra, frame.ac_excess_limit_kw)
    pv_forward = min(
        remaining,
        bridge.forward_limit_dc_kw,
        (frame.ac_delivery_kw + extra) / bridge.eta_forward,
    )
    forward_dc = pv_forward + battery_forward
    forward_ac = forward_dc * bridge.eta_forward
    battery_ac_kw = forward_ac * battery_forward / forward_dc if forward_dc else 0.0
    battery_ac = removed.scaled(
        battery_ac_kw * dt / removed.total if removed.total else 0.0
    )
    return DcPortPlan(
        frame=frame,
        model=model,
        command=command,
        before=before,
        _state=state,
        standing_loss=standing,
        internal_aux=internal_aux,
        internal_aux_unserved_kwh=unserved,
        discharged_internal=removed,
        pv_available_dc_kw=pv,
        pv_input_curtailed_dc_kw=potential - pv,
        pv_to_aux_dc_kw=pv_aux,
        pv_charge_bus_dc_kw=pv_charge,
        pv_to_inverter_dc_kw=pv_forward,
        pv_curtailed_dc_kw=max(remaining - pv_forward, 0.0),
        battery_to_aux_dc_kw=battery_aux,
        battery_to_inverter_dc_kw=battery_forward,
        discharge_terminal_dc_kw=discharge_terminal,
        forward_dc_kw=forward_dc,
        forward_ac_kw=forward_ac,
        pv_forward_ac_kw=max(forward_ac - battery_ac_kw, 0.0),
        battery_forward_ac=battery_ac,
        _charge_bus_bound_kw=charge_bus_bound,
        aux_dc_remaining_kw=max(aux_deficit - battery_aux, 0.0),
    )
