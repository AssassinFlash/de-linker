"""Show recorded physical materials without implying approval or completeness."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Object
from .project_materials import material_quantity
from .report_numbers import number


def material_section(review: Object, locale: str) -> ReportSection:
    de = locale == "de"
    rows: list[ReportRow] = []
    for item in cast(list[Object], review["rows"]):
        count = (
            ("Offen" if de else "Open")
            if item["quantity"] is None
            else material_quantity(item, locale)
        )
        status = item["circuit_status"]
        link = (
            ("Kein Stromkreis zugeordnet" if de else "No circuit linked")
            if status == "not_linked"
            else ("Stromkreis nicht verfügbar" if de else "Circuit unavailable")
            if status == "circuit_unavailable"
            else str(item["circuit_id"])
        )
        comparison = item.get("comparison_result")
        detail = ""
        href = None
        if isinstance(comparison, dict):
            statuses = {
                "within_recommendation": (
                    "Declared cross-section is within the manufacturer's numeric range",
                    "Angegebener Querschnitt liegt im Zahlenbereich des Herstellers",
                ),
                "outside_recommendation": (
                    "Outside manufacturer cross-section recommendation",
                    "Außerhalb der Herstellerempfehlung für den Querschnitt",
                ),
                "meets_minimum_values": (
                    "Meets the two manufacturer minimum values",
                    "Erfüllt die beiden Mindestwerte des Herstellers",
                ),
                "below_minimum_values": (
                    "Below a manufacturer minimum value",
                    "Unter einem Mindestwert des Herstellers",
                ),
            }
            label = statuses.get(
                str(comparison.get("status")),
                ("Comparison unavailable", "Vergleich nicht verfügbar"),
            )[1 if de else 0]
            fact = comparison.get("fact")
            source = fact.get("source") if isinstance(fact, dict) else None
            detail = f" · {label}"
            binding = item.get("comparison")
            if isinstance(binding, dict):
                for key, unit in (
                    ("cross_section_mm2", "mm²"),
                    ("rated_current_a", "A"),
                    ("rated_voltage_v", "V"),
                ):
                    if binding.get(key) is not None:
                        detail += " · " + number(binding[key], locale, unit)
            if isinstance(source, dict):
                detail += f" · p. {source['page']} · {source['quote']}"
                href = cast(str, source["url"])
        rows.append(
            ReportRow(
                label=str(item["name"]),
                value=f"{count} · {link} · {item['specification']} · {item['source_note']}{detail}",
                href=href,
            )
        )
    return ReportSection(
        id="installation-declared-materials",
        title="Angegebene Installationsmaterialien"
        if de
        else "Declared installation materials",
        paragraphs=[
            "Projektangaben; technische Eignung und Vollständigkeit der Materialliste sind nicht geprüft."
            if de
            else "Project declarations; technical suitability and completeness of the materials list are not assessed."
        ],
        rows=rows,
    )
