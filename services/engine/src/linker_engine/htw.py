"""Residential storage sizing and self-sufficiency by HTW Berlin's method.

Sizing follows HTW Berlin's three rules: storage only from 0.5 kWp of PV per
MWh/a, and usable capacity at most the smaller of 1.5 kWh per kWp and 1.5 kWh
per MWh/a (rules.HTW_*). HTW gives upper limits, not a lower one, so the range
the engine reports spans the consumption a household may have (a heat pump or
an electric car widens it, which HTW names as a reason for more capacity);
a backup reserve is added on top, never counted as daily cycling capacity.

Self-sufficiency and self-consumption are read from the HTW
Unabhängigkeitsrechner's own precomputed tables (data/htw/source.json) by the
calculator's bilinear interpolation, with no hourly simulation. The tables
describe one reference household; real households mostly lie within
rules.HTW_HOUSEHOLD_SPREAD_PP of it, which is the range reported.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from . import rules

DATA = Path(__file__).resolve().parents[2] / "data" / "htw"
_STEP = 0.0625


@dataclass(frozen=True)
class ConsumptionRange:
    household_kwh: float
    low_kwh: float
    high_kwh: float


@dataclass(frozen=True)
class Sizing:
    recommended: bool
    low_kwh: float
    high_kwh: float
    reserve_kwh: float
    kwp_per_mwh: float
    cap_per_kwp: float
    cap_per_mwh_low: float
    cap_per_mwh_high: float


@dataclass(frozen=True)
class Metrics:
    autarky: tuple[float, float]
    self_consumption: tuple[float, float]
    autarky_without: tuple[float, float]
    self_consumption_without: tuple[float, float]
    outside_table: bool


def consumption(
    household_kwh: float, heat_pump: bool, electric_vehicle: bool
) -> ConsumptionRange:
    low = high = household_kwh
    if heat_pump:
        low += rules.HEAT_PUMP_KWH_LOW.value
        high += rules.HEAT_PUMP_KWH_HIGH.value
    if electric_vehicle:
        low += rules.EV_KWH_LOW.value
        high += rules.EV_KWH_HIGH.value
    return ConsumptionRange(household_kwh, low, high)


def backup_reserve(load_kw: float | None, hours: float | None) -> float:
    """Energy kept back for an outage: load x hours, delivered through the discharge efficiency."""
    if not load_kw or not hours:
        return 0.0
    return round(load_kw * hours / rules.HTW_DISCHARGE_EFFICIENCY.value, 2)


def size(kwp: float, use: ConsumptionRange, reserve_kwh: float) -> Sizing:
    kwp_per_mwh = kwp / (use.low_kwh / 1000)
    recommended = kwp_per_mwh >= rules.HTW_MIN_KWP_PER_MWH.value - 1e-9
    per_kwp = rules.HTW_MAX_KWH_PER_KWP.value * kwp
    per_mwh_low = rules.HTW_MAX_KWH_PER_MWH.value * use.low_kwh / 1000
    per_mwh_high = rules.HTW_MAX_KWH_PER_MWH.value * use.high_kwh / 1000
    low = min(per_kwp, per_mwh_low) if recommended else 0.0
    high = min(per_kwp, per_mwh_high) if recommended else 0.0
    return Sizing(
        recommended=recommended,
        low_kwh=round(low + reserve_kwh, 2),
        high_kwh=round(high + reserve_kwh, 2),
        reserve_kwh=reserve_kwh,
        kwp_per_mwh=round(kwp_per_mwh, 3),
        cap_per_kwp=round(per_kwp, 2),
        cap_per_mwh_low=round(per_mwh_low, 2),
        cap_per_mwh_high=round(per_mwh_high, 2),
    )


@cache
def _table(name: str) -> list[list[float]]:
    data: list[list[float]] = json.loads((DATA / name).read_text())
    return data


def lookup(
    table: list[list[float]], pv_per_mwh: float, storage_per_mwh: float
) -> float:
    """Bilinear interpolation on the HTW grid (js/unabhaengig.js, SucheWertAusMatrix)."""
    top = table[0][-1]
    x = min(max(pv_per_mwh, 0.0), top)
    y = min(max(storage_per_mwh, 0.0), top)
    xi = min(max(math.ceil(x / _STEP) + 1, 2), len(table[0]) - 1)
    yi = min(max(math.ceil(y / _STEP) + 1, 2), len(table) - 1)
    x0, x1 = table[0][xi - 1], table[0][xi]
    y0, y1 = table[yi - 1][0], table[yi][0]
    upper = table[yi - 1][xi - 1] + (x - x0) * (
        table[yi - 1][xi] - table[yi - 1][xi - 1]
    ) / (x1 - x0)
    lower = table[yi][xi - 1] + (x - x0) * (table[yi][xi] - table[yi][xi - 1]) / (
        x1 - x0
    )
    return upper + (y - y0) * (lower - upper) / (y1 - y0)


def _band(value: float, spread: float) -> tuple[float, float]:
    return round(max(0.0, value - spread), 4), round(min(1.0, value + spread), 4)


def metrics(kwp: float, use: ConsumptionRange, usable_kwh: float) -> Metrics:
    """Self-sufficiency and self-consumption ranges for the consumption range given."""
    autarky_table = _table("tabelleAutarkie.json")
    share_table = _table("tabelleEigenverbrauch.json")
    spread = rules.HTW_HOUSEHOLD_SPREAD_PP.value / 100
    top = autarky_table[0][-1]
    outside = False
    autarky: list[float] = []
    share: list[float] = []
    autarky_0: list[float] = []
    share_0: list[float] = []
    for load in {use.low_kwh, use.high_kwh}:
        mwh = load / 1000
        x, y = kwp / mwh, usable_kwh / mwh
        outside = outside or x > top or y > top
        a = lookup(autarky_table, x, y)
        s = lookup(share_table, x, y)
        a0 = lookup(autarky_table, x, 0.0)
        s0 = lookup(share_table, x, 0.0)
        # Self-consumption moves with self-sufficiency: consumption over generation.
        scale = mwh / (kwp * rules.HTW_REFERENCE_YIELD.value / 1000)
        autarky += list(_band(a, spread))
        share += list(_band(s, spread * scale))
        autarky_0 += list(_band(a0, spread))
        share_0 += list(_band(s0, spread * scale))
    return Metrics(
        autarky=(min(autarky), max(autarky)),
        self_consumption=(min(share), max(share)),
        autarky_without=(min(autarky_0), max(autarky_0)),
        self_consumption_without=(min(share_0), max(share_0)),
        outside_table=outside,
    )
