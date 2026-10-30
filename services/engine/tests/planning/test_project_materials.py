"""Woo-maintained installation facts must remain sourced presentation data."""

from __future__ import annotations

import copy
import csv
import io
import math
from typing import cast

import pytest
from pypdf import PdfReader

from linker_engine import pdf
from linker_engine.planning.canonical import Object
from linker_engine.planning.equipment_facts import compile_product
from linker_engine.planning.project_materials import materials_csv, project_materials
from linker_engine.planning.report_model import build_report


def _source(page: int, quote: str) -> dict[str, object]:
    return {
        "document_id": "doc-installation",
        "document_revision": "a" * 64,
        "blob_sha256": "b" * 64,
        "product_id": 6506,
        "page": page,
        "url": "https://de-linker.com/wp-content/uploads/facts.pdf",
        "quote": quote,
    }


def _source_data() -> dict[str, object]:
    return {
        "project_id": "installation-facts",
        "revision": 1,
        "input_sha256": "0" * 64,
        "woo_bases": {"equipment": "fixture-publication"},
        "source_runs": [],
        "generated_at": "2026-10-30T00:00:00+00:00",
        "equipment": {
            "equipment_status": "unresolved",
            "overall_status": "unresolved",
            "checks": [],
            "selected_products": [
                {
                    "product_id": 6506,
                    "product_revision": "c" * 64,
                    "brand": "GoodWe",
                    "model": "GW75K-ET-G10",
                    "sku": "DLK-GOODWE-GW75KETG10",
                    "installation_facts": {
                        "status": "documented",
                        "items": [
                            {
                                "id": "pv-conductor",
                                "handling": "site_engineering_required",
                                "label": {
                                    "en": "PV terminal conductor",
                                    "de": "PV-Anschlussleiter",
                                },
                                "quantity": None,
                                "unit": "piece",
                                "basis": "manufacturer_recommended_conductor",
                                "specification": {
                                    "terminal_domain": "pv_dc",
                                    "terminals": ["PV1", "PV2"],
                                    "recommended_conductor_mm2": {
                                        "low": 4,
                                        "high": 6,
                                    },
                                    "cable_od_mm": {"low": 4.7, "high": 6.4},
                                },
                                "conditions": [],
                                "source": _source(
                                    12,
                                    "Recommended PV conductor 4-6 mm², OD 4.7-6.4 mm",
                                ),
                            },
                            {
                                "id": "pv-terminals",
                                "handling": "manufacturer_included",
                                "label": {
                                    "en": "PV terminals",
                                    "de": "PV-Anschlussklemmen",
                                },
                                "quantity": 16,
                                "unit": "piece",
                                "basis": "manufacturer_included_per_sales_unit",
                                "specification": {},
                                "conditions": [],
                                "source": _source(18, "PV terminals × 16"),
                            },
                            {
                                "id": "ac-breaker",
                                "handling": "customer_supplied_required",
                                "label": {
                                    "en": "AC circuit breaker",
                                    "de": "AC-Leitungsschutzschalter",
                                },
                                "quantity": None,
                                "unit": "piece",
                                "basis": "manufacturer_minimum_rating",
                                "specification": {
                                    "minimum_voltage_v": 400,
                                    "minimum_current_a": 160,
                                    "rating_note": "75/80 kW: 160 A × N",
                                },
                                "conditions": [
                                    {
                                        "en": "The model-specific current rule applies.",
                                        "de": "Die modellspezifische Stromregel gilt.",
                                    }
                                ],
                                "source": _source(23, "AC breaker ≥ 400 V, 160 A × N"),
                            },
                            {
                                "id": "optional-parallel-controller",
                                "handling": "manufacturer_included",
                                "label": {
                                    "en": "Parallel controller",
                                    "de": "Parallelsteuerung",
                                },
                                "quantity": 1,
                                "unit": "piece",
                                "basis": "manufacturer_included_conditional",
                                "specification": {},
                                "conditions": [
                                    {
                                        "en": "Optional parallel controller condition applies.",
                                        "de": "Die Bedingung für die optionale Parallelsteuerung gilt.",
                                    }
                                ],
                                "source": _source(
                                    31,
                                    "Optional parallel controller for parallel operation",
                                ),
                            },
                        ],
                    },
                }
            ],
            "provisional_bill_of_materials": [
                {
                    "product_id": 6506,
                    "quantity": 2,
                    "basis": "selected_converter",
                }
            ],
            "installation_requirements": [],
        },
    }


