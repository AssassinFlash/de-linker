"""Source-bound route quantities; electrical and structural design stay separate."""

from __future__ import annotations

import math
from typing import cast

from .canonical import Json, Object, digest, encode
from .errors import InvalidInput, ProductEvidenceChanged
from .geometry_documents import GeometryDocument
from .installation_electrical import electrical_review
from .installation_inputs import InstallationInputs, RoutePoint
from .installation_terminals import has_terminal_feature, terminal_assessment
from .pv_string_inputs import PvPlantStringPlan, PvStringPlan, plant_instance_statuses

METHOD = "installation_route_takeoff_v1"


def _conductor_status(recorded: list[Object]) -> str:
    """One declared cross-section across every recorded run of the circuit."""
    if not recorded:
        return "not_recorded"
    declared = [cast(Object | None, cable["conductor"]) for cable in recorded]
    # A run without its own specification is a gap; it never inherits its
    # neighbour's cross-section and it is not a contradiction either.
    if any(conductor is None for conductor in declared):
        return "unconfirmed"
    sections = {
        cast(float, conductor["cross_section_mm2"])
        for conductor in cast(list[Object], declared)
    }
    # Distinct actual cable identities may legitimately use different areas.
    # Their per-core suitability is evaluated separately, never by asserting
    # that all physical runs in one circuit are the same cable.
    referenced = all(
        isinstance(conductor.get("cable_reference"), dict)
        for conductor in cast(list[Object], declared)
    )
    return "conflicting" if len(sections) > 1 and not referenced else "declared"


def _quantity_status(recorded: list[Object]) -> str:
    if not recorded:
        return "not_recorded"
    if any(cable["quantity"] is None for cable in recorded):
        return "pending"
    return "confirmed"


def _closure(status: str, recorded: list[Object]) -> Object:
    conductor, quantity = _conductor_status(recorded), _quantity_status(recorded)
    return {
        "conductor": conductor,
        "quantity": quantity,
        # String and circuit identities, a declared cross-section and every
        # measured length are now in one frozen project revision.
        "recorded": status == "linked"
        and conductor == "declared"
        and quantity == "confirmed",
        # Ampacity, voltage drop, protection, earthing and country admission
        # are never implied by a recorded specification.
        "approval": "not_assessed",
    }


def _string_links(
    inputs: Object,
    plan: InstallationInputs,
    cables: list[Json],
    stale_instances: set[str],
) -> Object:
    if inputs.get("pv_plant_string_plan") is not None:
        return _plant_string_links(inputs, plan, cables, stale_instances)
    saved = inputs.get("pv_string_plan")
    strings = PvStringPlan.read(saved) if saved is not None else None
    known = {item.id: item for item in strings.strings} if strings else {}
    bindings = {link.string_id: link for link in plan.pv_string_links}
    circuits = {circuit.id: circuit for circuit in plan.circuits}
    instances = {instance.id: instance for instance in plan.instances}
    identities = [*known, *(key for key in bindings if key not in known)]
    rows: list[Json] = []
    for identifier in identities:
        string, binding = known.get(identifier), bindings.get(identifier)
        circuit = circuits.get(binding.circuit_id) if binding else None
        endpoints: list[Json] = []
        if circuit:
            for side in ("start", "end"):
                endpoint = getattr(circuit, side)
                instance = instances[endpoint.instance_id]
                endpoints.append(
                    {
                        "side": side,
                        "instance_id": instance.id,
                        "port_id": endpoint.port_id,
                        "product_id": instance.product_id,
                        "product_revision": instance.product_revision,
                    }
                )
        status = (
            "stale_string"
            if string is None
            else "unlinked"
            if binding is None
            else "stale_circuit"
            if circuit is None
            else "wrong_circuit_kind"
            if circuit.kind != "pv_dc"
            else "inverter_endpoint_unresolved"
            if strings is None
            or sum(
                endpoint["product_id"] == strings.inverter_product_id
                for endpoint in cast(list[Object], endpoints)
            )
            != 1
            or any(
                endpoint["product_id"] == strings.inverter_product_id
                and endpoint["instance_id"] in stale_instances
                for endpoint in cast(list[Object], endpoints)
            )
            else "linked"
        )
        recorded = [
            cable
            for cable in cast(list[Object], cables)
            if circuit is not None and cable["circuit_id"] == circuit.id
        ]
        closure = _closure(status, recorded)
        rows.append(
            {
                "string_id": identifier,
                "mppt": string.mppt if string else None,
                "input": string.input if string else None,
                "circuit_id": binding.circuit_id if binding else None,
                "status": status,
                "endpoints": endpoints,
                # These are the supplied physical runs, not an inferred pair.
                "cable_runs": cast(Json, recorded),
                # Identity, declared conductor and every measured length in one
                # place; separate from the reasons that guard the length itself.
                "closure": closure,
                "reasons": ["cable_runs_missing"] if circuit and not recorded else [],
            }
        )
    return {
        "schema_version": 1,
        "scope": "declared_project_identity_only",
        "pv_string_plan_sha256": digest(encode(saved)) if saved is not None else None,
        "plan_status": "missing"
        if strings is None
        else "available"
        if known
        else "empty",
        "rows": rows,
        "qualified": False,
    }


