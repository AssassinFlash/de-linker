import csv
import io

import pytest

from linker_engine.models import Report, ReportSection, ReportTable
from linker_engine.planning.canonical import Object
from linker_engine.planning.project_materials import (
    material_list,
    materials_csv,
    project_materials,
)
from linker_engine.planning.report_model import build_report, separate_panel_lists


@pytest.mark.parametrize("locale", ["en", "de"])
def test_project_panels_are_outside_the_offer_in_both_downloads(locale: str) -> None:
    rows = [["1", "Inverter", "INV", "Equipment"], ["4", "430 Wp", "", "Layout"]]
    report = Report(
        title="Project",
        subtitle="",
        generated_at="2026-11-01",
        locale=locale,
        sections=[
            ReportSection(
                id="bom",
                title="Materials",
                table=ReportTable(columns=["Qty", "Item", "Ref", "Scope"], rows=rows),
            ),
        ],
    )
    common: Object = {
        "quantity": 1,
        "unit": "piece",
        "source": {},
        "basis": "saved_layout",
    }
    sale: Object = {
        **common,
        "handling": "woo_product",
        "id": "item",
        "product_id": 1,
        "model": "Inverter",
        "sku": "INV",
    }
    panel: Object = {
        **common,
        "handling": "pv_reference",
        "id": "pv:roof",
        "quantity": 4,
        "model": "430 Wp",
        "product_id": None,
    }
    materials: Object = {"project_id": "project", "revision": 1, "lines": [sale, panel]}
    separated = separate_panel_lists(report, materials)
    grouped = {s.id: s.table.rows for s in separated.sections if s.table}
    assert grouped["bom"][0][1] == "Inverter"
    assert len(grouped["bom"]) == 1
    expected = (
        "Generic 430 W PV module (reference only — not supplied by Linker)"
        if locale == "en"
        else "Generisches 430-W-PV-Modul (nur Referenz — nicht im Lieferumfang von Linker)"
    )
    assert grouped["pv-components"] == [["4", expected]]
    export = list(
        csv.reader(
            io.StringIO(materials_csv(materials, "a" * 64, locale).decode("utf-8-sig"))
        )
    )
    assert expected in export[2]
    assert export[1][-1] == material_list(sale, locale)
    assert export[2][-1] == material_list(panel, locale) != export[1][-1]


@pytest.mark.parametrize(
    ("locale", "direction"),
    [("en", "Storage for existing PV"), ("de", "PV-Speicher nachrüsten")],
)
def test_direction_only_exports_the_selected_scope_without_equipment(
    locale: str, direction: str
) -> None:
    source: Object = {
        "locale": locale,
        "title": "Bonn",
        "project_id": "bonn",
        "revision": 2,
        "generated_at": "2026-11-23T00:00:00Z",
        "source_runs": [],
        "input_sha256": "a" * 64,
        "brief": {"site": {}, "system_scope": "storage_addition"},
    }
    report = build_report(source)
    assert direction in [
        row.value for section in report.sections for row in section.rows
    ]
    materials = project_materials(source)
    assert materials["lines"] == []
    csv_rows = list(
        csv.reader(
            io.StringIO(materials_csv(materials, "a" * 64, locale).decode("utf-8-sig"))
        )
    )
    assert csv_rows[1] == ["bonn", "2", direction]


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("with_bom", [True, False])
def test_reissue_replaces_existing_site_tables_once_from_the_frozen_materials(
    locale: str, with_bom: bool
) -> None:
    from typing import cast

    from .test_project_materials import _source_data

    raw = _source_data()
    raw["declared_pv_panels"] = {"count": 16, "stc_power_w": 500}
    materials = project_materials(cast(Object, raw))
    if not with_bom:
        materials["lines"] = [
            line
            for line in cast(list[Object], materials["lines"])
            if line["handling"]
            in (
                "site_engineering_required",
                "customer_supplied_required",
                "pv_declared",
            )
        ]
    archived = ReportSection(
        id="site-materials",
        title="Saved site materials",
        table=ReportTable(
            columns=["Quantity", "Item", "Reference"],
            rows=[["1", "Terminal", "p. 43 · B MPPT1 PV input"]],
        ),
    )
    sections = [ReportSection(id="project", title="Project")]
    if with_bom:
        sections.append(ReportSection(id="bom", title="Saved equipment"))
    sections.extend(
        [
            archived,
            ReportSection(id="site", title="Site"),
            ReportSection(
                id="material-evidence-1", tier="appendix", title="Old sources"
            ),
        ]
    )
    report = Report.model_validate(
        dict(
            locale=locale,
            title="Saved report",
            subtitle="",
            generated_at="2026-11-24",
            sections=sections,
        )
    )
    original = report.model_dump_json()
    csv_bytes = materials_csv(materials, "a" * 64, locale)
    updated = separate_panel_lists(report, materials)
    ids = [section.id for section in updated.sections]
    assert ids.count("bom") == int(with_bom)
    assert ids.count("site-materials") == ids.count("material-evidence-1") == 1
    assert ids.index("project") < ids.index("site-materials") < ids.index("site")
    assert "Old sources" not in str(updated.sections)
    site = next(s for s in updated.sections if s.id == "site-materials")
    assert site.table and any(
        row[2] == ("Seite 12" if locale == "de" else "Page 12")
        for row in site.table.rows
    )
    assert "B MPPT1" not in str(site)
    evidence = next(s for s in updated.sections if s.id == "material-evidence-1")
    assert "Recommended PV conductor 4-6 mm²" in str(evidence.rows)
    assert materials_csv(materials, "a" * 64, locale) == csv_bytes
    assert report.model_dump_json() == original
    assert separate_panel_lists(updated, materials) == updated
