"""Derive a DC planning envelope from the existing Woo equipment authority.

Keys describe quantities, never SKUs. Missing limits remain unknown; normal
maximum operating current and rated power remain limits, not guarantees of
continuous performance. No Wp, VA, peak or fault value is promoted to active kW.
"""

from __future__ import annotations

import re
from typing import cast

from .canonical import Object, digest, encode
from .dc_energy_parameters import DcLossScenario, DcPreparedParameters
from .equipment_assessment import assess_equipment, selection_products
from .equipment_evidence import EquipmentEvidence
from .equipment_inputs import EquipmentSelection
from .errors import EvidenceMissing, MethodDomainExceeded, ProductEvidenceChanged


class _Facts:
    def __init__(self, basis: Object, selection: EquipmentSelection) -> None:
        self.evidence = EquipmentEvidence(basis)
        self.selection = selection
        self.used: Object = {}

    def find(
        self,
        pid: int,
        keys: tuple[str, ...],
        quantity: str,
        *,
        required: bool = True,
        per_port: bool = False,
    ) -> Object | None:
        all_facts = cast(Object, self.evidence.compiled(pid)["facts"])
        found: list[Object] = []
        for key in keys:
            value = all_facts.get(key)
            if not isinstance(value, dict) or value.get("quantity") != quantity:
                continue
            qualifier = value.get("qualifier")
            scope_matched = qualifier == {"scope": "per_battery_port"} or (
                self.selection.parallel_stacks == 1
                and qualifier
                == {"scope": "per_battery_port", "connection": "one_stack_per_port"}
            )
            if value.get("status") != "typed" and not (
                per_port and scope_matched and value.get("status") == "conditional"
            ):
                continue
            explicitly_per_port = "_per_battery_port_" in key or "_per_port_" in key
            if per_port and not (scope_matched or explicitly_per_port):
                continue
            if value.get("shape") == "ordered_values":
                columns, values = value.get("columns"), value.get("value")
                if (
                    not isinstance(columns, list)
                    or not isinstance(values, list)
                    or len(columns) != len(values)
                ):
                    continue
                matched = [
                    item
                    for column, item in zip(columns, values, strict=True)
                    if isinstance(column, dict)
                    and column
                    == {"modules_per_stack": self.selection.modules_per_stack}
                ]
                if len(matched) != 1 or not isinstance(matched[0], dict):
                    continue
                value = {
                    **value,
                    "shape": matched[0].get("shape"),
                    "value": matched[0].get("value"),
                    "selected_modules_per_stack": self.selection.modules_per_stack,
                }
            if value.get("shape") != "scalar":
                continue
            if type(value.get("value")) not in (int, float):
                continue
            self.used[f"{pid}.{key}"] = value
            if per_port and scope_matched:
                self.used[f"{pid}.{key}.condition_match"] = {
                    "scope": "per_battery_port",
                    "parallel_stacks": self.selection.parallel_stacks,
                    "connection_matched": qualifier,
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
    ) -> float | None:
        fact = self.find(pid, keys, quantity, required=required, per_port=per_port)
        return float(cast(float, fact["value"])) if fact else None

    def capability(self, pid: int, key: str) -> bool | None:
        fact = cast(Object, self.evidence.compiled(pid)["facts"]).get(key)
        if (
            not isinstance(fact, dict)
            or fact.get("source") is None
            or fact.get("qualifier") not in (None, "", {}, [])
        ):
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
    facts = _Facts(basis, selection)
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
    if (
        usable is None
        or usable.get("status") != "satisfied"
        or type(usable.get("actual")) not in (int, float)
        or voltage is None
        or voltage.get("status") != "satisfied"
    ):
        raise EvidenceMissing(
            "woo_dc_fact:usable_energy_and_complete_voltage_window",
            product_id=battery,
            constraint_id="usable_energy_and_complete_voltage_window",
        )
    voltage_facts = cast(list[Object], voltage["facts"])
    inv_range = cast(list[float], voltage_facts[0]["value"])
    battery_range = cast(list[float], voltage_facts[1]["value"])
    facts.used["usable_energy_derivation"] = usable
    facts.used["complete_voltage_window"] = voltage
    port_match = re.fullmatch(r"battery-([1-9][0-9]*)", assumptions.battery_port_id)
    port_count = facts.number(
        inv,
        ("battery_port_count", "number_of_battery_ports", "n_battery_ports"),
        "count",
    )
    if port_match is None or port_count is None or int(port_match[1]) > port_count:
        raise EvidenceMissing(
            "woo_dc_fact:explicit_selected_battery_port",
            product_id=inv,
            fact_id="battery_port_count",
            constraint_id="selected_battery_port",
        )
    battery_charge = facts.number(battery, ("max_charge_current_a",), "current")
    battery_discharge = facts.number(battery, ("max_discharge_current_a",), "current")
    port_charge = facts.number(
        inv,
        (
            "max_battery_charge_a",
            "max_charge_current_per_battery_port_a",
            "max_battery_charge_current_per_port_a",
        ),
        "current",
        per_port=True,
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
    )
    rated_bank = facts.number(
        battery,
        ("system_rated_dc_power_w", "system_rated_dc_power_kw"),
        "active_power",
        required=False,
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
        reverse_ac = facts.number(
            inv,
            ("max_battery_charge_ac_power_kw", "rated_battery_charge_ac_power_kw"),
            "active_power",
        )
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
        "usable_window_kwh": usable["actual"],
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
            "charge_power_limit_kw": None,
            "discharge_power_limit_kw": None,
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
