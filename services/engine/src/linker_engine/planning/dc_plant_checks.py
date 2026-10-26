"""Independent port, common-bus, origin and hard inventory witnesses.

No controller/actuator is called. Transfer residuals are power over the real
interval; an inventory-size tolerance cannot finance a short, excessive flow.
Task shortages remain distinct from failure of a physical conservation law.
"""

from __future__ import annotations

import math

from .dc_plant_model import DcPlantFlow, DcPlantUnit
from .dispatch_checks import Check
from .energy_origins import EnergyOrigins
from .errors import InvalidInput, NumericalFailure
from .inventory_witness import InventoryWitness
from .numerical_tolerance import Tolerance
from .plant_energy_checks import PlantVerification

ORIGINS = ("pv_kwh", "grid_kwh", "initial_unknown_kwh")


def verify(
    flows: tuple[DcPlantFlow, ...],
    units: tuple[DcPlantUnit, ...],
    tolerance: Tolerance,
    *,
    initial: dict[str, EnergyOrigins],
    terminal_min_kwh: dict[str, float | None],
) -> PlantVerification:
    models = {u.id: u for u in units}
    if (
        not flows
        or len(models) != len(units)
        or set(models) != set(initial)
        or set(models) != set(terminal_min_kwh)
    ):
        raise InvalidInput(
            "DC verification requires every named initial and terminal state"
        )
    witnesses = {uid: InventoryWitness(state) for uid, state in initial.items()}
    preceding = initial
    checks: dict[str, Check] = {}
    tasks: set[str] = set()

    def record(
        code: str,
        residual: float,
        scale: float,
        index: int,
        *,
        bound: bool = False,
        hard: float | None = None,
        energy: bool = False,
        task: bool = False,
    ) -> None:
        if task:
            tasks.add(code)
        violation = max(residual, 0.0) if bound else abs(residual)
        allowance = (
            hard
            if hard is not None
            else (tolerance.absolute_kwh if energy else tolerance.absolute_kw)
            + tolerance.relative * abs(scale)
        )
        if (
            not all(math.isfinite(v) for v in (violation, scale, allowance))
            or allowance < 0
        ):
            raise NumericalFailure("nonfinite DC plant verification arithmetic")
        check = Check(
            code,
            violation <= allowance,
            violation,
            "kWh" if energy else "kW",
            index,
            allowance,
            0.0,
        )
        old = checks.get(code)
        if (
            old is None
            or (not check.passed and old.passed)
            or (
                check.passed == old.passed
                and check.worst_violation - check.allowance
                > old.worst_violation - old.allowance
            )
        ):
            checks[code] = check

    for index, flow in enumerate(flows):
        frame, site = flow.frame, flow.frame.site
        dt = site.interval.hours
        if (
            len(flow.units) != len(models)
            or {u.unit.id for u in flow.units} != set(models)
            or set(frame.pv_dc_kw) != set(models)
        ):
            raise InvalidInput("the DC trace omitted or repeated a physical unit")
        if index and flows[index - 1].frame.site.interval.end != site.interval.start:
            raise InvalidInput("the DC trace has a discontinuous time axis")
        scale = max(
            site.load_kw,
            site.aux_ac_kw,
            site.pv_potential_kw,
            flow.grid_import_kwh / dt,
            *(u.port.plan.forward_ac_kw for u in flow.units),
        )
        pv_ac = flow.independent_pv_available_kwh - flow.independent_pv_curtailed_kwh
        battery = EnergyOrigins(0, 0, 0)
        reverse = 0.0
        for unit in flow.units:
            uid, port, model = unit.unit.id, unit.port, models[unit.unit.id].model
            p, f = port.plan, port.plan.frame
            prefix = "unit:" + uid + ":"
            bridge = model.bridge(site.limits.mode)
            unit_scale = max(
                scale,
                f.pv_available_dc_kw,
                f.aux_dc_kw,
                model.charge_terminal_kw,
                model.discharge_terminal_kw,
            )
            if (
                unit.unit != models[uid]
                or p.model != model
                or f.interval != site.interval
                or f.mode != site.limits.mode
                or f.pv_enabled != site.limits.pv_enabled
                or f.pv_available_dc_kw != frame.pv_dc_kw[uid]
                or f.aux_dc_kw != frame.aux_dc_kw[uid]
                or f.reserve_kwh != frame.reserves_kwh[uid]
            ):
                raise InvalidInput(
                    "a DC trace port differs from its own frozen model or inputs"
                )

            def check(
                name: str,
                residual: float,
                *,
                bound: bool = False,
                hard: float | None = None,
                energy: bool = False,
                task: bool = False,
                _prefix: str = prefix,
                _capacity: float = model.usable_window_kwh,
                _scale: float = unit_scale,
                _index: int = index,
            ) -> None:
                record(
                    _prefix + name,
                    residual,
                    _capacity if energy else _scale,
                    _index,
                    bound=bound,
                    hard=hard,
                    energy=energy,
                    task=task,
                )

            potential = f.pv_available_dc_kw if f.pv_enabled else 0.0
            pv = (
                potential
                if model.pv_input_dc_kw is None
                else min(potential, model.pv_input_dc_kw)
            )
            check("pv_input", p.pv_available_dc_kw - pv)
            check("pv_input_cap", p.pv_input_curtailed_dc_kw - (potential - pv))
            check("pv_aux_priority", p.pv_to_aux_dc_kw - min(pv, f.aux_dc_kw))
            check(
                "pv_allocation",
                pv
                - p.pv_to_aux_dc_kw
                - p.pv_charge_bus_dc_kw
                - p.pv_to_inverter_dc_kw
                - p.pv_curtailed_dc_kw,
            )
            incoming_ac = port.incoming_aux_ac.total + port.incoming_charge_ac.total
            incoming_dc = port.incoming_aux_dc.total + port.incoming_charge_dc.total
            charge_bus = p.pv_charge_bus_dc_kw + port.incoming_charge_dc.total / dt
            battery_bus = p.battery_to_aux_dc_kw + p.battery_to_inverter_dc_kw
            check(
                "dc_bus",
                pv
                + battery_bus
                + incoming_dc / dt
                - charge_bus
                - (f.aux_dc_kw - port.unserved_aux_dc_kw)
                - p.forward_dc_kw
                - p.pv_curtailed_dc_kw,
            )
            check(
                "dc_aux",
                p.pv_to_aux_dc_kw
                + p.battery_to_aux_dc_kw
                + port.incoming_aux_dc.total / dt
                + port.unserved_aux_dc_kw
                - f.aux_dc_kw,
            )
            check("dc_aux_unserved", port.unserved_aux_dc_kw, task=True)
            check(
                "charge_conversion",
                port.charge_terminal_dc_kw - charge_bus * model.eta_bus_to_battery,
            )
            check(
                "discharge_conversion",
                battery_bus - p.discharge_terminal_dc_kw * model.eta_battery_to_bus,
            )
            check(
                "forward_sources",
                p.forward_dc_kw - p.pv_to_inverter_dc_kw - p.battery_to_inverter_dc_kw,
            )
            check(
                "forward_conversion",
                p.forward_ac_kw - p.forward_dc_kw * bridge.eta_forward,
            )
            check(
                "pv_forward_conversion",
                p.pv_forward_ac_kw - p.pv_to_inverter_dc_kw * bridge.eta_forward,
            )
            check(
                "shared_forward_cap",
                p.forward_dc_kw - bridge.forward_limit_dc_kw,
                bound=True,
            )
            check("one_bridge_direction", min(p.forward_ac_kw, incoming_ac / dt))
            eta_reverse = bridge.eta_reverse if bridge.reverse_supported else 1.0
            if bridge.reverse_supported:
                assert eta_reverse is not None and bridge.reverse_ac_kw is not None
                check(
                    "reverse_conversion", (incoming_dc - incoming_ac * eta_reverse) / dt
                )
                check(
                    "reverse_ac_cap",
                    incoming_ac / dt - bridge.reverse_ac_kw,
                    bound=True,
                )
                if bridge.reverse_dc_kw is not None:
                    check(
                        "reverse_dc_cap",
                        incoming_dc / dt - bridge.reverse_dc_kw,
                        bound=True,
                    )
            else:
                check(
                    "reverse_unavailable", max(incoming_ac, incoming_dc) / dt, hard=0.0
                )
            if not unit.unit.allow_ac_charge:
                check(
                    "ac_charging_disabled", port.incoming_charge_ac.total / dt, hard=0.0
                )
            check(
                "battery_exclusive",
                min(port.charge_terminal_dc_kw, p.discharge_terminal_dc_kw),
            )
            check(
                "charge_terminal_cap",
                port.charge_terminal_dc_kw
                - min(model.charge_terminal_kw, p.command.charge_kw),
                bound=True,
            )
            check(
                "discharge_terminal_cap",
                p.discharge_terminal_dc_kw
                - min(model.discharge_terminal_kw, p.command.discharge_kw),
                bound=True,
            )
            check(
                "actual_withdrawal",
                (
                    p.discharged_internal.total * model.eta_store_discharge
                    - p.discharge_terminal_dc_kw * dt
                )
                / dt,
            )
            for name in (
                "pv_available_dc_kw",
                "pv_input_curtailed_dc_kw",
                "pv_to_aux_dc_kw",
                "pv_charge_bus_dc_kw",
                "pv_to_inverter_dc_kw",
                "pv_curtailed_dc_kw",
                "battery_to_aux_dc_kw",
                "battery_to_inverter_dc_kw",
                "discharge_terminal_dc_kw",
                "forward_dc_kw",
                "forward_ac_kw",
            ):
                check("nonnegative:" + name, -getattr(p, name), bound=True)
            fraction = -math.expm1(-model.standing_loss_rate_per_hour * dt)
            aux = min(
                max(p.before.total * (1 - fraction), 0.0), model.internal_aux_kw * dt
            )
            check("internal_aux", (p.internal_aux.total - aux) / dt)
            check(
                "internal_aux_shortage",
                (
                    p.internal_aux_unserved_kwh
                    - max(model.internal_aux_kw * dt - aux, 0.0)
                )
                / dt,
            )
            check("internal_aux_unserved", p.internal_aux_unserved_kwh / dt, task=True)
            boundary = witnesses[uid].advance_dc_port(port)
            check(
                "window",
                boundary.capacity_violation_kwh,
                bound=True,
                hard=math.ulp(model.usable_window_kwh),
                energy=True,
            )
            check(
                "reserve",
                boundary.reserve_violation_kwh,
                bound=True,
                hard=math.ulp(f.reserve_kwh) if f.reserve_kwh else 0.0,
                energy=True,
                task=True,
            )
            check(
                "inventory_charge_power",
                port.charge_terminal_dc_kw - boundary.charge_kw,
                bound=True,
                hard=math.fsum(
                    math.ulp(v) if v else 0.0
                    for v in (port.charge_terminal_dc_kw, boundary.charge_kw)
                ),
            )
            check(
                "inventory_discharge_power",
                p.discharge_terminal_dc_kw - boundary.discharge_kw,
                bound=True,
                hard=math.fsum(
                    math.ulp(v) if v else 0.0
                    for v in (p.discharge_terminal_dc_kw, boundary.discharge_kw)
                ),
            )
            post_losses = p.before.total - p.standing_loss.total - p.internal_aux.total
            battery_forward_fraction = (
                p.battery_to_inverter_dc_kw / battery_bus if battery_bus else 0.0
            )
            for origin in ORIGINS:
                old = getattr(p.before, origin)
                standing = getattr(p.standing_loss, origin)
                internal = getattr(p.internal_aux, origin)
                withdrawn = getattr(p.discharged_internal, origin)
                check(
                    "continuity:" + origin,
                    old - getattr(preceding[uid], origin),
                    hard=0.0,
                    energy=True,
                )
                check("standing:" + origin, (standing - old * fraction) / dt)
                check(
                    "internal_aux:" + origin,
                    (
                        internal
                        - (old - standing)
                        / (p.before.total - p.standing_loss.total)
                        * aux
                    )
                    / dt
                    if p.before.total > p.standing_loss.total
                    else internal / dt,
                )
                check(
                    "withdrawal_mixing:" + origin,
                    (
                        withdrawn
                        - (old - standing - internal)
                        / post_losses
                        * p.discharged_internal.total
                    )
                    / dt
                    if post_losses
                    else withdrawn / dt,
                )
                local = p.pv_charge_bus_dc_kw * dt if origin == "pv_kwh" else 0.0
                charged = (
                    (local + getattr(port.incoming_charge_dc, origin))
                    * model.eta_bus_to_battery
                    * model.eta_store_charge
                )
                check(
                    "inventory_sources:" + origin,
                    (
                        old
                        - standing
                        - internal
                        - withdrawn
                        + charged
                        - getattr(port.after, origin)
                    )
                    / dt,
                )
                expected_forward = (
                    withdrawn
                    * model.eta_store_discharge
                    * model.eta_battery_to_bus
                    * bridge.eta_forward
                    * battery_forward_fraction
                )
                check(
                    "battery_forward:" + origin,
                    (getattr(p.battery_forward_ac, origin) - expected_forward) / dt,
                )
                check(
                    "reverse_aux_sources:" + origin,
                    (
                        getattr(port.incoming_aux_dc, origin)
                        - getattr(port.incoming_aux_ac, origin) * eta_reverse
                    )
                    / dt,
                )
                check(
                    "reverse_charge_sources:" + origin,
                    (
                        getattr(port.incoming_charge_dc, origin)
                        - getattr(port.incoming_charge_ac, origin) * eta_reverse
                    )
                    / dt,
                )
            pv_ac += p.pv_forward_ac_kw * dt
            battery = battery.plus(p.battery_forward_ac)
            reverse += incoming_ac
        record(
            "independent_pv_input",
            flow.independent_pv_available_kwh / dt
            - (site.pv_potential_kw if site.limits.pv_enabled else 0.0),
            scale,
            index,
        )
        record(
            "independent_pv_curtailment",
            -flow.independent_pv_curtailed_kwh / dt,
            scale,
            index,
            bound=True,
        )
        record(
            "independent_pv_curtailment_cap",
            (flow.independent_pv_curtailed_kwh - flow.independent_pv_available_kwh)
            / dt,
            scale,
            index,
            bound=True,
        )
        pool = EnergyOrigins(pv_ac, 0, 0).plus(battery)
        onsite_supply = pool.total
        load_share = (
            min(site.load_kw * dt / onsite_supply, 1.0) if onsite_supply else 0.0
        )
        aux_share = (
            min(site.aux_ac_kw * dt, max(onsite_supply - site.load_kw * dt, 0.0))
            / onsite_supply
            if onsite_supply
            else 0.0
        )
        for origin in ORIGINS:
            record(
                "battery_to_load:" + origin,
                (
                    getattr(flow.battery_to_load_ac, origin)
                    - getattr(battery, origin) * load_share
                )
                / dt,
                scale,
                index,
            )
            record(
                "battery_to_aux:" + origin,
                (
                    getattr(flow.battery_to_aux_ac, origin)
                    - getattr(battery, origin) * aux_share
                )
                / dt,
                scale,
                index,
            )
        record(
            "direct_pv_to_load",
            (flow.direct_pv_to_load_kwh - pv_ac * load_share) / dt,
            scale,
            index,
        )
        record(
            "direct_pv_to_aux",
            (flow.direct_pv_to_aux_kwh - pv_ac * aux_share) / dt,
            scale,
            index,
        )
        for name, demand, supplied, grid in (
            ("load", site.load_kw * dt, flow.load_sources, flow.grid_to_load_kwh),
            ("site_aux", site.aux_ac_kw * dt, flow.aux_sources, flow.grid_to_aux_kwh),
        ):
            pool, expected = pool.withdraw(demand)
            expected = expected.plus(EnergyOrigins(0, grid, 0))
            for origin in ORIGINS:
                record(
                    name + "_source_mixing:" + origin,
                    (getattr(supplied, origin) - getattr(expected, origin)) / dt,
                    scale,
                    index,
                )
        for role, grid in (
            ("aux", flow.grid_to_dc_aux_kwh),
            ("charge", flow.grid_charge_kwh),
        ):
            pool = pool.plus(EnergyOrigins(0, grid, 0))
            for unit in flow.units:
                received = (
                    unit.port.incoming_aux_ac
                    if role == "aux"
                    else unit.port.incoming_charge_ac
                )
                pool, expected = pool.withdraw(received.total)
                for origin in ORIGINS:
                    record(
                        "unit:" + unit.unit.id + ":bus_" + role + ":" + origin,
                        (getattr(received, origin) - getattr(expected, origin)) / dt,
                        scale,
                        index,
                    )
        for origin in ORIGINS:
            record(
                "pcc_sources:" + origin,
                (
                    getattr(pool, origin)
                    - getattr(flow.export_sources, origin)
                    - getattr(flow.unallocated_sources, origin)
                )
                / dt,
                scale,
                index,
            )
        record(
            "pcc_import_sinks",
            (
                flow.grid_import_kwh
                - flow.grid_to_load_kwh
                - flow.grid_to_aux_kwh
                - flow.grid_to_dc_aux_kwh
                - flow.grid_charge_kwh
            )
            / dt,
            scale,
            index,
        )
        record(
            "pcc_ac_balance",
            (
                pv_ac
                + battery.total
                + flow.grid_import_kwh
                - flow.load_sources.total
                - flow.aux_sources.total
                - reverse
                - flow.export_sources.total
                - flow.unallocated_sources.total
            )
            / dt,
            scale,
            index,
        )
        record(
            "pcc_import_cap",
            flow.grid_import_kwh / dt
            - site.limits.import_limit(flow.grid_import_kwh / dt),
            scale,
            index,
            bound=True,
        )
        record(
            "pcc_export_cap",
            flow.export_sources.total / dt
            - site.limits.export_limit(flow.export_sources.total / dt),
            scale,
            index,
            bound=True,
        )
        record(
            "pcc_direction",
            min(flow.grid_import_kwh, flow.export_sources.total) / dt,
            scale,
            index,
        )
        record("unallocated_ac", flow.unallocated_sources.total / dt, scale, index)
        record(
            "grid_charging_disabled",
            flow.grid_charge_kwh / dt if not site.limits.allow_grid_charge else 0.0,
            scale,
            index,
        )
        record(
            "load_balance",
            (flow.load_sources.total + flow.unserved_load_kwh) / dt - site.load_kw,
            scale,
            index,
        )
        record(
            "site_aux_balance",
            (flow.aux_sources.total + flow.unserved_aux_kwh) / dt - site.aux_ac_kw,
            scale,
            index,
        )
        record("unserved_load", flow.unserved_load_kwh / dt, scale, index, task=True)
        record("unserved_site_aux", flow.unserved_aux_kwh / dt, scale, index, task=True)
        preceding = {u.unit.id: u.port.after for u in flow.units}
    for uid, minimum in terminal_min_kwh.items():
        if minimum is not None:
            record(
                "unit:" + uid + ":terminal_minimum",
                witnesses[uid].terminal_violation(minimum),
                models[uid].model.usable_window_kwh,
                len(flows) - 1,
                bound=True,
                energy=True,
                hard=math.ulp(minimum) if minimum else 0.0,
                task=True,
            )
    return PlantVerification(tuple(checks.values()), tolerance, frozenset(tasks))
