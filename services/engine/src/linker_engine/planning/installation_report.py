"""Present the frozen routing calculation without granting installation approval."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection, ReportTable

from .canonical import Object
from .project_materials import conductor_specification, material_quantity
from .report_copy import text

# Reports created before the string-link closure existed keep their original
# rows. An absent closure is presented as not recorded: reading the old bundle
# must show what it actually saved instead of failing or inventing a closure.
HISTORICAL_CLOSURE: Object = {
    "conductor": "not_recorded",
    "quantity": "not_recorded",
    "recorded": False,
    "approval": "not_assessed",
}


def _saved_closure(row: Object) -> Object:
    closure = row.get("closure")
    return closure if isinstance(closure, dict) else HISTORICAL_CLOSURE


def _closure_label(closure: Object, locale: str) -> str:
    if closure["conductor"] == "not_recorded" and closure["quantity"] == "not_recorded":
        return text("installation_closure_not_recorded", locale)
    return text(
        "installation_closure_recorded"
        if closure["recorded"] is True
        else "installation_closure_open",
        locale,
    )


def installation_sections(source: Object, locale: str) -> list[ReportSection]:
    plan = source.get("installation")
    if not isinstance(plan, dict):
        return []
    devices = cast(list[Object], plan["instances"])
    cables = cast(list[Object], plan["cables"])
    sections = [
        ReportSection(
            id="installation-instances",
            title=text("installation_instances", locale),
            paragraphs=[text("installation_instance_scope", locale)],
            table=ReportTable(
                columns=[
                    text("installation_instance", locale),
                    text("product", locale),
                    text("installation_ports", locale),
                ],
                column_weights=[1, 1, 2],
                rows=[
                    [
                        cast(str, device["name"]),
                        f"{device['brand']} {device['model']}"
                        if device["product_id"] is not None
                        else text("installation_site_point", locale),
                        "; ".join(
                            cast(str, port["name"])
                            for port in cast(list[Object], device["ports"])
                        ),
                    ]
                    for device in devices
                ],
            ),
        ),
        ReportSection(
            id="installation-routing",
            title=text("installation", locale),
            paragraphs=[text("installation_scope", locale)],
            rows=[
                ReportRow(
                    label=f"{text('source', locale)} · {s['id']}",
                    value=cast(str, s["note"]),
                )
                for s in cast(list[Object], plan["sources"])
            ],
            table=ReportTable(
                columns=[
                    text("product", locale),
                    text("installation_circuit", locale),
                    text("quantity", locale),
                    text("installation_length", locale),
                    text("installation_conductor", locale),
                ],
                column_weights=[1.2, 1.2, 0.7, 1.7, 1.2],
                rows=[
                    [
                        cast(str, cable["name"]),
                        f"{cable['circuit_name']} / {cable['route_name']}",
                        material_quantity(cable, locale),
                        "; ".join(
                            text(f"installation_{reason}", locale)
                            for reason in cast(list[str], cable["reasons"])
                        )
                        or f"{material_quantity({'quantity': cable['route_length_m'], 'unit': 'm'}, locale)} + {material_quantity({'quantity': cable['extra_length_m'], 'unit': 'm'}, locale)} · {cable['extra_length_note']}",
                        conductor_specification(cable, locale),
                    ]
                    for cable in cables
                ],
            ),
        ),
    ]
    reconciliation = plan.get("pv_string_reconciliation")
    if isinstance(reconciliation, dict):
        reviewed = cast(list[Object], reconciliation["rows"])
        closures = [_saved_closure(row) for row in reviewed]
        paragraphs = [text("installation_string_link_scope", locale)]
        if reconciliation["plan_status"] != "available":
            paragraphs.append(
                text(
                    f"installation_string_plan_{reconciliation['plan_status']}", locale
                )
            )
        sections.append(
            ReportSection(
                id="installation-pv-string-links",
                title=text("installation_string_links", locale),
                paragraphs=paragraphs,
                rows=[
                    ReportRow(
                        label=text(label, locale),
                        value=str(count),
                    )
                    for label, count in (
                        (
                            "installation_string_linked_count",
                            sum(row["status"] == "linked" for row in reviewed),
                        ),
                        (
                            "installation_string_unresolved_count",
                            sum(row["status"] != "linked" for row in reviewed),
                        ),
                        (
                            "installation_string_cable_gaps",
                            sum(bool(row["reasons"]) for row in reviewed),
                        ),
                        (
                            "installation_string_recorded_count",
                            sum(closure["recorded"] is True for closure in closures),
                        ),
                        (
                            "installation_string_open_count",
                            sum(
                                closure["recorded"] is not True for closure in closures
                            ),
                        ),
                    )
                ]
                + [
                    ReportRow(
                        label=text(label, locale),
                        value=cast(str, reconciliation[key]) or "—",
                    )
                    for key, label in (
                        ("pv_string_plan_sha256", "installation_string_plan_hash"),
                        ("installation_input_sha256", "installation_input_hash"),
                        ("geometry_sha256", "installation_geometry_hash"),
                    )
                ],
                table=ReportTable(
                    columns=[
                        text("installation_string", locale),
                        text("installation_link_circuit", locale),
                        text("installation_ports", locale),
                        text("status", locale),
                        text("installation_link_cables", locale),
                        text("installation_conductor", locale),
                        text("installation_closure", locale),
                    ],
                    column_weights=[0.8, 0.8, 1.2, 1.1, 1.2, 0.9, 1.3],
                    rows=[
                        [
                            cast(str, row["string_id"]),
                            cast(str, row["circuit_id"]) or "—",
                            " → ".join(
                                f"{endpoint['instance_id']}/{endpoint['port_id']}"
                                for endpoint in cast(list[Object], row["endpoints"])
                            )
                            or "—",
                            text(f"installation_string_link_{row['status']}", locale),
                            "; ".join(
                                f"{cable['id']}: {material_quantity(cable, locale)}"
                                for cable in cast(list[Object], row["cable_runs"])
                            )
                            or text("installation_string_cable_runs_missing", locale),
                            text(
                                f"installation_conductor_{closure['conductor']}",
                                locale,
                            ),
                            _closure_label(closure, locale),
                        ]
                        for row, closure in zip(reviewed, closures, strict=True)
                    ],
                ),
            )
        )
    return sections
