"""Woo-maintained installation facts must remain sourced presentation data."""

from __future__ import annotations

import copy
import csv
import io
import json
import math
from pathlib import Path
from typing import Any, cast

import pytest
from pypdf import PdfReader

from linker_engine import pdf
from linker_engine.planning.canonical import Object
from linker_engine.planning.equipment_facts import compile_product
from linker_engine.planning.handoffs import HandoffIncomplete, purchase_items
from linker_engine.planning.project_materials import (
    material_quantity,
    material_scope,
    materials_csv,
    project_materials,
)
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


def test_batc_delivery_plan_multiplies_only_unconditional_contents() -> None:
    path = Path(__file__).resolve().parents[4] / "tools/migrate/548-batc-delivery.json"
    products = json.loads(path.read_text())["products"]
    source = _source_data()
    equipment = cast(dict[str, object], source["equipment"])
    selected = []
    bom = []
    for pid, quantity in ((1956, 2), (1957, 1), (1958, 3)):
        product = products[str(pid)]
        selected.append(
            {
                "product_id": pid,
                "product_revision": product["product_revision"],
                "brand": "GoodWe",
                "model": product["model"],
                "installation_facts": {
                    "status": "documented",
                    "items": product["items"],
                },
            }
        )
        bom.append(
            {"product_id": pid, "quantity": quantity, "basis": "selected_battery"}
        )
    equipment["selected_products"] = selected
    equipment["provisional_bill_of_materials"] = bom
    materials = project_materials(cast(Object, source))
    lines = cast(list[Object], materials["lines"])
    for pid, quantity in ((1956, 2), (1957, 1), (1958, 3)):
        own = [row for row in lines if row.get("parent_product_id") == pid]

        facts = {str(row["id"]).rsplit(":", 1)[-1]: row for row in own}

        assert len(own) == 27
        assert facts["expansion-bolt"]["quantity"] == 4 * quantity
        assert facts["m8-screw"]["quantity"] == 12 * quantity
        assert facts["cable-tie"]["quantity"] == 20 * quantity
        assert facts["liquid-cooling-drain-pipe"]["quantity"] == quantity
        assert facts["power-cable-et"]["handling"] == "site_engineering_required"
        assert facts["power-cable-et"]["quantity"] is None
        assert facts["power-cable-et"]["declared_quantity"] == 2
        assert (
            len([row for row in own if str(row["id"]).endswith(":expansion-bolt")]) == 1
        )
    for locale, name in (("en", "Expansion bolt"), ("de", "Spreizdübel")):
        output = materials_csv(materials, "a" * 64, locale).decode("utf-8-sig")
        assert name in output and "GW208.9-BAT-LC-G10" in output
        assert "GW_BAT-C-208-261kWh_User-Manual-EN.pdf" in output
        source["materials"] = materials
        source["locale"] = locale
        source["title"] = "BAT-C delivery"
        report = build_report(cast(Object, source))
        document = pdf.render(report)
        content = " ".join(
            " ".join(page.extract_text().split())
            for page in PdfReader(io.BytesIO(document)).pages
        )
        assert name in content and "GW208.9-BAT-LC-G10" in content
        assert (
            "Page 35" if locale == "en" else "Seite 35"
        ) in content and "8" in content


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
        assert (
            "Page 12" if locale == "en" else "Seite 12"
        ) in flat and "Recommended PV conductor" in flat
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


