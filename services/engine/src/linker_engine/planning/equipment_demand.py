"""Replay customer-declared AC scenarios over cited candidate usable windows."""

from __future__ import annotations

from typing import Annotated, cast

from pydantic import Field, ValidationError

from .assets import Assets
from .canonical import Object, digest, encode
from .dispatch import peak_shaving_with_reserve, replay, self_consumption_with_reserve
from .dispatch_checks import verify
from .energy_declarations import object_value, schedule, terminal
from .energy_equipment import assess_energy_equipment
from .energy_inputs import (
    BatteryParameters,
    Document,
    EnergyInputs,
    Identifier,
    Nonnegative,
    SchemaVersion,
    storage_only_project,
)
from .energy_metrics import metrics
from .energy_preparation import prepare_energy
from .errors import InvalidInput
from .frozen_profiles import frozen_profile
from .numerical_tolerance import Tolerance
from .product_sources import ProductSources
from .profile_assets import profile_dependencies
from .profile_selections import ProfileSelections
from .records import Actor
from .worker import Control
from .workspace import Workspace

MODEL = "single_ac_equipment_demand_v1"


class EquipmentDemand(Document):
    schema_version: SchemaVersion
    initial_usable_fraction: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    source_note: Identifier
    max_unserved_load_kwh: Nonnegative


def demand_scenario(
    inputs: Object,
) -> tuple[EquipmentDemand, EnergyInputs, BatteryParameters]:
    try:
        demand = EquipmentDemand.model_validate(inputs.get("equipment_demand"))
    except ValidationError as error:
        raise InvalidInput(
            "complete the customer demand declaration",
            fields=tuple(
                "equipment_demand"
                + (
                    "." + ".".join(str(part) for part in item["loc"])
                    if item["loc"]
                    else ""
                )
                for item in error.errors()
            ),
        ) from error
    if not isinstance(inputs.get("energy_scenario"), dict):
        raise InvalidInput("declare the energy scenario", fields=("energy_scenario",))
    settings = object_value(inputs.get("energy_scenario"), "energy scenario")
    if {"equipment_plant", "equipment_plant_setup"}.intersection(
        inputs
    ) or settings.get("coupling", "independent_ac") != "independent_ac":
        raise InvalidInput(
            "equipment demand requires a single independent AC scenario",
            fields=("equipment_demand",),
        )
    if not demand.source_note.strip():
        raise InvalidInput(
            "initial usable fraction requires its source",
            fields=("equipment_demand.source_note",),
        )
    note = settings.get("source_note")
    if not isinstance(note, str) or not note.strip():
        raise InvalidInput(
            "storage scenario requires its source",
            fields=("energy_scenario.source_note",),
        )
    if not isinstance(settings.get("battery"), dict):
        raise InvalidInput(
            "declare storage scenario parameters", fields=("energy_scenario.battery",)
        )
    battery = object_value(settings.get("battery"), "battery scenario")
    try:
        parameters = BatteryParameters.model_validate(
            {
                **battery,
                "schema_version": 1,
                "model": "constant_window_single_ac_bus_v1",
                "parameter_basis": "explicit_scenario",
                "usable_window_kwh": 0,
            }
        )
    except ValidationError as error:
        raise InvalidInput(
            "complete the storage scenario parameters",
            fields=tuple(
                "energy_scenario.battery." + ".".join(str(part) for part in item["loc"])
                for item in error.errors()
            ),
        ) from error
    periods = schedule(
        settings.get("schedule"), storage_only=storage_only_project(inputs)
    )
    selected = ProfileSelections.read(inputs.get("profile_selections")).selected
    pv_disabled = all(
        isinstance(p, dict) and p.get("pv_enabled") is False for p in periods
    )
    scenario = EnergyInputs.read(
        {
            "schema_version": 1,
            "gross_load_asset_id": selected.get("gross_load"),
            "critical_load_asset_id": selected.get("critical_load"),
            "pv_available_asset_id": None
            if pv_disabled
            else selected.get("pv_available_ac"),
            "aux_ac_asset_id": selected.get("aux_ac")
            if settings.get("aux_ac_kw") is None
            else None,
            **(
                {"aux_ac_kw": settings["aux_ac_kw"]}
                if settings.get("aux_ac_kw") is not None
                else {}
            ),
            # The model is constructed in memory for each candidate; no parameter asset is created.
            "battery_parameters_asset_id": "candidate-window",
            "initial_inventory": {
                "pv_kwh": 0,
                "grid_kwh": 0,
                "initial_unknown_kwh": 0,
                "basis": "user_declared",
                "source_note": demand.source_note,
            },
            "schedule": periods,
            "controller": settings.get("controller"),
            "terminal_min_kwh": terminal(settings),
        }
    )
    EnergyInputs.from_project(
        {**inputs, "energy_replay": scenario.model_dump(mode="json")}
    )
    return demand, scenario, parameters


