"""Validate individually reviewed, source-anchored manual passages.

The companion data identifies literal passages and the manufacturer's own
model declaration. A current Woo association is still required separately.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from linker_genie.manual_diagram import model_list_descriptor, physical_descriptor
from linker_genie.manual_diagram_records import DIAGRAMS
from linker_genie.manual_evidence_records import RECORDS
from linker_genie.source_models import model_pattern


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalized(value: str) -> str:
    # Docling sometimes wraps a single model immediately after its hyphen.
    return re.sub(r"(?<=-)\s+(?=[A-Za-z0-9])", "", value)


def subject_matches(record: Mapping[str, Any], model: str) -> bool:
    """Match only the manufacturer's role-specific declaration, not metadata."""
    quote = normalized(str(record["anchor_quote"]))
    if record["kind"] == "models":
        return bool(model and model_pattern(model).search(quote))
    if record["kind"] == "series":
        family = model.casefold().split("-", 1)[0]
        allowed = {str(value).casefold() for value in record["series"]}
        return (
            "-" in model
            and family in allowed
            and bool(
                re.search(
                    rf"(?<![\w./-]){re.escape(family)}(?:/[a-z0-9]+)?"
                    r"[-\s]+(?:series?|serie)\b",
                    quote,
                    re.IGNORECASE,
                )
            )
        )
    return False


def evidence_id(sha: str, page: int, model: str, source_id: str, text: str) -> str:
    digest = _digest(f"{model}\0{source_id}\0{text}")[:16]
    return f"{sha[:12]}-p{page}-manual-evidence-{digest}"


def valid_reviewed_manual(
    scope: Mapping[str, Any],
    product_ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    *,
    sha: str,
    chunk_id: str,
    text: str,
) -> bool:
    """Recheck the immutable source, the selected original text, and the model."""
    value = scope.get("reviewed_manual")
    if not isinstance(value, dict) or scope.get("basis") != "reviewed_manual":
        return False
    pid = value.get("product_id")
    if (
        type(pid) is not int
        or list(product_ids) != [pid]
        or scope.get("product_ids") != [pid]
        or pid not in products
        or value.get("model") != products[pid].get("model")
        or value.get("source_sha256") != sha
        or not isinstance(value.get("anchor_text"), str)
        or not isinstance(value.get("source_text"), str)
        or type(value.get("source_page")) is not int
        or value["source_page"] < 1
    ):
        return False
    for record in [*RECORDS, *DIAGRAMS]:
        if (
            record["sha256"] != sha
            or record["anchor_id"] != value.get("anchor_id")
            or record["source_id"] != value.get("source_id")
            or record["source_page"] != value["source_page"]
            or record["source_section"] != value.get("source_section")
            or record["anchor_sha256"] != _digest(value["anchor_text"])
            or record["source_sha256"] != _digest(value["source_text"])
            or record["anchor_quote"] not in value["anchor_text"]
            or record["excerpt"] != text
            or (
                (
                    value.get("physical_evidence") != physical_descriptor(record)
                    or value.get("physical_model_evidence")
                    != model_list_descriptor(record)
                )
                if "figure" in record
                else text not in value["source_text"]
                or value.get("physical_evidence") is not None
                or value.get("physical_model_evidence") is not None
            )
            or not subject_matches(record, str(value["model"]))
        ):
            continue
        required = {record["anchor_id"], record["source_id"]}
        reset = record.get("reviewed_reset")
        clearance = value.get("clearance")
        if reset:
            if (
                not isinstance(clearance, dict)
                or clearance.get("reset_id") != reset["id"]
                or not isinstance(clearance.get("reset_text"), str)
                or _digest(clearance["reset_text"]) != reset["text_sha256"]
                or not isinstance(clearance.get("cleared_texts"), list)
                or len(clearance["cleared_texts"]) != len(reset["cleared"])
            ):
                return False
            required.add(reset["id"])
            for item, source_text in zip(
                reset["cleared"], clearance["cleared_texts"], strict=True
            ):
                if (
                    not isinstance(source_text, str)
                    or _digest(source_text) != item["source_text_sha256"]
                ):
                    return False
                required.add(item["boundary"]["source_chunk_id"])
        elif clearance is not None:
            return False
        if not required.issubset(scope.get("source_chunk_ids", [])):
            return False
        return chunk_id == evidence_id(
            sha, value["source_page"], str(value["model"]), record["source_id"], text
        )
    return False
