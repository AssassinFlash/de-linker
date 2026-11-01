"""Compare a declared PV conductor current with one cited table row.

This is neither a site ampacity calculation nor protection or cable selection.
The manufacturer's 120 C rating basis is not the project's conductor
temperature or the temperature of a resistance measurement.
"""

from __future__ import annotations

from typing import cast

from .cable_facts import CableFacts, CableReferenceCurrentRating
from .canonical import Json, Object
from .installation_inputs import (
    CableRun,
    CircuitOperatingCondition,
    Endpoint,
    InstallationCircuit,
    InstallationInputs,
)

METHOD = "installation_single_conductor_reference_current_v1"


def _physical_run(plan: InstallationInputs, run: CableRun) -> Object:
    route = next(row for row in plan.routes if row.id == run.route_id)
    circuit = next(row for row in plan.circuits if row.id == run.circuit_id)

    def endpoint(value: Endpoint) -> Object:
        instance = next(row for row in plan.instances if row.id == value.instance_id)
        port = next(row for row in instance.ports if row.id == value.port_id)
        return {
            "instance_id": instance.id,
            "port_id": port.id,
            "product_id": instance.product_id,
            "product_revision": instance.product_revision,
            "position": cast(Json, port.position.model_dump(mode="json")),
        }

    return {
        "id": run.id,
        "construction": run.construction,
        "core_roles": cast(Json, run.core_roles),
        "cross_section_mm2": run.conductor.cross_section_mm2 if run.conductor else None,
        "cable_reference": cast(
            Json, run.conductor.cable_reference.model_dump(mode="json")
        )
        if run.conductor and run.conductor.cable_reference
        else None,
        "route": {
            "id": route.id,
            "points": cast(
                Json, [point.model_dump(mode="json") for point in route.points]
            ),
            "extra_length_m": route.extra_length_m,
        },
        "circuit": {
            "id": circuit.id,
            "kind": circuit.kind,
            "start": endpoint(circuit.start),
            "end": endpoint(circuit.end),
        },
    }


def reference_current_confirmation_context(
    plan: InstallationInputs, run: CableRun
) -> Object:
    """Comparable snapshot of the owner-confirmed physical context only."""
    declaration = run.reference_current_installation
    assert declaration is not None
    other = next(
        (row for row in plan.cable_runs if row.id == declaration.touching_run_id), None
    )
    return {
        "declaration": {
            "rating_id": declaration.rating_id,
            "laying": declaration.laying,
            "ambient_temperature_c": declaration.ambient_temperature_c,
            "touching_run_id": declaration.touching_run_id,
            "current_path": declaration.current_path,
        },
        "run": _physical_run(plan, run),
        "touching_run": _physical_run(plan, other) if other is not None else None,
    }


def _source_bound(raw: Object, rating: CableReferenceCurrentRating, pid: int) -> bool:
    source = rating.source
    if source.product_id != pid:
        return False
    return any(
        isinstance(doc, dict)
        and pid in cast(list[int], doc.get("product_ids", []))
        and all(
            doc.get(key) == getattr(source, key)
            for key in ("document_id", "document_revision", "blob_sha256", "url")
        )
        for doc in cast(list[Object], raw.get("documents", []))
    )


def _touching_matches(
    plan: InstallationInputs,
    run: CableRun,
    rows: list[CableRun],
    incoming: dict[str, set[str]],
) -> bool:
    selected = run.reference_current_installation
    assert selected is not None
    if selected.laying != "two_touching_on_surface":
        return selected.touching_run_id is None and not incoming.get(run.id)
    other = next((row for row in rows if row.id == selected.touching_run_id), None)
    if other is None or other.id == run.id:
        return False
    other_decl = other.reference_current_installation
    return bool(
        other_decl is not None
        and other_decl.laying == selected.laying
        and other_decl.rating_id == selected.rating_id
        and other_decl.ambient_temperature_c == selected.ambient_temperature_c
        and other_decl.touching_run_id == run.id
        and incoming.get(run.id) == {other.id}
        and incoming.get(other.id) == {run.id}
        and other_decl.conditions_confirmed
        and other_decl.confirmation_context is not None
        and other_decl.confirmation_context.model_dump(mode="json")
        == reference_current_confirmation_context(plan, other)
        and other.route_id == run.route_id
        and other.conductor is not None
        and run.conductor is not None
        and run.conductor.cable_reference is not None
        and other.conductor.cable_reference == run.conductor.cable_reference
    )


