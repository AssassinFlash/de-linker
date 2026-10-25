"""Independent dual-bus/source/window equations, without calling the actuator."""

from __future__ import annotations

import math
from dataclasses import fields

from .dc_battery_model import DcBatteryModel
from .dc_frame import DcFlows
from .dispatch_checks import Check, Verification
from .energy_origins import EnergyOrigins
from .errors import InvalidInput, NumericalFailure
from .inventory_witness import InventoryWitness
from .numerical_tolerance import Tolerance


def verify(
    flows: tuple[DcFlows, ...],
    model: DcBatteryModel,
    tolerance: Tolerance,
    *,
    initial: EnergyOrigins,
    terminal_min_kwh: float | None,
) -> Verification:
    if not flows:
        raise InvalidInput("DC verification needs a nonempty replay")
    checks: dict[str, Check] = {}
    inventory = InventoryWitness(initial)

    def record(
        code: str,
        residual: float,
        unit: str,
        index: int,
        scale: float,
        *,
        bound: bool = False,
        hard_allowance: float | None = None,
        arithmetic: float = 0.0,
    ) -> None:
        if unit == "kWh" and hard_allowance is None:
            # A small energy discrepancy over a short interval can represent
            # substantial power. Soft transfer checks retain that meaning;
            # their scale must never be the whole inventory divided by dt.
            frame = flows[index].frame
            duration = frame.interval.hours
            residual /= duration
            arithmetic /= duration
            unit = "kW"
            scale = max(
                frame.load_kw,
                frame.aux_ac_kw,
                frame.aux_dc_kw,
                frame.pv_available_dc_kw,
                model.internal_aux_kw,
                model.charge_terminal_kw,
                model.discharge_terminal_kw,
            )
        if not math.isfinite(residual) or not math.isfinite(scale):
            raise NumericalFailure("nonfinite shared DC ledger arithmetic")
        violation = max(residual, 0.0) if bound else abs(residual)
        allowance = (
            hard_allowance
            if hard_allowance is not None
            else (
                (tolerance.absolute_kwh if unit == "kWh" else tolerance.absolute_kw)
                + tolerance.relative * abs(scale)
                + arithmetic
            )
        )
        if (
            not math.isfinite(allowance)
            or allowance < 0
            or not math.isfinite(arithmetic)
            or arithmetic < 0
        ):
            raise NumericalFailure("DC verification tolerance exceeds finite domain")
        check = Check(
            code,
            violation <= allowance,
            violation,
            unit,
            index,
            allowance,
            hard_allowance if hard_allowance is not None else arithmetic,
        )
        previous = checks.get(code)
        if (
            previous is None
            or (not check.passed and previous.passed)
            or (
                check.passed == previous.passed
                and check.worst_violation > previous.worst_violation
            )
        ):
            checks[code] = check

    preceding = initial
    for index, flow in enumerate(flows):
        frame = flow.frame
        bridge = model.bridge(frame.limits.mode)
        duration = frame.interval.hours
        power_scale = max(
            frame.load_kw,
            frame.pv_available_dc_kw,
            model.charge_terminal_kw,
            model.discharge_terminal_kw,
        )
        energy_scale = max(model.usable_window_kwh, flow.before.total, flow.after.total)
        for field in fields(flow):
            if field.name.endswith("_kw"):
                record(
                    "nonnegative_flows",
                    -getattr(flow, field.name),
                    "kW",
                    index,
                    power_scale,
                    bound=True,
                )
        record(
            "internal_aux_nonnegative",
            -flow.internal_aux_unserved_kwh,
            "kWh",
            index,
            energy_scale,
            bound=True,
        )
        record(
            "continuous_axis",
            0.0
            if index == 0 or flows[index - 1].frame.interval.end == frame.interval.start
            else 1.0,
            "kW",
            index,
            0.0,
            hard_allowance=0.0,
        )
        pv = (
            min(frame.pv_available_dc_kw, model.pv_input_dc_kw)
            if frame.limits.pv_enabled
            else 0.0
        )
        potential = frame.pv_available_dc_kw if frame.limits.pv_enabled else 0.0
        pv_aux_first = min(pv, frame.aux_dc_kw)
        pv_for_load = min(
            max(pv - pv_aux_first, 0.0),
            bridge.forward_limit_dc_kw,
            (frame.load_kw + frame.aux_ac_kw) / bridge.eta_forward,
        )
        record(
            "pv_dc_aux_priority",
            flow.pv_to_aux_dc_kw - pv_aux_first,
            "kW",
            index,
            power_scale,
        )
        record(
            "pv_ac_load_before_storage",
            pv_for_load - flow.pv_to_inverter_dc_kw,
            "kW",
            index,
            power_scale,
            bound=True,
        )
        record(
            "pv_surplus_only_charge",
            flow.pv_charge_bus_dc_kw - max(pv - pv_aux_first - pv_for_load, 0.0),
            "kW",
            index,
            power_scale,
            bound=True,
        )
        record("load_supplied", flow.unserved_load_ac_kw, "kW", index, frame.load_kw)
        record("aux_ac_supplied", flow.unserved_aux_ac_kw, "kW", index, frame.aux_ac_kw)
        record("aux_dc_supplied", flow.unserved_aux_dc_kw, "kW", index, frame.aux_dc_kw)
        record(
            "internal_aux_supplied",
            flow.internal_aux_unserved_kwh / duration,
            "kW",
            index,
            model.internal_aux_kw,
        )
        record(
            "load_before_ac_aux",
            min(flow.unserved_load_ac_kw, frame.aux_ac_kw - flow.unserved_aux_ac_kw),
            "kW",
            index,
            power_scale,
        )
        record(
            "load_before_pv_export",
            min(flow.unserved_load_ac_kw + flow.unserved_aux_ac_kw, flow.export_ac_kw),
            "kW",
            index,
            power_scale,
        )
        record("pv_input_stage", flow.pv_available_dc_kw - pv, "kW", index, power_scale)
        record(
            "pv_input_limit",
            flow.pv_input_curtailed_dc_kw - (potential - pv),
            "kW",
            index,
            power_scale,
        )
        record(
            "pv_bus_allocation",
            pv
            - flow.pv_to_aux_dc_kw
            - flow.pv_charge_bus_dc_kw
            - flow.pv_to_inverter_dc_kw
            - flow.pv_curtailed_dc_kw,
            "kW",
            index,
            power_scale,
        )
        battery_bus = flow.battery_to_aux_dc_kw + flow.battery_to_inverter_dc_kw
        charge_bus = flow.pv_charge_bus_dc_kw + flow.grid_charge_bus_dc_kw
        served_dc_aux = frame.aux_dc_kw - flow.unserved_aux_dc_kw
        record(
            "dc_bus_balance",
            pv
            + battery_bus
            + flow.inverter_reverse_dc_kw
            - charge_bus
            - served_dc_aux
            - flow.inverter_forward_dc_kw
            - flow.pv_curtailed_dc_kw,
            "kW",
            index,
            power_scale,
        )
        record(
            "dc_aux_supply",
            flow.pv_to_aux_dc_kw
            + flow.battery_to_aux_dc_kw
            + flow.grid_to_aux_dc_kw
            - served_dc_aux,
            "kW",
            index,
            power_scale,
        )
        record(
            "charge_dc_dc",
            flow.charge_terminal_dc_kw - charge_bus * model.eta_bus_to_battery,
            "kW",
            index,
            power_scale,
        )
        record(
            "discharge_dc_dc",
            battery_bus - flow.discharge_terminal_dc_kw * model.eta_battery_to_bus,
            "kW",
            index,
            power_scale,
        )
        record(
            "forward_dc_sources",
            flow.inverter_forward_dc_kw
            - flow.pv_to_inverter_dc_kw
            - flow.battery_to_inverter_dc_kw,
            "kW",
            index,
            power_scale,
        )
        record(
            "reverse_dc_sinks",
            flow.inverter_reverse_dc_kw
            - flow.grid_to_aux_dc_kw
            - flow.grid_charge_bus_dc_kw,
            "kW",
            index,
            power_scale,
        )
        record(
            "shared_forward_conversion",
            flow.inverter_forward_ac_kw
            - flow.inverter_forward_dc_kw * bridge.eta_forward,
            "kW",
            index,
            power_scale,
        )
        record(
            "one_bridge_direction",
            min(flow.inverter_forward_dc_kw, flow.inverter_reverse_dc_kw),
            "kW",
            index,
            power_scale,
        )
        record(
            "shared_forward_ac_cap",
            flow.inverter_forward_ac_kw - bridge.forward_ac_kw,
            "kW",
            index,
            power_scale,
            bound=True,
        )
        record(
            "shared_forward_dc_cap",
            flow.inverter_forward_dc_kw - bridge.forward_dc_kw,
            "kW",
            index,
            power_scale,
            bound=True,
        )
        if bridge.reverse_supported:
            assert (
                bridge.eta_reverse is not None
                and bridge.reverse_ac_kw is not None
                and bridge.reverse_dc_kw is not None
            )
            record(
                "reverse_conversion",
                flow.inverter_reverse_dc_kw
                - flow.inverter_reverse_ac_kw * bridge.eta_reverse,
                "kW",
                index,
                power_scale,
            )
            record(
                "reverse_ac_cap",
                flow.inverter_reverse_ac_kw - bridge.reverse_ac_kw,
                "kW",
                index,
                power_scale,
                bound=True,
            )
            record(
                "reverse_dc_cap",
                flow.inverter_reverse_dc_kw - bridge.reverse_dc_kw,
                "kW",
                index,
                power_scale,
                bound=True,
            )
        else:
            record(
                "reverse_path_not_available",
                max(flow.inverter_reverse_dc_kw, flow.inverter_reverse_ac_kw),
                "kW",
                index,
                power_scale,
            )
        served_load = frame.load_kw - flow.unserved_load_ac_kw
        served_aux = frame.aux_ac_kw - flow.unserved_aux_ac_kw
        battery_load = flow.discharged_to_load_ac.total / duration
        record(
            "ac_bus_balance",
            flow.inverter_forward_ac_kw
            + flow.import_ac_kw
            - served_load
            - served_aux
            - flow.export_ac_kw
            - flow.inverter_reverse_ac_kw,
            "kW",
            index,
            power_scale,
        )
        record(
            "load_sources",
            flow.pv_to_load_ac_kw
            + battery_load
            + flow.grid_to_load_ac_kw
            - served_load,
            "kW",
            index,
            power_scale,
        )
        record(
            "ac_aux_sources",
            flow.pv_to_aux_ac_kw
            + flow.battery_to_aux_ac_kw
            + flow.grid_to_aux_ac_kw
            - served_aux,
            "kW",
            index,
            power_scale,
        )
        record(
            "import_sinks",
            flow.import_ac_kw
            - flow.grid_to_load_ac_kw
            - flow.grid_to_aux_ac_kw
            - flow.inverter_reverse_ac_kw,
            "kW",
            index,
            power_scale,
        )
        record(
            "pv_ac_allocation",
            flow.pv_to_load_ac_kw
            + flow.pv_to_aux_ac_kw
            + flow.export_ac_kw
            - flow.pv_to_inverter_dc_kw * bridge.eta_forward,
            "kW",
            index,
            power_scale,
        )
        record(
            "battery_ac_allocation",
            battery_load
            + flow.battery_to_aux_ac_kw
            - flow.battery_to_inverter_dc_kw * bridge.eta_forward,
            "kW",
            index,
            power_scale,
        )
        record(
            "charge_terminal_cap",
            flow.charge_terminal_dc_kw - model.charge_terminal_kw,
            "kW",
            index,
            power_scale,
            bound=True,
        )
        record(
            "discharge_terminal_cap",
            flow.discharge_terminal_dc_kw - model.discharge_terminal_kw,
            "kW",
            index,
            power_scale,
            bound=True,
        )
        record(
            "mutually_exclusive_battery",
            min(flow.charge_terminal_dc_kw, flow.discharge_terminal_dc_kw),
            "kW",
            index,
            power_scale,
        )
        record(
            "charge_command",
            flow.charge_terminal_dc_kw
            + flow.charge_command_unmet_dc_kw
            - flow.command.charge_kw,
            "kW",
            index,
            power_scale,
        )
        record(
            "discharge_command",
            flow.discharge_terminal_dc_kw
            + flow.discharge_command_unmet_dc_kw
            - flow.command.discharge_kw,
            "kW",
            index,
            power_scale,
        )
        record(
            "grid_charge_policy",
            flow.grid_charge_bus_dc_kw if not frame.limits.allow_grid_charge else 0.0,
            "kW",
            index,
            power_scale,
        )
        record(
            "import_cap",
            flow.import_ac_kw - frame.limits.import_limit(flow.import_ac_kw),
            "kW",
            index,
            power_scale,
            bound=True,
        )
        record(
            "export_cap",
            flow.export_ac_kw - frame.limits.export_limit(flow.export_ac_kw),
            "kW",
            index,
            power_scale,
            bound=True,
        )
        fraction = -math.expm1(-model.standing_loss_rate_per_hour * duration)
        after_standing = flow.before.total * (1 - fraction)
        expected_aux = min(after_standing, model.internal_aux_kw * duration)
        record(
            "internal_aux_supply",
            flow.internal_aux.total - expected_aux,
            "kWh",
            index,
            energy_scale,
        )
        record(
            "internal_aux_shortage",
            flow.internal_aux_unserved_kwh
            - (model.internal_aux_kw * duration - expected_aux),
            "kWh",
            index,
            energy_scale,
        )
        record(
            "actual_terminal_withdrawal",
            (
                flow.discharged_internal.total * model.eta_store_discharge
                - flow.discharge_terminal_dc_kw * duration
            )
            / duration,
            "kW",
            index,
            power_scale,
        )
        boundary = inventory.advance_dc(flow, model)
        record(
            "usable_window",
            boundary.capacity_violation_kwh,
            "kWh",
            index,
            energy_scale,
            bound=True,
            hard_allowance=math.ulp(model.usable_window_kwh)
            if model.usable_window_kwh
            else 0.0,
        )
        record(
            "reserve",
            boundary.reserve_violation_kwh,
            "kWh",
            index,
            energy_scale,
            bound=True,
            hard_allowance=math.ulp(frame.limits.reserve_kwh)
            if frame.limits.reserve_kwh
            else 0.0,
        )
        record(
            "inventory_charge_power",
            flow.charge_terminal_dc_kw - boundary.charge_kw,
            "kW",
            index,
            power_scale,
            bound=True,
            hard_allowance=math.fsum(
                math.ulp(value) if value else 0.0
                for value in (flow.charge_terminal_dc_kw, boundary.charge_kw)
            ),
        )
        record(
            "inventory_discharge_power",
            flow.discharge_terminal_dc_kw - boundary.discharge_kw,
            "kW",
            index,
            power_scale,
            bound=True,
            hard_allowance=math.fsum(
                math.ulp(value) if value else 0.0
                for value in (flow.discharge_terminal_dc_kw, boundary.discharge_kw)
            ),
        )
        for origin in ("pv_kwh", "grid_kwh", "initial_unknown_kwh"):
            before = getattr(flow.before, origin)
            record(
                "state_continuity",
                before - getattr(preceding, origin),
                "kWh",
                index,
                energy_scale,
                hard_allowance=0.0,
            )
            record(
                "standing_loss_sources",
                getattr(flow.standing_loss, origin) - before * fraction,
                "kWh",
                index,
                energy_scale,
            )
            after_loss = before * (1 - fraction)
            record(
                "internal_aux_sources",
                getattr(flow.internal_aux, origin)
                - (
                    after_loss / after_standing * expected_aux
                    if after_standing
                    else 0.0
                ),
                "kWh",
                index,
                energy_scale,
            )
            available = (
                before
                - getattr(flow.standing_loss, origin)
                - getattr(flow.internal_aux, origin)
            )
            total_available = after_standing - expected_aux
            removed = getattr(flow.discharged_internal, origin)
            record(
                "proportional_discharge_sources",
                removed
                - (
                    available / total_available * flow.discharged_internal.total
                    if total_available
                    else 0.0
                ),
                "kWh",
                index,
                energy_scale,
            )
            charged = (
                (
                    flow.pv_charge_bus_dc_kw
                    if origin == "pv_kwh"
                    else flow.grid_charge_bus_dc_kw
                    if origin == "grid_kwh"
                    else 0.0
                )
                * model.eta_bus_to_battery
                * model.eta_store_charge
                * duration
            )
            record(
                "stored_source_balance",
                math.fsum(
                    (
                        getattr(flow.after, origin),
                        -before,
                        getattr(flow.standing_loss, origin),
                        getattr(flow.internal_aux, origin),
                        removed,
                        -charged,
                    )
                )
                / duration,
                "kW",
                index,
                power_scale,
                arithmetic=math.fsum(
                    math.ulp(value) if value else 0.0
                    for value in (
                        before,
                        before,
                        getattr(flow.after, origin),
                        getattr(flow.standing_loss, origin),
                        getattr(flow.internal_aux, origin),
                        removed,
                        charged,
                    )
                )
                / duration,
            )
            record(
                "load_discharge_sources",
                (
                    getattr(flow.discharged_to_load_ac, origin)
                    - (
                        removed
                        / flow.discharged_internal.total
                        * battery_load
                        * duration
                        if flow.discharged_internal.total
                        else 0.0
                    )
                )
                / duration,
                "kW",
                index,
                power_scale,
            )
        preceding = flow.after
    if terminal_min_kwh is not None:
        if not math.isfinite(terminal_min_kwh) or terminal_min_kwh < 0:
            raise InvalidInput("finite nonnegative terminal inventory required")
        record(
            "terminal_requirement",
            inventory.terminal_violation(terminal_min_kwh),
            "kWh",
            len(flows) - 1,
            model.usable_window_kwh,
            bound=True,
            hard_allowance=math.ulp(terminal_min_kwh) if terminal_min_kwh else 0.0,
        )
    return Verification(tuple(checks.values()), tolerance)
