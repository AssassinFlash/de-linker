"""Literal per-document comparisons, without a project qualification decision."""

from __future__ import annotations

import re
from typing import cast

from .canonical import Json, Object
from .equipment_condition_inputs import (
    EquipmentConditionInputs,
    binding_key,
    selected_condition_devices,
    validate_condition_inputs,
)
from .errors import VersionUnavailable

# A model token may contain a printed slash (e.g. a power/capacity designation).
# Spaces, wildcards, prose and range operators do not form an explicit list.
_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./-]*\Z")
_FIRMWARE = re.compile(r"(?=[A-Za-z0-9._+\-]*\d)[A-Za-z0-9][A-Za-z0-9._+\-]*\Z")


def _literal_firmware(value: str) -> bool:
    return bool(_FIRMWARE.fullmatch(value)) and not (
        ".." in value
        or re.search(r"\d\s*[-+]\s*\d", value)
        or re.search(r"(?:^|[-_])(?:to|or|and)(?:[-_]|$)", value, re.I)
    )


REMAINING_OBLIGATIONS = [
    "document_scope",
    "other_pages_and_reports",
    "annex_conditions",
    "hardware_and_configuration",
    "operating_mode",
    "country_and_dso_settings",
    "standard_edition_and_transition",
    "issuer_current_status",
    "project_grid_assessment",
    "dso_permission",
]


def _field(inspection: Object, kind: str) -> Object | None:
    if inspection.get("status") != "read":
        return None
    declarations = inspection.get("declarations")
    if not isinstance(declarations, list):
        return None
    fields = [d for d in declarations if isinstance(d, dict) and d.get("kind") == kind]
    return fields[0] if len(fields) == 1 and fields[0].get("page") == 1 else None


def _model_check(inspection: Object, device: Object) -> Object:
    declared = device["declared_model"]
    value = declared if declared is not None else device["woo_model"]
    result: Object = {
        "status": "unresolved",
        "compared_value": value,
        "comparison_basis": "project_declared"
        if declared is not None
        else "selected_woo_model",
        "declared_values": None,
        "page": None,
        "reason": "model_field_unresolved",
    }
    field = _field(inspection, "models")
    if field is None or not isinstance(field.get("value"), str):
        return result
    # Only explicit delimiters separate full literal model names. A slash is
    # never expanded, nor are shared prefixes, X suffixes or power ranges.
    tokens = [part.strip() for part in re.split(r"[,;\n]", cast(str, field["value"]))]
    if not tokens or any(not _MODEL.fullmatch(token) for token in tokens):
        return result
    result.update(declared_values=tokens, page=1)
    if not isinstance(value, str) or not _MODEL.fullmatch(value):
        return {**result, "reason": "project_model_unresolved"}
    if value not in tokens and any("/" in token for token in tokens):
        # A slash may be a literal model designation or list shorthand. An
        # exact printed token can match; an absent token cannot expand it.
        return result
    return {
        **result,
        "status": "listed" if value in tokens else "not_listed",
        "reason": "literal_model_list_match"
        if value in tokens
        else "literal_model_not_listed",
    }


def _firmware_check(inspection: Object, device: Object) -> Object:
    value = device["declared_firmware"]
    result: Object = {
        "status": "unresolved",
        "compared_value": value,
        "declared_value": None,
        "page": None,
        "reason": "firmware_field_unresolved",
    }
    field = _field(inspection, "firmware")
    if field is None or not isinstance(field.get("value"), str):
        return result
    firmware = cast(str, field["value"])
    # Lists, ranges, descriptive software names and mixed component versions
    # remain unresolved. Numeric identity is never parsed or normalised.
    if not _literal_firmware(firmware):
        return result
    result.update(declared_value=firmware, page=1)
    if value is None or value == "":
        return {**result, "reason": "project_firmware_missing"}
    if not isinstance(value, str) or not _literal_firmware(value):
        return {**result, "reason": "project_firmware_unresolved"}
    return {
        **result,
        "status": "exact_match" if value == firmware else "conflict",
        "reason": "literal_firmware_equal"
        if value == firmware
        else "literal_firmware_different",
    }


def review_device_conditions(inputs: Object, evidence: Object) -> Object:
    observations: EquipmentConditionInputs | None = validate_condition_inputs(
        inputs, require_prepared=True
    )
    if observations is None:
        raise VersionUnavailable("project device observations are missing")
    observed = {
        binding_key(row): row
        for device in observations.devices
        for row in [cast(Object, device.model_dump(mode="json"))]
    }
    products = {p["product_id"]: p for p in cast(list[Object], evidence["products"])}
    inspections = cast(Object, evidence.get("inspections", {}))
    devices: list[Json] = []
    for binding in selected_condition_devices(inputs):
        product = products.get(binding["product_id"])
        if (
            product is None
            or product["product_revision"] != binding["product_revision"]
        ):
            raise VersionUnavailable("condition review differs from frozen Woo product")
        observation = observed.get(binding_key(binding), {})
        device: Object = {
            **binding,
            **{
                key: observation.get(key)
                for key in ("declared_model", "declared_firmware", "source_note")
            },
            "woo_model": product["model"],
        }
        declared_model = device["declared_model"]
        device["model_identity"] = {
            "status": "unprovided"
            if declared_model is None
            else "same_text"
            if declared_model == product["model"]
            else "different_text",
            "declared_value": declared_model,
            "selected_woo_value": product["model"],
        }
        documents: list[Json] = []
        for document in cast(list[Object], evidence["documents"]):
            if binding["product_id"] not in cast(list[Json], document["product_ids"]):
                continue
            inspection = inspections.get(str(document["document_id"]), {})
            if not isinstance(inspection, dict):
                raise VersionUnavailable("condition source inspection is invalid")
            if "declarations" in inspection and (
                inspection.get("method") != "literal_certificate_cover_v1"
                or inspection.get("applicability") != "not_assessed"
                or any(
                    inspection.get(key) != document[key]
                    for key in ("document_id", "document_revision", "blob_sha256")
                )
            ):
                raise VersionUnavailable("condition source inspection binding changed")
            documents.append(
                {
                    **{
                        key: document[key]
                        for key in ("document_id", "document_revision", "blob_sha256")
                    },
                    "applicability": "not_assessed",
                    "model": _model_check(inspection, device),
                    "firmware": _firmware_check(inspection, device),
                    "annex": {
                        "status": "unresolved",
                        "source": inspection.get("annex"),
                    },
                }
            )
        devices.append({**device, "documents": documents})
    return {
        "schema_version": 1,
        "method": "literal_device_conditions_v1",
        "applicability": "not_assessed",
        "devices": devices,
        "remaining_obligations": list(REMAINING_OBLIGATIONS),
    }
