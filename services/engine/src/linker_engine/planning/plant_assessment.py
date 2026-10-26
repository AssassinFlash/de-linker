"""Qualify each Woo-bound system, then assess the declared plant relationships."""

from __future__ import annotations

import re
from collections.abc import Callable
from decimal import Decimal
from typing import Any, cast

from .canonical import Object, decode_object, encode
from .equipment_assessment import assess_equipment, selection_products
from .equipment_evidence import EquipmentEvidence
from .equipment_plant import EquipmentPlant
from .errors import InvalidInput, ProductEvidenceChanged


def plant_products(plant: EquipmentPlant, basis: Object) -> dict[int, dict[str, Any]]:
    products: dict[int, dict[str, Any]] = {}
    for unit in plant.units:
        products = selection_products(unit.selection, basis)
    for group in plant.parallel_groups:
        if group.controller_product_id is not None:
            row = products.get(group.controller_product_id)
            if row is None or row["product_revision"] != group.controller_revision:
                raise ProductEvidenceChanged("selected plant controller data changed")
    return products


def assess_plant(
    inputs: Object, basis: Object, checkpoint: Callable[[], None] | None = None
) -> Object:
    plant = EquipmentPlant.from_inputs(inputs)
    products = plant_products(plant, basis)
    evidence = EquipmentEvidence(basis)
    evidence.require_basis(basis)
    units = {u.id: u for u in plant.units}
    checks: list[dict[str, Any]] = []
    systems: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []
    selected: dict[int, dict[str, Any]] = {}

    def add(identifier: str, status: str, reason: str, **details: Any) -> None:
        checks.append(
            {
                "id": identifier,
                "status": status,
                "reason": reason,
                "facts": [],
                "actual": None,
                "required": None,
                **details,
            }
        )

    for unit in plant.units:
        if checkpoint is not None:
            checkpoint()
        assessment = assess_equipment(
            {
                "brief": inputs.get("brief"),
                "equipment_selection": unit.selection.model_dump(mode="json"),
            },
            basis,
            evidence=evidence,
        )
        systems.append(
            {
                "id": unit.id,
                "name": unit.name,
                "selection": unit.selection.model_dump(mode="json"),
                "assessment": assessment,
            }
        )
        for check in cast(list[dict[str, Any]], assessment["checks"]):
            checks.append(
                {
                    **check,
                    "id": f"unit:{unit.id}:{check['id']}",
                    "unit_id": unit.id,
                    "unit_name": unit.name,
                    "semantic_id": check["id"],
                }
            )
        for key, expected in (
            ("grid_phase", plant.requirements.grid_phase),
            ("operating_mode", plant.requirements.operating_mode),
        ):
            actual = getattr(unit.selection, key)
            add(
                f"unit:{unit.id}:plant_{key}",
                "unresolved"
                if actual is None
                else "satisfied"
                if actual == expected
                else "violated",
                "unit_must_match_plant_connection",
                actual=actual,
                required=expected,
                semantic_id="plant_" + key,
                unit_name=unit.name,
            )
        for row in cast(list[dict[str, Any]], assessment["selected_products"]):
            selected[row["product_id"]] = row
        for line in cast(
            list[dict[str, Any]], assessment["provisional_bill_of_materials"]
        ):
            lines.append({**line, "unit_ids": [unit.id]})
        requirements.extend(
            {**r, "unit_id": unit.id, "unit_name": unit.name}
            for r in cast(list[dict[str, Any]], assessment["installation_requirements"])
        )

    for group in plant.parallel_groups:
        if checkpoint is not None:
            checkpoint()
        declarations = []
        group_name = ", ".join(units[uid].name for uid in group.unit_ids)
        covered: set[str] = set()
        for uid in group.unit_ids:
            selection = units[uid].selection
            raw = products[selection.inverter_product_id]
            matched = [
                r
                for r in evidence.contract.requirements(
                    raw["model"],
                    "parallel_controller",
                    inverter_id=selection.inverter_product_id,
                )
                if r.phase in (None, plant.requirements.grid_phase)
            ]
            declarations.extend(matched)
            if matched:
                covered.add(uid)
            bounds = [r.max_units for r in matched if r.max_units is not None]
            add(
                f"group:{group.id}:{uid}:parallel_count",
                "unresolved"
                if not bounds
                else "satisfied"
                if len(group.unit_ids) <= min(bounds)
                else "violated",
                "woo_parallel_count_requires_mode_scope",
                actual=len(group.unit_ids),
                required=min(bounds) if bounds else None,
                semantic_id="plant_parallel_count",
                group_name=group_name,
                documents=[
                    {"url": d.url, "page": d.page} for r in matched for d in r.documents
                ],
            )
        # Current Woo declarations have no typed operating-mode or mixed-model
        # scope. Neither a numerical bound nor matching controller text grants it.
        add(
            f"group:{group.id}:manufacturer_topology",
            "unresolved",
            "mode_model_firmware_and_battery_association_require_scoped_evidence",
            semantic_id="plant_joint_operation",
            group_name=group_name,
        )
        resolved: set[int] = set()
        required_quantities: set[int] = set()
        for declaration in declarations:
            requirements.append(
                {
                    "kind": "parallel_controller",
                    "group_id": group.id,
                    "group_name": group_name,
                    "included": declaration.included,
                    "conditions": [
                        {"en": t.en, "de": t.de} for t in declaration.conditions
                    ],
                    "documents": [
                        {"url": d.url, "page": d.page} for d in declaration.documents
                    ],
                }
            )
            for accessory in declaration.accessories:
                matches = [
                    p
                    for p in products.values()
                    if p["canonical_product_id"] == accessory.product_id
                    if accessory.product_id is not None
                ]
                if accessory.product_id is None:
                    matches = [
                        p
                        for p in products.values()
                        if re.search(accessory.model, p["model"])
                    ]
                if len(matches) == 1 and accessory.per == "system":
                    resolved.add(matches[0]["canonical_product_id"])
                    required_quantities.add(accessory.quantity)
        controller = group.controller_product_id
        known = (
            len(covered) == len(group.unit_ids)
            and len(resolved) == 1
            and required_quantities == {1}
        )
        add(
            f"group:{group.id}:controller",
            "unresolved"
            if not known or controller is None
            else "satisfied"
            if controller in resolved
            else "violated",
            "one_shared_controller_per_declared_group",
            actual=controller,
            required=next(iter(resolved)) if known else None,
            semantic_id="plant_controller",
            group_name=group_name,
            value_kind="product_identity",
            actual_label=(
                " ".join(
                    str(products[controller].get(k, "")) for k in ("brand", "model")
                )
                if controller is not None
                else None
            ),
            required_label=(
                " ".join(
                    str(products[next(iter(resolved))].get(k, ""))
                    for k in ("brand", "model")
                )
                if known
                else None
            ),
        )
        if controller is not None:
            selected[controller] = evidence.compiled(controller)
            product = products[controller]
            lines.append(
                {
                    "product_id": controller,
                    "quantity": 1,
                    "basis": "selected_parallel_controller",
                    "model": product["model"],
                    "brand": product["brand"],
                    "sku": product.get("sku"),
                    "group_ids": [group.id],
                }
            )

    for key in ("pv_dc_kw", "required_usable_kwh", "required_discharge_ac_kw"):
        requested = getattr(plant.requirements, key)
        allocations = [getattr(u.selection, key) for u in plant.units]
        total = (
            sum((Decimal(str(v)) for v in allocations), Decimal(0))
            if all(v is not None for v in allocations)
            else None
        )
        enough = (
            (
                total == Decimal(str(requested))
                if key == "pv_dc_kw"
                else total is not None and total >= Decimal(str(requested))
            )
            if requested is not None
            else None
        )
        if total is not None and total > 2**53 - 1:
            raise InvalidInput("plant demand allocation exceeds interoperable numbers")
        add(
            "plant:allocation:" + key,
            "unresolved"
            if total is None or requested is None
            else "satisfied"
            if enough
            else "violated",
            "declared_unit_demand_allocation_not_available_plant_output",
            actual=float(total) if total is not None else None,
            required=requested,
            semantic_id={
                "pv_dc_kw": "plant_pv_allocation",
                "required_usable_kwh": "plant_energy_allocation",
                "required_discharge_ac_kw": "plant_discharge_allocation",
            }[key],
            unit={
                "pv_dc_kw": "kWp",
                "required_usable_kwh": "kWh",
                "required_discharge_ac_kw": "kW",
            }[key],
        )

    # Keep hardware supply counts separate from the performance of a shared
    # connection. A sum of devices does not establish its dispatch/transfer.
    for key in ("required_usable_kwh", "required_discharge_ac_kw"):
        requested = getattr(plant.requirements, key)
        add(
            "plant:" + key,
            "satisfied" if requested == 0 else "unresolved",
            "joint_delivery_requires_allocation_and_connection_assessment",
            required=requested,
            semantic_id="plant_joint_energy"
            if key == "required_usable_kwh"
            else "plant_joint_discharge",
            unit="kWh" if key == "required_usable_kwh" else "kW",
        )
    merged: dict[int, dict[str, Any]] = {}
    for line in lines:
        key = line["product_id"]
        if key not in merged:
            merged[key] = {
                **line,
                "unit_ids": list(line.get("unit_ids", [])),
                "group_ids": list(line.get("group_ids", [])),
            }
        else:
            row = merged[key]
            if row["basis"] != line["basis"]:
                row["basis"] = "plant_allocations"
            row["quantity"] = (
                row["quantity"] + line["quantity"]
                if row["quantity"] is not None and line["quantity"] is not None
                else None
            )
            row["unit_ids"].extend(line.get("unit_ids", []))
            row["group_ids"].extend(line.get("group_ids", []))
        quantity = merged[key]["quantity"]
        if quantity is not None and (
            type(quantity) is not int or not 0 < quantity <= 2**53 - 1
        ):
            raise InvalidInput("plant material quantity exceeds interoperable integers")
    statuses = {c["status"] for c in checks}
    status = (
        "violated"
        if "violated" in statuses
        else "unresolved"
        if "unresolved" in statuses
        else "satisfied"
    )
    brief = inputs.get("brief")
    site = brief.get("site") if isinstance(brief, dict) else None
    return decode_object(
        encode(
            cast(
                Object,
                {
                    "model": "woo_multi_converter_plant_v1",
                    "equipment_status": status,
                    "checks": checks,
                    "systems": systems,
                    "manufacturer_pair": None,
                    "installation_requirements": requirements,
                    "selected_products": [selected[k] for k in sorted(selected)],
                    "provisional_bill_of_materials": list(merged.values()),
                    "bill_of_materials_status": "unresolved",
                    "country_assessment": {
                        "status": "unresolved",
                        "country_code": site.get("country_code")
                        if isinstance(site, dict)
                        else None,
                        "reason": "versioned_country_rules_required",
                    },
                    "overall_status": "violated"
                    if status == "violated"
                    else "unresolved",
                    "ranking": "not_performed_before_qualification",
                },
            )
        )
    )
