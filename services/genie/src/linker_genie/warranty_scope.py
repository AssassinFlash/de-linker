"""Conditional claims instructions, bound to two current manufacturer originals.

A series match establishes only the provenance of a procedure. It never grants
coverage, a warranty period, a technical parameter or an individual entitlement.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from linker_genie.source_models import model_pattern
from linker_genie.table_projection import model_axis, read_cells

# Literal manufacturer cover vocabulary in the hosted ESA/ET/STSs originals.
# Power ranges must agree; an ESA family name alone cannot cross its ranges.
FAMILY = re.compile(r"\b([a-z][a-z0-9]*)\s+(?:series|serie)\b", re.IGNORECASE)
POWER_RANGE = re.compile(
    r"(?<!\w)(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*kW\b",
    re.IGNORECASE,
)

CONDITIONAL_CLAIMS_NOTE = (
    "This source establishes only the manufacturer's first-contact claims procedure "
    "for the named series. It does not establish coverage, warranty duration or an "
    "individual device's eligibility; applicable original policy conditions still "
    "require verification."
)


def family_signature(quote: str) -> tuple[str, str, str] | None:
    """One explicit cover family and at most one distinct rated-power range."""
    names = {m.casefold() for m in FAMILY.findall(quote)}
    ranges = {
        tuple(str(Decimal(n.replace(",", ".")).normalize()) for n in pair)
        for pair in POWER_RANGE.findall(quote)
    }
    if len(names) != 1 or len(ranges) > 1:
        return None
    lower, upper = next(iter(ranges)) if ranges else ("", "")
    return next(iter(names)), lower, upper


def series_matches(cell: str, family: Sequence[str]) -> bool:
    """The original policy's Series cell must name the same qualified family."""
    if len(family) != 3:
        return False
    name, lower, upper = family
    if not lower and not upper:
        return bool(
            re.search(rf"\b{re.escape(name)}[-\s]+(?:series|serie)\b", cell, re.I)
        )
    matches = re.finditer(
        rf"\b{re.escape(name)}\s+(\d+(?:[.,]\d+)?)\s*[-–]\s*"
        r"(\d+(?:[.,]\d+)?)\s*k(?:W)?\b",
        cell,
        re.I,
    )
    return any(
        tuple(str(Decimal(n.replace(",", ".")).normalize()) for n in m.groups())
        == (lower, upper)
        for m in matches
    )


def claims_procedure(text: str) -> bool:
    """Only model-free first-contact instructions; no numbers or benefit terms.

    The original EN p2 and DE p2 name both seller and installer. Numeric dates,
    durations and specifications are deliberately outside this capability.
    """
    if re.search(
        r"\d|\b(?:warranty\s+period|coverage|eligible|years?|months?|"
        r"Garantiezeit\w*|Gewährleistungsfrist|Jahre\w*|Monate\w*)\b",
        text,
        re.I,
    ):
        return False
    english = all(
        re.search(pattern, text, re.I)
        for pattern in [r"\bclaim\w*\b", r"\bdistributor\w*\b", r"\binstaller\w*\b"]
    )
    german = all(
        re.search(pattern, text, re.I)
        for pattern in [
            r"\bGarantieantrag\w*\b",
            r"\b\w*händler\w*\b",
            r"\bInstallateur\w*\b",
        ]
    )
    return english or german


def procedure_id(sha: str, page: int, model: str, original: str, text: str) -> str:
    digest = hashlib.sha256(f"{model}\0{original}\0{text}".encode()).hexdigest()[:16]
    return f"{sha[:12]}-p{page}-warranty-{digest}"


def _purpose_is(document: Mapping[str, Any], purpose: str) -> bool:
    # Keep the established role-first precedence. A generic/dedicated role is
    # not overridden by the type while validating a new conditional grant.
    label = str(document.get("role", "")).strip() or str(document.get("type", ""))
    return (
        label.casefold()
        in {
            "datasheet": {"datasheet", "datenblatt"},
            "warranty": {"warranty", "garantie"},
        }[purpose]
    )


