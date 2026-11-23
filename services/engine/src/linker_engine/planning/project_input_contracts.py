"""Explicit complete-input writers; omitted metadata keeps legacy command hashes.

Import-time dependencies stay in the standard library so the native read-only
deployment probe can use the same retained-feature detector without a workspace.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .canonical import Object

type InputContract = Literal[
    "installation_circuit_electrical_v1",
    "pv_plant_string_plan_v1",
    "installation_pv_string_links_v1",
    "pv_string_links_direct_beam_visibility_v1",
    "pv_string_links_direct_beam_geometric_pv_v1",
    "grid_connection_evidence_v1",
    "installation_terminal_bindings_v1",
    "installation_conductor_reference_current_v1",
    "installation_physical_materials_v1",
    "project_engineering_v10",
    "installation_conductor_manufacturer_v1",
    "installation_mounting_quantities_v1",
    "installation_protection_evidence_v1",
    "geometry_image_calibration_v1",
    "storage_only_brief_v1",
    "equipment_use_v1",
    "energy_operating_modes_v1",
    "nullable_equipment_requirements_v1",
    "authored_energy_calculation_v1",
    "authored_equipment_discovery_v1",
    "known_pv_ac_reference_v1",
    "backup_demand_v1",
    "existing_system_v1",
    "project_panel_parameters_v1",
    "inquiry_quantities_v1",
]
INQUIRY_QUANTITIES_INPUT_CONTRACT: InputContract = "inquiry_quantities_v1"
PANEL_PARAMETERS_INPUT_CONTRACT: InputContract = "project_panel_parameters_v1"
EXISTING_SYSTEM_INPUT_CONTRACT: InputContract = "existing_system_v1"
BACKUP_DEMAND_INPUT_CONTRACT: InputContract = "backup_demand_v1"
KNOWN_PV_INPUT_CONTRACT: InputContract = "known_pv_ac_reference_v1"
AUTHORED_EQUIPMENT_INPUT_CONTRACT: InputContract = "authored_equipment_discovery_v1"
AUTHORED_ENERGY_INPUT_CONTRACT: InputContract = "authored_energy_calculation_v1"
NULLABLE_EQUIPMENT_INPUT_CONTRACT: InputContract = "nullable_equipment_requirements_v1"
ENERGY_MODES_INPUT_CONTRACT: InputContract = "energy_operating_modes_v1"
EQUIPMENT_USE_INPUT_CONTRACT: InputContract = "equipment_use_v1"
STORAGE_ONLY_INPUT_CONTRACT: InputContract = "storage_only_brief_v1"
CALIBRATION_INPUT_CONTRACT: InputContract = "geometry_image_calibration_v1"
MOUNTING_QUANTITIES_INPUT_CONTRACT: InputContract = (
    "installation_mounting_quantities_v1"
)
PROTECTION_EVIDENCE_INPUT_CONTRACT: InputContract = (
    "installation_protection_evidence_v1"
)
CONDUCTOR_MANUFACTURER_INPUT_CONTRACT: InputContract = (
    "installation_conductor_manufacturer_v1"
)
ENGINEERING_V10_INPUT_CONTRACT: InputContract = "project_engineering_v10"
MATERIALS_INPUT_CONTRACT: InputContract = "installation_physical_materials_v1"
REFERENCE_CURRENT_INPUT_CONTRACT: InputContract = (
    "installation_conductor_reference_current_v1"
)
TERMINAL_INPUT_CONTRACT: InputContract = "installation_terminal_bindings_v1"
GRID_CONNECTION_INPUT_CONTRACT: InputContract = "grid_connection_evidence_v1"
INPUT_CONTRACT: InputContract = "installation_pv_string_links_v1"
DIRECT_BEAM_INPUT_CONTRACT: InputContract = "pv_string_links_direct_beam_visibility_v1"
GEOMETRIC_PV_INPUT_CONTRACT: InputContract = (
    "pv_string_links_direct_beam_geometric_pv_v1"
)
PLANT_PV_INPUT_CONTRACT: InputContract = "pv_plant_string_plan_v1"
ELECTRICAL_INPUT_CONTRACT: InputContract = "installation_circuit_electrical_v1"
# Public complete-input writers, in release order. Each understands exactly
# the fields introduced by itself and every earlier released writer.
SUPPORTED_INPUT_CONTRACTS: tuple[str, ...] = (
    INPUT_CONTRACT,
    DIRECT_BEAM_INPUT_CONTRACT,
    GEOMETRIC_PV_INPUT_CONTRACT,
    PLANT_PV_INPUT_CONTRACT,
    ELECTRICAL_INPUT_CONTRACT,
    GRID_CONNECTION_INPUT_CONTRACT,
    TERMINAL_INPUT_CONTRACT,
    REFERENCE_CURRENT_INPUT_CONTRACT,
    MATERIALS_INPUT_CONTRACT,
    ENGINEERING_V10_INPUT_CONTRACT,
    CONDUCTOR_MANUFACTURER_INPUT_CONTRACT,
    MOUNTING_QUANTITIES_INPUT_CONTRACT,
    PROTECTION_EVIDENCE_INPUT_CONTRACT,
    CALIBRATION_INPUT_CONTRACT,
    STORAGE_ONLY_INPUT_CONTRACT,
    EQUIPMENT_USE_INPUT_CONTRACT,
    ENERGY_MODES_INPUT_CONTRACT,
    NULLABLE_EQUIPMENT_INPUT_CONTRACT,
    AUTHORED_ENERGY_INPUT_CONTRACT,
    AUTHORED_EQUIPMENT_INPUT_CONTRACT,
    KNOWN_PV_INPUT_CONTRACT,
    BACKUP_DEMAND_INPUT_CONTRACT,
    EXISTING_SYSTEM_INPUT_CONTRACT,
    PANEL_PARAMETERS_INPUT_CONTRACT,
    INQUIRY_QUANTITIES_INPUT_CONTRACT,
)


def _has_panel_parameters(inputs: Mapping[str, object]) -> bool:
    details = inputs.get("known_panel_details")
    if isinstance(details, Mapping) and any(
        details.get(key) is not None for key in ("count", "power_w", "system_kwp")
    ):
        return True
    geometry = inputs.get("geometry")
    specs = geometry.get("module_specs") if isinstance(geometry, Mapping) else None
    modules = list(specs) if isinstance(specs, list) else []
    installation = inputs.get("installation")
    materials = (
        installation.get("materials") if isinstance(installation, Mapping) else None
    )
    if isinstance(materials, list):
        modules.extend(
            basis.get("module")
            for row in materials
            if isinstance(row, Mapping)
            and isinstance(basis := row.get("mounting_quantity_basis"), Mapping)
        )
    return any(
        isinstance(module, Mapping) and "electrical" in module for module in modules
    )


def required_contracts(inputs: Mapping[str, object]) -> tuple[str, ...]:
    installation = inputs.get("installation")
    required = []
    if "inquiry_quantities" in inputs:
        required.append(INQUIRY_QUANTITIES_INPUT_CONTRACT)
    if _has_panel_parameters(inputs):
        required.append(PANEL_PARAMETERS_INPUT_CONTRACT)
    if "existing_system" in inputs:
        required.append(EXISTING_SYSTEM_INPUT_CONTRACT)
    if "backup_demand" in inputs:
        required.append(BACKUP_DEMAND_INPUT_CONTRACT)
    if any(
        isinstance(reference, Mapping)
        and reference.get("model") == "pvgis_5_3_known_ac_reference_v1"
        for reference in (
            inputs.get("pvgis_reference"),
            inputs.get("pvgis_reference_setup"),
        )
    ):
        required.append(KNOWN_PV_INPUT_CONTRACT)
    equipment_sources = [inputs]
    plant_setup = inputs.get("equipment_plant_setup")
    if isinstance(plant_setup, Mapping):
        units = plant_setup.get("units")
        equipment_sources.extend(
            unit["inputs"]
            for unit in (units if isinstance(units, list) else [])
            if isinstance(unit, Mapping) and isinstance(unit.get("inputs"), Mapping)
        )
    for source in equipment_sources:
        setup = source.get("equipment_setup")
        if isinstance(setup, Mapping) and "application" in setup:
            required.append(AUTHORED_EQUIPMENT_INPUT_CONTRACT)
            break
    scenario = inputs.get("energy_scenario")
    plant_energy = inputs.get("energy_plant_setup")
    if (
        isinstance(scenario, Mapping)
        and "battery_binding" not in scenario
        or isinstance(plant_energy, Mapping)
        and isinstance(plant_energy.get("units"), list)
        and any(
            isinstance(unit, Mapping)
            and isinstance(unit.get("settings"), Mapping)
            and "battery_binding" not in unit["settings"]
            for unit in plant_energy["units"]
        )
    ):
        required.append(AUTHORED_ENERGY_INPUT_CONTRACT)
    requirements = [inputs.get("equipment_requirements")]
    for key in ("equipment_plant", "equipment_plant_requirements"):
        plant = inputs.get(key)
        if not isinstance(plant, Mapping):
            continue
        requirements.append(plant.get("requirements"))
        if key == "equipment_plant_requirements":
            units = plant.get("units")
            requirements.extend(
                unit.get("requirements")
                for unit in (units if isinstance(units, list) else [])
                if isinstance(unit, Mapping)
            )
    # Editable drafts and selection/setup sizing were already nullable. Only
    # prepared requirements need a later reader and complete-input writer.
    if any(
        isinstance(demand, Mapping)
        and any(
            field in demand and demand[field] is None
            for field in ("required_usable_kwh", "required_discharge_ac_kw")
        )
        for demand in requirements
    ):
        required.append(NULLABLE_EQUIPMENT_INPUT_CONTRACT)
    for key in (
        "energy_scenario",
        "energy_plant_setup",
        "energy_replay",
        "energy_plant",
    ):
        energy = inputs.get(key)
        if not isinstance(energy, Mapping):
            continue
        if (
            "aux_ac_kw" in energy
            or (
                key in ("energy_scenario", "energy_plant_setup")
                and "controller" in energy
            )
            or energy.get("controller")
            in ("peak_shaving_with_reserve_v1", "proportional_peak_shaving_v1")
            or (
                (
                    key == "energy_replay"
                    and energy.get("coupling", "independent_ac") == "independent_ac"
                    or key == "energy_plant"
                    and energy.get("coupling") == "plant_ac"
                )
                and any(
                    field in energy and energy[field] is None
                    for field in ("pv_available_asset_id", "aux_ac_asset_id")
                )
            )
        ):
            required.append(ENERGY_MODES_INPUT_CONTRACT)
            break
    brief = inputs.get("brief")
    if isinstance(brief, Mapping) and brief.get("system_scope") == "storage_only":
        required.append(STORAGE_ONLY_INPUT_CONTRACT)
    selections = [inputs.get("equipment_setup"), inputs.get("equipment_selection")]
    controller_use = False
    for key in ("equipment_plant", "equipment_plant_setup"):
        plant = inputs.get(key)
        if not isinstance(plant, Mapping):
            continue
        groups = plant.get("parallel_groups")
        controller_use = controller_use or any(
            isinstance(group, Mapping) and group.get("controller_use") is not None
            for group in (groups if isinstance(groups, list) else [])
        )
        units = plant.get("units")
        for unit in units if isinstance(units, list) else []:
            if not isinstance(unit, Mapping):
                continue
            selections.append(unit.get("selection"))
            unit_inputs = unit.get("inputs")
            if isinstance(unit_inputs, Mapping):
                selections.extend(
                    unit_inputs.get(field)
                    for field in ("equipment_setup", "equipment_selection")
                )
    if controller_use or any(
        isinstance(selection, Mapping) and selection.get("equipment_use") is not None
        for selection in selections
    ):
        required.append(EQUIPMENT_USE_INPUT_CONTRACT)
    geometry = inputs.get("geometry")
    if isinstance(geometry, Mapping):
        sources = geometry.get("sources")
        if any(
            isinstance(source, Mapping) and source.get("calibration") is not None
            for source in (sources if isinstance(sources, list) else [])
        ):
            required.append(CALIBRATION_INPUT_CONTRACT)
    if "country_rule_inputs" in inputs:
        required.append(ENGINEERING_V10_INPUT_CONTRACT)
    if "grid_connection" in inputs:
        required.append(GRID_CONNECTION_INPUT_CONTRACT)
    if "pv_plant_string_plan" in inputs:
        required.append(PLANT_PV_INPUT_CONTRACT)
    if isinstance(installation, Mapping) and "pv_string_links" in installation:
        required.append(INPUT_CONTRACT)
    if isinstance(installation, Mapping):
        if "protection_assessments" in installation:
            required.append(PROTECTION_EVIDENCE_INPUT_CONTRACT)
        if "materials" in installation:
            required.append(MATERIALS_INPUT_CONTRACT)
            materials = installation.get("materials")
            if any(
                isinstance(row, Mapping)
                and row.get("mounting_quantity_basis") is not None
                for row in (materials if isinstance(materials, list) else [])
            ):
                required.append(MOUNTING_QUANTITIES_INPUT_CONTRACT)
        circuits, runs = installation.get("circuits"), installation.get("cable_runs")
        if any(
            isinstance(row, Mapping) and row.get("manufacturer_comparison") is not None
            for row in (runs if isinstance(runs, list) else [])
        ):
            required.append(CONDUCTOR_MANUFACTURER_INPUT_CONTRACT)
        instances = installation.get("instances")
        if any(
            isinstance(row, Mapping) and "reference_current_installation" in row
            for row in (runs if isinstance(runs, list) else [])
        ):
            required.append(REFERENCE_CURRENT_INPUT_CONTRACT)
        terminal = any(
            isinstance(row, Mapping) and "communication_use" in row
            for row in (circuits if isinstance(circuits, list) else [])
        ) or any(
            isinstance(port, Mapping) and "terminal_binding" in port
            for instance in (instances if isinstance(instances, list) else [])
            if isinstance(instance, Mapping) and isinstance(instance.get("ports"), list)
            for port in instance["ports"]
        )
        if terminal:
            required.append(TERMINAL_INPUT_CONTRACT)
        electrical = any(
            isinstance(row, Mapping) and "operating_conditions" in row
            for row in (circuits if isinstance(circuits, list) else [])
        ) or any(
            isinstance(row, Mapping)
            and (
                "core_roles" in row
                or isinstance(row.get("conductor"), Mapping)
                and "cable_reference" in row["conductor"]
            )
            for row in (runs if isinstance(runs, list) else [])
        )
        if electrical:
            required.append(ELECTRICAL_INPUT_CONTRACT)
    if "direct_beam_visibility" in inputs:
        required.append(DIRECT_BEAM_INPUT_CONTRACT)
    if "geometric_pv_preparation" in inputs:
        required.append(GEOMETRIC_PV_INPUT_CONTRACT)
        geometric = inputs["geometric_pv_preparation"]
        if (
            isinstance(geometric, Mapping)
            and geometric.get("model") == "opaque_perez_series_iv_forward_reference_v1"
        ):
            required.append(ENGINEERING_V10_INPUT_CONTRACT)
    return tuple(required)


def require_input_contract(
    existing: Mapping[str, object] | None,
    incoming: Mapping[str, object],
    input_contract: str | None,
) -> None:
    from .errors import InvalidInput, ProjectInputContractRequired

    if input_contract is not None and input_contract not in SUPPORTED_INPUT_CONTRACTS:
        raise InvalidInput("unsupported project input contract")
    required = set(required_contracts(incoming))
    if existing is not None:
        required.update(required_contracts(existing))
    generation = (
        SUPPORTED_INPUT_CONTRACTS.index(input_contract) + 1
        if input_contract is not None
        else 0
    )
    covered = SUPPORTED_INPUT_CONTRACTS[:generation]
    if not required.issubset(covered):
        raise ProjectInputContractRequired(
            "this complete-input write requires an updated editor"
        )


def create_command(
    title: str, inputs: Object, *, input_contract: str | None = None
) -> Object:
    value: Object = {"title": title, "inputs": inputs}
    if input_contract is not None:
        value["input_contract"] = input_contract
    return value


def revise_command(
    expected_revision: int, inputs: Object, *, input_contract: str | None = None
) -> Object:
    value: Object = {"expected_revision": expected_revision, "inputs": inputs}
    if input_contract is not None:
        value["input_contract"] = input_contract
    return value
