"""Electrical operating points under declared uniform module conditions.

These are model-point comparisons, not a maximum over every possible weather
condition, shading state or manufacturer EMS mode. Country/rating design stays
separate. Absolute cold Voc retains the manufacturer's independent method.
"""

from __future__ import annotations

from typing import Any, cast

from .canonical import Json, Object
from .pv_iv_model import derive_iv_model, model_point
from .pv_string_inputs import PvOperatingConditions


def assess_operating_conditions(
    conditions: PvOperatingConditions,
    strings: list[Json],
    module_facts: Object,
    inverter_facts: Object,
    uniform_trackers: dict[int, bool],
) -> Object:
    model = derive_iv_model(module_facts)
    checks: list[Json] = []
    points: list[Json] = []
    result: Object = {
        "model": model,
        "conditions": conditions.model_dump(mode="json"),
        "points": points,
        "checks": checks,
    }
    input_facts = cast(Object, model["input_facts"])
    references = list(input_facts.values())

    def add(
        identifier: str,
        status: str,
        reason: str,
        actual: Json = None,
        required: Json = None,
        facts: list[Json] | None = None,
        unit: str = "",
    ) -> None:
        checks.append(
            {
                "id": identifier,
                "status": status,
                "reason": reason,
                "actual": actual,
                "required": required,
                "facts": facts or [],
                "unit": unit,
            }
        )

    add(
        "pv_iv_model",
        "satisfied" if model["status"] == "available" else "unresolved",
        "derived_iv_model_with_numerical_readback"
        if model["status"] == "available"
        else str(model["reason"]),
        facts=references,
    )
    add(
        "pv_model_applicability",
        "unresolved",
        "manufacturer_iv_performance_validation_required",
    )
    if model["status"] != "available":
        return result
    g, hot, cold = (
        conditions.irradiance_w_m2,
        conditions.hot_cell_c,
        conditions.cold_cell_c,
    )
    if g is None or hot is None or cold is None or not conditions.source_note:
        add(
            "pv_operating_conditions",
            "unresolved",
            "operating_cell_conditions_required",
        )
        return result
    temperature = module_facts.get("operating_temp_c")
    limits = (
        temperature.get("value")
        if isinstance(temperature, dict)
        and temperature.get("status") == "typed"
        and temperature.get("shape") == "interval"
        and temperature.get("quantity") == "temperature"
        else None
    )
    temp_refs: list[Json] = [temperature] if isinstance(temperature, dict) else []
    if cold > hot or (
        isinstance(limits, list)
        and (cold < cast(float, limits[0]) or hot > cast(float, limits[1]))
    ):
        add(
            "pv_operating_conditions",
            "violated",
            "operating_cell_conditions_outside_domain",
            [cold, hot],
            limits,
            temp_refs,
            "°C",
        )
        return result
    add(
        "pv_operating_conditions",
        "satisfied" if limits is not None else "unresolved",
        "declared_uniform_irradiance_and_cell_conditions",
        [cold, hot],
        limits,
        temp_refs,
        "°C",
    )

    def field(key: str, mppt: int) -> tuple[Object | None, Json]:
        fact = inverter_facts.get(key)
        if not isinstance(fact, dict) or fact.get("status") != "typed":
            return (fact if isinstance(fact, dict) else None), None
        shape, value = fact["shape"], fact["value"]
        if shape == "ordered_values":
            entries = cast(list[Object], value)
            if mppt > len(entries):
                return fact, None
            value = entries[mppt - 1]["value"]
        return fact, value

    try:
        predicted = {
            case: model_point(cast(Object, model["parameters"]), g, temp)
            for case, temp in (("hot", hot), ("cold", cold))
        }
    except (
        ValueError,
        RuntimeError,
        FloatingPointError,
        OverflowError,
        ZeroDivisionError,
    ):
        add("pv_operating_curve", "unresolved", "module_operating_curve_not_admissible")
        return result
    tracker_rows: dict[int, list[dict[str, Any]]] = {}
    for row in cast(list[dict[str, Any]], strings):
        tracker_rows.setdefault(row["mppt"], []).append(row)
        fact, window = field("mppt_voltage_range_v", row["mppt"])
        known_window = (
            isinstance(window, list)
            and len(window) == 2
            and all(isinstance(x, (int, float)) for x in window)
            and fact is not None
            and fact.get("quantity") == "voltage"
        )
        for case, temperature_c in (("hot", hot), ("cold", cold)):
            estimate = predicted[case]
            voltage = row["module_count"] * cast(float, estimate["v_mp"])
            points.append(
                {
                    "string_id": row["id"],
                    "case": case,
                    "cell_c": temperature_c,
                    "irradiance_w_m2": g,
                    "v_mp_v": voltage,
                    "i_mp_a": estimate["i_mp"],
                    "i_sc_a": estimate["i_sc"],
                    "p_mp_w": row["module_count"] * cast(float, estimate["p_mp"]),
                }
            )
            status = (
                "unresolved"
                if not known_window
                else "satisfied"
                if cast(list[float], window)[0]
                <= voltage
                <= cast(list[float], window)[1]
                else "violated"
            )
            add(
                f"pv_{case}_mppt:{row['id']}",
                status,
                "modeled_mpp_at_declared_cell_condition",
                voltage,
                window if known_window else None,
                [*references, *([fact] if fact else [])],
                "V",
            )
    for tracker, rows in tracker_rows.items():
        for case in ("hot", "cold"):
            for suffix, prediction, key in (
                ("current", "i_mp", "mppt_max_current_a"),
                ("isc", "i_sc", "mppt_max_isc_a"),
            ):
                fact, maximum = field(key, tracker)
                # Different parallel string lengths/orientations do not have
                # independently attainable MPPs on the same tracker.
                coherent = suffix == "isc" or uniform_trackers.get(tracker, False)
                actual = (
                    len(rows) * cast(float, predicted[case][prediction])
                    if coherent
                    else None
                )
                known = (
                    isinstance(maximum, (int, float))
                    and fact is not None
                    and fact.get("quantity") == "current"
                )
                status = (
                    "unresolved"
                    if actual is None or not known
                    else "satisfied"
                    if actual <= cast(float, maximum)
                    else "violated"
                )
                add(
                    f"pv_{case}_{suffix}:{tracker}",
                    status,
                    "modeled_parallel_current_at_declared_conditions"
                    if coherent
                    else "parallel_operating_mpp_requires_matching_strings",
                    actual,
                    maximum if known else None,
                    [*references, *([fact] if fact else [])],
                    "A",
                )
    return result