def test_retained_equipment_stays_listed_and_leaves_procurement() -> None:
    source = copy.deepcopy(_source_data())
    equipment = cast(Object, source["equipment"])
    products = cast(list[Object], equipment["selected_products"])
    converter = products[0]
    converter["package_contents"] = cast(
        Object,
        {
            "status": "documented",
            "items": [
                {
                    "id": "smart-meter",
                    "label": {"en": "Smart meter", "de": "Smart Meter"},
                    "quantity": 1,
                    "unit": "piece",
                    "role": "meter",
                    "source": _source(40, "Smart meter × 1"),
                }
            ],
        },
    )
    equipment["selected_products"] = [
        converter,
        {
            "product_id": 7001,
            "product_revision": "d" * 64,
            "brand": "GoodWe",
            "model": "BAT-C",
            "sku": "DLK-GOODWE-BATC",
        },
        {
            "product_id": 9001,
            "product_revision": "e" * 64,
            "brand": "GoodWe",
            "model": "Backup Box",
            "sku": "DLK-GOODWE-BACKUP",
        },
    ]
    equipment["provisional_bill_of_materials"] = [
        {"product_id": 6506, "quantity": 2, "basis": "selected_converter"},
        {"product_id": 7001, "quantity": 2, "basis": "selected_battery"},
        {"product_id": 9001, "quantity": 1, "basis": "manufacturer_required_backup"},
    ]
    equipment["installation_requirements"] = [
        {"included": True, "kind": "meter", "documents": []}
    ]
    source["equipment_selection"] = {
        "inverter_product_id": 6506,
        "battery_product_id": 7001,
        "accessory_product_ids": [9001],
        "equipment_use": {"inverter": "retain", "battery": "replace"},
    }

    materials = project_materials(cast(Object, source))
    lines = cast(list[Object], materials["lines"])
    product_rows = [row for row in lines if row["handling"] == "woo_product"]

    assert [row["product_id"] for row in product_rows] == [6506, 7001, 9001]
    retained = product_rows[0]
    assert retained["quantity"] == 2
    assert retained["retained_quantity"] == 2
    battery = next(row for row in product_rows if row["product_id"] == 7001)
    assert battery["quantity"] == 2
    assert "retained_quantity" not in battery
    assert battery["replacement_quantity"] == 2
    for locale, replacement_scope in (
        ("en", "Selected equipment · purchase 2 as replacements"),
        ("de", "Ausgewählte Geräte · 2 als Ersatz beschaffen"),
    ):
        assert material_scope(battery, locale) == replacement_scope
        assert replacement_scope in materials_csv(materials, "0" * 64, locale).decode(
            "utf-8-sig"
        )
    # The complete system list keeps the retained converter's documented
    # package contents, while its inclusion still covers the generic row.
    package = [row for row in lines if str(row["id"]).startswith("package:6506")]
    assert [row["quantity"] for row in package] == [2]
    for locale, name, group in (
        ("en", "Smart meter", "Site and installation materials"),
        ("de", "Smart Meter", "Materialien für Standort und Montage"),
    ):
        exported = list(
            csv.reader(
                io.StringIO(
                    materials_csv(materials, "0" * 64, locale).decode("utf-8-sig")
                )
            )
        )
        assert [(row[2], row[-1]) for row in exported if row[3] == name] == [
            ("2", group)
        ]

    assert not [row for row in lines if str(row["id"]).startswith("included:")]
    for locale, scope in (
        ("en", "Existing device · retained on site, not purchased"),
        ("de", "Vorhandenes Gerät · bleibt am Standort, keine Beschaffung"),
    ):
        assert material_scope(retained, locale) == scope
        assert scope in materials_csv(materials, "0" * 64, locale).decode("utf-8-sig")
    woo_products = {
        cast(int, row["product_id"]): next(
            product
            for product in cast(list[Object], equipment["selected_products"])
            if product["product_id"] == row["product_id"]
        )
        for row in product_rows
    }
    items = purchase_items(product_rows, woo_products)
    assert [
        (item["product_id"], item["quantity"]) for item in cast(list[Object], items)
    ] == [
        (7001, 2),
        (9001, 1),
    ]


