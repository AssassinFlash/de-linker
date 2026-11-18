"""Profile-based optimistic physical bounds; these are not dispatch forecasts."""

from __future__ import annotations

import math
from datetime import datetime
from typing import cast

from .assets import Assets
from .canonical import Json, Object
from .energy_inputs import project_coupling, storage_only_project
from .equipment_evidence import EquipmentEvidence
from .equipment_fact_resolution import FactContext, FactUse, resolve_fact
from .equipment_inputs import EquipmentSelection
from .equipment_plant import EquipmentPlant
from .errors import InvalidInput
from .frozen_profiles import frozen_profile
from .interval import Interval
from .numerical_tolerance import Tolerance
from .product_sources import ProductSources
from .profile_assets import profile_dependencies
from .profile_selections import ProfileRole, ProfileSelections
from .records import Actor
from .regrid import regrid
from .worker import Control
from .workspace import Workspace

MODEL = "profile_physical_bounds_v1"
BASIS = "optimistic_full_initial_storage_lossless_upper_bound_not_dispatch"
CONTROLLERS = ("self_consumption_with_reserve_v1", "peak_shaving_with_reserve_v1")
PLANT_CONTROLLERS = {
    "proportional_available_power_self_consumption_v1": CONTROLLERS[0],
    "local_dc_then_proportional_ac_self_consumption_v1": CONTROLLERS[0],
    "proportional_peak_shaving_v1": CONTROLLERS[1],
}


def scenario(inputs: Object) -> tuple[Object, str | None, Json]:
    plant = {"equipment_plant", "equipment_plant_setup"}.intersection(inputs)
    plant_setup = inputs.get("energy_plant_setup") if plant else None
    settings = inputs.get("energy_scenario")
    if not isinstance(settings, dict) or settings.get("controller") not in CONTROLLERS:
        settings = plant_setup if isinstance(plant_setup, dict) else {}
    coupling = project_coupling(inputs)
    controller = settings.get("controller")
    goal = (
        controller
        if controller in CONTROLLERS
        else PLANT_CONTROLLERS.get(str(controller))
    )
    return settings, goal, coupling


def requested(inputs: Object) -> bool:
    return (
        not {"equipment_demand", "backup_demand"}.intersection(inputs)
        and scenario(inputs)[1] is not None
    )


def periods(
    inputs: Object, *, baseline_only: bool = False
) -> list[tuple[Interval, bool, float | None, bool]]:
    settings, controller, coupling = scenario(inputs)
    raw = settings.get("schedule")
    if not isinstance(raw, list) or not raw:
        raise InvalidInput(
            "select the profile horizon", fields=("energy_scenario.schedule",)
        )
    result: list[tuple[Interval, bool, float | None, bool]] = []
    for item in raw:
        if (
            not isinstance(item, dict)
            or item.get("mode") != "connected"
            or type(item.get("pv_enabled")) is not bool
        ):
            raise InvalidInput(
                "profile bounds require explicit connected periods and PV availability",
                fields=("energy_scenario.schedule",),
            )
        try:
            interval = Interval(
                datetime.fromisoformat(str(item.get("start_utc"))),
                datetime.fromisoformat(str(item.get("end_utc"))),
            )
        except ValueError as error:
            raise InvalidInput(
                "profile horizon requires explicit timestamps"
            ) from error
        cap = item.get("import_cap_kw")
        if cap is not None and (
            type(cap) not in (int, float)
            or not math.isfinite(cast(float, cap))
            or cast(float, cap) < 0
        ):
            raise InvalidInput("grid import target must be nonnegative")
        if not baseline_only and controller == CONTROLLERS[1] and cap is None:
            raise InvalidInput(
                "peak shaving requires the grid import target",
                fields=("energy_scenario.schedule.import_cap_kw",),
            )
        if result and result[-1][0].end != interval.start:
            raise InvalidInput("profile horizon must be ordered and continuous")
        result.append(
            (
                interval,
                cast(bool, item["pv_enabled"]) and not storage_only_project(inputs),
                cast(float | None, cap),
                # Allow headroom charging in the upper-bound case unless the
                # schedule explicitly forbids it.
                item.get("allow_grid_charge") is not False,
            )
        )
    if (
        not baseline_only
        and controller == CONTROLLERS[0]
        and coupling == "independent_ac"
        and not any(pv for _, pv, _, _ in result)
    ):
        raise InvalidInput(
            "self consumption requires the owned PV profile",
            fields=("profile_selections.selected.pv_available_ac",),
        )
    return result


