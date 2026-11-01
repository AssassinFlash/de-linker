"""Localize frozen conductor results and retain their conditions and sources."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection, ReportTable

from .canonical import Object

LABELS = {
    "resistance_upper_bound_not_absolute_drop_bound": (
        "With a leading power factor, maximum resistance does not bound the magnitude of voltage change. The project limit has not been assessed.",
        "Bei kapazitivem Leistungsfaktor begrenzt der maximale Widerstand nicht den Betrag der Spannungsänderung. Der Projektgrenzwert wurde nicht bewertet.",
    ),
    "maximum": ("Maximum resistance", "Maximaler Widerstand"),
    "nominal": ("Nominal resistance", "Nominaler Widerstand"),
    "calculated": ("Calculated", "Berechnet"),
    "method_not_applicable": ("Method does not apply", "Methode nicht anwendbar"),
    "data_insufficient": ("More input needed", "Angaben fehlen"),
    "not_evaluated": ("Limit not checked", "Grenzwert nicht geprüft"),
    "not_declared": ("No project limit recorded", "Kein Projektgrenzwert erfasst"),
    "within_declared_limit": (
        "Within recorded project limit",
        "Innerhalb des erfassten Projektgrenzwerts",
    ),
    "exceeds_declared_limit": (
        "Exceeds recorded project limit",
        "Erfasster Projektgrenzwert überschritten",
    ),
    "resistance_upper_bound": (
        "Maximum conductor resistance",
        "Maximaler Leiterwiderstand",
    ),
    "nominal_parameters": ("Nominal parameters", "Nennparameter"),
    "mixed_resistance_parameters": (
        "Mixed maximum and nominal resistance",
        "Gemischte maximale und nominale Widerstandswerte",
    ),
    "dc_resistive": ("DC resistance", "DC-Widerstand"),
    "ac_two_wire": ("Two-wire AC", "Zweileiter-Wechselstrom"),
    "ac_balanced_three_phase": ("Balanced three-phase AC", "Symmetrischer Drehstrom"),
    "start_to_end": ("Start to end", "Anfang nach Ende"),
    "end_to_start": ("End to start", "Ende nach Anfang"),
    "lagging": ("Lagging", "Induktiv"),
    "leading": ("Leading", "Kapazitiv"),
    "dc_positive": ("DC positive", "DC-Plusleiter"),
    "dc_negative": ("DC negative", "DC-Minusleiter"),
    "line": ("Line conductor", "Außenleiter"),
    "neutral": ("Neutral conductor", "Neutralleiter"),
    "l1": ("L1", "L1"),
    "l2": ("L2", "L2"),
    "l3": ("L3", "L3"),
    "dc_condition_not_applicable": (
        "The recorded conditions do not support the DC method.",
        "Die erfassten Bedingungen passen nicht zum DC-Verfahren.",
    ),
    "ac_condition_not_applicable": (
        "The recorded conditions do not support the AC method.",
        "Die erfassten Bedingungen passen nicht zum AC-Verfahren.",
    ),
    "cable_runs_missing": ("No cable runs recorded.", "Keine Kabelstrecken erfasst."),
    "core_roles_missing": (
        "Conductor roles are missing.",
        "Die Leiterzuordnung fehlt.",
    ),
    "core_roles_not_applicable": (
        "Conductor roles do not match this method.",
        "Die Leiterzuordnung passt nicht zu diesem Verfahren.",
    ),
    "cable_reference_unavailable": (
        "The selected cable source is unavailable.",
        "Die gewählte Kabelquelle ist nicht verfügbar.",
    ),
    "cable_specification_mismatch": (
        "The cable specification differs from its source.",
        "Die Kabelangaben weichen von der Quelle ab.",
    ),
    "cable_conditions_mismatch": (
        "No cable parameters match these conditions.",
        "Für diese Bedingungen liegen keine passenden Kabelparameter vor.",
    ),
    "cable_parameter_set_ambiguous": (
        "More than one cable parameter set matches.",
        "Mehrere Kabelparametersätze passen zu den Bedingungen.",
    ),
    "route_quantity_unconfirmed": (
        "Cable length is not confirmed.",
        "Die Kabellänge ist nicht bestätigt.",
    ),
    "parallel_or_branched_cores_not_supported": (
        "This method does not cover parallel or branched conductors.",
        "Dieses Verfahren deckt parallele oder verzweigte Leiter nicht ab.",
    ),
    "current_path_incomplete": (
        "The current path is incomplete.",
        "Der Strompfad ist unvollständig.",
    ),
    "phase_impedances_not_equal": (
        "The phase impedances differ.",
        "Die Phasenimpedanzen unterscheiden sich.",
    ),
    "numerical_range_not_supported": (
        "The values exceed the supported calculation range.",
        "Die Werte überschreiten den unterstützten Rechenbereich.",
    ),
}


def _label(value: object, locale: str) -> str:
    return LABELS[str(value)][locale.startswith("de")] if value is not None else "—"


def _number(value: object) -> str:
    return f"{value:.6g}" if isinstance(value, (int, float)) else "—"


def electrical_sections(electrical: Object, locale: str) -> list[ReportSection]:
    de = locale.startswith("de")
    pairs = [
        (circuit, condition)
        for circuit in cast(list[Object], electrical["circuits"])
        for condition in cast(list[Object], circuit["conditions"])
    ]
    sections = [
        ReportSection(
            id="installation-electrical",
            title="Leiterberechnung im stationären Betrieb"
            if de
            else "Steady-state conductor calculation",
            paragraphs=[
                "Berechnet werden die erfassten Leiterabschnitte. Anschlussverluste, Strombelastbarkeit, Schutzkoordination und nationale Anforderungen sind noch nicht geprüft. Maximale Herstellerwiderstände begrenzen den Leiterwiderstand; sie belegen keine Obergrenze für die gesamte Anlage. Grenzwerte stammen aus den Projektangaben."
                if de
                else "The calculation covers the recorded conductor segments. Terminal losses, ampacity, protection coordination and national requirements remain unassessed. Manufacturer maximum resistance bounds conductor resistance; it does not establish an upper bound for the whole installation. Limits come from the project inputs."
            ],
            table=ReportTable(
                columns=[
                    "Stromkreis / Betriebsfall",
                    "Ergebnis / Grundlage",
                    "Spannungsfall (V / %)",
                    "Leiterverlust (W)",
                ]
                if de
                else [
                    "Circuit / condition",
                    "Result / basis",
                    "Voltage drop (V / %)",
                    "Conductor loss (W)",
                ],
                column_weights=[1.2, 1.8, 1, 1],
                rows=[
                    [
                        f"{circuit['name']} / {result['name']}",
                        " · ".join(
                            [
                                _label(result["status"], locale),
                                _label(result["value_basis"], locale),
                            ]
                        ),
                        f"{_number(result['voltage_drop_v'])} / {_number(result['voltage_drop_percent'])}",
                        _number(result["conductor_loss_w"]),
                    ]
                    for circuit, result in pairs
                ]
                + [
                    [
                        cast(str, circuit["name"]),
                        "Kein Betriebsfall erfasst"
                        if de
                        else "No operating condition recorded",
                        "—",
                        "—",
                    ]
                    for circuit in cast(list[Object], electrical["circuits"])
                    if not circuit["conditions"]
                ],
            ),
        )
    ]
    for circuit, result in pairs:
        condition = cast(Object, result["condition"])
        limit = cast(Object, result["limit"])
        declared = limit["declared"]
        rows = [
            ReportRow(
                label="Verfahren" if de else "Method",
                value=_label(condition["method"], locale),
            ),
            ReportRow(
                label="Strom / Bezugsspannung" if de else "Current / reference voltage",
                value=f"{_number(condition['current_a'])} A / {_number(condition['reference_voltage_v'])} V",
            ),
            ReportRow(
                label="Leitertemperatur / Frequenz"
                if de
                else "Conductor temperature / frequency",
                value=f"{_number(condition['conductor_temperature_c'])} °C / {_number(condition['frequency_hz'])} Hz",
            ),
            ReportRow(
                label="Stromrichtung" if de else "Current direction",
                value=_label(condition["direction"], locale),
            ),
            ReportRow(
                label="Leistungsfaktor / Blindanteil"
                if de
                else "Power factor / reactive direction",
                value=f"{_number(condition['power_factor'])} / {_label(condition['reactive_direction'], locale)}",
            ),
            ReportRow(
                label="Symmetrisch / sinusförmig" if de else "Balanced / sinusoidal",
                value=" / ".join(
                    ("Ja" if de else "Yes")
                    if v is True
                    else ("Nein" if de else "No")
                    if v is False
                    else "—"
                    for v in (condition["balanced"], condition["sinusoidal"])
                ),
            ),
            ReportRow(
                label="Leiteranordnung" if de else "Conductor arrangement",
                value=cast(str, condition["arrangement"]) or "—",
            ),
            ReportRow(
                label="Grundlage des Betriebsfalls"
                if de
                else "Operating-condition source",
                value=cast(str, condition["source_note"]),
            ),
            ReportRow(
                label="Summe der Leiterwerte R / X (Ω)"
                if de
                else "Sum of conductor R / X (Ω)",
                value=f"{_number(result['loop_resistance_ohm'])} / {_number(result['loop_reactance_ohm'])}",
            ),
            ReportRow(
                label="U Ende − Anfang (V)" if de else "U end − start (V)",
                value=_number(result["end_minus_start_voltage_v"]),
            ),
            ReportRow(
                label="Projektgrenzwert" if de else "Project limit",
                value=_label(limit["status"], locale),
            ),
        ]
        if limit.get("reason") is not None:
            rows.append(
                ReportRow(
                    label="Grenzwertbewertung" if de else "Limit assessment",
                    value=_label(limit["reason"], locale),
                )
            )
        if isinstance(declared, dict):
            rows.append(
                ReportRow(
                    label="Erfasster Grenzwert / Quelle"
                    if de
                    else "Recorded limit / source",
                    value=f"{_number(declared['maximum_percent'])}% · {declared['source_note']}",
                )
            )
        for segment in cast(list[Object], result["segments"]):
            source = cast(Object, segment["source"])
            rows.append(
                ReportRow(
                    label=f"{segment['run_id']} · {_label(segment['role'], locale)}",
                    value=f"{_number(segment['length_m'])} m · {_label(segment['resistance_basis'], locale)} · R {_number(segment['resistance_ohm'])} Ω · X {_number(segment['reactance_ohm'])} Ω · {'Seite' if de else 'page'} {source['page']} · {source['quote']}",
                    href=cast(str, source["url"]),
                )
            )
            rows.append(
                ReportRow(
                    label="Quellenrevision / Parametersatz"
                    if de
                    else "Source revision / parameter set",
                    value=f"{source['document_revision']} / {segment['parameter_set_id']}",
                )
            )
        sections.append(
            ReportSection(
                id=f"installation-electrical-{circuit['circuit_id']}-{result['condition_id']}",
                title=f"{circuit['name']} / {result['name']}",
                paragraphs=[
                    _label(reason, locale)
                    for reason in cast(list[str], result["reasons"])
                ],
                rows=rows,
            )
        )
    return sections
