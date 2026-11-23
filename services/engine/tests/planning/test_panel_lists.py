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
