"""Named DC stages plus a common AC result; no ratio adds AC and DC PV input."""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import cast

from .canonical import Json, Object
from .dc_plant_model import DcPlantFlow, DcPlantStorageFlow
from .energy_metrics import _ratio
from .errors import InvalidInput
from .plant_energy_output import inventory


def flow_document(flow: DcPlantFlow) -> Object:
    site, dt = flow.frame.site, flow.frame.site.interval.hours
    frame = asdict(site)
    frame["interval"] = {
        "start_utc": site.interval.start.isoformat(),
        "end_utc": site.interval.end.isoformat(),
    }
    units: list[Json] = []
    for unit in flow.units:
        p, port = unit.port.plan, unit.port
        units.append(
            {
                "unit_id": unit.unit.id,
                "mode": p.frame.mode,
                "reserve_kwh": p.frame.reserve_kwh,
                "before": p.before.document(),
                "after": port.after.document(),
                "command": asdict(p.command),
                "charge_kw": port.charge_terminal_dc_kw,
                "discharge_kw": p.discharge_terminal_dc_kw,
                "charge_command_unmet_kw": max(
                    p.command.charge_kw - port.charge_terminal_dc_kw, 0.0
                ),
                "discharge_command_unmet_kw": max(
                    p.command.discharge_kw - p.discharge_terminal_dc_kw, 0.0
                ),
                "measurement": "battery_DC_terminal",
                "pv_available_dc_kw": p.pv_available_dc_kw,
                "pv_to_aux_dc_kw": p.pv_to_aux_dc_kw,
                "pv_charge_bus_dc_kw": p.pv_charge_bus_dc_kw,
                "pv_to_inverter_dc_kw": p.pv_to_inverter_dc_kw,
                "pv_curtailed_dc_kw": p.pv_curtailed_dc_kw,
                "pv_input_curtailed_dc_kw": p.pv_input_curtailed_dc_kw,
                "battery_to_aux_dc_kw": p.battery_to_aux_dc_kw,
                "battery_to_inverter_dc_kw": p.battery_to_inverter_dc_kw,
                "standing_loss": p.standing_loss.document(),
                "internal_aux": p.internal_aux.document(),
                "internal_aux_unserved_kwh": p.internal_aux_unserved_kwh,
                "withdrawn_internal": p.discharged_internal.document(),
                "battery_delivered_ac": p.battery_forward_ac.document(),
                "inverter_forward_ac_kw": p.forward_ac_kw,
                "incoming_aux_ac": port.incoming_aux_ac.document(),
                "incoming_charge_ac": port.incoming_charge_ac.document(),
                "incoming_aux_dc": port.incoming_aux_dc.document(),
                "incoming_charge_dc": port.incoming_charge_dc.document(),
                "unserved_aux_dc_kw": port.unserved_aux_dc_kw,
            }
        )
    return cast(
        Object,
        {
            "frame": frame,
            "units": units,
            "unit_reserves_kwh": dict(flow.frame.reserves_kwh),
            "inventory_boundary": "sum_of_distinct_units_for_presentation_only",
            "before": inventory([u.port.plan.before for u in flow.units]).document(),
            "after": inventory([u.port.after for u in flow.units]).document(),
            "pv_available_kw": (
                flow.independent_pv_available_kwh - flow.independent_pv_curtailed_kwh
            )
            / dt
            + math.fsum(u.port.plan.pv_forward_ac_kw for u in flow.units),
            "charge_kw": math.fsum(u.port.charge_terminal_dc_kw for u in flow.units),
            "discharge_kw": math.fsum(
                u.port.plan.discharge_terminal_dc_kw for u in flow.units
            ),
            "import_kw": flow.grid_import_kwh / dt,
            "export_kw": flow.export_sources.total / dt,
            "unserved_load_kw": flow.unserved_load_kwh / dt,
            "unserved_aux_kw": flow.unserved_aux_kwh / dt,
        },
    )


