"""A reference string layout per MPPT, and the string fuses it needs.

The layout answers two questions for a candidate inverter: can the array be
connected within the inverter's MPPT windows at all, and how many strings run
in parallel on each MPPT, which decides the string fuses. Each roof plane gets
MPPTs of its own (strings of different orientations are not mixed on one
tracker). It uses the reference module of the engineering overlay, a design
assumption the report discloses: the installer's module can change the layout.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import rules
from .catalog import Product, PvModule


@dataclass(frozen=True)
class MpptStrings:
    mppt: int
    plane: int | None  # index of the roof plane the strings come from
    strings: int
    modules_per_string: int
    fuses: int


@dataclass(frozen=True)
class StringLayout:
    strings: tuple[MpptStrings, ...]
    module_count: int
    array_kwp: float
    voc_cold_v: float
    vmp_hot_v: float

    @property
    def fuses(self) -> int:
        return sum(item.fuses for item in self.strings)

    @property
    def total_strings(self) -> int:
        return sum(item.strings for item in self.strings)

    @property
    def modules_per_string(self) -> int:
        return max((item.modules_per_string for item in self.strings), default=0)


@dataclass(frozen=True)
class LayoutResult:
    layout: StringLayout | None
    reason: str | None  # the rule that failed when there is no layout


def string_voltages(module: PvModule) -> tuple[float, float]:
    """Open-circuit voltage at the coldest and MPP voltage at the hottest design cell temperature."""
    beta = module.beta_voc_pct_per_c / 100
    voc_cold = module.voc_v * (1 + beta * (rules.STRING_T_MIN_C.value - 25))
    vmp_hot = module.vmpp_v * (1 + beta * (rules.STRING_T_CELL_MAX_C.value - 25))
    return voc_cold, vmp_hot


def fuses_needed(parallel_strings: int, module: PvModule) -> int:
    """gPV fuses on one MPPT, counted per string and pole.

    A fault in one string is fed by every other string in parallel with it.
    Protection is required once (N - 1) x 1.25 x Isc exceeds 1.35 times the
    module's maximum series fuse rating (rules.STRING_FUSE_*, IEC 60364-7-712);
    each MPPT is its own group.
    """
    reverse_current = (
        (parallel_strings - 1) * rules.STRING_FUSE_ISC_FACTOR.value * module.isc_a
    )
    withstand = rules.STRING_FUSE_OCPR_FACTOR.value * module.max_series_fuse_a
    if parallel_strings < 2 or reverse_current <= withstand:
        return 0
    return parallel_strings * int(rules.STRING_FUSE_POLES.value)


def modules_for(kwp: float, module: PvModule) -> int:
    return max(1, round(kwp * 1000 / module.pmax_w))


def _closest(target: int, lengths: range, max_strings: int) -> tuple[int, int] | None:
    """(length, strings) closest to `target` modules; ties: fewer strings, then longer ones."""
    if max_strings < 1 or not lengths:
        return None
    _, strings, _, length = min(
        (abs(length * strings - target), strings, -length, length)
        for length in lengths
        for strings in range(1, max_strings + 1)
    )
    return length, strings


def layout(
    inverter: Product, plane_kwps: list[float], module: PvModule
) -> LayoutResult:
    """The layout closest to each plane's kWp within every MPPT limit, or the failed rule."""
    n_mppt = inverter.n_mppt
    window = inverter.mppt_voltage_range_v
    v_max = inverter.max_pv_input_v
    isc_limits = inverter.mppt_max_isc_a
    current_limits = inverter.mppt_max_current_a
    if not n_mppt or not window or not v_max or not isc_limits or not current_limits:
        return LayoutResult(None, "engineering_data")
    per_mppt = inverter.strings_per_mppt or [1] * n_mppt
    per_mppt = (per_mppt * n_mppt)[:n_mppt]
    isc_limits = (isc_limits * n_mppt)[:n_mppt]
    current_limits = (current_limits * n_mppt)[:n_mppt]

    voc_cold, vmp_hot = string_voltages(module)
    longest = min(math.floor(v_max / voc_cold), math.floor(window[1] / module.vmpp_v))
    shortest = math.ceil(window[0] / vmp_hot)
    if shortest > longest:
        return LayoutResult(None, "string_voltage")
    lengths = range(shortest, longest + 1)

    # Strings each MPPT takes within its count, current and short-circuit limits.
    capacity = [
        min(
            per_mppt[i],
            math.floor(current_limits[i] / module.impp_a),
            math.floor(isc_limits[i] / module.isc_a),
        )
        for i in range(n_mppt)
    ]
    if sum(capacity) < 1:
        return LayoutResult(None, "string_current")

    free = sorted(
        (i for i in range(n_mppt) if capacity[i]), key=lambda i: (-capacity[i], i)
    )
    loads = [0] * n_mppt
    lengths_at = [0] * n_mppt
    planes_at: list[int | None] = [None] * n_mppt
    count = 0
    order = sorted(range(len(plane_kwps)), key=lambda p: (-plane_kwps[p], p))
    for position, plane in enumerate(order):
        target = modules_for(plane_kwps[plane], module)
        # Leave one MPPT for every plane still to come.
        spare = len(free) - (len(order) - position - 1)
        options = []
        for used in range(1, spare + 1):
            best = _closest(target, lengths, sum(capacity[i] for i in free[:used]))
            if best is not None:
                options.append((abs(best[0] * best[1] - target), -used, best))
        if not options:
            return LayoutResult(None, "string_count")
        # Closest to the plane's array; among equals, spread over more MPPTs so
        # fewer strings run in parallel.
        miss, negative_used, (length, total) = min(options)
        used = -negative_used
        if miss > length:
            # Even the closest layout misses the plane by more than a string.
            return LayoutResult(None, "string_count")
        inputs = free[:used]
        # Spread the strings, the emptiest input first: parallel strings
        # (and fuses) only once every input of the plane has one.
        for _ in range(total):
            index = min(
                (i for i in inputs if loads[i] < capacity[i]),
                key=lambda i: (loads[i], i),
            )
            loads[index] += 1
        for i in inputs:
            lengths_at[i] = length if loads[i] else 0
            planes_at[i] = plane if loads[i] else None
        count += length * total
        free = [
            i for i in free if not loads[i]
        ]  # inputs left without strings stay free

    groups = tuple(
        MpptStrings(
            mppt=i + 1,
            plane=planes_at[i],
            strings=loads[i],
            modules_per_string=lengths_at[i],
            fuses=fuses_needed(loads[i], module),
        )
        for i in range(n_mppt)
    )
    return LayoutResult(
        StringLayout(
            strings=groups,
            module_count=count,
            array_kwp=round(count * module.pmax_w / 1000, 3),
            voc_cold_v=round(voc_cold, 1),
            vmp_hot_v=round(vmp_hot, 1),
        ),
        None,
    )
