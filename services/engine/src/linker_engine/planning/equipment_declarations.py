"""Compile authored equipment into run-owned discovery and qualification inputs."""

from __future__ import annotations

from typing import cast

from pydantic import ValidationError

from .canonical import Json, Object, decode_object, encode
from .energy_declarations import normalize_authored_inputs, object_value
from .energy_inputs import storage_only_project
from .equipment_inputs import EquipmentSelection, EquipmentUse
from .equipment_plant import EquipmentPlant, ParallelGroup, PlantUnit
from .equipment_requirements import EquipmentRequirements
from .errors import InvalidInput
from .plant_search_plan import PlantSearchPlan, SearchGroup
from .product_sources import ProductSources


def _normalize_unit(inputs: Object) -> None:
    legacy = inputs.pop("equipment_requirements", None)
    setup = inputs.get("equipment_setup")
    if "equipment_setup" not in inputs:
        selection = inputs.get("equipment_selection")
        if isinstance(selection, dict):
            setup = {
                key: value
                for key, value in selection.items()
                if key != "product_revisions"
            }
        elif isinstance(legacy, dict):
            # These are the released editor's unanswered hardware fields, not
            # a chosen product, module count or sizing assumption.
            setup = {
                "schema_version": 1,
                "inverter_product_id": None,
                "battery_product_id": None,
                "modules_per_stack": None,
                "parallel_stacks": None,
                "accessory_product_ids": [],
                **{
                    key: legacy[key]
                    for key in EquipmentRequirements.model_fields
                    if key != "application" and key in legacy
                },
            }
        if isinstance(setup, dict):
            inputs["equipment_setup"] = setup
    if (
        isinstance(setup, dict)
        and "application" not in setup
        and isinstance(legacy, dict)
        and "application" in legacy
    ):
        setup["application"] = legacy["application"]


def normalize_discovery_inputs(inputs: Object) -> Object:
    result = normalize_authored_inputs(inputs)
    result.pop("equipment_plant_requirements", None)
    plant = result.get("equipment_plant_setup")
    if isinstance(plant, dict):
        result.pop("equipment_requirements", None)
        units = plant.get("units")
        if isinstance(units, list):
            for unit in units:
                declarations = unit.get("inputs") if isinstance(unit, dict) else None
                if isinstance(declarations, dict):
                    _normalize_unit(declarations)
    else:
        _normalize_unit(result)
    return result


def _requirements(
    setup: Object,
    *,
    path: str,
    connection: EquipmentRequirements | None = None,
    storage_only: bool,
) -> EquipmentRequirements:
    values = {key: setup.get(key) for key in EquipmentRequirements.model_fields}
    if connection is not None:
        values.update(
            grid_phase=connection.grid_phase, operating_mode=connection.operating_mode
        )
    if storage_only:
        values["pv_dc_kw"] = 0
    try:
        return EquipmentRequirements.model_validate(values)
    except ValidationError as error:
        fields = tuple(
            path + "." + ".".join(str(part) for part in item["loc"])
            for item in error.errors()
        )
        raise InvalidInput(
            "complete the declared equipment demand", fields=fields
        ) from error


def compile_discovery_inputs(authored: Object) -> Object:
    inputs = decode_object(encode(authored))
    storage_only = storage_only_project(inputs)
    raw = inputs.get("equipment_plant_setup")
    if not isinstance(raw, dict):
        setup = object_value(
            inputs.get("equipment_setup"), "equipment demand declarations"
        )
        inputs["equipment_requirements"] = _requirements(
            setup,
            path="equipment_setup",
            storage_only=storage_only,
        ).model_dump(mode="json")
        return inputs
    common = _requirements(
        object_value(raw.get("requirements"), "plant connection demand"),
        path="equipment_plant_setup.requirements",
        storage_only=storage_only,
    )
    raw["requirements"] = common.model_dump(mode="json")
    units, groups = raw.get("units"), raw.get("parallel_groups")
    if not isinstance(units, list) or not isinstance(groups, list):
        raise InvalidInput("declare the named plant systems and their groups")
    requests: list[Json] = []
    for index, value in enumerate(units):
        unit = object_value(value, "plant system")
        declarations = object_value(unit.get("inputs"), "plant system declarations")
        setup = object_value(
            declarations.get("equipment_setup"), "system demand declarations"
        )
        demand = _requirements(
            setup,
            path=f"equipment_plant_setup.units[{index}].inputs.equipment_setup",
            connection=common,
            storage_only=storage_only,
        )
        requests.append(
            {
                "id": unit.get("id"),
                "name": unit.get("name"),
                "requirements": demand.model_dump(mode="json"),
            }
        )
    search_groups: list[Json] = []
    for value in groups:
        group = object_value(value, "plant search group")
        search_groups.append(
            cast(
                Object,
                {
                    key: value
                    for key, value in group.items()
                    if key in SearchGroup.model_fields
                },
            )
        )
    plan = PlantSearchPlan.read(
        {
            "schema_version": raw.get("schema_version"),
            "requirements": common.model_dump(mode="json"),
            "units": requests,
            "parallel_groups": search_groups,
        }
    )
    inputs["equipment_plant_requirements"] = plan.model_dump(mode="json")
    return inputs


