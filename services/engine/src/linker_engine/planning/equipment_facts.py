"""Typed, cited projections of current Woo facts, never a product registry.

Raw keys retain the manufacturer's quantity basis: module/system energy,
maximum/nominal power, operating/fault current and AC/DC ports are not merged.
Top-level selection scalars are deliberately excluded. Conversion is by the
stored unit, so kVA never becomes active kW. Unsupported text stays visible.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .canonical import Json, Object, decode_object, digest, encode

# Unit identities and SI prefixes; these are conversions, not device limits.
_UNITS: dict[str, tuple[str, str, float]] = {
    "W": ("active_power", "kW", 0.001),
    "kW": ("active_power", "kW", 1),
    "Wp": ("pv_nameplate_power", "kWp", 0.001),
    "kWp": ("pv_nameplate_power", "kWp", 1),
    "VA": ("apparent_power", "kVA", 0.001),
    "kVA": ("apparent_power", "kVA", 1),
    "Wh": ("energy", "kWh", 0.001),
    "kWh": ("energy", "kWh", 1),
    "V": ("voltage", "V", 1),
    "kV": ("voltage", "V", 1000),
    "A": ("current", "A", 1),
    "mA": ("current", "A", 0.001),
    "%": ("fraction", "fraction", 0.01),
    "°C": ("temperature", "°C", 1),
    "℃": ("temperature", "°C", 1),
    "%/°C": ("temperature_coefficient", "1/°C", 0.01),
}
_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
_SCALAR = re.compile(rf"^{_NUMBER}$")
_RANGE = re.compile(rf"^({_NUMBER})\s*(?:~|–|−|-|to)\s*({_NUMBER})$")
_COUNTS = frozenset(
    {
        "phases",
        "n_mppt",
        "strings_per_mppt",
        "modules_per_stack_min",
        "modules_per_stack_max",
        "stacks_parallel_max",
        "modules_per_system_max",
        "max_battery_modules",
        "battery_port_count",
        "number_of_battery_ports",
        "n_battery_ports",
        "max_lan_inverters",
    }
)


def _number(text: str, factor: float) -> float:
    value = float(Decimal(text) * Decimal(str(factor)))
    if not math.isfinite(value):
        raise ValueError("non-finite fact")
    return value


def _values(raw: str | int | float, factor: float) -> tuple[str, Json]:
    text = str(raw).strip()
    if _SCALAR.fullmatch(text):
        return "scalar", _number(text, factor)
    match = _RANGE.fullmatch(text)
    if match:
        low, high = (_number(part, factor) for part in match.groups())
        if low <= high:
            return "interval", [low, high]
    # An ordered table of columns stays ordered. Its columns do not become
    # a whole-product range or acquire a module-count meaning here.
    parts = re.split(r"\s*/\s*", text)
    if len(parts) > 1:
        entries: list[Json] = []
        for part in parts:
            kind, value = _values(part, factor)
            if kind not in {"scalar", "interval"}:
                return "text", text
            entries.append({"shape": kind, "value": value})
        return "ordered_values", entries
    return "text", text


def numeric_value(raw: str | int | float, unit: str) -> tuple[str, str, str, Json]:
    """The same SI projection for an explicitly maintained table cell.

    This validates redundant column values against the cited raw table; it
    does not infer a column from a model name or introduce device limits.
    """
    quantity, canonical_unit, factor = _UNITS[unit]
    shape, value = _values(raw, factor)
    return quantity, canonical_unit, shape, value


def _source(product: dict[str, Any], key: str, figure: dict[str, Any]) -> Object | None:
    citation = figure.get("citation")
    if not isinstance(citation, dict):
        return None
    page, url = citation.get("page"), citation.get("url")
    if type(page) is not int or page <= 0 or not isinstance(url, str):
        return None
    matches = [
        doc
        for doc in product["documents"]
        if url in [doc["url"], *doc.get("aliases", [])]
    ]
    if len(matches) != 1:
        return None
    doc = matches[0]
    sha, revision = doc.get("blob_sha256"), doc.get("document_revision")
    if (
        not isinstance(sha, str)
        or re.fullmatch(r"[a-f0-9]{64}", sha) is None
        or not isinstance(revision, str)
        or re.fullmatch(r"[a-f0-9]{64}", revision) is None
        or product["canonical_product_id"] not in doc.get("product_ids", [])
    ):
        return None
    return {
        "product_id": product["canonical_product_id"],
        "product_revision": product["product_revision"],
        "figure_key": key,
        "figure_sha256": digest(encode(figure)),
        "document_id": doc["document_id"],
        "document_revision": revision,
        "blob_sha256": sha,
        "url": url,
        "page": page,
    }


def compile_facts(product: dict[str, Any]) -> Object:
    """One loaded/current/prepared Woo record -> inspectable typed evidence.

    Publication checks belong to the enclosing ProductSources operation. This
    deterministic compiler also refuses ambiguous local evidence relationships.
    It never interprets natural-language qualifiers as satisfied conditions.
    """
    facts: Object = {}
    for key, figure in product["figures"].items():
        source = _source(product, key, figure)
        unit = figure.get("unit")
        unit_spec = _UNITS.get(unit) if isinstance(unit, str) else None
        if key in _COUNTS and unit in (None, "", "units", "modules", "packs"):
            unit_spec = ("count", "count", 1)
        shape: str = "text"
        value: Json = str(figure["value"])
        if unit_spec:
            try:
                shape, value = _values(figure["value"], unit_spec[2])
            except (ValueError, InvalidOperation, OverflowError):
                shape, value = "text", str(figure["value"])
        qualifier = figure.get("qualifier")
        status = (
            "unresolved_source"
            if source is None
            else "conditional"
            if qualifier not in (None, "", {}, [])
            else "typed"
            if shape != "text"
            else "text_evidence"
        )
        if unit_spec and shape == "scalar" and isinstance(value, (int, float)):
            if (
                unit_spec[0]
                in {
                    "active_power",
                    "pv_nameplate_power",
                    "apparent_power",
                    "energy",
                    "voltage",
                    "current",
                    "count",
                }
                and value < 0
            ):
                status = "invalid_numeric"
            if unit_spec[0] == "count" and not float(value).is_integer():
                status = "invalid_numeric"
        facts[key] = {
            "status": status,
            "quantity": unit_spec[0] if unit_spec else None,
            "unit": unit_spec[1] if unit_spec else unit,
            "shape": shape,
            "value": value,
            "raw_value": figure["value"],
            "raw_unit": unit,
            "qualifier": qualifier,
            "evidence_refs": figure.get("evidence_refs", []),
            "columns": figure.get("columns", []),
            "source": source,
        }
    return decode_object(encode(facts))


def compile_product(product: dict[str, Any]) -> Object:
    """Keep sales identity distinct from reference-component fact compilation."""
    facts = compile_facts(product)
    compiled: Object = {
        "product_id": product["canonical_product_id"],
        "product_revision": product["product_revision"],
        "sku": product["sku"],
        "model": product["model"],
        "brand": product["brand"],
        "device_class": product["device_class"],
        "facts": facts,
        "package_contents": product.get("package_contents"),
    }
    if "installation_facts" in product:
        compiled["installation_facts"] = product["installation_facts"]
    return decode_object(encode(compiled))
