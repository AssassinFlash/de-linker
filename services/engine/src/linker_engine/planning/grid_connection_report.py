"""Present the grid connection evidence frozen in the selected equipment result."""

import csv
import io
from typing import cast

from linker_engine.models import ReportRow, ReportSection

from . import eu_connection_rules as eu_rules
from .canonical import Json, Object
from .grid_connection import BUNDLED_RULE_COUNTRIES, bundled_country_sources
from .report_copy import (
    country_display,
    country_gap_paragraph,
    country_gap_summary,
    text,
)


def _rule_review(value: Json) -> Object | None:
    if not isinstance(value, dict) or not isinstance(value.get("rule_review"), dict):
        return None
    return cast(Object, value["rule_review"])


def _declared_boolean(value: Json, locale: str) -> str:
    return text(
        "country_rule_yes"
        if value is True
        else "country_rule_no"
        if value is False
        else "country_rule_unknown",
        locale,
    )


def _rule_number(value: Json, locale: str, unit: str) -> str:
    """Keep full input precision: rounding can put a value across a rule threshold."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    shown = str(value)
    return f"{shown.replace('.', ',') if locale == 'de' else shown} {unit}"


def _rule_missing(check: Object, locale: str) -> str:
    return ", ".join(
        text(f"country_rule_input_{key}", locale)
        for key in cast(list[str], check["missing_inputs"])
    )


def _rule_sections(review: Object, locale: str) -> list[ReportSection]:
    inputs = cast(Object, review["inputs"])
    rows = [
        ReportRow(label=text("country", locale), value=str(review["country_code"])),
        ReportRow(
            label=text("country_rule_date", locale),
            value=str(review["rule_date"] or "—"),
        ),
        ReportRow(
            label=text("country_rule_basis", locale),
            value=text(f"country_rule_{inputs['basis']}", locale),
        ),
        ReportRow(
            label=text("country_rule_power", locale),
            value=_rule_number(inputs["power_kw"], locale, "kW"),
        ),
    ]
    extra_fields = eu_rules.FIELDS.get(str(review["country_code"]), ())
    if extra_fields:
        rows.pop()  # The EU readings use the declared quantities for their own country.
        for key in extra_fields:
            amount = inputs.get(key)
            unit = eu_rules.UNITS.get(key)
            rows.append(
                ReportRow(
                    label=text("eu_rule_field_" + key, locale),
                    value=_rule_number(amount, locale, unit)
                    if unit
                    else _declared_boolean(amount, locale),
                )
            )
    if review["country_code"] == "FR":
        rows.extend(
            [
                ReportRow(
                    label=text("country_rule_voltage", locale),
                    value=_rule_number(inputs["connection_voltage_kv"], locale, "kV"),
                ),
                ReportRow(
                    label=text("country_rule_full_self_consumption", locale),
                    value=_declared_boolean(
                        inputs["fr_enedis_full_self_consumption"], locale
                    ),
                ),
            ]
        )
    if review["country_code"] == "DE":
        remuneration = inputs["de_remuneration"]
        rows.extend(
            [
                ReportRow(
                    label=text("country_rule_before_test", locale),
                    value=_declared_boolean(inputs["de_before_control_test"], locale),
                ),
                ReportRow(
                    label=text("country_rule_remuneration", locale),
                    value=text(f"country_rule_{remuneration}", locale)
                    if remuneration
                    else text("country_rule_unknown", locale),
                ),
                ReportRow(
                    label=text("country_rule_plug_in", locale),
                    value=_declared_boolean(inputs["de_plug_in_exception"], locale),
                ),
            ]
        )
    if review["country_code"] == "AT":
        rows.extend(
            [
                ReportRow(
                    label=text("country_rule_voltage", locale),
                    value=_rule_number(inputs["connection_voltage_kv"], locale, "kV"),
                ),
                ReportRow(
                    label=text("country_rule_input_apparent_power_kva", locale),
                    value=_rule_number(inputs["apparent_power_kva"], locale, "kVA"),
                ),
                ReportRow(
                    label=text("country_rule_input_net_active_power_kw", locale),
                    value=_rule_number(inputs["net_active_power_kw"], locale, "kW"),
                ),
                ReportRow(
                    label=text(
                        "country_rule_input_at_existing_installation_change", locale
                    ),
                    value=_declared_boolean(
                        inputs["at_existing_installation_change"], locale
                    ),
                ),
                ReportRow(
                    label=text(
                        "country_rule_input_at_change_previous_power_kw", locale
                    ),
                    value=_rule_number(
                        inputs["at_change_previous_power_kw"], locale, "kW"
                    ),
                ),
            ]
        )
    if review["country_code"] == "SE":
        rows.extend(
            [
                ReportRow(
                    label=text("country_rule_voltage", locale),
                    value=_rule_number(inputs["connection_voltage_kv"], locale, "kV"),
                ),
                ReportRow(
                    label=text("country_rule_input_se_export_power_kw", locale),
                    value=_rule_number(inputs["se_export_power_kw"], locale, "kW"),
                ),
                ReportRow(
                    label=text(
                        "country_rule_input_se_existing_installation_change", locale
                    ),
                    value=_declared_boolean(
                        inputs["se_existing_installation_change"], locale
                    ),
                ),
            ]
        )
    sections = [
        ReportSection(
            id="country-rule-review",
            title=text("country_rule_title", locale),
            paragraphs=[text("country_rule_scope", locale)],
            rows=rows,
        )
    ]
    sources = {
        str(source["id"]): source for source in cast(list[Object], review["sources"])
    }
    for check in cast(list[Object], review["checks"]):
        source = sources[str(check["source_id"])]
        detail = [
            ReportRow(
                label=text("status", locale),
                value=text(f"country_rule_{check['status']}", locale),
            ),
            ReportRow(
                label=text("country_rule_result", locale),
                value=text(f"country_rule_{check['outcome']}", locale),
            ),
        ]
        missing = _rule_missing(check, locale)
        if missing:
            detail.append(
                ReportRow(label=text("country_rule_missing", locale), value=missing)
            )
        detail.extend(
            [
                ReportRow(
                    label=text("country_rule_source", locale),
                    value=" · ".join(
                        str(item)
                        for item in (
                            source["title"],
                            source.get("edition"),
                            source["clause"],
                            source["source_url"],
                        )
                        if item
                    ),
                ),
                ReportRow(
                    label=text("country_rule_snapshot", locale),
                    value=str(source["evidence_snapshot_date"]),
                ),
                ReportRow(
                    label=text("country_rule_hash", locale),
                    value=str(source["text_sha256"]),
                ),
            ]
        )
        sections.append(
            ReportSection(
                id=f"country-rule-{check['id']}",
                title=text(f"country_rule_{check['id']}", locale),
                rows=detail,
            )
        )
    return sections


def country_rule_csv(
    value: Json, locale: str, source: Object, source_sha: str
) -> bytes | None:
    """Export only the saved rule review; project names and DSO declarations stay out."""
    review = _rule_review(value)
    if review is None:
        return None
    inputs = cast(Object, review["inputs"])
    sources = {str(item["id"]): item for item in cast(list[Object], review["sources"])}
    grid_sources = (
        cast(list[Object], value.get("rule_sources", []))
        if isinstance(value, dict)
        else []
    )
    grid_hashes = "; ".join(
        f"{item['id']}:{item['raw_sha256']}"
        for item in grid_sources
        if item.get("raw_sha256")
    )
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    # Human-readable headers retain stable IDs for downstream processing.
    columns = [
        ("project_id", "Project ID", "Projekt-ID"),
        ("revision", "Revision", "Revision"),
        ("input_sha256", "Input SHA-256", "SHA-256 der Eingaben"),
        ("report_source_sha256", "Report source SHA-256", "SHA-256 der Berichtsquelle"),
        ("locale", "Language", "Sprache"),
        ("country_code", "Country code", "Ländercode"),
        ("rule_date", "Rule date", "Regelungsdatum"),
        ("basis", "Power basis ID", "ID des Leistungsbezugs"),
        ("basis_label", "Power basis", "Leistungsbezug"),
        ("power_kw", "Declared power (kW)", "Angegebene Leistung (kW)"),
        (
            "connection_voltage_kv",
            "Connection-point voltage (kV)",
            "Spannung am Netzanschlusspunkt (kV)",
        ),
        (
            "de_before_control_test",
            "Meter and control-test stage",
            "Stand von Messsystem und Ansteuerungsprüfung",
        ),
        ("de_remuneration", "EEG remuneration ID", "ID der EEG-Vergütungsform"),
        ("de_remuneration_label", "EEG remuneration", "EEG-Vergütungsform"),
        (
            "de_plug_in_exception",
            "Complete plug-in solar exception",
            "Vollständige Steckersolar-Ausnahme",
        ),
        (
            "fr_enedis_full_self_consumption",
            "Full self-consumption without grid injection",
            "Vollständiger Eigenverbrauch ohne Netzeinspeisung",
        ),
        ("check_id", "Check ID", "Prüfungs-ID"),
        ("check_label", "Check", "Prüfung"),
        ("status", "Status ID", "Status-ID"),
        ("status_label", "Status", "Status"),
        ("scope", "Scope", "Geltungsbereich"),
        ("outcome", "Result ID", "Ergebnis-ID"),
        ("outcome_label", "Result", "Ergebnis"),
        ("missing_inputs", "Missing information IDs", "IDs fehlender Angaben"),
        ("missing_labels", "Missing information", "Fehlende Angaben"),
        ("source_id", "Source ID", "Quellen-ID"),
        ("source_title", "Source title", "Quellentitel"),
        ("source_url", "Source URL", "Quellen-URL"),
        ("source_edition", "Source edition", "Quellenausgabe"),
        ("source_clause", "Provision", "Vorschrift"),
        ("source_effective_from", "Effective from", "Gültig ab"),
        ("evidence_snapshot_date", "Source reviewed", "Quelle geprüft am"),
        ("source_text_sha256", "Source text SHA-256", "SHA-256 des Quellentextes"),
        (
            "grid_source_hashes",
            "Grid source text SHA-256",
            "SHA-256 der Netzanschlussquellen",
        ),
    ]
    country_fields = eu_rules.FIELDS.get(str(review["country_code"]), ())
    columns.extend(
        (key, text("eu_rule_field_" + key, "en"), text("eu_rule_field_" + key, "de"))
        for key in country_fields
        if key not in {"power_kw", "connection_voltage_kv"}
    )
    writer.writerow(
        f"{de if locale == 'de' else en} [{key}]" for key, en, de in columns
    )
    for check in cast(list[Object], review["checks"]):
        origin = sources[str(check["source_id"])]
        writer.writerow(
            [
                source["project_id"],
                source["revision"],
                source["input_sha256"],
                source_sha,
                locale,
                review["country_code"],
                review["rule_date"],
                inputs["basis"],
                text(f"country_rule_{inputs['basis']}", locale),
                inputs["power_kw"],
                inputs["connection_voltage_kv"],
                _declared_boolean(inputs["de_before_control_test"], locale)
                if inputs["de_before_control_test"] is not None
                else "",
                inputs["de_remuneration"],
                text(f"country_rule_{inputs['de_remuneration']}", locale)
                if inputs["de_remuneration"]
                else "",
                _declared_boolean(inputs["de_plug_in_exception"], locale)
                if inputs["de_plug_in_exception"] is not None
                else "",
                _declared_boolean(inputs["fr_enedis_full_self_consumption"], locale)
                if inputs["fr_enedis_full_self_consumption"] is not None
                else "",
                check["id"],
                text(f"country_rule_{check['id']}", locale),
                check["status"],
                text(f"country_rule_{check['status']}", locale),
                text("country_rule_scope", locale),
                check["outcome"],
                text(f"country_rule_{check['outcome']}", locale),
                ", ".join(cast(list[str], check["missing_inputs"])),
                _rule_missing(check, locale),
                origin["id"],
                origin["title"],
                origin["source_url"],
                origin.get("edition"),
                origin["clause"],
                origin.get("effective_from"),
                origin["evidence_snapshot_date"],
                origin["text_sha256"],
                grid_hashes,
                *[
                    inputs.get(key)
                    for key in country_fields
                    if key not in {"power_kw", "connection_voltage_kv"}
                ],
            ]
        )
    return output.getvalue().encode("utf-8-sig")


def grid_connection_sections(value: Json, locale: str) -> list[ReportSection]:
    if (
        not isinstance(value, dict)
        or value.get("model") != "declared_grid_connection_evidence_v1"
    ):
        return []

    facts = cast(Object, value["project_facts"])
    tab = cast(Object, facts["tab"])
    voltage = facts.get("voltage_level")
    entered = [
        ("grid_dso", facts.get("dso_name")),
        ("grid_dso_source", facts.get("dso_source_url")),
        ("grid_voltage", text(f"grid_{voltage}", locale) if voltage else None),
        ("grid_tab_title", tab.get("title")),
        ("grid_tab_source", tab.get("source_url")),
        ("grid_edition", tab.get("edition")),
        ("grid_tab_date", tab.get("date")),
    ]
    declarations = ReportSection(
        id="grid-connection-declarations",
        title=text("grid_declarations", locale),
        rows=[
            ReportRow(label=text(key, locale), value=str(raw))
            for key, raw in entered
            if raw
        ],
        paragraphs=[text("grid_declaration_basis", locale)],
    )

    def _source_row(source: Object) -> ReportRow:
        return ReportRow(
            label=str(source["title"]),
            value=" · ".join(
                str(item)
                for item in (
                    source.get("edition"),
                    source["clause"],
                    f"{text('grid_source_read', locale)} {source['evidence_snapshot_date']}",
                    source["source_url"],
                    source.get("raw_sha256") or source.get("text_sha256"),
                )
                if item
            ),
        )

    country_raw = value.get("country_code")
    country_code = (
        country_raw.upper() if isinstance(country_raw, str) and country_raw else None
    )
    is_bundled = country_code in BUNDLED_RULE_COUNTRIES
    review = _rule_review(value)
    missing = cast(list[str], value["missing_inputs"])
    missing_items = [text(f"grid_missing_{key}", locale) for key in missing]

    if country_code in BUNDLED_RULE_COUNTRIES:
        assert country_code is not None
        scope_paragraph = text(f"grid_bundled_scope_{country_code}", locale)
    else:
        scope_paragraph = country_gap_paragraph(country_code, locale)

    evidence_rows: list[ReportRow] = [
        ReportRow(
            label=text("grid_to_supply", locale),
            value=", ".join(missing_items) or text("grid_all_entered", locale),
        ),
        ReportRow(
            label=text("grid_territory_tab", locale),
            value=text("grid_unverified", locale),
        ),
        ReportRow(
            label=text("grid_permission", locale),
            value=text("grid_no_permission", locale),
        ),
        ReportRow(
            label=text("country", locale),
            value=country_display(country_code, locale),
        ),
        ReportRow(
            label=text("grid_rule_pack_status", locale),
            value=country_gap_summary(country_code, locale),
        ),
    ]
    checks = ReportSection(
        id="grid-connection-evidence",
        title=text("grid_evidence", locale),
        paragraphs=[scope_paragraph],
        rows=evidence_rows,
    )
    recorded_sources = cast(list[Object], value["rule_sources"])
    recorded_ids = {str(source["id"]) for source in recorded_sources}
    for source in recorded_sources:
        checks.rows.append(_source_row(source))
    if is_bundled and review is None:
        for source in bundled_country_sources(country_code):
            if str(source["id"]) not in recorded_ids:
                checks.rows.append(_source_row(source))
    return [declarations, checks] + (_rule_sections(review, locale) if review else [])


def unfilled_grid_connection_sections(
    country_code: Json, locale: str
) -> list[ReportSection]:
    code = (
        country_code.upper() if isinstance(country_code, str) and country_code else None
    )
    is_bundled = code in BUNDLED_RULE_COUNTRIES
    if is_bundled:
        assert code is not None
        paragraph = text(
            f"grid_bundled_scope_{code}"
            if code in eu_rules.CHECKS
            else f"grid_bundled_unfilled_{code}",
            locale,
        )
    else:
        paragraph = country_gap_paragraph(code, locale)

    missing_keys = [
        "dso_name",
        "dso_source_url",
        "voltage_level",
        "tab.source_url",
        "tab.edition_or_date",
    ]
    if code is None:
        missing_keys.insert(0, "country_code")
    missing_items = [text(f"grid_missing_{key}", locale) for key in missing_keys]
    if is_bundled:
        missing_items.append(text("grid_missing_country_rule_inputs", locale))

    rows: list[ReportRow] = [
        ReportRow(
            label=text("country", locale),
            value=country_display(code, locale),
        ),
        ReportRow(
            label=text("grid_rule_pack_status", locale),
            value=country_gap_summary(code, locale),
        ),
        ReportRow(
            label=text("grid_to_supply", locale),
            value=", ".join(missing_items),
        ),
        ReportRow(
            label=text("grid_territory_tab", locale),
            value=text("grid_unverified", locale),
        ),
        ReportRow(
            label=text("grid_permission", locale),
            value=text("grid_no_permission", locale),
        ),
    ]
    if is_bundled:
        for source in bundled_country_sources(code):
            rows.append(
                ReportRow(
                    label=str(source["title"]),
                    value=" · ".join(
                        str(item)
                        for item in (
                            source.get("edition"),
                            source["clause"],
                            f"{text('grid_source_read', locale)} {source['evidence_snapshot_date']}",
                            source["source_url"],
                            source.get("raw_sha256") or source.get("text_sha256"),
                        )
                        if item
                    ),
                )
            )
    return [
        ReportSection(
            id="grid-connection-evidence",
            title=text("grid_evidence", locale),
            paragraphs=[paragraph],
            rows=rows,
        )
    ]
