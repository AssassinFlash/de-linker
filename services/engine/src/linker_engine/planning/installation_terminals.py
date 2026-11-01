"""Resolve each declared connection end against its pinned Woo terminal fact."""

from __future__ import annotations

from typing import cast

from .canonical import Json, Object
from .installation_inputs import (
    ConnectionPoint,
    DeviceInstance,
    InstallationCircuit,
    InstallationInputs,
)


def has_terminal_feature(plan: InstallationInputs) -> bool:
    return any("communication_use" in c.model_fields_set for c in plan.circuits) or any(
        "terminal_binding" in port.model_fields_set
        for device in plan.instances
        for port in device.ports
    )


def _source_is_current(fact: Object, product: Object, basis: Object) -> bool:
    """A fact is usable only through the selected product's scoped document."""
    source = fact.get("source")
    publication = basis.get("publication")
    if not isinstance(source, dict) or not isinstance(publication, dict):
        return False
    product_id = product.get("canonical_product_id")
    if source.get("product_id") != product_id:
        return False
    scope_products, scope_documents = (
        publication.get("products"),
        publication.get("documents"),
    )
    documents = product.get("documents")
    if not all(
        isinstance(rows, list) for rows in (scope_products, scope_documents, documents)
    ):
        return False
    if {
        "product_id": product_id,
        "product_revision": product.get("product_revision"),
    } not in cast(list[Object], scope_products):
        return False
    dependency = {
        "document_id": source.get("document_id"),
        "document_revision": source.get("document_revision"),
        "product_id": product_id,
    }
    if not any(
        all(document.get(key) == value for key, value in dependency.items())
        for document in cast(list[Object], scope_documents)
    ):
        return False
    for doc in cast(list[Object], documents):
        if (
            doc.get("document_id") == source.get("document_id")
            and doc.get("document_revision") == source.get("document_revision")
            and doc.get("blob_sha256") == source.get("blob_sha256")
            and source.get("url")
            in [doc.get("url"), *cast(list[Json], doc.get("aliases", []))]
            and product_id in cast(list[Json], doc.get("product_ids", []))
        ):
            return True
    return False


def resolve_binding(
    instance: DeviceInstance, port: ConnectionPoint, basis: Object
) -> tuple[str, Object | None]:
    binding = port.terminal_binding
    if binding is None:
        return "not_bound", None
    if (
        binding.instance_id != instance.id
        or binding.product_id != instance.product_id
        or binding.product_revision != instance.product_revision
    ):
        return "instance_mismatch", None
    products = cast(list[Object], basis.get("products", []))
    product = next(
        (p for p in products if p.get("canonical_product_id") == binding.product_id),
        None,
    )
    if product is None:
        # The prepared Woo view does not disclose whether an absent item was
        # withdrawn, unprepared, or removed; none is a usable current fact.
        return "product_unavailable", None
    if product.get("product_revision") != binding.product_revision:
        return "product_revision_changed", None
    facts = product.get("installation_facts")
    if not isinstance(facts, dict) or facts.get("status") != "documented":
        return "fact_unavailable", None
    items = facts.get("items")
    if not isinstance(items, list):
        return "invalid_evidence", None
    matches = [
        f for f in items if isinstance(f, dict) and f.get("id") == binding.fact_id
    ]
    if not matches:
        return "fact_unavailable", None
    if len(matches) != 1:
        return "invalid_evidence", None
    fact = matches[0]
    specification, source = fact.get("specification"), fact.get("source")
    if (
        fact.get("basis") != "manufacturer_terminal_map"
        or not isinstance(specification, dict)
        or not isinstance(specification.get("terminal_domain"), str)
        or not isinstance(specification.get("terminals"), list)
        or not isinstance(source, dict)
    ):
        return "invalid_evidence", None
    if (
        source.get("document_id") != binding.document_id
        or source.get("document_revision") != binding.document_revision
    ):
        return "document_changed", None
    if binding.terminal not in cast(list[Json], specification["terminals"]):
        return "terminal_unavailable", None
    if not _source_is_current(fact, product, basis):
        return "invalid_evidence", None
    return "documented", fact


def _endpoint(
    side: str,
    circuit: InstallationCircuit,
    instance: DeviceInstance,
    port: ConnectionPoint,
    basis: Object,
) -> Object:
    status, fact = resolve_binding(instance, port, basis)
    domain_status, use_status = "not_assessed", "not_assessed"
    if fact is not None:
        specification = cast(Object, fact["specification"])
        expected_domain = {
            "ac": "ac",
            "pv_dc": "pv_dc",
            "battery_dc": "battery_dc",
            "protective_earth": "pe",
            "control": "communication",
        }.get(circuit.kind)
        if expected_domain is not None:
            domain_status = (
                "matches"
                if specification.get("terminal_domain") == expected_domain
                else "mismatch"
            )
        if circuit.kind == "control" and domain_status == "matches":
            documented = specification.get("terminal_use")
            use_status = (
                "not_declared"
                if circuit.communication_use is None
                else "not_documented"
                if documented
                not in ("external_communication", "internal_communication")
                else "matches"
                if documented == circuit.communication_use
                else "mismatch"
            )
    return {
        "side": side,
        "instance_id": instance.id,
        "port_id": port.id,
        "status": status,
        "binding": port.terminal_binding.model_dump(mode="json")
        if port.terminal_binding is not None
        else None,
        "fact": fact,
        "domain_status": domain_status,
        "use_status": use_status,
    }


def terminal_assessment(plan: InstallationInputs, basis: Object) -> Object:
    instances = {item.id: item for item in plan.instances}
    ports = {(item.id, port.id): port for item in plan.instances for port in item.ports}
    rows: list[Json] = []
    for circuit in plan.circuits:
        ends: list[Json] = []
        for side in ("start", "end"):
            endpoint = getattr(circuit, side)
            instance = instances[endpoint.instance_id]
            port = ports[(endpoint.instance_id, endpoint.port_id)]
            ends.append(_endpoint(side, circuit, instance, port, basis))
        rows.append(
            {
                "circuit_id": circuit.id,
                "name": circuit.name,
                "kind": circuit.kind,
                "communication_use": circuit.communication_use,
                "endpoints": ends,
            }
        )
    return {
        "schema_version": 1,
        "scope": "manufacturer_one_end_mapping",
        "qualified": False,
        "circuits": rows,
    }
