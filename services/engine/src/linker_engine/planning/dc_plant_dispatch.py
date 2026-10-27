"""Local DC self-consumption, then proportional sharing at one AC meter.

Each port supplies its own DC auxiliaries and retains its assigned share of
common AC demand before charging from its own DC surplus. Battery discharge
is requested for customer/site demand, never to manufacture a charging cycle.
Remaining common-bus energy can supply documented reverse paths; explicit
grid charging uses the residual site import limit. There is no forecast or
manufacturer EMS/optimality claim. Final PV back-pressure occurs before DC/AC
conversion, rather than treating curtailed potential as delivered electricity.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import replace

from .dc_plant_model import DcPlantFlow, DcPlantFrame, DcPlantStorageFlow, DcPlantUnit
from .dc_port import DcPortFrame, DcPortPlan, plan, storage_internal_losses
from .dispatch_frame import Command
from .energy_origins import EnergyOrigins
from .errors import InvalidInput

type States = dict[str, EnergyOrigins]
EMPTY = EnergyOrigins(0, 0, 0)


def _shares(bounds: dict[str, float], available: float) -> dict[str, float]:
    total = math.fsum(bounds.values())
    fraction = min(available / total, 1.0) if total else 0.0
    return {key: value * fraction for key, value in bounds.items()}


def _validate(
    frame: DcPlantFrame, units: tuple[DcPlantUnit, ...], before: States
) -> None:
    ids = {u.id for u in units}
    if (
        not units
        or len(ids) != len(units)
        or ids != set(before)
        or ids != set(frame.pv_dc_kw)
    ):
        raise InvalidInput(
            "the DC plant needs each distinct unit and state exactly once"
        )
    for unit in units:
        if (
            before[unit.id].total > unit.model.usable_window_kwh
            or frame.reserves_kwh[unit.id] > unit.model.usable_window_kwh
        ):
            raise InvalidInput(
                "a DC unit's inventory or reserve exceeds its own window"
            )
        unit.model.bridge(frame.site.limits.mode)


def _plans(
    frame: DcPlantFrame, units: tuple[DcPlantUnit, ...], before: States
) -> dict[str, DcPortPlan]:
    site, dt = frame.site, frame.site.interval.hours
    pv_bounds, battery_bounds, aux_battery = {}, {}, {}
    for unit in units:
        model, uid = unit.model, unit.id
        bridge = model.bridge(site.limits.mode)
        state = storage_internal_losses(site.interval, model, before[uid])[0]
        pv = frame.pv_dc_kw[uid] if site.limits.pv_enabled else 0.0
        if model.pv_input_dc_kw is not None:
            pv = min(pv, model.pv_input_dc_kw)
        pv_remaining = max(pv - frame.aux_dc_kw[uid], 0.0)
        terminal = min(
            model.discharge_terminal_kw,
            max(state.total - frame.reserves_kwh[uid], 0.0)
            * model.eta_store_discharge
            / dt,
        )
        aux_battery[uid] = min(
            max(frame.aux_dc_kw[uid] - pv, 0.0), terminal * model.eta_battery_to_bus
        )
        pv_bounds[uid] = (
            min(pv_remaining, bridge.forward_limit_dc_kw) * bridge.eta_forward
        )
        battery_bounds[uid] = (
            min(
                max(terminal * model.eta_battery_to_bus - aux_battery[uid], 0.0),
                max(bridge.forward_limit_dc_kw - pv_remaining, 0.0),
            )
            * bridge.eta_forward
        )
    independent = site.pv_potential_kw if site.limits.pv_enabled else 0.0
    demand = max(site.load_kw + site.aux_ac_kw - independent, 0.0)
    pv_targets = _shares(pv_bounds, demand)
    battery_targets = _shares(
        battery_bounds, max(demand - math.fsum(pv_bounds.values()), 0.0)
    )
    result = {}
    for unit in units:
        uid, model = unit.id, unit.model
        bridge = model.bridge(site.limits.mode)
        discharge = (
            aux_battery[uid] + battery_targets[uid] / bridge.eta_forward
        ) / model.eta_battery_to_bus
        command = (
            Command(0, discharge) if discharge else Command(model.charge_terminal_kw, 0)
        )
        result[uid] = plan(
            DcPortFrame(
                site.interval,
                frame.pv_dc_kw[uid],
                frame.aux_dc_kw[uid],
                site.limits.mode,
                frame.reserves_kwh[uid],
                site.limits.pv_enabled,
                pv_targets[uid] + battery_targets[uid],
                None,
            ),
            model,
            before[uid],
            command,
        )
    return result


def _packets(
    pool: EnergyOrigins, bounds: dict[str, float], duration: float
) -> tuple[EnergyOrigins, States]:
    shares = _shares(bounds, pool.total / duration)
    packets = {}
    for uid, value in shares.items():
        pool, packets[uid] = pool.withdraw(value * duration)
    return pool, packets


def step(
    frame: DcPlantFrame, units: tuple[DcPlantUnit, ...], before: States
) -> DcPlantFlow:
    _validate(frame, units, before)
    site, dt = frame.site, frame.site.interval.hours
    plans = _plans(frame, units, before)
    independent = (site.pv_potential_kw if site.limits.pv_enabled else 0.0) * dt
    direct_pv = math.fsum(
        [independent, *(p.pv_forward_ac_kw * dt for p in plans.values())]
    )
    battery = EMPTY
    for port in plans.values():
        battery = battery.plus(port.battery_forward_ac)
    pool = EnergyOrigins(direct_pv, 0, 0).plus(battery)
    offered = pool.total
    load_fraction = min(site.load_kw * dt / offered, 1.0) if offered else 0.0
    aux_fraction = (
        min(site.aux_ac_kw * dt, max(offered - site.load_kw * dt, 0.0)) / offered
        if offered
        else 0.0
    )
    pool, load_sources = pool.withdraw(site.load_kw * dt)
    pool, aux_sources = pool.withdraw(site.aux_ac_kw * dt)
    missing_load = max(site.load_kw * dt - load_sources.total, 0.0)
    missing_aux = max(site.aux_ac_kw * dt - aux_sources.total, 0.0)
    base_import = site.limits.import_limit((missing_load + missing_aux) / dt) * dt
    grid_load = min(base_import, missing_load)
    grid_aux = max(base_import - grid_load, 0.0)
    load_sources = load_sources.plus(EnergyOrigins(0, grid_load, 0))
    aux_sources = aux_sources.plus(EnergyOrigins(0, grid_aux, 0))
    used_grid = base_import

    def available(include_grid: bool) -> float | None:
        if not include_grid or site.limits.mode == "outage":
            return pool.total / dt
        cap = site.limits.import_cap_kw
        return None if cap is None else pool.total / dt + max(cap - used_grid / dt, 0.0)

    def receive(bounds: dict[str, float], include_grid: bool) -> tuple[States, float]:
        nonlocal pool, used_grid
        wanted = math.fsum(bounds.values()) * dt
        imported = 0.0
        if include_grid:
            imported = max(
                site.limits.import_limit(
                    (used_grid + max(wanted - pool.total, 0.0)) / dt
                )
                * dt
                - used_grid,
                0.0,
            )
        used_grid += imported
        pool = pool.plus(EnergyOrigins(0, imported, 0))
        pool, packets = _packets(pool, bounds, dt)
        return packets, imported

    aux_bounds = {
        uid: p.auxiliary_request_ac_kw(available(True)) for uid, p in plans.items()
    }
    aux_packets, grid_dc_aux = receive(aux_bounds, True)
    charge_bounds = {
        unit.id: plans[unit.id].charging_request_ac_kw(
            available(site.limits.allow_grid_charge), aux_packets[unit.id].total / dt
        )
        if unit.allow_ac_charge
        else 0.0
        for unit in units
    }
    charge_packets, grid_charge = receive(charge_bounds, site.limits.allow_grid_charge)
    completed = {
        uid: p.complete(aux_packets[uid], charge_packets[uid])
        for uid, p in plans.items()
    }
    for completed_port in completed.values():
        pool = pool.plus(completed_port.unused_aux_ac).plus(
            completed_port.unused_charge_ac
        )
    pool, exported = pool.withdraw(site.limits.export_limit(pool.total / dt) * dt)

    # All rejected *current* PV potential is backed off at its own producer.
    # A foreign bank's stored PV origin is never counted as new PV generation.
    pv_backpressure = min(pool.pv_kwh, direct_pv)
    rejected_fraction = pv_backpressure / direct_pv if direct_pv else 0.0
    final = []
    for unit in units:
        p = plans[unit.id]
        adjusted = p.accept_forward_pv(p.pv_forward_ac_kw * (1 - rejected_fraction))
        final.append(
            DcPlantStorageFlow(unit, replace(completed[unit.id], plan=adjusted))
        )
    unallocated = EnergyOrigins(
        max(pool.pv_kwh - pv_backpressure, 0.0), pool.grid_kwh, pool.initial_unknown_kwh
    )
    return DcPlantFlow(
        frame=frame,
        units=tuple(final),
        independent_pv_available_kwh=independent,
        independent_pv_curtailed_kwh=independent * rejected_fraction,
        load_sources=load_sources,
        aux_sources=aux_sources,
        battery_to_load_ac=battery.scaled(load_fraction),
        battery_to_aux_ac=battery.scaled(aux_fraction),
        direct_pv_to_load_kwh=direct_pv * load_fraction,
        direct_pv_to_aux_kwh=direct_pv * aux_fraction,
        grid_to_load_kwh=grid_load,
        grid_to_aux_kwh=grid_aux,
        grid_to_dc_aux_kwh=grid_dc_aux,
        grid_charge_kwh=grid_charge,
        grid_import_kwh=used_grid,
        export_sources=exported,
        unallocated_sources=unallocated,
        unserved_load_kwh=max(missing_load - grid_load, 0.0),
        unserved_aux_kwh=max(missing_aux - grid_aux, 0.0),
    )


def replay(
    frames: tuple[DcPlantFrame, ...],
    units: tuple[DcPlantUnit, ...],
    initial: States,
    *,
    checkpoint: Callable[[], None],
) -> tuple[DcPlantFlow, ...]:
    if not frames:
        raise InvalidInput("a DC plant replay requires a nonempty continuous horizon")
    states, result = initial, []
    previous = None
    for frame in frames:
        checkpoint()
        if (
            previous is not None
            and previous.site.interval.end != frame.site.interval.start
        ):
            raise InvalidInput("a DC plant cannot reset inventories across time gaps")
        flow = step(frame, units, states)
        result.append(flow)
        states = {unit.unit.id: unit.port.after for unit in flow.units}
        previous = frame
    return tuple(result)
