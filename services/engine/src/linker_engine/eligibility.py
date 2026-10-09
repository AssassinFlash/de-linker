"""Which inverters may carry a residential design, rule by rule.

Each rule returns a check with its id, the value it read and whether it
passed; `None` means the fact is unknown, which never passes (an engineering
design only proposes what the data proves). The rules and their sources:
application and phase from #7's SelectionFacts; the single-phase limit of
VDE-AR-N 4105; the manufacturer's maximum PV input (the DC/AC limit); the
backup output from the datasheet or a documented accessory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from . import rules
from .catalog import Product
from .compatibility import Compatibility, Requirement

Backup = Literal["none", "needed", "needed_accessory_ok"]


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


def backup(
    inverter: Product, wanted: Backup, compatibility: Compatibility
) -> tuple[Check | None, list[Requirement]]:
    """The backup check and, when only an accessory provides it, the requirement to add.

    The industry states backup in three values: yes, yes with an accessory, no
    (docs/research/2026-10-09/pv-wholesale-selection-tools.md, section 2.1).
    "needed" accepts the first; "needed_accessory_ok" also the second.
    """
    if wanted == "none":
        return None, []
    native = inverter.backup_power_kva
    if native:
        # A backup output of its own ("ja" in the industry's three values) needs no part.
        return Check("backup", True, native, wanted), []
    documented = compatibility.requirements(inverter.model, "backup")
    if wanted == "needed_accessory_ok" and documented:
        return Check("backup", True, "accessory", wanted), documented
    return Check("backup", False, None, wanted), []