def test_installation_facts_become_distinct_sourced_material_rows() -> None:
    materials = project_materials(cast(Object, _source_data()))
    lines = materials["lines"]
    assert isinstance(lines, list)
    rows: dict[str, Object] = {}
    for raw in lines:
        assert isinstance(raw, dict)
        row = raw
        assert isinstance(row["id"], str)
        if row["id"].startswith("installation:"):
            assert isinstance(row["handling"], str)
            rows[row["handling"]] = row

    assert set(rows) == {
        "manufacturer_included",
        "customer_supplied_required",
        "site_engineering_required",
    }
    assert rows["manufacturer_included"]["quantity"] == 32
    assert rows["manufacturer_included"]["declared_quantity"] == 16
    assert rows["site_engineering_required"]["quantity"] is None
    assert rows["customer_supplied_required"]["quantity"] is None
    optional = next(
        row
        for row in rows.values()
        if str(row["id"]).endswith(":optional-parallel-controller")
    )
    assert optional["handling"] == "site_engineering_required"
    assert optional["quantity"] is None
    assert optional["declared_quantity"] == 1
    for handling, row in rows.items():
        source_value = row["source"]
        assert isinstance(source_value, dict)
        source = source_value
        assert source["authority"] == "woocommerce_product_meta"
        assert source["origin"] == "_linker_installation_facts"
        assert source["source"] == "linked_woo_document"
        assert source["document_id"] == "doc-installation"
        assert source["document_revision"] == "a" * 64
        assert source["blob_sha256"] == "b" * 64
        assert source["page"] in (12, 18, 23, 31)
        assert source["quote"] and handling


def test_compile_product_preserves_the_woo_typed_installation_projection() -> None:
    raw = {
        "id": 6506,
        "canonical_product_id": 6506,
        "product_revision": "c" * 64,
        "sku": "DLK-GOODWE-GW75KETG10",
        "model": "GW75K-ET-G10",
        "brand": "GoodWe",
        "device_class": "inverters",
        "figures": {},
        "documents": [],
        "installation_facts": {
            "status": "documented",
            "items": [],
        },
    }

    compiled = compile_product(raw)

    assert compiled["installation_facts"] == raw["installation_facts"]


def test_compile_product_omits_a_missing_installation_projection() -> None:
    raw = {
        "id": 4107,
        "canonical_product_id": 4107,
        "product_revision": "c" * 64,
        "sku": "existing-product",
        "model": "Existing product",
        "brand": "Fixture",
        "device_class": "inverters",
        "figures": {},
        "documents": [],
    }

    compiled = compile_product(raw)

    assert "installation_facts" not in compiled


@pytest.mark.parametrize(
    ("quantity", "unit", "declared_quantity"),
    ((2**53, "piece", 2**53), (1e308, "m", 1e308), (math.inf, "m", None)),
)
def test_installation_quantity_overflow_stays_unquantified(
    quantity: int | float, unit: str, declared_quantity: int | float | None
) -> None:
    source = cast(Object, copy.deepcopy(_source_data()))
    equipment = cast(Object, source["equipment"])
    products = cast(list[Object], equipment["selected_products"])
    installation = cast(Object, products[0]["installation_facts"])
    items = cast(list[Object], installation["items"])
    included = next(item for item in items if item["id"] == "pv-terminals")
    included["quantity"] = quantity
    included["unit"] = unit

    materials = project_materials(source)
    lines = cast(list[Object], materials["lines"])
    line = next(line for line in lines if str(line["id"]).endswith(":pv-terminals"))

    assert line["quantity"] is None
    assert line["declared_quantity"] == declared_quantity


def test_en_and_de_reports_and_csv_use_the_same_material_model() -> None:
    source = _source_data()
    materials = project_materials(cast(Object, source))
    source["materials"] = materials

    for (
        locale,
        conductor,
        customer,
        site,
        condition,
        package_source,
        installation_source,
        scope_fact,
    ) in (
        (
            "en",
            "PV terminal conductor",
            "Customer supplies after project-specific selection",
            "Site engineering assessment required",
            "Optional parallel controller condition applies.",
            "Manufacturer package contents",
            "Installation requirement source",
            "customer-supplied requirements and site-engineering obligations",
        ),
        (
            "de",
            "PV-Anschlussleiter",
            "Kundenseitige Bereitstellung nach projektspezifischer Auswahl",
            "Projektspezifische Planungsprüfung erforderlich",
            "Die Bedingung für die optionale Parallelsteuerung gilt.",
            "Herstellerseitiger Lieferumfang",
            "Quelle der Installationsanforderung",
            "kundenseitig bereitzustellende Anforderungen und projektseitig zu prüfende Pflichten",
        ),
    ):
        report_source = dict(source)
        report_source["locale"] = locale
        report_source["title"] = "Installation facts"
        report_source["project_id"] = "installation-facts"
        report_source["revision"] = 1
        report = build_report(cast(Object, report_source))
        bom = next(section for section in report.sections if section.id == "bom")
        source_labels = [row.value for row in bom.rows]
        assert source_labels.count(package_source) == 1
        assert source_labels.count(installation_source) == 3
        assert scope_fact in bom.paragraphs[0]

        document = pdf.render(report)
        text = "\n".join(
            page.extract_text() for page in PdfReader(io.BytesIO(document)).pages
        )
        flat = " ".join(text.split())
        assert conductor in flat and customer in flat and site in flat
        assert condition in flat
        assert "p. 12" in flat and "Recommended PV conductor" in flat
        assert (
            package_source in flat
            and installation_source in flat
            and scope_fact in flat
        )

        rows = list(
            csv.reader(
                io.StringIO(
                    materials_csv(materials, "0" * 64, locale).decode("utf-8-sig")
                )
            )
        )
        assert len(rows) == 6
        assert all(
            '"authority":"woocommerce_product_meta"' in row[6] for row in rows[2:]
        )
        assert any('"quote":"PV terminals × 16"' in row[6] for row in rows[2:])
        assert any(condition in row[6] for row in rows[2:])
