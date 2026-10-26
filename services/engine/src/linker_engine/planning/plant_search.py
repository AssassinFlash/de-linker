"""Compose whole-plant candidates within the customer's explicit search layout.

One Woo snapshot and one execution budget cover unit qualification and joint
checks. Identical unit demands share computation, never a physical battery.
"""

from __future__ import annotations

import itertools
import re
from collections import deque
from collections.abc import Callable, Iterator
from typing import cast

from .canonical import Json, Object, digest, encode
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_plant import EquipmentPlant
from .equipment_search import candidate_record
from .equipment_search_limits import EquipmentSearchLimits
from .equipment_search_space import EquipmentSearchSpace
from .plant_assessment import assess_plant
from .plant_search_plan import PlantSearchPlan, SearchGroup


def controller_options(
    group: SearchGroup, selections: dict[str, Object], space: EquipmentSearchSpace
) -> list[int | None]:
    evidence = space.evidence
    occupied = {
        int(pid)
        for s in selections.values()
        for pid in cast(Object, s["product_revisions"])
    }
    if group.controller_product_id is not None:
        if (
            group.controller_product_id in evidence.products
            and group.controller_product_id not in occupied
        ):
            return [group.controller_product_id]
        space.gaps["selected_controller_not_current"] += 1
        return []
    common: set[int] | None = None
    for uid in group.unit_ids:
        selection = selections[uid]
        pid = cast(int, selection["inverter_product_id"])
        converter = evidence.products[pid]
        options: set[int] = set()
        for row in evidence.contract.requirements(
            converter["model"],
            "parallel_controller",
            inverter_id=pid,
            operating_mode=cast(str, selection["operating_mode"]),
            topology="parallel_group",
            control_network=group.control_network,
        ):
            if row.phase not in (None, selection["grid_phase"]):
                continue
            for part in row.accessories:
                if part.per != "system" or part.quantity != 1:
                    continue
                matches = [
                    p["canonical_product_id"]
                    for p in evidence.rows
                    if (
                        p["canonical_product_id"] == part.product_id
                        if part.product_id is not None
                        else re.search(part.model, p["model"])
                    )
                ]
                if len(matches) == 1:
                    options.add(matches[0])
        common = options if common is None else common & options
    if not common:
        space.gaps["group_controller_association_not_established"] += 1
        return [None]
    return [pid for pid in sorted(common - occupied)]


def new_combinations(
    keys: list[str], pools: dict[str, list[Object]], changed: str
) -> Iterator[tuple[Object, ...]]:
    """Enumerate each Cartesian tuple when its last new option arrives once.

    For repeated demands, the first instance using the new option partitions
    the tuples. This avoids rescanning the already assessed Cartesian prefix.
    """
    if any(not pools[key] for key in keys):
        return
    for index, key in enumerate(keys):
        if key != changed:
            continue
        columns = [
            [pools[k][-1]]
            if i == index
            else pools[k][:-1]
            if i < index and k == changed
            else pools[k]
            for i, k in enumerate(keys)
        ]
        yield from itertools.product(*columns)


def search_plant(
    inputs: Object,
    basis: Object,
    limits: EquipmentSearchLimits,
    store: EquipmentCandidateStore,
    checkpoint: Callable[[], None],
) -> Object:
    plan = PlantSearchPlan.from_inputs(inputs)
    space = EquipmentSearchSpace(basis, limits, checkpoint)
    cache: dict[str, list[Object]] = {}
    assessments: dict[str, Object] = {}
    keys: list[str] = []
    pending: deque[tuple[str, Iterator[tuple[Object, Object]]]] = deque()
    # Unit checks depend on this same brief, current Woo snapshot and demand.
    unit_context = {"brief": inputs.get("brief")}
    for unit in plan.units:
        if not space.available():
            break
        key = digest(encode(cast(Object, unit.requirements.model_dump(mode="json"))))
        keys.append(key)
        if key not in cache:
            cache[key] = []
            pending.append((key, space.options(unit.requirements, unit_context)))
    candidates: list[Json] = []
    while pending and not space.exhausted and len(keys) == len(plan.units):
        key, iterator = pending.popleft()
        for selection, assessment in iterator:
            if assessment["overall_status"] == "violated":
                space.gaps["unit_constraints_violated"] += 1
                continue
            cache[key].append(selection)
            assessments[digest(encode(selection))] = assessment
            pending.append((key, iterator))
            break
        else:
            continue
        for combination in new_combinations(keys, cache, key):
            if not space.available():
                break
            selected = dict(zip((u.id for u in plan.units), combination, strict=True))
            options = [
                controller_options(g, selected, space) for g in plan.parallel_groups
            ]
            for controllers in itertools.product(*options):
                # The result contains every system, not just one tuple ID.
                # Charge expansion before materialising that candidate, so a
                # large layout cannot multiply payload under a flat-step cap.
                if not space.available(len(plan.units) + len(plan.parallel_groups)):
                    break
                plant = EquipmentPlant.read(
                    {
                        "schema_version": 1,
                        "requirements": plan.requirements.model_dump(mode="json"),
                        "units": [
                            {"id": u.id, "name": u.name, "selection": selected[u.id]}
                            for u in plan.units
                        ],
                        "parallel_groups": [
                            {
                                **g.model_dump(mode="json"),
                                "controller_product_id": pid,
                                "controller_revision": space.evidence.products[pid][
                                    "product_revision"
                                ]
                                if pid is not None
                                else None,
                            }
                            for g, pid in zip(
                                plan.parallel_groups, controllers, strict=True
                            )
                        ],
                    }
                )
                value = cast(Object, plant.model_dump(mode="json"))
                assessment = assess_plant(
                    {"brief": inputs.get("brief"), "equipment_plant": value},
                    basis,
                    checkpoint,
                    unit_assessments=assessments,
                    evidence=space.evidence,
                )
                candidates.append(candidate_record("plant", value, assessment, store))
    return space.result(
        candidates,
        {
            "template": "declared_plant_one_external_assembly_per_converter",
            "plan": cast(Object, plan.model_dump(mode="json")),
            "unit_configurations": [len(cache[key]) for key in keys],
            "identical_demand_cache_entries": len(cache),
            "work_basis": "source_pairs_unit_checks_cartesian_steps_and_expanded_systems",
            "unassessed_templates": [
                "alternative_system_counts",
                "alternative_demand_allocations",
                "multiple_battery_ports",
                "parallel_battery_assemblies",
                "integrated_systems",
            ],
        },
    )
