"""POST /design/commercial: storage for businesses, from their 15-minute load profile.

With a load profile (the registering measurement every consumer above
rules.RLM_THRESHOLD_KWH receives), peak shaving is sized from the load itself:
the power is the peak above the cap, the energy the largest daily area above
it, and each day must leave enough room below the cap to recharge. Without a
profile the engine gives only indicative ranges from published rules of thumb
and asks for an inquiry; it does not pretend a design (docs/research/
2026-10-09/planner-methods.md section 5.2).
"""

from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass

from . import htw, rules, stacking
from .compatibility import Accessory
from .engine import Engine, documents_of, ref, release
from .models import (
    CommercialInput,
    CommercialResult,
    CommercialSystem,
    Line,
    LoadSummary,
    Range,
    Role,
    ShavingOption,
)
from .products import Product
from .texts import Locale, t

# Company and service questions go to the team address (owner ruling,
# AGENTS.md section 2, 2026-10-05).
TEAM_EMAIL = "sales@de-linker.com"
INVERTER_CLASSES = ("inverters", "all-in-one-systems")
BATTERY_CLASSES = ("battery-systems", "home-storage")
OPTION_STEPS = (
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
)  # shares of the peak shown as options


class LoadProfileError(ValueError):
    """The uploaded load profile cannot be read as 15-minute values."""


_NUMBER = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def _value(cell: str) -> float | None:
    text = cell.strip().replace(" ", "")
    if not text:
        return None
    if "," in text and "." in text:
        text = (
            text.replace(".", "").replace(",", ".")
            if text.rfind(",") > text.rfind(".")
            else text.replace(",", "")
        )
    elif "," in text:
        text = text.replace(",", ".")
    return float(text) if _NUMBER.match(text) else None


def parse_load_profile(text: str, unit: str) -> list[float]:
    """kW per 15-minute interval from CSV text: the last numeric cell of each line counts."""
    sample = text[:2048]
    delimiter = (
        ";"
        if sample.count(";") >= sample.count(",") and ";" in sample
        else ("\t" if "\t" in sample else ",")
    )
    values: list[float] = []
    for row in csv.reader(io.StringIO(text), delimiter=delimiter):
        numbers = [v for v in (_value(cell) for cell in row) if v is not None]
        if not numbers:
            continue  # header or empty line
        values.append(numbers[-1])
    if len(values) < 96 * 7:
        raise LoadProfileError(
            "a load profile needs at least one week of 15-minute values"
        )
    if any(v < 0 for v in values):
        raise LoadProfileError("the load profile contains negative values")
    interval = rules.LOAD_INTERVAL_H.value
    return [v / interval for v in values] if unit == "kWh" else values


