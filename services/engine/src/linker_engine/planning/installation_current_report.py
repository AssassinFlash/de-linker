"""Present a single conductor's comparison with a cited manufacturer table row."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Object

STATUS = {
    "below_reference": ("Below the listed current", "Unter dem Tabellenwert"),
    "equal_reference": ("Equal to the listed current", "Entspricht dem Tabellenwert"),
    "above_reference": ("Above the listed current", "Über dem Tabellenwert"),
    "not_evaluated": ("Comparison unavailable", "Vergleich nicht möglich"),
}
LAYING = {
    "single_in_air": ("Single cable in air", "Einzelnes Kabel in Luft"),
    "single_on_surface": (
        "Single cable on a surface",
        "Einzelnes Kabel auf einer Oberfläche",
    ),
    "two_touching_on_surface": (
        "Two cables touching on a surface",
        "Zwei sich berührende Kabel auf einer Oberfläche",
    ),
}
REASONS = {
    "operating_condition_missing": (
        "No operating condition recorded",
        "Betriebsfall fehlt",
    ),
    "circuit_kind_not_supported": (
        "Requires a PV DC circuit",
        "PV-Gleichstromkreis erforderlich",
    ),
    "condition_method_not_supported": (
        "Requires a DC operating condition",
        "Gleichstrom-Betriebsfall erforderlich",
    ),
    "current_path_not_single_pair": (
        "Requires one conductor for each polarity",
        "Je Polarität ist ein einzelner Leiter erforderlich",
    ),
    "current_path_not_confirmed": (
        "Unbranched current path unconfirmed",
        "Unverzweigter Strompfad nicht bestätigt",
    ),
    "confirmation_context_changed": (
        "Confirm the laying conditions for the current connection and route",
        "Verlegebedingungen für den aktuellen Anschluss und Leitungsweg erneut bestätigen",
    ),
    "installation_conditions_not_confirmed": (
        "Installation conditions unconfirmed",
        "Verlegebedingungen nicht bestätigt",
    ),
    "touching_pair_mismatch": (
        "The two touching cables are not confirmed as a pair",
        "Die beiden berührenden Kabel sind nicht als Paar bestätigt",
    ),
    "cable_reference_unavailable": (
        "Cable reference unavailable",
        "Kabelreferenz nicht verfügbar",
    ),
    "cable_specification_mismatch": (
        "Conductor differs from the cable reference",
        "Leiter stimmt nicht mit der Kabelreferenz überein",
    ),
    "reference_rating_unavailable": (
        "Manufacturer table entry unavailable",
        "Herstellerangabe nicht verfügbar",
    ),
    "reference_rating_conditions_mismatch": (
        "Installation differs from the table conditions",
        "Verlegebedingungen weichen von der Tabelle ab",
    ),
    "reference_source_unavailable": (
        "The cited document could not be verified",
        "Das angegebene Dokument konnte nicht geprüft werden",
    ),
}


def _value(value: object, unit: str, de: bool) -> str:
    if not isinstance(value, int | float):
        return "—"
    number = format(value, ".6g")
    return f"{number.replace('.', ',') if de else number} {unit}"


def current_sections(
    electrical: Object, cables: list[Object], locale: str
) -> list[ReportSection]:
    segments = electrical.get("reference_current_segments")
    if not isinstance(segments, list) or not segments:
        return []
    de = locale == "de"
    cables_by_id = {str(c["id"]): c["name"] for c in cables}
    circuits = cast(list[Object], electrical["circuits"])
    circuit_names = {str(c["circuit_id"]): c["name"] for c in circuits}
    conditions = {
        (str(c["circuit_id"]), str(r["condition_id"])): r["name"]
        for c in circuits
        for r in cast(list[Object], c["conditions"])
    }
    section = ReportSection(
        id="installation-manufacturer-current",
        title="Leiterstrom im Vergleich zur Herstellertabelle"
        if de
        else "Conductor current compared with the manufacturer's table",
        paragraphs=[
            "Der Tabellenwert gilt für den angegebenen Leiterabschnitt und die genannte Verlegung. Die Leitertemperatur der Tabelle ist keine gemessene Betriebstemperatur. Für die Freigabe des Stromkreises sind weitere Prüfungen erforderlich."
            if de
            else "The listed current applies to the conductor segment and laying conditions shown. The conductor temperature in the table is a reference condition. Circuit protection and the suitability of the complete installation still require separate checks."
        ],
    )
    for segment in cast(list[Object], segments):
        cid = str(segment["circuit_id"])
        title = " · ".join(
            str(s)
            for s in (
                circuit_names.get(cid),
                conditions.get((cid, str(segment["condition_id"]))),
                cables_by_id.get(str(segment["run_id"])),
            )
            if s
        )
        status = STATUS[str(segment["status"])][de]
        reasons = [
            REASONS[str(code)][de] for code in cast(list[str], segment["reasons"])
        ]
        section.rows.append(
            ReportRow(label=title, value=" · ".join([status, *reasons]))
        )
        if segment["project_current_a"] is not None:
            section.rows.append(
                ReportRow(
                    label="Strom im Betriebsfall / Tabellenwert"
                    if de
                    else "Operating current / listed current",
                    value=f"{_value(segment['project_current_a'], 'A', de)} / {_value(segment['reference_current_a'], 'A', de)}",
                )
            )
        if segment.get("reference_input_id") and segment.get("product_revision"):
            section.rows.append(
                ReportRow(
                    label="Kabelreferenz und Produktstand"
                    if de
                    else "Cable reference and product revision",
                    value=f"{segment['reference_input_id']} · {segment['product_revision']}",
                )
            )
        installation = segment["installation"]
        if isinstance(installation, dict) and installation.get("source_note"):
            section.rows.append(
                ReportRow(
                    label="Grundlage der Verlegung"
                    if de
                    else "Basis for laying conditions",
                    value=str(installation["source_note"]),
                )
            )
        rating = segment.get("rating")
        if isinstance(rating, dict):
            doc = cast(Object, rating["source"])
            section.rows.append(
                ReportRow(
                    label=LAYING[str(rating["laying"])][de],
                    value=(
                        f"{_value(rating['current_a'], 'A', de)} · "
                        f"{'Umgebung' if de else 'Ambient'} {_value(rating['ambient_temperature_c'], '°C', de)} · "
                        f"{'Leiter (Tabellenbedingung)' if de else 'Conductor (table condition)'} {_value(rating['rated_conductor_temperature_c'], '°C', de)}"
                    ),
                )
            )
            section.rows.append(
                ReportRow(
                    label=f"{'Herstellerquelle' if de else 'Manufacturer source'} · {'S.' if de else 'p.'} {doc['page']}",
                    value=f"{doc['quote']} · {'Dokumentstand' if de else 'Document revision'} {doc['document_revision']}",
                    href=str(doc["url"]),
                )
            )
    return [section]
