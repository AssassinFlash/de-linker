"""The design report: one model for the screen and the PDF.

Sections follow the ticket: site and inputs, yield (range), storage sizing,
self-sufficiency and self-consumption (ranges), selection basis (every rule
with the value it read), manufacturer releases with their documents, the
Stückliste, assumptions and limits, next steps. There is no payback, cash
flow or tariff anywhere (docs/specs/14-solution-configurator.md).
"""

from __future__ import annotations

from urllib.parse import unquote, urlsplit

from . import rules
from .models import Line, Report, ReportRow, ReportSection, ReportTable, RuleResult
from .residential import Design
from .texts import Locale, fmt, t, tn

# Rules whose value the report can state without a source; listed under assumptions.
UNVERIFIED = [
    rules.STRING_T_MIN_C,
    rules.STRING_T_CELL_MAX_C,
    rules.DC_CABLE_M_PER_STRING,
    rules.CONNECTOR_PAIRS_PER_STRING,
]


def _pct(value: float, locale: Locale) -> str:
    return f"{fmt(round(value * 100), locale)} %"


def _range(
    low: float, high: float, locale: Locale, unit: str = "", percent: bool = False
) -> str:
    if percent:
        return f"{_pct(low, locale)} – {_pct(high, locale)}"
    if round(low, 2) == round(high, 2):
        return f"{fmt(low, locale)} {unit}".strip()
    return f"{fmt(low, locale)} – {fmt(high, locale)} {unit}".strip()


def _file_name(url: str) -> str:
    """The document's file name, which is also its title in the product data."""
    return unquote(urlsplit(url).path.rsplit("/", 1)[-1]) or url


def _rule_row(rule: RuleResult, locale: Locale) -> ReportRow:
    state = (
        ""
        if rule.passed is None
        else t("row.passed" if rule.passed else "row.failed", locale)
    )
    return ReportRow(
        label=rule.label, value=f"{rule.text} · {state}" if state else rule.text
    )


def _quantity_text(line: Line, locale: Locale) -> str:
    """The quantity with its unit, in the grammatical number of the count: 1 pc, 22 pcs, 60 m."""
    return tn(f"unit.{line.unit}", line.quantity, locale, n=line.quantity)


def _bom_table(lines: list[Line], locale: Locale) -> ReportTable:
    rows = []
    for line in lines:
        quantity = _quantity_text(line, locale)
        model = f"{line.product.brand} {line.product.model}" if line.product else "–"
        scope = t("scope.ours" if line.product else "scope.installer", locale)
        rows.append([quantity, line.label, model, scope])
    return ReportTable(
        columns=[t(f"col.{c}", locale) for c in ("quantity", "item", "model", "scope")],
        rows=rows,
    )


