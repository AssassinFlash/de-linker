"""One request-local Woo search domain and work budget for single/plant searches.

Source facts and qualification are shared. Reusing a unit's identical demand
avoids reassessing the same hardware when the plant names another instance.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterator
from typing import Any, cast

from .canonical import Json, Object, digest, encode
from .equipment_assessment import assess_equipment
from .equipment_evidence import EquipmentEvidence
from .equipment_inputs import EquipmentSelection
from .equipment_requirements import EquipmentRequirements
from .equipment_search_limits import EquipmentSearchLimits


class EquipmentSearchSpace:
    def __init__(
        self,
        basis: Object,
        limits: EquipmentSearchLimits,
        checkpoint: Callable[[], None],
    ) -> None:
        self.basis, self.limits, self.checkpoint = basis, limits, checkpoint
        self.evidence = EquipmentEvidence(basis)
        self.work = 0
        self.exhausted = False
        self.converters = sorted(
            (
                row
                for row in self.evidence.rows
                if row["device_class"] == "inverters"
                or "ac_output_kw_nominal" in row["figures"]
            ),
            key=lambda row: row["canonical_product_id"],
        )
        self.batteries = sorted(
            (
                row
                for row in self.evidence.rows
                if row["device_class"] in {"home-storage", "battery-systems"}
            ),
            key=lambda row: row["canonical_product_id"],
        )
        self.gaps: Counter[str] = Counter()
        self.excluded_products: list[Json] = []
        self.included: list[dict[str, Any]] = []
        for source_battery in self.batteries:
            pid = source_battery["canonical_product_id"]
            if self.evidence.sales_unit(pid) in {"battery_module", "battery_system"}:
                self.included.append(source_battery)
            else:
                self.gaps["sales_unit_evidence_missing"] += 1
                self.excluded_products.append(
                    {"product_id": pid, "reason": "sales_unit_evidence_missing"}
                )

    def available(self, work_units: int = 1) -> bool:
        self.checkpoint()
        if self.work + work_units > self.limits.work_budget:
            self.exhausted = True
            return False
        self.work += work_units
        return True

    def options(
        self, requirements: EquipmentRequirements, inputs: Object
    ) -> Iterator[tuple[Object, Object]]:
        seen: set[str] = set()
        no_battery = (
            requirements.required_usable_kwh == 0
            and requirements.required_discharge_ac_kw == 0
        )
        for converter in self.converters:
            if self.exhausted:
                break
            converter_id = converter["canonical_product_id"]
            if self.evidence.sales_unit(converter_id) == "integrated_system":
                self.gaps["integrated_topology_not_assessed"] += 1
                continue
            options: list[dict[str, Any] | None] = (
                [None] if no_battery else [*self.included]
            )
            for battery in options:
                if not self.available():
                    break
                battery_id = battery["canonical_product_id"] if battery else None
                counts: range | tuple[None] = (None,)
                pair = (
                    self.evidence.contract.pair(
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
                        self.gaps["pair_release_not_established"] += 1
                        continue
                    assert battery_id is not None
                    minimum = self.evidence.scalar(
                        battery_id, "modules_per_stack_min", "count"
                    )
                    maximum = self.evidence.scalar(
                        battery_id, "modules_per_stack_max", "count"
                    )
                    bounds = ([pair.modules] if pair.modules else []) + (
                        [(int(minimum), int(maximum))]
                        if minimum is not None and maximum is not None
                        else []
                    )
                    if bounds:
                        low, high = max(r[0] for r in bounds), min(r[1] for r in bounds)
                        if low > high:
                            self.gaps["documented_count_ranges_disjoint"] += 1
                            continue
                        if low < 1 or high > 9007199254740991:
                            self.gaps["configuration_count_outside_wire_domain"] += 1
                        else:
                            counts = range(low, high + 1)
                    else:
                        self.gaps["configuration_count_not_established"] += 1

                accessories = list(pair.accessories) if pair else []
                for kind in (
                    "meter",
                    *(("backup",) if requirements.operating_mode == "backup" else ()),
                ):
                    for row in self.evidence.contract.requirements(
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
                        for row in self.evidence.rows
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
                    if not self.available():
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
                            str(pid): self.evidence.products[pid]["product_revision"]
                            for pid in identities
                        },
                    )
                    value = cast(Object, selection.model_dump(mode="json"))
                    identity = digest(encode(value))
                    if identity in seen:
                        continue
                    seen.add(identity)
                    assessment = assess_equipment(
                        {**inputs, "equipment_selection": value},
                        self.basis,
                        evidence=self.evidence,
                    )
                    yield value, assessment

    def result(self, candidates: list[Json], coverage: Object) -> Object:
        return {
            "completion": "budget_exhausted"
            if self.exhausted
            else "exhausted_supported_domain",
            "work_used": self.work,
            "work_budget": self.limits.work_budget,
            "coverage": {
                "converter_products": len(self.converters),
                "battery_products": len(self.batteries),
                "excluded_products": self.excluded_products,
                "gaps": dict(self.gaps),
                **coverage,
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
                    self.evidence.rows, key=lambda row: row["canonical_product_id"]
                )
            ],
            "candidates": candidates,
            "qualified_count": sum(
                row["status"] == "satisfied" for row in cast(list[Object], candidates)
            ),
            "ranking": "not_performed_before_qualification",
            "display_order": "canonical_product_and_documented_module_count",
        }
