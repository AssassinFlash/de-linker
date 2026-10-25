"""Frozen DC trace and metrics preserve terminal/DC-bus/AC measurement stages."""

from __future__ import annotations

import math
from dataclasses import asdict, fields

from .canonical import Object
from .dc_battery_model import DcBatteryModel
from .dc_frame import DcFlows
from .energy_origins import EnergyOrigins
from .errors import InvalidInput, NumericalFailure


def flow_document(flow: DcFlows) -> Object:
    frame = flow.frame
    result: Object = {
        "frame": {
            "interval": {
                "start_utc": frame.interval.start.isoformat(),
                "end_utc": frame.interval.end.isoformat(),
            },
            "load_kw": frame.load_kw,
            "pv_available_dc_kw": frame.pv_available_dc_kw,
            "aux_ac_kw": frame.aux_ac_kw,
            "aux_dc_kw": frame.aux_dc_kw,
            "load_measurement": frame.load_measurement,
            "limits": asdict(frame.limits),
        },
        "command": asdict(flow.command),
    }
    for field in fields(flow):
        if field.name in ("frame", "command"):
            continue
        value = getattr(flow, field.name)
        result[field.name] = (
            value.document() if isinstance(value, EnergyOrigins) else value
        )
    return result


def metrics(flows: tuple[DcFlows, ...], model: DcBatteryModel) -> Object:
    if not flows:
        raise InvalidInput("DC metrics require a nonempty period")

    def energy(name: str) -> float:
        value = math.fsum(
            float(getattr(flow, name)) * flow.frame.interval.hours for flow in flows
        )
        if not math.isfinite(value):
            raise NumericalFailure("DC period energy is not finite")
        return value

    load = math.fsum(flow.frame.load_kw * flow.frame.interval.hours for flow in flows)
    pv_battery_load = math.fsum(flow.discharged_to_load_ac.pv_kwh for flow in flows)
    pv_direct = energy("pv_to_load_ac_kw")
    solar_load = pv_direct + pv_battery_load
    available = energy("pv_available_dc_kw")
    generated = math.fsum(
        (
            energy("pv_to_aux_dc_kw"),
            energy("pv_charge_bus_dc_kw"),
            energy("pv_to_inverter_dc_kw"),
        )
    )
    onsite = math.fsum(
        (
            energy("pv_to_aux_dc_kw"),
            energy("pv_charge_bus_dc_kw"),
            math.fsum(
                (flow.pv_to_load_ac_kw + flow.pv_to_aux_ac_kw)
                / model.bridge(flow.frame.limits.mode).eta_forward
                * flow.frame.interval.hours
                for flow in flows
            ),
        )
    )
    scopes = {flow.frame.load_measurement for flow in flows}
    whole_site = scopes == {"gross_load"}
    gross_reason = (
        None if whole_site else "requested_load_scope_is_not_whole_site_gross"
    )

    def ratio(numerator: float, denominator: float, reason: str) -> Object:
        if denominator == 0:
            return {"value": None, "undefined_reason": reason}
        value = numerator / denominator
        if not math.isfinite(value):
            raise NumericalFailure("DC period ratio is not finite")
        return {"value": value, "undefined_reason": None}

    result: Object = {
        "load_demand_kwh": load,
        "load_measurement_scope": next(iter(scopes)) if len(scopes) == 1 else "mixed",
        "gross_load_kwh": load if whole_site else None,
        "gross_load_undefined_reason": gross_reason,
        "unserved_load_kwh": energy("unserved_load_ac_kw"),
        "pv_available_before_curtail_dc_kwh": available,
        "pv_generated_dc_kwh": generated,
        "pv_curtailed_dc_kwh": energy("pv_curtailed_dc_kw"),
        "pv_input_curtailed_dc_kwh": energy("pv_input_curtailed_dc_kw"),
        "pv_direct_load_kwh": pv_direct,
        "pv_battery_to_load_kwh": pv_battery_load,
        "solar_load_kwh": solar_load,
        "pv_charge_bus_dc_kwh": energy("pv_charge_bus_dc_kw"),
        "grid_charge_bus_dc_kwh": energy("grid_charge_bus_dc_kw"),
        "grid_import_kwh": energy("import_ac_kw"),
        "pv_export_ac_kwh": energy("export_ac_kw"),
        "grid_origin_battery_to_load_kwh": math.fsum(
            flow.discharged_to_load_ac.grid_kwh for flow in flows
        ),
        "initial_unknown_battery_to_load_kwh": math.fsum(
            flow.discharged_to_load_ac.initial_unknown_kwh for flow in flows
        ),
        "shared_inverter_forward_loss_kwh": math.fsum(
            flow.inverter_forward_dc_kw
            * (1 - model.bridge(flow.frame.limits.mode).eta_forward)
            * flow.frame.interval.hours
            for flow in flows
        ),
        "shared_inverter_reverse_loss_kwh": math.fsum(
            (flow.inverter_reverse_ac_kw - flow.inverter_reverse_dc_kw)
            * flow.frame.interval.hours
            for flow in flows
        ),
        "charge_dc_dc_loss_kwh": (
            energy("pv_charge_bus_dc_kw") + energy("grid_charge_bus_dc_kw")
        )
        * (1 - model.eta_bus_to_battery),
        "charge_internal_loss_kwh": energy("charge_terminal_dc_kw")
        * (1 - model.eta_store_charge),
        "discharge_dc_dc_loss_kwh": energy("discharge_terminal_dc_kw")
        * (1 - model.eta_battery_to_bus),
        "discharge_internal_loss_kwh": math.fsum(
            flow.discharged_internal.total * (1 - model.eta_store_discharge)
            for flow in flows
        ),
        "standing_loss_kwh": math.fsum(flow.standing_loss.total for flow in flows),
        "internal_aux_supplied_kwh": math.fsum(
            flow.internal_aux.total for flow in flows
        ),
        "internal_aux_unserved_kwh": math.fsum(
            flow.internal_aux_unserved_kwh for flow in flows
        ),
        "aux_ac_unserved_kwh": energy("unserved_aux_ac_kw"),
        "aux_dc_unserved_kwh": energy("unserved_aux_dc_kw"),
        "maximum_interval_average_import_kw": max(flow.import_ac_kw for flow in flows),
        "stored_initial": flows[0].before.document(),
        "stored_final": flows[-1].after.document(),
        "solar_autarky": ratio(solar_load, load, "gross_load_is_zero")
        if whole_site
        else {"value": None, "undefined_reason": gross_reason},
        "solar_load_share_of_requested_demand": ratio(
            solar_load, load, "requested_load_is_zero"
        ),
        "pv_input_self_use": ratio(onsite, generated, "pv_generation_is_zero"),
        "pv_onsite_available_share": ratio(
            onsite, available, "pv_availability_is_zero"
        ),
        "definitions": {
            "solar_autarky": "(PV_direct_AC_to_customer_load + PV_origin_battery_AC_to_customer_load) / gross_AC_customer_load_demand",
            "pv_input_self_use": "(PV_generated_DC_at_bus - PV_export_AC/eta_forward) / PV_generated_DC_at_bus",
            "pv_generated_dc_kwh": "PV_available_at_DC_bus - PV_curtailed_at_DC_bus; excludes_PV_input_curtailment",
            "inventory_origin": "proportional_mixing; initial_unknown_and_grid_are_not_solar",
            "boundary": "shared_DC_bus_and_one_inverter; battery_export_excluded; AC_and_DC_aux_separate_from_customer_load",
        },
    }
    # Nothing here substitutes the separate reference-AC yield for this DC
    # dispatch measurement, or counts unknown/grid inventory as solar supply.
    return result
