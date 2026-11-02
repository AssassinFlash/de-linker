"""Show bounded comparisons of a physical conductor with a cited instruction."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Object
from .project_materials import conductor_specification
from .report_numbers import number


def conductor_section(cables: list[Object], locale: str) -> ReportSection:
    de = locale == "de"
    rows: list[ReportRow] = []
    for cable in cables:
        comparison = cable.get("manufacturer_comparison")
        if not isinstance(comparison, dict):
            continue
        status = comparison.get("status")
        message = (
            (
                "Innerhalb des empfohlenen Querschnittsbereichs"
                if de
                else "Within the recommended cross-section range"
            )
            if status == "within_recommendation"
            else (
                "Außerhalb des empfohlenen Querschnittsbereichs"
                if de
                else "Outside the recommended cross-section range"
            )
            if status == "outside_recommendation"
            else (
                "Vergleich nicht verfügbar; Auswahl und Bestätigung prüfen"
                if de
                else "Comparison unavailable; check the selection and confirmation"
            )
        )
        fact = comparison.get("fact")
        source = fact.get("source") if isinstance(fact, dict) else None
        detail = f"{conductor_specification(cable, locale)} · {message}"
        href = None
        if isinstance(source, dict) and isinstance(fact, dict):
            spec = cast(Object, fact["specification"])
            limits = cast(Object, spec["recommended_conductor_mm2"])
            detail += (
                f" · {'Herstellerbereich' if de else 'Manufacturer range'} "
                f"{number(limits['low'], locale, 'mm²')}–{number(limits['high'], locale, 'mm²')}"
            )
            detail += f" · p. {source['page']} · {source['quote']}"
            href = cast(str, source["url"])
        rows.append(ReportRow(label=str(cable["name"]), value=detail, href=href))
    return ReportSection(
        id="installation-conductor-manufacturer-comparisons",
        title="Herstellervergleich der Leiterquerschnitte"
        if de
        else "Manufacturer conductor cross-section comparisons",
        paragraphs=[
            "Kabelaufbau, Schutz und Erdung müssen gesondert geprüft werden."
            if de
            else "Cable construction, protection and earthing require separate checks."
        ],
        rows=rows,
    )