def _segment(
    plan: InstallationInputs,
    circuit: InstallationCircuit,
    condition: CircuitOperatingCondition | None,
    run: CableRun,
    rows: list[CableRun],
    references: dict[Json, Object],
    incoming: dict[str, set[str]],
) -> Object:
    declaration = run.reference_current_installation
    assert declaration is not None
    reasons: list[str] = []
    if condition is None:
        reasons.append("operating_condition_missing")
    if circuit.kind != "pv_dc":
        reasons.append("circuit_kind_not_supported")
    if condition is not None and (
        condition.method != "dc_resistive"
        or any(
            value is not None
            for value in (
                condition.frequency_hz,
                condition.power_factor,
                condition.reactive_direction,
                condition.balanced,
            )
        )
    ):
        reasons.append("condition_method_not_supported")
    if (
        len(rows) != 2
        or any(row.construction != "single_conductor" for row in rows)
        or sorted(role for row in rows for role in row.core_roles)
        != ["dc_negative", "dc_positive"]
        or any(len(row.core_roles) != 1 for row in rows)
    ):
        reasons.append("current_path_not_single_pair")
    if any(
        row.reference_current_installation is None
        or row.reference_current_installation.current_path != "single_unbranched"
        for row in rows
    ):
        reasons.append("current_path_not_confirmed")
    if not declaration.conditions_confirmed:
        reasons.append("installation_conditions_not_confirmed")
    if (
        declaration.confirmation_context is None
        or declaration.confirmation_context.model_dump(mode="json")
        != reference_current_confirmation_context(plan, run)
    ):
        reasons.append("confirmation_context_changed")
    if not _touching_matches(plan, run, rows, incoming):
        reasons.append("touching_pair_mismatch")

    selection = run.conductor.cable_reference if run.conductor else None
    raw = references.get(selection.product_id) if selection else None
    rating: CableReferenceCurrentRating | None = None
    if (
        raw is None
        or selection is None
        or raw.get("product_revision") != selection.product_revision
    ):
        reasons.append("cable_reference_unavailable")
    else:
        facts = CableFacts.read(raw["cable_facts"])
        assert run.conductor is not None
        if (
            run.construction != "single_conductor"
            or facts.construction != "single_conductor"
            or facts.core_count != 1
            or run.conductor.cross_section_mm2 != facts.cross_section_mm2
        ):
            reasons.append("cable_specification_mismatch")
        matches = [
            r for r in facts.reference_current_ratings if r.id == declaration.rating_id
        ]
        if len(matches) != 1:
            reasons.append("reference_rating_unavailable")
        else:
            rating = matches[0]
            # The reviewed NPE SUN PLUS data sheets, page 2, give these rows
            # only at 60 °C ambient and 120 °C reference conductor temperature.
            if (
                rating.laying != declaration.laying
                or rating.ambient_temperature_c != declaration.ambient_temperature_c
                or rating.ambient_temperature_c != 60
                or rating.rated_conductor_temperature_c != 120
            ):
                reasons.append("reference_rating_conditions_mismatch")
            if not _source_bound(raw, rating, selection.product_id):
                reasons.append("reference_source_unavailable")

    assessed = not reasons and condition is not None and rating is not None
    project_current = (
        condition.current_a if assessed and condition is not None else None
    )
    reference_current = rating.current_a if assessed and rating is not None else None
    status = "not_evaluated"
    if project_current is not None and reference_current is not None:
        status = (
            "below_reference"
            if project_current < reference_current
            else "above_reference"
            if project_current > reference_current
            else "equal_reference"
        )
    return {
        "circuit_id": circuit.id,
        "condition_id": condition.id if condition is not None else None,
        "run_id": run.id,
        "role": run.core_roles[0] if len(run.core_roles) == 1 else None,
        "status": status,
        "reasons": cast(Json, reasons),
        "project_current_a": project_current,
        "reference_current_a": reference_current,
        "installation": declaration.project_document(),
        "rating": cast(Json, rating.model_dump(mode="json"))
        if rating is not None and "reference_source_unavailable" not in reasons
        else None,
        "product_id": selection.product_id if selection is not None else None,
        "product_revision": selection.product_revision
        if selection is not None
        else None,
        "reference_input_id": raw.get("id") if raw is not None else None,
        "scope": "single_conductor_reference_only",
        "qualified": False,
    }


def reference_current_segments(plan: InstallationInputs, basis: Object) -> list[Object]:
    """Input-order stable: circuits, then conditions, then physical runs."""
    references = {
        row["canonical_product_id"]: row
        for row in cast(list[Object], basis.get("cable_references", []))
    }
    # A declaration from another circuit can contradict a single cable or
    # a two-cable pair. A shared route by itself does not establish contact.
    incoming: dict[str, set[str]] = {}
    for run in plan.cable_runs:
        declaration = run.reference_current_installation
        if declaration is not None and declaration.touching_run_id is not None:
            incoming.setdefault(declaration.touching_run_id, set()).add(run.id)
    result: list[Object] = []
    for circuit in plan.circuits:
        rows = [run for run in plan.cable_runs if run.circuit_id == circuit.id]
        selected = [
            run for run in rows if run.reference_current_installation is not None
        ]
        conditions: list[CircuitOperatingCondition | None] = (
            list(circuit.operating_conditions)
            if circuit.operating_conditions
            else [None]
        )
        result.extend(
            _segment(plan, circuit, condition, run, rows, references, incoming)
            for condition in conditions
            for run in selected
        )
    return result
