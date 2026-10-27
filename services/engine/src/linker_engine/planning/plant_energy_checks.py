"""Independent device/source/AC-bus equations for a joint storage replay.

No actuator or controller is called here. Energy residuals are also checked
as power over their actual interval, so a short interval cannot hide an
excessive power error behind a fixed whole-inventory energy tolerance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import cast

from .canonical import Json, Object
from .dispatch_checks import Check, Verification
from .energy_origins import EnergyOrigins
from .errors import InvalidInput, NumericalFailure
from .inventory_witness import InventoryWitness
from .numerical_tolerance import Tolerance
from .plant_energy_model import PlantFlow, StorageUnit


@dataclass(frozen=True)
class PlantVerification:
    checks: tuple[Check, ...]
    tolerance: Tolerance
    task_codes: frozenset[str]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def physical_passed(self) -> bool:
        return all(
            check.passed for check in self.checks if check.code not in self.task_codes
        )

    def document(self) -> Object:
        return {
            **Verification(self.checks, self.tolerance).document(),
            "physical_passed": self.physical_passed,
            "task_codes": cast(Json, sorted(self.task_codes)),
        }


def verify(
    flows: tuple[PlantFlow, ...],
    units: tuple[StorageUnit, ...],
    tolerance: Tolerance,
    *,
    initial: dict[str, EnergyOrigins],
    terminal_min_kwh: dict[str, float | None],
) -> PlantVerification:
    ids = {unit.id for unit in units}
    if (
        not flows
        or len(ids) != len(units)
        or ids != set(initial)
        or ids != set(terminal_min_kwh)
    ):
        raise InvalidInput(
            "joint verification requires each named initial and terminal state"
        )
    models = {unit.id: unit for unit in units}
    checks: dict[str, Check] = {}
    task_codes: set[str] = set()
    witnesses = {uid: InventoryWitness(state) for uid, state in initial.items()}

    def record(
        code: str,
        residual: float,
        index: int,
        scale: float,
        *,
        bound: bool = False,
        energy: bool = False,
        hard_allowance: float | None = None,
        task: bool = False,
    ) -> None:
        if task:
            task_codes.add(code)
        violation = max(residual, 0.0) if bound else abs(residual)
        absolute = tolerance.absolute_kwh if energy else tolerance.absolute_kw
        allowance = (
            hard_allowance
            if hard_allowance is not None
            else absolute + tolerance.relative * abs(scale)
        )
        if not all(math.isfinite(v) for v in (violation, scale, allowance)):
            raise NumericalFailure("joint replay has nonfinite verification arithmetic")
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

    preceding = initial
    for index, flow in enumerate(flows):
        site, dt = flow.frame.site, flow.frame.site.interval.hours
        if {f.unit.id for f in flow.units} != ids or len(flow.units) != len(ids):
            raise InvalidInput("joint trace omitted or repeated a physical unit")
        if index and flows[index - 1].frame.site.interval.end != site.interval.start:
            raise InvalidInput("joint verification requires continuous time")
        demand = site.load_kw * dt
        aux = site.aux_ac_kw * dt
        charge = math.fsum(f.received_ac.total for f in flow.units)
        discharge = math.fsum(f.delivered_ac.total for f in flow.units)
        scale = max(
            site.load_kw,
            site.aux_ac_kw,
            site.pv_potential_kw,
            charge / dt,
            discharge / dt,
            flow.grid_import_kwh / dt,
        )
        residual = (
            flow.pv_available_kwh
            + flow.grid_import_kwh
            + discharge
            - flow.load_sources.total
            - flow.aux_sources.total
            - charge
            - flow.export_sources.total
            - flow.curtailed_sources.total
        )
        record("pcc_ac_balance", residual / dt, index, scale)
        record(
            "load_balance",
            (flow.load_sources.total + flow.unserved_load_kwh - demand) / dt,
            index,
            site.load_kw,
        )
        record(
            "site_aux_balance",
            (flow.aux_sources.total + flow.unserved_aux_kwh - aux) / dt,
            index,
            site.aux_ac_kw,
        )
        record(
            "pv_input",
            flow.pv_available_kwh / dt
            - (site.pv_potential_kw if site.limits.pv_enabled else 0),
            index,
            site.pv_potential_kw,
        )
        record(
            "unserved_load",
            flow.unserved_load_kwh / dt,
            index,
            site.load_kw,
            bound=True,
            task=True,
        )
        record(
            "unserved_site_aux",
            flow.unserved_aux_kwh / dt,
            index,
            site.aux_ac_kw,
            bound=True,
            task=True,
        )
        import_cap = 0.0 if site.limits.mode == "outage" else site.limits.import_cap_kw
        export_cap = 0.0 if site.limits.mode == "outage" else site.limits.export_cap_kw
        if import_cap is not None:
            record(
                "pcc_import_limit",
                flow.grid_import_kwh / dt - import_cap,
                index,
                import_cap,
                bound=True,
            )
        if export_cap is not None:
            record(
                "pcc_export_limit",
                flow.export_sources.total / dt - export_cap,
                index,
                export_cap,
                bound=True,
            )
        record(
            "pcc_direction",
            min(flow.grid_import_kwh, flow.export_sources.total) / dt,
            index,
            scale,
        )
        for name in (
            "pv_available_kwh",
            "grid_import_kwh",
            "grid_charge_kwh",
            "unserved_load_kwh",
            "unserved_aux_kwh",
        ):
            record(
                "nonnegative:" + name,
                -getattr(flow, name) / dt,
                index,
                scale,
                bound=True,
            )
        if set(flow.frame.reserves_kwh) != ids:
            raise InvalidInput("joint trace reserves differ from the named units")
        if not site.limits.allow_grid_charge:
            record("grid_charging_disabled", flow.grid_charge_kwh / dt, index, scale)
        ac_supply = math.fsum((flow.pv_available_kwh, discharge))
        onsite_load = min(ac_supply, demand)
        onsite_aux = min(max(ac_supply - onsite_load, 0.0), aux)
        load_share = onsite_load / ac_supply if ac_supply else 0.0
        aux_share = onsite_aux / ac_supply if ac_supply else 0.0
        remaining_share = (
            max(ac_supply - onsite_load - onsite_aux, 0.0) / ac_supply
            if ac_supply
            else 0.0
        )
        base_import = flow.grid_import_kwh - flow.grid_charge_kwh
        grid_load = min(base_import, max(demand - onsite_load, 0.0))
        grid_aux = max(base_import - grid_load, 0.0)
        charging_supply = (
            max(ac_supply - onsite_load - onsite_aux, 0.0) + flow.grid_charge_kwh
        )
        record(
            "grid_charge_within_import",
            flow.grid_charge_kwh - flow.grid_import_kwh,
            index,
            scale,
            bound=True,
        )
        record(
            "charging_supply", (charge - charging_supply) / dt, index, scale, bound=True
        )
        record(
            "direct_pv_load",
            (flow.direct_pv_to_load_kwh - flow.pv_available_kwh * load_share) / dt,
            index,
            scale,
        )
        record(
            "direct_pv_aux",
            (flow.direct_pv_to_aux_kwh - flow.pv_available_kwh * aux_share) / dt,
            index,
            scale,
        )
        record(
            "direct_pv_charge",
            (
                flow.direct_pv_to_charge_kwh
                - (
                    flow.pv_available_kwh * remaining_share * charge / charging_supply
                    if charging_supply
                    else 0.0
                )
            )
            / dt,
            index,
            scale,
        )
        record("grid_to_load", (flow.grid_to_load_kwh - grid_load) / dt, index, scale)
        record("grid_to_aux", (flow.grid_to_aux_kwh - grid_aux) / dt, index, scale)
        residue_fraction = (
            max(1 - charge / charging_supply, 0.0) if charging_supply else 0.0
        )
        record(
            "no_storage_export_or_curtailment",
            discharge * remaining_share * residue_fraction / dt,
            index,
            scale,
        )
        for field in ("export_sources", "curtailed_sources"):
            for origin in ("grid_kwh", "initial_unknown_kwh"):
                record(
                    field + ":" + origin,
                    getattr(getattr(flow, field), origin) / dt,
                    index,
                    scale,
                )
        for origin in ("pv_kwh", "grid_kwh", "initial_unknown_kwh"):
            emitted = math.fsum(
                getattr(unit.delivered_ac, origin) for unit in flow.units
            )
            incoming = emitted + (flow.pv_available_kwh if origin == "pv_kwh" else 0.0)
            expected_load = incoming * load_share + (
                grid_load if origin == "grid_kwh" else 0.0
            )
            expected_aux = incoming * aux_share + (
                grid_aux if origin == "grid_kwh" else 0.0
            )
            record(
                "pcc_mixing_load:" + origin,
                (getattr(flow.load_sources, origin) - expected_load) / dt,
                index,
                scale,
            )
            record(
                "pcc_mixing_aux:" + origin,
                (getattr(flow.aux_sources, origin) - expected_aux) / dt,
                index,
                scale,
            )
            record(
                "battery_to_load:" + origin,
                (getattr(flow.battery_to_load_ac, origin) - emitted * load_share) / dt,
                index,
                scale,
            )
            record(
                "battery_to_aux:" + origin,
                (getattr(flow.battery_to_aux_ac, origin) - emitted * aux_share) / dt,
                index,
                scale,
            )
            charge_origin = incoming * remaining_share + (
                flow.grid_charge_kwh if origin == "grid_kwh" else 0.0
            )
            for unit in flow.units:
                expected_received = (
                    unit.received_ac.total * charge_origin / charging_supply
                    if charging_supply
                    else 0.0
                )
                record(
                    "unit:" + unit.unit.id + ":pcc_mixing_charge:" + origin,
                    (getattr(unit.received_ac, origin) - expected_received) / dt,
                    index,
                    scale,
                )
            supply = (
                flow.pv_available_kwh
                if origin == "pv_kwh"
                else flow.grid_import_kwh
                if origin == "grid_kwh"
                else 0.0
            ) + math.fsum(getattr(f.delivered_ac, origin) for f in flow.units)
            used = math.fsum(
                getattr(getattr(flow, field), origin)
                for field in (
                    "load_sources",
                    "aux_sources",
                    "export_sources",
                    "curtailed_sources",
                )
            ) + math.fsum(getattr(f.received_ac, origin) for f in flow.units)
            record("pcc_source_" + origin, (supply - used) / dt, index, scale)
        following: dict[str, EnergyOrigins] = {}
        for unit in flow.units:
            uid, model = unit.unit.id, models[unit.unit.id].for_mode(site.limits.mode)
            if unit.unit != models[uid]:
                raise InvalidInput("unit model changed inside the frozen trace")
            if unit.mode != site.limits.mode:
                raise InvalidInput(
                    "unit mode differs from the common connection interval"
                )
            power_scale = max(
                model.charge_ac_kw, model.discharge_ac_kw, model.internal_aux_kw
            )
            c, d = unit.received_ac.total / dt, unit.delivered_ac.total / dt
            state_scale = max(
                model.usable_window_kwh, unit.before.total, unit.after.total
            )
            prefix = "unit:" + uid + ":"
            boundary = witnesses[uid].advance_storage(unit, site.interval)
            # The hard inventory budget uses exact interval integration.
            # Only representation ULPs of transferred power/capacity apply;
            # an absolute kWh tolerance never finances short-interval delivery.
            record(
                prefix + "inventory_charge_power",
                c - boundary.charge_kw,
                index,
                power_scale,
                bound=True,
                hard_allowance=math.fsum(
                    math.ulp(v) if v else 0.0 for v in (c, boundary.charge_kw)
                ),
            )
            record(
                prefix + "inventory_discharge_power",
                d - boundary.discharge_kw,
                index,
                power_scale,
                bound=True,
                hard_allowance=math.fsum(
                    math.ulp(v) if v else 0.0 for v in (d, boundary.discharge_kw)
                ),
            )
            record(
                prefix + "hard_window",
                boundary.capacity_violation_kwh,
                index,
                state_scale,
                bound=True,
                energy=True,
                hard_allowance=math.ulp(model.usable_window_kwh)
                if model.usable_window_kwh
                else 0.0,
            )
            record(
                prefix + "hard_reserve",
                boundary.reserve_violation_kwh,
                index,
                state_scale,
                bound=True,
                energy=True,
                hard_allowance=math.ulp(unit.reserve_kwh) if unit.reserve_kwh else 0.0,
                task=True,
            )
            record(
                prefix + "reserve_binding",
                unit.reserve_kwh - flow.frame.reserves_kwh[uid],
                index,
                state_scale,
                energy=True,
            )
            record(
                prefix + "charge_limit",
                c - model.charge_ac_kw,
                index,
                model.charge_ac_kw,
                bound=True,
            )
            record(
                prefix + "discharge_limit",
                d - model.discharge_ac_kw,
                index,
                model.discharge_ac_kw,
                bound=True,
            )
            record(prefix + "device_direction", min(c, d), index, power_scale)
            record(
                prefix + "charge_command",
                c - unit.command.charge_kw,
                index,
                power_scale,
                bound=True,
            )
            record(
                prefix + "discharge_command",
                d - unit.command.discharge_kw,
                index,
                power_scale,
                bound=True,
            )
            record(
                prefix + "window",
                unit.after.total - model.usable_window_kwh,
                index,
                state_scale,
                bound=True,
                energy=True,
            )
            record(
                prefix + "reserve",
                min(unit.reserve_kwh - unit.after.total, d * dt / model.eta_discharge),
                index,
                state_scale,
                bound=True,
                energy=True,
                task=True,
            )
            expected_standing = unit.before.total * -math.expm1(
                -model.standing_loss_rate_per_hour * dt
            )
            expected_internal = min(
                max(unit.before.total - expected_standing, 0.0),
                model.internal_aux_kw * dt,
            )
            record(
                prefix + "standing_loss",
                (unit.standing_loss.total - expected_standing) / dt,
                index,
                power_scale,
            )
            record(
                prefix + "internal_aux",
                (unit.internal_aux.total - expected_internal) / dt,
                index,
                power_scale,
            )
            record(
                prefix + "internal_aux_shortfall",
                (
                    unit.internal_aux_unserved_kwh
                    + unit.internal_aux.total
                    - model.internal_aux_kw * dt
                )
                / dt,
                index,
                model.internal_aux_kw,
            )
            record(
                prefix + "internal_aux_unserved",
                unit.internal_aux_unserved_kwh / dt,
                index,
                model.internal_aux_kw,
                bound=True,
                task=True,
            )
            record(
                prefix + "discharge_efficiency",
                (
                    unit.delivered_ac.total
                    - unit.withdrawn_internal.total * model.eta_discharge
                )
                / dt,
                index,
                model.discharge_ac_kw,
            )
            for origin in ("pv_kwh", "grid_kwh", "initial_unknown_kwh"):
                before = getattr(unit.before, origin)
                fraction = before / unit.before.total if unit.before.total else 0.0
                for field in ("standing_loss", "internal_aux", "withdrawn_internal"):
                    record(
                        prefix + "mixing_" + field + ":" + origin,
                        (
                            getattr(getattr(unit, field), origin)
                            - getattr(unit, field).total * fraction
                        )
                        / dt,
                        index,
                        power_scale,
                    )
                record(
                    prefix + "continuity_" + origin,
                    before - getattr(preceding[uid], origin),
                    index,
                    state_scale,
                    energy=True,
                    # Replay carries the exact preceding origin object;
                    # continuity is identity, not a fresh arithmetic result.
                    hard_allowance=0.0,
                )
                expected = (
                    before
                    - getattr(unit.standing_loss, origin)
                    - getattr(unit.internal_aux, origin)
                    - getattr(unit.withdrawn_internal, origin)
                    + getattr(unit.received_ac, origin) * model.eta_charge
                )
                record(
                    prefix + "state_" + origin,
                    (getattr(unit.after, origin) - expected) / dt,
                    index,
                    power_scale,
                )
                record(
                    prefix + "discharge_source_" + origin,
                    (
                        getattr(unit.delivered_ac, origin)
                        - getattr(unit.withdrawn_internal, origin) * model.eta_discharge
                    )
                    / dt,
                    index,
                    power_scale,
                )
            following[uid] = unit.after
        preceding = following
    for uid, minimum in terminal_min_kwh.items():
        if minimum is not None:
            if not math.isfinite(minimum) or minimum < 0:
                raise InvalidInput(
                    "finite nonnegative per-unit terminal minimum required"
                )
            record(
                "unit:" + uid + ":terminal_minimum",
                witnesses[uid].terminal_violation(minimum),
                len(flows) - 1,
                max(minimum, models[uid].model.usable_window_kwh),
                bound=True,
                energy=True,
                hard_allowance=math.ulp(minimum) if minimum else 0.0,
                task=True,
            )
    return PlantVerification(tuple(checks.values()), tolerance, frozenset(task_codes))
