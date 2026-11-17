"""Customer declarations about an existing system, independent of product evidence."""

from typing import Annotated

from pydantic import Field

from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput


class ExistingSystem(Document):
    schema_version: SchemaVersion
    name: Annotated[str, Field(max_length=256)]
    inverter_power_kw: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None
    keep_inverter: bool


def retained_inverter_declared(inputs: Object, *, selection: bool = False) -> bool:
    """The existing system is the first system when promoted to a plant draft."""
    plant_fields = (
        (("equipment_plant", "selection"),)
        if selection
        else (
            ("equipment_plant_setup", "inputs"),
            ("equipment_plant", "selection"),
        )
    )
    for field, input_field in plant_fields:
        plant = inputs.get(field)
        if isinstance(plant, dict):
            units = plant.get("units")
            if (
                not isinstance(units, list)
                or not units
                or not isinstance(units[0], dict)
            ):
                return False
            source = units[0].get(input_field)
            if isinstance(source, dict) and input_field == "inputs":
                source = source.get(
                    "equipment_setup", source.get("equipment_selection")
                )
            break
    else:
        source = (
            inputs.get("equipment_selection")
            if selection
            else inputs.get("equipment_setup", inputs.get("equipment_selection"))
        )
    if not isinstance(source, dict):
        return False
    product = source.get("inverter_product_id")
    use = source.get("equipment_use")
    return (
        type(product) is int
        and product > 0
        and isinstance(use, dict)
        and use.get("inverter") == "retain"
    )


def unverified_retained_inverter(
    inputs: Object, *, selection: bool = False
) -> ExistingSystem | None:
    if "existing_system" not in inputs:
        return None
    declaration = ExistingSystem.read(inputs["existing_system"])
    if declaration.keep_inverter and not retained_inverter_declared(
        inputs, selection=selection
    ):
        return declaration
    return None


def require_retained_inverter(inputs: Object, *, selection: bool = False) -> None:
    if unverified_retained_inverter(inputs, selection=selection) is not None:
        raise InvalidInput(
            "confirm the retained inverter model to check compatibility",
            fields=("existing_system.keep_inverter",),
        )
