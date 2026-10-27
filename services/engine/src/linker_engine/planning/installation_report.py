"""Present the frozen routing calculation without granting installation approval."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection, ReportTable

from .canonical import Object
from .project_materials import material_quantity
from .report_copy import text


def installation_sections(source: Object, locale: str) -> list[ReportSection]:
    plan = source.get("installation")
    if not isinstance(plan, dict):
        return []
    devices = cast(list[Object], plan["instances"])
    cables = cast(list[Object], plan["cables"])
    return [
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
                ],
                column_weights=[1.3, 1.4, 0.8, 2],
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
                    ]
                    for cable in cables
                ],
            ),
        ),
    ]
