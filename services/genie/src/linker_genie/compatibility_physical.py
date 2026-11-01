"""Validate physical-source compatibility proofs and their current owners."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from linker_genie.table_projection import (
    overview_row,
    read_cells,
    valid_compatibility_series,
)

# Digests record the reviewed original text, character positions and bounding
# boxes, including the complete condition in each actual manufacturer row.
PHYSICAL_DIGESTS = {
    (
        "4f7178042e8faf03bd926dc33a5ff0b85ffcd4f46e12f1dcf86d6db10befee4d",
        "series_axis",
        2,
    ): "880e39b2339bfae7129c486ebaed576b7545ba3f4bbb69673668969f5b230134",
    (
        "76df70ea8474531fb1f1d168b6faf3262cf2242358be9ba9d17b5f2fb5e75afd",
        "series_axis",
        2,
    ): "a773ae92bfe125facc16ec1712dc9a5a7b5b20ac9ee243f2dc0d2027cf7e353a",
    (
        "6f33b8361fe25fa2798c424fd30c2601036a56212b9e62a312e6aadb060b8b3d",
        "iot_matrix",
        7,
    ): "4b1b973f769a8d356f1641d473e2f7fa1e336ed6d82c0901c0b951a34ed2ace1",
    (
        "6f33b8361fe25fa2798c424fd30c2601036a56212b9e62a312e6aadb060b8b3d",
        "iot_matrix",
        9,
    ): "c2859e1d24ae58c5d7b5ac90b5fc112c9464a1f9edf4ff109e8c0419e21e037f",
}


def physical_key(chunk_id: str) -> str:
    return "physical:" + chunk_id


def valid_physical_evidence(evidence: Any, sha: str, chunk_id: str, text: str) -> bool:
    if not isinstance(evidence, dict):
        return False
    kind, page = evidence.get("kind"), evidence.get("source_page")
    if not isinstance(kind, str) or type(page) is not int:
        return False
    key = (sha, kind, page)
    expected = PHYSICAL_DIGESTS.get(key)
    if (
        expected is None
        or evidence.get("source_sha256") != sha
        or evidence.get("target_chunk_id") != chunk_id
        or evidence.get("source_text") != text
    ):
        return False
    encoded = json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode()).hexdigest() == expected


def source_id(sha: str, page: int, basis: str, text: str) -> str:
    digest = hashlib.sha256((basis + "\0" + text).encode()).hexdigest()[:16]
    return f"{sha[:12]}-p{page}-{basis}-{digest}"


def inverter_text(model: str, series: str, base: str, lang: str) -> str:
    label = "Inverter model" if lang == "en" else "Wechselrichtermodell"
    heading = "Inverter series" if lang == "en" else "Wechselrichterserie"
    lines = base.splitlines()
    body = "\n".join(lines[:2])
    note = inverter_condition(base)
    if len(lines) > 2 and not note:
        return ""
    if note:
        body += f"\n{note} (p. 6)"
    return f"| {label} | {heading} |\n| {model} | {series} |\n{body}"


def inverter_condition(base: str) -> str:
    """Keep the matrix's complete model-specific power limitation together."""
    lines = base.splitlines()[2:]
    if not lines:
        return ""
    condition = " ".join(lines)
    match = re.fullmatch(r"\*?3\.\s+(.+)", condition)
    return "*3: " + match.group(1) if match else ""


def iot_condition(row: str, page: int) -> str:
    number = {7: 1, 9: 3}.get(page)
    if number is None:
        return ""
    marker = f" √*{number} *{number} "
    if row.count(marker) != 1:
        return ""
    return f"*{number}: " + row.split(marker, 1)[1]


def iot_text(first: str, second: str) -> str:
    """Render each physically verified relation with its own complete note."""
    parts = []
    for row, page, number, device in (
        (first, 7, 1, "GM330"),
        (second, 9, 3, "SEC3000C"),
    ):
        condition = iot_condition(row, page)
        if not condition:
            return ""
        marker = f" √*{number} *{number} "
        parts.append(
            f"{device} (p. {page})\n{row.split(marker, 1)[0]} √*{number}\n"
            f"{condition} (p. {page})"
        )
    return "\n".join(parts)


def _axis_contains(evidence: Any, model: str, series: str) -> bool:
    if not isinstance(evidence, dict) or evidence.get("kind") != "series_axis":
        return False
    match = re.fullmatch(r"GW(\d+(?:\.\d+)?)K-(ET|ETR)-G10", model)
    if not match or evidence.get("family") != match.group(2):
        return False
    limits = {"ET (80-100kW)": ("ET", 80, 100), "ETR 80-125kW": ("ETR", 80, 125)}
    group = limits.get(series)
    if group is None or group[0] != match.group(2):
        return False
    if not Decimal(group[1]) <= Decimal(match.group(1)) <= Decimal(group[2]):
        return False
    members = evidence.get("models")
    return (
        isinstance(members, list)
        and sum(
            isinstance(item, dict) and item.get("text") == model for item in members
        )
        == 1
    )


