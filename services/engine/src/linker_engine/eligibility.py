"""Which inverters may carry a residential design, rule by rule.

Each rule returns a check with its id, the value it read and whether it
passed; `None` means the fact is unknown, which never passes (an engineering
design only proposes what the data proves). The rules and their sources:
application and phase from #7's SelectionFacts; the single-phase limit of
VDE-AR-N 4105; the manufacturer's maximum PV input (the DC/AC limit); and, for
a backup request, that a released battery configuration can hold the reserve.
Backup is a sizing input, not an inverter capability gate: spec 14 adds the
reserve on top of the HTW band and its eligibility list does not name a backup
output. The accessory a document names is added when the customer accepts one.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import rules
from .products import Product


@dataclass(frozen=True)
class Check:
    id: str
    passed: bool | None
    value: float | str | None
    limit: float | str | None = None


def application(inverter: Product) -> Check:
    return Check(
        "application", inverter.application == "home", inverter.application, "home"
    )


def phase(inverter: Product, wanted: int) -> Check:
    if inverter.phase is None:
        return Check("phase", None, None, wanted)
    return Check("phase", inverter.phase == wanted, inverter.phase, wanted)


def single_phase_limit(inverter: Product) -> Check | None:
    if inverter.phase != 1:
        return None
    limit = rules.SINGLE_PHASE_MAX_KVA.value
    if inverter.ac_power_kw is None:
        return Check(rules.SINGLE_PHASE_MAX_KVA.id, None, None, limit)
    return Check(
        rules.SINGLE_PHASE_MAX_KVA.id,
        inverter.ac_power_kw <= limit + 1e-9,
        inverter.ac_power_kw,
        limit,
    )


def pv_input(inverter: Product, kwp: float) -> Check:
    if inverter.pv_input_kw is None:
        return Check("pv_input", None, None, kwp)
    return Check(
        "pv_input", inverter.pv_input_kw >= kwp - 1e-9, inverter.pv_input_kw, kwp
    )


def dc_ac_ratio(inverter: Product, kwp: float) -> Check:
    """kWp over AC power against the manufacturer's own ratio (maximum PV input over AC)."""
    if not inverter.ac_power_kw or inverter.pv_input_kw is None:
        return Check("dc_ac_ratio", None, None, None)
    ratio = round(kwp / inverter.ac_power_kw, 2)
    limit = round(inverter.pv_input_kw / inverter.ac_power_kw, 2)
    return Check("dc_ac_ratio", ratio <= limit + 1e-9, ratio, limit)


def backup_storage(usable_kwh: float | None, reserve_kwh: float) -> Check:
    """A released battery configuration of this inverter can hold the reserve.

    The caps behind `usable_kwh` are the datasheet stacking figures of
    `stacking.configurations`; the reserve is the customer's load times its
    duration over the discharge efficiency. No other threshold: the HTW band
    is an upper limit, so the battery need not reach the band's top, but it
    must be able to keep the reserve back from daily cycling. None means no
    battery is released for the inverter, which never passes.
    """
    if usable_kwh is None:
        return Check("backup_storage", None, None, reserve_kwh)
    return Check(
        "backup_storage",
        usable_kwh >= reserve_kwh - 1e-9,
        usable_kwh,
        reserve_kwh,
    )
