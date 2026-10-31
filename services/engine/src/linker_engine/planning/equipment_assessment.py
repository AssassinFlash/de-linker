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
    converter_power, converter_refs = number(
        selection.inverter_product_id,
        "ac_output_kw_nominal",
        "active_power",
        "nominal_ac_output",
    )
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
        limit(
            "pv_dc_input",
            selection.pv_dc_kw,
            selection.inverter_product_id,
            "max_pv_input_power_w",
            "pv_nameplate_power",
            "pv_nameplate_limit",
        )
    if inputs.get("pv_string_plan") is not None and "pv_module_inputs" in basis:
        from .pv_string_assessment import assess_pv_strings

        pv_electrical = assess_pv_strings(inputs, basis, module_scope=pv_module_scope)
        checks.extend(cast(list[Json], pv_electrical["checks"]))
    elif selection.pv_dc_kw is not None:
        add(
            "pv_electrical_topology",
            "unresolved",
            "string_ports_voltage_current_and_temperature_require_assessment",
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
    requirements = list(pair_result.accessories) if pair_result else []
    requirements.extend(
        a for r in installation if not r.included for a in r.accessories
    )
    resolved: dict[int, tuple[int, str]] = {}
    for accessory in requirements:
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
            add(
                "required_accessory:" + str(pid),
                "unresolved",
                "accessory_quantity_rules_conflict",
            )
            continue
        resolved[pid] = (quantity, accessory.per)
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
        pairing = {
            "verdict": pair.verdict,
            "conditions": [{"en": text.en, "de": text.de} for text in pair.conditions],
            "documents": [{"url": doc.url, "page": doc.page} for doc in pair.documents],
        }
        # Existing 'not_released' entries include absence-of-evidence findings.
        # They cannot honestly be reinterpreted as physical incompatibility.
        add(
            "manufacturer_pair",
            "satisfied" if pair.released and not pair.conditions else "unresolved",
            "manufacturer_conditions_require_assessment"
            if pair.released
            else "manufacturer_release_not_established",
        )
        low, high = pair.modules if pair.modules is not None else (None, None)
        if low is None or high is None or count is None:
            add("modules_per_stack", "unresolved", "cited_configuration_count_missing")
        else:
            add(
                "modules_per_stack",
                "satisfied" if low <= count <= high else "violated",
                "manufacturer_pair_module_count",
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
        for pid in [battery_id, *selection.accessory_product_ids]:
            found = fact(pid, "system_operating_voltage_range_v", "voltage")
            voltage_projection = (
                resolve_fact(
                    cast(Object, found), fact_context, "battery_operating_voltage"
                ).fact
                if found
                else None
            )
            if not voltage_projection or voltage_projection["shape"] != "interval":
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
        sales = fact(battery_id, "sales_unit_kind")
        sales_kind = (
            sales["raw_value"]
            if sales and sales["source"] and not sales["qualifier"]
            else None
        )
        multiplier: int | None = None
        energy_key: str | None = None
        if sales_kind == "battery_module" and count is not None and stacks is not None:
            multiplier, energy_key = count * stacks, "module_energy_kwh_usable"
        elif sales_kind == "battery_system" and stacks is not None:
            multiplier, energy_key = stacks, "system_usable_energy_kwh"
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
        value, refs = (
            number(battery_id, energy_key, "energy") if energy_key else (None, [])
        )
        rated_total = (
            value * multiplier if value is not None and multiplier is not None else None
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
            refs,
            total,
            required,
            derivation={
                "operation": "multiply",
                "factors": [value, multiplier],
                "unit": "kWh",
            }
            if total is not None
            else None,
        )
        if selection.required_discharge_ac_kw is not None:
            # Maximum DC current and fault current do not establish sustained
            # AC output. This check needs a cited continuous AC capability.
            limit(
                "continuous_battery_ac_output",
                selection.required_discharge_ac_kw,
                selection.inverter_product_id,
                "continuous_battery_discharge_ac_power_kw",
                "active_power",
            )
            add(
                "battery_discharge_path",
                "unresolved",
                "battery_continuous_output_ports_and_conversion_require_assessment",
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
    brief = inputs.get("brief")
    site = brief.get("site") if isinstance(brief, dict) else None
    country = site.get("country_code") if isinstance(site, dict) else None
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
                "country_assessment": {
                    "status": "unresolved",
                    "country_code": country,
                    "reason": "versioned_country_rules_required",
                },
                "overall_status": "violated"
                if equipment_status == "violated"
                else "unresolved",
                "ranking": "not_performed_before_qualification",
            }
        )
    )
