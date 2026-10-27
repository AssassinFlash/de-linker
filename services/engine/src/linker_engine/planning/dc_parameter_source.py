"""Derive a DC planning envelope from the existing Woo equipment authority.

Keys describe quantities, never SKUs. Missing limits remain unknown; normal
maximum operating current and rated power remain limits, not guarantees of
continuous performance. No Wp, VA, peak or fault value is promoted to active kW.
"""

from __future__ import annotations

import re
from typing import Any, cast

from .canonical import Object, digest, encode
from .capacity_window import capacity_window
from .dc_energy_parameters import DcLossScenario, DcPreparedParameters
from .equipment_assessment import assess_equipment, selection_products
from .equipment_evidence import EquipmentEvidence
from .equipment_fact_resolution import (
    FactContext,
    FactUse,
    declared_battery_ports,
    resolve_fact,
)
from .equipment_inputs import EquipmentSelection
from .errors import EvidenceMissing, MethodDomainExceeded, ProductEvidenceChanged


class _Facts:
    def __init__(
        self,
        basis: Object,
        selection: EquipmentSelection,
        assumptions: DcLossScenario,
        country_code: str | None = None,
    ) -> None:
        self.evidence = EquipmentEvidence(basis)
        self.selection = selection
        self.context = FactContext(
            selection,
            {
                r["canonical_product_id"]: r
                for r in cast(list[dict[str, Any]], basis["products"])
            },
            assumptions.battery_temperature_c,
            assumptions.battery_port_id,
            country_code=country_code,
        )
        self.used: Object = {}

    def find(
        self,
        pid: int,
        keys: tuple[str, ...],
        quantity: str,
        *,
        required: bool = True,
        per_port: bool = False,
        use: FactUse = "numeric",
    ) -> Object | None:
        all_facts = cast(Object, self.evidence.compiled(pid)["facts"])
        found: list[Object] = []
        for key in keys:
            value = all_facts.get(key)
            if not isinstance(value, dict) or value.get("quantity") != quantity:
                continue
            projected = resolve_fact(value, self.context, use)
            if projected.fact is None:
                if (
                    value.get("source") is not None
                    and value.get("status") == "conditional"
                ):
                    raise EvidenceMissing(
                        f"woo_dc_condition:{pid}:{key}",
                        product_id=pid,
                        fact_id=key,
                        constraint_id=projected.issue,
                    )
                continue
            value = projected.fact
            qualifier = value.get("qualifier")
            scope_matched = (
                isinstance(qualifier, dict)
                and qualifier.get("scope") == "per_battery_port"
            )
            explicitly_per_port = "_per_battery_port_" in key or "_per_port_" in key
            if per_port and not (scope_matched or explicitly_per_port):
                continue
            if value.get("shape") != "scalar" or type(value.get("value")) not in (
                int,
                float,
            ):
                continue
            self.used[f"{pid}.{key}"] = value
            if "condition_match" in value:
                self.used[f"{pid}.{key}.condition_match"] = {
                    "scope": qualifier.get("scope")
                    if isinstance(qualifier, dict)
                    else None,
                    "parallel_stacks": self.selection.parallel_stacks,
                    "connection_matched": qualifier,
                    "matched_scenario": value["condition_match"],
                }
            found.append(value)
        if not found:
            if required:
                raise EvidenceMissing(
                    f"woo_dc_fact:{pid}:{keys[0]}",
                    product_id=pid,
                    fact_id=keys[0],
                    constraint_id="per_battery_port_scope" if per_port else None,
                )
            return None
        if len({encode(item["value"]) for item in found}) != 1:
            raise EvidenceMissing(
                f"woo_dc_fact_conflict:{pid}:{keys[0]}",
                product_id=pid,
                fact_id=keys[0],
                constraint_id="conflicting_woo_facts",
            )
        return found[0]

    def number(
        self,
        pid: int,
        keys: tuple[str, ...],
        quantity: str,
        *,
        required: bool = True,
        per_port: bool = False,
        use: FactUse = "numeric",
    ) -> float | None:
        fact = self.find(
            pid, keys, quantity, required=required, per_port=per_port, use=use
        )
        return float(cast(float, fact["value"])) if fact else None

    def capability(self, pid: int, key: str) -> bool | None:
        fact = cast(Object, self.evidence.compiled(pid)["facts"]).get(key)
        if not isinstance(fact, dict) or fact.get("source") is None:
            return None
        qualifier = fact.get("qualifier")
        if qualifier not in (None, "", {}, []):
            # This records a documented physical path, never grid permission.
            # Permission to use it is separately declared by the operation;
            # manufacturer/country approval remains an assessment obligation.
            if key != "battery_grid_charging_supported" or qualifier != {
                "quantity_kind": "documented_operating_function",
                "scope": "grid_connected_battery_charging",
                "requires_local_grid_permission": True,
            }:
                return None
        value = fact.get("raw_value")
        if (
            value is True
            or isinstance(value, str)
            and value in ("supported", "yes", "true")
        ):
            self.used[f"{pid}.{key}"] = fact
            return True
        if (
            value is False
            or isinstance(value, str)
            and value in ("not_supported", "no", "false")
        ):
            self.used[f"{pid}.{key}"] = fact
            return False
        return None


