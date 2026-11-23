"""Build presentation only from the report's already frozen facts and results."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, cast

from linker_engine.models import (
    Report,
    ReportPhaseConflict,
    ReportRow,
    ReportSection,
    ReportTable,
)

from .canonical import Object
from .certificate_report import certificate_sections
from .comparison_report import comparison_sections
from .direct_beam_report import direct_beam_sections
from .geometric_pv_report import geometric_pv_sections
from .grid_connection_report import (
    grid_connection_sections,
    unfilled_grid_connection_sections,
)
from .installation_report import installation_sections
from .project_materials import (
    listed_materials,
    material_list,
    material_name,
    material_quantity,
    material_reference,
    material_scope,
    panel_description,
    project_materials,
)
from .pv_operating_report import operating_sections
from .report_capacity import capacity_section
from .report_copy import TEXT, check_label, text
from .report_numbers import comparison_values, percent
from .report_numbers import number as number
from .report_pv_components import pv_components_note
from .report_pvlib import pvlib_sections


def _material_table(
    lines: list[Object], section_id: str, title: str, locale: str
) -> ReportSection:
    material_documents: dict[tuple[str, int, str], ReportRow] = {}
    for line in lines:
        origin = line.get("source")
        citation = origin.get("document") if isinstance(origin, dict) else None
        if isinstance(citation, dict):
            url, page = cast(str, citation["url"]), cast(int, citation["page"])
            source_label = (
                "material_installation_source"
                if isinstance(origin, dict)
                and origin.get("origin") == "_linker_installation_facts"
                and line["handling"] != "manufacturer_included"
                else "material_package_source"
            )
            material_documents[(url, page, source_label)] = ReportRow(
                label=f"{text('source', locale)} · {text('page', locale)} {page}",
                value=text(source_label, locale),
                href=url,
            )
    if all(line.get("basis") == "manufacturer_one_end_mapping" for line in lines):
        scope_key = "terminal_material_scope"
    elif all(
        line["handling"] == "installation_requirement"
        and line.get("basis") != "manufacturer_one_end_mapping"
        for line in lines
    ):
        scope_key = "installation_scope"
    else:
        scope_key = "bom_scope"
    return ReportSection(
        id=section_id,
        title=title,
        paragraphs=[text(scope_key, locale)] if title == text("bom", locale) else [],
        rows=list(material_documents.values()),
        table=ReportTable(
            columns=[
                text("quantity", locale),
                text("product", locale),
                text("reference", locale),
                text("material_handling", locale),
            ],
            column_weights=[0.6, 1.7, 1, 1.7],
            rows=[
                [
                    material_quantity(line, locale),
                    material_name(line, locale),
                    material_reference(line),
                    material_scope(line, locale),
                ]
                for line in lines
            ],
        ),
    )


def _material_sections(lines: list[Object], locale: str) -> list[ReportSection]:
    if not lines:
        return []
    lines = listed_materials(lines)
    panel_types = ("pv_reference", "pv_declared")
    if not any(
        line["handling"] in panel_types or "package_supply" in line for line in lines
    ):
        return [_material_table(lines, "bom", text("bom", locale), locale)]
    sections = []
    for section_id, key in (
        ("bom", "equipment_list"),
        ("site-materials", "site_material_list"),
    ):
        group = [
            line for line in lines if material_list(line, locale) == text(key, locale)
        ]
        if group:
            sections.append(
                _material_table(group, section_id, text(key, locale), locale)
            )
    return sections


def _panel_schedule(
    sections: list[ReportSection], lines: list[Object], locale: str
) -> None:
    panels = [
        line for line in lines if line["handling"] in ("pv_reference", "pv_declared")
    ]
    if not panels:
        return
    design = next(
        (section for section in sections if section.id == "pv-components"), None
    )
    if design is None:
        design = ReportSection(
            id="pv-components", title=text("pv_components_title", locale)
        )
        sections.append(design)
    design.title = material_list(panels[0], locale)
    if design.table:
        design.table.columns[1] = text("panel_parameters", locale)
    else:
        design.paragraphs = (
            []
            if panels[0]["handling"] == "pv_declared"
            else [text("panel_design_only", locale)]
        )
        design.table = ReportTable(
            columns=[text("quantity", locale), text("panel_parameters", locale)],
            rows=[
                [
                    str(line["quantity"])
                    if line.get("quantity") is not None
                    else text("not_defined", locale),
                    material_name(line, locale),
                ]
                for line in panels
            ],
        )


def separate_panel_lists(report: Report, materials: Object) -> Report:
    """Reissue only material tables from their original frozen quantities and sources."""
    lines = cast(list[Object], materials.get("lines", []))
    if not any(line["handling"] in ("pv_reference", "pv_declared") for line in lines):
        return report
    sections = []
    for section in report.sections:
        if section.id == "bom":
            sections.extend(_material_sections(lines, report.locale))
        else:
            sections.append(section)
    _panel_schedule(sections, lines, report.locale)
    report.sections = sections
    return report


def build_report(source: Object) -> Report:
    locale = cast(Literal["en", "de"], source["locale"])
    sections: list[ReportSection] = []
    phase_conflicts: list[ReportPhaseConflict] = []

    def row(key: str, value: Any, href: str | None = None) -> ReportRow:
        return ReportRow(
            label=text(key, locale),
            value=str(value) if value is not None else "—",
            href=href,
        )

    def standby_voltage(value: float | None, interval: list[float]) -> str:
        if value is None:
            return number(None, locale, "V")
        shown = number(value, locale, "V")
        for bound in interval:
            distinct, _ = comparison_values(value, bound, locale, "V")
            if distinct != shown:
                if len(str(value).partition(".")[2]) > 8:
                    return ("< " if value < bound else "> ") + number(
                        bound, locale, "V"
                    )
                return distinct
        return shown

    sections.append(
        ReportSection(
            id="project",
            title=text("project", locale),
            paragraphs=[text("scope", locale)],
            rows=[
                row("project", source["title"]),
                row("project_id", source["project_id"]),
                row("revision", source["revision"]),
            ],
        )
    )
    brief = source.get("brief")
    brief_country_code: Any = None
    if isinstance(brief, dict):
        if direction := brief.get("system_scope"):
            sections[0].rows.append(
                row("planned_system", text(f"scope_{direction}", locale))
            )
        site = cast(Object, brief["site"])
        brief_country_code = site.get("country_code")
        # A row the visitor never declared is left out rather than printed as a
        # dash: "Time zone —" reads as a field the report failed to fill, and a
        # postcode does not establish a time zone on its own.
        site_rows = [
            row(label, value)
            for label, value in (
                ("location", site.get("location_label")),
                ("country", brief_country_code),
                ("timezone", site.get("timezone")),
                ("note", brief.get("project_note")),
            )
            if value
        ]
        if site_rows:
            sections.append(
                ReportSection(id="site", title=text("site", locale), rows=site_rows)
            )

    existing = source.get("existing_system")
    if isinstance(existing, dict):
        from .existing_system import retained_inverter_declared

        existing_rows = []
        if existing["name"]:
            existing_rows.append(row("existing_system", existing["name"]))
        if existing["inverter_power_kw"] is not None:
            existing_rows.append(
                row(
                    "existing_inverter_power",
                    number(existing["inverter_power_kw"], locale, "kW"),
                )
            )
        existing_paragraphs = [text("existing_system_declared", locale)]
        if existing["keep_inverter"]:
            existing_paragraphs.append(text("existing_inverter_keep", locale))
            if not retained_inverter_declared(source, selection=True):
                existing_paragraphs.append(text("existing_inverter_open", locale))
        sections.append(
            ReportSection(
                id="existing-system",
                title=text("existing_system", locale),
                paragraphs=existing_paragraphs,
                rows=existing_rows,
            )
        )

    retained = source.get("retained_inverter")
    if isinstance(retained, dict):

        def demand_rows(requirements: Object) -> list[ReportRow]:
            return [
                row(label, number(value, locale, unit))
                for label, field, unit in (
                    ("declared_pv_power", "pv_dc_kw", "kWp"),
                    ("declared_usable_storage", "required_usable_kwh", "kWh"),
                    ("declared_discharge_power", "required_discharge_ac_kw", "kW"),
                )
                if (value := requirements.get(field)) is not None
            ] + [
                row(label, value)
                for label, value in (
                    ("declared_grid_phase", requirements.get("grid_phase")),
                    (
                        "declared_operating_mode",
                        text(
                            "grid_connected"
                            if requirements.get("operating_mode") == "grid_connected"
                            else "declared_backup",
                            locale,
                        )
                        if requirements.get("operating_mode")
                        else None,
                    ),
                )
                if value is not None
            ]

        sections.append(
            ReportSection(
                id="declared-equipment-demand",
                title=text("declared_project_requirements", locale),
                rows=demand_rows(cast(Object, retained["requirements"])),
            )
        )
        for index, declared_unit in enumerate(
            cast(list[Object], retained.get("units", []))
        ):
            sections.append(
                ReportSection(
                    id=f"declared-equipment-demand-{index + 1}",
                    title=cast(str, declared_unit["name"]),
                    rows=demand_rows(cast(Object, declared_unit["requirements"])),
                )
            )

        profile = retained.get("profile_baseline")
        if isinstance(profile, dict):
            metrics = cast(Object, profile["baseline"])
            sections.append(
                ReportSection(
                    id="retained-energy-baseline",
                    title=text("retained_energy_baseline", locale),
                    rows=[
                        row(
                            "retained_profile_period",
                            f"{profile['horizon_start_utc']} – {profile['horizon_end_utc']}",
                        )
                    ]
                    + [
                        row(label, number(value, locale, unit))
                        for label, field, unit in (
                            ("retained_profile_load", "load_kwh", "kWh"),
                            ("retained_profile_direct_pv", "direct_pv_use_kwh", "kWh"),
                            ("retained_profile_import", "grid_import_kwh", "kWh"),
                            ("retained_profile_peak", "peak_grid_import_kw", "kW"),
                        )
                        if (value := metrics.get(field)) is not None
                    ],
                )
            )

    direct_beam = source.get("direct_beam")
    if isinstance(direct_beam, dict):
        sections.extend(direct_beam_sections(direct_beam, locale))
    geometric_pv = source.get("geometric_pv_references")
    if isinstance(geometric_pv, list):
        sections.extend(geometric_pv_sections(geometric_pv, locale))

    self_use = source.get("self_use_comparison")
    if isinstance(self_use, dict):
        baseline = cast(Object, self_use["baseline"])
        upper = self_use["upper_kwh"]
        rows = [
            row(
                "retained_profile_period",
                f"{self_use['horizon_start_utc']} – {self_use['horizon_end_utc']}",
            )
        ]
        rows.extend(
            row(label, number(value, locale, unit))
            for label, key, unit in (
                ("retained_profile_load", "load_kwh", "kWh"),
                ("generation", "pv_available_kwh", "kWh"),
                ("retained_profile_direct_pv", "direct_pv_use_kwh", "kWh"),
                ("retained_profile_import", "grid_import_kwh", "kWh"),
                ("export", "grid_export_kwh", "kWh"),
                ("retained_profile_peak", "peak_grid_import_kw", "kW"),
            )
            if (value := baseline[key]) is not None
        )
        if upper is not None:
            rows.append(row("self_use_upper", number(upper, locale, "kWh")))
        sections.append(
            ReportSection(
                id="self-consumption-comparison",
                title=text("self_use_comparison", locale),
                paragraphs=[text("self_use_bound_basis", locale)]
                if upper is not None
                else [],
                rows=rows,
            )
        )

    peak_comparison = source.get("peak_comparison")
    if isinstance(peak_comparison, dict):
        sections.append(
            ReportSection(
                id="peak-shaving-comparison",
                title=text("peak_comparison", locale),
                paragraphs=[text("peak_bound_basis", locale)]
                if peak_comparison["lower_bound_kw"] is not None
                else [],
                rows=[
                    row(
                        "peak_target",
                        f"{period['start_utc']} – {period['end_utc']}: "
                        + number(period["import_cap_kw"], locale, "kW"),
                    )
                    for period in cast(
                        list[Object], peak_comparison.get("target_periods", [])
                    )
                ]
                + [
                    row(label, number(value, locale, "kW"))
                    for label, field in (
                        ("peak_target", "target_kw"),
                        ("retained_profile_peak", "baseline_kw"),
                        ("peak_optimistic_bound", "lower_bound_kw"),
                    )
                    if (value := peak_comparison[field]) is not None
                ]
                + [
                    row(
                        "peak_result",
                        text(
                            "violated"
                            if peak_comparison["status"] == "violated"
                            else "unresolved",
                            locale,
                        ),
                    )
                ],
            )
        )

    assessment = source.get("equipment")
    if isinstance(assessment, dict):
        selected = {
            product["product_id"]: product
            for product in cast(list[dict[str, Any]], assessment["selected_products"])
        }
        pv_wiring = assessment.get("pv_electrical")
        string_numbers: dict[str, int] = {}
        if isinstance(pv_wiring, dict):
            plant_wiring = pv_wiring.get("method") == "woo_plant_layout_electrical_v1"
            wiring_units = cast(list[dict[str, Any]], pv_wiring.get("units", []))
            wiring_rows = (
                [
                    {
                        **string,
                        "unit_name": unit["unit_name"],
                        "inverter_instance_id": unit["inverter_instance_id"],
                    }
                    for unit in wiring_units
                    for string in unit["assessment"]["strings"]
                ]
                if plant_wiring
                else cast(list[dict[str, Any]], pv_wiring["strings"])
            )
            string_numbers = {s["id"]: i + 1 for i, s in enumerate(wiring_rows)}
            sections.append(
                ReportSection(
                    id="pv-strings",
                    title=text("pv_strings_title", locale),
                    paragraphs=[text("pv_strings_scope", locale)],
                    rows=(
                        [
                            ReportRow(
                                label=unit["unit_name"]
                                + " · "
                                + text("pv_min_ambient", locale),
                                value=number(
                                    unit["assessment"]["minimum_ambient_c"],
                                    locale,
                                    "°C",
                                )
                                + " · "
                                + str(unit["assessment"]["temperature_source"] or "—"),
                            )
                            for unit in wiring_units
                        ]
                        if plant_wiring
                        else [
                            row(
                                "pv_min_ambient",
                                number(
                                    pv_wiring.get("minimum_ambient_c"), locale, "°C"
                                ),
                            ),
                            row(
                                "pv_temperature_source",
                                pv_wiring.get("temperature_source"),
                            ),
                        ]
                    ),
                    table=ReportTable(
                        # At the native A4 width, the German inverter heading
                        # is 69.6 pt; equal columns leave only 54.2 pt of text.
                        column_weights=[1, 1.4, 0.8, 0.8, 1, 1, 1, 1]
                        if plant_wiring
                        else None,
                        columns=[
                            *(
                                [
                                    text("plant_unit", locale),
                                    text("pv_inverter_instance", locale),
                                ]
                                if plant_wiring
                                else []
                            ),
                            text("pv_string", locale),
                            "MPPT",
                            text("pv_input", locale),
                            text("pv_count", locale),
                            text("pv_stc_vmpp", locale),
                            text("pv_cold_voc", locale),
                        ],
                        rows=[
                            [
                                *(
                                    [
                                        s["unit_name"],
                                        s["inverter_instance_id"]
                                        or text("pv_instance_not_recorded", locale),
                                    ]
                                    if plant_wiring
                                    else []
                                ),
                                str(i + 1),
                                str(s["mppt"]),
                                str(s["input"]),
                                str(s["module_count"]),
                                number(s["stc_vmpp_v"], locale, "V"),
                                number(s["cold_voc_v"], locale, "V"),
                            ]
                            for i, s in enumerate(wiring_rows)
                        ],
                    ),
                )
            )
        if isinstance(pv_wiring, dict):
            standby_units = (
                [(u["unit_name"], u["assessment"]) for u in wiring_units]
                if plant_wiring
                else [(None, pv_wiring)]
            )
            for unit_index, (unit_name, unit_wiring) in enumerate(standby_units):
                standby_data = unit_wiring.get("standby")
                if not isinstance(standby_data, dict):
                    continue
                source_fact = cast(dict[str, Any], standby_data["fact"])
                standby_cited = cast(dict[str, Any], source_fact["source"])
                unit_rows = cast(list[dict[str, Any]], unit_wiring["strings"])
                numbers = {s["id"]: i + 1 for i, s in enumerate(unit_rows)}
                interval = cast(list[float], standby_data["interval_v"])

                sections.append(
                    ReportSection(
                        id=f"pv-standby-{unit_index}",
                        title=(f"{unit_name} · " if unit_name else "")
                        + text("pv_standby_title", locale),
                        paragraphs=[text("pv_standby_scope", locale)],
                        rows=[
                            row(
                                "pv_standby_title",
                                " – ".join(number(v, locale) for v in interval) + " V",
                            ),
                            ReportRow(
                                label=text("source", locale),
                                value=f"{text('page', locale)} {standby_cited['page']}",
                                href=standby_cited["url"],
                            ),
                        ],
                        table=ReportTable(
                            columns=[
                                text("pv_string", locale),
                                text("pv_standby_case", locale),
                                text("pv_standby_value", locale),
                                text("pv_standby_observation", locale),
                            ],
                            rows=[
                                [
                                    str(numbers[p["string_id"]]),
                                    text("pv_standby_case_" + p["case"], locale),
                                    standby_voltage(p["voltage_v"], interval),
                                    text("pv_standby_" + p["observation"], locale),
                                ]
                                for p in standby_data["points"]
                            ],
                        ),
                    )
                )
        if isinstance(pv_wiring, dict) and isinstance(pv_wiring.get("operating"), dict):
            sections.extend(
                operating_sections(
                    cast(Object, pv_wiring["operating"]), wiring_rows, locale
                )
            )
        if (
            isinstance(pv_wiring, dict)
            and pv_wiring.get("method") == "woo_plant_layout_electrical_v1"
        ):
            for unit in cast(list[dict[str, Any]], pv_wiring["units"]):
                unit_result = unit["assessment"]
                if isinstance(unit_result.get("operating"), dict):
                    for section in operating_sections(
                        unit_result["operating"], unit_result["strings"], locale
                    ):
                        sections.append(
                            section.model_copy(
                                update={
                                    "id": f"unit-{unit['unit_id']}-{section.id}",
                                    "title": f"{unit['unit_name']} · {section.title}",
                                }
                            )
                        )
        country_assessment_value = assessment.get("country_assessment")
        grid_sections = grid_connection_sections(country_assessment_value, locale)
        if not grid_sections:
            unfilled_country = (
                country_assessment_value.get("country_code")
                if isinstance(country_assessment_value, dict)
                else None
            ) or brief_country_code
            grid_sections = unfilled_grid_connection_sections(unfilled_country, locale)
        sections.append(
            ReportSection(
                id="equipment",
                title=text("equipment", locale),
                rows=[row("status", text(str(assessment["overall_status"]), locale))],
                paragraphs=([] if grid_sections else [text("country_open", locale)])
                + (
                    [text("plant_scope", locale)]
                    if assessment.get("model") == "woo_multi_converter_plant_v1"
                    else []
                ),
            )
        )
        sections.extend(grid_sections)
        for index, check in enumerate(cast(list[dict[str, Any]], assessment["checks"])):
            semantic_id = str(check.get("semantic_id", check["id"]))
            actual, required = check["actual"], check["required"]
            if (
                semantic_id == "grid_phase"
                and check["status"] == "violated"
                and type(actual) is int
                and actual in (1, 3)
                and type(required) is int
                and required in (1, 3)
                and actual != required
            ):
                phase_conflicts.append(
                    ReportPhaseConflict(
                        unit=check.get("unit_name"),
                        actual=cast(Literal[1, 3], actual),
                        required=cast(Literal[1, 3], required),
                    )
                )
            if isinstance(source.get("energy_equipment"), dict) and check["id"] in {
                "scenario_operating_mode",
                "scenario_parameter_basis",
                "scenario_model_domain",
            }:
                # These checks and their stated scope appear together in the
                # dedicated energy-equipment section below.
                continue
            unit = {
                "converter_identity": "kW",
                "pv_dc_input": "kWp",
                "usable_energy": "kWh",
                "continuous_battery_ac_output": "kW",
            }.get(semantic_id.split(":")[0], check.get("unit", ""))
            rows = [row("status", text(check["status"], locale))]
            if isinstance(check["actual"], (int, float)) and not isinstance(
                check["actual"], bool
            ):
                if (
                    semantic_id.split(":")[0] == "required_accessory"
                    or check.get("value_kind") == "product_identity"
                ):
                    product = selected.get(check["actual"], {})
                    name = " ".join(
                        str(product.get(key, "")) for key in ("brand", "model")
                    ).strip()
                    name = check.get("actual_label") or name
                    if name:
                        rows.append(row("actual", name))
                else:
                    rows.append(
                        row(
                            "controller_group_size"
                            if semantic_id == "plant_controller_network_count"
                            else "actual",
                            number(check["actual"], locale, unit),
                        )
                    )
            if isinstance(check["required"], (int, float)) and not isinstance(
                check["required"], bool
            ):
                if check.get("value_kind") == "product_identity":
                    if check.get("required_label"):
                        rows.append(row("required", check["required_label"]))
                else:
                    rows.append(
                        row(
                            "controller_network_max"
                            if semantic_id == "plant_controller_network_count"
                            else "required",
                            number(check["required"], locale, unit),
                        )
                    )
            elif isinstance(check["required"], list) and all(
                isinstance(n, (int, float)) and not isinstance(n, bool)
                for n in check["required"]
            ):
                rows.append(
                    row(
                        "required",
                        " – ".join(number(n, locale) for n in check["required"])
                        + (f" {unit}" if unit else ""),
                    )
                )
            if semantic_id == "plant_operating_mode":
                for field in ("actual", "required"):
                    if check.get(field) in ("grid_connected", "backup"):
                        rows.append(row(field, text(check[field], locale)))
            if semantic_id == "plant_controller_network_count":
                network = check.get("control_network")
                rows.append(
                    row(
                        "control_network",
                        str(network).upper()
                        if network
                        else text("not_specified", locale),
                    )
                )
            if semantic_id == "plant_operating_scope":
                network = check.get("control_network")
                rows.append(
                    row(
                        "actual",
                        text(check["actual"], locale)
                        + " · "
                        + (
                            str(network).upper()
                            if network
                            else text("not_specified", locale)
                        ),
                    )
                )
            plant_backup = check["id"] == "plant:backup_runtime"
            if plant_backup:
                for label, values, field, suffix_unit in (
                    ("plant_backup_load", check["required"], "load_kw", "kW"),
                    ("plant_backup_duration", check["required"], "duration_hours", "h"),
                    (
                        "plant_backup_load_energy",
                        check["required"],
                        "ac_load_energy_kwh",
                        "kWh",
                    ),
                    (
                        "plant_backup_power_ceiling",
                        check["actual"],
                        "discharge_upper_bound_kw",
                        "kW",
                    ),
                    (
                        "plant_backup_storage",
                        check["actual"],
                        "usable_energy_kwh",
                        "kWh",
                    ),
                ):
                    if (value := values.get(field)) is not None:
                        rows.append(row(label, number(value, locale, suffix_unit)))
            paragraphs: list[str] = (
                [text(check["reason"], locale)] if check["reason"] in TEXT else []
            )
            if plant_backup and check["status"] == "unresolved":
                paragraphs.append(text("plant_backup_open", locale))
            derivation = check.get("derivation")
            if isinstance(derivation, dict):
                factors = cast(list[float], derivation["factors"])
                paragraphs.append(
                    " × ".join(number(n, locale) for n in factors)
                    + " = "
                    + number(check["actual"], locale, str(derivation["unit"]))
                )
            seen: set[tuple[str, int | None]] = set()
            for fact in check["facts"]:
                cited = fact.get("source") or {}
                url = cited.get("url")
                page = cited.get("page")
                if isinstance(url, str) and (url, page) not in seen:
                    seen.add((url, page))
                    label = text("source", locale) + (
                        f" · {text('page', locale)} {page}" if page else ""
                    )
                    source_display_value = str(fact.get("raw_value", "—"))
                    if cited.get(
                        "figure_key"
                    ) == "sales_unit_kind" and source_display_value in {
                        "battery_module",
                        "battery_system",
                        "integrated_system",
                    }:
                        source_display_value = text(
                            "sales_" + source_display_value, locale
                        )
                    if cited.get("figure_key") == "max_lan_inverters":
                        source_display_value = "LAN · " + source_display_value
                    if fact.get("raw_unit") and fact.get("unit") != "count":
                        source_display_value += f" {fact['raw_unit']}"
                    rows.append(
                        ReportRow(
                            label=label,
                            value=source_display_value,
                            href=url,
                        )
                    )
            for doc in check.get("documents", []):
                if (
                    isinstance(doc.get("url"), str)
                    and (doc["url"], doc.get("page")) not in seen
                ):
                    rows.append(
                        ReportRow(
                            label=text("source", locale)
                            + (
                                f" · {text('page', locale)} {doc['page']}"
                                if doc.get("page")
                                else ""
                            ),
                            value=doc["url"],
                            href=doc["url"],
                        )
                    )
                    seen.add((doc["url"], doc.get("page")))
            check_title = (
                text("plant_backup_runtime", locale)
                if plant_backup
                else check_label(semantic_id, locale)
            )
            suffix = semantic_id.partition(":")[2]
            if suffix in string_numbers:
                check_title = f"{text('pv_string', locale)} {string_numbers[suffix]} · {check_title}"
            elif semantic_id.split(":")[0] in {
                "pv_stc_current",
                "pv_stc_isc",
                "pv_parallel_match",
                "pv_parallel_count",
                "pv_hot_current",
                "pv_cold_current",
                "pv_hot_isc",
                "pv_cold_isc",
            }:
                check_title = f"MPPT {suffix} · {check_title}"
            if isinstance(check.get("unit_name"), str):
                check_title = f"{check['unit_name']} · {check_title}"
            elif isinstance(check.get("group_name"), str):
                check_title = f"{text('plant_group', locale)} {check['group_name']} · {check_title}"
            sections.append(
                ReportSection(
                    id=f"check-controller-network-{index}"
                    if semantic_id == "plant_controller_network_count"
                    else "plant-backup-runtime"
                    if plant_backup
                    else f"check-{index}",
                    title=check_title,
                    rows=rows,
                    paragraphs=paragraphs,
                )
            )
        requirements = list(
            cast(list[dict[str, Any]], assessment.get("installation_requirements", []))
        )
        pair = assessment.get("manufacturer_pair")
        if isinstance(pair, dict):
            requirements = [*requirements, pair]
        for system in cast(list[dict[str, Any]], assessment.get("systems", [])):
            unit_pair = system.get("assessment", {}).get("manufacturer_pair")
            if isinstance(unit_pair, dict):
                requirements.append({**unit_pair, "unit_name": system["name"]})
        conditions: list[str] = []
        documents: list[ReportRow] = []
        for requirement in requirements:
            scope_name = requirement.get("unit_name", requirement.get("group_name"))
            scope_prefix = str(scope_name) + " · " if scope_name else ""
            conditions.extend(
                scope_prefix + str(condition[locale])
                for condition in requirement.get("conditions", [])
                if condition.get(locale)
            )
            for doc in requirement.get("documents", []):
                label = (
                    scope_prefix
                    + text("source", locale)
                    + (
                        f" · {text('page', locale)} {doc['page']}"
                        if doc.get("page")
                        else ""
                    )
                )
                documents.append(
                    ReportRow(label=label, value=doc["url"], href=doc["url"])
                )
        if conditions or documents:
            sections.append(
                ReportSection(
                    id="conditions",
                    title=text("conditions", locale),
                    paragraphs=list(dict.fromkeys(conditions)),
                    rows=list({(d.label, d.href): d for d in documents}.values()),
                )
            )
    sections.extend(installation_sections(source, locale))
    materials = source.get("materials")
    if not isinstance(materials, dict):
        materials = project_materials(source)
    lines = cast(list[Object], materials["lines"])
    sections.extend(_material_sections(lines, locale))

    pv_parts = source.get("pv_components")
    if isinstance(pv_parts, dict):
        part_rows: list[ReportRow] = []
        part_table: ReportTable | None = None
        if pv_parts["status"] == "available":
            components = cast(list[Object], pv_parts["components"])
            part_paragraphs = [
                text(
                    "pv_components_roof_scope"
                    if pv_parts["scope"] == "saved_roof"
                    else "pv_components_scope",
                    locale,
                )
            ]
            if pv_parts["scope"] == "dc_group":
                part_paragraphs.append(text("pv_components_dc_scope", locale))
            if pv_parts["layout_revision"] is not None:
                part_rows.append(row("revision", pv_parts["layout_revision"]))
            part_rows.append(
                row(
                    "pv_components_capacity",
                    number(pv_parts["nameplate_kwp"], locale, "kWp"),
                )
            )
            part_table = ReportTable(
                columns=[
                    text("quantity", locale),
                    text("model", locale),
                    text("pv_components_module_power", locale),
                ],
                rows=[
                    [
                        number(component["quantity"], locale),
                        panel_description(component, locale),
                        number(component["stc_power_w"], locale, "W"),
                    ]
                    for component in components
                ],
                column_weights=[1, 3, 2],
            )
        else:
            component_note = pv_components_note(pv_parts, locale)
            part_paragraphs = [component_note] if component_note is not None else []
        sections.append(
            ReportSection(
                id="pv-components",
                title=text("pv_components_title", locale),
                paragraphs=part_paragraphs,
                rows=part_rows,
                table=part_table,
            )
        )

    elif isinstance(brief_country_code, str) and brief_country_code:
        sections.extend(unfilled_grid_connection_sections(brief_country_code, locale))

    binding = source.get("energy_equipment")
    if isinstance(binding, dict) and "selection" in binding:
        linked = cast(Object, binding["assessment"])
        linked_checks = [
            check
            for check in cast(list[dict[str, Any]], linked["checks"])
            if check["id"]
            in {
                "usable_energy",
                "continuous_battery_ac_output",
                "continuous_battery_ac_charge",
                "scenario_operating_mode",
                "scenario_parameter_basis",
                "scenario_model_domain",
            }
            or check["status"] == "violated"
        ]
        bound_products = cast(list[Object], linked["selected_products"])
        selection = cast(Object, binding["selection"])
        linked_rows = [row("status", text(str(linked["overall_status"]), locale))]
        linked_rows.extend(
            row("model", " ".join(str(product[key]) for key in ("brand", "model")))
            for product in bound_products
        )
        linked_rows.extend(
            ReportRow(
                label=check_label(key, locale), value=number(selection[key], locale)
            )
            for key in ("modules_per_stack", "parallel_stacks")
        )
        paragraphs = [text("energy_equipment_scope", locale)]
        seen_facts: set[tuple[str, str, int]] = set()
        for check in linked_checks:
            derivation = check.get("derivation")
            if isinstance(derivation, dict):
                paragraphs.append(
                    " × ".join(number(n, locale) for n in derivation["factors"])
                    + " = "
                    + number(check["actual"], locale, str(derivation["unit"]))
                )
            for fact in check["facts"]:
                cited = fact.get("source")
                if not isinstance(cited, dict):
                    continue
                url, page = cited["url"], cited["page"]
                fact_key = (check["id"], url, page)
                if fact_key in seen_facts:
                    continue
                seen_facts.add(fact_key)
                linked_rows.append(
                    ReportRow(
                        label=f"{check_label(check['id'], locale)} · {text('source', locale)} · {text('page', locale)} {page}",
                        value=str(fact["raw_value"])
                        + (f" {fact['raw_unit']}" if fact.get("raw_unit") else ""),
                        href=url,
                    )
                )

        def linked_value(check: dict[str, Any], field: str) -> str:
            # Count, voltage and an accessory's product ID must not be printed
            # as kW when a decisive non-core failure is retained in this table.
            unit = {
                "usable_energy": "kWh",
                "continuous_battery_ac_output": "kW",
                "continuous_battery_ac_charge": "kW",
                "converter_identity": "kW",
                "pv_dc_input": "kWp",
            }.get(check["id"].split(":")[0], "")
            value = check[field]
            if check["id"].split(":")[0] == "required_accessory" and isinstance(
                value, int
            ):
                product = next(
                    (p for p in bound_products if p["product_id"] == value), None
                )
                return (
                    " ".join(str(product[key]) for key in ("brand", "model"))
                    if product
                    else "—"
                )
            return number(value, locale, unit)

        sections.append(
            ReportSection(
                id="energy-equipment",
                title=text("energy_equipment", locale),
                paragraphs=paragraphs,
                rows=linked_rows,
                table=ReportTable(
                    column_weights=[0.32, 0.36, 0.16, 0.16],
                    columns=[
                        text("check", locale),
                        text("status", locale),
                        text("actual", locale),
                        text("required", locale),
                    ],
                    rows=[
                        [
                            check_label(check["id"], locale),
                            text(check["status"], locale),
                            linked_value(check, "actual"),
                            linked_value(check, "required"),
                        ]
                        for check in linked_checks
                    ],
                ),
            )
        )

    pv = source.get("pv")
    if isinstance(pv, dict) and pv.get("kind") != "prepare_pvgis_roof_ac_reference_v1":
        profile = cast(Object, pv["profile_summary"])
        sections.append(
            ReportSection(
                id="pv",
                title=text("pv", locale),
                paragraphs=[text("pv_scope", locale)],
                rows=[
                    row("generation", number(profile["energy_kwh"], locale, "kWh")),
                    row("period", f"{profile['start_utc']} – {profile['end_utc']}"),
                    row("intervals", number(profile["interval_count"], locale)),
                ],
            )
        )
    sections.extend(pvlib_sections(source, locale))
    roof_references = source.get("pvgis_roof_ac_references")
    if isinstance(roof_references, list):
        for index, roof_reference in enumerate(cast(list[Object], roof_references)):
            parameters = cast(Object, roof_reference["parameters"])
            summary = cast(Object, roof_reference["profile_summary"])
            reference_rows = [
                row("pvgis_calendar_year", parameters["year"]),
                row("pvgis_radiation_database", parameters["radiation_database"]),
                row("pvgis_reference_technology", parameters["pv_technology"]),
                row(
                    "pvgis_mounting_type",
                    text("pvgis_mounting_" + str(parameters["mounting_place"]), locale),
                ),
                row(
                    "pvgis_system_loss",
                    percent(parameters["system_loss_percent"], locale),
                ),
                row(
                    "pvgis_terrain_horizon",
                    text(
                        "pvgis_horizon_included"
                        if parameters["use_terrain_horizon"]
                        else "pvgis_horizon_omitted",
                        locale,
                    ),
                ),
                *(
                    [row("pvgis_reference_note", parameters["source_note"])]
                    if isinstance(parameters.get("source_note"), str)
                    and str(parameters["source_note"]).strip()
                    else []
                ),
                row("pvgis_ac_energy", number(summary["energy_kwh"], locale, "kWh")),
                row("period", f"{summary['start_utc']} – {summary['end_utc']}"),
                row("intervals", number(summary["interval_count"], locale)),
            ]
            reference_uses = cast(list[Object], roof_reference["used_by"])
            reference_rows.extend(
                row(
                    "comparison_" + str(use["comparison_role"])
                    if "comparison_role" in use
                    else "pvgis_source_run",
                    f"{use['run_id']} / {use['revision']}",
                )
                for use in reference_uses
            )
            for array in cast(list[Object], roof_reference["arrays"]):
                native_source = cast(Object, array["source_document"])
                capture = cast(Object, native_source["capture"])
                reference_rows.append(
                    row(
                        "pvgis_array_source",
                        array["id"],
                        cast(str, capture["requested_url"]),
                    )
                )
            reference_table: ReportTable | None = None
            reference_paragraphs = [text("pvgis_roof_reference_scope", locale)]
            if any("comparison_role" in use for use in reference_uses) and isinstance(
                roof_reference.get("pv_components"), dict
            ):
                reference_parts = cast(Object, roof_reference["pv_components"])
                if "nameplate_kwp" in reference_parts:
                    components = cast(list[Object], reference_parts["components"])
                    reference_paragraphs.append(text("pv_components_scope", locale))
                    reference_rows.append(
                        row(
                            "pv_components_capacity",
                            number(reference_parts["nameplate_kwp"], locale, "kWp"),
                        )
                    )
                    reference_table = ReportTable(
                        columns=[
                            text(key, locale)
                            for key in (
                                "quantity",
                                "model",
                                "pv_components_module_power",
                            )
                        ],
                        rows=[
                            [
                                number(component["quantity"], locale),
                                panel_description(component, locale),
                                number(component["stc_power_w"], locale, "W"),
                            ]
                            for component in components
                        ],
                        column_weights=[1, 3, 2],
                    )
                else:
                    component_note = pv_components_note(reference_parts, locale)
                    if component_note is not None:
                        reference_paragraphs.append(component_note)
            sections.append(
                ReportSection(
                    id=f"pvgis-roof-reference-{index}",
                    title=text("pvgis_roof_reference", locale),
                    paragraphs=reference_paragraphs,
                    rows=reference_rows,
                    table=reference_table,
                )
            )
    known_references = source.get("pvgis_known_ac_references")
    if isinstance(known_references, list):
        for index, known_reference in enumerate(cast(list[Object], known_references)):
            parameters = cast(Object, known_reference["parameters"])
            site = cast(Object, known_reference["site"])
            summary = cast(Object, known_reference["profile_summary"])
            known_rows = [
                ReportRow(
                    label=text("pvgis_known_site", locale),
                    value=f"{site['latitude']}, {site['longitude']} · {site['location_label']}",
                ),
                row("pvgis_calendar_year", parameters["year"]),
                row("pvgis_radiation_database", parameters["radiation_database"]),
                row("pvgis_reference_technology", parameters["pv_technology"]),
                row(
                    "pvgis_mounting_type",
                    text("pvgis_mounting_" + str(parameters["mounting_place"]), locale),
                ),
                row(
                    "pvgis_system_loss",
                    percent(parameters["system_loss_percent"], locale),
                ),
                row(
                    "pvgis_terrain_horizon",
                    text(
                        "pvgis_horizon_included"
                        if parameters["use_terrain_horizon"]
                        else "pvgis_horizon_omitted",
                        locale,
                    ),
                ),
                row("pvgis_reference_note", parameters["source_note"]),
                row("pvgis_ac_energy", number(summary["energy_kwh"], locale, "kWh")),
                row("period", f"{summary['start_utc']} – {summary['end_utc']}"),
            ]
            known_rows.extend(
                row(
                    "comparison_" + str(use["comparison_role"])
                    if "comparison_role" in use
                    else "pvgis_source_run",
                    f"{use['run_id']} / {use['revision']}",
                )
                for use in cast(list[Object], known_reference["used_by"])
            )
            for array in cast(list[Object], known_reference["arrays"]):
                known_rows.extend(
                    [
                        row(
                            "pvgis_known_power",
                            number(array["peak_power_kwp"], locale, "kWp"),
                        ),
                        row("pvgis_known_tilt", number(array["tilt_deg"], locale, "°")),
                        row(
                            "pvgis_known_azimuth",
                            number(array["azimuth_north_clockwise_deg"], locale, "°"),
                        ),
                        row("pvgis_known_note", array["source_note"]),
                        row(
                            "pvgis_array_source",
                            array["id"],
                            str(
                                cast(
                                    Object,
                                    cast(Object, array["source_document"])["capture"],
                                )["requested_url"]
                            ),
                        ),
                    ]
                )
            sections.append(
                ReportSection(
                    id=f"pvgis-known-reference-{index}",
                    title=text("pvgis_known_title", locale),
                    paragraphs=[text("pvgis_known_scope", locale)],
                    rows=known_rows,
                )
            )
    energy = source.get("energy")
    if isinstance(energy, dict):
        metrics = cast(Object, energy["metrics"])
        dc = energy.get("kind") == "shared_dc_energy_replay_v1"
        joint_dc = energy.get("kind") == "plant_shared_dc_energy_replay_v1"
        joint = energy.get("kind") in {
            "plant_ac_energy_replay_v1",
            "plant_shared_dc_energy_replay_v1",
        }
        pv_only_plant = (
            joint and isinstance(brief, dict) and brief.get("system_scope") == "pv_only"
        )
        # The report resolves this scenario against the selected frozen run.
        # Display each actual segment, rather than suggesting an annual total
        # or merging different operating states. The label explicitly says UTC.
        scenario = source.get("energy_scenario")
        schedule = scenario.get("schedule") if isinstance(scenario, dict) else None
        energy_rows = (
            [
                row(
                    "period",
                    " – ".join(
                        datetime.fromisoformat(str(segment[key]))
                        .astimezone(UTC)
                        .isoformat()
                        for key in ("start_utc", "end_utc")
                    ),
                )
                for segment in cast(list[Object], schedule)
            ]
            if isinstance(schedule, list) and schedule
            else [row("period", None)]
        )
        storage_only = False
        if isinstance(scenario, dict) and not (dc or joint_dc):
            storage_only = scenario["pv_available_asset_id"] is None
            constant_aux = (
                scenario["aux_ac_asset_id"] is None
                and scenario.get("aux_ac_kw") is not None
            )
            # Keep legacy profile-based self-consumption reports unchanged.
            if (
                storage_only
                or constant_aux
                or scenario["controller"]
                in {
                    "peak_shaving_with_reserve_v1",
                    "proportional_peak_shaving_v1",
                }
            ):
                energy_rows.append(
                    row("energy_controller", text(str(scenario["controller"]), locale))
                )
            if storage_only:
                energy_rows.append(
                    row("energy_pv_source", text("energy_no_pv", locale))
                )
            if constant_aux:
                energy_rows.append(
                    row(
                        "energy_constant_aux",
                        number(scenario["aux_ac_kw"], locale, "kW"),
                    )
                )
        energy_rows.extend(
            [
                row(label, number(metrics.get(key), locale, "kWh"))
                for label, key in (
                    ("load", "load_demand_kwh"),
                    (
                        "plant_common_ac_generation"
                        if joint_dc
                        else "generation_dc"
                        if dc
                        else "generation",
                        "pv_generated_dc_kwh" if dc else "pv_generated_ac_kwh",
                    ),
                    ("import", "grid_import_kwh"),
                    ("export", "pv_export_ac_kwh" if dc else "pv_export_kwh"),
                    (
                        "curtailed_dc" if dc or joint_dc else "curtailed",
                        "pv_curtailed_dc_kwh" if dc or joint_dc else "pv_curtailed_kwh",
                    ),
                    ("unserved", "unserved_load_kwh"),
                )
            ]
        )
        if joint_dc:
            energy_rows.append(
                row(
                    "plant_dc_generation",
                    number(metrics["pv_generated_dc_kwh"], locale, "kWh"),
                )
            )
        for label, key in (
            ("autarky", "solar_autarky"),
            ("self_use", "pv_input_self_use"),
        ):
            ratio = cast(Object, metrics[key])
            value = ratio.get("value")
            energy_rows.append(
                row(
                    label,
                    percent(value * 100, locale)
                    if isinstance(value, (int, float))
                    else text("not_defined", locale),
                )
            )
        energy_rows.append(row("intervals", number(energy["interval_count"], locale)))
        temperature = None
        if dc:
            parameters = cast(Object, energy.get("prepared_dc_parameters", {}))
            temperature = cast(Object, parameters.get("loss_scenario", {})).get(
                "battery_temperature_c"
            )
            if temperature is not None:
                energy_rows.append(
                    row("dc_battery_temperature", number(temperature, locale, "°C"))
                )
        sections.append(
            ReportSection(
                id="energy",
                title=text("energy", locale),
                paragraphs=[
                    text(
                        "scenario_dc_plant_scope"
                        if joint_dc
                        else "scenario_pv_only_plant_scope"
                        if pv_only_plant
                        else "scenario_storage_plant_scope"
                        if joint and storage_only
                        else "scenario_plant_scope"
                        if joint
                        else "scenario_dc_scope"
                        if dc
                        else "scenario_scope",
                        locale,
                    )
                ]
                + (
                    [
                        text("plant_dc_stages", locale),
                        text("scenario_plant_limits", locale),
                    ]
                    if joint_dc
                    else [text("scenario_plant_limits", locale)]
                    if joint and (storage_only or pv_only_plant)
                    else []
                )
                + (
                    [text("dc_temperature_scope", locale)]
                    if temperature is not None
                    else []
                ),
                rows=energy_rows,
            )
        )
        if dc:
            reference = capacity_section(
                cast(Object, energy["prepared_dc_parameters"]),
                locale,
                number,
                identity="energy-capacity-reference",
            )
            if reference is not None:
                sections.append(reference)
        if joint:
            binding = cast(Object, energy.get("equipment_binding", {}))
            plant = cast(Object, binding.get("plant", {}))
            scenarios = {
                str(unit["unit_id"]): unit
                for unit in cast(
                    list[Object], cast(Object, source["energy_scenario"])["units"]
                )
            }
            parameter_sources = cast(Object, energy["parameter_sources"])
            parameter_pool = cast(Object, parameter_sources["pool"])
            names = {
                str(unit["id"]): str(unit["name"])
                for unit in cast(list[Object], plant.get("units", []))
            }
            for unit in cast(list[Object], metrics.get("units", [])):
                start = cast(Object, unit["stored_initial"])
                finish = cast(Object, unit["stored_final"])
                rows = [
                    row(
                        "plant_unit_window",
                        number(unit["usable_window_kwh"], locale, "kWh"),
                    ),
                    row(
                        "plant_unit_start",
                        number(
                            sum(
                                float(cast(float, start[k]))
                                for k in ("pv_kwh", "grid_kwh", "initial_unknown_kwh")
                            ),
                            locale,
                            "kWh",
                        ),
                    ),
                    row(
                        "plant_unit_finish",
                        number(
                            sum(
                                float(cast(float, finish[k]))
                                for k in ("pv_kwh", "grid_kwh", "initial_unknown_kwh")
                            ),
                            locale,
                            "kWh",
                        ),
                    ),
                ]
                for key in ("pv_kwh", "grid_kwh", "initial_unknown_kwh"):
                    rows.append(
                        row(
                            "plant_unit_finish_" + key,
                            number(finish[key], locale, "kWh"),
                        )
                    )
                condition = scenarios[str(unit["unit_id"])]
                if joint_dc:
                    rows.extend(
                        [
                            row(
                                "plant_dc_generation",
                                number(unit["pv_generated_dc_kwh"], locale, "kWh"),
                            ),
                            row(
                                "plant_pv_group",
                                str(condition["pv_converter_id"])
                                if condition["pv_converter_id"] is not None
                                else text("plant_pv_unused", locale),
                            ),
                            row(
                                "comparison_dc_auxiliary",
                                number(condition["aux_dc_kw"], locale, "kW"),
                            ),
                            row(
                                "plant_ac_charge_policy",
                                text(
                                    "plant_ac_charge_on"
                                    if condition["allow_ac_charge"]
                                    else "plant_ac_charge_off",
                                    locale,
                                ),
                            ),
                        ]
                    )
                rows.extend(
                    [
                        row(
                            "plant_unit_reserve",
                            number(condition["reserve_kwh"], locale, "kWh"),
                        ),
                        row(
                            "plant_unit_terminal",
                            number(condition["terminal_min_kwh"], locale, "kWh")
                            if condition["terminal_min_kwh"] is not None
                            else text("plant_no_terminal_minimum", locale),
                        ),
                    ]
                )
                sections.append(
                    ReportSection(
                        id="energy-unit-" + str(unit["unit_id"]),
                        title=names.get(str(unit["unit_id"]), str(unit["unit_id"])),
                        rows=rows,
                    )
                )
            for index, (sha, raw) in enumerate(parameter_pool.items()):
                proof = cast(Object, raw)
                losses = cast(Object, proof["loss_scenario"])
                assigned = [
                    names[str(u["unit_id"])]
                    for u in cast(list[Object], parameter_sources["units"])
                    if u["parameter_sha256"] == sha
                ]
                reference = capacity_section(
                    proof,
                    locale,
                    number,
                    identity="energy-capacity-reference-" + str(index),
                    unit_names=" · ".join(assigned),
                )
                if reference is not None:
                    sections.append(reference)
                rows = []
                for key in (
                    "eta_bus_to_battery",
                    "eta_battery_to_bus",
                    "eta_store_charge",
                    "eta_store_discharge",
                    "eta_inverter_forward",
                    "eta_inverter_reverse",
                    "internal_aux_kw",
                    "standing_loss_rate_per_hour",
                ):
                    value = losses[key]
                    efficiency = key.startswith("eta_")
                    rows.append(
                        row(
                            "plant_loss_" + key,
                            percent(float(cast(float, value)) * 100, locale)
                            if efficiency and value is not None
                            else number(
                                value,
                                locale,
                                "kW" if key == "internal_aux_kw" else "1/h",
                            ),
                        )
                    )
                unit_citations = {}
                for fact in cast(Object, proof["source_facts"]).values():
                    cited = fact.get("source") if isinstance(fact, dict) else None
                    if isinstance(cited, dict):
                        unit_citations[
                            (str(cited["url"]), int(cast(int, cited["page"])))
                        ] = cited
                for url, page in unit_citations:
                    rows.append(
                        ReportRow(
                            label=f"{text('source', locale)} · {text('page', locale)} {page}",
                            value=url,
                            href=url,
                        )
                    )
                sections.append(
                    ReportSection(
                        id="energy-parameters-" + str(index),
                        title=text("plant_parameter_sources", locale),
                        paragraphs=[" · ".join(assigned), str(losses["source_note"])],
                        rows=rows,
                    )
                )

    comparison = source.get("comparison")
    if isinstance(comparison, dict):
        sections.extend(comparison_sections(comparison, locale, number))

    references: list[ReportRow] = []
    references.extend(
        row("data_source", label)
        for label in cast(list[str], source.get("source_labels", []))
    )
    for item in cast(list[Object], source["source_runs"]):
        value = f"{item['run_id']} · {text('revision', locale)} {item['revision']}"
        if item.get("candidate_id"):
            value += f" · {item['candidate_id']}"
        references.append(row("run", value))
    if references:
        sections.append(
            ReportSection(id="basis", title=text("basis", locale), rows=references)
        )
    if isinstance(source.get("certificates"), dict):
        sections.extend(
            certificate_sections(
                cast(Object, source["certificates"]),
                locale,
                cast(Object | None, source.get("certificate_context")),
            )
        )
    report = Report(
        title=text("title", locale),
        subtitle=text("subtitle", locale),
        generated_at=str(source["generated_at"]),
        locale=locale,
        sections=sections,
        phase_conflicts=phase_conflicts,
    )
    _panel_schedule(report.sections, lines, locale)
    return report