def residential(design: Design, generated_at: str) -> Report:
    request = design.request
    locale = request.locale
    sections: list[ReportSection] = []

    site = [
        ReportRow(
            label=t("row.postcode", locale), value=f"{request.plz} {design.place.name}"
        ),
        ReportRow(
            label=t("row.position", locale),
            value=f"{fmt(design.yield_.latitude, locale, 3)}, {fmt(design.yield_.longitude, locale, 3)}",
        ),
        ReportRow(
            label=t("row.consumption", locale),
            value=f"{fmt(request.annual_kwh, locale)} kWh",
        ),
    ]
    if design.use.high_kwh != design.use.household_kwh:
        site.append(
            ReportRow(
                label=t("row.consumption_range", locale),
                value=_range(design.use.low_kwh, design.use.high_kwh, locale, "kWh"),
            )
        )
    site.append(
        ReportRow(
            label=t("row.array", locale), value=f"{fmt(request.pv_kwp, locale)} kWp"
        )
    )
    for index, plane in enumerate(design.yield_.planes, start=1):
        site.append(
            ReportRow(
                label=t("row.plane", locale, index=index),
                value=t(
                    "row.plane_value",
                    locale,
                    kwp=plane.kwp,
                    tilt=round(plane.tilt_deg),
                    azimuth=round(plane.azimuth_deg),
                ),
            )
        )
    site += [
        ReportRow(
            label=t("row.phase", locale),
            value=t("row.phase_value", locale, phase=request.phase),
        ),
        ReportRow(
            label=t("row.backup", locale), value=t(f"backup.{request.backup}", locale)
        ),
        ReportRow(
            label=t("row.heat_pump", locale),
            value=t("yes" if request.heat_pump else "no", locale),
        ),
        ReportRow(
            label=t("row.ev", locale),
            value=t("yes" if request.electric_vehicle else "no", locale),
        ),
    ]
    if request.existing_inverter:
        site.append(
            ReportRow(label=t("row.existing", locale), value=request.existing_inverter)
        )
    sections.append(ReportSection(id="site", title=t("report.site", locale), rows=site))

    y = design.yield_
    sections.append(
        ReportSection(
            id="yield",
            title=t("report.yield", locale),
            rows=[
                ReportRow(
                    label=t(
                        "row.yield_year",
                        locale,
                        first=str(y.years[0]),
                        last=str(y.years[1]),
                    ),
                    value=_range(
                        y.kwh_year_range.low, y.kwh_year_range.high, locale, "kWh"
                    ),
                ),
                ReportRow(
                    label=t("row.yield_mean", locale),
                    value=f"{fmt(y.kwh_year_mean, locale)} kWh",
                ),
                ReportRow(
                    label=t("row.yield_specific", locale),
                    value=_range(
                        y.kwh_per_kwp_range.low,
                        y.kwh_per_kwp_range.high,
                        locale,
                        "kWh/kWp",
                    ),
                ),
                ReportRow(label=t("row.yield_source", locale), value=y.source),
            ],
        )
    )

    sizing = design.sizing
    storage_rows = [_rule_row(rule, locale) for rule in design.sizing_rules]
    if sizing.recommended:
        storage_rows.append(
            ReportRow(
                label=t(
                    "row.storage_range_reserve"
                    if sizing.reserve_kwh
                    else "row.storage_range",
                    locale,
                ),
                value=_range(sizing.low_kwh, sizing.high_kwh, locale, "kWh"),
            )
        )
    if design.selected and design.selected.battery:
        battery = design.selected.battery
        storage_rows.append(
            ReportRow(
                label=t("row.storage_selected", locale),
                value=f"{fmt(battery.usable_kwh, locale)} kWh ({battery.quantity} × {battery.product.model})",
            )
        )
    sections.append(
        ReportSection(
            id="storage", title=t("report.storage", locale), rows=storage_rows
        )
    )

    if design.metrics:
        m = design.metrics
        sections.append(
            ReportSection(
                id="metrics",
                title=t("report.metrics", locale),
                rows=[
                    ReportRow(
                        label=t("row.autarky", locale),
                        value=_range(
                            m.autarky_range.low,
                            m.autarky_range.high,
                            locale,
                            percent=True,
                        ),
                    ),
                    ReportRow(
                        label=t("row.share", locale),
                        value=_range(
                            m.self_consumption_range.low,
                            m.self_consumption_range.high,
                            locale,
                            percent=True,
                        ),
                    ),
                    ReportRow(
                        label=t("row.autarky_without", locale),
                        value=_range(
                            m.without_storage_autarky_range.low,
                            m.without_storage_autarky_range.high,
                            locale,
                            percent=True,
                        ),
                    ),
                    ReportRow(
                        label=t("row.share_without", locale),
                        value=_range(
                            m.without_storage_self_consumption_range.low,
                            m.without_storage_self_consumption_range.high,
                            locale,
                            percent=True,
                        ),
                    ),
                    ReportRow(
                        label=t("row.metrics_basis", locale),
                        value=t("metrics.method", locale),
                    ),
                ],
            )
        )

    if design.selected:
        selected = design.selected
        basis_rows = [
            ReportRow(
                label=t("row.inverter", locale),
                value=f"{selected.inverter.brand} {selected.inverter.model}",
            )
        ]
        basis_rows += [_rule_row(rule, locale) for rule in selected.inverter_rules]
        s = selected.strings
        if s:
            total = sum(g.strings for g in s.groups)
            basis_rows.append(
                ReportRow(
                    label=t("row.strings", locale),
                    value=tn(
                        "row.strings_value",
                        total,
                        locale,
                        count=s.module_count,
                        wp=s.module_wp,
                        strings=total,
                        tmin=rules.STRING_T_MIN_C.value,
                        voc=s.voc_cold_v,
                    ),
                )
            )
        sections.append(
            ReportSection(
                id="basis",
                title=t("report.basis", locale),
                rows=basis_rows,
            )
        )
        release_rows: list[ReportRow] = []
        paragraphs: list[str] = []
        if selected.battery:
            battery = selected.battery
            release_rows.append(
                ReportRow(
                    label=f"{selected.inverter.model} + {battery.product.model}",
                    value=t(f"verdict.{battery.release.verdict}", locale),
                )
            )
            paragraphs += battery.release.conditions
            for document in battery.release.documents:
                page = (
                    f", {t('row.page', locale, page=document.page)}"
                    if document.page
                    else ""
                )
                release_rows.append(
                    ReportRow(
                        label=t("row.document", locale),
                        value=f"{_file_name(document.url)}{page}",
                        href=document.url,
                    )
                )
        sections.append(
            ReportSection(
                id="releases",
                title=t("report.releases", locale),
                rows=release_rows,
                paragraphs=paragraphs,
            )
        )
        sections.append(
            ReportSection(
                id="bom",
                title=t("report.bom", locale),
                table=_bom_table(selected.lines, locale),
            )
        )

    if design.warnings:
        sections.append(
            ReportSection(
                id="warnings",
                title=t("report.warnings", locale),
                paragraphs=design.warnings,
            )
        )

    assumptions = [
        t("limit.no_payback", locale),
        t("limit.reference_module", locale, model=_module_name(design)),
        t("limit.household", locale),
    ]
    if not request.planes:
        assumptions.append(t("limit.default_orientation", locale))
    assumptions += [
        f"{t(f'assume.{rule.id}', locale)} ({t('limit.unverified', locale)})"
        for rule in UNVERIFIED
    ]
    sections.append(
        ReportSection(
            id="assumptions",
            title=t("report.assumptions", locale),
            paragraphs=assumptions,
        )
    )
    sections.append(
        ReportSection(
            id="next",
            title=t("report.next", locale),
            paragraphs=[t("next.draft", locale), t("next.installer", locale)],
        )
    )
    return Report(
        title=t("report.title", locale),
        subtitle=t("report.subtitle", locale),
        generated_at=generated_at,
        locale=locale,
        sections=sections,
    )


def _module_name(design: Design) -> str:
    if design.selected and design.selected.strings:
        return design.selected.strings.module
    return ""
