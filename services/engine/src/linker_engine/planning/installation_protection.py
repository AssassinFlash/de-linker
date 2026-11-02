"""Bounded comparisons of project-provided protective-device evidence.

Schneider Electrical Installation Guide E7/E8 and PE Fig.G59 are recorded in
CAPABILITY-MAP sections 9.2 and 9.5. This does not establish installation,
earthing, automatic disconnection, coordination or national compliance.
"""

from __future__ import annotations

import math
from typing import cast

from .canonical import Json, Object, digest, encode
from .installation_inputs import InstallationInputs
from .installation_protection_inputs import ProtectionAssessment

METHOD = "installation_protection_evidence_v1"


def _context(
    plan: InstallationInputs, item: ProtectionAssessment, stale_instances: set[str]
) -> Object | None:
    circuit = next((c for c in plan.circuits if c.id == item.circuit_id), None)
    protector = next(
        (m for m in plan.materials if m.id == item.protection_material_id), None
    )
    if (
        circuit is None
        or protector is None
        or protector.kind != "protection"
        or protector.circuit_id != circuit.id
        or protector.unit != "piece"
        or protector.quantity != 1
    ):
        return None
    condition = next(
        (
            c
            for c in circuit.operating_conditions
            if c.id == item.operating_condition_id
        ),
        None,
    )
    if (
        condition is None
        or (circuit.kind == "ac") != (condition.method != "dc_resistive")
        or circuit.kind not in {"ac", "pv_dc", "battery_dc"}
    ):
        return None
    runs = [r for r in plan.cable_runs if r.circuit_id == circuit.id]
    if not runs:
        return None
    for thermal in item.thermal:
        run = next((r for r in plan.cable_runs if r.id == thermal.run_id), None)
        other = next(
            (c for c in plan.circuits if run is not None and c.id == run.circuit_id),
            None,
        )
        if (
            run is None
            or other is None
            or thermal.core_role not in run.core_roles
            or run.conductor is None
        ):
            return None
        if other.id != circuit.id:
            main_ends = {circuit.start.instance_id, circuit.end.instance_id}
            other_ends = {other.start.instance_id, other.end.instance_id}
            if (
                thermal.core_role != "pe"
                or other.kind != "protective_earth"
                or main_ends != other_ends
            ):
                return None
        if run not in runs:
            runs.append(run)
    runs.sort(key=lambda run: run.id)
    routes = [
        r.model_dump(mode="json", exclude={"name"})
        for r in sorted(plan.routes, key=lambda value: value.id)
        if r.id in {run.route_id for run in runs}
    ]
    involved = [
        c
        for c in sorted(plan.circuits, key=lambda value: value.id)
        if c.id in {run.circuit_id for run in runs} | {circuit.id}
    ]
    involved_circuits = [
        c.model_dump(mode="json", include={"id", "kind", "start", "end"})
        for c in involved
    ]
    endpoints = {
        (endpoint.instance_id, endpoint.port_id)
        for c in involved
        for endpoint in (c.start, c.end)
    }
    if any(instance_id in stale_instances for instance_id, _ in endpoints):
        return None
    instances = [
        {
            "id": d.id,
            "product_id": d.product_id,
            "product_revision": d.product_revision,
            "source_id": d.source_id,
            "ports": [
                p.model_dump(mode="json", exclude={"name"})
                for p in sorted(d.ports, key=lambda value: value.id)
                if (d.id, p.id) in endpoints
            ],
        }
        for d in sorted(plan.instances, key=lambda value: value.id)
        if any(instance_id == d.id for instance_id, _ in endpoints)
    ]
    return {
        "assessment": cast(
            Json, item.model_dump(mode="json", exclude={"confirmed_context_sha256"})
        ),
        "circuits": cast(Json, involved_circuits),
        "operating_condition": cast(
            Json, condition.model_dump(mode="json", exclude={"name"})
        ),
        "protection_material": cast(Json, protector.model_dump(mode="json")),
        "runs": cast(
            Json,
            [
                r.model_dump(
                    mode="json",
                    exclude={
                        "name",
                        "reference_current_installation",
                        "manufacturer_comparison",
                    },
                )
                for r in runs
            ],
        ),
        "routes": cast(Json, routes),
        "instances": cast(Json, instances),
    }


def _comparison(measured: float, maximum: float) -> Object:
    return {
        "status": "within_declared_values"
        if measured <= maximum
        else "outside_declared_values",
        "measured": measured,
        "maximum": maximum,
    }


