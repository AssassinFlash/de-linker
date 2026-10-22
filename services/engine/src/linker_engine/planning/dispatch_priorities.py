"""Independent fixed-allocation equations for the declared AC-bus model.

Spec 548-energy-replay §7 defines these priorities. They are model semantics,
not a universal controller policy. Neither actuator nor its limit/withdraw
helpers are called here: a balanced but differently allocated ledger must fail.

This checks allocation of ACTUAL delivery. Separate independent energy,
power, reserve, source and command checks constrain that delivery. Reconstructing
energy-limited power again from subtraction of large total inventories would
amplify roundoff by 1/dt and falsely reject small, short-interval deliveries.
"""

from __future__ import annotations

from .dispatch_frame import Flows


def priority_residuals(flow: Flows) -> dict[str, float]:
    frame, limits = flow.frame, flow.frame.limits
    dt = frame.interval.hours
    pv = frame.pv_potential_kw if limits.pv_enabled else 0.0
    pv_load = min(pv, frame.load_kw)
    pv_aux = min(pv - pv_load, frame.aux_ac_kw)
    load_deficit = frame.load_kw - pv_load
    aux_deficit = frame.aux_ac_kw - pv_aux

    discharge = flow.discharge_kw
    battery_load = min(discharge, load_deficit)
    battery_aux = max(discharge - battery_load, 0.0)
    remaining_load = max(load_deficit - battery_load, 0.0)
    remaining_aux = max(aux_deficit - battery_aux, 0.0)
    import_cap = 0.0 if limits.mode == "outage" else limits.import_cap_kw
    grid_base = remaining_load + remaining_aux
    if import_cap is not None:
        grid_base = min(grid_base, import_cap)
    grid_load = min(grid_base, remaining_load)
    grid_aux = max(grid_base - grid_load, 0.0)

    surplus = max(pv - pv_load - pv_aux, 0.0)
    pv_charge = min(flow.charge_kw, surplus)
    grid_charge = 0.0
    if limits.mode == "connected" and limits.allow_grid_charge:
        grid_charge = max(flow.charge_kw - pv_charge, 0.0)
        if import_cap is not None:
            grid_charge = min(grid_charge, max(import_cap - grid_base, 0.0))
    remaining_surplus = max(surplus - pv_charge, 0.0)
    export_cap = 0.0 if limits.mode == "outage" else limits.export_cap_kw
    export = (
        remaining_surplus if export_cap is None else min(remaining_surplus, export_cap)
    )
    actual_battery_load = flow.discharged_to_load_ac.total / dt
    comparisons = (
        ("pv_load_priority", flow.pv_to_load_kw, pv_load),
        ("pv_aux_priority", flow.pv_to_aux_kw, pv_aux),
        ("battery_load_priority", actual_battery_load, battery_load),
        ("battery_aux_priority", flow.discharge_kw - actual_battery_load, battery_aux),
        ("grid_load_priority", flow.grid_to_load_kw, grid_load),
        ("grid_aux_priority", flow.grid_to_aux_kw, grid_aux),
        ("pv_charge_priority", flow.pv_charge_kw, pv_charge),
        ("grid_charge_priority", flow.grid_charge_kw, grid_charge),
        ("pv_export_priority", flow.export_kw, export),
        ("pv_curtailment_priority", flow.curtailed_kw, remaining_surplus - export),
    )
    return {code: abs(actual - expected) for code, actual, expected in comparisons}