def test_plant_retention_purchases_only_new_units_of_a_shared_model() -> None:
    source = copy.deepcopy(_source_data())
    equipment = cast(Object, source["equipment"])
    equipment["selected_products"] = [
        {
            "product_id": 6506,
            "product_revision": "c" * 64,
            "brand": "GoodWe",
            "model": "GW75K-ET-G10",
            "sku": "DLK-A",
            "package_contents": {
                "status": "documented",
                "items": [
                    {
                        "id": "meter-lead",
                        "label": {"en": "Meter lead", "de": "Zählerleitung"},
                        "quantity": 1.25,
                        "unit": "m",
                        "role": "communication_cable",
                        "source": cast(Object, _source(40, "Meter lead × 1.25 m")),
                    }
                ],
            },
        },
        {
            "product_id": 8001,
            "product_revision": "e" * 64,
            "brand": "GoodWe",
            "model": "Controller",
            "sku": "DLK-C",
        },
    ]
    north_selection: Object = {
        "inverter_product_id": 6506,
        "battery_product_id": None,
        "accessory_product_ids": [],
        "equipment_use": {"inverter": "retain", "battery": "new"},
    }
    south_selection: Object = {
        "inverter_product_id": 6506,
        "battery_product_id": None,
        "accessory_product_ids": [],
    }
    # Two same-model converters: north keeps the original device, south adds
    # a new one. The unmerged per-system assessment bills still carry each
    # owner's exact quantity, which is where the retained share comes from.
    equipment["systems"] = [
        {
            "id": "north",
            "name": "North",
            "selection": north_selection,
            "assessment": {
                "provisional_bill_of_materials": [
                    {"product_id": 6506, "quantity": 1, "basis": "selected_converter"}
                ]
            },
        },
        {
            "id": "south",
            "name": "South",
            "selection": south_selection,
            "assessment": {
                "provisional_bill_of_materials": [
                    {"product_id": 6506, "quantity": 1, "basis": "selected_converter"}
                ]
            },
        },
    ]
    equipment["provisional_bill_of_materials"] = [
        {
            "product_id": 6506,
            "quantity": 2,
            "basis": "plant_allocations",
            "unit_ids": ["north", "south"],
        },
        {
            "product_id": 8001,
            "quantity": 1,
            "basis": "selected_parallel_controller",
            "group_ids": ["ac"],
        },
    ]
    equipment["installation_requirements"] = []
    source["equipment_plant"] = {
        "units": [
            {"id": "north", "name": "North", "selection": north_selection},
            {"id": "south", "name": "South", "selection": south_selection},
        ],
        "parallel_groups": [],
    }

    materials = project_materials(cast(Object, source))
    lines = cast(list[Object], materials["lines"])
    product_rows = [row for row in lines if row["handling"] == "woo_product"]

    assert [row["product_id"] for row in product_rows] == [6506, 8001]
    shared = next(row for row in product_rows if row["product_id"] == 6506)
    assert shared["quantity"] == 2
    assert shared["retained_quantity"] == 1
    assert material_scope(shared, "en") == (
        "Selected equipment · 1 of 2 retained on site · purchase 1"
    )
    assert material_scope(shared, "de") == (
        "Ausgewählte Geräte · 1 von 2 vorhanden · Beschaffung 1"
    )
    package = next(row for row in lines if row["handling"] == "manufacturer_included")
    assert package["quantity"] == 2.5
    for locale, label, supplied, retained_group in (
        (
            "en",
            "Meter lead",
            "Equipment from Linker",
            "Site and installation materials",
        ),
        (
            "de",
            "Zählerleitung",
            "Geräte von Linker",
            "Materialien für Standort und Montage",
        ),
    ):
        exported = list(
            csv.reader(
                io.StringIO(
                    materials_csv(materials, "0" * 64, locale).decode("utf-8-sig")
                )
            )
        )
        assert [(r[2], r[-1]) for r in exported if r[3] == label] == [
            ("1.25", supplied),
            ("1.25", retained_group),
        ]
        report = build_report(
            cast(
                Object,
                {**source, "title": "Plant", "locale": locale, "materials": materials},
            )
        )
        assert {
            s.title: [r[0] for r in s.table.rows if r[1] == label]
            for s in report.sections
            if s.table and s.title in (supplied, retained_group)
        } == {
            supplied: ["1.25 m" if locale == "en" else "1,25 m"],
            retained_group: ["1.25 m" if locale == "en" else "1,25 m"],
        }
    woo_products = {
        cast(int, row["product_id"]): next(
            product
            for product in cast(list[Object], equipment["selected_products"])
            if product["product_id"] == row["product_id"]
        )
        for row in product_rows
    }
    items = purchase_items(product_rows, woo_products)
    assert [
        (item["product_id"], item["quantity"]) for item in cast(list[Object], items)
    ] == [
        (6506, 1),
        (8001, 1),
    ]
    # The shared controller is one selected device per AC group, independently
    # retained from the converter units that group contains.
    plant = cast(Object, source["equipment_plant"])
    plant["parallel_groups"] = [
        {"id": "ac", "controller_product_id": 8001, "controller_use": "retain"}
    ]
    kept_controller = project_materials(cast(Object, source))
    kept_rows = [
        row
        for row in cast(list[Object], kept_controller["lines"])
        if row["handling"] == "woo_product"
    ]
    assert (
        next(row for row in kept_rows if row["product_id"] == 8001)["retained_quantity"]
        == 1
    )
    assert [
        (item["product_id"], item["quantity"])
        for item in cast(list[Object], purchase_items(kept_rows, woo_products))
    ] == [(6506, 1)]


