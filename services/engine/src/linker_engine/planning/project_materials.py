"""One frozen projection of established equipment, roof and included materials.

Woo remains the maintained authority. This projection introduces no product
facts or installation quantities, and does not turn reference modules into
products that can be added to the solution draft.
"""

from __future__ import annotations

import csv
import io
from typing import Any, cast

from .canonical import Json, Object, encode
from .report_copy import text


def project_materials(source: Object) -> Object:
    lines: list[Json] = []
    equipment = source.get("equipment")
    if isinstance(equipment, dict):
        products = {
            p["product_id"]: p
            for p in cast(list[Object], equipment["selected_products"])
        }
        for index, line in enumerate(
            cast(list[Object], equipment["provisional_bill_of_materials"])
        ):
            product = products.get(line["product_id"], {})
            identity = {
                field: line.get(field, product.get(field))
                for field in ("brand", "model", "sku")
            }
            facts = product.get("facts", {})
            sales = facts.get("sales_unit_kind") if isinstance(facts, dict) else None
            lines.append(
                {
                    "id": f"product:{index}:{line['product_id']}",
                    "handling": "woo_product",
                    "product_id": line["product_id"],
                    **identity,
                    "quantity": line.get("quantity"),
                    "basis": line["basis"],
                    "source": {
                        "woo_basis": cast(Object, source.get("woo_bases", {})).get(
                            "equipment"
                        ),
                        "product_revision": product.get("product_revision"),
                        "quantity_citation": sales.get("source")
                        if isinstance(sales, dict)
                        else None,
                        "selection": source.get("equipment_selection"),
                    },
                }
            )
        for index, requirement in enumerate(
            cast(list[Object], equipment.get("installation_requirements", []))
        ):
            if requirement.get("included") is True:
                lines.append(
                    {
                        "id": f"included:{index}:{requirement['kind']}",
                        "handling": "manufacturer_included",
                        "kind": requirement["kind"],
                        # An inclusion statement is not a documented count.
                        "quantity": None,
                        "basis": "manufacturer_included",
                        "conditions": requirement.get("conditions", []),
                        "source": {"documents": requirement.get("documents", [])},
                    }
                )
    pv = source.get("pv_components")
    if isinstance(pv, dict) and pv.get("status") == "available":
        for part in cast(list[Object], pv["components"]):
            citation = cast(Object, part["source"])
            woo = cast(Object, citation["woo"])
            lines.append(
                {
                    "id": f"pv:{woo['reference_input_id']}",
                    "handling": "pv_reference",
                    "product_id": woo["product_id"],
                    "model": part["model"],
                    "quantity": part["quantity"],
                    "basis": "saved_layout",
                    "source": citation,
                    "array_ids": part["array_ids"],
                    "layout_revision": pv["layout_revision"],
                    "scope": pv["scope"],
                }
            )
    return {
        "schema_version": 1,
        "kind": "project_materials_v1",
        "project_id": source["project_id"],
        "revision": source["revision"],
        "input_sha256": source["input_sha256"],
        "lines": lines,
        "installation_status": "not_assessed",
        "equipment_status": equipment.get("equipment_status")
        if isinstance(equipment, dict)
        else None,
    }


def material_name(line: Object, locale: str) -> str:
    if line["handling"] == "manufacturer_included":
        return text(f"material_{line['kind']}", locale)
    return " ".join(str(line[key]) for key in ("brand", "model") if line.get(key))


def material_reference(line: Object) -> str:
    if line["handling"] == "pv_reference":
        # The reference-input key is provenance, not a manufacturer SKU.
        return ""
    return str(line.get("sku") or "")


def material_scope(line: Object, locale: str) -> str:
    return text(f"material_{line['handling']}", locale)


def _cell(value: Any) -> str:
    shown = "" if value is None else str(value)
    # Product/project labels and conditions are untrusted spreadsheet cells.
    # Quoting alone does not prevent formulas when the file is opened in Excel.
    if shown[:1] in ("\t", "\r", "\n") or shown.lstrip().startswith(
        ("=", "+", "-", "@")
    ):
        return "'" + shown
    return shown


def materials_csv(materials: Object, sha256: str, locale: str) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            text(key, locale)
            for key in (
                "project_id",
                "revision",
                "quantity",
                "product",
                "reference",
                "material_handling",
                "material_source",
                "material_snapshot",
                "material_assessment",
            )
        ]
    )
    for line in cast(list[Object], materials["lines"]):
        provenance = encode(
            {
                key: line[key]
                for key in (
                    "basis",
                    "source",
                    "array_ids",
                    "layout_revision",
                    "scope",
                    "conditions",
                )
                if key in line
            }
        ).decode("utf-8")
        writer.writerow(
            _cell(value)
            for value in (
                materials["project_id"],
                materials["revision"],
                line["quantity"],
                material_name(line, locale),
                material_reference(line),
                material_scope(line, locale),
                provenance,
                sha256,
                text("material_installation_open", locale),
            )
        )
    # BOM ensures Excel also recognizes German names as UTF-8.
    return output.getvalue().encode("utf-8-sig")