def metrics(flows: tuple[DcPlantFlow, ...]) -> Object:
    if not flows:
        raise InvalidInput("DC plant metrics require a nonempty horizon")
    histories: dict[str, list[DcPlantStorageFlow]] = {
        u.unit.id: [] for u in flows[0].units
    }
    for f in flows:
        for unit in f.units:
            histories[unit.unit.id].append(unit)
    units: list[Json] = []
    for uid, history in histories.items():

        def energy(
            name: str,
            *,
            plan: bool = False,
            _history: list[DcPlantStorageFlow] = history,
        ) -> float:
            return math.fsum(
                float(getattr(u.port.plan if plan else u.port, name))
                * u.port.plan.frame.interval.hours
                for u in _history
            )

        available = energy("pv_available_dc_kw", plan=True)
        curtailed = energy("pv_curtailed_dc_kw", plan=True)
        units.append(
            {
                "unit_id": uid,
                "usable_window_kwh": history[0].unit.model.usable_window_kwh,
                "stored_initial": history[0].port.plan.before.document(),
                "stored_final": history[-1].port.after.document(),
                "charge_ac_kwh": math.fsum(
                    u.port.incoming_charge_ac.total for u in history
                ),
                "discharge_ac_kwh": math.fsum(
                    u.port.plan.battery_forward_ac.total for u in history
                ),
                "charge_terminal_dc_kwh": energy("charge_terminal_dc_kw"),
                "discharge_terminal_dc_kwh": energy(
                    "discharge_terminal_dc_kw", plan=True
                ),
                "local_pv_charge_bus_dc_kwh": energy("pv_charge_bus_dc_kw", plan=True),
                "pv_available_dc_kwh": available,
                "pv_generated_dc_kwh": available - curtailed,
                "pv_curtailed_dc_kwh": curtailed,
                "pv_input_curtailed_dc_kwh": energy(
                    "pv_input_curtailed_dc_kw", plan=True
                ),
            }
        )
    load = math.fsum(f.frame.site.load_kw * f.frame.site.interval.hours for f in flows)
    scopes = {f.frame.site.load_measurement for f in flows}
    whole_site = scopes == {"gross_load"}
    reason = None if whole_site else "critical_or_mixed_demand_is_not_whole_site_load"
    solar = math.fsum(f.load_sources.pv_kwh for f in flows)
    all_units = [u for f in flows for u in f.units]
    return cast(
        Object,
        {
            "load_demand_kwh": load,
            "load_measurement_scope": next(iter(scopes))
            if len(scopes) == 1
            else "mixed",
            "gross_load_kwh": load if whole_site else None,
            "gross_load_undefined_reason": reason,
            "unserved_load_kwh": math.fsum(f.unserved_load_kwh for f in flows),
            "solar_load_kwh": solar,
            "pv_direct_load_kwh": math.fsum(f.direct_pv_to_load_kwh for f in flows),
            "pv_battery_to_load_kwh": math.fsum(
                f.battery_to_load_ac.pv_kwh for f in flows
            ),
            "pv_generated_ac_kwh": math.fsum(
                f.independent_pv_available_kwh
                - f.independent_pv_curtailed_kwh
                + math.fsum(
                    u.port.plan.pv_forward_ac_kw * f.frame.site.interval.hours
                    for u in f.units
                )
                for f in flows
            ),
            "pv_generated_dc_kwh": math.fsum(
                float(cast(float, u["pv_generated_dc_kwh"]))
                for u in cast(list[Object], units)
            ),
            "pv_curtailed_dc_kwh": math.fsum(
                float(cast(float, u["pv_curtailed_dc_kwh"]))
                for u in cast(list[Object], units)
            ),
            "independent_pv_curtailed_ac_kwh": math.fsum(
                f.independent_pv_curtailed_kwh for f in flows
            ),
            "grid_import_kwh": math.fsum(f.grid_import_kwh for f in flows),
            "pv_export_kwh": math.fsum(f.export_sources.pv_kwh for f in flows),
            "grid_charge_ac_kwh": math.fsum(f.grid_charge_kwh for f in flows),
            "grid_origin_battery_to_load_kwh": math.fsum(
                f.battery_to_load_ac.grid_kwh for f in flows
            ),
            "initial_unknown_battery_to_load_kwh": math.fsum(
                f.battery_to_load_ac.initial_unknown_kwh for f in flows
            ),
            "shared_inverter_forward_loss_kwh": math.fsum(
                u.port.plan.forward_dc_kw
                * (1 - u.port.plan.bridge.eta_forward)
                * u.port.plan.frame.interval.hours
                for u in all_units
            ),
            "shared_inverter_reverse_loss_kwh": math.fsum(
                u.port.incoming_aux_ac.total
                + u.port.incoming_charge_ac.total
                - u.port.incoming_aux_dc.total
                - u.port.incoming_charge_dc.total
                for u in all_units
            ),
            "standing_loss_kwh": math.fsum(
                u.port.plan.standing_loss.total for u in all_units
            ),
            "internal_aux_supplied_kwh": math.fsum(
                u.port.plan.internal_aux.total for u in all_units
            ),
            "internal_aux_unserved_kwh": math.fsum(
                u.port.plan.internal_aux_unserved_kwh for u in all_units
            ),
            "aux_ac_unserved_kwh": math.fsum(f.unserved_aux_kwh for f in flows),
            "aux_dc_unserved_kwh": math.fsum(
                u.port.unserved_aux_dc_kw * u.port.plan.frame.interval.hours
                for u in all_units
            ),
            "maximum_interval_average_import_kw": max(
                f.grid_import_kwh / f.frame.site.interval.hours for f in flows
            ),
            "stored_initial": inventory(
                [u.port.plan.before for u in flows[0].units]
            ).document(),
            "stored_final": inventory(
                [u.port.after for u in flows[-1].units]
            ).document(),
            "units": units,
            "solar_autarky": _ratio(solar, load, "gross_load_is_zero")
            if whole_site
            else {"value": None, "undefined_reason": reason},
            "solar_load_share_of_requested_demand": _ratio(
                solar, load, "requested_load_is_zero"
            ),
            "pv_input_self_use": {
                "value": None,
                "undefined_reason": "mixed_pv_measurement_stages",
            },
            "pv_onsite_available_share": {
                "value": None,
                "undefined_reason": "mixed_pv_measurement_stages",
            },
            "definitions": {
                "inventory": "separate_physical_units; totals_are_presentation_only",
                "pv_generated_ac_kwh": "PV_delivered_to_common_AC_bus_after_curtailment; excludes_direct_DC_storage_and_DC_aux",
                "pv_generated_dc_kwh": "sum_of_local_PV_DC_bus_output_after_curtailment; not_added_to_AC_generation",
                "pv_input_self_use": "undefined_for_combined_AC_and_DC_input_stages; inspect_each_unit_stage",
                "solar_autarky": "PV_origin_energy_delivered_to_whole_site_load / whole_site_load_demand",
                "controller": "local_dc_then_proportional_ac_self_consumption_v1; no_forecast_or_optimality_claim",
            },
        },
    )
