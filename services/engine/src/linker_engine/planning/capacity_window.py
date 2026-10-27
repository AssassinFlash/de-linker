"""A Woo usable-energy rating may define an explicitly chosen reference model.

This does not resolve the rating conditions or infer temperature/rate/age curves.
The already-usable rating is not nominal energy and is not reduced by DOD again.
See the retained SAM/manufacturer evidence in FACT-INTAKE.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Annotated, Literal, cast

from pydantic import Field, model_validator

from .battery_assembly import battery_assembly
from .canonical import Object
from .energy_inputs import Document
from .equipment_evidence import EquipmentEvidence
from .equipment_inputs import EquipmentSelection
from .errors import EvidenceMissing, InvalidInput

REFERENCE_CAPACITY = "manufacturer_reference_constant_window_v1"


class ReferenceConditions(Document):
    life_state: Literal["beginning_of_life"]
    depth_of_discharge_pct: Annotated[float, Field(gt=0, le=100, allow_inf_nan=False)]
    charge_rate_c: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    discharge_rate_c: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    test_temperature_c: Annotated[
        list[Annotated[float, Field(allow_inf_nan=False)]],
        Field(min_length=2, max_length=2),
    ]

    @model_validator(mode="after")
    def ordered_temperature(self) -> ReferenceConditions:
        if self.test_temperature_c[0] > self.test_temperature_c[1]:
            raise ValueError("reference temperature range must be ordered")
        return self


class ReferenceQualifier(Document):
    quantity_kind: Literal["rated_usable_energy"]
    scope: Literal["battery_system", "battery_module"]
    rating_conditions: ReferenceConditions
    configuration_dependent: bool
    source_text: dict[str, str]

    @model_validator(mode="after")
    def bilingual_source(self) -> ReferenceQualifier:
        if set(self.source_text) != {"en", "de"} or any(
            not value.strip() for value in self.source_text.values()
        ):
            raise ValueError("original reference conditions are required")
        return self


@dataclass(frozen=True)
class CapacityWindow:
    window_kwh: float
    source_facts: Object


def capacity_window(
    selection: EquipmentSelection,
    usable_assessment: Object | None,
    evidence: EquipmentEvidence,
    choice: str | None,
) -> CapacityWindow:
    if choice != REFERENCE_CAPACITY:
        if (
            usable_assessment is not None
            and usable_assessment.get("status") == "satisfied"
            and type(usable_assessment.get("actual")) in (int, float)
        ):
            return CapacityWindow(float(cast(float, usable_assessment["actual"])), {})
        raise EvidenceMissing(
            "woo_dc_fact:usable_energy_and_complete_voltage_window",
            product_id=selection.battery_product_id,
            constraint_id="usable_energy_and_complete_voltage_window",
        )

    pid = selection.battery_product_id
    assert pid is not None  # Selected single-stack topology was already checked.
    compiled = evidence.compiled(pid)
    assembly = battery_assembly(compiled)
    if (
        assembly is None
        or assembly["sales_unit_kind"] not in ("battery_system", "battery_module")
        or selection.parallel_stacks != 1
    ):
        raise EvidenceMissing("capacity_reference:sales_unit", product_id=pid)
    system = assembly["sales_unit_kind"] == "battery_system"
    modules = selection.modules_per_stack
    if modules is None or (system and assembly["fixed_modules_per_stack"] != modules):
        raise EvidenceMissing("capacity_reference:configuration", product_id=pid)
    key = "system_usable_energy_kwh" if system else "module_energy_kwh_usable"
    fact = cast(Object, compiled["facts"]).get(key)
    if (
        not isinstance(fact, dict)
        or fact.get("source") is None
        or fact.get("status") not in ("typed", "conditional")
        or fact.get("quantity") != "energy"
        or fact.get("shape") != "scalar"
        or type(fact.get("value")) not in (int, float)
        or cast(float, fact["value"]) < 0
    ):
        raise EvidenceMissing("capacity_reference:cited_usable_energy", product_id=pid)
    qualifier = fact.get("qualifier")
    try:
        rating = ReferenceQualifier.read(qualifier)
    except InvalidInput as error:
        raise EvidenceMissing(
            "capacity_reference:uninterpreted_conditions",
            product_id=pid,
            constraint_id="capacity_reference_conditions",
        ) from error
    if rating.scope != ("battery_system" if system else "battery_module"):
        raise EvidenceMissing("capacity_reference:quantity_scope", product_id=pid)
    multiplier = 1 if system else modules
    window = float(cast(float, fact["value"])) * multiplier
    if not math.isfinite(window):
        raise EvidenceMissing("capacity_reference:finite_window", product_id=pid)
    return CapacityWindow(
        window,
        {
            f"{pid}.{key}": fact,
            "capacity_window_assumption": {
                "basis": REFERENCE_CAPACITY,
                "reference_fact_id": f"{pid}.{key}",
                "window_kwh": window,
                "published_usable_energy_kwh": fact["value"],
                "sales_unit_multiplier": multiplier,
                "rating_conditions_status": "not_established",
                "internal_window_mapping": "published_usable_energy_as_model_window",
                "conversion_and_storage_losses": "separate_declared_scenario",
                "unmodelled_capacity_effects": [
                    "age",
                    "temperature",
                    "charge_discharge_rate",
                ],
                "manufacturer_qualifier": qualifier,
            },
        },
    )
