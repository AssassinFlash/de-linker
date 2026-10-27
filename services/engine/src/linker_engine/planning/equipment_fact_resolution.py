"""Resolve documented Woo conditions against an explicit selected scenario.

The source status/qualifier remains intact. Only known quantity meanings and
conditions are matched; unknown conditions never become unconditional facts.
Temperature is a declared scenario input, never inferred from outdoor weather.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Literal, cast

from .canonical import Json, Object, encode
from .equipment_facts import numeric_value
from .equipment_inputs import EquipmentSelection

type FactUse = Literal[
    "numeric",
    "nominal_ac_output",
    "grid_output_ceiling",
    "grid_input_ceiling",
    "pv_nameplate_limit",
    "normal_charge_current",
    "normal_discharge_current",
    "battery_terminal_power",
    "bank_rated_dc_power",
    "battery_operating_voltage",
]


@dataclass(frozen=True)
class FactContext:
    selection: EquipmentSelection
    products: dict[int, dict[str, Any]]
    battery_temperature_c: float | None = None
    battery_port_id: str | None = None
    battery_port_count: int | None = None
    country_code: str | None = None


@dataclass(frozen=True)
class FactResolution:
    fact: Object | None
    issue: str | None = None


def declared_battery_ports(compiled: Object) -> list[str] | None:
    """Explicit source labels, None for unnamed ports, [] for contradictory labels.

    Count-only legacy sources are never expanded into an unbounded list. Their
    existing numeric port selection is separately checked by the DC adapter.
    """
    facts = cast(Object, compiled["facts"])
    counts = [
        fact["value"]
        for key in ("n_battery_ports", "battery_port_count", "number_of_battery_ports")
        if isinstance((fact := facts.get(key)), dict)
        and fact.get("status") == "typed"
        and fact.get("shape") == "scalar"
        and fact.get("quantity") == "count"
    ]
    declared: list[list[str]] = []
    for key in ("max_battery_charge_a", "max_battery_discharge_a"):
        fact = facts.get(key)
        if not isinstance(fact, dict) or fact.get("source") is None:
            continue
        qualifier = fact.get("qualifier")
        if not isinstance(qualifier, dict) or "ports" not in qualifier:
            continue
        ports = qualifier["ports"]
        if (
            qualifier.get("scope") != "per_battery_port"
            or not isinstance(ports, list)
            or not ports
            or not all(isinstance(p, str) and p for p in ports)
            or len(set(cast(list[str], ports))) != len(ports)
        ):
            return []
        declared.append(cast(list[str], ports))
    if not declared:
        return None
    first = declared[0]
    if (
        not counts
        or any(count != len(first) for count in counts)
        or any(set(names) != set(first) for names in declared)
    ):
        return []
    return first


def _finite(value: Json | None) -> bool:
    return type(value) in (int, float) and math.isfinite(cast(float, value))


def _configured_column(fact: Object, count: int | None) -> FactResolution:
    columns = fact.get("columns")
    if fact.get("shape") != "ordered_values":
        qualifier = fact.get("qualifier")
        if (
            not isinstance(qualifier, dict)
            or qualifier.get("module_count_basis") != "columns"
        ):
            return FactResolution(fact)
        values: list[Json] = [{"shape": fact.get("shape"), "value": fact.get("value")}]
    else:
        raw_values = fact.get("value")
        values = raw_values if isinstance(raw_values, list) else []
    if (
        count is None
        or not isinstance(columns, list)
        or not isinstance(values, list)
        or len(columns) != len(values)
        or not columns
    ):
        return FactResolution(None, "module_count_column_required")
    counts: list[int] = []
    for raw in columns:
        if not isinstance(raw, dict):
            return FactResolution(None, "module_count_column_required")
        keys = set(raw)
        identity = keys & {"module_count", "modules_per_stack"}
        if len(identity) != 1 or keys - {
            *identity,
            "model",
            "unit",
            "value",
            "min",
            "max",
        }:
            return FactResolution(None, "module_count_column_required")
        column_count = raw[next(iter(identity))]
        if type(column_count) is not int or column_count < 1:
            return FactResolution(None, "module_count_column_required")
        counts.append(column_count)
    if len(set(counts)) != len(counts) or counts.count(count) != 1:
        return FactResolution(None, "module_count_column_required")
    index = counts.index(count)
    column, value = cast(Object, columns[index]), values[index]
    if not isinstance(value, dict) or value.get("shape") not in ("scalar", "interval"):
        return FactResolution(None, "module_count_column_required")
    # A maintained model label is descriptive. Only the explicit count picks
    # the column, and any redundant value/unit must agree with the raw table.
    if "model" in column and not isinstance(column["model"], str):
        return FactResolution(None, "module_count_column_required")
    if "unit" in column:
        unit = column["unit"]
        if not isinstance(unit, str):
            return FactResolution(None, "column_value_unit_mismatch")
        try:
            quantity, canonical_unit, _, _ = numeric_value(0, unit)
        except KeyError:
            return FactResolution(None, "column_value_unit_mismatch")
        if quantity != fact.get("quantity") or canonical_unit != fact.get("unit"):
            return FactResolution(None, "column_value_unit_mismatch")
    if {"value", "min", "max"} & set(column):
        unit = column.get("unit")
        if not isinstance(unit, str):
            return FactResolution(None, "column_value_unit_mismatch")
        try:
            if "value" in column and not {"min", "max"} & set(column):
                raw_value = column["value"]
                if type(raw_value) not in (str, int, float):
                    raise ValueError("numeric column value required")
                quantity, canonical_unit, shape, parsed = numeric_value(
                    cast(str | int | float, raw_value), unit
                )
            elif {"min", "max"}.issubset(column) and "value" not in column:
                low, high = column["min"], column["max"]
                if not _finite(low) or not _finite(high):
                    raise ValueError("finite interval column required")
                quantity, canonical_unit, _, left = numeric_value(
                    cast(float, low), unit
                )
                _, _, _, right = numeric_value(cast(float, high), unit)
                shape, parsed = "interval", [left, right]
            else:
                raise ValueError("one column quantity required")
        except (KeyError, ValueError, OverflowError):
            return FactResolution(None, "column_value_unit_mismatch")
        if (
            quantity != fact.get("quantity")
            or canonical_unit != fact.get("unit")
            or shape != value["shape"]
            or encode(parsed) != encode(value["value"])
        ):
            return FactResolution(None, "column_value_unit_mismatch")
    return FactResolution(
        {
            **fact,
            "table_values": fact["value"],
            "shape": value["shape"],
            "value": value["value"],
            "selected_module_count": count,
            "selected_column": column,
        }
    )


def resolve_fact(
    fact: Object, context: FactContext, use: FactUse = "numeric"
) -> FactResolution:
    if fact.get("source") is None or fact.get("status") not in ("typed", "conditional"):
        return FactResolution(None, "cited_fact_required")
    qualifier = fact.get("qualifier")
    source = cast(Object, fact["source"])
    generic_bank_power = (
        use == "bank_rated_dc_power" and source.get("figure_key") == "rated_power_w"
    )
    if generic_bank_power and (
        not isinstance(qualifier, dict)
        or qualifier.get("scope") != "battery_system"
        or qualifier.get("module_count_basis") != "columns"
    ):
        return FactResolution(None, "system_power_basis_required")
    match: Object = {}
    if qualifier not in (None, "", {}, []):
        if not isinstance(qualifier, dict):
            return FactResolution(None, "uninterpreted_condition")
        q = qualifier
        if use == "nominal_ac_output":
            valid = q == {
                "quantity_kind": "rated_active_power",
                "scope": "on_grid_ac_output",
            }
        elif use in ("grid_output_ceiling", "grid_input_ceiling"):
            excluded = q.get("excluded_countries")
            conditions = {k: v for k, v in q.items() if k != "excluded_countries"}
            valid = fact.get("quantity") in (
                "active_power",
                "apparent_power",
            ) and conditions == {
                "quantity_kind": "maximum_" + str(fact["quantity"]),
                "scope": "on_grid_ac_output"
                if use == "grid_output_ceiling"
                else "on_grid_ac_input",
            }
            if "excluded_countries" in q:
                valid = (
                    valid
                    and use == "grid_input_ceiling"
                    and isinstance(excluded, list)
                    and all(
                        isinstance(code, str) and re.fullmatch(r"[A-Z]{2}", code)
                        for code in excluded
                    )
                )
                if valid:
                    if context.country_code is None:
                        return FactResolution(None, "country_required")
                    if context.country_code in cast(list[str], excluded):
                        return FactResolution(None, "country_outside_condition")
                    match["country_code"] = context.country_code
        elif use == "battery_terminal_power":
            valid = q == {
                "quantity_kind": "maximum_active_power",
                "scope": "inverter_battery_terminals_total",
            }
        elif use == "pv_nameplate_limit":
            valid = q == {
                "quantity_kind": "maximum_pv_nameplate_power",
                "scope": "pv_array",
                "rating_basis": "STC",
            }
        elif use in ("bank_rated_dc_power", "battery_operating_voltage"):
            allowed = {
                "quantity_kind",
                "scope",
                "module_count_basis",
                "battery_module",
                "control_module",
            }
            kind = "rated" if use == "bank_rated_dc_power" else "operating_range"
            valid = (
                not set(q) - allowed
                and q.get("quantity_kind") == kind
                and q.get("scope") == "battery_system"
                and q.get("module_count_basis") == "columns"
            )
            if valid and "battery_module" in q:
                battery = context.products.get(
                    context.selection.battery_product_id or 0
                )
                valid = battery is not None and q["battery_module"] == battery["model"]
            if valid and "control_module" in q:
                valid = any(
                    q["control_module"] == context.products[pid]["model"]
                    for pid in context.selection.accessory_product_ids
                    if pid in context.products
                )
        elif use in ("normal_charge_current", "normal_discharge_current"):
            allowed = {
                "quantity_kind",
                "scope",
                "direction",
                "ports",
                "source_expression",
                "connection",
                "module_count_min",
                "module_count_max",
                "operating_temperature_c",
            }
            direction = "charge" if use == "normal_charge_current" else "discharge"
            valid = (
                not set(q) - allowed
                and q.get("quantity_kind", "maximum") == "maximum"
                and q.get("direction", direction) == direction
                and q.get("scope") in ("series_stack", "per_battery_port")
            )
            if valid and q["scope"] == "per_battery_port":
                if "connection" in q:
                    valid = (
                        q["connection"] == "one_stack_per_port"
                        and context.selection.parallel_stacks == 1
                    )
                if "ports" in q:
                    ports = q["ports"]
                    valid = (
                        valid
                        and isinstance(ports, list)
                        and all(isinstance(p, str) and p for p in ports)
                    )
                    if valid:
                        valid = (
                            len(set(cast(list[str], ports)))
                            == len(cast(list[str], ports))
                            and len(cast(list[str], ports))
                            == context.battery_port_count
                            and context.battery_port_id in cast(list[str], ports)
                        )
                if "source_expression" in q:
                    valid = valid and isinstance(q["source_expression"], str)
            elif valid:
                valid = (
                    context.selection.parallel_stacks == 1
                    and "ports" not in q
                    and "connection" not in q
                    and "source_expression" not in q
                )
            for key, compare in (
                ("module_count_min", "min"),
                ("module_count_max", "max"),
            ):
                if key in q:
                    bound = q[key]
                    count = context.selection.modules_per_stack
                    if type(bound) is not int or count is None or bound < 1:
                        valid = False
                    elif (compare == "min" and count < bound) or (
                        compare == "max" and count > bound
                    ):
                        return FactResolution(None, "module_count_outside_condition")
            if "operating_temperature_c" in q:
                limits = q["operating_temperature_c"]
                if (
                    not isinstance(limits, list)
                    or len(limits) != 2
                    or not all(_finite(v) for v in limits)
                    or cast(float, limits[0]) > cast(float, limits[1])
                ):
                    valid = False
                elif context.battery_temperature_c is None:
                    return FactResolution(
                        None, "battery_operating_temperature_required"
                    )
                elif (
                    not cast(float, limits[0])
                    <= context.battery_temperature_c
                    <= cast(float, limits[1])
                ):
                    return FactResolution(None, "battery_temperature_outside_condition")
                else:
                    match["battery_temperature_c"] = context.battery_temperature_c
        else:
            valid = False
        if not valid:
            return FactResolution(None, "uninterpreted_condition")
        match = {**match, "qualifier": qualifier}
    configured = _configured_column(fact, context.selection.modules_per_stack)
    if configured.fact is None:
        return configured
    result = configured.fact
    if (
        generic_bank_power
        and result.get("selected_module_count") != context.selection.modules_per_stack
    ):
        return FactResolution(None, "module_count_column_required")
    if match:
        result = {**result, "condition_match": match}
    return FactResolution(result)
