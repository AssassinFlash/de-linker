"""One request-local Woo search domain and work budget for single/plant searches.

Source facts and qualification are shared. Reusing a unit's identical demand
avoids reassessing the same hardware when the plant names another instance.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterator
from math import inf
from typing import Any, cast

from .canonical import Json, Object, digest, encode
from .equipment_assessment import (
    AC_OUTPUT_KEYS,
    DC_AC_RATIO_MIDPOINT,
    assess_equipment,
)
from .equipment_evidence import EquipmentEvidence
from .equipment_inputs import EquipmentSelection
from .equipment_requirements import EquipmentRequirements
from .equipment_search_limits import EquipmentSearchLimits

# The feed's normalized `pa_application` facet values per project application.
# `home` is the manufacturers' residential filing (2026-11-14 production Woo:
# 55 EN/55 DE home products, 30/30 commercial).
PRODUCT_APPLICATIONS: dict[str, str] = {"home": "residential", "commercial": "commercial"}


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
        self.application_excluded: set[int] = set()
        self.included: list[dict[str, Any]] = []
        for source_battery in self.batteries:
            pid = source_battery["canonical_product_id"]
            if self.evidence.sales_unit(pid) in {"battery_module", "battery_system"}:
                self.included.append(source_battery)
                stacks_max = self.evidence.scalar(pid, "stacks_parallel_max", "count")
                if (
                    stacks_max is None
                    or stacks_max < 1
                    or stacks_max != int(stacks_max)
                ):
                    # Single stack is the documented default, not an invented
                    # parallel maximum. The gap keeps the missing fact visible.
                    self.gaps["stacks_parallel_max_missing"] += 1
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
            named = PRODUCT_APPLICATIONS.get(str(converter.get("application") or ""))
            if requirements.application is not None and named not in (
                None,
                requirements.application,
            ):
                # A manufacturer-filed application that contradicts the stated
                # project application excludes the converter; an unknown filing
                # stays in the candidate list rather than being dropped.
                if converter_id not in self.application_excluded:
                    self.application_excluded.add(converter_id)
                    self.gaps["converter_application_mismatch"] += 1
                    self.excluded_products.append(
                        {
                            "product_id": converter_id,
                            "reason": "converter_application_mismatch",
                        }
                    )
                continue
            options: list[dict[str, Any] | None] = (
                [None] if no_battery else [*self.included]
            )
            for battery in options:
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
                if pair is not None and not pair.released:
                    continue
                if not self.available():
                    break
                if pair is not None:
                    assert battery_id is not None
                    minimum = self.evidence.scalar(
                        battery_id, "modules_per_stack_min", "count"
                    )
                    maximum = self.evidence.scalar(
                        battery_id, "modules_per_stack_max", "count"
                    )
                    stack_low = (
                        int(minimum)
                        if minimum is not None
                        else 1
                        if maximum is not None
                        and self.evidence.sales_unit(battery_id) == "battery_module"
                        else None
                    )
                    bounds = ([pair.modules] if pair.modules else []) + (
                        [(stack_low, int(maximum))]
                        if stack_low is not None and maximum is not None
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

                stacks_max = (
                    self.evidence.scalar(battery_id, "stacks_parallel_max", "count")
                    if battery_id is not None
                    else None
                )
                # Only a cited parallel-stack maximum widens the domain; stacks
                # ascend in the outer loop so single-stack coverage is spent
                # first when the budget runs out.
                stacks_domain: range = (
                    range(1, int(stacks_max) + 1)
                    if battery_id is not None
                    and stacks_max is not None
                    and stacks_max >= 1
                    and stacks_max == int(stacks_max)
                    else range(1, 2)
                )

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
                # The customer-visible combination is inverter, battery and
                # documented modules per stack. Parallel-stack levels of one
                # combination are assessed in ascending order and the
                # combination yields one candidate: the first stack level that
                # satisfies, or the smallest one as its failing representative.
                # A failing representative is only held back while a further
                # cited stack level could still replace it; with a single
                # stack level the candidate leaves immediately, preserving
                # first-coverage ordering under a tight budget.
                combination_representative: dict[
                    tuple[int, int | None, int | None], tuple[Object, Object]
                ] = {}
                combination_satisfied: set[tuple[int, int | None, int | None]] = set()
                escalate = len(stacks_domain) > 1
                for stacks in stacks_domain:
                    if self.exhausted:
                        break
                    for count in counts:
                        if not self.available():
                            break
                        identities = {converter_id, *accessory_ids}
                        if battery_id is not None:
                            identities.add(battery_id)
                        selection = EquipmentSelection(
                            **{
                                key: value
                                for key, value in requirements.model_dump().items()
                                if key in EquipmentSelection.model_fields
                            },
                            inverter_product_id=converter_id,
                            battery_product_id=battery_id,
                            modules_per_stack=count,
                            parallel_stacks=stacks if battery else None,
                            accessory_product_ids=sorted(accessory_ids),
                            product_revisions={
                                str(pid): self.evidence.products[pid][
                                    "product_revision"
                                ]
                                for pid in identities
                            },
                        )
                        value = cast(Object, selection.model_dump(mode="json"))
                        identity = digest(encode(value))
                        if identity in seen:
                            continue
                        seen.add(identity)
                        combination = (converter_id, battery_id, count)
                        if combination in combination_satisfied:
                            continue
                        assessment = assess_equipment(
                            {**inputs, "equipment_selection": value},
                            self.basis,
                            evidence=self.evidence,
                        )
                        if cast(str, assessment["overall_status"]) == "satisfied":
                            combination_satisfied.add(combination)
                            combination_representative.pop(combination, None)
                            yield value, assessment
                        elif not escalate:
                            yield value, assessment
                        elif combination not in combination_representative:
                            combination_representative[combination] = (
                                value,
                                assessment,
                            )
                yield from combination_representative.values()

    def inverter_ac_kw(self, product_id: int) -> float | None:
        fields = cast(dict[str, Any], self.evidence.compiled(product_id)["facts"])
        for key in AC_OUTPUT_KEYS:
            found = fields.get(key)
            if (
                found
                and found["status"] == "typed"
                and found["shape"] == "scalar"
                and found["quantity"] == "active_power"
            ):
                return float(cast(float, found["value"]))
        return None

    def ratio_deviation(self, selection: Object) -> float:
        pv = cast(float | None, selection.get("pv_dc_kw"))
        ac = self.inverter_ac_kw(int(cast(int, selection["inverter_product_id"])))
        if pv is None or pv <= 0 or ac is None or ac <= 0:
            return inf
        return abs(pv / ac - DC_AC_RATIO_MIDPOINT)

    def combination_fitness(
        self, candidate: Json
    ) -> tuple[int, float, int, int, int, int, str]:
        record = cast(Object, candidate)
        value = cast(Object, record.get("selection") or record.get("plant") or {})
        selections = (
            [value]
            if "selection" in record
            else [
                cast(Object, unit["selection"])
                for unit in cast(list[Object], value.get("units", []))
            ]
        )
        # After the canonical product id, the documented assembly (smallest
        # stack level, then module count) keeps the order total and stable;
        # the candidate digest is the last resort, never the visible order.
        return (
            0 if record["status"] == "satisfied" else 1,
            max((self.ratio_deviation(row) for row in selections), default=inf),
            int(cast(int, record["unresolved_checks"])),
            min(int(cast(int, row["inverter_product_id"])) for row in selections),
            min(int(cast(int, row["parallel_stacks"] or 0)) for row in selections),
            min(int(cast(int, row["modules_per_stack"] or 0)) for row in selections),
            str(record["id"]),
        )

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
            "candidates": sorted(candidates, key=self.combination_fitness),
            "qualified_count": sum(
                row["status"] == "satisfied" for row in cast(list[Object], candidates)
            ),
            "ranking": "dc_ac_proximity_then_unresolved_then_product_and_module_count",
            "display_order": "ranking_then_canonical_product_and_documented_module_count",
        }