def pin_profiles(
    workspace: Workspace,
    products: ProductSources,
    actor: Actor,
    project_id: str,
    inputs: Object,
    *,
    baseline_only: bool = False,
    skip_pv: bool = False,
) -> dict[str, str]:
    source = inputs.get("profile_selections")
    if source is None:
        return {}
    selected = ProfileSelections.read(source).selected
    _, _, coupling = scenario(inputs)
    has_load = "gross_load" in selected
    needs_pv = (
        any(pv for _, pv, _, _ in periods(inputs, baseline_only=baseline_only))
        if has_load
        else not storage_only_project(inputs)
    )
    roles: list[ProfileRole] = ["gross_load"] if has_load else []
    if (
        needs_pv
        and not skip_pv
        and coupling not in ("shared_dc", "plant_shared_dc")
        and "pv_available_ac" in selected
    ):
        roles.append("pv_available_ac")
    pinned = {}
    for role in roles:
        identity = selected[role]
        asset = Assets(workspace).get(actor, project_id, identity)
        products.check_profile(asset.metadata)
        pinned.update(profile_dependencies(asset, role, inputs, workspace.blobs))
    return pinned


def peak_targets(
    schedule: list[tuple[Interval, bool, float | None, bool]],
) -> Object:
    caps = {cap for _, _, cap, _ in schedule}
    if len(caps) == 1:
        return {"peak_target_kw": next(iter(caps))}
    return {
        "peak_target_kw": None,
        "peak_target_periods": [
            {
                "start_utc": interval.start.isoformat(),
                "end_utc": interval.end.isoformat(),
                "import_cap_kw": cap,
            }
            for interval, _, cap, _ in schedule
            if cap is not None
        ],
    }


