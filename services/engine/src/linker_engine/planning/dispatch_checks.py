"""Independent equations verify a replay's ledger and hard task boundaries.

This module never calls the actuator, policy or origin-withdraw implementation.
Tolerances are numerical software settings; they are not engineering margins.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .battery_model import BatteryModel, nonnegative
from .canonical import Json, Object
from .dispatch_delivery_checks import delivery_checks
from .dispatch_frame import Flows
from .dispatch_priorities import priority_residuals
from .errors import InvalidInput, NumericalFailure
from .numerical_tolerance import Tolerance


@dataclass(frozen=True)
class Check:
    code: str
    passed: bool
    worst_violation: float
    unit: str
    at_interval: int
    allowance: float
    arithmetic_allowance: float

    def document(self) -> Object:
        return {
            "code": self.code,
            "passed": self.passed,
            "worst_violation": self.worst_violation,
            "unit": self.unit,
            "at_interval": self.at_interval,
            "allowance": self.allowance,
            "arithmetic_allowance": self.arithmetic_allowance,
        }


@dataclass(frozen=True)
class Verification:
    checks: tuple[Check, ...]
    tolerance: Tolerance

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def document(self) -> Object:
        checks: list[Json] = [check.document() for check in self.checks]
        return {
            "passed": self.passed,
            "checks": checks,
            "tolerance": self.tolerance.document(),
        }


def verify(
    flows: tuple[Flows, ...],
    model: BatteryModel,
    tolerance: Tolerance,
    *,
    terminal_min_kwh: float | None,
) -> Verification:
    if not flows:
        raise InvalidInput("verification needs a nonempty replay")
    if terminal_min_kwh is not None:
        nonnegative(terminal_min_kwh, "terminal inventory requirement")
    checks: dict[str, Check] = {}

    def record(
        code: str,
        violation: float,
        unit: str,
        index: int,
        scale: float,
        arithmetic_allowance: float = 0.0,
    ) -> None:
        if not math.isfinite(violation) or not math.isfinite(scale):
            raise NumericalFailure("replay verification received nonfinite arithmetic")
        absolute = tolerance.absolute_kwh if unit == "kWh" else tolerance.absolute_kw
        if not math.isfinite(arithmetic_allowance) or arithmetic_allowance < 0:
            raise NumericalFailure("invalid arithmetic allowance")
        allowance = absolute + tolerance.relative * abs(scale) + arithmetic_allowance
        if not math.isfinite(allowance):
            raise NumericalFailure(
                "verification tolerance exceeds finite numerical domain"
            )
        value = max(violation, 0.0)
        current = Check(
            code,
            math.isfinite(value) and value <= allowance,
            value,
            unit,
            index,
            allowance,
            arithmetic_allowance,
        )
        previous = checks.get(code)
        # Preserve ANY failure; among equal statuses keep the largest margin
        # above its own allowance rather than a large, well-scaled raw residual.
        if (
            previous is None
            or (not current.passed and previous.passed)
            or (
                current.passed == previous.passed
                and current.worst_violation - current.allowance
                > previous.worst_violation - previous.allowance
            )
        ):
            checks[code] = current

    for index, flow in enumerate(flows):
        frame, dt = flow.frame, flow.frame.interval.hours
        power_scale = math.fsum(
            (
                flow.pv_available_kw,
                flow.import_kw,
                flow.discharge_kw,
                frame.load_kw,
                frame.aux_ac_kw,
            )
        )
        energy_scale = max(model.usable_window_kwh, flow.before.total, flow.after.total)
        for code, residual in priority_residuals(flow).items():
            record(code, residual, "kW", index, power_scale)
        for check in delivery_checks(flow, model):
            record(
                check.code,
                check.violation_kw,
                "kW",
                index,
                power_scale,
                check.arithmetic_allowance_kw,
            )
        ac_left = math.fsum((flow.pv_available_kw, flow.import_kw, flow.discharge_kw))
        ac_right = math.fsum(
            (
                flow.served_load_kw,
                flow.served_aux_kw,
                flow.charge_kw,
                flow.export_kw,
                flow.curtailed_kw,
            )
        )
        record(
            "ac_energy_balance",
            abs(ac_left - ac_right) * dt,
            "kWh",
            index,
            power_scale * dt,
        )
        expected_e = math.fsum(
            (
                flow.before.total,
                -flow.standing_loss.total,
                -flow.internal_aux.total,
                model.eta_charge * flow.charge_kw * dt,
                -flow.discharge_kw * dt / model.eta_discharge,
            )
        )
        record(
            "stored_energy_balance",
            abs(expected_e - flow.after.total),
            "kWh",
            index,
            energy_scale,
        )
        for origin in ("pv_kwh", "grid_kwh", "initial_unknown_kwh"):
            incoming = (
                flow.pv_charge_kw * model.eta_charge * dt
                if origin == "pv_kwh"
                else flow.grid_charge_kw * model.eta_charge * dt
                if origin == "grid_kwh"
                else 0.0
            )
            expected = math.fsum(
                (
                    getattr(flow.before, origin),
                    incoming,
                    -getattr(flow.standing_loss, origin),
                    -getattr(flow.internal_aux, origin),
                    -getattr(flow.discharged_internal, origin),
                )
            )
            record(
                f"origin_balance_{origin}",
                abs(expected - getattr(flow.after, origin)),
                "kWh",
                index,
                energy_scale,
            )
            before_origin = getattr(flow.before, origin)
            expected_standing_origin = (
                before_origin * flow.standing_loss.total / flow.before.total
                if flow.before.total
                else 0.0
            )
            record(
                f"standing_origin_{origin}",
                abs(expected_standing_origin - getattr(flow.standing_loss, origin)),
                "kWh",
                index,
                energy_scale,
            )
            after_standing = flow.before.total - flow.standing_loss.total
            expected_aux_origin = (
                (before_origin - getattr(flow.standing_loss, origin))
                * flow.internal_aux.total
                / after_standing
                if after_standing
                else 0.0
            )
            record(
                f"aux_origin_{origin}",
                abs(expected_aux_origin - getattr(flow.internal_aux, origin)),
                "kWh",
                index,
                energy_scale,
            )
            after_losses = after_standing - flow.internal_aux.total
            expected_discharge_origin = (
                (
                    before_origin
                    - getattr(flow.standing_loss, origin)
                    - getattr(flow.internal_aux, origin)
                )
                * flow.discharged_internal.total
                / after_losses
                if after_losses
                else 0.0
            )
            record(
                f"discharge_origin_{origin}",
                abs(
                    expected_discharge_origin
                    - getattr(flow.discharged_internal, origin)
                ),
                "kWh",
                index,
                energy_scale,
            )
        nonnegative_flows = (
            flow.pv_available_kw,
            flow.pv_to_load_kw,
            flow.pv_to_aux_kw,
            flow.pv_charge_kw,
            flow.grid_charge_kw,
            flow.discharge_kw,
            flow.charge_kw,
            flow.grid_to_load_kw,
            flow.grid_to_aux_kw,
            flow.import_kw,
            flow.export_kw,
            flow.curtailed_kw,
            flow.unserved_load_kw,
            flow.unserved_aux_kw,
            flow.charge_command_unmet_kw,
            flow.discharge_command_unmet_kw,
        )
        record(
            "nonnegative_ac_flows", -min(nonnegative_flows), "kW", index, power_scale
        )
        record(
            "unserved_load_bounds",
            flow.unserved_load_kw - frame.load_kw,
            "kW",
            index,
            frame.load_kw,
        )
        record(
            "unserved_aux_bounds",
            flow.unserved_aux_kw - frame.aux_ac_kw,
            "kW",
            index,
            frame.aux_ac_kw,
        )
        record(
            "pv_allocation",
            abs(
                flow.pv_available_kw
                - math.fsum(
                    (
                        flow.pv_to_load_kw,
                        flow.pv_to_aux_kw,
                        flow.pv_charge_kw,
                        flow.export_kw,
                        flow.curtailed_kw,
                    )
                )
            ),
            "kW",
            index,
            power_scale,
        )
        record(
            "grid_allocation",
            abs(
                flow.import_kw
                - math.fsum(
                    (flow.grid_to_load_kw, flow.grid_to_aux_kw, flow.grid_charge_kw)
                )
            ),
            "kW",
            index,
            power_scale,
        )
        record(
            "charge_allocation",
            abs(flow.charge_kw - flow.pv_charge_kw - flow.grid_charge_kw),
            "kW",
            index,
            power_scale,
        )
        battery_to_load = flow.discharged_to_load_ac.total / dt
        record(
            "load_allocation",
            abs(
                flow.served_load_kw
                - flow.pv_to_load_kw
                - flow.grid_to_load_kw
                - battery_to_load
            ),
            "kW",
            index,
            power_scale,
        )
        record(
            "aux_allocation",
            abs(
                flow.served_aux_kw
                - flow.pv_to_aux_kw
                - flow.grid_to_aux_kw
                - flow.discharge_kw
                + battery_to_load
            ),
            "kW",
            index,
            power_scale,
        )
        record(
            "discharge_conversion",
            abs(
                flow.discharged_internal.total * model.eta_discharge
                - flow.discharge_kw * dt
            ),
            "kWh",
            index,
            energy_scale,
        )
        for origin in ("pv_kwh", "grid_kwh", "initial_unknown_kwh"):
            expected_load = (
                getattr(flow.discharged_internal, origin)
                * model.eta_discharge
                * battery_to_load
                / flow.discharge_kw
                if flow.discharge_kw
                else 0.0
            )
            record(
                f"load_origin_{origin}",
                abs(expected_load - getattr(flow.discharged_to_load_ac, origin)),
                "kWh",
                index,
                energy_scale,
            )
        expected_standing = flow.before.total * (
            1.0 - math.exp(-model.standing_loss_rate_per_hour * dt)
        )
        record(
            "standing_loss_model",
            abs(expected_standing - flow.standing_loss.total),
            "kWh",
            index,
            energy_scale,
        )
        aux_demand = model.internal_aux_kw * dt
        expected_aux = min(
            aux_demand, max(flow.before.total - flow.standing_loss.total, 0.0)
        )
        record(
            "internal_aux_model",
            abs(expected_aux - flow.internal_aux.total),
            "kWh",
            index,
            energy_scale,
        )
        record(
            "internal_aux_shortage_nonnegative",
            -flow.internal_aux_unserved_kwh,
            "kWh",
            index,
            aux_demand,
        )
        record(
            "internal_aux_account",
            abs(aux_demand - flow.internal_aux.total - flow.internal_aux_unserved_kwh),
            "kWh",
            index,
            energy_scale,
        )
        record(
            "internal_aux_supplied",
            flow.internal_aux_unserved_kwh,
            "kWh",
            index,
            aux_demand,
        )
        record("load_supplied", flow.unserved_load_kw, "kW", index, frame.load_kw)
        record("aux_ac_supplied", flow.unserved_aux_kw, "kW", index, frame.aux_ac_kw)
        record(
            "usable_capacity",
            max(flow.before.total, flow.after.total) - model.usable_window_kwh,
            "kWh",
            index,
            energy_scale,
        )
        minimum_e = min(
            flow.before.total,
            flow.after.total,
            flow.before.total - flow.standing_loss.total - flow.internal_aux.total,
        )
        record(
            "reserve_maintained",
            frame.limits.reserve_kwh - minimum_e,
            "kWh",
            index,
            energy_scale,
        )
        record(
            "charge_power",
            flow.charge_kw - model.charge_ac_kw,
            "kW",
            index,
            model.charge_ac_kw,
        )
        record(
            "discharge_power",
            flow.discharge_kw - model.discharge_ac_kw,
            "kW",
            index,
            model.discharge_ac_kw,
        )
        record(
            "charge_discharge_exclusive",
            min(flow.charge_kw, flow.discharge_kw),
            "kW",
            index,
            power_scale,
        )
        record(
            "charge_command_account",
            abs(flow.command.charge_kw - flow.charge_kw - flow.charge_command_unmet_kw),
            "kW",
            index,
            flow.command.charge_kw,
        )
        record(
            "discharge_command_account",
            abs(
                flow.command.discharge_kw
                - flow.discharge_kw
                - flow.discharge_command_unmet_kw
            ),
            "kW",
            index,
            flow.command.discharge_kw,
        )
        record(
            "charge_not_above_command",
            flow.charge_kw - flow.command.charge_kw,
            "kW",
            index,
            flow.command.charge_kw,
        )
        record(
            "discharge_not_above_command",
            flow.discharge_kw - flow.command.discharge_kw,
            "kW",
            index,
            flow.command.discharge_kw,
        )
        record(
            "charge_command_met",
            flow.charge_command_unmet_kw,
            "kW",
            index,
            flow.command.charge_kw,
        )
        record(
            "discharge_command_met",
            flow.discharge_command_unmet_kw,
            "kW",
            index,
            flow.command.discharge_kw,
        )
        import_cap = (
            0.0 if frame.limits.mode == "outage" else frame.limits.import_cap_kw
        )
        export_cap = (
            0.0 if frame.limits.mode == "outage" else frame.limits.export_cap_kw
        )
        if import_cap is not None:
            record("import_limit", flow.import_kw - import_cap, "kW", index, import_cap)
        if export_cap is not None:
            record("export_limit", flow.export_kw - export_cap, "kW", index, export_cap)
        if not frame.limits.allow_grid_charge:
            record(
                "grid_charge_permission", flow.grid_charge_kw, "kW", index, power_scale
            )
        expected_pv = frame.pv_potential_kw if frame.limits.pv_enabled else 0.0
        record(
            "mode_pv_availability",
            abs(flow.pv_available_kw - expected_pv),
            "kW",
            index,
            expected_pv,
        )
        if index:
            previous = flows[index - 1]
            if previous.frame.interval.end != frame.interval.start:
                raise InvalidInput("verification horizon must be continuous")
            for origin in ("pv_kwh", "grid_kwh", "initial_unknown_kwh"):
                record(
                    f"continuous_{origin}",
                    abs(getattr(flow.before, origin) - getattr(previous.after, origin)),
                    "kWh",
                    index,
                    energy_scale,
                )
    if terminal_min_kwh is not None:
        record(
            "terminal_inventory",
            terminal_min_kwh - flows[-1].after.total,
            "kWh",
            len(flows) - 1,
            terminal_min_kwh,
        )
    return Verification(tuple(checks.values()), tolerance)
