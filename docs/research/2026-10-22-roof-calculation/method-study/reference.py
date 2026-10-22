"""Independent ideal AC-coupled energy reference, not a production engine.

This module imports no Linker engine. The MILP is an existence oracle under
explicit synthetic limits and perfect foresight; replay independently checks
its ledger. Primary-source provenance and limits are documented in README.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

TOL = 1e-7  # numerical invariant tolerance in kWh/kW, not an accuracy promise


@dataclass(frozen=True)
class Case:
    name: str
    load: list[float]
    pv: list[float]
    dt_h: float
    energy_kwh: float
    charge_kw: float
    discharge_kw: float
    eta_charge: float = 0.94
    eta_discharge: float = 0.94
    initial_kwh: float = 0
    terminal_min_kwh: float = 0
    reserve_kwh: float = 0
    grid_limit_kw: float = 1000
    allow_grid_charge: bool = False
    export_limit_kw: float = 1000
    start: str = "2026-01-01T00:00:00+00:00"
    grid_limits_kw: list[float] | None = None


def solve(case: Case) -> dict:
    """MILP: explicit source/destination AC flows and internal battery energy.

    No battery export, battery auxiliary loss, voltage/current/temperature model
    or topology transformation in this minimal AC-only research reference.
    Binary mode prevents simultaneous charge/discharge. Curtailment is explicit.
    Objective minimizes total grid import, then a tiny battery-throughput tie
    penalty. This is not a multiobjective optimum or a controller simulation.
    """
    n = len(case.load)
    assert n == len(case.pv) and n > 0 and case.dt_h > 0
    assert 0 < case.eta_charge <= 1 and 0 < case.eta_discharge <= 1
    assert 0 <= case.reserve_kwh <= case.initial_kwh <= case.energy_kwh
    assert 0 <= case.terminal_min_kwh <= case.energy_kwh
    assert min(case.load + case.pv) >= 0
    grid_limits = case.grid_limits_kw or [case.grid_limit_kw] * n
    assert len(grid_limits) == n and min(grid_limits) >= 0
    # PV->load, PV->battery, PV->grid, PV curtail, grid->load,
    # grid->battery, battery->load; then E[0..n], binary charge mode.
    names = ["pv_load", "pv_charge", "pv_export", "pv_curtail", "grid_load", "grid_charge", "battery_load"]
    size = 7 * n + (n + 1) + n
    energy = 7 * n
    mode = energy + n + 1
    low = np.zeros(size)
    high = np.full(size, np.inf)
    for t in range(n):
        high[0 * n + t] = case.load[t]
        high[1 * n + t] = case.charge_kw
        high[2 * n + t] = case.export_limit_kw
        high[3 * n + t] = case.pv[t]
        high[4 * n + t] = grid_limits[t]
        high[5 * n + t] = case.charge_kw if case.allow_grid_charge else 0
        high[6 * n + t] = case.discharge_kw
    low[energy:energy + n + 1] = case.reserve_kwh
    high[energy:energy + n + 1] = case.energy_kwh
    low[energy] = high[energy] = case.initial_kwh
    low[energy + n] = max(case.reserve_kwh, case.terminal_min_kwh)
    high[mode:] = 1
    rows: list[dict[int, float]] = []
    lo: list[float] = []
    hi: list[float] = []

    def add(coefficients: dict[int, float], lower: float, upper: float) -> None:
        rows.append(coefficients)
        lo.append(lower)
        hi.append(upper)

    for t in range(n):
        add({j * n + t: 1 for j in [0, 1, 2, 3]}, case.pv[t], case.pv[t])
        add({j * n + t: 1 for j in [0, 4, 6]}, case.load[t], case.load[t])
        add({energy + t + 1: 1, energy + t: -1,
             n + t: -case.eta_charge * case.dt_h,
             5 * n + t: -case.eta_charge * case.dt_h,
             6 * n + t: case.dt_h / case.eta_discharge}, 0, 0)
        add({4 * n + t: 1, 5 * n + t: 1}, -np.inf, grid_limits[t])
        add({n + t: 1, 5 * n + t: 1, mode + t: -case.charge_kw}, -np.inf, 0)
        add({6 * n + t: 1, mode + t: case.discharge_kw}, -np.inf, case.discharge_kw)
    matrix = lil_matrix((len(rows), size))
    for r, values in enumerate(rows):
        for col, value in values.items():
            matrix[r, col] = value
    objective = np.zeros(size)
    objective[4 * n:6 * n] = case.dt_h
    objective[n:2 * n] += 1e-8 * case.dt_h
    objective[6 * n:7 * n] += 1e-8 * case.dt_h
    integrality = np.zeros(size)
    integrality[mode:] = 1
    solution = milp(objective, integrality=integrality,
                    bounds=Bounds(low, high),
                    constraints=LinearConstraint(matrix.tocsc(), lo, hi),
                    options={"time_limit": 30, "mip_rel_gap": 1e-9})
    if solution.status == 2:
        return {"name": case.name, "status": "infeasible_under_stated_model", "solver_status": int(solution.status), "input": case.__dict__}
    if not solution.success:
        return {"name": case.name, "status": "unknown_solver_not_complete", "solver_status": int(solution.status), "message": solution.message, "input": case.__dict__}
    x = solution.x
    flows = {name: [float(v) for v in x[i * n:(i + 1) * n]] for i, name in enumerate(names)}
    states = [float(v) for v in x[energy:energy + n + 1]]
    ledger = replay(case, flows, states)
    return {"name": case.name, "status": "feasible_under_stated_model", "solver_status": int(solution.status),
            "input": case.__dict__, "ledger": ledger, "flows_kw": flows, "states_kwh": states}


def replay(case: Case, flows: dict[str, list[float]], expected_states: list[float]) -> dict:
    """Independent scalar energy/source ledger, separate from MILP matrix.

    Initial energy provenance is unknown, not presumed solar. Stored energy is
    mixed proportionally for source attribution, a declared accounting choice.
    The bookkeeping choice is not a claim about physical electron identity.
    """
    buckets = {"pv": 0.0, "grid": 0.0, "initial_unknown": case.initial_kwh}
    delivered = {key: 0.0 for key in buckets}
    input_internal = 0.0
    output_internal = 0.0
    max_error = 0.0
    max_grid = 0.0
    times = []
    for t, (load, pv) in enumerate(zip(case.load, case.pv, strict=True)):
        f = {key: values[t] for key, values in flows.items()}
        pv_balance = pv - sum(f[key] for key in ["pv_load", "pv_charge", "pv_export", "pv_curtail"])
        load_balance = load - f["pv_load"] - f["grid_load"] - f["battery_load"]
        charge = f["pv_charge"] + f["grid_charge"]
        discharge = f["battery_load"]
        grid = f["grid_load"] + f["grid_charge"]
        assert charge <= case.charge_kw + TOL and discharge <= case.discharge_kw + TOL
        assert charge <= TOL or discharge <= TOL
        assert grid <= (case.grid_limits_kw[t] if case.grid_limits_kw else case.grid_limit_kw) + TOL
        max_grid = max(max_grid, grid)
        start = sum(buckets.values())
        internal_draw = discharge * case.dt_h / case.eta_discharge
        if internal_draw > TOL:
            assert start > 0 and internal_draw <= start - case.reserve_kwh + TOL
            for key, value in list(buckets.items()):
                share = value / start
                buckets[key] -= share * internal_draw
                delivered[key] += share * discharge * case.dt_h
        buckets["pv"] += f["pv_charge"] * case.dt_h * case.eta_charge
        buckets["grid"] += f["grid_charge"] * case.dt_h * case.eta_charge
        now = sum(buckets.values())
        assert case.reserve_kwh - TOL <= now <= case.energy_kwh + TOL
        input_internal += charge * case.dt_h * case.eta_charge
        output_internal += internal_draw
        max_error = max(max_error, abs(pv_balance), abs(load_balance), abs(now - expected_states[t + 1]))
        assert max_error < TOL
        times.append((datetime.fromisoformat(case.start) + timedelta(hours=t * case.dt_h)).isoformat())
    total_load = sum(case.load) * case.dt_h
    total_pv = sum(case.pv) * case.dt_h
    direct_pv = sum(flows["pv_load"]) * case.dt_h
    pv_charge = sum(flows["pv_charge"]) * case.dt_h
    pv_curtailed = sum(flows["pv_curtail"]) * case.dt_h
    actual_generated = total_pv - pv_curtailed
    solar_delivered = direct_pv + delivered["pv"]
    assert solar_delivered <= total_load + TOL
    assert solar_delivered <= total_pv + TOL  # no initial solar credit
    assert sum(buckets.values()) >= case.terminal_min_kwh - TOL
    assert abs(case.initial_kwh + input_internal - output_internal - sum(buckets.values())) < TOL
    return {"load_kwh": total_load, "available_pv_kwh": total_pv,
            "curtailed_pv_kwh": pv_curtailed, "actual_generated_pv_kwh": actual_generated,
            "direct_pv_to_load_kwh": direct_pv, "pv_to_charge_ac_kwh": pv_charge,
            "battery_to_load_by_origin_kwh": delivered, "remaining_internal_by_origin_kwh": buckets,
            "solar_delivered_kwh": solar_delivered,
            "solar_autarky": solar_delivered / total_load if total_load else None,
            "pv_used_onsite_input_share": (direct_pv + pv_charge) / total_pv if total_pv else None,
            "pv_self_consumption_of_actual_generation": (direct_pv + pv_charge) / actual_generated if actual_generated > TOL else None,
            "delivered_solar_fraction_of_available_pv": solar_delivered / total_pv if total_pv else None,
            "grid_import_kwh": (sum(flows["grid_load"]) + sum(flows["grid_charge"])) * case.dt_h,
            "peak_grid_kw": max_grid, "max_replay_balance_error": max_error,
            "first_interval": times[0], "last_interval": times[-1],
            "end_internal_kwh": sum(buckets.values())}


def run_cases() -> list[dict]:
    outputs = []

    def check(case: Case, expected_feasible: bool, expectation: str) -> dict:
        value = solve(case)
        assert value["status"] == ("feasible_under_stated_model" if expected_feasible else "infeasible_under_stated_model"), value
        value["independent_expectation"] = expectation
        outputs.append(value)
        return value

    # 20:00 to 04:00 continuous peak, grid can recharge in other hours.
    load = [0.] * 80 + [20.] * 32 + [0.] * 80
    lower = 80 / .94
    for cap in [42.6, lower]:
        check(Case(f"midnight_{cap:.3f}kwh", load, [0.] * 192, .25, cap, 10, 10,
                   initial_kwh=cap, terminal_min_kwh=cap, grid_limit_kw=10,
                   allow_grid_charge=True), cap == lower,
              "8h × (20−10)kW / 0.94 = 85.1063829787kWh internal energy; recharged outside event")
    # Repeated equal AC need/room cannot replenish battery conversion losses.
    for grid in [10., 10 / (.94 * .94)]:
        check(Case(f"recharge_room_{grid:.6f}", [20., 0.], [0., 0.], 1, 20, 20, 20,
                   initial_kwh=10 / .94, terminal_min_kwh=10 / .94,
                   grid_limits_kw=[10., grid], allow_grid_charge=True), grid > 10,
              "At 10kW cap, 10kWh AC discharge requires 10/0.94²=11.31733816kWh AC recharge; equal 10kWh room is insufficient")
    # Low yield with no initial solar cannot exceed energy upper bound.
    result = check(Case("low_pv_solar_bound", [0., 4.], [2.208, 0.], 1,
                        2.5, 2.5, 4., eta_charge=1, eta_discharge=1), True,
                   "Scaled two-period energy case: solar autarky ≤2.208/4=0.552; ideal lossless storage attains the bound")
    assert abs(result["ledger"]["solar_autarky"] - .552) < TOL
    # Enough kWh is insufficient when a one-hour outage needs more kW.
    for power in [5., 10.]:
        check(Case(f"outage_power_{power}", [10.], [0.], 1, 20, 10, power,
                   eta_charge=1, eta_discharge=1, initial_kwh=20, grid_limit_kw=0), power == 10,
              "A 10kW critical load in an outage requires ≥10kW deliverable power even when capacity is 20kWh")
    # Grid-charged electricity cannot contribute to solar autarky.
    result = check(Case("grid_charge_attribution", [0., 5.], [0., 0.], 1,
                        10, 10, 10, eta_charge=1, eta_discharge=1,
                        grid_limits_kw=[5., 0.], allow_grid_charge=True), True,
                   "No PV exists, therefore solar autarky is 0 irrespective of grid-charged discharge")
    assert result["ledger"]["solar_autarky"] == 0
    # Force grid charging: next interval zero grid capacity is represented
    # with an explicit schedule and replay outside this fixed-cap MILP case.
    source = Case("forced_grid_charge_ledger", [0., 5.], [0., 0.], 1, 5, 5, 5,
                  eta_charge=1, eta_discharge=1, allow_grid_charge=True)
    f = {k: [0., 0.] for k in ["pv_load", "pv_charge", "pv_export", "pv_curtail", "grid_load", "grid_charge", "battery_load"]}
    f["grid_charge"] = [5., 0.]; f["battery_load"] = [0., 5.]
    ledger = replay(source, f, [0., 5., 0.])
    assert ledger["battery_to_load_by_origin_kwh"]["grid"] == 5 and ledger["solar_autarky"] == 0
    outputs.append({"name": source.name, "status": "manual_schedule_replay_passed", "input": source.__dict__, "flows_kw": f, "states_kwh": [0., 5., 0.], "ledger": ledger,
                    "independent_expectation": "5kWh grid-charged discharge is grid-origin, never solar"})
    # Explicit initial inventory can make an outage feasible, but repeated
    # operation without recharging it cannot be called sustainable.
    for terminal in [0., 5.]:
        result = check(Case(f"initial_terminal_{terminal}", [5.], [0.], 1, 5, 5, 5,
                            eta_charge=1, eta_discharge=1, initial_kwh=5,
                            terminal_min_kwh=terminal, grid_limit_kw=0), terminal == 0,
                       "One-shot 5kWh initial inventory can supply 5kWh; E_end≥E_start without any energy input cannot")
        if terminal == 0:
            assert result["ledger"]["solar_autarky"] == 0
    # PV input self-consumption includes conversion losses; delivered solar
    # fraction is a different metric and must not be swapped under one label.
    result = check(Case("pv_losses_and_metric_definitions", [0., 8.], [10., 0.], 1, 10, 10, 10,
                        eta_charge=.9, eta_discharge=.9), True,
                   "Solar may charge >8kWh AC to deliver 8kWh; onsite input share differs from delivered-solar fraction")
    assert result["ledger"]["pv_used_onsite_input_share"] > result["ledger"]["delivered_solar_fraction_of_available_pv"]
    # Holding backup reserve leaves less energy for normal self-consumption.
    result = check(Case("reserve_partition", [8.], [0.], 1, 10, 10, 10,
                        eta_charge=1, eta_discharge=1, initial_kwh=10, reserve_kwh=4), True,
                   "A 4kWh held reserve in a 10kWh battery leaves at most 6kWh for normal dispatch; grid supplies ≥2kWh")
    assert result["ledger"]["grid_import_kwh"] >= 2 - TOL

    # A declared SOC partition preserves 4kWh for a later peak while using
    # only energy above it for ordinary self-consumption, as in SMA multiuse.
    # This hand schedule is an example of that structure, not a full copy of
    # SMA's device controller or a claim that 4kWh is a universal optimum.
    multi = Case("multiuse_soc_partition", [0., 3., 8.], [6., 0., 0.], 1, 10, 10, 10,
                 eta_charge=1, eta_discharge=1, grid_limit_kw=4)
    mf = {k: [0., 0., 0.] for k in ["pv_load", "pv_charge", "pv_export", "pv_curtail", "grid_load", "grid_charge", "battery_load"]}
    mf["pv_charge"] = [6., 0., 0.]
    mf["battery_load"] = [0., 2., 4.]; mf["grid_load"] = [0., 1., 4.]
    ml = replay(multi, mf, [0., 6., 4., 0.])
    outputs.append({"name": multi.name, "status": "manual_schedule_replay_passed", "input": multi.__dict__, "flows_kw": mf, "states_kwh": [0., 6., 4., 0.], "ledger": ml,
                    "independent_expectation": "Hold a 4kWh peak buffer: 2kWh self-use at first, 4kWh peak support later; greedy load-following uses 3 then 3 and reaches 5kW grid import"})
    check(multi, True, "Independent MILP also finds feasibility after storing the same 6kWh of PV with a 4kW grid cap")
    for initial in [6., 8.]:
        check(Case(f"multiuse_with_backup_floor_{initial}", [3., 8.], [0., 0.], 1,
                   10, 10, 10, eta_charge=1, eta_discharge=1,
                   initial_kwh=initial, reserve_kwh=4, grid_limit_kw=4), initial == 8,
              "A 4kWh backup reserve cannot also be spent on peak support; available dispatch energy is initial minus reserve")
    return outputs


if __name__ == "__main__":
    results = run_cases()
    target = Path(__file__).with_name("reference-results.json")
    target.write_text(json.dumps({"scope": "independent ideal AC-coupled research reference, not SAM/SSC or vendor validation", "runtime": {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__, "platform": platform.platform(), "reference_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, "cases": results}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"cases": len(results), "results": [{"name": r["name"], "status": r["status"]} for r in results]}, indent=2))
