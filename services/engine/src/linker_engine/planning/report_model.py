"""Build presentation only from the report's already frozen facts and results."""

from __future__ import annotations

from typing import Any, Literal, cast

from linker_engine.models import Report, ReportRow, ReportSection, ReportTable

from .canonical import Object
from .comparison_report import comparison_sections
from .installation_report import installation_sections
from .project_materials import (
    material_name,
    material_quantity,
    material_reference,
    material_scope,
    project_materials,
)
from .pv_operating_report import operating_sections
from .report_copy import TEXT, check_label, text


def number(value: Any, locale: str, unit: str = "") -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    # Report display resolution only; the immutable source retains full values.
    shown = f"{value:,.3f}".rstrip("0").rstrip(".")
    if locale == "de":
        shown = shown.translate(str.maketrans(",.", ".,"))
    return shown + (f" {unit}" if unit else "")


def build_report(source: Object) -> Report:
    locale = cast(Literal["en", "de"], source["locale"])
    sections: list[ReportSection] = []

    def row(key: str, value: Any, href: str | None = None) -> ReportRow:
        return ReportRow(
            label=text(key, locale),
            value=str(value) if value is not None else "—",
            href=href,
        )

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
    if isinstance(brief, dict):
        site = cast(Object, brief["site"])
        sections.append(
            ReportSection(
                id="site",
                title=text("site", locale),
                rows=[
                    row("location", site["location_label"]),
                    row("country", site["country_code"]),
                    row("timezone", site["timezone"]),
                    row("note", brief["project_note"]),
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
            wiring_rows = cast(list[dict[str, Any]], pv_wiring["strings"])
            string_numbers = {s["id"]: i + 1 for i, s in enumerate(wiring_rows)}
            sections.append(
                ReportSection(
                    id="pv-strings",
                    title=text("pv_strings_title", locale),
                    paragraphs=[text("pv_strings_scope", locale)],
                    rows=[
                        row(
                            "pv_min_ambient",
                            number(pv_wiring["minimum_ambient_c"], locale, "°C"),
                        ),
                        row("pv_temperature_source", pv_wiring["temperature_source"]),
                    ],
                    table=ReportTable(
                        columns=[
                            text("pv_string", locale),
                            "MPPT",
                            text("pv_input", locale),
                            text("pv_count", locale),
                            text("pv_stc_vmpp", locale),
                            text("pv_cold_voc", locale),
                        ],
                        rows=[
                            [
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
        if isinstance(pv_wiring, dict) and isinstance(pv_wiring.get("operating"), dict):
            sections.extend(
                operating_sections(
                    cast(Object, pv_wiring["operating"]), wiring_rows, locale
                )
            )
        sections.append(
            ReportSection(
                id="equipment",
                title=text("equipment", locale),
                rows=[row("status", text(str(assessment["overall_status"]), locale))],
                paragraphs=[text("country_open", locale)]
                + (
                    [text("plant_scope", locale)]
                    if assessment.get("model") == "woo_multi_converter_plant_v1"
                    else []
                ),
            )
        )
        for index, check in enumerate(cast(list[dict[str, Any]], assessment["checks"])):
            semantic_id = str(check.get("semantic_id", check["id"]))
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
                    rows.append(row("actual", number(check["actual"], locale, unit)))
            if isinstance(check["required"], (int, float)) and not isinstance(
                check["required"], bool
            ):
                if check.get("value_kind") == "product_identity":
                    if check.get("required_label"):
                        rows.append(row("required", check["required_label"]))
                else:
                    rows.append(
                        row("required", number(check["required"], locale, unit))
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
            paragraphs: list[str] = (
                [text(check["reason"], locale)] if check["reason"] in TEXT else []
            )
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
                    rows.append(
                        ReportRow(
                            label=label,
                            value=str(fact.get("raw_value", "—"))
                            + (f" {fact['raw_unit']}" if fact.get("raw_unit") else ""),
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
            check_title = check_label(semantic_id, locale)
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
                    id=f"check-{index}",
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
    if lines:
        material_documents: dict[tuple[str, int], ReportRow] = {}
        for line in lines:
            origin = line.get("source")
            citation = origin.get("document") if isinstance(origin, dict) else None
            if isinstance(citation, dict):
                url, page = cast(str, citation["url"]), cast(int, citation["page"])
                material_documents[(url, page)] = ReportRow(
                    label=f"{text('source', locale)} · {text('page', locale)} {page}",
                    value=text("material_package_source", locale),
                    href=url,
                )
        sections.append(
            ReportSection(
                id="bom",
                title=text("bom", locale),
                paragraphs=[
                    text(
                        "installation_scope"
                        if all(
                            line["handling"] == "installation_requirement"
                            for line in lines
                        )
                        else "bom_scope",
                        locale,
                    )
                ],
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
        )

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
            for component in components:
                citation = cast(Object, component["source"])
                part_rows.append(
                    ReportRow(
                        label=text("source", locale)
                        + f" · {text('page', locale)} {citation['page']}",
                        value=str(component["model"]),
                        href=cast(str, citation["url"]),
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
                        str(component["model"]),
                        number(component["stc_power_w"], locale, "W"),
                    ]
                    for component in components
                ],
                column_weights=[1, 3, 2],
            )
        else:
            part_paragraphs = [text("pv_components_" + str(pv_parts["reason"]), locale)]
        sections.append(
            ReportSection(
                id="pv-components",
                title=text("pv_components_title", locale),
                paragraphs=part_paragraphs,
                rows=part_rows,
                table=part_table,
            )
        )

    binding = source.get("energy_equipment")
    if isinstance(binding, dict):
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
    if isinstance(pv, dict):
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
    energy = source.get("energy")
    if isinstance(energy, dict):
        metrics = cast(Object, energy["metrics"])
        dc = energy.get("kind") == "shared_dc_energy_replay_v1"
        energy_rows = [
            row(label, number(metrics.get(key), locale, "kWh"))
            for label, key in (
                ("load", "load_demand_kwh"),
                (
                    "generation_dc" if dc else "generation",
                    "pv_generated_dc_kwh" if dc else "pv_generated_ac_kwh",
                ),
                ("import", "grid_import_kwh"),
                ("export", "pv_export_ac_kwh" if dc else "pv_export_kwh"),
                (
                    "curtailed_dc" if dc else "curtailed",
                    "pv_curtailed_dc_kwh" if dc else "pv_curtailed_kwh",
                ),
                ("unserved", "unserved_load_kwh"),
            )
        ]
        for label, key in (
            ("autarky", "solar_autarky"),
            ("self_use", "pv_input_self_use"),
        ):
            ratio = cast(Object, metrics[key])
            value = ratio.get("value")
            energy_rows.append(
                row(
                    label,
                    number(value * 100, locale, "%")
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
                    text("scenario_dc_scope" if dc else "scenario_scope", locale)
                ]
                + (
                    [text("dc_temperature_scope", locale)]
                    if temperature is not None
                    else []
                ),
                rows=energy_rows,
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
    return Report(
        title=text("title", locale),
        subtitle=text("subtitle", locale),
        generated_at=str(source["generated_at"]),
        locale=locale,
        sections=sections,
    )
