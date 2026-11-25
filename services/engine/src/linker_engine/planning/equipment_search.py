"""Search current Woo configurations with one shared qualification domain."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any, cast

from .backup_demand import BackupDemand
from .canonical import Json, Object, digest, encode
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_requirements import EquipmentRequirements
from .equipment_search_limits import EquipmentSearchLimits
from .equipment_search_space import EquipmentSearchSpace


def candidate_record(
    key: str, value: Object, assessment: Object, store: EquipmentCandidateStore
) -> Object:
    checks = cast(list[Object], assessment["checks"])
    usable: Json
    if key == "plant":
        battery_units = {
            unit["id"]
            for unit in cast(list[dict[str, Any]], value["units"])
            if unit["selection"]["battery_product_id"] is not None
        }
        capacities = {
            row["unit_id"]: row["actual"]
            for row in checks
            if row.get("semantic_id") == "usable_energy"
            and row["unit_id"] in battery_units
        }
        usable = (
            float(sum((Decimal(str(n)) for n in capacities.values()), Decimal(0)))
            if battery_units
            and battery_units == capacities.keys()
            and all(isinstance(n, (int, float)) for n in capacities.values())
            else None
        )
    else:
        usable = next(
            (row["actual"] for row in checks if row["id"] == "usable_energy"), None
        )
    converters = [
        row["actual"]
        for row in checks
        if row.get("semantic_id", row["id"]) == "converter_identity"
    ]
    nominal_ac_kw = (
        sum(cast(list[float], converters))
        if converters
        and all(isinstance(kw, (int, float)) and kw > 0 for kw in converters)
        else None
    )
    return {
        "nominal_ac_kw": nominal_ac_kw,
        "id": digest(encode(value)),
        key: value,
        "status": assessment["overall_status"],
        "usable_energy_kwh": usable,
        "assessment_sha256": store.put(assessment),
        "violated_checks": sum(row["status"] == "violated" for row in checks),
        "unresolved_checks": sum(row["status"] == "unresolved" for row in checks),
    }


def search_equipment(
    inputs: Object,
    basis: Object,
    limits: EquipmentSearchLimits,
    store: EquipmentCandidateStore,
    checkpoint: Callable[[], None],
    *,
    constrain_models: bool = False,
) -> Object:
    space = EquipmentSearchSpace(basis, limits, checkpoint)
    candidates: list[Json] = [
        candidate_record("selection", value, assessment, store)
        for value, assessment in space.options(
            EquipmentRequirements.from_inputs(inputs),
            inputs,
            constrain_models=constrain_models,
        )
    ]
    result = space.result(
        candidates,
        {
            "template": "one_converter_one_external_battery_assembly",
            "unassessed_templates": [
                "parallel_converters",
                "multiple_battery_ports",
                "integrated_systems",
            ],
        },
    )
    backup = BackupDemand.from_inputs(inputs, complete=True)
    if backup is not None:
        result["backup_demand"] = backup.summary()
    return result
