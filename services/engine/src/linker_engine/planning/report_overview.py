"""Commercial report figures from selected, frozen calculation results."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import cast

from linker_engine.models import ReportSummaryCard

from .canonical import Json, Object
from .power_series import PowerSeries
from .pv_dc_profile import DcPvProfile
from .report_copy import text
from .report_numbers import number


def calendar_totals(
    intervals: Iterable[tuple[datetime, datetime, float, float | None]],
) -> Object | None:
    """Integrate mean interval power at UTC month boundaries over complete years."""
    start: datetime | None = None
    previous: datetime | None = None
    pv: list[Json] = [0.0] * 12
    load: list[Json] = [0.0] * 12
    whole_site = True
    for begin, end, generation, demand in intervals:
        begin, end = begin.astimezone(UTC), end.astimezone(UTC)
        if previous is not None and begin != previous:
            return None
        if start is None:
            start = begin
        previous = end
        whole_site = whole_site and demand is not None
        while begin < end:
            boundary = datetime(
                begin.year + (begin.month == 12), begin.month % 12 + 1, 1, tzinfo=UTC
            )
            cutoff = min(boundary, end)
            hours = (cutoff - begin).total_seconds() / 3600
            idx = begin.month - 1
            pv[idx] = cast(float, pv[idx]) + generation * hours
            if demand is not None:
                load[idx] = cast(float, load[idx]) + demand * hours
            begin = cutoff
    if not start or not previous or not any(pv):
        return None
    years = previous.year - start.year
    if years < 1 or start.timetuple()[1:6] != previous.timetuple()[1:6]:
        return None
    return {
        "pv_kwh": [cast(float, v) / years for v in pv],
        "load_kwh": [cast(float, v) / years for v in load] if whole_site else None,
        "start": start.date().isoformat(),
        "end": previous.date().isoformat(),
        "years": years,
    }


def profile_months(profile: PowerSeries | DcPvProfile) -> Object | None:
    return calendar_totals(
        (i.start, i.end, kw, None)
        for i, kw in zip(profile.intervals, profile.values_kw, strict=True)
    )


def replay_months(trace: Object) -> Object | None:
    def intervals() -> Iterable[tuple[datetime, datetime, float, float | None]]:
        for flow in cast(list[Object], trace["flows"]):
            frame = cast(Object, flow["frame"])
            interval = cast(Object, frame["interval"])
            if "pv_available_dc_kw" in frame:
                power = cast(float, flow["pv_available_dc_kw"]) - cast(
                    float, flow["pv_curtailed_dc_kw"]
                )
            else:
                power = cast(float, flow["pv_available_kw"]) - cast(
                    float, flow.get("curtailed_kw", 0)
                )
            yield (
                datetime.fromisoformat(str(interval["start_utc"])),
                datetime.fromisoformat(str(interval["end_utc"])),
                max(0.0, power),
                cast(float, frame["load_kw"])
                if frame["load_measurement"] == "gross_load"
                else None,
            )

    return calendar_totals(intervals())


def summary_cards(source: Object, locale: str) -> list[ReportSummaryCard]:
    de = locale == "de"
    cards = []
    components = source.get("pv_components")
    peak = components.get("nameplate_kwp") if isinstance(components, dict) else None
    references = source.get("pvgis_known_ac_references")
    if peak is None and isinstance(references, list) and len(references) == 1:
        arrays = cast(list[Object], cast(Object, references[0])["arrays"])
        if arrays:
            peak = sum(cast(float, a["peak_power_kwp"]) for a in arrays)
    selection = source.get("equipment_selection")
    if isinstance(selection, dict) and peak is None:
        peak = selection.get("pv_dc_kw")
    if isinstance(peak, (int, float)) and peak > 0:
        cards.append(
            ReportSummaryCard(
                label="PV-Leistung" if de else "PV array",
                value=number(peak, locale, "kWp"),
            )
        )
    equipment = source.get("equipment")
    if isinstance(equipment, dict):
        checks = cast(list[Object], equipment["checks"])
        usable = [
            check["actual"]
            for check in checks
            if check.get("id") == "usable_energy"
            and isinstance(check.get("actual"), (float, int))
        ]
        if len(usable) == 1:
            cards.append(
                ReportSummaryCard(
                    label="Nutzbare Speicherkapazität" if de else "Usable storage",
                    value=number(usable[0], locale, "kWh"),
                    note="Geräteauslegung" if de else "Equipment assessment",
                )
            )
    monthly = source.get("monthly_energy")
    if isinstance(monthly, dict):
        total = sum(cast(list[float], monthly["pv_kwh"]))
        cards.append(
            ReportSummaryCard(
                label="Erwarteter Jahresertrag"
                if de
                else "Estimated annual generation",
                value=number(round(total, 1), locale, "kWh"),
                note=f"{monthly['start']} – {monthly['end']}",
            )
        )
    brief = source.get("brief")
    phase = selection.get("grid_phase") if isinstance(selection, dict) else None
    if phase in (1, 3):
        cards.append(
            ReportSummaryCard(
                label="Netzanschluss" if de else "Grid connection",
                value=f"{phase}-phasig" if de else f"{phase}-phase",
                note="Projektangabe" if de else "Project input",
            )
        )
    elif isinstance(brief, dict) and brief.get("system_scope"):
        cards.append(
            ReportSummaryCard(
                label="Systemkonzept" if de else "System design",
                value=text(f"scope_{brief['system_scope']}", locale),
            )
        )
    return cards