def prepare_dc_parameters(
    inputs: Object, basis: Object, assumptions: DcLossScenario
) -> DcPreparedParameters:
    selection = EquipmentSelection.read(inputs.get("equipment_selection"))
    selection_products(selection, basis)
    if (
        selection.battery_product_id is None
        or selection.modules_per_stack is None
        or selection.parallel_stacks != 1
    ):
        raise MethodDomainExceeded(
            "shared DC currently requires one explicitly configured battery stack"
        )
    brief = inputs.get("brief")
    site = brief.get("site") if isinstance(brief, dict) else None
    country = site.get("country_code") if isinstance(site, dict) else None
    facts = _Facts(
        basis,
        selection,
        assumptions,
        country
        if isinstance(country, str) and re.fullmatch(r"[A-Z]{2}", country)
        else None,
    )
    inv, battery = selection.inverter_product_id, selection.battery_product_id
    assessment = assess_equipment(
        {
            **inputs,
            "equipment_selection": selection.model_copy(
                update={"required_usable_kwh": 0, "required_discharge_ac_kw": 0}
            ).model_dump(mode="json"),
        },
        basis,
        evidence=facts.evidence,
    )
    checks = cast(list[Object], assessment["checks"])
    usable = next((check for check in checks if check["id"] == "usable_energy"), None)
    voltage = next(
        (check for check in checks if check["id"] == "battery_voltage"), None
    )
    if voltage is None or voltage.get("status") != "satisfied":
        raise EvidenceMissing(
            "woo_dc_fact:usable_energy_and_complete_voltage_window",
            product_id=battery,
            constraint_id="usable_energy_and_complete_voltage_window",
        )
    capacity = capacity_window(
        selection, usable, facts.evidence, assumptions.capacity_window_basis
    )
    voltage_facts = cast(list[Object], voltage["facts"])
    inv_range = cast(list[float], voltage_facts[0]["value"])
    battery_range = cast(list[float], voltage_facts[1]["value"])
    facts.used["usable_energy_derivation"] = usable
    facts.used["complete_voltage_window"] = voltage
    facts.used.update(capacity.source_facts)
    port_match = re.fullmatch(r"battery-([1-9][0-9]*)", assumptions.battery_port_id)
    port_count = facts.number(
        inv,
        ("battery_port_count", "number_of_battery_ports", "n_battery_ports"),
        "count",
    )
    ports = declared_battery_ports(facts.evidence.compiled(inv))
    if (
        port_count is None
        or (ports is not None and assumptions.battery_port_id not in ports)
        or (ports is None and (port_match is None or int(port_match[1]) > port_count))
    ):
        raise EvidenceMissing(
            "woo_dc_fact:explicit_selected_battery_port",
            product_id=inv,
            fact_id="battery_port_count",
            constraint_id="selected_battery_port",
        )
    facts.context = FactContext(
        selection,
        facts.context.products,
        assumptions.battery_temperature_c,
        assumptions.battery_port_id,
        int(port_count),
        facts.context.country_code,
    )
    battery_charge = facts.number(
        battery, ("max_charge_current_a",), "current", use="normal_charge_current"
    )
    battery_discharge = facts.number(
        battery, ("max_discharge_current_a",), "current", use="normal_discharge_current"
    )
    port_charge = facts.number(
        inv,
        (
            "max_battery_charge_a",
            "max_charge_current_per_battery_port_a",
            "max_battery_charge_current_per_port_a",
        ),
        "current",
        per_port=True,
        use="normal_charge_current",
    )
    port_discharge = facts.number(
        inv,
        (
            "max_battery_discharge_a",
            "max_discharge_current_per_battery_port_a",
            "max_battery_discharge_current_per_port_a",
        ),
        "current",
        per_port=True,
        use="normal_discharge_current",
    )
    terminal_charge = facts.number(
        inv,
        ("max_battery_terminal_charge_power_kw",),
        "active_power",
        required=False,
        use="battery_terminal_power",
    )
    terminal_discharge = facts.number(
        inv,
        ("max_battery_terminal_discharge_power_kw",),
        "active_power",
        required=False,
        use="battery_terminal_power",
    )
    rated_bank = facts.number(
        battery,
        ("system_rated_dc_power_w", "system_rated_dc_power_kw", "rated_power_w"),
        "active_power",
        required=False,
        use="bank_rated_dc_power",
    )
    if rated_bank is None:
        rated_module = facts.number(
            battery,
            ("module_rated_dc_power_w", "module_rated_dc_power_kw"),
            "active_power",
            required=False,
        )
        if rated_module is not None:
            rated_bank = rated_module * selection.modules_per_stack
    forward_ac = facts.number(
        inv,
        (
            "rated_ac_power_kw",
            "nominal_ac_power_kw",
            "rated_ac_power",
            "ac_output_w_nominal",
            "ac_output_kw_nominal",
            "rated_output_power_kw",
        ),
        "active_power",
        use="nominal_ac_output",
    )
    forward_dc = facts.number(
        inv, ("shared_inverter_max_dc_input_power_kw",), "active_power", required=False
    )
    pv_limit = facts.number(
        inv, ("max_pv_dc_instantaneous_input_power_kw",), "active_power", required=False
    )
    # Reverse conversion is not inferred from 'hybrid', phase count or AC
    # current. This self-consumption policy can run with the path unknown.
    reverse = facts.capability(inv, "battery_grid_charging_supported")
    reverse_ac = reverse_dc = None
    if reverse:
        if assumptions.eta_inverter_reverse is None:
            raise EvidenceMissing(
                "dc_loss_scenario:explicit_reverse_efficiency",
                constraint_id="explicit_reverse_efficiency",
            )
        active_ceiling = facts.number(
            inv,
            ("max_battery_charge_ac_power_kw", "rated_battery_charge_ac_power_kw"),
            "active_power",
            required=False,
        )
        apparent_ceiling = facts.number(
            inv,
            ("max_apparent_power_from_grid_kva",),
            "apparent_power",
            required=False,
            use="grid_input_ceiling",
        )
        bounds = [v for v in (active_ceiling, apparent_ceiling) if v is not None]
        if not bounds:
            raise EvidenceMissing(
                f"woo_dc_fact:{inv}:reverse_ac_input_ceiling",
                product_id=inv,
                fact_id="max_battery_charge_ac_power_kw",
                constraint_id="reverse_ac_input_ceiling",
            )
        reverse_ac = min(bounds)
        if apparent_ceiling is not None:
            # P^2 + Q^2 = S^2 implies |P| <= S. This is a necessary ceiling,
            # not an active-power rating, efficiency or deliverability proof.
            facts.used["reverse_ac_input_ceiling"] = {
                "relation": "abs(P)<=S",
                "role": "necessary_upper_bound_only",
                "active_power_limit_kw": active_ceiling,
                "apparent_power_limit_kva": apparent_ceiling,
                "effective_active_upper_bound_kw": reverse_ac,
            }
        reverse_dc = facts.number(
            inv, ("max_battery_charge_dc_power_kw",), "active_power", required=False
        )
    connected: Object = {
        "forward_ac_kw": forward_ac,
        "forward_dc_kw": forward_dc,
        "eta_forward": assumptions.eta_inverter_forward,
        "reverse_supported": reverse,
        "reverse_ac_kw": reverse_ac,
        "reverse_dc_kw": reverse_dc,
        "eta_reverse": assumptions.eta_inverter_reverse if reverse else None,
    }
    backup_ac = facts.number(
        inv,
        ("backup_ac_active_power_kw", "rated_backup_ac_active_power_kw"),
        "active_power",
        required=False,
    )
    outage: Object | None = (
        {
            "forward_ac_kw": backup_ac,
            "forward_dc_kw": None,
            "eta_forward": assumptions.eta_inverter_forward,
            "reverse_supported": False,
            "reverse_ac_kw": None,
            "reverse_dc_kw": None,
            "eta_reverse": None,
        }
        if backup_ac is not None
        else None
    )
    result: Object = {
        "schema_version": 1,
        "model": assumptions.model,
        "parameter_basis": "woo_selected_equipment_with_explicit_loss_scenario",
        "loss_scenario": assumptions.model_dump(mode="json"),
        "selection_sha256": digest(encode(inputs["equipment_selection"])),
        "product_revisions": dict(selection.product_revisions),
        "source_facts": facts.used,
        "usable_window_kwh": capacity.window_kwh,
        "battery": {
            "id": f"woo:{battery}",
            "operating_min_v": battery_range[0],
            "operating_max_v": battery_range[1],
            "charge_power_limit_kw": rated_bank,
            "discharge_power_limit_kw": rated_bank,
            "charge_current_a": battery_charge,
            "discharge_current_a": battery_discharge,
        },
        "selected_port": {
            "id": assumptions.battery_port_id,
            "operating_min_v": inv_range[0],
            "operating_max_v": inv_range[1],
            # A single selected battery port is below the whole converter's
            # battery-terminal ceiling. PV and reversed AC share this cap.
            "charge_power_limit_kw": terminal_charge,
            "discharge_power_limit_kw": terminal_discharge,
            "charge_current_a": port_charge,
            "discharge_current_a": port_discharge,
        },
        "pv_input_dc_kw": pv_limit,
        "dc_dc_charge_bus_kw": None,
        "dc_dc_discharge_bus_kw": None,
        "connected_bridge": connected,
        "outage_bridge": outage,
    }
    return DcPreparedParameters.read(result)


def confirm_dc_parameters(
    inputs: Object, basis: Object, parameters: DcPreparedParameters
) -> None:
    current = prepare_dc_parameters(inputs, basis, parameters.loss_scenario)
    if current != parameters:
        raise ProductEvidenceChanged(
            "prepared DC parameters differ from the selected current Woo evidence"
        )
