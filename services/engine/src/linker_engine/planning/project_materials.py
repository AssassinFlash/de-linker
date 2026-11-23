"""One frozen projection of established equipment, roof and included materials.

Woo remains the maintained authority. This projection introduces no manufacturer
facts or inferred installation quantities, and does not turn reference modules into
products that can be added to the solution draft.
"""

from __future__ import annotations

import csv
import io
import math
import re
from decimal import Decimal
from typing import Any, cast

from .canonical import Json, Object, encode
from .report_copy import text
from .report_numbers import number


def _equipment_shares(
    equipment: Object, source: Object, use_kind: str
) -> dict[int, int | None]:
    """Read retained/replacement counts from the unmerged per-system bills.

    Same-model units can have different uses. A missing exact bill quantity
    stays unresolved rather than being inferred from the merged plant total.
    """
    owners: list[tuple[Object, list[Object]]] = []
    systems = equipment.get("systems")
    if isinstance(systems, list):
        for system in cast(list[Object], systems):
            raw_selection = system.get("selection")
            assessment = system.get("assessment")
            raw_bill = (
                assessment.get("provisional_bill_of_materials")
                if isinstance(assessment, dict)
                else None
            )
            if isinstance(raw_selection, dict) and isinstance(raw_bill, list):
                owners.append((raw_selection, cast(list[Object], raw_bill)))
    elif isinstance(source.get("equipment_selection"), dict):
        owners.append(
            (
                cast(Object, source["equipment_selection"]),
                cast(list[Object], equipment.get("provisional_bill_of_materials")),
            )
        )
    shares: dict[int, int | None] = {}
    for selection, bill in owners:
        use = selection.get("equipment_use")
        if not isinstance(use, dict):
            continue
        retained_ids: set[int] = set()
        for part in ("inverter", "battery"):
            if use.get(part) != use_kind:
                continue
            product_id = selection.get(f"{part}_product_id")
            if type(product_id) is int:
                retained_ids.add(product_id)
        for product_id in retained_ids:
            exact: list[int] = []
            for line in bill:
                if line.get("product_id") != product_id:
                    continue
                quantity = line.get("quantity")
                if type(quantity) is int:
                    exact.append(quantity)
            if product_id not in shares:
                shares[product_id] = sum(exact) if exact else None
                continue
            current = shares[product_id]
            if current is not None and exact:
                shares[product_id] = current + sum(exact)
            else:
                shares[product_id] = None
    plant = source.get("equipment_plant")
    if isinstance(plant, dict):
        for group in cast(list[Object], plant["parallel_groups"]):
            product_id = group.get("controller_product_id")
            if group.get("controller_use") == use_kind and type(product_id) is int:
                # plant_assessment emits one selected controller per AC group.
                current = shares.get(product_id, 0)
                shares[product_id] = current + 1 if current is not None else None
    return shares


