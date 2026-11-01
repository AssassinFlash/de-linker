"""Reviewed ESA IoT rows and exact manufacturer model-axis authorization."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

IOT = "6f33b8361fe25fa2798c424fd30c2601036a56212b9e62a312e6aadb060b8b3d"
MANUAL = "67a7f715ca9db734edba1b4f15b50d1a29c866b172ffd1909759e0abc66c8d2a"
MODEL = "GW10K-ETA-G20"
P6 = "6f33b8361fe2-p6-d2bb94e7"
P9 = "6f33b8361fe2-p9-7a4f8c43"
P13 = "6f33b8361fe2-p13-7680004c"
AXIS = "67a7f715ca9d-p4-b97f02f3"
MANUAL_METER = "67a7f715ca9d-p35-e2f45a66"
SOURCES = {
    AXIS: (
        MANUAL,
        4,
        "92294632929e364efebef3439de0bed4221fa78e76bbe8c1bec814fd489faf7b",
    ),
    MANUAL_METER: (
        MANUAL,
        35,
        "1c0075f911cd87dbae4a3c254ec8a881393ab0c84a60cd33b1c7a7b37ba2eb52",
    ),
}
# SHA-bound PDFium offsets, bounding boxes and the complete unmodified row.
ROW_DIGESTS = {
    6: "6e2c0e1bfadafab58c088e518517c6cb3a7057eb6e3df32cc10ea3517d67c671",
    9: "dca5fa43bc0f41a38f82d8df52f2086872e2b287d740e1c3f166ab84991ef29a",
    13: "966ed985895912514fa89907126e487edc327f871de6cbd0be08ab3ff8bb0526",
}
# Numbered markers are compiler labels required by the qualification contract;
# the manual's meter condition and the HEMS row are not source footnotes.
IOT_9 = (
    "*1: ARM≥03, DSP≥01; BMS≥06, DCDC≥ 08; DCDC-08 must be bound to "
    "BMS-06 or above versions. It cannot be upgraded to BMS-06 alone or "
    "DCDC-08 alone. BMS: 410-02167-06, DCDC: 410-04081-08"
)
IOT_13 = (
    "*2: ESA 5-30K Three-phase parallel : 4+4 In total ≤4 √ √ DSP：2 ARM：4 "
    "Ezmanager：04 WIFILAN 2.0 Module（Cyber Security version）≥05"
)
METER_CT = "*1: GMK330: CT is not replaceable; CT ratio: 120A:40mA."
METER_PARALLEL = (
    "*2: If more than 2 Inverters are paralleled, or the wire diameter or measuring range "
    "of the standard CT does not meet the total current requirements of the on-site "
    "parallel system, use the GM330 Smart Meter."
)


def row_key(cid: str) -> str:
    return "esa-row:" + cid


def source_key(cid: str) -> str:
    return "esa-source:" + cid


def source_anchors(
    rows: Iterable[tuple[str, str, int, str, str]],
) -> dict[str, dict[str, Any]]:
    anchors = {}
    for cid, sha, page, kind, text in rows:
        expected = SOURCES.get(cid)
        if (
            expected
            and kind == "table"
            and (sha, page, hashlib.sha256(text.encode()).hexdigest()) == expected
        ):
            anchors[source_key(cid)] = {
                "source_sha256": sha,
                "source_page": page,
                "text": text,
            }
    return anchors


def valid_row(item: Any, sha: str, cid: str, text: str) -> bool:
    if not isinstance(item, dict) or item.get("kind") != "esa_iot_row":
        return False
    page = item.get("source_page")
    expected = ROW_DIGESTS.get(page) if type(page) is int else None
    if (
        not expected
        or sha != IOT
        or item.get("source_sha256") != sha
        or item.get("target_chunk_id") != cid
        or item.get("source_text") != text
    ):
        return False
    encoded = json.dumps(
        item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode()).hexdigest() == expected


def rendered(device: str) -> str:
    if device == "GMK330":
        return (
            f"{MODEL} is an ESA 5–30 kW model (manual p. 4). The IoT list "
            "marks GMK330, 3CT 120A:40mA, for ESA 5–30K (p. 6).\n"
            f"{METER_CT} (p. 35)\n{METER_PARALLEL} (p. 35)"
        )
    if device == "EzManager3000":
        return (
            f"{MODEL} is an ESA 5–30 kW model (manual p. 4). The IoT list "
            "marks EzManager3000 for ESA 5–30K (p. 9).\n"
            f"{IOT_9} (p. 9)\nFor the HEMS parallel configuration:\n"
            f"{IOT_13} (p. 13)"
        )
    return ""


def chunk_id(text: str, page: int) -> str:
    return (
        f"{IOT[:12]}-p{page}-esa-iot-" + hashlib.sha256(text.encode()).hexdigest()[:16]
    )


def valid_scope(
    scope: Mapping[str, Any],
    ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    documents: Mapping[str, Mapping[str, Any]],
    *,
    sha: str,
    cid: str,
    text: str,
    anchors: Mapping[str, Any] | None,
) -> bool:
    proof = scope.get("compatibility_esa")
    if not isinstance(proof, dict) or not isinstance(anchors, Mapping) or sha != IOT:
        return False
    device_id, inverter_id = proof.get("device_id"), proof.get("inverter_id")
    if (
        type(device_id) is not int
        or type(inverter_id) is not int
        or device_id == inverter_id
    ):
        return False
    device, inverter = products.get(device_id), products.get(inverter_id)
    support = proof.get("support_document")
    if not device or not inverter or not isinstance(support, dict):
        return False
    model = device.get("model")
    if (
        model not in {"GMK330", "EzManager3000"}
        or inverter.get("model") != MODEL
        or set(ids) != {device_id}
        or set(scope.get("product_ids", [])) != {device_id}
    ):
        return False
    main_ids = scope.get("document_ids")
    if not isinstance(main_ids, list) or len(main_ids) != 1:
        return False
    main = documents.get(str(main_ids[0]))
    if (
        not main
        or main.get("blob_sha256") != IOT
        or device_id not in main.get("product_ids", [])
        or main_ids[0] not in device.get("documents", [])
    ):
        return False
    doc = documents.get(str(support.get("document_id", "")))
    if not doc or (
        str(doc.get("role", "")).strip() or str(doc.get("type", "")).strip()
    ).casefold() not in {"manual", "user_manual"}:
        return False
    if (
        doc.get("blob_sha256") != MANUAL
        or doc.get("document_revision") != support.get("document_revision")
        or inverter.get("product_revision") != support.get("product_revision")
        or inverter_id not in doc.get("product_ids", [])
        or doc.get("document_id") not in inverter.get("documents", [])
    ):
        return False
    pages = [(P6, 6)] if model == "GMK330" else [(P9, 9), (P13, 13)]
    needed = (
        [x[0] for x in pages] + [AXIS] + ([MANUAL_METER] if model == "GMK330" else [])
    )
    if scope.get("source_chunk_ids") != needed:
        return False
    for source in (x for x in needed if x in SOURCES):
        anchor = anchors.get(source_key(source))
        if not isinstance(anchor, dict):
            return False
        source_text = anchor.get("text")
        source_page = anchor.get("source_page")
        if (
            not isinstance(source_text, str)
            or type(source_page) is not int
            or not source_anchors(
                [
                    (
                        source,
                        str(anchor.get("source_sha256", "")),
                        source_page,
                        "table",
                        source_text,
                    )
                ]
            )
        ):
            return False
    for source, page in pages:
        row = anchors.get(row_key(source))
        if (
            not isinstance(row, dict)
            or row.get("source_page") != page
            or not valid_row(row, sha, source, str(row.get("source_text", "")))
        ):
            return False
    expected = rendered(str(model))
    return text == expected and cid == chunk_id(expected, pages[0][1])
