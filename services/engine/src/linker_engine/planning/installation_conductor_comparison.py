"""Compare a recorded conductor with an explicitly selected Woo instruction."""

from __future__ import annotations

from typing import cast

from .canonical import Object
from .installation_inputs import CableRun, InstallationInputs
from .installation_terminals import _source_is_current


def has_conductor_comparison(plan: InstallationInputs) -> bool:
    return any(run.manufacturer_comparison is not None for run in plan.cable_runs)


def conductor_comparison(
    plan: InstallationInputs, run: CableRun, basis: Object
) -> Object:
    binding = run.manufacturer_comparison
    assert binding is not None
    result: Object = {"status": "unavailable", "qualified": False, "fact": None}
    circuit = next((item for item in plan.circuits if item.id == run.circuit_id), None)
    instance = next(
        (item for item in plan.instances if item.id == binding.instance_id), None
    )
    if (
        circuit is None
        or instance is None
        or binding.instance_id
        not in (
            circuit.start.instance_id,
            circuit.end.instance_id,
        )
    ):
        result["status"] = "circuit_or_instance_unavailable"
        return result
    if not binding.conditions_confirmed:
        result["status"] = "conditions_not_confirmed"
        return result
    if run.conductor is None or binding.confirmation_context.model_dump(
        mode="json"
    ) != {
        "circuit": {
            key: getattr(circuit, key).model_dump(mode="json")
            if key in ("start", "end")
            else getattr(circuit, key)
            for key in ("id", "kind", "start", "end")
        },
        "construction": run.construction,
        "conductor": run.conductor.model_dump(mode="json"),
        "core_roles": run.core_roles,
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
    if fact.get("conditions") != []:
        result["status"] = "conditions_not_assessed"
        return result
    expected = {
        "ac": ("manufacturer_recommended_ac_conductor", "ac"),
        "protective_earth": ("manufacturer_recommended_pe_conductor", "pe"),
        "battery_dc": ("manufacturer_model_specific_conductor", "battery_dc"),
    }.get(circuit.kind)
    if (
        expected is None
        or (fact.get("basis"), spec.get("terminal_domain")) != expected
        or (
            circuit.kind == "battery_dc"
            and fact.get("id") != "battery-cluster-conductor"
        )
    ):
        result["status"] = "scope_mismatch"
        return result
    limits = spec.get("recommended_conductor_mm2")
    if (
        not isinstance(limits, dict)
        or type(limits.get("low")) not in (int, float)
        or type(limits.get("high")) not in (int, float)
    ):
        return result
    section = run.conductor.cross_section_mm2
    result.update(
        status="within_recommendation"
        if cast(float, limits["low"]) <= section <= cast(float, limits["high"])
        else "outside_recommendation",
        fact=fact,
    )
    return result
