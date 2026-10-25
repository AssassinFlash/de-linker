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
        """Integrate actual terminal transfers on exact time, without rounding stock.

        DC path/priority limits are checked independently by the DC verifier.
        These returned powers are upper inventory/command bounds, not a second
        dispatch policy. Fixed kWh tolerances cannot finance any DC delivery.
        """
        before = self.energy
        dt = Fraction(flow.frame.interval.duration_us, 3_600_000_000)
        eta_c, eta_d = (
            Fraction(model.eta_store_charge),
            Fraction(model.eta_store_discharge),
        )
        fraction = -math.expm1(
            -model.standing_loss_rate_per_hour * flow.frame.interval.hours
        )
        standing = Fraction(float(before) * fraction)
        post_standing = max(before - standing, Fraction())
        after_losses = post_standing - min(
            Fraction(model.internal_aux_kw) * dt, post_standing
        )
        discharge_bound = min(
            Fraction(flow.command.discharge_kw),
            Fraction(model.discharge_terminal_kw),
            max(after_losses - Fraction(flow.frame.limits.reserve_kwh), Fraction())
            * eta_d
            / dt,
        )
        # As in the AC witness, only independently admissible transfer enters
        # the conserved budget. The DC verifier separately requires the actual
        # reported power to fit this bound within its local representation ULPs.
        # It never lends an absolute kWh allowance to a short interval.
        discharge = min(Fraction(flow.discharge_terminal_dc_kw), discharge_bound)
        after_discharge = after_losses - discharge * dt / eta_d
        charge_bound = min(
            Fraction(flow.command.charge_kw),
            Fraction(model.charge_terminal_kw),
            max(Fraction(model.usable_window_kwh) - after_discharge, Fraction())
            / (eta_c * dt),
        )
        charge = min(Fraction(flow.charge_terminal_dc_kw), charge_bound)
        self.energy = after_discharge + charge * dt * eta_c
        deviation = max(
            abs(before - _energy(flow.before)),
            abs(
                after_losses
                - (
                    _energy(flow.before)
                    - _energy(flow.standing_loss)
                    - _energy(flow.internal_aux)
                )
            ),
            abs(self.energy - _energy(flow.after)),
        )
        return InventoryBoundary(
            float(
                max(before, self.energy, _energy(flow.before), _energy(flow.after))
                - Fraction(model.usable_window_kwh)
            ),
            float(
                Fraction(flow.frame.limits.reserve_kwh)
                - min(before, after_losses, after_discharge, self.energy)
            ),
            float(deviation),
            float(charge_bound),
            float(discharge_bound),
        )
