"""The reviewed HS3 variant statement, bounded by three original documents.

The datasheet's W/G notation is not itself an exact certificate subject. The
manufacturer separately names W and G in the EU declaration; only a conditional
statement, requiring the actual nameplate and module count, may be offered.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

CERTIFICATE = "43d6efd869b4c66f485eb40f602e369d95a47665f33fb6330607a99884012479"
DATASHEET = "b4a653fd2c0bdbff01337165df0567eb71488634eaa1c1420070fc170526c1c3"
MANUAL = "2c1dd5c1e2f7efd96eba4f24aa3804ee135936ac90bcccfd1a681f2188868f46"
# These are the complete original native chunks, not snippets or generated text.
# The final declaration chunk preserves the X range and the stated directives.
SOURCES: dict[str, tuple[str, int, str]] = {
    "43d6efd869b4-p1-4adb8123": (
        CERTIFICATE,
        1,
        "e36bfd5a2675b99c0a36468d9081009655ce1ce288bfb1da81ef441ac32a5a92",
    ),
    "43d6efd869b4-p1-2679bdaa": (
        CERTIFICATE,
        1,
        "f682a053fc72feb5e8a647fe1c17e1add10f468af06ae24978e84a8ffc18c4e5",
    ),
    "43d6efd869b4-p1-ce289ee7": (
        CERTIFICATE,
        1,
        "2927127492d116215fd85992f60957b260fd578df693bd50153253a53ee1d1c1",
    ),
    "b4a653fd2c0b-p2-a2df8f70": (
        DATASHEET,
        2,
        "acc0ce1692fa29d6e89159cb43613febabf9124c2209cfa383c682044388412a",
    ),
    "2c1dd5c1e2f7-p18-576d01a7": (
        MANUAL,
        18,
        "9a9619df42d1b958a29f573a6677207fad49e220961d42cf5b1316e3a8a669a2",
    ),
}
CERT_HEADER = "43d6efd869b4-p1-4adb8123"
CERT_MODELS = "43d6efd869b4-p1-2679bdaa"
CERT_END = "43d6efd869b4-p1-ce289ee7"
DATA_MODELS = "b4a653fd2c0b-p2-a2df8f70"
MANUAL_MODEL = "2c1dd5c1e2f7-p18-576d01a7"
_MODEL = re.compile(r"HS3-(?:5|6|8|10|12)K-T2-W/G-PX\Z")
# PDFium located each visible header on page 2 of this exact original PDF.
# These are digests of the character offsets and page-relative bounding boxes,
# rounded to hundredths of a point; the original table supplies the column.
DATA_AXIS = {
    "HS3-5K-T2-W/G-PX": (
        1,
        "7c1b140b21f81692da81537d97d223c9875f63cba6ff3673e25addde32e4cad3",
    ),
    "HS3-6K-T2-W/G-PX": (
        2,
        "fd5e1a8aa50e4089359862528839502b4070213125ef51d91e6870f1c450d9e2",
    ),
    "HS3-8K-T2-W/G-PX": (
        3,
        "84be41d031ce2bfee1d5c0ade10be6f0197e79a1f2025544012deafb36e33a94",
    ),
    "HS3-10K-T2-W/G-PX": (
        4,
        "366431aaa37caa5f47c7e1b2a2249551ee2c041baa24fb8ed2c689f4cbc5c710",
    ),
    "HS3-12K-T2-W/G-PX": (
        5,
        "bea46542e6ec417e66411a17fb5405f72639eaf75f18809c70436450fb6cebd1",
    ),
}


def normalized_axis_span(span: Any) -> dict[str, Any] | None:
    """Preserve the reviewed source offsets and physical page coordinates."""
    if not isinstance(span, dict) or set(span) != {
        "text",
        "bbox",
        "char_start",
        "char_end",
        "page",
        "source_sha256",
        "page_size",
    }:
        return None
    boxes = (span.get("bbox"), span.get("page_size"))
    if any(
        not isinstance(box, (list, tuple))
        or len(box) != length
        or any(
            type(value) not in (int, float) or not math.isfinite(value) for value in box
        )
        for box, length in zip(boxes, (4, 2), strict=True)
    ):
        return None
    return {
        **span,
        "bbox": [round(value, 2) for value in span["bbox"]],
        "page_size": [round(value, 2) for value in span["page_size"]],
    }


def axis_span_valid(model: str, axis: Any) -> bool:
    expected = DATA_AXIS.get(model)
    if (
        expected is None
        or not isinstance(axis, dict)
        or set(axis) != {"column", "span"}
    ):
        return False
    span = normalized_axis_span(axis["span"])
    return bool(
        type(axis["column"]) is int
        and axis["column"] == expected[0]
        and span is not None
        and span["text"] == model
        and span["page"] == 2
        and span["source_sha256"] == DATASHEET
        and hashlib.sha256(
            json.dumps(span, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        == expected[1]
    )


def datasheet_axis(
    model: str, cells: Sequence[Mapping[str, Any]]
) -> dict[str, Any] | None:
    """Select the exact original header column and visible PDF text span."""
    expected = DATA_AXIS.get(model)
    if expected is None:
        return None
    found = []
    for cell in cells:
        if (
            cell.get("row_start") != 0
            or cell.get("row_end") != 1
            or cell.get("col_start") != expected[0]
            or cell.get("col_end") != expected[0] + 1
            or cell.get("column_header") is not True
        ):
            continue
        for span in cell.get("model_spans", []):
            axis = {"column": expected[0], "span": normalized_axis_span(span)}
            if axis_span_valid(model, axis):
                found.append(axis)
    return found[0] if len(found) == 1 else None


def has_purpose(document: Mapping[str, Any], expected: str) -> bool:
    """The explicit Woo role wins over its fallback document type."""
    role, label = document.get("role", ""), document.get("type", "")
    if not isinstance(role, str) or not isinstance(label, str):
        return False
    return (role.strip() or label.strip()).casefold() == expected


def variants(model: str) -> tuple[str, str] | None:
    """Only the five exactly reviewed composite labels, never generic slash expansion."""
    if _MODEL.fullmatch(model) is None:
        return None
    return model.replace("-W/G-", "-W-"), model.replace("-W/G-", "-G-")


def hs3_anchor_key(chunk_id: str) -> str:
    """Keep whole-text HS3 evidence separate from native table anchors."""
    return f"hs3:{chunk_id}"


def hs3_anchors(
    rows: Iterable[tuple[str, str, int, str, str]],
) -> dict[str, dict[str, Any]]:
    """Verify each independently retained original chunk, including its whole text."""
    found: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    seen: set[str] = set()
    for cid, sha, page, kind, text in rows:
        expected = SOURCES.get(cid)
        if expected is None:
            continue
        if cid in seen:
            duplicates.add(cid)
            continue
        seen.add(cid)
        if (
            kind == ("table" if cid == DATA_MODELS else "text")
            and (sha, page) == expected[:2]
            and hashlib.sha256(text.encode()).hexdigest() == expected[2]
        ):
            found[hs3_anchor_key(cid)] = {
                "source_sha256": sha,
                "page": page,
                "kind": kind,
                "text": text,
            }
    for cid in duplicates:
        found.pop(hs3_anchor_key(cid), None)
    return found


def source_text(model: str) -> str | None:
    """A statement of the individually listed subjects and the required check."""
    pair = variants(model)
    if pair is None:
        return None
    w, g = pair
    return (
        f"The EU declaration names {w} and {g}. "
        "X denotes the number of battery modules: 1, 2, 3, 4, 5, 6, 7 or 8. "
        "Check the W or G designation on the nameplate and confirm the installed module count."
    )


def evidence_id(model: str, did: str, text: str) -> str:
    digest = hashlib.sha256(f"{model}\0{did}\0{text}".encode()).hexdigest()[:16]
    return f"{CERTIFICATE[:12]}-p1-hs3-conditional-{digest}"


def conditional_answers(cid: str, model: str) -> dict[str, str]:
    """Server-authorized EN/DE answer; range values are filled from source figures."""
    pair = variants(model)
    if pair is None:
        return {}
    w, g = pair
    first, last = f"{{fact:{cid}.n1}}", f"{{fact:{cid}.n8}}"
    return {
        "en": (
            f"The EU declaration lists {w} and {g}. X is the number of battery modules "
            f"({first} to {last}). Check the W or G designation on the nameplate "
            "and confirm the installed module count."
        ),
        "de": (
            f"Die EU-Konformitätserklärung führt {w} und {g} auf. X steht für die Anzahl "
            f"der Batteriemodule ({first} bis {last}). Lesen Sie die W- oder G-Variante "
            "am Typenschild ab und prüfen Sie die Anzahl der installierten Module."
        ),
    }


def valid_hs3_scope(
    scope: Mapping[str, Any],
    product_ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    documents: Mapping[str, Mapping[str, Any]],
    *,
    sha: str,
    chunk_id: str,
    text: str,
    anchors: Mapping[str, Any] | None,
) -> bool:
    """Recheck all three current associations and all five retained original chunks."""
    proof = scope.get("hs3_conditional_certificate")
    if scope.get("basis") != "hs3_conditional_certificate" or not isinstance(
        proof, dict
    ):
        return False
    pid = proof.get("product_id")
    product = products.get(pid) if type(pid) is int else None
    model = str(product.get("model", "")) if product else ""
    pair = variants(model)
    source_docs = proof.get("source_documents")
    if (
        product is None
        or pair is None
        or list(product_ids) != [pid]
        or scope.get("product_ids") != [pid]
        or proof.get("model") != model
        or proof.get("product_revision") != product.get("product_revision")
        or sha != CERTIFICATE
        or not isinstance(source_docs, dict)
        or set(source_docs) != {"certificate", "datasheet", "manual"}
        or not isinstance(anchors, Mapping)
        or not {hs3_anchor_key(cid) for cid in SOURCES}.issubset(anchors)
        or not set(SOURCES).issubset(scope.get("source_chunk_ids", []))
    ):
        return False
    for role, expected_sha in (
        ("certificate", CERTIFICATE),
        ("datasheet", DATASHEET),
        ("manual", MANUAL),
    ):
        ref = source_docs[role]
        if not isinstance(ref, dict) or not isinstance(ref.get("document_id"), str):
            return False
        doc = documents.get(ref["document_id"])
        if (
            doc is None
            or ref.get("blob_sha256") != expected_sha
            or doc.get("blob_sha256") != expected_sha
            or ref.get("document_revision") != doc.get("document_revision")
            or not has_purpose(doc, role)
            or pid not in doc.get("product_ids", [])
            or ref["document_id"] not in product.get("documents", [])
        ):
            return False
    cert_id = source_docs["certificate"]["document_id"]
    if scope.get("document_ids") != [cert_id] or not axis_span_valid(
        model, proof.get("datasheet_axis")
    ):
        return False
    expected_rows = []
    for cid in SOURCES:
        value = anchors.get(hs3_anchor_key(cid))
        if not isinstance(value, dict):
            return False
        source_sha = value.get("source_sha256")
        source_page = value.get("page")
        source_kind = value.get("kind")
        source_body = value.get("text")
        if (
            not isinstance(source_sha, str)
            or type(source_page) is not int
            or not isinstance(source_kind, str)
            or not isinstance(source_body, str)
        ):
            return False
        expected_rows.append((cid, source_sha, source_page, source_kind, source_body))
    # Do not trust metadata merely because it was copied into the proof.
    if len(hs3_anchors(expected_rows)) != len(SOURCES):
        return False
    header = anchors[hs3_anchor_key(CERT_HEADER)]["text"]
    declaration = (
        anchors[hs3_anchor_key(CERT_MODELS)]["text"]
        + "\n"
        + anchors[hs3_anchor_key(CERT_END)]["text"]
    )
    data = anchors[hs3_anchor_key(DATA_MODELS)]["text"]
    manual = anchors[hs3_anchor_key(MANUAL_MODEL)]["text"]
    if (
        "We Guangzhou Sanjing Electric Co., Ltd." not in header
        or "We declare under our own responsibility" not in header
        or model not in data
        or any(
            not re.search(r"(?<![\w/-])" + re.escape(v) + r"(?![\w/-])", declaration)
            for v in pair
        )
        or "(X=1,2,3,4,5,6,7,8)" not in declaration
        or "observe the following directives and regulations" not in declaration
        or "HS3 - xK - T2 - a - b X - c" not in manual
        or "W: With a built-in AIO3 module." not in manual
        or "G: With a built-in 4G modules." not in manual
        or "P: Professional model" not in manual
        or "X: Quantity of the battery modules, ranging from 1 to 8." not in manual
    ):
        return False
    rendered = source_text(model)
    return rendered == text and chunk_id == evidence_id(model, cert_id, text)