@pytest.mark.parametrize(
    ("use", "line_id", "quantity_key", "en", "de"),
    [
        (
            "retain",
            "product:retained:7001",
            "retained_quantity",
            "Selected equipment · retained quantity unresolved",
            "Ausgewählte Geräte · Menge vorhandener Geräte noch offen",
        ),
        (
            "replace",
            "product:replacement:7001",
            "replacement_quantity",
            "Selected equipment · replacement quantity unresolved",
            "Ausgewählte Geräte · Menge der Ersatzgeräte noch offen",
        ),
    ],
)
def test_existing_device_without_a_bill_line_stays_visible_unresolved(
    use: str,
    line_id: str,
    quantity_key: str,
    en: str,
    de: str,
) -> None:
    source = copy.deepcopy(_source_data())
    equipment = cast(Object, source["equipment"])
    equipment["selected_products"] = [
        {
            "product_id": 6506,
            "product_revision": "c" * 64,
            "brand": "GoodWe",
            "model": "GW75K-ET-G10",
            "sku": "DLK-A",
        },
        {
            "product_id": 7001,
            "product_revision": "d" * 64,
            "brand": "GoodWe",
            "model": "BAT-C",
            "sku": "DLK-B",
        },
    ]
    # Without an established module count, the selected device remains visible
    # with an unresolved retained or replacement quantity.
    equipment["provisional_bill_of_materials"] = [
        {"product_id": 6506, "quantity": 1, "basis": "selected_converter"}
    ]
    equipment["installation_requirements"] = []
    source["equipment_selection"] = {
        "inverter_product_id": 6506,
        "battery_product_id": 7001,
        "accessory_product_ids": [],
        "equipment_use": {"inverter": "new", "battery": use},
    }

    materials = project_materials(cast(Object, source))
    product_rows = [
        row
        for row in cast(list[Object], materials["lines"])
        if row["handling"] == "woo_product"
    ]

    assert [row["product_id"] for row in product_rows] == [6506, 7001]
    selected = next(row for row in product_rows if row["product_id"] == 7001)
    assert selected["id"] == line_id
    assert selected["quantity"] is None
    assert selected[quantity_key] is None
    assert material_scope(selected, "en") == en
    assert material_scope(selected, "de") == de
    with pytest.raises(HandoffIncomplete):
        purchase_items(product_rows, {})


def test_purchase_items_rejects_a_retained_share_above_the_quantity() -> None:
    line: Object = {
        "product_id": 6506,
        "quantity": 1,
        "retained_quantity": 2,
        "brand": "GoodWe",
        "model": "GW75K-ET-G10",
    }

    with pytest.raises(HandoffIncomplete):
        purchase_items([line], {})


def test_route_quantity_uses_report_display_precision() -> None:
    line: Object = {"quantity": 12.36931687685298, "unit": "m"}
    assert material_quantity(line, "en") == "12.369 m"
    assert material_quantity(line, "de") == "12,369 m"


