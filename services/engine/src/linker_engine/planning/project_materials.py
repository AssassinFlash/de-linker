"""One frozen projection of established equipment, roof and included materials.

Woo remains the maintained authority. This projection introduces no manufacturer
facts or inferred installation quantities, and does not turn reference modules into
products that can be added to the solution draft.
"""

from __future__ import annotations

import csv
import io
import math
from decimal import Decimal
from typing import Any, cast

from .canonical import Json, Object, encode
from .report_copy import text


def project_materials(source: Object) -> Object:
    lines: list[Json] = []
    covered_inclusions: set[tuple[str, str]] = set()
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
                    "unit": "piece",
                    "basis": line["basis"],
                    "source": {
                        "woo_basis": cast(Object, source.get("woo_bases", {})).get(
                            "equipment"
                        ),
                        "product_revision": product.get("product_revision"),
                        "quantity_citation": sales.get("source")
                        if isinstance(sales, dict)
                        else None,
                        "selection": source.get(
                            "equipment_plant", source.get("equipment_selection")
                        ),
                    },
                }
            )
            package = product.get("package_contents")
            if isinstance(package, dict) and package.get("status") == "documented":
                parent_quantity = line.get("quantity")
                for item in cast(list[Object], package["items"]):
                    known = type(parent_quantity) is int and parent_quantity > 0
                    quantity = None
                    if known:
                        total = Decimal(str(item["quantity"])) * cast(
                            int, parent_quantity
                        )
                        quantity = float(total) if item["unit"] == "m" else int(total)
                    # Same exact-number browser transport bound as the source
                    # contracts; a large product cannot publish an unsafe total.
                    if quantity is not None and (
                        not math.isfinite(quantity) or quantity > 2**53 - 1
                    ):
                        quantity = None
                    lines.append(
                        {
                            "id": f"package:{line['product_id']}:{item['id']}",
                            "handling": "manufacturer_included",
                            "parent_product_id": line["product_id"],
                            "parent_label": " ".join(
                                str(identity[key])
                                for key in ("brand", "model")
                                if identity[key]
                            ),
                            "label": item["label"],
                            "quantity": quantity,
                            "unit": item["unit"],
                            "basis": "cited_contents_per_woo_sales_unit",
                            "source": {
                                "woo_basis": cast(
                                    Object, source.get("woo_bases", {})
                                ).get("equipment"),
                                "document": item["source"],
                                "per_sales_unit": item["quantity"],
                                "parent_quantity": parent_quantity,
                            },
                        }
                    )
                    if line.get("basis") == "selected_converter":
                        owners = line.get("unit_ids")
                        scopes = (
                            ["unit:" + str(uid) for uid in owners]
                            if isinstance(owners, list)
                            else ["legacy"]
                        )
                        covered_inclusions.update(
                            (scope, cast(str, item["role"])) for scope in scopes
                        )
        for index, requirement in enumerate(
            cast(list[Object], equipment.get("installation_requirements", []))
        ):
            inclusion_scope = (
                "unit:" + str(requirement["unit_id"])
                if "unit_id" in requirement
                else "group:" + str(requirement["group_id"])
                if "group_id" in requirement
                else "legacy"
            )
            if (
                requirement.get("included") is True
                and (inclusion_scope, requirement["kind"]) not in covered_inclusions
            ):
                lines.append(
                    {
                        "id": f"included:{index}:{requirement['kind']}",
                        "handling": "manufacturer_included",
                        "kind": requirement["kind"],
                        # An inclusion statement is not a documented count.
                        "quantity": None,
                        "unit": "piece",
                        "basis": "manufacturer_included",
                        "conditions": requirement.get("conditions", []),
                        "source": {"documents": requirement.get("documents", [])},
                        **(
                            {"unit_name": requirement["unit_name"]}
                            if "unit_name" in requirement
                            else {}
                        ),
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
                    "unit": "piece",
                    "basis": "saved_layout",
                    "source": citation,
                    "array_ids": part["array_ids"],
                    "layout_revision": pv["layout_revision"],
                    "scope": pv["scope"],
                }
            )
    installation = source.get("installation")
    if isinstance(installation, dict):
        for cable in cast(list[Object], installation["cables"]):
            lines.append(
                {
                    "id": f"installation:{cable['id']}",
                    "handling": "installation_requirement",
                    "label": {"en": cable["name"], "de": cable["name"]},
                    "quantity": cable["quantity"],
                    "unit": "m",
                    "basis": installation["method"],
                    "source": {
                        "installation_input_sha256": installation["input_sha256"],
                        "geometry_sha256": installation["geometry_sha256"],
                        **cable,
                    },
                }
            )
        reconciliation = installation.get("pv_string_reconciliation")
        if isinstance(reconciliation, dict):
            # Review requirements carry identity gaps into the existing export.
            # They have no material quantity and never become Woo sale rows.
            reviewed = cast(list[Object], reconciliation["rows"])
            review_rows: list[Object | None] = list(reviewed) if reviewed else [None]
            for link in review_rows:
                lines.append(
                    {
                        "id": f"installation-link:{link['string_id'] if link else 'plan'}",
                        "handling": "installation_requirement",
                        "label": {
                            locale: text("installation_string_link_review", locale)
                            for locale in ("en", "de")
                        },
                        "quantity": None,
                        "unit": "piece",
                        "basis": "pv_string_circuit_identity_v1",
                        "source": {
                            "scope": reconciliation["scope"],
                            "pv_string_plan_sha256": reconciliation[
                                "pv_string_plan_sha256"
                            ],
                            "installation_input_sha256": reconciliation[
                                "installation_input_sha256"
                            ],
                            "geometry_sha256": reconciliation["geometry_sha256"],
                            "plan_status": reconciliation["plan_status"],
                            "link": link,
                        },
                    }
                )
    return {
        "schema_version": 3,
        "kind": "project_materials_v3",
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
    if line["handling"] in {"manufacturer_included", "installation_requirement"}:
        if isinstance(line.get("label"), dict):
            name = cast(str, cast(Object, line["label"])[locale])
        else:
            name = text(f"material_{line['kind']}", locale)
    else:
        name = " ".join(str(line[key]) for key in ("brand", "model") if line.get(key))
    return f"{line['unit_name']} · {name}" if line.get("unit_name") else name


def material_reference(line: Object) -> str:
    if line["handling"] == "pv_reference":
        # The reference-input key is provenance, not a manufacturer SKU.
        return ""
    return str(line.get("sku") or "")


def material_scope(line: Object, locale: str) -> str:
    if line.get("basis") == "pv_string_circuit_identity_v1":
        source = cast(Object, line["source"])
        link = source["link"]
        status = (
            text(f"installation_string_link_{link['status']}", locale)
            if isinstance(link, dict)
            else text(f"installation_string_plan_{source['plan_status']}", locale)
        )
        return f"{text('installation_string_link_material_scope', locale)} · {status}"
    if line["handling"] == "manufacturer_included" and line.get("quantity") is not None:
        scope = text("material_included_documented", locale)
        parent = line.get("parent_label")
        return f"{scope} · {parent}" if parent else scope
    return text(f"material_{line['handling']}", locale)


def material_unit(line: Object, locale: str) -> str:
    return text(f"material_unit_{line.get('unit', 'piece')}", locale)


def material_quantity(line: Object, locale: str) -> str:
    value = line.get("quantity")
    if type(value) not in (int, float) or not math.isfinite(cast(float, value)):
        return "—"
    shown = format(Decimal(str(value)), ",f")
    if "." in shown:
        shown = shown.rstrip("0").rstrip(".")
    if locale == "de":
        shown = shown.translate(str.maketrans(",.", ".,"))
    return f"{shown} {material_unit(line, locale)}"


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
                "material_unit",
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
                material_unit(line, locale),
            )
        )
    # BOM ensures Excel also recognizes German names as UTF-8.
    return output.getvalue().encode("utf-8-sig")