def _one(
    plan: InstallationInputs, item: ProtectionAssessment, stale_instances: set[str]
) -> Object:
    context = _context(plan, item, stale_instances)
    key = digest(encode(context)) if context is not None else None
    state = (
        "context_unavailable"
        if key is None
        else "confirmation_required"
        if item.confirmed_context_sha256 is None
        else "confirmed"
        if item.confirmed_context_sha256 == key
        else "context_changed"
    )
    result: Object = {
        "id": item.id,
        "circuit_id": item.circuit_id,
        "protection_material_id": item.protection_material_id,
        "scenario": item.scenario,
        "confirmation_context_sha256": key,
        "confirmation_status": state,
        "breaking": {"status": "not_assessed"},
        "disconnection": {"status": "not_assessed"},
        "thermal": [],
        "qualified": False,
    }
    if state != "confirmed":
        result["breaking"] = {"status": "not_assessed", "reason": state}
        result["disconnection"] = {"status": "not_assessed", "reason": state}
        result["thermal"] = cast(
            Json,
            [
                {
                    "run_id": e.run_id,
                    "core_role": e.core_role,
                    "status": "not_assessed",
                    "reason": state,
                }
                for e in item.thermal
            ],
        )
        return result
    circuit = next(c for c in plan.circuits if c.id == item.circuit_id)
    condition = next(
        c for c in circuit.operating_conditions if c.id == item.operating_condition_id
    )
    kind = "dc" if condition.method == "dc_resistive" else "ac"
    if item.fault_range is None:
        result["breaking"] = {"status": "not_assessed", "reason": "fault_range_missing"}
        result["disconnection"] = {
            "status": "not_assessed",
            "reason": "fault_range_missing",
        }
    else:
        if item.breaking is None:
            result["breaking"] = {
                "status": "not_assessed",
                "reason": "device_rating_missing",
            }
        if item.disconnection is None:
            result["disconnection"] = {
                "status": "not_assessed",
                "reason": "clearing_evidence_missing",
            }
    if item.fault_range and item.breaking:
        breaking = item.breaking
        if (
            breaking.current_kind == kind
            and breaking.rated_voltage_v == condition.reference_voltage_v
        ):
            result["breaking"] = {
                **_comparison(item.fault_range.maximum_fault_a, breaking.capacity_a),
                "fault_source_note": item.fault_range.source_note,
                "device_source_note": breaking.source_note,
                "voltage_v": condition.reference_voltage_v,
                "current_kind": kind,
            }
        else:
            result["breaking"] = {
                "status": "not_assessed",
                "reason": "rating_conditions_differ",
            }
    if (
        item.fault_range
        and item.disconnection
        and item.fault_range.minimum_fault_a == 0
    ):
        result["disconnection"] = {
            "status": "not_assessed",
            "reason": "zero_minimum_fault_current",
        }
    elif item.fault_range and item.disconnection:
        disconnection = item.disconnection
        result["disconnection"] = {
            **_comparison(
                disconnection.device_worst_case_clear_s, disconnection.required_clear_s
            ),
            "minimum_fault_a": item.fault_range.minimum_fault_a,
            "fault_source_note": item.fault_range.source_note,
            "device_source_note": disconnection.device_source_note,
            "limit_source_note": disconnection.limit_source_note,
        }
    thermal_results: list[Json] = []
    for thermal in item.thermal:
        row: Object = {
            "run_id": thermal.run_id,
            "core_role": thermal.core_role,
            "status": "not_assessed",
        }
        run = next(r for r in plan.cable_runs if r.id == thermal.run_id)
        assert run.conductor is not None
        if item.fault_range is None:
            row["reason"] = "fault_range_missing"
        elif (
            thermal.coverage_min_fault_a > item.fault_range.minimum_fault_a
            or thermal.coverage_max_fault_a < item.fault_range.maximum_fault_a
        ):
            row["reason"] = "fault_range_not_covered"
        elif thermal.maximum_clear_s > 5:
            row["reason"] = "adiabatic_duration_exceeds_five_seconds"
        elif (
            item.disconnection
            and thermal.maximum_clear_s < item.disconnection.device_worst_case_clear_s
        ):
            row["reason"] = "clearing_time_evidence_inconsistent"
        else:
            factor = thermal.k_a_sqrt_s_per_mm2 * run.conductor.cross_section_mm2
            capacity = factor * factor
            if not math.isfinite(capacity):
                row["reason"] = "numerical_range_not_supported"
            else:
                row.update(_comparison(thermal.maximum_let_through_a2s, capacity))
                row.update(
                    {
                        "cross_section_mm2": run.conductor.cross_section_mm2,
                        "k_a_sqrt_s_per_mm2": thermal.k_a_sqrt_s_per_mm2,
                        "maximum_clear_s": thermal.maximum_clear_s,
                        "coverage_min_fault_a": thermal.coverage_min_fault_a,
                        "coverage_max_fault_a": thermal.coverage_max_fault_a,
                        "fault_source_note": item.fault_range.source_note,
                        "k_source_note": thermal.k_source_note,
                        "let_through_source_note": thermal.let_through_source_note,
                    }
                )
        thermal_results.append(row)
    result["thermal"] = thermal_results
    return result


def protection_review(plan: InstallationInputs, stale_instances: set[str]) -> Object:
    return {
        "method": METHOD,
        "assessments": cast(
            Json,
            [_one(plan, item, stale_instances) for item in plan.protection_assessments],
        ),
        "qualified": False,
    }
