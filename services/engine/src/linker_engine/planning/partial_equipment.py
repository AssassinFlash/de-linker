"""Freeze customer-selected Woo items when the saved setup lacks a complete system."""

from typing import cast

from .canonical import Json, Object
from .equipment_condition_inputs import add_setup_devices
from .equipment_evidence import EquipmentEvidence
from .errors import InvalidInput, ProductEvidenceChanged
from .product_sources import ProductSources


def partial_equipment(
    inputs: Object, products: ProductSources
) -> tuple[list[Object], Object] | None:
    if "equipment_setup" not in inputs and "equipment_plant_setup" not in inputs:
        return None
    plant = inputs.get("equipment_plant_setup")
    if isinstance(plant, dict):
        units = [
            cast(Object, unit["inputs"]) for unit in cast(list[Object], plant["units"])
        ]
        groups = cast(list[Object], plant["parallel_groups"])
        requirements = cast(Object, plant["requirements"])
    else:
        units, groups, requirements = [inputs], [], None
    setups = [
        unit.get("equipment_setup", unit.get("equipment_selection")) for unit in units
    ]
    if all(
        isinstance(setup, dict)
        and setup.get("inverter_product_id")
        and (setup if requirements is None else requirements).get("operating_mode")
        in ("grid_connected", "backup")
        for setup in setups
    ):
        return None
    choices: list[tuple[int, str, Json, Object]] = []
    for setup in setups:
        if not isinstance(setup, dict):
            continue
        devices: list[Object] = []
        add_setup_devices(devices, setup, {})
        use = setup.get("equipment_use")
        for device in devices:
            role = str(cast(Object, device["selection_ref"])["role"])
            choices.append(
                (
                    cast(int, device["product_id"]),
                    role,
                    use.get(role) if isinstance(use, dict) else None,
                    setup,
                )
            )
    for group in groups:
        pid = group.get("controller_product_id")
        if type(pid) is int:
            choices.append((pid, "controller", group.get("controller_use"), group))
    if not choices:
        return None

    basis = products.equipment_basis()
    evidence = EquipmentEvidence(basis)
    lines: dict[tuple[int, str], Object] = {}
    for pid, role, use, setup in choices:
        if use not in (None, "new", "retain", "replace"):
            raise InvalidInput("invalid intended equipment use")
        row = evidence.products.get(pid)
        if row is None:
            raise ProductEvidenceChanged("selected product is no longer available")
        revisions = setup.get("product_revisions")
        revision = (
            revisions.get(str(pid))
            if isinstance(revisions, dict)
            else setup.get("controller_revision")
        )
        if revision is not None and revision != row["product_revision"]:
            raise ProductEvidenceChanged("selected product revision changed")
        quantity: int | None = None
        if role in ("inverter", "controller"):
            quantity = 1
        elif role == "battery":
            count, stacks = setup.get("modules_per_stack"), setup.get("parallel_stacks")
            kind = evidence.sales_unit(pid)
            if (
                stacks is None
                and evidence.scalar(pid, "stacks_parallel_max", "count") == 1
            ):
                stacks = 1
            if kind == "battery_module" and count is None:
                minimum = evidence.scalar(pid, "modules_per_stack_min", "count")
                maximum = evidence.scalar(pid, "modules_per_stack_max", "count")
                if (
                    minimum is not None
                    and minimum == maximum
                    and minimum.is_integer()
                    and minimum > 0
                ):
                    count = int(minimum)
            if type(stacks) is int and stacks > 0:
                if kind == "battery_module" and type(count) is int and count > 0:
                    quantity = count * stacks
                elif kind == "battery_system":
                    quantity = stacks
        handling = (
            "customer_equipment_retained"
            if use == "retain"
            else "customer_equipment_pending"
            if quantity is None
            else "woo_product"
        )
        key = pid, handling
        if key in lines and quantity is not None:
            previous = lines[key]["quantity"]
            quantity = previous + quantity if type(previous) is int else None
        if quantity is not None and quantity > 2**53 - 1:
            raise InvalidInput("equipment quantity exceeds supported precision")
        lines[key] = {
            "id": f"customer-equipment:{pid}:{handling}",
            "product_id": pid,
            "brand": row["brand"],
            "model": row["model"],
            "sku": row["sku"],
            "quantity": quantity,
            "unit": "piece",
            "handling": handling,
            "basis": "customer_selected_equipment",
            "source": {
                "product_revision": row["product_revision"],
                "selected_role": role,
            },
        }
    ids = {pid for pid, _ in lines}
    scope = dict(cast(Object, basis["publication"]))
    for field in ("products", "documents"):
        scope[field] = [
            r for r in cast(list[Object], scope[field]) if r["product_id"] in ids
        ]
    return list(lines.values()), {"schema_version": 1, "publication": scope}
