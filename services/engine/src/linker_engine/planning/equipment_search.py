"""Search current Woo configurations with one shared qualification domain."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from .canonical import Json, Object, digest, encode
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_requirements import EquipmentRequirements
from .equipment_search_limits import EquipmentSearchLimits
from .equipment_search_space import EquipmentSearchSpace


def candidate_record(
    key: str, value: Object, assessment: Object, store: EquipmentCandidateStore
) -> Object:
    checks = cast(list[Object], assessment["checks"])
    return {
        "id": digest(encode(value)),
        key: value,
        "status": assessment["overall_status"],
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
) -> Object:
    space = EquipmentSearchSpace(basis, limits, checkpoint)
    candidates: list[Json] = [
        candidate_record("selection", value, assessment, store)
        for value, assessment in space.options(
            EquipmentRequirements.from_inputs(inputs), inputs
        )
    ]
    return space.result(
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
