"""Common-meter metrics and individually retained storage traces.

Summed inventories are presentation totals only. Actuation and verification
always use the named states, ports, reserves and directional unit limits.
"""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import cast

from .canonical import Object, decode_object, encode
from .energy_metrics import _ratio
from .energy_origins import EnergyOrigins
from .errors import InvalidInput
from .plant_energy_model import PlantFlow, StorageFlow


def inventory(values: list[EnergyOrigins]) -> EnergyOrigins:
    return EnergyOrigins(
        math.fsum(v.pv_kwh for v in values),
        math.fsum(v.grid_kwh for v in values),
        math.fsum(v.initial_unknown_kwh for v in values),
    )


def flow_document(flow: PlantFlow) -> Object:
    site, dt = flow.frame.site, flow.frame.site.interval.hours
    frame = asdict(site)
    frame["interval"] = {
        "start_utc": site.interval.start.isoformat(),
        "end_utc": site.interval.end.isoformat(),
    }
    units = []
    for unit in flow.units:
        units.append(
            {
                "unit_id": unit.unit.id,
                "mode": unit.mode,
                "reserve_kwh": unit.reserve_kwh,
                "model": unit.unit.for_mode(unit.mode).document(),
                "before": unit.before.document(),
                "after": unit.after.document(),
                "command": asdict(unit.command),
                "charge_kw": unit.received_ac.total / dt,
                "discharge_kw": unit.delivered_ac.total / dt,
                "received_ac": unit.received_ac.document(),
                "delivered_ac": unit.delivered_ac.document(),
                "withdrawn_internal": unit.withdrawn_internal.document(),
                "standing_loss": unit.standing_loss.document(),
                "internal_aux": unit.internal_aux.document(),
                "internal_aux_unserved_kwh": unit.internal_aux_unserved_kwh,
                "charge_command_unmet_kw": max(
                    unit.command.charge_kw - unit.received_ac.total / dt, 0.0
                ),
                "discharge_command_unmet_kw": max(
                    unit.command.discharge_kw - unit.delivered_ac.total / dt, 0.0
                ),
            }
        )
    return decode_object(
        encode(
            cast(
                Object,
                {
                    "frame": frame,
                    "unit_reserves_kwh": flow.frame.reserves_kwh,
                    "units": units,
                    "inventory_boundary": "sum_of_distinct_units_for_presentation_only",
                    "before": inventory([u.before for u in flow.units]).document(),
                    "after": inventory([u.after for u in flow.units]).document(),
                    "standing_loss": inventory(
                        [u.standing_loss for u in flow.units]
                    ).document(),
                    "internal_aux": inventory(
                        [u.internal_aux for u in flow.units]
                    ).document(),
                    "internal_aux_unserved_kwh": math.fsum(
                        u.internal_aux_unserved_kwh for u in flow.units
                    ),
                    "discharged_internal": inventory(
                        [u.withdrawn_internal for u in flow.units]
                    ).document(),
                    "discharged_to_load_ac": flow.battery_to_load_ac.document(),
                    "pv_available_kw": flow.pv_available_kwh / dt,
                    "pv_to_load_kw": flow.direct_pv_to_load_kwh / dt,
                    "pv_to_aux_kw": flow.direct_pv_to_aux_kwh / dt,
                    "pv_charge_kw": flow.direct_pv_to_charge_kwh / dt,
                    "grid_charge_kw": flow.grid_charge_kwh / dt,
                    "discharge_kw": math.fsum(u.delivered_ac.total for u in flow.units)
                    / dt,
                    "charge_kw": math.fsum(u.received_ac.total for u in flow.units)
                    / dt,
                    "grid_to_load_kw": flow.grid_to_load_kwh / dt,
                    "grid_to_aux_kw": flow.grid_to_aux_kwh / dt,
                    "import_kw": flow.grid_import_kwh / dt,
                    "export_kw": flow.export_sources.total / dt,
                    "curtailed_kw": flow.curtailed_sources.total / dt,
                    "unserved_load_kw": flow.unserved_load_kwh / dt,
                    "unserved_aux_kw": flow.unserved_aux_kwh / dt,
                },
            )
        )
    )