def compile_equipment_inputs(inputs: Object, source: ProductSources | None) -> Object:
    if not {"equipment_setup", "equipment_plant_setup"}.intersection(inputs):
        return {**inputs}
    setup = inputs.get("equipment_setup")
    if "equipment_plant_setup" not in inputs and isinstance(setup, dict):
        use = (
            EquipmentUse.read(setup["equipment_use"])
            if setup.get("equipment_use") is not None
            else None
        )
        if (
            all(
                setup.get(field) is None
                for field in (
                    "inverter_product_id",
                    "battery_product_id",
                    "modules_per_stack",
                    "parallel_stacks",
                )
            )
            and setup.get("accessory_product_ids") in (None, [])
            and (use is None or use.inverter == use.battery == "new")
        ):
            return {
                key: value
                for key, value in inputs.items()
                if key != "equipment_selection"
            }
    if source is None:
        raise InvalidInput("current Woo source required for hardware declarations")
    basis = source.equipment_basis()
    raw_products = basis.get("products")
    if not isinstance(raw_products, list):
        raise InvalidInput("Woo products required")
    products = {
        str(row["canonical_product_id"]): row
        for row in raw_products
        if isinstance(row, dict)
    }

    def selection(setup: Object, path: str) -> EquipmentSelection:
        chosen = [
            (field, setup.get(field))
            for field in ("inverter_product_id", "battery_product_id")
        ]
        accessories = setup.get("accessory_product_ids")
        if not isinstance(accessories, list):
            raise InvalidInput(
                "explicit equipment accessories required",
                fields=(path + ".accessory_product_ids",),
            )
        chosen.extend(
            (f"accessory_product_ids[{index}]", pid)
            for index, pid in enumerate(accessories)
        )
        revisions: Object = {}
        for field, pid in chosen:
            if pid is None:
                continue
            product = products.get(str(pid))
            if not isinstance(product, dict):
                raise InvalidInput(
                    "selected equipment is absent from the current Woo source",
                    fields=(path + "." + field,),
                )
            revisions[str(pid)] = product.get("product_revision")
        try:
            return EquipmentSelection.model_validate(
                {
                    **{
                        k: v
                        for k, v in setup.items()
                        if k in EquipmentSelection.model_fields
                        and k != "product_revisions"
                    },
                    "product_revisions": revisions,
                }
            )
        except ValidationError as error:
            fields = tuple(
                path
                + (
                    "." + ".".join(str(part) for part in item["loc"])
                    if item["loc"]
                    else ""
                )
                for item in error.errors()
            )
            raise InvalidInput(
                "complete the declared hardware selection", fields=fields
            ) from error

    result = {**inputs}
    if isinstance(inputs.get("equipment_plant_setup"), dict):
        setup = cast(Object, inputs["equipment_plant_setup"])
        requirements = object_value(setup.get("requirements"), "plant requirements")
        raw_units, raw_groups = setup.get("units"), setup.get("parallel_groups")
        if not isinstance(raw_units, list) or not isinstance(raw_groups, list):
            raise InvalidInput("plant units and parallel groups required")
        units = []
        for index, raw in enumerate(raw_units):
            unit = object_value(raw, "plant unit")
            unit_inputs = object_value(unit.get("inputs"), "plant unit declarations")
            declared = object_value(
                unit_inputs.get(
                    "equipment_setup", unit_inputs.get("equipment_selection")
                ),
                "unit hardware",
            )
            chosen = selection(
                {
                    **declared,
                    "grid_phase": requirements.get("grid_phase"),
                    "operating_mode": requirements.get("operating_mode"),
                },
                f"equipment_plant_setup.units[{index}].inputs."
                + (
                    "equipment_setup"
                    if "equipment_setup" in unit_inputs
                    else "equipment_selection"
                ),
            )
            units.append(
                PlantUnit.read(
                    {
                        "id": unit.get("id"),
                        "name": unit.get("name"),
                        "selection": chosen.model_dump(mode="json"),
                    }
                )
            )
        groups = []
        for raw in raw_groups:
            group = object_value(raw, "parallel group")
            pid = group.get("controller_product_id")
            controller = products.get(str(pid)) if pid is not None else None
            if pid is not None and not isinstance(controller, dict):
                raise InvalidInput("selected controller is absent from Woo")
            groups.append(
                ParallelGroup.read(
                    {
                        **group,
                        "controller_revision": controller.get("product_revision")
                        if isinstance(controller, dict)
                        else None,
                    }
                )
            )
        plant = EquipmentPlant.read(
            {
                "schema_version": 1,
                "requirements": requirements,
                "units": [u.model_dump(mode="json") for u in units],
                "parallel_groups": [g.model_dump(mode="json") for g in groups],
            }
        )
        result["equipment_plant"] = plant.model_dump(mode="json")
    elif isinstance(inputs.get("equipment_setup"), dict):
        result["equipment_selection"] = selection(
            cast(Object, inputs["equipment_setup"]), "equipment_setup"
        ).model_dump(mode="json")
    source.confirm_basis(basis, require_reference=False)
    return result
