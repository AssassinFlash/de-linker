"""Exact rational net-flow witness for hard inventory/task boundaries.

Fraction represents each declared binary float exactly. It independently
bounds commanded power by inventory/ports and integrates it on the exact time
axis, rather than adding already rounded proportional-source withdrawals.
No stock ULP is earned by an idle frame or an exact cycle.
This is a verifier witness, never the actuator or a replacement battery model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from .battery_model import BatteryModel
from .dispatch_frame import Flows
from .energy_origins import EnergyOrigins

if TYPE_CHECKING:
    from .dc_battery_model import DcBatteryModel
    from .dc_frame import DcFlows
    from .dc_port import DcPortFlow
    from .dispatch_frame import Command
    from .interval import Interval
    from .plant_energy_model import StorageFlow


def _energy(value: EnergyOrigins) -> Fraction:
    return sum(
        (
            Fraction(item)
            for item in (value.pv_kwh, value.grid_kwh, value.initial_unknown_kwh)
        ),
        Fraction(),
    )


@dataclass(frozen=True)
class InventoryBoundary:
    capacity_violation_kwh: float
    reserve_violation_kwh: float
    tracked_deviation_kwh: float
    charge_kw: float
    discharge_kw: float


@dataclass(frozen=True)
class _BoundedTransfer:
    interval: Interval
    before: EnergyOrigins
    after: EnergyOrigins
    standing_loss: EnergyOrigins
    internal_aux: EnergyOrigins
    command: Command
    capacity_kwh: float
    reserve_kwh: float
    eta_charge: float
    eta_discharge: float
    charge_limit_kw: float
    discharge_limit_kw: float
    actual_charge_kw: float
    actual_discharge_kw: float
    standing_rate_per_hour: float
    internal_aux_kw: float


class InventoryWitness:
    def __init__(self, initial: EnergyOrigins) -> None:
        self.energy = _energy(initial)

    def advance(self, flow: Flows, model: BatteryModel) -> InventoryBoundary:
        before = self.energy
        frame, limits = flow.frame, flow.frame.limits
        dt = Fraction(frame.interval.duration_us, 3_600_000_000)
        eta_c, eta_d = Fraction(model.eta_charge), Fraction(model.eta_discharge)
        # The named loss fraction is evaluated once in float64, as in the
        # declared model. Only the small loss transfer is rounded; the large
        # stock is not repeatedly rounded or used as an error allowance.
        loss_fraction = -math.expm1(
            -model.standing_loss_rate_per_hour * frame.interval.hours
        )
        standing = Fraction(float(before) * loss_fraction)
        post_standing = max(before - standing, Fraction())
        internal_aux = min(Fraction(model.internal_aux_kw) * dt, post_standing)
        after_losses = post_standing - internal_aux
        pv = Fraction(frame.pv_potential_kw) if limits.pv_enabled else Fraction()
        load, aux = Fraction(frame.load_kw), Fraction(frame.aux_ac_kw)
        direct_load = min(pv, load)
        direct_aux = min(pv - direct_load, aux)
        deficit = load + aux - direct_load - direct_aux
        discharge = min(
            Fraction(flow.command.discharge_kw),
            Fraction(model.discharge_ac_kw),
            max(after_losses - Fraction(limits.reserve_kwh), Fraction()) * eta_d / dt,
            deficit,
        )
        after_discharge = after_losses - discharge * dt / eta_d
        remaining_demand = max(deficit - discharge, Fraction())
        import_cap = (
            Fraction()
            if limits.mode == "outage"
            else Fraction(limits.import_cap_kw)
            if limits.import_cap_kw is not None
            else None
        )
        grid_load = (
            remaining_demand
            if import_cap is None
            else min(remaining_demand, import_cap)
        )
        headroom = max(Fraction(model.usable_window_kwh) - after_discharge, Fraction())
        charge_bound = min(
            Fraction(flow.command.charge_kw),
            Fraction(model.charge_ac_kw),
            headroom / (eta_c * dt),
        )
        surplus = max(pv - direct_load - direct_aux, Fraction())
        pv_charge = min(charge_bound, surplus)
        grid_charge = Fraction()
        if limits.mode == "connected" and limits.allow_grid_charge:
            grid_charge = charge_bound - pv_charge
            if import_cap is not None:
                grid_charge = min(grid_charge, max(import_cap - grid_load, Fraction()))
        charge = pv_charge + grid_charge
        self.energy = after_discharge + charge * dt * eta_c
        tracked_before = _energy(flow.before)
        tracked_after_losses = (
            tracked_before - _energy(flow.standing_loss) - _energy(flow.internal_aux)
        )
        tracked_after = _energy(flow.after)
        deviation = max(
            abs(before - tracked_before),
            abs(after_losses - tracked_after_losses),
            abs(self.energy - tracked_after),
        )
        return InventoryBoundary(
            float(max(before, self.energy) - Fraction(model.usable_window_kwh)),
            float(
                Fraction(flow.frame.limits.reserve_kwh)
                - min(before, after_losses, self.energy)
            ),
            float(deviation),
            float(charge),
            float(discharge),
        )

    def terminal_violation(self, minimum_kwh: float) -> float:
        return float(Fraction(minimum_kwh) - self.energy)

    def advance_dc(self, flow: DcFlows, model: DcBatteryModel) -> InventoryBoundary:
        """DC paths retain their own checks; only admissible transfer finances stock."""
        return self._advance_bounded(
            _BoundedTransfer(
                flow.frame.interval,
                flow.before,
                flow.after,
                flow.standing_loss,
                flow.internal_aux,
                flow.command,
                model.usable_window_kwh,
                flow.frame.limits.reserve_kwh,
                model.eta_store_charge,
                model.eta_store_discharge,
                model.charge_terminal_kw,
                model.discharge_terminal_kw,
                flow.charge_terminal_dc_kw,
                flow.discharge_terminal_dc_kw,
                model.standing_loss_rate_per_hour,
                model.internal_aux_kw,
            )
        )

    def advance_storage(
        self, flow: StorageFlow, interval: Interval
    ) -> InventoryBoundary:
        """Each physical plant unit has a separate conserved rational budget."""
        model = flow.unit.for_mode(flow.mode)
        return self._advance_bounded(
            _BoundedTransfer(
                interval,
                flow.before,
                flow.after,
                flow.standing_loss,
                flow.internal_aux,
                flow.command,
                model.usable_window_kwh,
                flow.reserve_kwh,
                model.eta_charge,
                model.eta_discharge,
                model.charge_ac_kw,
                model.discharge_ac_kw,
                flow.received_ac.total / interval.hours,
                flow.delivered_ac.total / interval.hours,
                model.standing_loss_rate_per_hour,
                model.internal_aux_kw,
            )
        )

    def advance_dc_port(self, flow: DcPortFlow) -> InventoryBoundary:
        """Use the same hard stock witness for a converter on a common AC bus."""
        p, model = flow.plan, flow.plan.model
        return self._advance_bounded(
            _BoundedTransfer(
                p.frame.interval,
                p.before,
                flow.after,
                p.standing_loss,
                p.internal_aux,
                p.command,
                model.usable_window_kwh,
                p.frame.reserve_kwh,
                model.eta_store_charge,
                model.eta_store_discharge,
                model.charge_terminal_kw,
                model.discharge_terminal_kw,
                flow.charge_terminal_dc_kw,
                p.discharge_terminal_dc_kw,
                model.standing_loss_rate_per_hour,
                model.internal_aux_kw,
            )
        )

    def _advance_bounded(self, step: _BoundedTransfer) -> InventoryBoundary:
        before = self.energy
        dt = Fraction(step.interval.duration_us, 3_600_000_000)
        eta_c, eta_d = Fraction(step.eta_charge), Fraction(step.eta_discharge)
        fraction = -math.expm1(-step.standing_rate_per_hour * step.interval.hours)
        standing = Fraction(float(before) * fraction)
        post_standing = max(before - standing, Fraction())
        after_losses = post_standing - min(
            Fraction(step.internal_aux_kw) * dt, post_standing
        )
        discharge_bound = min(
            Fraction(step.command.discharge_kw),
            Fraction(step.discharge_limit_kw),
            max(after_losses - Fraction(step.reserve_kwh), Fraction()) * eta_d / dt,
        )
        discharge = min(Fraction(step.actual_discharge_kw), discharge_bound)
        after_discharge = after_losses - discharge * dt / eta_d
        charge_bound = min(
            Fraction(step.command.charge_kw),
            Fraction(step.charge_limit_kw),
            max(Fraction(step.capacity_kwh) - after_discharge, Fraction())
            / (eta_c * dt),
        )
        charge = min(Fraction(step.actual_charge_kw), charge_bound)
        self.energy = after_discharge + charge * dt * eta_c
        deviation = max(
            abs(before - _energy(step.before)),
            abs(
                after_losses
                - (
                    _energy(step.before)
                    - _energy(step.standing_loss)
                    - _energy(step.internal_aux)
                )
            ),
            abs(self.energy - _energy(step.after)),
        )
        return InventoryBoundary(
            float(
                max(before, self.energy, _energy(step.before), _energy(step.after))
                - Fraction(step.capacity_kwh)
            ),
            float(
                Fraction(step.reserve_kwh)
                - min(before, after_losses, after_discharge, self.energy)
            ),
            float(deviation),
            float(charge_bound),
            float(discharge_bound),
        )