def _document_current(
    evidence: Any,
    pid: int,
    products: Mapping[int, Mapping[str, Any]],
    documents: Mapping[str, Mapping[str, Any]],
) -> bool:
    if not isinstance(evidence, dict) or pid not in products:
        return False
    doc = documents.get(str(evidence.get("document_id", "")))
    return bool(
        doc
        and (str(doc.get("role", "")).strip() or str(doc.get("type", ""))).casefold()
        in {"datasheet", "datenblatt"}
        and doc.get("document_revision") == evidence.get("document_revision")
        and doc.get("blob_sha256") == evidence.get("source_sha256")
        and pid in doc.get("product_ids", [])
        and doc.get("document_id") in products[pid].get("documents", [])
        and products[pid].get("product_revision") == evidence.get("product_revision")
    )


def valid_inverter_scope(
    scope: Mapping[str, Any],
    ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    documents: Mapping[str, Mapping[str, Any]],
    *,
    sha: str,
    chunk_id: str,
    text: str,
    anchors: Mapping[str, Any] | None,
) -> bool:
    proof = scope.get("compatibility_inverter")
    if not isinstance(proof, dict) or not isinstance(anchors, Mapping):
        return False
    inverter, battery = proof.get("inverter_id"), proof.get("battery_id")
    model, series, lang = proof.get("model"), proof.get("series"), proof.get("lang")
    base, base_scope = proof.get("base_text"), proof.get("base_scope")
    page, base_id, axis_id = (
        proof.get("source_page"),
        proof.get("base_chunk_id"),
        proof.get("axis_chunk_id"),
    )
    support = proof.get("support_document")
    if (
        type(inverter) is not int
        or type(battery) is not int
        or inverter == battery
        or set(ids) != {inverter, battery}
        or set(scope.get("product_ids", [])) != set(ids)
        or inverter not in products
        or products[inverter].get("model") != model
        or not isinstance(base_scope, dict)
        or not isinstance(base, str)
        or not isinstance(base_id, str)
        or not isinstance(axis_id, str)
        or not isinstance(model, str)
        or not isinstance(series, str)
        or lang not in ("en", "de")
        or type(page) is not int
        or proof.get("source_sha256") != sha
        or not isinstance(support, dict)
        or not _document_current(support, inverter, products, documents)
    ):
        return False
    axis = anchors.get(physical_key(axis_id))
    if (
        not isinstance(axis, dict)
        or axis.get("source_sha256") != support.get("source_sha256")
        or not _axis_contains(axis, model, series)
        or not valid_compatibility_series(
            base_scope,
            [battery],
            products,
            sha=sha,
            chunk_id=base_id,
            text=base,
            anchors=anchors,
        )
    ):
        return False
    base_proof = base_scope.get("compatibility_series", {})
    if not isinstance(base_proof, dict) or base_proof.get("lang") != lang:
        return False
    cells = read_cells(base_proof.get("source_cells"))
    row, column = base_proof.get("source_row"), base_proof.get("source_column")
    native = (
        overview_row(cells, row, column, lang)
        if cells is not None and type(row) is int and type(column) is int
        else None
    )
    if native is None or native[1] != series:
        return False
    source_ids = scope.get("source_chunk_ids")
    if not isinstance(source_ids, list) or axis_id not in source_ids:
        return False
    rendered = inverter_text(model, series, base, lang)
    return (
        bool(rendered)
        and rendered == text
        and chunk_id == source_id(sha, page, "inverter-series", text)
    )


def valid_iot_scope(
    scope: Mapping[str, Any],
    ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    *,
    sha: str,
    chunk_id: str,
    text: str,
    anchors: Mapping[str, Any] | None,
) -> bool:
    proof = scope.get("compatibility_iot")
    if not isinstance(proof, dict) or not isinstance(anchors, Mapping):
        return False
    subjects = proof.get("subjects")
    if (
        not isinstance(subjects, list)
        or len(subjects) != 3
        or any(not isinstance(item, dict) for item in subjects)
        or {item.get("model") for item in subjects}
        != {"GM330", "SEC3000C", "GW125/261-ESA-LCN-G10"}
        or {item.get("product_id") for item in subjects} != set(ids)
        or set(scope.get("product_ids", [])) != set(ids)
        or any(
            type(item.get("product_id")) is not int
            or item["product_id"] not in products
            or products[item["product_id"]].get("model") != item.get("model")
            for item in subjects
        )
    ):
        return False
    first, second = proof.get("first_chunk_id"), proof.get("second_chunk_id")
    if (
        not isinstance(first, str)
        or not isinstance(second, str)
        or first == second
        or scope.get("source_chunk_ids") != [first, second]
    ):
        return False
    a, b = anchors.get(physical_key(first)), anchors.get(physical_key(second))
    if (
        not isinstance(a, dict)
        or not isinstance(b, dict)
        or a.get("source_sha256") != sha
        or b.get("source_sha256") != sha
        or a.get("kind") != "iot_matrix"
        or b.get("kind") != "iot_matrix"
        or a.get("source_page") != 7
        or b.get("source_page") != 9
        or not isinstance(a.get("source_text"), str)
        or not isinstance(b.get("source_text"), str)
        or not valid_physical_evidence(a, sha, first, a["source_text"])
        or not valid_physical_evidence(b, sha, second, b["source_text"])
    ):
        return False
    expected = iot_text(str(a.get("row_text", "")), str(b.get("row_text", "")))
    return (
        bool(expected)
        and expected == text
        and chunk_id == source_id(sha, 7, "iot", text)
    )
