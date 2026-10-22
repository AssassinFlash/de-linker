"""Exact rational net-flow witness for hard inventory/task boundaries.

Fraction represents each recorded binary float exactly. Its net-flow sum does
not accumulate a fresh inventory ULP for an idle frame or an exact cycle.
Source/power/model checks separately validate the recorded transfer amounts.
This is a verifier witness, never the actuator or a replacement battery model.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .battery_model import BatteryModel
from .dispatch_frame import Flows
from .energy_origins import EnergyOrigins


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


class InventoryWitness:
    def __init__(self, initial: EnergyOrigins) -> None:
        self.energy = _energy(initial)

    def advance(self, flow: Flows, model: BatteryModel) -> InventoryBoundary:
        before = self.energy
        after_losses = before - _energy(flow.standing_loss) - _energy(flow.internal_aux)
        # Match the explicitly recorded internal charge-energy terms. The
        # exact witness then adds/subtracts those floats without large-stock
        # cancellation or an interval-count-dependent numerical budget.
        incoming = Fraction(
            flow.pv_charge_kw * model.eta_charge * flow.frame.interval.hours
        ) + Fraction(flow.grid_charge_kw * model.eta_charge * flow.frame.interval.hours)
        self.energy = after_losses + incoming - _energy(flow.discharged_internal)
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
        )

    def terminal_violation(self, minimum_kwh: float) -> float:
        return float(Fraction(minimum_kwh) - self.energy)