def summary(load: list[float]) -> LoadSummary:
    interval = rules.LOAD_INTERVAL_H.value
    energy = sum(load) * interval
    peak = max(load)
    ordered = sorted(load, reverse=True)
    step = max(1, len(ordered) // 100)
    curve = [round(ordered[i], 1) for i in range(0, len(ordered), step)][:100]
    days = len(load) * interval / 24
    return LoadSummary(
        intervals=len(load),
        days=round(days, 1),
        annual_kwh=round(energy * 365 / days),
        peak_kw=round(peak, 1),
        base_kw=round(ordered[int(len(ordered) * 0.9)], 1),
        full_load_hours=round(energy / peak * 365 / days) if peak else 0,
        duration_curve_kw=curve,
    )


@dataclass(frozen=True)
class Shaving:
    cap_kw: float
    power_kw: float
    energy_kwh: float  # usable battery energy, after the discharge efficiency
    events: int
    short_days: int  # days without enough headroom below the cap to recharge


def shave(load: list[float], cap_kw: float) -> Shaving:
    """Power and energy that keep every interval at or below `cap_kw`."""
    interval = rules.LOAD_INTERVAL_H.value
    per_day = round(24 / interval)
    power = max(0.0, max(load) - cap_kw)
    events = 0
    above_previous = False
    worst = 0.0
    short = 0
    for start in range(0, len(load), per_day):
        day = load[start : start + per_day]
        need = sum(max(0.0, p - cap_kw) for p in day) * interval
        room = sum(max(0.0, cap_kw - p) for p in day) * interval
        worst = max(worst, need)
        if need > room:
            short += 1
        for p in day:
            above = p > cap_kw
            if above and not above_previous:
                events += 1
            above_previous = above
    energy = worst / rules.HTW_DISCHARGE_EFFICIENCY.value
    return Shaving(round(cap_kw, 1), round(power, 1), round(energy, 1), events, short)


def options(load: list[float]) -> list[Shaving]:
    peak = max(load)
    return [shave(load, peak * (1 - share)) for share in OPTION_STEPS]


# Hardware ---------------------------------------------------------------------------------


def _controller(
    engine: Engine, inverter: Product
) -> tuple[int | None, list[Accessory]]:
    found = engine.compatibility.requirements(inverter.model, "parallel_controller")
    if not found:
        return None, []
    requirement = found[0]
    return requirement.max_units, list(requirement.accessories)


def systems(
    engine: Engine, power_kw: float, energy_kwh: float, locale: Locale
) -> list[CommercialSystem]:
    """Up to three systems of our range that reach the power and the energy, smallest first."""
    out: list[tuple[tuple[float, float, int], CommercialSystem]] = []
    for inverter in engine.products.in_class(*INVERTER_CLASSES):
        if (
            inverter.application != "commercial"
            or inverter.phase != 3
            or not inverter.ac_power_kw
        ):
            continue
        max_units, controller = _controller(engine, inverter)
        units = max(1, math.ceil(power_kw / inverter.ac_power_kw))
        if units > 1 and not max_units:
            continue  # no documented way to run this model in parallel
        if max_units and units > max_units:
            continue
        own = inverter.usable_kwh
        if own:  # an all-in-one cabinet with its own documented usable energy
            total = own * units
            if total < energy_kwh:
                units = math.ceil(energy_kwh / own)
                if max_units and units > max_units:
                    continue
            lines = [_line(inverter, units, "inverter", locale)] + _controller_lines(
                engine, controller, units, locale
            )
            system = CommercialSystem(
                inverter=ref(inverter),
                inverter_units=units,
                battery=None,
                battery_units=0,
                usable_kwh=round(own * units, 1),
                power_kw=round(inverter.ac_power_kw * units, 1),
                release=None,
                lines=lines,
            )
            out.append(((system.power_kw, system.usable_kwh, inverter.id), system))
            continue
        for battery in engine.products.in_class(*BATTERY_CLASSES):
            pair = engine.compatibility.pair(inverter.model, battery.model)
            # Each inverter carries the same battery configuration, within the
            # stacking figures and the release; the smallest that reaches the energy.
            reaching = [
                config
                for config in stacking.configurations(inverter, battery, pair)
                if config.usable_kwh * units >= energy_kwh
            ]
            if not reaching:
                continue
            config = min(reaching, key=lambda c: (c.usable_kwh, c.quantity))
            lines = [
                _line(inverter, units, "inverter", locale),
                _line(battery, config.quantity * units, "battery", locale),
            ]
            for accessory in pair.accessories:
                matches = engine.products.by_model_pattern(accessory.model)
                if matches:
                    per = {"system": 1, "stack": config.stacks, "unit": 1}[
                        accessory.per
                    ]
                    lines.append(
                        _line(
                            matches[0],
                            accessory.quantity * per * units,
                            "accessory",
                            locale,
                        )
                    )
            lines += _controller_lines(engine, controller, units, locale)
            system = CommercialSystem(
                inverter=ref(inverter),
                inverter_units=units,
                battery=ref(battery),
                battery_units=config.quantity * units,
                usable_kwh=round(config.usable_kwh * units, 1),
                power_kw=round(inverter.ac_power_kw * units, 1),
                release=release(pair, locale),
                lines=lines,
            )
            key = (system.power_kw, system.usable_kwh, inverter.id * 10000 + battery.id)
            out.append((key, system))
    return [system for _, system in sorted(out, key=lambda item: item[0])[:3]]


_LABELS: dict[Role, str] = {
    "inverter": "line.inverter",
    "battery": "line.battery_units",
    "accessory": "line.accessory",
    "controller": "line.controller",
}


def _line(product: Product, quantity: int, role: Role, locale: Locale) -> Line:
    return Line(
        role=role,
        product=ref(product),
        quantity=quantity,
        unit="pcs",
        label=t(_LABELS[role], locale),
        basis=[],
        documents=documents_of(product, "datasheet", locale),
    )


def _controller_lines(
    engine: Engine, controller: list[Accessory], units: int, locale: Locale
) -> list[Line]:
    if units < 2:
        return []
    lines = []
    for accessory in controller:
        matches = engine.products.by_model_pattern(accessory.model)
        if matches:
            lines.append(
                Line(
                    role="controller",
                    product=ref(matches[0]),
                    quantity=accessory.quantity,
                    unit="pcs",
                    label=t("line.controller", locale),
                    basis=[],
                    documents=documents_of(matches[0], "datasheet", locale),
                )
            )
    return lines


# Design --------------------------------------------------------------------------------------


def _inquiry(request: CommercialInput) -> str:
    subject = (
        "Commercial storage inquiry"
        if request.locale == "en"
        else "Anfrage Gewerbespeicher"
    )
    return f"mailto:{TEAM_EMAIL}?subject={subject.replace(' ', '%20')}%20{request.plz}"


def design(
    engine: Engine, request: CommercialInput, generated_at: str
) -> CommercialResult:
    locale = request.locale
    warnings: list[str] = []
    basis: list[str] = []
    reserve = 0.0
    if "backup" in request.goals and request.backup_load_kw and request.backup_hours:
        # The same reserve the residential path holds back (htw.backup_reserve).
        reserve = htw.backup_reserve(request.backup_load_kw, request.backup_hours)
        basis.append(
            t(
                "ci.basis.backup",
                locale,
                load=request.backup_load_kw,
                hours=request.backup_hours,
                kwh=round(reserve, 1),
            )
        )
    if request.grid_connection_kva > rules.NA_PROTECTION_KVA.value:
        warnings.append(t("warn.na_protection", locale))
    if request.grid_connection_kva > rules.VDE_4110_KW.value:
        warnings.append(t("warn.vde_4110", locale))

    if request.load_profile_csv:
        load = parse_load_profile(request.load_profile_csv, request.load_profile_unit)
        overview = summary(load)
        table = [
            ShavingOption(
                cap_kw=o.cap_kw,
                power_kw=o.power_kw,
                energy_kwh=o.energy_kwh,
                events=o.events,
            )
            for o in options(load)
        ]
        if overview.days < 360:
            warnings.append(
                t("ci.warn.short_profile", locale, days=round(overview.days))
            )
        if "peak_shaving" in request.goals and request.target_peak_kw:
            result = shave(load, request.target_peak_kw)
            power, energy = result.power_kw, result.energy_kwh + reserve
            basis.append(
                t(
                    "ci.basis.shaving",
                    locale,
                    peak=overview.peak_kw,
                    cap=result.cap_kw,
                    power=power,
                    energy=result.energy_kwh,
                )
            )
            if result.short_days:
                warnings.append(t("ci.warn.recharge", locale, days=result.short_days))
            return CommercialResult(
                status="sized",
                load=overview,
                options=table,
                power_kw_range=Range(low=power, high=power),
                energy_kwh_range=Range(low=round(energy, 1), high=round(energy, 1)),
                basis=basis,
                systems=systems(engine, power, energy, locale),
                warnings=warnings,
                inquiry=_inquiry(request),
            )
        if "peak_shaving" in request.goals:
            warnings.append(t("ci.warn.pick_cap", locale))
        return CommercialResult(
            status="indicative",
            load=overview,
            options=table,
            power_kw_range=None,
            energy_kwh_range=None,
            basis=basis + [t("ci.basis.options", locale)],
            systems=[],
            warnings=warnings,
            inquiry=_inquiry(request),
        )

    # Without a profile: published rules of thumb only, as ranges.
    power_low = power_high = 0.0
    energy_low = energy_high = reserve
    if "peak_shaving" in request.goals and request.peak_kw and request.target_peak_kw:
        shaved = max(0.0, request.peak_kw - request.target_peak_kw)
        power_low = power_high = shaved
        energy_low += shaved * rules.CI_HOURS_PEAK.value
        energy_high += shaved * rules.CI_HOURS_SELF_CONSUMPTION.value
        basis.append(t("ci.basis.peak_indicative", locale, power=shaved))
    if "self_consumption" in request.goals:
        if request.pv_kwp:
            energy = request.pv_kwp * rules.CI_KWH_PER_KWP.value
            basis.append(t("ci.basis.self_pv", locale, kwp=request.pv_kwp, kwh=energy))
            energy_low, energy_high = energy_low + energy, energy_high + energy
        else:
            mwh = request.annual_kwh / 1000
            low, high = (
                mwh * rules.CI_KWP_PER_MWH_LOW.value,
                mwh * rules.CI_KWP_PER_MWH_HIGH.value,
            )
            basis.append(
                t("ci.basis.self_consumption", locale, low=round(low), high=round(high))
            )
            energy_low, energy_high = energy_low + low, energy_high + high
        power_low = max(power_low, energy_low / rules.CI_HOURS_SELF_CONSUMPTION.value)
        power_high = max(power_high, energy_high / rules.CI_HOURS_PEAK.value)
    if request.annual_kwh > rules.RLM_THRESHOLD_KWH.value:
        warnings.append(t("ci.warn.rlm", locale))
    known = energy_high > 0 or power_high > 0
    return CommercialResult(
        status="indicative",
        load=None,
        options=[],
        power_kw_range=Range(low=round(power_low, 1), high=round(power_high, 1))
        if known
        else None,
        energy_kwh_range=Range(low=round(energy_low, 1), high=round(energy_high, 1))
        if known
        else None,
        basis=basis + [t("ci.basis.indicative", locale)],
        systems=[],
        warnings=warnings,
        inquiry=_inquiry(request),
    )
