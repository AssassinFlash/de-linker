"""Project-declared installation materials and their remaining checks."""

from __future__ import annotations

from typing import cast

from .canonical import Json, Object
from .geometry import validate_geometry
from .geometry_documents import GeometryDocument
from .installation_inputs import InstallationInputs, InstallationMaterial
from .installation_terminals import _source_is_current


def _comparison(
    plan: InstallationInputs, item: InstallationMaterial, basis: Object
) -> Object | None:
    binding = item.comparison
    if binding is None:
        return None
    result: Object = {"status": "unavailable", "qualified": False, "fact": None}
    circuit = next((c for c in plan.circuits if c.id == item.circuit_id), None)
    instance = next((d for d in plan.instances if d.id == binding.instance_id), None)
    if (
        circuit is None
        or instance is None
        or binding.instance_id
        not in (circuit.start.instance_id, circuit.end.instance_id)
    ):
        result["status"] = "circuit_or_instance_unavailable"
        return result
    if not binding.conditions_confirmed:
        result["status"] = "conditions_not_confirmed"
        return result
    if binding.circuit_context.model_dump(mode="json") != {
        "id": circuit.id,
        "kind": circuit.kind,
        "start": circuit.start.model_dump(mode="json"),
        "end": circuit.end.model_dump(mode="json"),
    }:
        result["status"] = "conditions_changed"
        return result
    if (instance.product_id, instance.product_revision) != (
        binding.product_id,
        binding.product_revision,
    ):
        result["status"] = "instance_mismatch"
        return result
    product = next(
        (
            p
            for p in cast(list[Object], basis.get("products", []))
            if p.get("canonical_product_id") == binding.product_id
        ),
        None,
    )
    if product is None or product.get("product_revision") != binding.product_revision:
        result["status"] = "product_unavailable"
        return result
    facts = product.get("installation_facts")
    items = (
        facts.get("items")
        if isinstance(facts, dict) and facts.get("status") == "documented"
        else None
    )
    matches = (
        [f for f in items if isinstance(f, dict) and f.get("id") == binding.fact_id]
        if isinstance(items, list)
        else []
    )
    if len(matches) != 1:
        result["status"] = "fact_unavailable"
        return result
    fact = matches[0]
    source, spec = fact.get("source"), fact.get("specification")
    if (
        not isinstance(source, dict)
        or not isinstance(spec, dict)
        or source.get("document_id") != binding.document_id
        or source.get("document_revision") != binding.document_revision
        or not _source_is_current(fact, product, basis)
    ):
        result["status"] = "document_unavailable"
        return result
    # No inferred handling of conditional/model-specific requirements.
    if fact.get("conditions") != []:
        result["status"] = "conditions_not_assessed"
        return result
    if (
        item.kind == "earthing"
        and circuit.kind == "protective_earth"
        and fact.get("basis") == "manufacturer_recommended_pe_conductor"
        and spec.get("terminal_domain") == "pe"
    ):
        limits = spec.get("recommended_conductor_mm2")
        if (
            not isinstance(limits, dict)
            or binding.cross_section_mm2 is None
            or type(limits.get("low")) not in (int, float)
            or type(limits.get("high")) not in (int, float)
        ):
            return result
        result.update(
            status="within_recommendation"
            if cast(float, limits["low"])
            <= binding.cross_section_mm2
            <= cast(float, limits["high"])
            else "outside_recommendation",
            fact=fact,
        )
    elif (
        item.kind == "protection"
        and circuit.kind == "ac"
        and fact.get("basis") == "manufacturer_minimum_rating"
        and spec.get("terminal_domain") == "ac"
    ):
        current, voltage = spec.get("minimum_current_a"), spec.get("minimum_voltage_v")
        if (
            binding.rated_current_a is None
            or binding.rated_voltage_v is None
            or type(current) not in (int, float)
            or type(voltage) not in (int, float)
        ):
            return result
        result.update(
            status="meets_minimum_values"
            if binding.rated_current_a >= cast(float, current)
            and binding.rated_voltage_v >= cast(float, voltage)
            else "below_minimum_values",
            fact=fact,
        )
    else:
        result["status"] = "scope_mismatch"
    return result


def _mounting_quantity(
    item: InstallationMaterial, geometry: GeometryDocument
) -> Object:
    rule = item.mounting_quantity_basis
    assert rule is not None
    result: Object = {"status": "layout_changed", "quantity": None}
    array = next((a for a in geometry.arrays if a.id == rule.array.id), None)
    module = next((m for m in geometry.module_specs if m.id == rule.module.id), None)
    roof = next((r for r in geometry.roofs if r.id == rule.roof.id), None)
    if array != rule.array or module != rule.module or roof != rule.roof:
        return result
    excluded = set(array.excluded_slots)
    modules = segments = 0
    for row in range(array.rows):
        previous = False
        for column in range(array.columns):
            present = f"{row}:{column}" not in excluded
            if present:
                modules += 1
                if not previous:
                    segments += 1
            previous = present
    if modules == 0:
        return {"status": "no_modules", "quantity": None}
    adjacency = modules - segments
    return {
        "status": "calculated",
        "quantity": modules * rule.per_module
        + segments * rule.per_segment
        + adjacency * rule.per_adjacency,
        "modules": modules,
        "segments": segments,
        "adjacencies": adjacency,
        "per_module": rule.per_module,
        "per_segment": rule.per_segment,
        "per_adjacency": rule.per_adjacency,
    }


def material_review(
    plan: InstallationInputs, basis: Object, geometry: GeometryDocument
) -> Object:
    if any(item.mounting_quantity_basis is not None for item in plan.materials):
        validate_geometry(geometry)
    circuits = {c.id for c in plan.circuits}
    rows: list[Json] = []
    declarations = cast(list[Object], plan.project_document().get("materials", []))
    for item, row in zip(plan.materials, declarations, strict=True):
        rows.append(
            {
                **row,
                "circuit_status": "not_linked"
                if item.circuit_id is None
                else "linked"
                if item.circuit_id in circuits
                else "circuit_unavailable",
                # User-entered specifications are not cited Woo facts.
                "verification": "not_assessed",
                **(
                    {"mounting_quantity_result": _mounting_quantity(item, geometry)}
                    if item.mounting_quantity_basis
                    else {}
                ),
                **(
                    {"comparison_result": _comparison(plan, item, basis)}
                    if item.comparison
                    else {}
                ),
            }
        )
    return {
        "method": "project_declared_installation_materials_v1",
        "qualified": False,
        "complete_bos": False,
        "rows": rows,
    }
