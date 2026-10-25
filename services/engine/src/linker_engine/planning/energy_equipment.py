"""Bind one explicit replay envelope to its frozen Woo equipment evidence.

This assessment checks the stated scenario against the selected configuration.
It does not replace a shared-port/DC converter model or turn scenario losses
into manufacturer performance. Both missing evidence and contradictions are
retained, separately from the numerical replay's conservation checks.
"""

from __future__ import annotations

from typing import cast

from .battery_model import BatteryModel
from .canonical import Json, Object, digest, encode
from .energy_inputs import EnergyInputs
from .equipment_assessment import assess_equipment
from .equipment_evidence import EquipmentEvidence
from .equipment_inputs import EquipmentSelection

MODEL = "selected_woo_scenario_envelope_v1"


def assess_energy_equipment(
    inputs: Object, basis: Object, model: BatteryModel
) -> Object:
    selection = EquipmentSelection.read(inputs.get("equipment_selection"))
    scenario = EnergyInputs.from_project(inputs)
    # The selection's manually entered sizing target is not the parameter set
    # that was simulated. Qualify the actual frozen replay window/power here.
    demand = selection.model_copy(
        update={
            "required_usable_kwh": model.usable_window_kwh,
            "required_discharge_ac_kw": model.discharge_ac_kw,
        }
    )
    evidence = EquipmentEvidence(basis)
    assessment = assess_equipment(
        {**inputs, "equipment_selection": demand.model_dump(mode="json")},
        basis,
        evidence=evidence,
    )
    checks = cast(list[Object], assessment["checks"])
    fields = cast(Object, evidence.compiled(selection.inverter_product_id)["facts"])
    charge = fields.get("continuous_battery_charge_ac_power_kw")
    charge_fact = charge if isinstance(charge, dict) else None
    limit = (
        charge_fact.get("value")
        if charge_fact is not None
        and charge_fact.get("status") == "typed"
        and charge_fact.get("shape") == "scalar"
        and charge_fact.get("quantity") == "active_power"
        else None
    )
    checks.append(
        {
            "id": "continuous_battery_ac_charge",
            "status": "unresolved"
            if limit is None
            else "satisfied"
            if model.charge_ac_kw <= cast(float, limit)
            else "violated",
            "reason": "cited_continuous_ac_charge_limit"
            if limit is not None
            else "current_cited_limit_missing_or_conditional",
            "actual": limit,
            "required": model.charge_ac_kw,
            "facts": cast(list[Json], [charge_fact] if charge_fact else []),
        }
    )
    outage = any(period.mode == "outage" for period in scenario.schedule)
    mode_matches = not outage or selection.operating_mode == "backup"
    checks.append(
        {
            "id": "scenario_operating_mode",
            "status": "satisfied" if mode_matches else "violated",
            "reason": "scenario_mode_matches_selection"
            if mode_matches
            else "outage_requires_backup_selection",
            "actual": None,
            "required": None,
            "facts": [],
        }
    )
    # None of these manufacturer properties follows from a maximum efficiency,
    # DC current, general pairing, or an AC-bus trace. Do not silently convert
    # those facts into missing continuous ports or loss/temperature curves.
    for identifier, reason in (
        ("scenario_parameter_basis", "scenario_losses_not_manufacturer_performance"),
        ("scenario_model_domain", "selected_port_topology_requires_assessment"),
    ):
        checks.append(
            {
                "id": identifier,
                "status": "unresolved",
                "reason": reason,
                "actual": None,
                "required": None,
                "facts": [],
            }
        )
    assessment["overall_status"] = (
        "violated"
        if any(check["status"] == "violated" for check in checks)
        else "unresolved"
    )
    assessment["equipment_status"] = assessment["overall_status"]
    assessment["bill_of_materials_status"] = "unresolved"
    return {
        "schema_version": 1,
        "model": MODEL,
        "selection": inputs["equipment_selection"],
        "selection_sha256": digest(encode(inputs["equipment_selection"])),
        "scenario_model": model.document(),
        "assessment": assessment,
        "performance_status": "not_established_by_scenario_envelope",
    }