def _plant_string_links(
    inputs: Object,
    plan: InstallationInputs,
    cables: list[Json],
    stale_instances: set[str],
) -> Object:
    wiring = PvPlantStringPlan.read(inputs.get("pv_plant_string_plan"))
    statuses = plant_instance_statuses(inputs, wiring)
    known = {
        string.id: (unit, string)
        for unit in wiring.units
        for string in unit.plan.strings
    }
    bindings = {link.string_id: link for link in plan.pv_string_links}
    circuits = {circuit.id: circuit for circuit in plan.circuits}
    instances = {instance.id: instance for instance in plan.instances}
    rows: list[Json] = []
    for identifier in [*known, *(key for key in bindings if key not in known)]:
        pair = known.get(identifier)
        unit, string = pair if pair else (None, None)
        binding = bindings.get(identifier)
        circuit = circuits.get(binding.circuit_id) if binding else None
        endpoints: list[Json] = []
        if circuit:
            for side in ("start", "end"):
                endpoint = getattr(circuit, side)
                instance = instances[endpoint.instance_id]
                endpoints.append(
                    {
                        "side": side,
                        "instance_id": instance.id,
                        "port_id": endpoint.port_id,
                        "product_id": instance.product_id,
                        "product_revision": instance.product_revision,
                    }
                )
        instance_status = statuses[unit.unit_id] if unit else "not_recorded"
        status = (
            "stale_string"
            if string is None
            else "unlinked"
            if binding is None
            else "stale_circuit"
            if circuit is None
            else "wrong_circuit_kind"
            if circuit.kind != "pv_dc"
            else "inverter_endpoint_unresolved"
            if instance_status != "declared"
            or unit is None
            or unit.inverter_instance_id in stale_instances
            or sum(
                endpoint["instance_id"] == unit.inverter_instance_id
                for endpoint in cast(list[Object], endpoints)
            )
            != 1
            else "linked"
        )
        recorded = [
            cable
            for cable in cast(list[Object], cables)
            if circuit is not None and cable["circuit_id"] == circuit.id
        ]
        rows.append(
            {
                "string_id": identifier,
                "unit_id": unit.unit_id if unit else None,
                "inverter_instance_id": unit.inverter_instance_id if unit else None,
                "instance_status": instance_status,
                "mppt": string.mppt if string else None,
                "input": string.input if string else None,
                "circuit_id": binding.circuit_id if binding else None,
                "status": status,
                "endpoints": endpoints,
                "cable_runs": cast(Json, recorded),
                "closure": _closure(status, recorded),
                "reasons": ["cable_runs_missing"] if circuit and not recorded else [],
            }
        )
    return {
        "schema_version": 2,
        "scope": "declared_project_identity_only",
        "pv_plant_string_plan_sha256": digest(encode(inputs["pv_plant_string_plan"])),
        "plan_status": "available" if known else "empty",
        "rows": rows,
        "qualified": False,
    }