def test_customer_requested_quantity_is_separate_from_system_design() -> None:
    source = cast(Object, _source_data())
    source["inquiry_quantities"] = {"6506": {"planned_purchase": 2, "requested": 3}}
    materials = project_materials(source)
    row = next(
        line
        for line in cast(list[Object], materials["lines"])
        if line["handling"] == "woo_product"
    )
    assert row["quantity"] == 2 and row["inquiry_quantity"] == 3
    transfer = purchase_items([row], {})
    assert cast(Object, transfer[0])["quantity"] == 3
    for locale, heading in (("en", "Requested quantity"), ("de", "Anfragemenge")):
        csv_row = next(
            csv.DictReader(
                io.StringIO(
                    materials_csv(materials, "0" * 64, locale).decode("utf-8-sig")
                )
            )
        )
        assert csv_row[heading] == "3"
        assert heading + ": 3" in material_scope(row, locale)
    source["inquiry_quantities"] = {
        "6506": {"planned_purchase": 1, "requested": 3},
        "829": {"planned_purchase": 1, "requested": 99},
    }
    updated = project_materials(source)
    assert all(
        "inquiry_quantity" not in line for line in cast(list[Object], updated["lines"])
    )


@pytest.mark.parametrize("locale,page", [("en", "Page 43"), ("de", "Seite 43")])
@pytest.mark.parametrize("with_storage", [False, True])
def test_saj_equipment_proposal_places_terminal_excerpts_only_in_the_appendix(
    locale: str, page: str, with_storage: bool
) -> None:
    snapshots = Path(__file__).resolve().parents[4] / "tools/migrate"
    saj = json.loads((snapshots / "548-installation-facts.json").read_text())[
        "products"
    ]["1179"]
    documents = json.loads((snapshots / "548-page-excerpts.json").read_text())[
        "documents"
    ]
    facts = saj["items"]
    for item in facts:
        origin = item["source"]
        origin["url"] = documents[origin["document_id"]]["url"]
    assert facts[0]["source"]["quote"].startswith("B MPPT1 PV input")
    source = _source_data()
    source["declared_pv_panels"] = {"count": 16, "stc_power_w": 500}
    equipment = cast(dict[str, Any], source["equipment"])
    equipment["selected_products"] = [
        {
            "product_id": 1179,
            "model": saj["model"],
            "sku": "DLK-SAJ-H225KT3",
            "brand": "SAJ",
            "product_revision": saj["product_revision"],
            "installation_facts": {"status": "documented", "items": facts},
        }
    ]
    equipment["provisional_bill_of_materials"] = [
        {"product_id": 1179, "quantity": 1, "basis": "selected_converter"}
    ]
    if with_storage:
        equipment["selected_products"].append(
            {
                "product_id": 2068,
                "brand": "SAJ",
                "model": "B2-15.0-HV1",
                "sku": "DLK-SAJ-B2150HV1",
            }
        )
        equipment["provisional_bill_of_materials"].append(
            {"product_id": 2068, "quantity": 1, "basis": "selected_battery"}
        )
    material_source = cast(Object, source)
    materials = project_materials(material_source)
    report = build_report(
        {**material_source, "title": "SAJ", "locale": locale, "materials": materials}
    )
    commercial = [s for s in report.sections if s.tier == "commercial"]
    appendix = [s for s in report.sections if s.tier == "appendix"]
    shown = str([s.model_dump() for s in commercial])
    assert page in shown and ("DLK-SAJ-B2150HV1" in shown) == with_storage
    site = next(s for s in commercial if s.id == "site-materials")
    assert site.table and all(row[2] == page for row in site.table.rows)
    evidence = str([s.model_dump() for s in appendix])
    csv_rows = list(
        csv.reader(
            io.StringIO(materials_csv(materials, "0" * 64, locale).decode("utf-8-sig"))
        )
    )
    pages = [p.extract_text() for p in PdfReader(io.BytesIO(pdf.render(report))).pages]
    appendix_start = next(
        i
        for i, p in enumerate(pages)
        if (
            "Technischer & rechtlicher Anhang"
            if locale == "de"
            else "Technical & Compliance Appendix"
        )
        in p
    )
    for item in facts:
        origin = item["source"]
        assert origin["quote"] not in shown
        assert origin["quote"] in evidence and origin["url"] in evidence
        assert (
            origin["document_revision"] in evidence
            and origin["blob_sha256"] in evidence
        )
        assert any(origin["quote"] in row[4] for row in csv_rows)
        normalized = "".join(origin["quote"].split())
        assert normalized not in "".join("".join(pages[:appendix_start]).split())
        assert normalized in "".join("".join(pages[appendix_start:]).split())
