"""Cited string checks with explicit STC and design-temperature boundaries.

The linear cold-Voc method follows the manufacturer's published coefficient
definition and Trina UM-M-0002 O, section 6.4.1 (PDF pp37-38). It is not an
I-V model or country release. See NUMERICAL-MODELS.md section 13 for scope.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, cast

from .canonical import Json, Object
from .equipment_facts import compile_facts, compile_product
from .equipment_inputs import EquipmentSelection
from .errors import InvalidInput
from .geometry import panel_poses, read_geometry
from .product_sources import ProductSources
from .pv_string_inputs import PvStringPlan


def assess_pv_strings(inputs: Object, basis: Object) -> Object:
    plan = PvStringPlan.read(inputs.get("pv_string_plan"))
    selection = EquipmentSelection.read(inputs.get("equipment_selection"))
    if plan.inverter_product_id != selection.inverter_product_id:
        raise InvalidInput("PV strings belong to a different inverter selection")
    proof = basis.get("pv_module_inputs")
    if not isinstance(proof, dict) or not isinstance(
        proof.get("electrical_product"), dict
    ):
        raise InvalidInput("PV strings require the frozen Woo module electrical source")
    geometry = read_geometry(inputs.get("geometry"))
    poses = {p.id: p for p in panel_poses(geometry) if p.included}
    arrays = {a.id: a for a in geometry.arrays}
    specs = {s.id: s for s in geometry.module_specs}
    products = cast(list[dict[str, Any]], basis["products"])
    inverter = next(
        p
        for p in products
        if p["canonical_product_id"] == selection.inverter_product_id
    )
    module = cast(dict[str, Any], proof["electrical_product"])
    mf = cast(dict[str, Any], compile_facts(module))
    inv = cast(dict[str, Any], compile_product(inverter)["facts"])
    checks: list[Json] = []
    rows: list[Json] = []

    def fact(fields: dict[str, Any], key: str, quantity: str) -> dict[str, Any] | None:
        value = fields.get(key)
        return (
            value
            if value and value["status"] == "typed" and value["quantity"] == quantity
            else None
        )

    def scalar(
        fields: dict[str, Any], key: str, quantity: str, port: int | None = None
    ) -> tuple[float | None, list[Json]]:
        value = fact(fields, key, quantity)
        refs = cast(list[Json], [fields[key]] if key in fields else [])
        if value and value["shape"] == "scalar":
            return float(value["value"]), refs
        # Slash-separated limits retain their declared MPPT order. No range
        # flattening, highest-column selection or whole-device multiplication.
        if value and port is not None and value["shape"] == "ordered_values":
            values = value["value"]
            if port <= len(values) and values[port - 1]["shape"] == "scalar":
                return float(values[port - 1]["value"]), refs
        return None, refs

    def add(
        identifier: str,
        actual: Json = None,
        required: Json = None,
        refs: list[Json] | None = None,
        *,
        status: str | None = None,
        unit: str = "",
        reason: str = "cited_pv_limit",
    ) -> None:
        checks.append(
            {
                "id": identifier,
                "status": status
                or (
                    "unresolved"
                    if actual is None or required is None
                    else "satisfied"
                    if cast(float, actual) <= cast(float, required)
                    else "violated"
                ),
                "reason": reason,
                "actual": actual,
                "required": required,
                "facts": refs or [],
                "unit": unit,
            }
        )

    assigned = [mid for item in plan.strings for mid in item.module_ids]
    if any(mid not in poses for mid in assigned):
        raise InvalidInput("a PV string refers to a removed or excluded roof module")
    add(
        "pv_layout_coverage",
        len(assigned),
        len(poses),
        status="satisfied" if set(assigned) == set(poses) and poses else "violated",
        reason="all_included_modules_must_be_assigned",
    )
    total_wp = Decimal(0)
    tracker_strings: dict[int, list[tuple[int, tuple[tuple[float, ...], ...]]]] = {}
    n_mppt, n_refs = scalar(inv, "n_mppt", "count")
    voc, voc_refs = scalar(mf, "voc_v", "voltage")
    vmpp, vmpp_refs = scalar(mf, "vmpp_v", "voltage")
    beta, beta_refs = scalar(mf, "beta_voc_pct_per_c", "temperature_coefficient")
    max_v, max_refs = scalar(inv, "max_pv_input_v", "voltage")
    mpp_window = fact(inv, "mppt_voltage_range_v", "voltage")
    for item in plan.strings:
        module_poses = [poses[mid] for mid in item.module_ids]
        used_specs = {arrays[p.array_id].module_spec_id for p in module_poses}
        if len(used_specs) != 1:
            raise InvalidInput(
                "each PV string must use a single maintained module specification"
            )
        spec = specs[next(iter(used_specs))]
        ProductSources._check_module(spec, proof)
        count = len(module_poses)
        total_wp += Decimal(str(spec.stc_power_w)) * count
        add(f"pv_tracker:{item.id}", item.mppt, n_mppt, n_refs)
        # Allowed strings per MPPT does not prove a physical connector map.
        # The input number is a project wiring label until that map is cited.
        add(
            f"pv_input:{item.id}",
            item.input,
            reason="physical_input_map_requires_evidence",
        )
        cold_v = None
        if (
            voc is not None
            and beta is not None
            and plan.minimum_ambient_c is not None
            and plan.temperature_source
        ):
            cold_v = count * voc * (1 + beta * (plan.minimum_ambient_c - 25))
            if cold_v <= 0:
                raise InvalidInput(
                    "the supplied conditions leave the linear Voc model outside its domain"
                )
        add(
            f"pv_cold_voc:{item.id}",
            cold_v,
            max_v,
            [*voc_refs, *beta_refs, *max_refs],
            unit="V",
            reason="linear_cold_voc_at_declared_ambient",
        )
        module_limit, module_refs = scalar(mf, "max_system_voltage_v", "voltage")
        # This exact maintained datum includes its own DC/IEC scope. Keep
        # the original cited text; no generic digit stripping is permitted.
        raw_limit = mf.get("max_system_voltage_v")
        if (
            module_limit is None
            and raw_limit
            and raw_limit["status"] == "text_evidence"
        ):
            match = re.fullmatch(
                r"(\d+(?:\.\d+)?) V DC \(IEC\)", str(raw_limit["raw_value"]).strip()
            )
            if match:
                module_limit = float(match[1])
        add(
            f"pv_module_voltage:{item.id}",
            cold_v,
            module_limit,
            [*voc_refs, *beta_refs, *module_refs],
            unit="V",
            reason="module_dc_system_rating_iec",
        )
        stc_vmpp = count * vmpp if vmpp is not None else None
        window = (
            mpp_window["value"]
            if mpp_window and mpp_window["shape"] == "interval"
            else None
        )
        add(
            f"pv_stc_mppt:{item.id}",
            stc_vmpp,
            cast(Json, window),
            cast(list[Json], [*vmpp_refs, *([mpp_window] if mpp_window else [])]),
            status="unresolved"
            if stc_vmpp is None or window is None
            else "satisfied"
            if window[0] <= stc_vmpp <= window[1]
            else "violated",
            unit="V",
            reason="stc_operating_point_only",
        )
        tracker_strings.setdefault(item.mppt, []).append(
            (count, tuple(sorted({tuple(p.normal_enu) for p in module_poses})))
        )
        rows.append(
            {
                "id": item.id,
                "mppt": item.mppt,
                "input": item.input,
                "module_ids": list(item.module_ids),
                "module_count": count,
                "model": spec.model,
                "stc_vmpp_v": stc_vmpp,
                "cold_voc_v": cold_v,
            }
        )
    add(
        "pv_nameplate_layout",
        float(total_wp / 1000),
        selection.pv_dc_kw,
        status="unresolved"
        if selection.pv_dc_kw is None
        else "satisfied"
        if selection.pv_dc_kw is not None
        and Decimal(str(selection.pv_dc_kw)) == total_wp / 1000
        else "violated",
        unit="kWp",
        reason="assigned_modules_must_match_selected_array_rating",
    )
    for tracker, strings in tracker_strings.items():
        maximum_strings, refs = scalar(inv, "strings_per_mppt", "count", tracker)
        add(f"pv_parallel_count:{tracker}", len(strings), maximum_strings, refs)
        for key, current_key, limit_key in (
            ("pv_stc_current", "impp_a", "mppt_max_current_a"),
            ("pv_stc_isc", "isc_a", "mppt_max_isc_a"),
        ):
            current, current_refs = scalar(mf, current_key, "current")
            maximum, refs = scalar(inv, limit_key, "current", tracker)
            add(
                f"{key}:{tracker}",
                current * len(strings) if current is not None else None,
                maximum,
                [*current_refs, *refs],
                unit="A",
                reason="parallel_current_at_stc_only",
            )
        add(
            f"pv_parallel_match:{tracker}",
            status="satisfied"
            if len(set(strings)) == 1 and len(strings[0][1]) == 1
            else "unresolved",
            reason="parallel_strings_length_and_orientation",
        )
    add("pv_operating_temperatures", reason="hot_and_cold_mpp_model_required")
    add("pv_design_current", reason="design_irradiance_and_rating_rules_required")
    add(
        "pv_wiring_protection",
        reason="cables_connectors_fuses_and_isolation_require_design",
    )
    return {
        "schema_version": 1,
        "method": "woo_layout_linear_voc_stc_v1",
        "minimum_ambient_c": plan.minimum_ambient_c,
        "temperature_source": plan.temperature_source,
        "strings": rows,
        "checks": checks,
        "assigned_modules": len(assigned),
        "included_modules": len(poses),
        "nameplate_kwp": float(total_wp / 1000),
    }