def project_materials(source: Object) -> Object:
    lines: list[Json] = [
        dict(line) for line in cast(list[Object], source.get("customer_equipment", []))
    ]
    covered_inclusions: set[tuple[str, str]] = set()
    equipment = source.get("equipment")
    if isinstance(equipment, dict):
        products = {
            p["product_id"]: p
            for p in cast(list[Object], equipment["selected_products"])
        }
        retained_shares = _equipment_shares(equipment, source, "retain")
        replacement_shares = _equipment_shares(equipment, source, "replace")
        for index, line in enumerate(
            cast(list[Object], equipment["provisional_bill_of_materials"])
        ):
            product_id = cast(int, line["product_id"])
            product = products.get(product_id, {})
            identity = {
                field: line.get(field, product.get(field))
                for field in ("brand", "model", "sku")
            }
            facts = product.get("facts", {})
            sales = facts.get("sales_unit_kind") if isinstance(facts, dict) else None
            # Retained devices stay in the complete system list with their
            # exact on-site share; procurement reads quantity minus the share.
            retained_quantity = (
                {"retained_quantity": retained_shares[product_id]}
                if product_id in retained_shares
                else {}
            )
            lines.append(
                {
                    "id": f"product:{index}:{product_id}",
                    "handling": "woo_product",
                    "product_id": product_id,
                    **identity,
                    **retained_quantity,
                    **(
                        {"replacement_quantity": replacement_shares[product_id]}
                        if product_id in replacement_shares
                        else {}
                    ),
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
                    # Package contents describe the complete system, so a
                    # retained device's documented inclusions stay listed.
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
                    if line.get("basis") in {
                        "selected_converter",
                        "selected_parallel_controller",
                    }:
                        central = line.get("basis") == "selected_parallel_controller"
                        owners = line.get("group_ids" if central else "unit_ids")
                        scopes = (
                            [
                                ("group:" if central else "unit:") + str(uid)
                                for uid in owners
                            ]
                            if isinstance(owners, list)
                            else ["legacy"]
                        )
                        covered_inclusions.update(
                            (scope, cast(str, item["role"])) for scope in scopes
                        )
            installation = product.get("installation_facts")
            if (
                isinstance(installation, dict)
                and installation.get("status") == "documented"
            ):
                for item_index, item in enumerate(
                    cast(list[Object], installation["items"])
                ):
                    product_id = cast(int, line["product_id"])
                    # Installation facts describe the complete system and stay
                    # listed for a retained device, exactly as for a new one.
                    lines.append(
                        _installation_fact_line(
                            product_id,
                            item_index,
                            item,
                            identity,
                            line.get("quantity"),
                            product.get("product_revision"),
                            cast(Object, source.get("woo_bases", {})).get("equipment"),
                        )
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
        # Keep declared retained/replacement devices visible when their module
        # count was not established by the assessment.
        billed = {
            line["product_id"]
            for line in cast(list[Object], equipment["provisional_bill_of_materials"])
        }
        for product_id in sorted(
            (set(retained_shares) | set(replacement_shares)) - billed
        ):
            product = products.get(product_id, {})
            use = "retained" if product_id in retained_shares else "replacement"
            lines.append(
                {
                    "id": f"product:{use}:{product_id}",
                    "handling": "woo_product",
                    "product_id": product_id,
                    **{
                        field: product.get(field) for field in ("brand", "model", "sku")
                    },
                    **(
                        {"retained_quantity": None}
                        if product_id in retained_shares
                        else {}
                    ),
                    **(
                        {"replacement_quantity": None}
                        if product_id in replacement_shares
                        else {}
                    ),
                    "quantity": None,
                    "unit": "piece",
                    "basis": f"{use}_original_without_bill",
                    "source": {
                        "woo_basis": cast(Object, source.get("woo_bases", {})).get(
                            "equipment"
                        ),
                        "product_revision": product.get("product_revision"),
                        "selection": source.get(
                            "equipment_plant", source.get("equipment_selection")
                        ),
                    },
                }
            )
    pv = source.get("pv_components")
    if isinstance(pv, dict) and pv.get("status") == "available":
        for part in cast(list[Object], pv["components"]):
            citation = cast(Object, part["source"])
            lines.append(
                {
                    "id": f"pv:{part['module_spec_id']}",
                    "handling": "pv_reference",
                    "product_id": None,
                    "model": part["model"],
                    **{
                        key: part[key]
                        for key in ("stc_power_w", "length_m", "width_m")
                        if key in part
                    },
                    "quantity": part["quantity"],
                    "unit": "piece",
                    "basis": "saved_layout",
                    "source": citation,
                    "array_ids": part["array_ids"],
                    "layout_revision": pv["layout_revision"],
                    "scope": pv["scope"],
                }
            )
    declared_panels = source.get("declared_pv_panels")
    if isinstance(declared_panels, dict):
        lines.append(
            {
                "id": "pv:declared",
                "handling": "pv_declared",
                "product_id": None,
                "quantity": declared_panels["count"],
                "stc_power_w": declared_panels["stc_power_w"],
                "unit": "piece",
                "basis": "project_declared_panel_parameters",
                "source": {"kind": "user_declared"},
            }
        )
    installation = source.get("installation")
    if isinstance(installation, dict):
        declared = installation.get("material_review")
        protection = installation.get("protection_review")
        protection_rows = (
            protection.get("assessments", []) if isinstance(protection, dict) else []
        )
        if isinstance(declared, dict):
            for item in cast(list[Object], declared["rows"]):
                mounting_result = item.get("mounting_quantity_result")
                lines.append(
                    {
                        "id": f"installation-material:{item['id']}",
                        "handling": "installation_requirement",
                        "label": {"en": item["name"], "de": item["name"]},
                        "quantity": mounting_result.get("quantity")
                        if isinstance(mounting_result, dict)
                        else item["quantity"],
                        "unit": item["unit"],
                        "basis": "project_declared_installation_materials_v1",
                        "source": {
                            "installation_input_sha256": installation["input_sha256"],
                            "qualified": False,
                            "declaration": item,
                            **(
                                {
                                    "protection_assessments": [
                                        row
                                        for row in protection_rows
                                        if isinstance(row, dict)
                                        and row.get("protection_material_id")
                                        == item["id"]
                                    ]
                                }
                                if isinstance(protection_rows, list)
                                and any(
                                    isinstance(row, dict)
                                    and row.get("protection_material_id") == item["id"]
                                    for row in protection_rows
                                )
                                else {}
                            ),
                        },
                    }
                )
        electrical = installation.get("electrical")
        current_checks: dict[str, list[Json]] = {}
        if isinstance(electrical, dict):
            for segment in cast(
                list[Object], electrical.get("reference_current_segments", [])
            ):
                current_checks.setdefault(str(segment["run_id"]), []).append(segment)
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
                        **(
                            {
                                "reference_current_segments": current_checks[
                                    str(cable["id"])
                                ]
                            }
                            if str(cable["id"]) in current_checks
                            else {}
                        ),
                        **(
                            {
                                "electrical": {
                                    "method": electrical["method"],
                                    "circuit": next(
                                        (
                                            row
                                            for row in cast(
                                                list[Object], electrical["circuits"]
                                            )
                                            if row["circuit_id"] == cable["circuit_id"]
                                        ),
                                        None,
                                    ),
                                }
                            }
                            if isinstance(electrical, dict)
                            else {}
                        ),
                    },
                }
            )
        terminals = installation.get("terminal_assessment")
        if isinstance(terminals, dict):
            for circuit in cast(list[Object], terminals["circuits"]):
                lines.append(
                    {
                        "id": f"installation-terminals:{circuit['circuit_id']}",
                        "handling": "installation_requirement",
                        "label": {
                            "en": f"Terminal check · {circuit['name']}",
                            "de": f"Klemmenprüfung · {circuit['name']}",
                        },
                        "quantity": None,
                        "unit": "piece",
                        "basis": "manufacturer_one_end_mapping",
                        "source": {
                            "installation_input_sha256": installation["input_sha256"],
                            "qualified": False,
                            "circuit": circuit,
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
                        "basis": "pv_plant_string_circuit_identity_v2"
                        if reconciliation["schema_version"] == 2
                        else "pv_string_circuit_identity_v1",
                        "source": {
                            "scope": reconciliation["scope"],
                            **(
                                {
                                    "pv_plant_string_plan_sha256": reconciliation[
                                        "pv_plant_string_plan_sha256"
                                    ]
                                }
                                if reconciliation["schema_version"] == 2
                                else {
                                    "pv_string_plan_sha256": reconciliation[
                                        "pv_string_plan_sha256"
                                    ]
                                }
                            ),
                            "installation_input_sha256": reconciliation[
                                "installation_input_sha256"
                            ],
                            "geometry_sha256": reconciliation["geometry_sha256"],
                            "plan_status": reconciliation["plan_status"],
                            "link": link,
                        },
                    }
                )
    existing = source.get("existing_system")
    if isinstance(existing, dict):
        from .existing_system import retained_inverter_declared

        if not (
            existing["keep_inverter"]
            and equipment
            and retained_inverter_declared(source, selection=True)
        ):
            lines.append(
                {
                    "id": "existing-system",
                    "handling": "existing_system_declared",
                    "model": existing["name"],
                    "quantity": None,
                    "unit": "piece",
                    "basis": "customer_declared_existing_system",
                    "source": existing,
                }
            )
    retained = source.get("retained_inverter")
    if isinstance(retained, dict):
        declared_units = cast(list[Object], retained.get("units", []))
        demand_scopes = declared_units or [retained]
        for index, scope in enumerate(demand_scopes):
            requirements = cast(Object, scope["requirements"])
            if (
                any(
                    isinstance(value, (int, float)) and value > 0
                    for value in (
                        requirements.get("required_usable_kwh"),
                        requirements.get("required_discharge_ac_kw"),
                    )
                )
                or requirements.get("operating_mode") == "backup"
            ):
                lines.append(
                    {
                        "id": f"pending-battery:{index}",
                        "handling": "pending_battery_selection",
                        "quantity": None,
                        "unit": "piece",
                        "basis": "customer_declared_storage_demand",
                        "source": requirements,
                        **({"unit_name": scope["name"]} if "name" in scope else {}),
                    }
                )
    brief = source.get("brief")
    direction = brief.get("system_scope") if isinstance(brief, dict) else None
    requested = source.get("inquiry_quantities")
    if isinstance(requested, dict):
        for raw_line in lines:
            material = cast(Object, raw_line)
            if material["handling"] != "woo_product":
                continue
            entry = requested.get(str(material["product_id"]))
            planned = _requested_quantity(material)
            if (
                isinstance(entry, dict)
                and planned is not None
                and entry.get("planned_purchase") == planned
            ):
                material["inquiry_quantity"] = entry["requested"]
    return {
        "schema_version": 3,
        **({"system_scope": direction} if direction else {}),
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


def panel_description(panel: Object, locale: str) -> str:
    """Describe project parameters independently of the supply list."""
    power = panel.get("stc_power_w")
    length, width = panel.get("length_m"), panel.get("width_m")
    dimensions = ""
    if isinstance(length, (int, float)) and isinstance(width, (int, float)):
        dimensions = (
            f" · {number(length * 1000, locale)} × {number(width * 1000, locale)} mm"
        )
    if not isinstance(power, (int, float)):
        # Earlier materials stored these parameters in panel_label's display string.
        historical = re.fullmatch(
            r"(?:PV )?([0-9]+(?:\.[0-9]+)?) Wp(?: · ([0-9]+(?:\.[0-9]+)?) × ([0-9]+(?:\.[0-9]+)?) mm)?",
            str(panel.get("model") or ""),
        )
        if not historical:
            return text("panel_reference_only", locale)
        power = float(historical[1])
        if historical[2] and historical[3]:
            dimensions = f" · {number(float(historical[2]), locale)} × {number(float(historical[3]), locale)} mm"
    return (
        text("panel_reference_power", locale).format(power=number(power, locale))
        + dimensions
    )


def material_name(line: Object, locale: str) -> str:
    if line["handling"] in {"pv_declared", "pv_reference"}:
        return panel_description(line, locale)
    if line["handling"] == "pending_battery_selection":
        return text("pending_battery", locale)
    if line["handling"] == "existing_system_declared":
        return str(line.get("model") or text("existing_system", locale))
    if line["handling"] in {
        "manufacturer_included",
        "customer_supplied_required",
        "site_engineering_required",
        "installation_requirement",
    }:
        if isinstance(line.get("label"), dict):
            name = cast(str, cast(Object, line["label"])[locale])
        else:
            name = text(f"material_{line['kind']}", locale)
    else:
        name = " ".join(str(line[key]) for key in ("brand", "model") if line.get(key))
    return f"{line['unit_name']} · {name}" if line.get("unit_name") else name


def material_reference(line: Object) -> str:
    origin = line.get("source")
    if line["handling"] in {
        "manufacturer_included",
        "customer_supplied_required",
        "site_engineering_required",
    }:
        if (
            isinstance(origin, dict)
            and origin.get("origin") == "_linker_installation_facts"
        ):
            document = cast(Object, origin["document"])
            if isinstance(document, dict):
                return f"p. {document['page']} · {document['quote']}"
    if line["handling"] == "pv_reference":
        # The reference-input key is provenance, not a manufacturer SKU.
        return ""
    return str(line.get("sku") or "")


def mounting_quantity_explanation(result: Object, locale: str) -> str:
    if result.get("status") != "calculated":
        return (
            "Mengenregel erneut bestätigen"
            if locale == "de"
            else "Reconfirm the quantity rule"
        )
    if locale == "de":
        return (
            f"{result['modules']} Module × {result['per_module']} + "
            f"{result['segments']} belegte Reihenabschnitte × {result['per_segment']} + "
            f"{result['adjacencies']} Paare benachbarter Modulplätze × {result['per_adjacency']} = {result['quantity']} Stück"
        )
    return (
        f"{result['modules']} modules × {result['per_module']} + "
        f"{result['segments']} occupied row segments × {result['per_segment']} + "
        f"{result['adjacencies']} neighboring slot pairs × {result['per_adjacency']} = {result['quantity']} pieces"
    )


def material_scope(line: Object, locale: str) -> str:
    if line["handling"] == "pending_battery_selection":
        return text("pending_battery_compatibility", locale)
    if line["handling"] == "existing_system_declared":
        existing = cast(Object, line["source"])
        return " · ".join(
            text(key, locale)
            for key in (
                (
                    "existing_system_declared",
                    "existing_inverter_keep",
                    "existing_inverter_open",
                )
                if existing["keep_inverter"]
                else ("existing_system_declared",)
            )
        )
    if line.get("basis") == "project_declared_installation_materials_v1":
        source = line.get("source")
        declaration = source.get("declaration") if isinstance(source, dict) else None
        result = (
            declaration.get("mounting_quantity_result")
            if isinstance(declaration, dict)
            else None
        )
        if isinstance(result, dict):
            return mounting_quantity_explanation(result, locale) + (
                " · Projektangabe; technische Eignung nicht geprüft"
                if locale == "de"
                else " · Project declaration; technical suitability not assessed"
            )
        return (
            "Projektangabe · technische Eignung nicht geprüft"
            if locale == "de"
            else "Project declaration · technical suitability not assessed"
        )
    if line.get("basis") == "manufacturer_one_end_mapping":
        return "Klemmenprüfung" if locale == "de" else "Terminal check"
    if line.get("basis") in {
        "pv_string_circuit_identity_v1",
        "pv_plant_string_circuit_identity_v2",
    }:
        source = cast(Object, line["source"])
        link = source["link"]
        status = (
            text(f"installation_string_link_{link['status']}", locale)
            if isinstance(link, dict)
            else text(f"installation_string_plan_{source['plan_status']}", locale)
        )
        return (
            f"{text('installation_string_link_material_scope', locale)} · "
            + (
                f"{link['unit_id']} · {link['inverter_instance_id'] or text('pv_instance_not_recorded', locale)} · "
                if isinstance(link, dict) and "unit_id" in link
                else ""
            )
            + status
        )
    if line["handling"] == "installation_requirement":
        # A recorded cross-section is still not a sizing result, so the scope
        # names what is declared instead of claiming the specification is done.
        origin = line.get("source")
        specification = (
            origin.get("specification") if isinstance(origin, dict) else None
        )
        return text(
            "material_installation_declared"
            if specification == "declared"
            else "material_installation_requirement",
            locale,
        )
    if line["handling"] == "woo_product":
        scope = text("material_woo_product", locale)
        if "retained_quantity" in line:
            retained = line["retained_quantity"]
            quantity = line.get("quantity")
            if type(retained) is not int or type(quantity) is not int:
                scope += f" · {text('material_retention_unresolved', locale)}"
            elif retained >= quantity:
                scope = text("material_retained_full", locale)
            elif locale == "de":
                scope += (
                    f" · {retained} von {quantity} vorhanden"
                    f" · Beschaffung {quantity - retained}"
                )
            else:
                scope += (
                    f" · {retained} of {quantity} retained on site"
                    f" · purchase {quantity - retained}"
                )
        if "replacement_quantity" in line:
            replacement = line["replacement_quantity"]
            description = (
                text("material_replacements", locale).format(quantity=replacement)
                if type(replacement) is int
                else text("material_replacements_unresolved", locale)
            )
            scope += f" · {description}"
        if "inquiry_quantity" in line:
            scope += (
                f" · {text('inquiry_quantity', locale)}: {line['inquiry_quantity']}"
            )
        return scope
    if line.get("package_supply") == "retained":
        scope = (
            "Lieferumfang der vorhandenen Geräte"
            if locale == "de"
            else "Package contents of existing equipment"
        )
    elif line.get("package_supply") == "unresolved":
        scope = (
            "Zuordnung zu vorhandenen oder neuen Geräten offen"
            if locale == "de"
            else "Allocation to existing or new equipment unconfirmed"
        )
    elif (
        line["handling"] == "manufacturer_included" and line.get("quantity") is not None
    ):
        scope = text("material_included_documented", locale)
        parent = line.get("parent_label")
        scope = f"{scope} · {parent}" if parent else scope
    else:
        scope = text(f"material_{line['handling']}", locale)
    origin = line.get("source")
    if (
        isinstance(origin, dict)
        and origin.get("origin") == "_linker_installation_facts"
    ):
        conditions = line.get("conditions")
        if isinstance(conditions, list):
            localized: list[str] = []
            for condition in conditions:
                if not isinstance(condition, dict):
                    continue
                value = condition.get(locale)
                if isinstance(value, str) and value:
                    localized.append(value)
            if localized:
                return f"{scope} · {'; '.join(localized)}"
    return scope


def material_unit(line: Object, locale: str) -> str:
    return text(f"material_unit_{line.get('unit', 'piece')}", locale)


def conductor_specification(line: Object, locale: str) -> str:
    """A declared cross-section shown as declared, never as a sizing result."""
    # Routing rows carry the run at top level; BOM lines nest it as source.
    source = line.get("source")
    declared = line.get("conductor")
    if declared is None and isinstance(source, dict):
        declared = source.get("conductor")
    if not isinstance(declared, dict):
        return text("installation_conductor_open", locale)
    value = format(Decimal(str(declared["cross_section_mm2"])), ",f")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    if locale == "de":
        value = value.translate(str.maketrans(",.", ".,"))
    return f"{value} mm²"


def material_quantity(line: Object, locale: str) -> str:
    value = line.get("quantity")
    if type(value) not in (int, float) or not math.isfinite(cast(float, value)):
        return "—"
    return number(value, locale, material_unit(line, locale))


def _cell(value: Any) -> str:
    shown = "" if value is None else str(value)
    # Product/project labels and conditions are untrusted spreadsheet cells.
    # Quoting alone does not prevent formulas when the file is opened in Excel.
    if shown[:1] in ("\t", "\r", "\n") or shown.lstrip().startswith(
        ("=", "+", "-", "@")
    ):
        return "'" + shown
    return shown


def _installation_fact_line(
    product_id: int,
    item_index: int,
    item: Object,
    identity: Object,
    parent_quantity: Any,
    product_revision: Any,
    woo_basis: Any,
) -> Json:
    quantity = None
    conditions = item.get("conditions")
    is_conditional = isinstance(conditions, list) and bool(conditions)
    handling = (
        "site_engineering_required"
        if item["handling"] == "manufacturer_included" and is_conditional
        else item["handling"]
    )
    known = type(parent_quantity) is int and parent_quantity > 0
    declared = item.get("quantity")
    declared_quantity = (
        declared
        if (isinstance(declared, int) and not isinstance(declared, bool))
        or (isinstance(declared, float) and math.isfinite(declared))
        else None
    )
    if (
        item["handling"] == "manufacturer_included"
        and not is_conditional
        and known
        and isinstance(declared, (int, float))
        and not isinstance(declared, bool)
        and (isinstance(declared, int) or math.isfinite(declared))
    ):
        total = Decimal(str(declared)) * cast(int, parent_quantity)
        if total <= Decimal(2**53 - 1):
            candidate = float(total) if item["unit"] == "m" else int(total)
            if math.isfinite(float(candidate)) and candidate <= 2**53 - 1:
                quantity = candidate
    source = cast(Object, item["source"])
    return {
        "id": f"installation:{product_id}:{item_index}:{item['id']}",
        "handling": handling,
        "parent_product_id": product_id,
        "parent_label": " ".join(
            str(identity[key]) for key in ("brand", "model") if identity[key]
        ),
        "label": item["label"],
        "quantity": quantity,
        "declared_quantity": declared_quantity,
        "unit": item["unit"],
        "basis": f"installation_fact:{item['basis']}",
        "specification": item.get("specification"),
        "conditions": item.get("conditions", []),
        "source": {
            "woo_basis": woo_basis,
            "product_revision": product_revision,
            "authority": "woocommerce_product_meta",
            "origin": "_linker_installation_facts",
            "document_id": source["document_id"],
            "document_revision": source["document_revision"],
            "blob_sha256": source["blob_sha256"],
            "page": source["page"],
            "quote": source["quote"],
            "source": "linked_woo_document",
            "document": source,
        },
    }


def listed_materials(lines: list[Object]) -> list[Object]:
    """Allocate frozen package contents to the same supply lists as their parents."""
    retained = {
        cast(int, line["product_id"]): line
        for line in lines
        if line["handling"] == "woo_product"
        and "retained_quantity" in line
        and isinstance(line.get("product_id"), int)
    }
    result = []
    for line in lines:
        parent_id = line.get("parent_product_id")
        parent = retained.get(parent_id) if isinstance(parent_id, int) else None
        if line["handling"] != "manufacturer_included" or parent is None:
            result.append(line)
            continue
        existing, total = parent["retained_quantity"], parent.get("quantity")
        if existing == 0:
            result.append(line)
        elif type(total) is int and type(existing) is int and existing >= total:
            result.append({**line, "package_supply": "retained"})
        else:
            origin = line.get("source")
            per_unit = (
                origin.get("per_sales_unit") if isinstance(origin, dict) else None
            )
            if per_unit is None:
                per_unit = line.get("declared_quantity")
            if (
                type(existing) is not int
                or type(total) is not int
                or not isinstance(per_unit, (int, float))
                or line.get("quantity") is None
            ):
                result.append({**line, "package_supply": "unresolved"})
                continue
            factor = Decimal(str(per_unit))
            for use, parents in (("retained", existing), ("new", total - existing)):
                amount = factor * parents
                result.append(
                    {
                        **line,
                        "package_supply": use,
                        "quantity": float(amount)
                        if line.get("unit") == "m"
                        else int(amount),
                    }
                )
    return result


def material_list(line: Object, locale: str) -> str:
    if line.get("package_supply") in ("retained", "unresolved"):
        return text("site_material_list", locale)
    if line["handling"] == "pv_declared":
        return text("material_pv_declared", locale)
    if line["handling"] == "pv_reference":
        return text("pv_components_title", locale)
    quantity, retained = line.get("quantity"), line.get("retained_quantity")
    if (
        line["handling"] == "woo_product"
        and type(quantity) is int
        and type(retained) is int
        and retained >= quantity
    ):
        return text("site_material_list", locale)
    if line["handling"] in (
        "woo_product",
        "manufacturer_included",
        "customer_equipment_pending",
    ):
        return text("equipment_list", locale)
    return text("site_material_list", locale)


def _requested_quantity(line: Object) -> int | None:
    if line.get("handling") != "woo_product":
        return None
    quantity, retained = line.get("quantity"), line.get("retained_quantity", 0)
    if type(quantity) is not int or type(retained) is not int or quantity <= retained:
        return None
    return cast(int, line.get("inquiry_quantity", quantity - retained))


def materials_csv(materials: Object, sha256: str, locale: str) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    direction = materials.get("system_scope")
    if not materials["lines"] and direction:
        writer.writerow(
            text(key, locale) for key in ("project_id", "revision", "planned_system")
        )
        writer.writerow(
            [
                _cell(materials["project_id"]),
                materials["revision"],
                text(f"scope_{direction}", locale),
            ]
        )
        return output.getvalue().encode("utf-8-sig")
    has_requested = any(
        "inquiry_quantity" in row for row in cast(list[Object], materials["lines"])
    )
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
                "material_list",
                *(("inquiry_quantity",) if has_requested else ()),
            )
        ]
    )
    lines = listed_materials(cast(list[Object], materials["lines"]))
    order = [
        text(key, locale)
        for key in (
            "equipment_list",
            "site_material_list",
            "pv_components_title",
            "material_pv_declared",
        )
    ]
    for line in sorted(lines, key=lambda row: order.index(material_list(row, locale))):
        origin = line.get("source")
        comparison = (
            origin.get("manufacturer_comparison") if isinstance(origin, dict) else None
        )
        assessment = text("material_installation_open", locale)
        protection_checks = (
            origin.get("protection_assessments") if isinstance(origin, dict) else None
        )
        if isinstance(protection_checks, list) and protection_checks:
            from .installation_protection_report import protection_section

            section = protection_section({"assessments": protection_checks}, locale)
            assessment += " · " + " · ".join(
                f"{row.label}: {row.value}" for row in section.rows
            )
        if isinstance(comparison, dict):
            labels = {
                "within_recommendation": (
                    "Within the recommended cross-section range",
                    "Innerhalb des empfohlenen Querschnittsbereichs",
                ),
                "outside_recommendation": (
                    "Outside the recommended cross-section range",
                    "Außerhalb des empfohlenen Querschnittsbereichs",
                ),
            }
            label = labels.get(
                str(comparison.get("status")),
                ("Comparison unavailable", "Vergleich nicht verfügbar"),
            )
            assessment = label[1 if locale == "de" else 0] + " · " + assessment
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
                assessment,
                material_unit(line, locale),
                material_list(line, locale),
                *((_requested_quantity(line),) if has_requested else ()),
            )
        )
    # BOM ensures Excel also recognizes German names as UTF-8.
    return output.getvalue().encode("utf-8-sig")
