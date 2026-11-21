"""One request-local Woo search domain and work budget for single/plant searches.

Source facts and qualification are shared. Reusing a unit's identical demand
avoids reassessing the same hardware when the plant names another instance.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterator
from typing import Any, cast

from pydantic import TypeAdapter, ValidationError

from .canonical import Json, Object, digest, encode
from .equipment_assessment import assess_equipment
from .equipment_evidence import EquipmentEvidence
from .equipment_inputs import Count, EquipmentSelection, EquipmentUse
from .equipment_requirements import EquipmentRequirements
from .equipment_search_limits import EquipmentSearchLimits
from .errors import InvalidInput

# The feed's normalized `pa_application` facet values per project application.
# `home` is the manufacturers' residential filing (2026-11-14 production Woo:
# 55 EN/55 DE home products, 30/30 commercial).
PRODUCT_APPLICATIONS: dict[str, str] = {
    "home": "residential",
    "commercial": "commercial",
}


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
        self,
        requirements: EquipmentRequirements,
        inputs: Object,
        *,
        plant_backup: bool = False,
        constrain_models: bool = False,
    ) -> Iterator[tuple[Object, Object]]:
        seen: set[str] = set()
        brief = inputs.get("brief")
        scope = brief.get("system_scope") if isinstance(brief, dict) else None
        no_battery = scope == "pv_only"
        storage_required = scope in (
            "new_pv_storage",
            "storage_addition",
            "storage_only",
        )
        if scope is None:
            self.gaps["storage_scope_not_declared"] += 1
        if no_battery and any(
            value is not None and value > 0
            for value in (
                requirements.required_usable_kwh,
                requirements.required_discharge_ac_kw,
            )
        ):
            raise InvalidInput(
                "PV-only scope conflicts with positive storage requirements"
            )
        unknown_sizing = (
            requirements.required_usable_kwh is None
            or requirements.required_discharge_ac_kw is None
        )
        source = inputs.get("equipment_setup", inputs.get("equipment_selection"))
        raw_use = source.get("equipment_use") if isinstance(source, dict) else None
        use = EquipmentUse.read(raw_use) if raw_use is not None else None
        selected: dict[str, int] = {}
        retained_assembly: dict[str, int] = {}
        if no_battery and use is not None and use.battery != "new":
            raise InvalidInput("PV-only scope conflicts with declared battery use")
        models = source.get("comparison_models") if isinstance(source, dict) else None
        for part in ("inverter", "battery"):
            field = f"{part}_product_id"
            retain = use is not None and getattr(use, part) == "retain"
            declaration = models if isinstance(models, dict) and not retain else source
            value = declaration.get(field) if isinstance(declaration, dict) else None
            if retain or (
                constrain_models
                and value is not None
                and (part != "battery" or not no_battery)
            ):
                try:
                    selected[field] = TypeAdapter(Count).validate_python(value)
                except ValidationError as error:
                    raise InvalidInput(
                        "retained equipment needs its declared product and assembly"
                        if retain
                        else "select a valid equipment model",
                        fields=(field,),
                    ) from error
        if use is not None and use.battery == "retain":
            assert isinstance(source, dict)
            for field in ("modules_per_stack", "parallel_stacks"):
                try:
                    retained_assembly[field] = TypeAdapter(Count).validate_python(
                        source.get(field)
                    )
                except ValidationError as error:
                    raise InvalidInput(
                        "retained equipment needs its declared product and assembly",
                        fields=(field,),
                    ) from error
        for part, products in (
            ("inverter", self.converters),
            ("battery", self.included),
        ):
            field = f"{part}_product_id"
            if field in selected and not any(
                row["canonical_product_id"] == selected[field] for row in products
            ):
                reason = (
                    "retained_equipment_not_in_search_domain"
                    if use is not None and getattr(use, part) == "retain"
                    else "selected_equipment_not_in_search_domain"
                )
                self.gaps[reason] += 1
                self.excluded_products.append(
                    {"product_id": selected[field], "reason": reason}
                )
                return
        for converter in self.converters:
            if self.exhausted:
                break
            converter_id = converter["canonical_product_id"]
            if selected.get("inverter_product_id", converter_id) != converter_id:
                continue
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
                [None]
                if no_battery
                else [*self.included]
                if storage_required or use is not None and use.battery != "new"
                else [None, *self.included]
            )
            for battery in options:
                battery_id = battery["canonical_product_id"] if battery else None
                if selected.get("battery_product_id", battery_id) != battery_id:
                    continue
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
                    if selected:
                        reason = (
                            "retained_equipment_pair_not_released"
                            if use is not None
                            and "retain" in (use.inverter, use.battery)
                            else "selected_equipment_pair_not_released"
                        )
                        self.gaps[reason] += 1
                        self.excluded_products.append(
                            {
                                "product_id": battery_id,
                                "reason": reason,
                            }
                        )
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
                if retained_assembly:
                    retained_count = retained_assembly["modules_per_stack"]
                    retained_stacks = retained_assembly["parallel_stacks"]
                    if (
                        retained_count not in counts
                        or retained_stacks not in stacks_domain
                    ):
                        reason = "retained_battery_configuration_outside_search_domain"
                        self.gaps[reason] += 1
                        self.excluded_products.append(
                            {"product_id": battery_id, "reason": reason}
                        )
                        continue
                    counts = range(retained_count, retained_count + 1)
                    stacks_domain = range(retained_stacks, retained_stacks + 1)

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
                            equipment_use=use,
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
                        if (
                            unknown_sizing
                            or plant_backup
                            or "equipment_demand" in inputs
                        ):
                            # With no complete demand there is no smallest
                            # sufficient assembly. Keep cited alternatives for
                            # comparison within the same work budget.
                            yield value, assessment
                        elif cast(str, assessment["overall_status"]) == "satisfied":
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

    def combination_fitness(
        self, candidate: Json
    ) -> tuple[
        int, int, int, int, int, tuple[tuple[int, ...], ...], tuple[int, ...], str
    ]:
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
        # Ties on the smallest inverter ID, stack count and module count follow
        # the equipment assigned to each unit and group in the declared order.
        return (
            (
                0
                if record["status"] == "satisfied"
                else 2
                if "plant" in record and record["status"] == "violated"
                else 1
            ),
            int(cast(int, record["unresolved_checks"])),
            min(int(cast(int, row["inverter_product_id"])) for row in selections),
            min(int(cast(int, row["parallel_stacks"] or 0)) for row in selections),
            min(int(cast(int, row["modules_per_stack"] or 0)) for row in selections),
            tuple(
                (
                    cast(int, row["inverter_product_id"]),
                    cast(int, row["battery_product_id"] or 0),
                    cast(int, row["parallel_stacks"] or 0),
                    cast(int, row["modules_per_stack"] or 0),
                    *cast(list[int], row["accessory_product_ids"]),
                )
                for row in selections
            ),
            tuple(
                cast(int, group["controller_product_id"] or 0)
                for group in cast(list[Object], value.get("parallel_groups", []))
            ),
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
                    "canonical_product_id": row["canonical_product_id"],
                    "model": row["model"],
                    "brand": row["brand"],
                    "sku": row["sku"],
                    "product_revision": row["product_revision"],
                    # The battery's own energy travels with it so the reader can
                    # say what a stack adds up to instead of how many modules it
                    # was built from. Measured 2026-11-15 on production: the
                    # choice list showed "Battery modules per stack: 4" for four
                    # different stacks, which is a build detail.
                    #
                    # These are the feed row's own flattened fields, not the
                    # compiled `figures` map: the evidence basis is the
                    # publication feed (`equipment_evidence.py:16`), whose rows
                    # carry `usable_kwh` and `nominal_kwh` at the top level. The
                    # first version of this read `row["figures"]` and shipped an
                    # empty object — the fixture rows in the test carry that
                    # shape, production's do not.
                    "energy": {
                        key: row[key]
                        for key in (
                            "usable_kwh",
                            "nominal_kwh",
                            "module_energy_kwh_usable",
                            "module_energy_kwh_nominal",
                        )
                        if isinstance(row.get(key), (int, float))
                    },
                }
                for row in sorted(
                    self.evidence.rows, key=lambda row: row["canonical_product_id"]
                )
            ],
            "candidates": sorted(candidates, key=self.combination_fitness),
            "qualified_count": sum(
                row["status"] == "satisfied" for row in cast(list[Object], candidates)
            ),
            "ranking": "unresolved_then_product_and_module_count",
            "display_order": "ranking_then_canonical_product_and_documented_module_count",
        }