def product_basis(
    plan: InstallationInputs, basis: Object, *, allow_stale: bool = False
) -> Object:
    ids = {d.product_id for d in plan.instances if d.product_id is not None}
    cable_ids = {
        run.conductor.cable_reference.product_id
        for run in plan.cable_runs
        if run.conductor is not None and run.conductor.cable_reference is not None
    }
    rows = {p["canonical_product_id"]: p for p in cast(list[Object], basis["products"])}
    for item in plan.instances:
        if (
            not allow_stale
            and item.product_id is not None
            and rows.get(item.product_id, {}).get("product_revision")
            != item.product_revision
        ):
            raise ProductEvidenceChanged("installation device facts changed")
    scope = dict(cast(Object, basis["publication"]))
    scope["products"] = [
        p
        for p in cast(list[Object], scope["products"])
        if p["product_id"] in ids | cable_ids
    ]
    scope["documents"] = [
        d
        for d in cast(list[Object], scope["documents"])
        if d["product_id"] in ids | cable_ids
    ]
    bound_documents = {
        (b.product_id, b.document_id, b.document_revision)
        for device in plan.instances
        for port in device.ports
        if (b := port.terminal_binding) is not None
    }
    scoped_documents: list[Json] = []
    for document in cast(list[Object], scope["documents"]):
        key = (
            document["product_id"],
            document["document_id"],
            document["document_revision"],
        )
        product = rows.get(document["product_id"], {})
        source = next(
            (
                doc
                for doc in cast(list[Object], product.get("documents", []))
                if doc.get("document_id") == key[1]
                and doc.get("document_revision") == key[2]
                and isinstance(doc.get("blob_sha256"), str)
            ),
            None,
        )
        scoped_documents.append(
            {**document, "blob_sha256": source["blob_sha256"]}
            if key in bound_documents and source is not None
            else document
        )
    scope["documents"] = scoped_documents
    scope["reference_inputs"] = []
    return {
        **basis,
        "products": [rows[pid] for pid in sorted(ids) if pid in rows],
        **(
            {
                "cable_references": [
                    row
                    for row in cast(list[Object], basis["cable_references"])
                    if row["canonical_product_id"] in cable_ids
                ]
            }
            if "cable_references" in basis
            else {}
        ),
        "publication": scope,
    }


def _coordinates(point: RoutePoint) -> tuple[float, float, float]:
    assert point.height_m is not None
    return point.east_m, point.north_m, point.height_m