def metrics(flows: tuple[PlantFlow, ...]) -> Object:
    if not flows:
        raise InvalidInput("joint metrics require a nonempty horizon")
    load = math.fsum(f.frame.site.load_kw * f.frame.site.interval.hours for f in flows)
    scopes = {f.frame.site.load_measurement for f in flows}
    whole_site = scopes == {"gross_load"}
    gross_reason = (
        None if whole_site else "critical_or_mixed_demand_is_not_whole_site_load"
    )
    solar = math.fsum(f.load_sources.pv_kwh for f in flows)
    available = math.fsum(f.pv_available_kwh for f in flows)
    curtailed = math.fsum(f.curtailed_sources.total for f in flows)
    generated = math.fsum(f.pv_available_kwh - f.curtailed_sources.total for f in flows)
    direct = math.fsum(f.direct_pv_to_load_kwh for f in flows)
    aux = math.fsum(f.direct_pv_to_aux_kwh for f in flows)
    pv_charge = math.fsum(f.direct_pv_to_charge_kwh for f in flows)
    onsite = math.fsum((direct, aux, pv_charge))
    units = []
    histories: dict[str, list[StorageFlow]] = {u.unit.id: [] for u in flows[0].units}
    for flow in flows:
        for unit in flow.units:
            histories[unit.unit.id].append(unit)
    for first in flows[0].units:
        uid = first.unit.id
        history = histories[uid]
        units.append(
            {
                "unit_id": uid,
                "stored_initial": history[0].before.document(),
                "stored_final": history[-1].after.document(),
                "charge_ac_kwh": math.fsum(u.received_ac.total for u in history),
                "discharge_ac_kwh": math.fsum(u.delivered_ac.total for u in history),
                "usable_window_kwh": first.unit.model.usable_window_kwh,
            }
        )
    return cast(
        Object,
        {
            "load_demand_kwh": load,
            "load_measurement_scope": next(iter(scopes))
            if len(scopes) == 1
            else "mixed",
            "gross_load_kwh": load if whole_site else None,
            "gross_load_undefined_reason": gross_reason,
            "unserved_load_kwh": math.fsum(f.unserved_load_kwh for f in flows),
            "pv_potential_before_mode_kwh": math.fsum(
                f.frame.site.pv_potential_kw * f.frame.site.interval.hours
                for f in flows
            ),
            "pv_available_before_curtail_kwh": available,
            "pv_curtailed_kwh": curtailed,
            "pv_generated_ac_kwh": generated,
            "pv_direct_load_kwh": direct,
            "pv_battery_to_load_kwh": math.fsum(
                f.battery_to_load_ac.pv_kwh for f in flows
            ),
            "solar_load_kwh": solar,
            "pv_charge_ac_kwh": pv_charge,
            "pv_direct_aux_ac_kwh": aux,
            "grid_import_kwh": math.fsum(f.grid_import_kwh for f in flows),
            "pv_export_kwh": math.fsum(f.export_sources.total for f in flows),
            "grid_charge_ac_kwh": math.fsum(f.grid_charge_kwh for f in flows),
            "grid_origin_battery_to_load_kwh": math.fsum(
                f.battery_to_load_ac.grid_kwh for f in flows
            ),
            "initial_unknown_battery_to_load_kwh": math.fsum(
                f.battery_to_load_ac.initial_unknown_kwh for f in flows
            ),
            "charge_conversion_loss_kwh": math.fsum(
                u.charge_loss.total for f in flows for u in f.units
            ),
            "discharge_conversion_loss_kwh": math.fsum(
                u.discharge_loss.total for f in flows for u in f.units
            ),
            "standing_loss_kwh": math.fsum(
                u.standing_loss.total for f in flows for u in f.units
            ),
            "internal_aux_supplied_kwh": math.fsum(
                u.internal_aux.total for f in flows for u in f.units
            ),
            "internal_aux_unserved_kwh": math.fsum(
                u.internal_aux_unserved_kwh for f in flows for u in f.units
            ),
            "aux_ac_unserved_kwh": math.fsum(f.unserved_aux_kwh for f in flows),
            "maximum_interval_average_import_kw": max(
                f.grid_import_kwh / f.frame.site.interval.hours for f in flows
            ),
            "stored_initial": inventory([u.before for u in flows[0].units]).document(),
            "stored_final": inventory([u.after for u in flows[-1].units]).document(),
            "units": units,
            "solar_autarky": _ratio(solar, load, "gross_load_is_zero")
            if whole_site
            else {"value": None, "undefined_reason": gross_reason},
            "solar_load_share_of_requested_demand": _ratio(
                solar, load, "requested_load_is_zero"
            ),
            "pv_input_self_use": _ratio(onsite, generated, "pv_generation_is_zero"),
            "pv_onsite_available_share": _ratio(
                onsite, available, "pv_availability_is_zero"
            ),
            "definitions": {
                "inventory": "separate_physical_units; total_is_presentation_only",
                "source_accounting": "proportional_mixing_in_each_bank_and_at_common_ac_bus; grid_and_unknown_are_not_solar",
                "solar_autarky": "PV-origin energy delivered to whole-site load / whole-site load demand",
                "pv_input_self_use": "new AC PV delivered directly to load, auxiliaries or storage / new AC PV generation after curtailment",
                "control": "proportional_available_power_self_consumption_v1; no forecast or optimality claim",
            },
        },
    )
