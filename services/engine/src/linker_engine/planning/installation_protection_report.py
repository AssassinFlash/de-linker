"""Present project-evidence comparisons without claiming protection approval."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Object
from .report_numbers import comparison_values, number


def _state(row: Object, locale: str) -> str:
    de = locale == "de"
    status = row.get("status")
    if status == "within_declared_values":
        return "Innerhalb der angegebenen Werte" if de else "Within the declared values"
    if status == "outside_declared_values":
        return (
            "Außerhalb der angegebenen Werte" if de else "Outside the declared values"
        )
    reasons = {
        "context_unavailable": (
            "Circuit, device, operating condition or conductor is unavailable",
            "Stromkreis, Schutzgerät, Betriebsfall oder Leiter ist nicht verfügbar",
        ),
        "confirmation_required": (
            "Confirm the current evidence and circuit",
            "Aktuelle Nachweise und Stromkreis bestätigen",
        ),
        "context_changed": (
            "Circuit or evidence changed; confirm again",
            "Stromkreis oder Nachweise geändert; erneut bestätigen",
        ),
        "fault_range_missing": (
            "Fault-current range is missing",
            "Kurzschlussstrombereich fehlt",
        ),
        "device_rating_missing": (
            "Breaking-capacity evidence is missing",
            "Nachweis des Ausschaltvermögens fehlt",
        ),
        "clearing_evidence_missing": (
            "Clearing-time evidence is missing",
            "Nachweis der Abschaltzeit fehlt",
        ),
        "zero_minimum_fault_current": (
            "Zero minimum fault current requires a separate operating assessment",
            "Ein Mindestfehlerstrom von null erfordert eine gesonderte Funktionsprüfung",
        ),
        "rating_conditions_differ": (
            "Device rating voltage or current type differs",
            "Bemessungsspannung oder Stromart des Geräts stimmt nicht überein",
        ),
        "fault_range_not_covered": (
            "Let-through evidence does not cover the fault range",
            "Der Durchlassenergienachweis deckt den Fehlerstrombereich nicht ab",
        ),
        "adiabatic_duration_exceeds_five_seconds": (
            "Clearing duration exceeds the five-second method",
            "Abschaltdauer überschreitet den Fünf-Sekunden-Bereich der Methode",
        ),
        "clearing_time_evidence_inconsistent": (
            "Clearing-time evidence is inconsistent",
            "Die Nachweise zur Abschaltzeit widersprechen sich",
        ),
        "numerical_range_not_supported": (
            "Numerical range is not supported",
            "Zahlenbereich wird nicht unterstützt",
        ),
    }
    detail = "Nicht geprüft" if de else "Not assessed"
    reason = reasons.get(str(row.get("reason")))
    return detail + (" · " + reason[1 if de else 0] if reason else "")


def protection_section(review: Object, locale: str) -> ReportSection:
    de = locale == "de"
    rows: list[ReportRow] = []
    for item in cast(list[Object], review.get("assessments", [])):
        scenario = str(item["scenario"])
        for key, title, unit, measured_label, limit_label in (
            (
                "breaking",
                "Ausschaltvermögen" if de else "Breaking capacity",
                "A",
                "Maximaler Fehlerstrom" if de else "Maximum prospective fault current",
                "Ausschaltvermögen des Schutzgeräts"
                if de
                else "device breaking capacity",
            ),
            (
                "disconnection",
                "Abschaltzeit" if de else "Clearing time",
                "s",
                "Längste Abschaltzeit des Schutzgeräts"
                if de
                else "Worst-case device clearing time",
                "zulässige Abschaltzeit" if de else "required maximum clearing time",
            ),
        ):
            value = cast(Object, item[key])
            detail = _state(value, locale)
            measured, maximum = value.get("measured"), value.get("maximum")
            if isinstance(measured, (int, float)) and isinstance(maximum, (int, float)):
                left, right = comparison_values(measured, maximum, locale, unit)
                relation = ">" if value["status"] == "outside_declared_values" else "≤"
                detail += f" · {measured_label} {left} {relation} {limit_label} {right}"
            if key == "breaking" and isinstance(value.get("voltage_v"), (int, float)):
                detail += f" · {number(value['voltage_v'], locale, 'V')} {str(value.get('current_kind', '')).upper()}"
            if key == "disconnection" and isinstance(
                value.get("minimum_fault_a"), (int, float)
            ):
                detail += (
                    " · Mindestfehlerstrom " if de else " · Minimum fault current "
                ) + number(value["minimum_fault_a"], locale, "A")
            for field in (
                "fault_source_note",
                "device_source_note",
                "limit_source_note",
            ):
                if isinstance(value.get(field), str):
                    detail += " · " + cast(str, value[field])
            rows.append(ReportRow(label=f"{scenario} · {title}", value=detail))
        for thermal in cast(list[Object], item.get("thermal", [])):
            detail = _state(thermal, locale)
            measured, maximum = thermal.get("measured"), thermal.get("maximum")
            if isinstance(measured, (int, float)) and isinstance(maximum, (int, float)):
                left, right = comparison_values(measured, maximum, locale, "A²s")
                relation = (
                    ">" if thermal["status"] == "outside_declared_values" else "≤"
                )
                energy = (
                    "Maximales Durchlassintegral I²t"
                    if de
                    else "Maximum let-through I²t"
                )
                limit = (
                    "thermische Leitergrenze k²S²" if de else "conductor withstand k²S²"
                )
                detail += f" · {energy} {left} {relation} {limit} {right}"
                detail += f" · S {number(thermal['cross_section_mm2'], locale, 'mm²')} · k {number(thermal['k_a_sqrt_s_per_mm2'], locale, 'A√s/mm²')}"
                detail += f" · {number(thermal['coverage_min_fault_a'], locale, 'A')}–{number(thermal['coverage_max_fault_a'], locale, 'A')} · {number(thermal['maximum_clear_s'], locale, 's')}"
            for field in (
                "fault_source_note",
                "k_source_note",
                "let_through_source_note",
            ):
                if isinstance(thermal.get(field), str):
                    detail += " · " + cast(str, thermal[field])
            rows.append(
                ReportRow(
                    label=f"{scenario} · {'Thermische Beanspruchung' if de else 'Thermal withstand'} · {thermal['run_id']} / {thermal['core_role']}",
                    value=detail,
                )
            )
    return ReportSection(
        id="installation-protection",
        title="Schutz und thermische Beanspruchung"
        if de
        else "Protection and thermal withstand",
        paragraphs=[
            "Vergleich der angegebenen Projektwerte unter den bestätigten Bedingungen. Selektivität, Schutzleiterführung, Erdungssystem, automatische Abschaltung und nationale Anforderungen sind damit nicht freigegeben."
            if de
            else "Comparison of project-declared values under the confirmed conditions. This does not approve selectivity, protective conductor routing, the earthing system, automatic disconnection or national requirements."
        ],
        rows=rows
        + [
            ReportRow(
                label="Methode" if de else "Method",
                value="Schneider Electric: Leiter im Kurzschlussfall (höchstens 5 s)"
                if de
                else "Schneider Electric: conductor short-circuit withstand (up to 5 s)",
                href="https://www.electrical-installation.org/enwiki/Verification_of_the_withstand_capabilities_of_cables_under_short-circuit_conditions#Thermal_constraints",
            ),
            ReportRow(
                label="Schutzleiter" if de else "Protective conductor",
                value="Schneider Electric: adiabatische Bemessung"
                if de
                else "Schneider Electric: adiabatic sizing",
                href="https://www.electrical-installation.org/enwiki/Sizing_of_protective_earthing_conductor#Values_of_factor_k_to_be_used_in_the_formulae",
            ),
        ],
    )
