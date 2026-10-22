"""Local power and inventory checks that cannot borrow an absolute kWh budget.

Over a short interval an energy-small error can be a power-large error. These
checks retain both meanings. The reported arithmetic allowance is computed
from float64 ULPs of the actual ledger terms, not a physical safety margin.
No policy, actuator, source withdrawal or grid-limit helper is called.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .battery_model import BatteryModel
from .dispatch_frame import Flows


def _ulp(value: float) -> float:
    # An exact zero operand contributes no roundoff to the paired products.
    return math.ulp(value) if value else 0.0


@dataclass(frozen=True)
class DeliveryCheck:
    code: str
    violation_kw: float
    arithmetic_allowance_kw: float


def delivery_checks(flow: Flows, model: BatteryModel) -> tuple[DeliveryCheck, ...]:
    dt = flow.frame.interval.hours
    result: list[DeliveryCheck] = []

    def power(code: str, residual_kwh: float, roundoff_kwh: float = 0.0) -> None:
        result.append(DeliveryCheck(code, residual_kwh / dt, roundoff_kwh / dt))

    removed = flow.discharged_internal.total
    power(
        "discharge_conversion_kw",
        abs(flow.discharge_kw * dt - removed * model.eta_discharge),
        _ulp(flow.discharge_kw * dt) + _ulp(removed * model.eta_discharge),
    )
    power("internal_aux_supplied_kw", flow.internal_aux_unserved_kwh)
    standing = flow.before.total * -math.expm1(-model.standing_loss_rate_per_hour * dt)
    power(
        "standing_loss_model_kw",
        abs(flow.standing_loss.total - standing),
        _ulp(flow.standing_loss.total) + _ulp(standing),
    )
    aux = min(
        model.internal_aux_kw * dt,
        flow.before.total * math.exp(-model.standing_loss_rate_per_hour * dt),
    )
    power(
        "internal_aux_model_kw",
        abs(flow.internal_aux.total - aux),
        # Two paired proportional withdrawals precede AC delivery. Their
        # complement/product roundings can differ from this direct expression.
        2 * _ulp(flow.before.total) + _ulp(aux) + _ulp(flow.internal_aux.total),
    )
    available: list[float] = []
    availability_roundoff: list[float] = []
    for origin in ("pv_kwh", "grid_kwh", "initial_unknown_kwh"):
        before = getattr(flow.before, origin)
        loss = getattr(flow.standing_loss, origin)
        auxiliary = getattr(flow.internal_aux, origin)
        withdrawal = getattr(flow.discharged_internal, origin)
        after = getattr(flow.after, origin)
        incoming = (
            flow.pv_charge_kw * model.eta_charge * dt
            if origin == "pv_kwh"
            else flow.grid_charge_kw * model.eta_charge * dt
            if origin == "grid_kwh"
            else 0.0
        )
        local_stock = math.fsum((before, -loss, -auxiliary))
        # Each paired withdrawal a*(1-f), a*f can differ in sum from a due
        # to complement/product rounding. One ULP of a plus the withdrawn
        # term bounds that pair. There are two pre-AC pairs; their later a
        # cannot exceed before. fsum contributes one ULP of its result.
        local_roundoff = math.fsum(
            (2 * _ulp(before), _ulp(loss), _ulp(auxiliary), _ulp(local_stock))
        )
        available.append(local_stock)
        availability_roundoff.append(local_roundoff)
        power(
            f"origin_available_kw_{origin}",
            (withdrawal - max(local_stock, 0.0)) * model.eta_discharge,
            local_roundoff * model.eta_discharge,
        )
        expected_after = math.fsum((before, incoming, -loss, -auxiliary, -withdrawal))
        # A third paired withdrawal is discharge; charging then adds one
        # rounded term. Report this local arithmetic budget separately from
        # the caller's absolute/relative software tolerance.
        transition_roundoff = math.fsum(
            (
                3 * _ulp(before),
                _ulp(incoming),
                _ulp(loss),
                _ulp(auxiliary),
                _ulp(withdrawal),
                _ulp(after),
                _ulp(expected_after),
            )
        )
        power(
            f"origin_transition_kw_{origin}",
            abs(expected_after - after),
            transition_roundoff,
        )
        battery_to_load = flow.discharged_to_load_ac.total / dt
        expected_load = (
            withdrawal * model.eta_discharge * battery_to_load / flow.discharge_kw
            if flow.discharge_kw
            else 0.0
        )
        actual_load = getattr(flow.discharged_to_load_ac, origin)
        power(
            f"load_origin_kw_{origin}",
            abs(expected_load - actual_load),
            _ulp(expected_load) + _ulp(actual_load),
        )
    stock = math.fsum(available)
    reserve = flow.frame.limits.reserve_kwh
    available_above_reserve = max(stock - reserve, 0.0)
    stock_roundoff = math.fsum(
        (*availability_roundoff, _ulp(stock), _ulp(reserve), _ulp(stock - reserve))
    )
    power(
        "discharge_available_above_reserve_kw",
        (removed - available_above_reserve) * model.eta_discharge,
        stock_roundoff * model.eta_discharge,
    )
    return tuple(result)
