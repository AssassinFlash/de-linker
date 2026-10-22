"""Period metrics with source accounting and named undefined denominators."""

from __future__ import annotations

import math

from .battery_model import BatteryModel
from .canonical import Object
from .dispatch_frame import Flows
from .errors import InvalidInput, NumericalFailure


def _ratio(numerator: float, denominator: float, reason: str) -> Object:
    if denominator == 0:
        return {"value": None, "undefined_reason": reason}
    value = numerator / denominator
    if not math.isfinite(value):
        raise NumericalFailure("energy ratio is not finite")
    return {"value": value, "undefined_reason": None}


def metrics(flows: tuple[Flows, ...], model: BatteryModel) -> Object:
    if not flows:
        raise InvalidInput("metrics need a nonempty period")
    load = math.fsum(flow.frame.load_kw * flow.frame.interval.hours for flow in flows)
    pv_direct_load = math.fsum(
        flow.pv_to_load_kw * flow.frame.interval.hours for flow in flows
    )
    pv_battery_load = math.fsum(flow.discharged_to_load_ac.pv_kwh for flow in flows)
    pv_aux = math.fsum(flow.pv_to_aux_kw * flow.frame.interval.hours for flow in flows)
    pv_charge = math.fsum(
        flow.pv_charge_kw * flow.frame.interval.hours for flow in flows
    )
    available_pv = math.fsum(
        flow.pv_available_kw * flow.frame.interval.hours for flow in flows
    )
    curtailed = math.fsum(
        flow.curtailed_kw * flow.frame.interval.hours for flow in flows
    )
    generated_pv = math.fsum(
        (flow.pv_to_load_kw + flow.pv_to_aux_kw + flow.pv_charge_kw + flow.export_kw)
        * flow.frame.interval.hours
        for flow in flows
    )
    solar_load = pv_direct_load + pv_battery_load
    onsite_pv_input = pv_direct_load + pv_aux + pv_charge
    return {
        "gross_load_kwh": load,
        "unserved_load_kwh": math.fsum(
            flow.unserved_load_kw * flow.frame.interval.hours for flow in flows
        ),
        "pv_potential_before_mode_kwh": math.fsum(
            flow.frame.pv_potential_kw * flow.frame.interval.hours for flow in flows
        ),
        "pv_available_before_curtail_kwh": available_pv,
        "pv_curtailed_kwh": curtailed,
        "pv_generated_ac_kwh": generated_pv,
        "pv_direct_load_kwh": pv_direct_load,
        "pv_battery_to_load_kwh": pv_battery_load,
        "solar_load_kwh": solar_load,
        "pv_charge_ac_kwh": pv_charge,
        "pv_direct_aux_ac_kwh": pv_aux,
        "grid_import_kwh": math.fsum(
            flow.import_kw * flow.frame.interval.hours for flow in flows
        ),
        "pv_export_kwh": math.fsum(
            flow.export_kw * flow.frame.interval.hours for flow in flows
        ),
        "grid_charge_ac_kwh": math.fsum(
            flow.grid_charge_kw * flow.frame.interval.hours for flow in flows
        ),
        "grid_origin_battery_to_load_kwh": math.fsum(
            flow.discharged_to_load_ac.grid_kwh for flow in flows
        ),
        "initial_unknown_battery_to_load_kwh": math.fsum(
            flow.discharged_to_load_ac.initial_unknown_kwh for flow in flows
        ),
        "charge_conversion_loss_kwh": math.fsum(
            (1 - model.eta_charge) * flow.charge_kw * flow.frame.interval.hours
            for flow in flows
        ),
        "discharge_conversion_loss_kwh": math.fsum(
            (1 - model.eta_discharge) * flow.discharged_internal.total for flow in flows
        ),
        "standing_loss_kwh": math.fsum(flow.standing_loss.total for flow in flows),
        "internal_aux_supplied_kwh": math.fsum(
            flow.internal_aux.total for flow in flows
        ),
        "internal_aux_unserved_kwh": math.fsum(
            flow.internal_aux_unserved_kwh for flow in flows
        ),
        "aux_ac_unserved_kwh": math.fsum(
            flow.unserved_aux_kw * flow.frame.interval.hours for flow in flows
        ),
        "maximum_interval_average_import_kw": max(flow.import_kw for flow in flows),
        "stored_initial": flows[0].before.document(),
        "stored_final": flows[-1].after.document(),
        "solar_autarky": _ratio(solar_load, load, "gross_load_is_zero"),
        "pv_input_self_use": _ratio(
            onsite_pv_input, generated_pv, "pv_generation_is_zero"
        ),
        "pv_onsite_available_share": _ratio(
            onsite_pv_input, available_pv, "pv_availability_is_zero"
        ),
        "definitions": {
            "solar_autarky": "(PV_direct_to_customer_load + PV_origin_battery_to_customer_load) / gross_customer_load_demand",
            "pv_input_self_use": "(PV_direct_load + PV_direct_system_aux + PV_charge_input) / PV_generated_after_curtailment",
            "pv_onsite_available_share": "(PV_direct_load + PV_direct_system_aux + PV_charge_input) / PV_available_before_curtailment",
            "inventory_origin": "proportional_mixing; initial_unknown_and_grid_are_not_solar",
            "boundary": "single_AC_bus; battery_export_excluded; system_aux_separate_from_customer_load",
        },
    }
