"""Bind a forward-only series scenario to the saved roof and Woo evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from .canonical import Object
from .equipment_assessment import selection_products
from .equipment_facts import compile_facts, compile_product
from .equipment_inputs import EquipmentSelection
from .errors import InvalidInput
from .pv_iv_model import derive_iv_model
from .pv_string_assessment import assess_pv_strings
from .pv_string_inputs import PvString, PvStringPlan


@dataclass(frozen=True)
class SeriesPlan:
    strings: tuple[PvString, ...]
    parameters: Object
    model: Object
    limits: dict[int, tuple[tuple[float, float], float]]
    inverter_facts: Object
    assessment: Object


def _value(facts: Object, key: str, quantity: str, tracker: int) -> Any:
    item = facts.get(key)
    if (
        not isinstance(item, dict)
        or item.get("status") != "typed"
        or item.get("quantity") != quantity
        or not item.get("source")
        or item.get("qualifier") not in (None, "", {}, [])
    ):
        raise InvalidInput(
            "the cited inverter " + key + " is required for this scenario"
        )
    value = item.get("value")
    if item.get("shape") == "ordered_values":
        if not isinstance(value, list) or tracker > len(value):
            raise InvalidInput("the cited tracker " + key + " is missing")
        row = value[tracker - 1]
        if not isinstance(row, dict):
            raise InvalidInput("the cited tracker " + key + " is invalid")
        value = row.get("value")
    return value


def series_plan(inputs: Object, basis: Object) -> SeriesPlan:
    """Only a single selected inverter and one string per tracker are supported.

    Evidence is the existing frozen Woo equipment basis plus its retained module
    reference. The physical connector map, shared-tracker parallel curves and
    manufacturer operation are not inferred from a product or port count.
    """
    if (
        inputs.get("pv_plant_string_plan") is not None
        or inputs.get("equipment_plant") is not None
    ):
        raise InvalidInput(
            "the series scenario currently requires one selected inverter"
        )
    selection = EquipmentSelection.read(inputs.get("equipment_selection"))
    plan = PvStringPlan.read(inputs.get("pv_string_plan"))
    if not plan.strings:
        raise InvalidInput("assign roof modules to at least one PV string")
    if len({row.mppt for row in plan.strings}) != len(plan.strings):
        raise InvalidInput("the series scenario requires one string per tracker")
    products = selection_products(selection, basis)
    raw_module = basis.get("pv_module_inputs")
    if not isinstance(raw_module, dict) or not isinstance(
        raw_module.get("electrical_product"), dict
    ):
        raise InvalidInput("the cited Woo module I-V source is required")
    assessment = assess_pv_strings(inputs, basis)
    checks = cast(list[dict[str, Any]], assessment["checks"])
    coverage = next(row for row in checks if row["id"] == "pv_layout_coverage")
    if coverage["status"] != "satisfied":
        raise InvalidInput(
            "the series scenario requires every included module assigned"
        )
    model = derive_iv_model(compile_facts(cast(Object, raw_module["electrical_product"])))
    if model["status"] != "available":
        raise InvalidInput("the cited module cannot produce an admissible I-V fit")
    inverter = cast(
        Object, compile_product(products[selection.inverter_product_id])["facts"]
    )
    limits: dict[int, tuple[tuple[float, float], float]] = {}
    for string in plan.strings:
        count = _value(inverter, "n_mppt", "count", string.mppt)
        window = _value(inverter, "mppt_voltage_range_v", "voltage", string.mppt)
        current = _value(inverter, "mppt_max_current_a", "current", string.mppt)
        if (
            not isinstance(count, (int, float))
            or string.mppt > count
            or not isinstance(window, list)
            or len(window) != 2
            or not all(isinstance(value, (int, float)) for value in window)
            or not isinstance(current, (int, float))
        ):
            raise InvalidInput(
                "the selected tracker needs a cited operating window and current"
            )
        limits[string.mppt] = ((float(window[0]), float(window[1])), float(current))
    return SeriesPlan(
        tuple(plan.strings),
        cast(Object, model["parameters"]),
        model,
        limits,
        {
            key: inverter[key]
            for key in ("n_mppt", "mppt_voltage_range_v", "mppt_max_current_a")
        },
        assessment,
    )
