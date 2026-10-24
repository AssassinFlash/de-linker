"""Enumerate the declared Woo topology domain before any ranking.

Unlisted pairs are evidence gaps, not proven incompatibility. The explicit
work budget counts pairing and assessment work, and exhaustion remains visible.
Single-converter searches never claim to exhaust parallel or integrated designs.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from typing import Any, cast

from .canonical import Json, Object, digest, encode
from .equipment_assessment import assess_equipment
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_evidence import EquipmentEvidence
from .equipment_inputs import EquipmentSelection
from .equipment_requirements import EquipmentRequirements
from .equipment_search_limits import EquipmentSearchLimits


def search_equipment(
    inputs: Object,
    basis: Object,
    limits: EquipmentSearchLimits,
    store: EquipmentCandidateStore,
    checkpoint: Callable[[], None],
) -> Object:
    requirements = EquipmentRequirements.from_inputs(inputs)
    evidence = EquipmentEvidence(basis)
    converters = sorted(
        (
            row
            for row in evidence.rows
            if row["device_class"] == "inverters"
            or "ac_output_kw_nominal" in row["figures"]
        ),
        key=lambda row: row["canonical_product_id"],
    )
    batteries = sorted(
        (
            row
            for row in evidence.rows
            if row["device_class"] in {"home-storage", "battery-systems"}
        ),
        key=lambda row: row["canonical_product_id"],
    )
    gaps: Counter[str] = Counter()
    excluded_products: list[Json] = []
    included: list[dict[str, Any]] = []
    for source_battery in batteries:
        pid = source_battery["canonical_product_id"]
        if evidence.sales_unit(pid) in {"battery_module", "battery_system"}:
            included.append(source_battery)
        else:
            gaps["sales_unit_evidence_missing"] += 1
            excluded_products.append(
                {"product_id": pid, "reason": "sales_unit_evidence_missing"}
            )
    candidates: list[Json] = []
    seen: set[str] = set()
    work = 0
    exhausted = False
    no_battery = (
        requirements.required_usable_kwh == 0
        and requirements.required_discharge_ac_kw == 0
    )

    def available() -> bool:
        nonlocal work, exhausted
        checkpoint()
        if work >= limits.work_budget:
            exhausted = True
            return False
        work += 1
        return True

    for converter in converters:
        if exhausted:
            break
        converter_id = converter["canonical_product_id"]
        if evidence.sales_unit(converter_id) == "integrated_system":
            gaps["integrated_topology_not_assessed"] += 1
            continue
        options: list[dict[str, Any] | None] = [None] if no_battery else [*included]
        for battery in options:
            if not available():
                break
            battery_id = battery["canonical_product_id"] if battery else None
            counts: range | tuple[None] = (None,)
            pair = (
                evidence.contract.pair(
                    converter["model"],
                    battery["model"],
                    inverter_id=converter_id,
                    battery_id=battery_id,
                )
                if battery
                else None
            )
            if pair is not None:
                if not pair.released:
                    gaps["pair_release_not_established"] += 1
                    continue
                assert battery_id is not None
                minimum = evidence.scalar(battery_id, "modules_per_stack_min", "count")
                maximum = evidence.scalar(battery_id, "modules_per_stack_max", "count")
                bounds = ([pair.modules] if pair.modules else []) + (
                    [(int(minimum), int(maximum))]
                    if minimum is not None and maximum is not None
                    else []
                )
                if bounds:
                    low, high = max(r[0] for r in bounds), min(r[1] for r in bounds)
                    if low > high:
                        gaps["documented_count_ranges_disjoint"] += 1
                        continue
                    if low < 1 or high > 9007199254740991:
                        gaps["configuration_count_outside_wire_domain"] += 1
                    else:
                        counts = range(low, high + 1)
                else:
                    gaps["configuration_count_not_established"] += 1

            accessories = list(pair.accessories) if pair else []
            for kind in (
                "meter",
                *(("backup",) if requirements.operating_mode == "backup" else ()),
            ):
                for row in evidence.contract.requirements(
                    converter["model"], kind, inverter_id=converter_id
                ):
                    if not row.included and row.phase in (
                        None,
                        requirements.grid_phase,
                    ):
                        accessories.extend(row.accessories)
            accessory_ids: set[int] = set()
            for accessory in accessories:
                matches = [
                    row
                    for row in evidence.rows
                    if (
                        (
                            accessory.product_id is None
                            and re.search(accessory.model, row["model"])
                        )
                        or row["canonical_product_id"] == accessory.product_id
                    )
                ]
                if len(matches) == 1:
                    accessory_ids.add(matches[0]["canonical_product_id"])
            for count in counts:
                if not available():
                    break
                identities = {converter_id, *accessory_ids}
                if battery_id is not None:
                    identities.add(battery_id)
                # The supported template has one external battery assembly.
                # No undocumented parallel count is invented to satisfy demand.
                selection = EquipmentSelection(
                    **requirements.model_dump(),
                    inverter_product_id=converter_id,
                    battery_product_id=battery_id,
                    modules_per_stack=count,
                    parallel_stacks=1 if battery else None,
                    accessory_product_ids=sorted(accessory_ids),
                    product_revisions={
                        str(pid): evidence.products[pid]["product_revision"]
                        for pid in identities
                    },
                )
                value = cast(Object, selection.model_dump(mode="json"))
                identity = digest(encode(value))
                if identity in seen:
                    continue
                seen.add(identity)
                assessment = assess_equipment(
                    {**inputs, "equipment_selection": value}, basis, evidence=evidence
                )
                status = assessment["overall_status"]
                candidates.append(
                    {
                        "id": identity,
                        "selection": value,
                        "status": status,
                        "assessment_sha256": store.put(assessment),
                        "violated_checks": sum(
                            row["status"] == "violated"
                            for row in cast(list[Object], assessment["checks"])
                        ),
                        "unresolved_checks": sum(
                            row["status"] == "unresolved"
                            for row in cast(list[Object], assessment["checks"])
                        ),
                    }
                )
    return {
        "completion": "budget_exhausted" if exhausted else "exhausted_supported_domain",
        "work_used": work,
        "work_budget": limits.work_budget,
        "coverage": {
            "template": "one_converter_one_external_battery_assembly",
            "converter_products": len(converters),
            "battery_products": len(batteries),
            "excluded_products": excluded_products,
            "gaps": dict(gaps),
            "unassessed_templates": [
                "parallel_converters",
                "multiple_battery_ports",
                "integrated_systems",
            ],
        },
        "products": [
            {
                k: row[k]
                for k in (
                    "canonical_product_id",
                    "model",
                    "brand",
                    "sku",
                    "product_revision",
                )
            }
            for row in sorted(
                evidence.rows, key=lambda row: row["canonical_product_id"]
            )
        ],
        "candidates": candidates,
        "qualified_count": sum(
            row["status"] == "satisfied" for row in cast(list[Object], candidates)
        ),
        "ranking": "not_performed_before_qualification",
        "display_order": "canonical_product_and_documented_module_count",
    }