def valid_warranty_scope(
    scope: Mapping[str, Any],
    product_ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    documents: Mapping[str, Mapping[str, Any]],
    *,
    sha: str,
    chunk_id: str,
    text: str,
) -> bool:
    """Recheck both document grants and the exact model/series/procedure chain."""
    value = scope.get("warranty_scope")
    if not isinstance(value, dict) or scope.get("basis") != "warranty_procedure":
        return False
    pid = value.get("product_id")
    if (
        type(pid) is not int
        or list(product_ids) != [pid]
        or scope.get("product_ids") != [pid]
        or pid not in products
        or value.get("conditional") is not True
        or value.get("model") != products[pid].get("model")
        or value.get("source_sha256") != sha
        or value.get("text_sha256") != hashlib.sha256(text.encode()).hexdigest()
        or type(value.get("source_page")) is not int
        or value["source_page"] <= 0
        or not claims_procedure(text)
    ):
        return False
    source_ids = scope.get("source_chunk_ids", [])
    for field, purpose in [("datasheet", "datasheet"), ("policy", "warranty")]:
        evidence = value.get(field)
        if not isinstance(evidence, dict):
            return False
        document = documents.get(evidence.get("document_id", ""))
        if (
            document is None
            or not _purpose_is(document, purpose)
            or document.get("document_revision") != evidence.get("document_revision")
            or document.get("blob_sha256") != evidence.get("blob_sha256")
            or pid not in document.get("product_ids", [])
            or document.get("document_id") not in products[pid].get("documents", [])
        ):
            return False
    sheet, policy = value["datasheet"], value["policy"]
    conditions = policy.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        return False
    brand = str(products[pid].get("brand", ""))
    if not brand or not any(
        isinstance(c, dict)
        and re.search(rf"\b{re.escape(brand)}\b", str(c.get("quote", "")), re.I)
        for c in conditions
    ):
        return False
    if any(
        not isinstance(c, dict)
        or type(c.get("page")) is not int
        or c["page"] <= 0
        or not isinstance(c.get("quote"), str)
        or not c["quote"]
        or not isinstance(c.get("chunk_id"), str)
        or not c["chunk_id"].startswith(sha[:12] + "-p")
        or c["chunk_id"] not in source_ids
        for c in conditions
    ):
        return False
    family = family_signature(str(sheet.get("cover_quote", "")))
    model_quote = sheet.get("model_quote", "")
    header_cells = sheet.get("model_header_cells", [])
    if header_cells:
        cells = read_cells(header_cells)
        axis = model_axis(cells) if cells is not None else None
        if (
            axis is None
            or str(value["model"]).casefold() not in {v.casefold() for v in axis}
            or model_quote not in axis
            or any(
                s["source_sha256"] != sheet["blob_sha256"]
                or s["page"] != sheet.get("model_source_page")
                for c in cells or []
                for s in c.get("model_spans", [])
            )
        ):
            return False
    original = value.get("source_chunk_id", "")
    if (
        family is None
        or list(family) != value.get("family")
        or not series_matches(str(policy.get("series_cell", "")), family)
        or not policy.get("row_quote")
        or policy["series_cell"] not in policy["row_quote"]
        or not isinstance(model_quote, str)
        or not model_pattern(str(value["model"])).search(model_quote)
        or not isinstance(original, str)
        or not original.startswith(sha[:12] + "-p")
    ):
        return False
    for evidence, fields in [
        (sheet, ["cover_chunk_id", "model_chunk_id"]),
        (policy, ["row_chunk_id"]),
    ]:
        for field in fields:
            cid = evidence.get(field)
            if (
                not isinstance(cid, str)
                or cid not in source_ids
                or not cid.startswith(evidence["blob_sha256"][:12] + "-p")
            ):
                return False
    return (
        original in source_ids
        and policy["blob_sha256"] == sha
        and chunk_id
        == procedure_id(sha, value["source_page"], str(value["model"]), original, text)
    )
