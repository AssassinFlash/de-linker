"""Render the same frozen comparison used by the interactive workbench."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from linker_engine.models import ReportRow, ReportSection, ReportTable

from .canonical import Object
from .report_copy import check_label, text


def comparison_sections(
    comparison: Object, locale: str, number: Callable[[Any, str, str], str]
) -> list[ReportSection]:
    def label(key: str) -> str:
        return text("comparison_" + key, locale)

    result: list[ReportSection] = [
        ReportSection(
            id="comparison",
            title=label("title"),
            paragraphs=[label("definition"), label("scope")]
            + ([] if comparison["conditions_aligned"] else [label("blocked")]),
        )
    ]
    for side in ("baseline", "candidate"):
        ref = cast(Object, comparison[side])
        rows = [
            ReportRow(label=text("revision", locale), value=str(ref["revision"])),
            ReportRow(label=text("run", locale), value=str(ref["run_id"])),
        ]
        rows.extend(
            ReportRow(label=text("model", locale), value=str(value))
            for value in cast(list[str], ref["equipment_models"])
        )
        rows.append(
            ReportRow(
                label=check_label("usable_energy", locale),
                value=number(ref["usable_window_kwh"], locale, "kWh"),
            )
        )
        for field in ("modules_per_stack", "parallel_stacks"):
            if ref[field] is not None:
                rows.append(
                    ReportRow(
                        label=check_label(field, locale),
                        value=number(ref[field], locale, ""),
                    )
                )
        site = ref.get("site")
        if isinstance(site, dict):
            rows.extend(
                ReportRow(
                    label=text(label_key, locale), value=str(site.get(field) or "—")
                )
                for label_key, field in (
                    ("location", "location_label"),
                    ("country", "country_code"),
                    ("timezone", "timezone"),
                )
            )
        for period in cast(list[Object], ref["operating_periods"]):
            rows.append(
                ReportRow(
                    label=label("periods") + " (UTC)",
                    value=str(period["start_utc"]) + " – " + str(period["end_utc"]),
                )
            )
        rows.append(
            ReportRow(
                label=label("starting_inventory"),
                value=number(ref["starting_energy_kwh"], locale, "kWh"),
            )
        )
        rows.append(
            ReportRow(
                label=label("terminal_requirement"),
                value=number(ref["terminal_min_kwh"], locale, "kWh")
                if ref["terminal_min_kwh"] is not None
                else label("no_minimum"),
            )
        )
        rows.append(
            ReportRow(
                label=label("scenario_constraints"),
                value=text(str(ref["scenario_constraint_status"]), locale),
            )
        )
        paragraphs = [str(ref["source_note"])] if ref.get("source_note") else []
        result.append(
            ReportSection(
                id="comparison-" + side,
                title=label(side),
                rows=rows,
                paragraphs=paragraphs,
            )
        )
    values: list[list[str]] = []
    for row in cast(list[Object], comparison["metrics"]):
        columns = [label(str(row["id"]))]
        for side in ("baseline", "candidate"):
            value = row[side]
            shown = number(
                cast(float, value) * 100
                if row["unit"] == "%" and value is not None
                else value,
                locale,
                str(row["unit"]),
            )
            if row["id"] in {"pv_generation", "pv_use"}:
                shown += f" ({str(row[side + '_boundary']).upper()})"
            columns.append(shown)
        columns.append(number(row["delta"], locale, str(row["delta_unit"])))
        values.append(columns)
    result.append(
        ReportSection(
            id="comparison-values",
            title=label("title"),
            table=ReportTable(
                columns=[
                    text("actual", locale),
                    label("baseline"),
                    label("candidate"),
                    label("difference"),
                ],
                rows=values,
                column_weights=[3.2, 2.4, 2.4, 1.5],
            ),
        )
    )
    result.append(
        ReportSection(
            id="comparison-basis",
            title=label("basis"),
            rows=[
                ReportRow(label=label(str(row["id"])), value=label(str(row["status"])))
                for row in cast(list[Object], comparison["conditions"])
            ],
        )
    )
    result.append(
        ReportSection(
            id="comparison-changes",
            title=label("changes"),
            rows=[
                ReportRow(
                    label=label(str(row["id"])),
                    value=label("changed" if row["changed"] else "unchanged"),
                )
                for row in cast(list[Object], comparison["differences"])
            ],
        )
    )
    return result
