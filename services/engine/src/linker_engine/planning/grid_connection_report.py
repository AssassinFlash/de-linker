"""Present the grid connection evidence frozen in the selected equipment result."""

from typing import cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Json, Object
from .report_copy import text


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
    missing = cast(list[str], value["missing_inputs"])
    checks = ReportSection(
        id="grid-connection-evidence",
        title=text("grid_evidence", locale),
        paragraphs=[
            text(
                "grid_de_scope"
                if value.get("country_code") == "DE"
                else "grid_no_rule",
                locale,
            )
        ],
        rows=[
            ReportRow(
                label=text("grid_to_supply", locale),
                value=", ".join(text(f"grid_missing_{key}", locale) for key in missing)
                or text("grid_all_entered", locale),
            ),
            ReportRow(
                label=text("grid_territory_tab", locale),
                value=text("grid_unverified", locale),
            ),
            ReportRow(
                label=text("grid_permission", locale),
                value=text("grid_no_permission", locale),
            ),
        ],
    )
    for source in cast(list[Object], value["rule_sources"]):
        checks.rows.append(
            ReportRow(
                label=str(source["title"]),
                value=" · ".join(
                    str(item)
                    for item in (
                        source.get("edition"),
                        source["clause"],
                        f"{text('grid_source_read', locale)} {source['evidence_snapshot_date']}",
                        source["source_url"],
                    )
                    if item
                ),
            )
        )
    return [declarations, checks]
