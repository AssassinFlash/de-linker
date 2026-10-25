"""Build presentation only from the report's already frozen facts and results."""

from __future__ import annotations

from typing import Any, Literal, cast

from linker_engine.models import Report, ReportRow, ReportSection, ReportTable

from .canonical import Object
from .report_copy import check_label, text


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
        sections.append(
            ReportSection(
                id="equipment",
                title=text("equipment", locale),
                rows=[row("status", text(str(assessment["overall_status"]), locale))],
                paragraphs=[text("country_open", locale)],
            )
        )
        for index, check in enumerate(cast(list[dict[str, Any]], assessment["checks"])):
            unit = {
                "pv_dc_input": "kWp",
                "usable_energy": "kWh",
                "continuous_battery_ac_output": "kW",
            }.get(check["id"].split(":")[0], "")
            rows = [row("status", text(check["status"], locale))]
            if isinstance(check["actual"], (int, float)) and not isinstance(
                check["actual"], bool
            ):
                rows.append(row("actual", number(check["actual"], locale, unit)))
            if isinstance(check["required"], (int, float)) and not isinstance(
                check["required"], bool
            ):
                rows.append(row("required", number(check["required"], locale, unit)))
            paragraphs: list[str] = []
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
                cited = fact.get("source", {})
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
            sections.append(
                ReportSection(
                    id=f"check-{index}",
                    title=check_label(check["id"], locale),
                    rows=rows,
                    paragraphs=paragraphs,
                )
            )
        requirements = cast(
            list[dict[str, Any]], assessment.get("installation_requirements", [])
        )
        pair = assessment.get("manufacturer_pair")
        if isinstance(pair, dict):
            requirements = [*requirements, pair]
        conditions: list[str] = []
        documents: list[ReportRow] = []
        for requirement in requirements:
            conditions.extend(
                str(condition[locale])
                for condition in requirement.get("conditions", [])
                if condition.get(locale)
            )
            for doc in requirement.get("documents", []):
                label = text("source", locale) + (
                    f" · {text('page', locale)} {doc['page']}"
                    if doc.get("page")
                    else ""
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
        lines = cast(list[dict[str, Any]], assessment["provisional_bill_of_materials"])
        selected = {
            product["product_id"]: product
            for product in cast(list[dict[str, Any]], assessment["selected_products"])
        }

        def product_detail(line: dict[str, Any], field: str) -> str:
            value = line.get(field)
            if value is None:
                value = selected.get(line["product_id"], {}).get(field)
            return str(value) if value is not None else ""

        sections.append(
            ReportSection(
                id="bom",
                title=text("bom", locale),
                paragraphs=[text("bom_scope", locale)],
                table=ReportTable(
                    columns=[
                        text("quantity", locale),
                        text("product", locale),
                        text("reference", locale),
                    ],
                    rows=[
                        [
                            number(line.get("quantity"), locale),
                            f"{product_detail(line, 'brand')} {product_detail(line, 'model')}",
                            product_detail(line, "sku"),
                        ]
                        for line in lines
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
        energy_rows = [
            row(label, number(metrics.get(key), locale, "kWh"))
            for label, key in (
                ("load", "load_demand_kwh"),
                ("generation", "pv_generated_ac_kwh"),
                ("import", "grid_import_kwh"),
                ("export", "pv_export_kwh"),
                ("curtailed", "pv_curtailed_kwh"),
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
        sections.append(
            ReportSection(
                id="energy",
                title=text("energy", locale),
                paragraphs=[text("scenario_scope", locale)],
                rows=energy_rows,
            )
        )

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