def evaluate_bounds(
    workspace: Workspace,
    products: ProductSources,
    inputs: Object,
    basis: Object | None,
    pinned: Object,
    search: Object,
    control: Control,
    *,
    max_intervals: int,
    work_budget: int,
    tolerance: Tolerance | None,
) -> None:
    schedule = periods(inputs, baseline_only=basis is None)
    profiles = {}
    for role in ("gross_load", "pv_available_ac"):
        if role + ".raw" not in pinned:
            continue
        metadata = str(pinned[role + ".metadata"])
        products.check_profile(workspace.blobs.object(metadata))
        profiles[role] = frozen_profile(
            workspace.blobs,
            str(pinned[role + ".raw"]),
            metadata,
            str(pinned[role + ".timezone"]) if role + ".timezone" in pinned else None,
        )
        if profiles[role].measurement != role:
            raise InvalidInput("selected profile measurement differs")
    start, end = schedule[0][0].start, schedule[-1][0].end
    edges = {
        start,
        end,
        *(p.start for p, _, _, _ in schedule),
        *(p.end for p, _, _, _ in schedule),
    }
    for profile in profiles.values():
        for interval in profile.intervals:
            if start < interval.start < end:
                edges.add(interval.start)
            if start < interval.end < end:
                edges.add(interval.end)
    axis = sorted(edges)
    if len(axis) - 1 > max_intervals:
        raise InvalidInput("aligned horizon exceeds the configured interval limit")
    target = tuple(Interval(a, b) for a, b in zip(axis, axis[1:], strict=False))
    aligned = {role: regrid(profile, target) for role, profile in profiles.items()}
    frames = []
    period_index = 0
    for index, interval in enumerate(target):
        while interval.start >= schedule[period_index][0].end:
            period_index += 1
        _, pv_enabled, cap, grid_charge = schedule[period_index]
        load = aligned["gross_load"].values_kw[index]
        pv = (
            aligned["pv_available_ac"].values_kw[index]
            if pv_enabled and "pv_available_ac" in aligned
            else 0
        )
        frames.append((interval.hours, load, pv, cap, grid_charge))
    _, controller, coupling = scenario(inputs)
    shared_dc = coupling in ("shared_dc", "plant_shared_dc")
    pv_requested = any(pv for _, pv, _, _ in schedule)
    # A selected AC trace can describe only the separate AC branch of a DC
    # plant. The DC PV stage is not interchangeable with site AC output.
    pv_evidence_missing = pv_requested and (
        shared_dc or "pv_available_ac" not in aligned
    )
    baseline: Object = {
        "load_kwh": math.fsum(h * load for h, load, _, _, _ in frames),
        "pv_available_kwh": math.fsum(h * pv for h, _, pv, _, _ in frames),
        "direct_pv_use_kwh": math.fsum(
            h * min(load, pv) for h, load, pv, _, _ in frames
        ),
        "grid_import_kwh": math.fsum(
            h * max(0, load - pv) for h, load, pv, _, _ in frames
        ),
        "grid_export_kwh": math.fsum(
            h * max(0, pv - load) for h, load, pv, _, _ in frames
        ),
        "peak_grid_import_kw": max(max(0, load - pv) for _, load, pv, _, _ in frames),
        "over_target_kwh": math.fsum(
            h * max(0, load - pv - cap)
            for h, load, pv, cap, _ in frames
            if cap is not None
        ),
    }
    if basis is None and any(cap is None for _, _, _, cap, _ in frames):
        baseline["over_target_kwh"] = None
    meter_missing = bool(
        {"equipment_plant", "equipment_plant_setup"}.intersection(inputs)
    ) and coupling not in ("plant_ac", "plant_shared_dc")
    if pv_evidence_missing or meter_missing:
        for key in baseline.keys() - {"load_kwh"}:
            baseline[key] = None
    profile_summary: Object = {
        "model": MODEL,
        "controller": controller,
        "horizon_start_utc": start.isoformat(),
        "horizon_end_utc": end.isoformat(),
        "interval_count": len(frames),
        "baseline": baseline,
    }
    if controller == CONTROLLERS[1]:
        profile_summary.update(peak_targets(schedule))
    control.checkpoint()
    if basis is None:
        search["demand"] = profile_summary
        return
    evidence = EquipmentEvidence(basis)
    used, exhausted = 0, False
    cache: dict[tuple[float, float, float], Object] = {}

    def power(key: str, context: FactContext, use: FactUse) -> Object | None:
        fact = cast(
            Object, evidence.compiled(context.selection.inverter_product_id)["facts"]
        ).get(key)
        if not isinstance(fact, dict) or fact.get("quantity") != "active_power":
            return None
        resolved = resolve_fact(fact, context, use).fact
        return (
            resolved
            if resolved is not None and resolved.get("shape") == "scalar"
            else None
        )

    def unresolved(reason: str, missing: list[str]) -> Object:
        return {
            "status": "unresolved",
            "reason": reason,
            "basis": BASIS,
            "additional_pv_use_upper_kwh": None,
            "peak_import_lower_bound_kw": None,
            "missing_facts": cast(list[Json], missing),
            "source_facts": [],
        }

    for candidate in cast(list[Object], search["candidates"]):
        control.checkpoint()
        raw_plant = candidate.get("plant")
        missing_topology = (
            ["project_pv_available_ac_profile"] if pv_evidence_missing else []
        )
        if shared_dc and pv_requested:
            missing_topology = ["project_pv_output_through_assigned_dc_converters"]
        elif raw_plant is not None and coupling not in ("plant_ac", "plant_shared_dc"):
            missing_topology.append("common_ac_meter_and_storage_topology")
        if missing_topology:
            candidate["demand"] = unresolved(
                "profile_topology_evidence_missing", missing_topology
            )
            continue

        if raw_plant is None:
            units = [
                (
                    EquipmentSelection.read(candidate["selection"]),
                    candidate.get("usable_energy_kwh"),
                )
            ]
        else:
            plant = EquipmentPlant.read(raw_plant)
            if any(
                unit.selection.battery_product_id is not None
                and unit.selection.pv_dc_kw != 0
                for unit in plant.units
            ):
                candidate["demand"] = unresolved(
                    "profile_topology_evidence_missing",
                    ["separate_ac_storage_converter_pv_allocation"],
                )
                continue
            assessment = workspace.blobs.object(
                cast(str, candidate["assessment_sha256"])
            )
            capacities = {
                row["id"]: next(
                    (
                        check["actual"]
                        for check in cast(
                            list[Object], cast(Object, row["assessment"])["checks"]
                        )
                        if check["id"] == "usable_energy"
                    ),
                    None,
                )
                for row in cast(list[Object], assessment["systems"])
            }
            units = [(unit.selection, capacities[unit.id]) for unit in plant.units]

        missing: list[str] = []
        refs: list[Json] = []
        cap_value = charge = discharge = 0.0
        for selection, capacity in units:
            if selection.battery_product_id is None:
                continue
            missing.extend(
                ("documented_conversion_and_storage_losses", "initial_stored_energy")
            )
            context = FactContext(selection, evidence.products)
            charge_limits: tuple[tuple[str, FactUse], ...]
            discharge_limits: tuple[tuple[str, FactUse], ...]
            if shared_dc:
                # With PV disabled, every kW delivered from storage traverses
                # the battery terminals and the shared DC-to-AC bridge.
                charge_limits = (
                    ("max_battery_terminal_charge_power_kw", "battery_terminal_power"),
                    ("max_battery_charge_ac_power_kw", "grid_input_ceiling"),
                )
                discharge_limits = (
                    (
                        "max_battery_terminal_discharge_power_kw",
                        "battery_terminal_power",
                    ),
                    ("ac_output_kw_max", "grid_output_ceiling"),
                )
            else:
                charge_limits = (("continuous_battery_charge_ac_power_kw", "numeric"),)
                discharge_limits = (
                    ("continuous_battery_discharge_ac_power_kw", "numeric"),
                )
            unit_power: list[float] = []
            for limits in (charge_limits, discharge_limits):
                ceiling = math.inf
                for key, use in limits:
                    fact = power(key, context, use)
                    if fact is None:
                        missing.append(key)
                        continue
                    ceiling = min(ceiling, cast(float, fact["value"]))
                    if fact not in refs:
                        refs.append(fact)
                unit_power.append(ceiling)
            charge += unit_power[0]
            discharge += unit_power[1]
            if isinstance(capacity, (int, float)):
                cap_value += capacity
            else:
                missing.append("usable_energy_at_selected_voltage_and_assembly")
                cap_value = math.inf
        # Pooling independent AC windows relaxes unit dispatch and coordination.
        # The one project trace is evaluated once against these upper limits.
        missing = list(dict.fromkeys(missing))
        model_key = (cap_value, charge, discharge)
        outcome = cache.get(model_key)
        if outcome is None:
            if used + len(frames) > work_budget:
                exhausted = True
                candidate["demand"] = {
                    "status": "unresolved",
                    "reason": "work_budget_exhausted",
                    "basis": BASIS,
                    "additional_pv_use_upper_kwh": None,
                    "peak_import_lower_bound_kw": None,
                    "missing_facts": cast(list[Json], missing),
                    "source_facts": refs,
                }
                continue
            used += len(frames)
            # PV shifting starts with no attributed PV; peak screening grants a
            # full battery. Both are explicit best-case bounds, not assumed SOC.
            pv_stored, peak_stored, shifted, peak_floor, target_impossible = (
                0.0,
                cap_value,
                0.0,
                0.0,
                False,
            )
            peak_block_hours = peak_block_kwh = 0.0
            for index, (h, load, pv, cap, grid_charge) in enumerate(frames):
                if index % 1024 == 0:
                    control.checkpoint()
                net = load - pv
                surplus = max(0, -net)
                charged = min(surplus, charge) * h
                pv_stored = min(cap_value, pv_stored + charged)
                delivered = min(max(0, net), discharge, pv_stored / h)
                pv_stored = max(0, pv_stored - delivered * h)
                shifted += delivered * h
                if cap is not None:
                    recharge = surplus + (
                        max(0, cap - max(0, net)) if grid_charge else 0
                    )
                    peak_stored = min(
                        cap_value, peak_stored + min(recharge, charge) * h
                    )
                    required = max(0, net - cap)
                    reduction = min(required, discharge, peak_stored / h)
                    peak_stored = max(0, peak_stored - reduction * h)
                    met = math.isclose(
                        required,
                        reduction,
                        rel_tol=tolerance.relative if tolerance else 0,
                        abs_tol=tolerance.absolute_kw if tolerance else 0,
                    )
                    # Import across a sustained deficit block must cover net
                    # energy minus at most one initial storage window. Grid
                    # recharge inside the block is itself import.
                    if net <= 0:
                        peak_block_hours = peak_block_kwh = 0.0
                    else:
                        peak_block_hours += h
                        peak_block_kwh += net * h
                        peak_floor = max(
                            peak_floor,
                            net - min(discharge, cap_value / h),
                            (peak_block_kwh - cap_value) / peak_block_hours,
                        )
                    target_impossible = target_impossible or (
                        reduction < required and not met
                    )
            outcome = {
                "status": "violated"
                if controller == CONTROLLERS[1] and target_impossible
                else "bounded",
                "reason": "peak_target_exceeds_optimistic_physical_bound"
                if controller == CONTROLLERS[1] and target_impossible
                else "optimistic_profile_bound",
                "basis": BASIS,
                "additional_pv_use_upper_kwh": min(
                    shifted,
                    cast(float, baseline["grid_import_kwh"]),
                    cast(float, baseline["grid_export_kwh"]),
                ),
                "peak_import_lower_bound_kw": min(
                    peak_floor, cast(float, baseline["peak_grid_import_kw"])
                )
                if controller == CONTROLLERS[1]
                else None,
            }
            cache[model_key] = outcome
        candidate["demand"] = {
            **outcome,
            "missing_facts": cast(list[Json], missing),
            "source_facts": refs,
        }
    search["demand"] = {
        **profile_summary,
        "completion": "budget_exhausted" if exhausted else "complete",
        "work_used": used,
        "work_budget": work_budget,
    }
