"""Assess a proposed topology from frozen Woo evidence, before any ranking.

No legacy sizing ratios or device scalars are used. A passed electrical limit
is one check, not a manufacturer-mode/country release. Missing table mapping,
uninterpreted conditions and sales-unit basis remain explicit obligations.
"""

from __future__ import annotations

import re
from typing import Any, cast

from .canonical import Json, Object, decode_object, encode
from .equipment_evidence import EquipmentEvidence
from .equipment_fact_resolution import FactContext, FactUse, resolve_fact
from .equipment_inputs import EquipmentSelection
from .errors import InvalidInput, ProductEvidenceChanged
from .grid_connection import country_assessment


def selection_products(
    selection: EquipmentSelection, basis: Object
) -> dict[int, dict[str, Any]]:
    products = {
        item["canonical_product_id"]: item
        for item in cast(list[dict[str, Any]], basis["products"])
    }
    for identity, revision in selection.product_revisions.items():
        row = products.get(int(identity))
        if row is None or row["product_revision"] != revision:
            raise ProductEvidenceChanged("selected Woo equipment data changed")
    return products


def assess_equipment(
    inputs: Object,
    basis: Object,
    *,
    evidence: EquipmentEvidence | None = None,
    pv_module_scope: set[str] | None = None,
) -> Object:
    evidence = evidence or EquipmentEvidence(basis)
    evidence.require_basis(basis)
    selection = EquipmentSelection.read(inputs.get("equipment_selection"))
    raw = cast(list[dict[str, Any]], basis["products"])
    products = selection_products(selection, basis)
    selected = {
        selection.inverter_product_id,
        *selection.accessory_product_ids,
        *(
            ()
            if selection.battery_product_id is None
            else (selection.battery_product_id,)
        ),
    }
    if not selected.issubset(products):
        raise InvalidInput("selected equipment is outside the current Woo-ready set")
    typed = {key: evidence.compiled(key) for key in selected}
    fact_context = FactContext(selection, products)
    checks: list[Json] = []
    pv_electrical: Object | None = None

    def add(
        identifier: str,
        status: str,
        reason: str,
        facts: list[dict[str, Any]] | None = None,
        actual: Json = None,
        required: Json = None,
        derivation: Object | None = None,
        documents: list[dict[str, Any]] | None = None,
    ) -> None:
        checks.append(
            {
                "id": identifier,
                "status": status,
                "reason": reason,
                "facts": cast(list[Json], facts or []),
                "actual": actual,
                "required": required,
                **({"derivation": derivation} if derivation is not None else {}),
                **(
                    {"documents": cast(list[Json], documents)}
                    if documents is not None
                    else {}
                ),
            }
        )

    def fact(
        product_id: int, key: str, quantity: str | tuple[str, ...] | None = None
    ) -> dict[str, Any] | None:
        fields = cast(dict[str, dict[str, Any]], typed[product_id]["facts"])
        found = fields.get(key)
        if found is None or (
            quantity is not None
            and found["quantity"]
            not in ((quantity,) if isinstance(quantity, str) else quantity)
        ):
            return None
        return found

    def number(
        product_id: int,
        key: str,
        quantity: str | tuple[str, ...],
        use: FactUse = "numeric",
    ) -> tuple[float | None, list[dict[str, Any]]]:
        found = fact(product_id, key, quantity)
        resolved = (
            resolve_fact(cast(Object, found), fact_context, use).fact if found else None
        )
        if resolved and resolved["shape"] == "scalar":
            return float(cast(float, resolved["value"])), [
                cast(dict[str, Any], resolved)
            ]
        return None, [found] if found else []

    def limit(
        identifier: str,
        requested: float | None,
        product_id: int,
        key: str,
        quantity: str | tuple[str, ...],
        use: FactUse = "numeric",
    ) -> None:
        if requested is None:
            add(identifier, "unresolved", "project_requirement_missing")
            return
        value, refs = number(product_id, key, quantity, use)
        if value is None:
            add(
                identifier,
                "unresolved",
                "current_cited_limit_missing_or_conditional",
                refs,
                required=requested,
            )
        else:
            add(
                identifier,
                "satisfied" if requested <= value else "violated",
                "published_limit_comparison",
                refs,
                value,
                requested,
            )

    inverter = products[selection.inverter_product_id]
    converter_power: float | None = None
    converter_refs: list[dict[str, Any]] = []
    for ac_key in (
        "ac_output_kw_nominal",
        "ac_output_w_nominal",
        "rated_ac_power_kw",
        "nominal_ac_power_kw",
        "rated_ac_power",
        "rated_power_kw",
        "power_kw",
    ):
        converter_power, converter_refs = number(
            selection.inverter_product_id,
            ac_key,
            "active_power",
            "nominal_ac_output",
        )
        if converter_power is not None or converter_refs:
            break
    add(
        "converter_identity",
        "satisfied"
        if converter_power is not None and converter_power > 0
        else "unresolved",
        "cited_nominal_active_ac_output_required",
        converter_refs,
        converter_power,
    )
    if (
        selection.operating_mode == "grid_connected"
        and selection.required_discharge_ac_kw is not None
        and selection.required_discharge_ac_kw > 0
    ):
        ceilings: list[float] = []
        ceiling_refs: list[dict[str, Any]] = []
        for key in ("ac_output_kw_max", "max_apparent_power_kva"):
            value, refs = number(
                selection.inverter_product_id,
                key,
                ("active_power", "apparent_power"),
                "grid_output_ceiling",
            )
            if value is not None:
                ceilings.append(value)
                ceiling_refs.extend(refs)
        if ceilings:
            # |P| <= S: a cited maximum apparent output gives a necessary
            # active-power upper bound, never continuous battery capability.
            # Retain the original quantity/unit in every bound source fact.
            ceiling = min(ceilings)
            checks.append(
                {
                    "id": "grid_output_ceiling",
                    "status": "satisfied"
                    if selection.required_discharge_ac_kw <= ceiling
                    else "violated",
                    "reason": "maximum_grid_output_is_necessary_bound_only",
                    "facts": cast(list[Json], ceiling_refs),
                    "actual": ceiling,
                    "required": selection.required_discharge_ac_kw,
                    "unit": "kW",
                    "calculation": {
                        "relation": "abs(P)<=S",
                        "role": "necessary_upper_bound_only",
                    },
                }
            )
    phase = inverter["phase"]
    add(
        "grid_phase",
        "unresolved"
        if selection.grid_phase is None or phase == "unknown"
        else "satisfied"
        if selection.grid_phase == phase
        else "violated",
        "woocommerce_phase_attribute",
        actual=phase,
        required=selection.grid_phase,
    )
    if selection.pv_dc_kw is not None:
        pv_key = (
            "max_pv_input_power_w"
            if fact(
                selection.inverter_product_id,
                "max_pv_input_power_w",
                ("pv_nameplate_power", "active_power"),
            )
            is not None
            or fact(selection.inverter_product_id, "max_pv_array_power") is None
            else "max_pv_array_power"
        )
        limit(
            "pv_dc_input",
            selection.pv_dc_kw,
            selection.inverter_product_id,
            pv_key,
            ("pv_nameplate_power", "active_power"),
            "pv_nameplate_limit",
        )
    if inputs.get("pv_string_plan") is not None and "pv_module_inputs" in basis:
        from .pv_string_assessment import assess_pv_strings

        pv_electrical = assess_pv_strings(inputs, basis, module_scope=pv_module_scope)
        checks.extend(cast(list[Json], pv_electrical["checks"]))
    elif selection.pv_dc_kw is not None:
        if selection.pv_dc_kw == 0:
            add(
                "pv_electrical_topology",
                "satisfied",
                "no_pv_dc_input_requested",
                actual=0,
                required=0,
            )
        else:
            mppt_count, mppt_refs = number(
                selection.inverter_product_id, "n_mppt", "count"
            )
            mppt_window = fact(
                selection.inverter_product_id, "mppt_voltage_range_v", "voltage"
            )
            max_pv_v, max_pv_v_refs = number(
                selection.inverter_product_id, "max_pv_input_v", "voltage"
            )
            window_valid = (
                mppt_window is not None
                and mppt_window["status"] == "typed"
                and mppt_window["shape"] == "interval"
                and 0 < mppt_window["value"][0] < mppt_window["value"][1]
                and (max_pv_v is None or max_pv_v >= mppt_window["value"][1])
            )
            topology_refs = [
                *mppt_refs,
                *([mppt_window] if mppt_window is not None else []),
                *max_pv_v_refs,
            ]
            if mppt_count is not None and mppt_count >= 1 and window_valid:
                add(
                    "pv_electrical_topology",
                    "satisfied",
                    "cited_mppt_inputs_and_voltage_window",
                    topology_refs,
                    actual=int(mppt_count),
                )
            else:
                add(
                    "pv_electrical_topology",
                    "unresolved",
                    "string_ports_voltage_current_and_temperature_require_assessment",
                    topology_refs,
                )

    contract = evidence.contract
    installation = [
        requirement
        for kind in (
            "meter",
            *(("backup",) if selection.operating_mode == "backup" else ()),
        )
        for requirement in contract.requirements(
            inverter["model"], kind, inverter_id=selection.inverter_product_id
        )
        if requirement.phase is None
        or selection.grid_phase is None
        or requirement.phase == selection.grid_phase
    ]
    bom: list[Json] = [
        {
            "product_id": selection.inverter_product_id,
            "quantity": 1,
            "basis": "selected_converter",
        }
    ]
    count, stacks = selection.modules_per_stack, selection.parallel_stacks
    pair_result = (
        contract.pair(
            inverter["model"],
            products[selection.battery_product_id]["model"],
            inverter_id=selection.inverter_product_id,
            battery_id=selection.battery_product_id,
        )
        if selection.battery_product_id is not None
        else None
    )
    pair_accessories = list(pair_result.accessories) if pair_result else []
    requirements = [
        *pair_accessories,
        *(a for r in installation if not r.included for a in r.accessories),
    ]
    resolved: dict[int, tuple[int, str]] = {}
    pair_accessory_unresolved = False
    pair_accessory_missing = False
    for index_acc, accessory in enumerate(requirements):
        from_pair = index_acc < len(pair_accessories)
        matches = [
            p
            for p in raw
            if (
                (
                    accessory.product_id is None
                    and re.search(accessory.model, p["model"])
                )
                or p["canonical_product_id"] == accessory.product_id
            )
        ]
        accessory_multiplier = (
            stacks
            if accessory.per == "stack"
            else 1
            if accessory.per in {"system", "unit"}
            else None
        )
        if len(matches) != 1 or accessory_multiplier is None:
            if from_pair:
                pair_accessory_unresolved = True
            add(
                "required_accessory:" + accessory.model,
                "unresolved",
                "accessory_identity_or_quantity_unresolved",
            )
            continue
        pid, quantity = (
            matches[0]["canonical_product_id"],
            accessory.quantity * accessory_multiplier,
        )
        if pid in resolved and resolved[pid] != (quantity, accessory.per):
            if from_pair:
                pair_accessory_unresolved = True
            add(
                "required_accessory:" + str(pid),
                "unresolved",
                "accessory_quantity_rules_conflict",
            )
            continue
        resolved[pid] = (quantity, accessory.per)
        if from_pair and pid not in selection.accessory_product_ids:
            pair_accessory_missing = True
        add(
            "required_accessory:" + str(pid),
            "satisfied" if pid in selection.accessory_product_ids else "violated",
            "manufacturer_required_component",
            actual=pid,
        )
    for pid, (quantity, per) in resolved.items():
        if quantity > 9007199254740991:
            raise InvalidInput("accessory quantity exceeds interoperable integers")
        bom.append(
            {
                "product_id": pid,
                "quantity": quantity,
                "basis": "manufacturer_required_" + per,
            }
        )
    for pid in selection.accessory_product_ids:
        if pid not in resolved:
            bom.append(
                {
                    "product_id": pid,
                    "quantity": None,
                    "basis": "selected_accessory_quantity_unresolved",
                }
            )
            add(
                "accessory_quantity:" + str(pid),
                "unresolved",
                "selected_accessory_quantity_requires_evidence",
            )

    pairing: Json = None
    if selection.battery_product_id is not None:
        battery_id = selection.battery_product_id
        pair = pair_result
        assert pair is not None
        pair_documents: list[dict[str, Any]] = [
            {"url": doc.url, "page": doc.page} for doc in pair.documents
        ]
        pairing = {
            "verdict": pair.verdict,
            "conditions": [{"en": text.en, "de": text.de} for text in pair.conditions],
            "documents": cast(list[Json], pair_documents),
        }
        sales = fact(battery_id, "sales_unit_kind")
        sales_kind = (
            sales["raw_value"]
            if sales and sales["source"] and not sales["qualifier"]
            else None
        )
        min_val, min_refs = number(battery_id, "modules_per_stack_min", "count")
        max_val, max_refs = number(battery_id, "modules_per_stack_max", "count")
        sys_max_val, sys_max_refs = number(
            battery_id, "modules_per_system_max", "count"
        )
        stack_low = (
            int(min_val)
            if min_val is not None
            else 1
            if max_val is not None and sales_kind == "battery_module"
            else None
        )
        stack_bounds = ([pair.modules] if pair.modules is not None else []) + (
            [(stack_low, int(max_val))]
            if stack_low is not None and max_val is not None
            else []
        )
        if (
            sys_max_val is not None
            and stacks is not None
            and stacks >= 1
            and stack_bounds
        ):
            stack_bounds.append((1, int(sys_max_val) // stacks))
        count_refs = [*min_refs, *max_refs, *sys_max_refs]
        low, high = (
            (max(r[0] for r in stack_bounds), min(r[1] for r in stack_bounds))
            if stack_bounds
            else (None, None)
        )
        if low is None or high is None or low > high or count is None:
            modules_status = "unresolved"
        else:
            modules_status = "satisfied" if low <= count <= high else "violated"

        # Evaluate compatibility release and attached manufacturer conditions
        # against the selected configuration rather than rejecting all pairs
        # that carry documentation notes.
        if not pair.released:
            pair_status = "unresolved"
            pair_reason = "manufacturer_release_not_established"
        else:
            condition_texts = [text.en for text in pair.conditions]
            one_way_unapproved = any(
                "Listed one-way:" in text or "not a complete warranty approval" in text
                for text in condition_texts
            )
            column_limit_issue: str | None = None
            if any(
                "limits one column to six batteries" in text for text in condition_texts
            ):
                if count is None or stacks is None:
                    column_limit_issue = "unresolved"
                elif count > 6 or stacks != 1:
                    column_limit_issue = "violated"
            voc_condition_violated = False
            for text in condition_texts:
                voc_match = re.search(
                    r"open-circuit input voltage above (\d+(?:\.\d+)?)\s*V", text
                )
                if voc_match and pv_electrical is not None:
                    min_voc = float(voc_match.group(1))
                    for string_row in cast(
                        list[Object], pv_electrical.get("strings", [])
                    ):
                        cold_voc = string_row.get("cold_voc_v")
                        if isinstance(cold_voc, (int, float)) and cold_voc <= min_voc:
                            voc_condition_violated = True
            if (
                pair_accessory_missing
                or (pair.modules is not None and modules_status == "violated")
                or column_limit_issue == "violated"
                or voc_condition_violated
            ):
                pair_status = "violated"
                pair_reason = "manufacturer_conditions_require_assessment"
            elif (
                pair_accessory_unresolved
                or one_way_unapproved
                or (pair.modules is not None and modules_status == "unresolved")
                or column_limit_issue == "unresolved"
            ):
                pair_status = "unresolved"
                pair_reason = "manufacturer_conditions_require_assessment"
            else:
                pair_status = "satisfied"
                pair_reason = "manufacturer_pair_released"
        add(
            "manufacturer_pair",
            pair_status,
            pair_reason,
            documents=pair_documents,
        )
        if modules_status == "unresolved":
            add(
                "modules_per_stack",
                "unresolved",
                "cited_configuration_count_missing",
                count_refs,
            )
        else:
            assert low is not None and high is not None
            add(
                "modules_per_stack",
                modules_status,
                "manufacturer_pair_module_count",
                count_refs,
                actual=count,
                required=[low, high],
            )
        parallel, refs = number(battery_id, "stacks_parallel_max", "count")
        add(
            "parallel_stacks",
            "unresolved"
            if stacks is None or (parallel is None and stacks != 1)
            else "satisfied"
            if stacks == 1 or (parallel is not None and stacks <= parallel)
            else "violated",
            "single_stack_without_parallel_connection"
            if stacks == 1
            else "parallel_topology_limit",
            refs,
            stacks,
            parallel,
        )

        inv_range = fact(
            selection.inverter_product_id, "battery_voltage_range_v", "voltage"
        )
        voltage_status = "unresolved"
        operating: dict[str, Any] | None = None
        candidates: list[dict[str, Any]] = []
        ordered_table_unresolved = False
        for pid in [battery_id, *selection.accessory_product_ids]:
            found = None
            for vkey in (
                "system_operating_voltage_range_v",
                "operating_voltage_range_v",
                "voltage_range",
            ):
                found = fact(pid, vkey, "voltage")
                if found is not None:
                    break
            if found is None:
                continue
            voltage_projection = resolve_fact(
                cast(Object, found), fact_context, "battery_operating_voltage"
            ).fact
            if not voltage_projection or voltage_projection["shape"] != "interval":
                if found.get("shape") == "ordered_values":
                    ordered_table_unresolved = True
                continue
            if (
                voltage_projection.get("selected_module_count") == count
                and count is not None
            ):
                candidates.append(cast(dict[str, Any], voltage_projection))
            else:
                minimum, _ = number(pid, "modules_per_stack_min", "count")
                maximum, _ = number(pid, "modules_per_stack_max", "count")
                if count is not None and minimum == maximum == count:
                    candidates.append(cast(dict[str, Any], voltage_projection))
                elif (
                    pid == battery_id
                    and count is not None
                    and low is not None
                    and high is not None
                    and low <= count <= high
                ):
                    candidates.append(cast(dict[str, Any], voltage_projection))
        if (
            not candidates
            and not ordered_table_unresolved
            and count is not None
            and low is not None
            and high is not None
            and low <= count <= high
        ):
            mod_v = fact(battery_id, "module_voltage_range_v", "voltage")
            if (
                mod_v is not None
                and mod_v["status"] == "typed"
                and mod_v["shape"] == "interval"
            ):
                ml, mh = cast(list[float], mod_v["value"])
                if sales_kind == "battery_system" and min_val == max_val == count:
                    candidates.append(mod_v)
                elif (
                    sales_kind == "battery_module"
                    and inv_range is not None
                    and inv_range["shape"] == "interval"
                ):
                    il, ih = cast(list[float], inv_range["value"])
                    if il <= ml <= mh <= ih:
                        candidates.append(mod_v)
                    else:
                        candidates.append(
                            {
                                **mod_v,
                                "value": [
                                    round(ml * count, 6),
                                    round(mh * count, 6),
                                ],
                                "selected_module_count": count,
                            }
                        )
        if (
            candidates
            and len({encode(cast(Json, item["value"])) for item in candidates}) == 1
        ):
            operating = candidates[0]

        if (
            inv_range
            and inv_range["status"] == "typed"
            and inv_range["shape"] == "interval"
            and operating
        ):
            il, ih = inv_range["value"]
            bl, bh = operating["value"]
            status = (
                "violated"
                if bh < il or bl > ih
                else "satisfied"
                if il <= bl <= bh <= ih
                else "unresolved"
            )
            voltage_status = status
            add(
                "battery_voltage",
                status,
                "disjoint_voltage_windows"
                if status == "violated"
                else "full_voltage_window_containment"
                if status == "satisfied"
                else "partial_voltage_window_energy_not_established",
                [inv_range, operating],
            )
        else:
            add("battery_voltage", "unresolved", "cited_topology_voltage_missing")

        # A field describing one internal pack does not define the Woo SKU's
        # sales unit. Without this cited identity we publish no battery count.
        multiplier: int | None = None
        energy_val: float | None = None
        energy_refs: list[dict[str, Any]] = []
        if sales_kind == "battery_module" and count is not None and stacks is not None:
            multiplier = count * stacks
            energy_val, energy_refs = number(
                battery_id, "module_energy_kwh_usable", "energy"
            )
        elif sales_kind == "battery_system" and stacks is not None:
            multiplier = stacks
            for ekey in (
                "system_usable_energy_kwh",
                "usable_energy_kwh",
                "usable_energy",
                "module_energy_kwh_usable",
            ):
                energy_val, energy_refs = number(
                    battery_id, ekey, "energy", "usable_energy"
                )
                if energy_val is not None or energy_refs:
                    break
            if energy_val is None and not energy_refs:
                dod_val, dod_refs = number(battery_id, "dod_pct", "fraction")
                if dod_val == 1.0:
                    for nkey in (
                        "system_nominal_energy_kwh",
                        "system_capacity_kwh_nominal",
                        "system_energy_kwh_nominal",
                        "rated_energy_kwh",
                        "rated_energy",
                    ):
                        nom_val, nom_refs = number(battery_id, nkey, "energy")
                        if nom_val is not None:
                            energy_val = nom_val
                            energy_refs = [*nom_refs, *dod_refs]
                            break
        add(
            "battery_sales_unit",
            "satisfied" if multiplier is not None else "unresolved",
            "cited_sales_unit_basis"
            if multiplier is not None
            else "sales_unit_basis_not_established",
            [sales] if sales else [],
        )
        if multiplier is not None:
            if battery_id != selection.inverter_product_id:
                bom.append(
                    {
                        "product_id": battery_id,
                        "quantity": multiplier,
                        "basis": sales_kind,
                    }
                )
            else:
                add(
                    "integrated_sales_unit",
                    "unresolved",
                    "combined_converter_and_battery_sales_unit_requires_assessment",
                )
        rated_total = (
            energy_val * multiplier
            if energy_val is not None and multiplier is not None
            else None
        )
        # Capacity at the battery's own rated window does not prove usable
        # energy through a narrower converter window. No V-SOC curve is inferred.
        total = rated_total if voltage_status == "satisfied" else None
        required = selection.required_usable_kwh
        add(
            "usable_energy",
            "unresolved"
            if required is None or total is None
            else "satisfied"
            if total >= required
            else "violated",
            "cited_usable_energy_and_sales_basis"
            if voltage_status == "satisfied"
            else "usable_energy_requires_full_voltage_window",
            energy_refs,
            total,
            required,
            derivation={
                "operation": "multiply",
                "factors": [energy_val, multiplier],
                "unit": "kWh",
            }
            if total is not None
            else None,
        )
        if selection.required_discharge_ac_kw is not None:
            discharge_bounds: list[float] = []
            discharge_refs: list[dict[str, Any]] = []
            inv_discharge_kw: float | None = None
            inv_discharge_refs: list[dict[str, Any]] = []
            for dkey in (
                "continuous_battery_discharge_ac_power_kw",
                "max_battery_discharge_power_kw",
            ):
                inv_discharge_kw, inv_discharge_refs = number(
                    selection.inverter_product_id, dkey, "active_power"
                )
                if inv_discharge_kw is not None or inv_discharge_refs:
                    break
            if inv_discharge_kw is None and not inv_discharge_refs:
                inv_discharge_kw, inv_discharge_refs = converter_power, converter_refs
            if inv_discharge_kw is not None:
                discharge_bounds.append(inv_discharge_kw)
                discharge_refs.extend(inv_discharge_refs)
            elif inv_discharge_refs:
                discharge_refs.extend(inv_discharge_refs)

            bat_discharge_kw: float | None = None
            bat_discharge_refs: list[dict[str, Any]] = []
            for bkey in (
                "system_rated_dc_power_w",
                "system_rated_dc_power_kw",
                "rated_power_w",
            ):
                bat_discharge_kw, bat_discharge_refs = number(
                    battery_id, bkey, "active_power", "bank_rated_dc_power"
                )
                if bat_discharge_kw is not None:
                    break
            if bat_discharge_kw is None:
                for bkey in (
                    "max_input_output_power_kw",
                    "max_charging_discharging_power_kw",
                    "max_charge_discharge_power_kw",
                ):
                    bfact = fact(battery_id, bkey, "active_power")
                    if bfact is None or bfact["status"] != "typed":
                        continue
                    if bfact["shape"] == "scalar":
                        bat_discharge_kw = float(cast(float, bfact["value"]))
                        bat_discharge_refs = [bfact]
                        break
                    if (
                        bfact["shape"] == "ordered_values"
                        and isinstance(bfact["value"], list)
                        and len(bfact["value"]) == 2
                        and isinstance(bfact["value"][1], dict)
                        and bfact["value"][1].get("shape") == "scalar"
                    ):
                        bat_discharge_kw = float(
                            cast(float, bfact["value"][1]["value"])
                        )
                        bat_discharge_refs = [bfact]
                        break
            if bat_discharge_kw is not None and stacks is not None:
                discharge_bounds.append(bat_discharge_kw * stacks)
                discharge_refs.extend(bat_discharge_refs)

            discharge_limit = min(discharge_bounds) if discharge_bounds else None
            if discharge_limit is None:
                add(
                    "continuous_battery_ac_output",
                    "unresolved",
                    "current_cited_limit_missing_or_conditional",
                    discharge_refs,
                    required=selection.required_discharge_ac_kw,
                )
            else:
                add(
                    "continuous_battery_ac_output",
                    "satisfied"
                    if selection.required_discharge_ac_kw <= discharge_limit
                    else "violated",
                    "published_limit_comparison",
                    discharge_refs,
                    discharge_limit,
                    selection.required_discharge_ac_kw,
                )
            path_satisfied = (
                pair.released
                and voltage_status == "satisfied"
                and discharge_limit is not None
                and inv_range is not None
                and operating is not None
            )
            add(
                "battery_discharge_path",
                "satisfied" if path_satisfied else "unresolved",
                "cited_battery_port_and_converter_output"
                if path_satisfied
                else "battery_continuous_output_ports_and_conversion_require_assessment",
                [inv_range, operating, *discharge_refs]
                if path_satisfied and inv_range is not None and operating is not None
                else [],
            )
    else:
        requirements_known_empty = (
            selection.required_usable_kwh == 0
            and selection.required_discharge_ac_kw == 0
        )
        requirements_positive = any(
            value is not None and value > 0
            for value in (
                selection.required_usable_kwh,
                selection.required_discharge_ac_kw,
            )
        )
        add(
            "battery",
            "satisfied"
            if requirements_known_empty
            else "violated"
            if requirements_positive
            else "unresolved",
            "no_battery_selected",
        )

    if selection.operating_mode == "backup":
        add(
            "backup_mode",
            "unresolved",
            "mode_ports_transfer_and_continuous_output_require_assessment",
        )
    statuses = [cast(dict[str, Any], check)["status"] for check in checks]
    equipment_status = (
        "violated"
        if "violated" in statuses
        else "unresolved"
        if "unresolved" in statuses
        else "satisfied"
    )
    return decode_object(
        encode(
            {
                "equipment_status": equipment_status,
                "checks": checks,
                **(
                    {"pv_electrical": pv_electrical}
                    if pv_electrical is not None
                    else {}
                ),
                "manufacturer_pair": pairing,
                "installation_requirements": [
                    {
                        "kind": r.kind,
                        "included": r.included,
                        "conditions": [
                            {"en": text.en, "de": text.de} for text in r.conditions
                        ],
                        "documents": [
                            {"url": doc.url, "page": doc.page} for doc in r.documents
                        ],
                    }
                    for r in installation
                ],
                "selected_products": [typed[key] for key in sorted(typed)],
                "provisional_bill_of_materials": [
                    {
                        **cast(Object, line),
                        "model": products[cast(dict[str, Any], line)["product_id"]][
                            "model"
                        ],
                        "brand": products[cast(dict[str, Any], line)["product_id"]][
                            "brand"
                        ],
                        "sku": products[cast(dict[str, Any], line)["product_id"]][
                            "sku"
                        ],
                    }
                    for line in bom
                ],
                "bill_of_materials_status": "unresolved"
                if any(cast(dict[str, Any], c)["status"] != "satisfied" for c in checks)
                else "equipment_checks_satisfied",
                "country_assessment": country_assessment(inputs),
                "overall_status": equipment_status,
                "ranking": "not_performed_before_qualification",
            }
        )
    )