def route_takeoff(
    inputs: Object,
    basis: Object,
    *,
    bind_geometry: bool = False,
    allow_stale_products: bool = False,
) -> Object:
    plan = InstallationInputs.read(inputs.get("installation"))
    geometry = GeometryDocument.read(inputs.get("geometry"))
    # Use the exact saved document bytes, including its explicit/default shape.
    geometry_sha = digest(encode(cast(Object, inputs["geometry"])))
    if bind_geometry:
        plan = plan.model_copy(update={"geometry_sha256": geometry_sha})
    selected = product_basis(
        plan, basis, allow_stale=allow_stale_products or has_terminal_feature(plan)
    )
    products = {
        p["canonical_product_id"]: p for p in cast(list[Object], selected["products"])
    }
    stale_instances = {
        item.id
        for item in plan.instances
        if item.product_id is not None
        and products.get(item.product_id, {}).get("product_revision")
        != item.product_revision
    }
    sources = {s.id: s for s in geometry.sources}
    circuits, routes = {c.id: c for c in plan.circuits}, {r.id: r for r in plan.routes}
    ports = {(d.id, p.id): p for d in plan.instances for p in d.ports}
    instances = {d.id: d for d in plan.instances}
    # Shared paths are measured once, even when many conductors use them.
    lengths: dict[str, tuple[float, float | None]] = {}
    for route in plan.routes:
        projected = math.fsum(
            math.hypot(b.east_m - a.east_m, b.north_m - a.north_m)
            for a, b in zip(route.points, route.points[1:], strict=False)
        )
        spatial = (
            None
            if any(p.height_m is None for p in route.points)
            else math.fsum(
                math.dist(_coordinates(a), _coordinates(b))
                for a, b in zip(route.points, route.points[1:], strict=False)
            )
        )
        if any(
            v is not None and (not math.isfinite(v) or v > 2**53 - 1)
            for v in (projected, spatial)
        ):
            raise InvalidInput("route length exceeds the interoperable number range")
        lengths[route.id] = projected, spatial
    lines: list[Json] = []
    prepared_runs = {
        row["id"]: row
        for row in cast(list[Object], plan.project_document()["cable_runs"])
    }
    for cable in plan.cable_runs:
        route, circuit = routes[cable.route_id], circuits[cable.circuit_id]
        start = ports[(circuit.start.instance_id, circuit.start.port_id)].position
        end = ports[(circuit.end.instance_id, circuit.end.port_id)].position
        source_ids = {
            route.source_id,
            instances[circuit.start.instance_id].source_id,
            instances[circuit.end.instance_id].source_id,
        }
        reasons: list[Json] = []
        if plan.geometry_sha256 != geometry_sha:
            reasons.append("layout_confirmation_required")
        if any(sid not in sources for sid in source_ids):
            reasons.append("source_missing")
        if any(
            sources[sid].permissions.export != "permitted"
            for sid in source_ids
            if sid in sources
        ):
            reasons.append("source_export_unconfirmed")
        if not (
            (route.points[0] == start and route.points[-1] == end)
            or (route.points[0] == end and route.points[-1] == start)
        ):
            reasons.append("route_endpoints_differ")
        plan_length, length = lengths[route.id]
        if length is None or start.height_m is None or end.height_m is None:
            reasons.append("height_missing")
        if route.extra_length_m is None or route.extra_length_note is None:
            reasons.append("extra_length_unconfirmed")
        if length is not None and length <= 0:
            reasons.append("route_length_not_positive")
        total = (
            length + route.extra_length_m
            if not reasons and length is not None and route.extra_length_m is not None
            else None
        )
        # A conductor is a separate declared fact. Its absence leaves the
        # specification open; it never shortens or voids a measured length, and
        # it is never filled from a module count or packaged quantity.
        conductor = prepared_runs[cable.id].get("conductor")
        if any(
            value is not None and (not math.isfinite(value) or value > 2**53 - 1)
            for value in (plan_length, length, total)
        ):
            raise InvalidInput("route length exceeds the interoperable number range")
        lines.append(
            {
                "id": cable.id,
                "name": cable.name,
                "circuit_id": circuit.id,
                "circuit_name": circuit.name,
                "route_id": route.id,
                "route_name": route.name,
                "construction": cable.construction,
                "conductor": conductor,
                **(
                    {"core_roles": cast(Json, cable.core_roles)}
                    if "core_roles" in cable.model_fields_set
                    else {}
                ),
                "specification": "open" if conductor is None else "declared",
                "quantity": total,
                "unit": "m",
                "plan_length_m": plan_length,
                "route_length_m": length,
                "extra_length_m": route.extra_length_m,
                "extra_length_note": route.extra_length_note,
                "reasons": reasons,
                "source_ids": cast(Json, sorted(source_ids)),
            }
        )
    used_sources = {
        sid
        for line in cast(list[Object], lines)
        for sid in cast(list[str], line["source_ids"])
    }
    prepared = plan.project_document()
    input_sha = digest(encode(prepared))
    prepared_instances = {
        row["id"]: row for row in cast(list[Object], prepared["instances"])
    }
    return {
        "schema_version": 1,
        "method": METHOD,
        "geometry_sha256": geometry_sha,
        "input_sha256": input_sha,
        "prepared_inputs": prepared,
        **(
            {"terminal_assessment": terminal_assessment(plan, selected)}
            if has_terminal_feature(plan)
            else {}
        ),
        **(
            {"electrical": electrical_review(plan, selected, cast(list[Object], lines))}
            if any(
                "operating_conditions" in circuit.model_fields_set
                for circuit in plan.circuits
            )
            or any(
                "core_roles" in cable.model_fields_set
                or cable.conductor is not None
                and cable.conductor.cable_reference is not None
                for cable in plan.cable_runs
            )
            else {}
        ),
        **(
            {
                "pv_string_reconciliation": {
                    **_string_links(inputs, plan, lines, stale_instances),
                    "installation_input_sha256": input_sha,
                    "geometry_sha256": geometry_sha,
                }
            }
            if "pv_string_links" in plan.model_fields_set
            or inputs.get("pv_plant_string_plan") is not None
            else {}
        ),
        "instances": [
            {
                "id": d.id,
                "name": d.name,
                "product_id": d.product_id,
                "product_revision": d.product_revision,
                "model": products[d.product_id]["model"]
                if d.product_id in products
                and products[d.product_id]["product_revision"] == d.product_revision
                else None,
                "brand": products[d.product_id]["brand"]
                if d.product_id in products
                and products[d.product_id]["product_revision"] == d.product_revision
                else None,
                "ports": prepared_instances[d.id]["ports"],
            }
            for d in plan.instances
        ],
        "cables": lines,
        "sources": [
            cast(Json, source.model_dump(mode="json"))
            for source in geometry.sources
            if source.id in used_sources
        ],
        "qualified": False,
        "domains": {
            key: "not_assessed"
            for key in (
                "mounting",
                "cable_sizing",
                "connectors",
                "protection",
                "earthing",
                "country",
            )
        },
    }
