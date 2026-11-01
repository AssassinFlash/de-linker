"""Steady conductor-only circuit results, using CAPABILITY-MAP section 9.

DC uses the explicit resistive-loop derivation. AC uses Schneider EIG Fig.G29
for two-wire and balanced three-phase steady sinusoidal conditions. Neither
method supplies terminal, protection, thermal or country qualification.
"""

from __future__ import annotations

import math
from typing import cast

from .cable_facts import CableFacts, CableParameterSet
from .canonical import Json, Object
from .installation_inputs import CircuitOperatingCondition, InstallationInputs

METHOD = "installation_circuit_steady_conductors_v1"


def _condition(
    plan: InstallationInputs,
    circuit_id: str,
    condition: CircuitOperatingCondition,
    basis: Object,
    cables: list[Object],
) -> Object:
    circuit = next(row for row in plan.circuits if row.id == circuit_id)
    rows = [row for row in plan.cable_runs if row.circuit_id == circuit_id]
    measured = {row["id"]: row for row in cables}
    references = {
        row["canonical_product_id"]: row
        for row in cast(list[Object], basis.get("cable_references", []))
    }
    reasons: list[str] = []
    unsupported: list[str] = []
    required: tuple[str, ...]
    if condition.method == "dc_resistive":
        required = ("dc_positive", "dc_negative")
        if circuit.kind not in {"pv_dc", "battery_dc"} or any(
            value is not None
            for value in (
                condition.frequency_hz,
                condition.power_factor,
                condition.reactive_direction,
                condition.balanced,
            )
        ):
            unsupported.append("dc_condition_not_applicable")
    else:
        required = (
            ("line", "neutral")
            if condition.method == "ac_two_wire"
            else ("l1", "l2", "l3")
        )
        if condition.method == "ac_two_wire" and {
            role
            for run in rows
            for role in run.core_roles
            if role not in {"pe", "unused"}
        } == {"l1", "l2"}:
            required = ("l1", "l2")
        if (
            circuit.kind != "ac"
            or not condition.sinusoidal
            or condition.frequency_hz is None
            or condition.power_factor is None
            or condition.reactive_direction is None
            or condition.arrangement is None
            or condition.method == "ac_balanced_three_phase"
            and condition.balanced is not True
        ):
            unsupported.append("ac_condition_not_applicable")
    segments: list[Object] = []
    roles: dict[str, list[Object]] = {role: [] for role in required}
    non_current_roles = {"pe", "unused"}
    if (
        condition.method == "ac_balanced_three_phase"
        and condition.balanced is True
        and condition.sinusoidal
    ):
        # Under the explicitly declared balance and sinusoidal restriction,
        # the neutral carries zero steady current. It remains a purchased core.
        non_current_roles.add("neutral")
    if not rows:
        reasons.append("cable_runs_missing")
    for run in rows:
        active = [role for role in run.core_roles if role not in non_current_roles]
        if not run.core_roles:
            reasons.append("core_roles_missing")
        if any(role not in required for role in active):
            unsupported.append("core_roles_not_applicable")
        selection = run.conductor.cable_reference if run.conductor else None
        raw = references.get(selection.product_id) if selection else None
        if (
            raw is None
            or selection is None
            or raw.get("product_revision") != selection.product_revision
        ):
            reasons.append("cable_reference_unavailable")
            continue
        facts = CableFacts.read(raw.get("cable_facts"))
        assert run.conductor is not None
        if (
            run.construction != facts.construction
            or run.conductor.cross_section_mm2 != facts.cross_section_mm2
            or len(run.core_roles) != facts.core_count
        ):
            reasons.append("cable_specification_mismatch")
            continue
        # Non-current cores still belong to the selected physical cable, so
        # its identity and every core must be accounted for above. They do not
        # need a resistance/temperature/frequency selection for zero current.
        if run.core_roles and not active:
            continue
        matching = [
            p
            for p in facts.parameter_sets
            if p.current_kind == ("dc" if condition.method == "dc_resistive" else "ac")
            and p.temperature_c == condition.conductor_temperature_c
            and p.frequency_hz == condition.frequency_hz
            and p.arrangement == condition.arrangement
        ]
        if len(matching) != 1:
            reasons.append(
                "cable_conditions_mismatch"
                if not matching
                else "cable_parameter_set_ambiguous"
            )
            continue
        parameter: CableParameterSet = matching[0]
        length = measured[run.id]["quantity"]
        if not isinstance(length, (int, float)):
            reasons.append("route_quantity_unconfirmed")
            continue
        for role in active:
            segment: Object = {
                "run_id": run.id,
                "role": role,
                "length_m": length,
                "product_id": selection.product_id,
                "product_revision": selection.product_revision,
                "reference_input_id": raw["id"],
                "parameter_set_id": parameter.id,
                "resistance_basis": parameter.resistance_basis,
                "resistance_ohm": parameter.resistance_ohm_per_km * length / 1000,
                "reactance_ohm": parameter.reactance_ohm_per_km * length / 1000
                if parameter.reactance_ohm_per_km is not None
                else None,
                "source": cast(Json, parameter.source.model_dump(mode="json")),
            }
            if any(
                value is not None and not math.isfinite(cast(float, value))
                for value in (segment["resistance_ohm"], segment["reactance_ohm"])
            ):
                reasons.append("numerical_range_not_supported")
                continue
            segments.append(segment)
            if role in roles:
                roles[role].append(segment)
    if any(len(items) > 1 for items in roles.values()):
        unsupported.append("parallel_or_branched_cores_not_supported")
    if any(not items for items in roles.values()):
        reasons.append("current_path_incomplete")
    resistance, reactance, drop, loss = None, None, None, None
    if not reasons and not unsupported:
        resistance = _sum_impedance(segments, "resistance_ohm")
        if condition.method == "dc_resistive":
            drop = condition.current_a * resistance
        else:
            reactance = _sum_impedance(segments, "reactance_ohm")
            assert condition.power_factor is not None
            sine = math.sqrt(max(0, 1 - condition.power_factor**2)) * (
                1 if condition.reactive_direction == "lagging" else -1
            )
            factor = 1.0
            if condition.method == "ac_balanced_three_phase":
                # Fig.G29 assumes equal phase impedances. No averaging unequal
                # paths, lengths or source groups into a fabricated balance.
                values = {
                    (
                        row["resistance_ohm"],
                        row["reactance_ohm"],
                        row["resistance_basis"],
                    )
                    for row in segments
                }
                if len(values) != 1:
                    unsupported.append("phase_impedances_not_equal")
                factor = math.sqrt(3) / 3
            drop = (
                factor
                * condition.current_a
                * (resistance * condition.power_factor + reactance * sine)
            )
        loss = condition.current_a * condition.current_a * resistance
        if unsupported:
            resistance, reactance, drop, loss = None, None, None, None
    percent = 100 * drop / condition.reference_voltage_v if drop is not None else None
    if any(
        value is not None and not math.isfinite(value)
        for value in (resistance, reactance, drop, loss, percent)
    ):
        reasons.append("numerical_range_not_supported")
        resistance, reactance, drop, loss = None, None, None, None
        percent = None
    parameter_bases = {row["resistance_basis"] for row in segments}
    resistance_basis = (
        next(iter(parameter_bases))
        if len(parameter_bases) == 1
        else "mixed"
        if parameter_bases
        else None
    )
    # With a leading load the reactive term is negative. An upper resistance
    # bounds signed drop, but cannot by itself bound its absolute magnitude:
    # a smaller actual R can yield a larger voltage rise. Keep the computed
    # condition, without calling this an absolute voltage-limit assessment.
    limit_reason = (
        "resistance_upper_bound_not_absolute_drop_bound"
        if percent is not None
        and condition.voltage_limit is not None
        and condition.method != "dc_resistive"
        and condition.reactive_direction == "leading"
        and condition.power_factor is not None
        and 0 < condition.power_factor < 1
        and condition.current_a > 0
        and reactance is not None
        and reactance > 0
        and "maximum" in parameter_bases
        else None
    )
    return {
        "condition_id": condition.id,
        "name": condition.name,
        "condition": cast(Json, condition.model_dump(mode="json")),
        "status": "method_not_applicable"
        if unsupported
        else "data_insufficient"
        if reasons
        else "calculated",
        "reasons": cast(Json, sorted(set(reasons + unsupported))),
        "segments": cast(Json, segments),
        "resistance_basis": resistance_basis,
        "value_basis": "resistance_upper_bound"
        if resistance_basis == "maximum"
        else "nominal_parameters"
        if resistance_basis == "nominal"
        else "mixed_resistance_parameters"
        if resistance_basis
        else None,
        "loop_resistance_ohm": resistance,
        "loop_reactance_ohm": reactance,
        "voltage_drop_v": drop,
        "voltage_drop_percent": percent,
        "end_minus_start_voltage_v": (
            -drop if condition.direction == "start_to_end" else drop
        )
        if drop is not None
        else None,
        "conductor_loss_w": loss,
        "limit": {
            "status": "not_evaluated"
            if percent is None or limit_reason is not None
            else "not_declared"
            if condition.voltage_limit is None
            else "within_declared_limit"
            if abs(percent) <= condition.voltage_limit.maximum_percent
            else "exceeds_declared_limit",
            "declared": cast(Json, condition.voltage_limit.model_dump(mode="json"))
            if condition.voltage_limit
            else None,
            **({"reason": limit_reason} if limit_reason is not None else {}),
        },
        "scope": "conductor_segments_only",
        "qualified": False,
    }


def _sum_impedance(segments: list[Object], key: str) -> float:
    try:
        return math.fsum(cast(float, row[key]) for row in segments)
    except OverflowError:
        return math.inf


def electrical_review(
    plan: InstallationInputs, basis: Object, cables: list[Object]
) -> Object:
    return {
        "schema_version": 1,
        "method": METHOD,
        "circuits": [
            {
                "circuit_id": circuit.id,
                "name": circuit.name,
                "status": "not_recorded"
                if not circuit.operating_conditions
                else "reviewed",
                "conditions": [
                    _condition(plan, circuit.id, condition, basis, cables)
                    for condition in circuit.operating_conditions
                ],
            }
            for circuit in plan.circuits
        ],
        "qualified": False,
    }
