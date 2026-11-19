import csv
import io

import pytest

from linker_engine.models import Report, ReportSection, ReportTable
from linker_engine.planning.canonical import Object
from linker_engine.planning.project_materials import material_list, materials_csv
from linker_engine.planning.report_model import separate_panel_lists


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
    common = {"quantity": 1, "unit": "piece", "source": {}, "basis": "saved_layout"}
    sale = {
        **common,
        "handling": "woo_product",
        "id": "item",
        "product_id": 1,
        "model": "Inverter",
        "sku": "INV",
    }
    panel = {
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
    assert grouped["pv-components"] == [["4", "430 Wp"]]
    export = list(
        csv.reader(
            io.StringIO(materials_csv(materials, "a" * 64, locale).decode("utf-8-sig"))
        )
    )
    assert export[1][-1] == material_list(sale, locale)
    assert export[2][-1] == material_list(panel, locale) != export[1][-1]