def pin_demand_profiles(
    workspace: Workspace,
    products: ProductSources,
    actor: Actor,
    project_id: str,
    inputs: Object,
) -> dict[str, str]:
    _, scenario, _ = demand_scenario(inputs)
    assets = Assets(workspace)
    pinned: dict[str, str] = {}
    for role, asset_id in scenario.profiles().items():
        asset = assets.get(actor, project_id, asset_id)
        products.check_profile(asset.metadata)
        pinned.update(profile_dependencies(asset, role, inputs, workspace.blobs))
    return pinned


def replay_demand(
    workspace: Workspace,
    products: ProductSources,
    inputs: Object,
    basis: Object,
    pinned: Object,
    search: Object,
    control: Control,
    *,
    tolerance: Tolerance,
    max_intervals: int,
    work_budget: int,
) -> None:
    demand, scenario, parameters = demand_scenario(inputs)
    profiles = {}
    for role in scenario.profiles():
        raw, metadata = str(pinned[role + ".raw"]), str(pinned[role + ".metadata"])
        products.check_profile(workspace.blobs.object(metadata))
        profiles[role] = frozen_profile(
            workspace.blobs,
            raw,
            metadata,
            str(pinned[role + ".timezone"]) if role + ".timezone" in pinned else None,
        )
    prepared = prepare_energy(scenario, profiles, control, max_intervals=max_intervals)
    count, used, exhausted = len(prepared.frames), 0, False
    # All other physical inputs are fixed for this run; only the window varies.
    physical_by_capacity: dict[float, Object] = {}
    for candidate in cast(list[Object], search["candidates"]):
        control.checkpoint()
        outcome: Object = {
            "status": "unresolved",
            "reason": "usable_energy_not_established",
            "metrics": None,
            "equipment": None,
        }
        candidate["demand"] = outcome
        capacity = candidate.get("usable_energy_kwh")
        if not isinstance(capacity, (int, float)):
            continue
        model_parameters = parameters.model_copy(update={"usable_window_kwh": capacity})
        model = model_parameters.battery(
            digest(encode(model_parameters.model_dump(mode="json")))
        )
        initial = scenario.initial_inventory.model_copy(
            update={"initial_unknown_kwh": capacity * demand.initial_usable_fraction}
        )
        candidate_scenario = scenario.model_copy(update={"initial_inventory": initial})
        replay_inputs = {
            **inputs,
            "energy_replay": candidate_scenario.model_dump(mode="json"),
            "equipment_selection": candidate["selection"],
        }
        outcome["equipment"] = assess_energy_equipment(replay_inputs, basis, model)
        if any(period.reserve_kwh > capacity for period in scenario.schedule):
            outcome.update(status="violated", reason="scenario_not_feasible")
            continue
        if capacity in physical_by_capacity:
            outcome.update(physical_by_capacity[capacity])
            continue
        if used + count > work_budget:
            exhausted = True
            outcome["reason"] = "work_budget_exhausted"
            continue
        used += count
        flows = replay(
            prepared.frames,
            model,
            initial.energy(),
            peak_shaving_with_reserve
            if scenario.controller == "peak_shaving_with_reserve_v1"
            else self_consumption_with_reserve,
            checkpoint=control.checkpoint,
            tolerance=tolerance,
        )
        verification = verify(
            flows,
            model,
            tolerance,
            initial=initial.energy(),
            terminal_min_kwh=scenario.terminal_min_kwh,
        )
        values = metrics(flows, model)
        target_met = (
            cast(float, values["unserved_load_kwh"]) <= demand.max_unserved_load_kwh
        )
        physical_passed = all(
            check.passed
            for check in verification.checks
            if check.code != "load_supplied"
        )
        outcome.update(
            status="satisfied" if physical_passed and target_met else "violated",
            reason="scenario_not_feasible"
            if not physical_passed
            else "target_met"
            if target_met
            else "unserved_load_exceeds_target",
            metrics=values,
        )
        physical_by_capacity[capacity] = {
            "status": outcome["status"],
            "reason": outcome["reason"],
            "metrics": values,
        }
    for role in scenario.profiles():
        products.check_profile(workspace.blobs.object(str(pinned[role + ".metadata"])))
    search["demand"] = {
        "model": MODEL,
        "completion": "budget_exhausted" if exhausted else "complete",
        "interval_count": count,
        "work_used": used,
        "work_budget": work_budget,
    }
