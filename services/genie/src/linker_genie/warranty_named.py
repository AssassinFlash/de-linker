"""Explicit-model warranty policy: source-bound text and consumer proof.

The manufacturer specifies models on the same policy line as a territory and
period. This format never transfers a claim to a family, an adjacent region or
another revision. All supporting passages remain independently anchored.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from linker_genie.table_projection import native_chunk_id_matches
from linker_genie.warranty_named_de import EXCLUSIONS

FORMAT = "explicit_model_europe_policy"
_PERIOD = re.compile(
    r"^(?P<period>\d+\s+years?)\s+\*\s+limited warranty for EV Charger including:\s*"
    r"(?P<models>[^;]+);\s*\(For Europe, excluding UK\)\s*$",
    re.I,
)
_POLICY_ROW = re.compile(
    r"^\d+\s+years?\s+\*\s+limited warranty for EV Charger including:\s*"
    r"[^;]+;\s*\(For (?:Europe(?:, excluding UK)?|UK)\)\s*$",
    re.I,
)
_MODEL = re.compile(r"[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)+")
_START = re.compile(
    r"starting from the earlier one of following two dates:\s*"
    r"The date on which the product was first installed\.\s*"
    r"(?P<production>\d+\s+months? after the date of production\.)",
    re.I,
)
_COVERAGE = re.compile(
    r"Unless a special/unique agreement exists between GOODWE and the customer,\s*"
    r"the GOODWE limited warranty\s+covers only the cost of hardware material "
    r"required to get the device functioning again\.",
    re.I,
)
_EFFECTIVE = re.compile(
    r"This limited warranty applies to the product which is sold and installed "
    r"after [A-Za-z]+ \d{4}\.",
    re.I,
)
LEGAL = "However, this limited warranty shall neither exclude nor limit any of your legal (statutory) rights under the applicable national laws."
LOCAL = (
    "In some countries/districts, end users may receive an additional warranty promise "
    "(should be at least equivalent to the manufacturer's warranty) which is provided "
    "by GOODWE's local distributor; should any claims arise in this respect, please "
    "direct them to the local distributor."
)
LATEST = (
    "Please note this GOODWE limited warranty statement may NOT be the latest version, "
    "please refer to the latest version of the GOODWE limited warranty by visiting our global website"
)
LATEST_QUOTE = "this GOODWE limited warranty statement may NOT be the latest version"
EXCLUSION_INTRO = "The following circumstances may cause device defects, but are NOT covered by GOODWE's limited warranty."


def is_named_policy_overview(text: str) -> bool:
    """Recognize a literal policy row, without granting any model."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if line.casefold().startswith("starting from the earlier")
        ),
        -1,
    )
    introduction = re.compile(
        r"^[A-Za-z]+ Technologies Co\.,Ltd, \(hereinafter referred to as [A-Za-z]+\) "
        r"warrants that, subject to the exclusions and limitations set out below, "
        r"the EV Charger and accessory product [A-Za-z]+ provides shall be in good "
        r"working order during the period of$",
        re.I,
    )
    accessory = re.compile(
        r"^\d+\s+years?\s+limited warranty for accessory products [A-Za-z0-9]+;$",
        re.I,
    )
    return bool(
        start > 1
        and introduction.fullmatch(lines[0])
        and all(
            _POLICY_ROW.fullmatch(line) or accessory.fullmatch(line)
            for line in lines[1:start]
        )
        and sum(_PERIOD.fullmatch(line) is not None for line in lines[1:start]) == 1
        and _START.fullmatch("\n".join(lines[start:]))
    )


def _source(
    item: Any, sha: str, ids: Sequence[str], *, page: int, section: str
) -> bool:
    if not isinstance(item, dict):
        return False
    cid, text = item.get("chunk_id"), item.get("text")
    return bool(
        isinstance(cid, str)
        and isinstance(text, str)
        and item.get("page") == page
        and item.get("section") == section
        and item.get("lang") == "en"
        and cid in ids
        and native_chunk_id_matches(sha, page, "text", text, cid)
    )


def render_named_terms(
    value: Mapping[str, Any], source_ids: Sequence[str]
) -> tuple[str, list[dict[str, Any]]] | None:
    """Rebuild the period and original conditions from complete source passages."""
    policy, model = value.get("policy"), value.get("model")
    if (
        not isinstance(policy, dict)
        or policy.get("format") != FORMAT
        or not isinstance(model, str)
    ):
        return None
    sha, sources = policy.get("blob_sha256"), policy.get("sources")
    if not isinstance(sha, str) or not isinstance(sources, dict):
        return None
    expected = {
        "overview": (1, "OVERVIEW"),
        "coverage": (1, "WHAT IS COVERED AND NOT COVERED?"),
        "geography": (3, "GEOGRAPHICAL SCOPE"),
        "effective": (3, "LIMITATION OF GOODWE's LIABILITY"),
        "legal": (3, "LIMITATION OF GOODWE's LIABILITY"),
        "local": (3, "LIMITATION OF GOODWE's LIABILITY"),
        "latest": (3, "LIMITATION OF GOODWE's LIABILITY"),
    }
    if set(sources) != {*expected, "exclusions"} or not all(
        _source(sources[name], sha, source_ids, page=page, section=section)
        for name, (page, section) in expected.items()
    ):
        return None
    exclusions = sources["exclusions"]
    if (
        not isinstance(exclusions, list)
        or not exclusions
        or any(
            not _source(item, sha, source_ids, page=2, section="WARRANTY EXCEPTIONS")
            for item in exclusions
        )
        or len({item["chunk_id"] for item in exclusions}) != len(exclusions)
    ):
        return None
    overview = sources["overview"]["text"]
    if not is_named_policy_overview(overview):
        return None
    row = next(
        _PERIOD.fullmatch(line.strip())
        for line in overview.splitlines()
        if _PERIOD.fullmatch(line.strip())
    )
    assert row is not None
    models = re.split(r"\s*,\s*|\s+and\s+", row["models"].strip(), flags=re.I)
    if (
        not models
        or any(_MODEL.fullmatch(name) is None for name in models)
        or len({name.casefold() for name in models}) != len(models)
        or model.casefold() not in {name.casefold() for name in models}
    ):
        return None
    start = _START.search(overview)
    coverage = _COVERAGE.search(sources["coverage"]["text"])
    effective = _EFFECTIVE.search(sources["effective"]["text"])
    geography = sources["geography"]["text"].strip()
    geo_lower = geography.casefold()
    if (
        start is None
        or coverage is None
        or effective is None
        or "6 months" not in start.group("production")
        or "sold and installed after November 2022" not in effective.group(0)
        or LEGAL not in sources["legal"]["text"]
        or LOCAL not in sources["local"]["text"]
        or LATEST not in sources["latest"]["text"]
        or not all(
            term in geo_lower
            for term in (
                "authorized by goodwe",
                "installed",
                "european union",
                "norway",
                "switzerland",
                "written confirmation/approval",
            )
        )
    ):
        return None
    purchaser = "channels authorized by GOODWE"
    if purchaser not in geography:
        return None
    source_lines = [
        (item, index, line.strip())
        for item in exclusions
        for index, line in enumerate(item["text"].splitlines())
        if line.strip()
    ]
    if sum(line == EXCLUSION_INTRO for _, _, line in source_lines) != 1 or [
        line for _, _, line in source_lines if line != EXCLUSION_INTRO
    ] != list(EXCLUSIONS):
        return None
    selected_id = policy.get("exclusion_source_id")
    index = policy.get("exclusion_index")
    chosen = [
        (item, line)
        for item, line_number, line in source_lines
        if item["chunk_id"] == selected_id
        and line_number == index
        and line in EXCLUSIONS
    ]
    if type(index) is not int or len(chosen) != 1:
        return None
    selected, exclusion = chosen[0]
    source_quotes = [
        (sources["overview"], "6 months"),
        (sources["geography"], purchaser),
        (sources["overview"], start.group(0)),
        (sources["effective"], "sold and installed after November 2022"),
        (sources["geography"], geography),
        (sources["coverage"], coverage.group(0)),
        (selected, exclusion),
        (sources["overview"], "For Europe, excluding UK"),
        (sources["legal"], LEGAL),
        (sources["local"], LOCAL),
        (sources["latest"], LATEST_QUOTE),
    ]
    notes = [
        {
            "quote": f"*{i}: {' '.join(quote.split())}",
            "page": source["page"],
            "chunk_id": source["chunk_id"],
            "lang": "en",
        }
        for i, (source, quote) in enumerate(source_quotes, 1)
    ]
    text = "\n".join(
        [
            f"| Warranty / Garantie | {row['period']} |",
            f"| Model / Modell | {model} |",
            *(f"{note['quote']} (p. {note['page']})" for note in notes),
        ]
    )
    return text, notes


def valid_named_scope(
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
    """Revalidate current attachment, exact model and every original paragraph."""
    value = scope.get("warranty_scope")
    if not isinstance(value, dict) or scope.get("basis") != "warranty_terms":
        return False
    pid, policy = value.get("product_id"), value.get("policy")
    if (
        type(pid) is not int
        or list(product_ids) != [pid]
        or scope.get("product_ids") != [pid]
        or pid not in products
        or value.get("conditional") is not True
        or value.get("model") != products[pid].get("model")
        or value.get("source_sha256") != sha
        or value.get("source_page") != 1
        or value.get("text_sha256") != hashlib.sha256(text.encode()).hexdigest()
        or not isinstance(policy, dict)
        or policy.get("format") != FORMAT
        or policy.get("blob_sha256") != sha
        or not isinstance(anchors, Mapping)
    ):
        return False
    document_id = policy.get("document_id")
    document = documents.get(document_id, "") if isinstance(document_id, str) else ""
    if (
        not isinstance(document, Mapping)
        or document.get("document_revision") != policy.get("document_revision")
        or document.get("blob_sha256") != sha
        or pid not in document.get("product_ids", [])
        or document_id not in products[pid].get("documents", [])
        or str(document.get("role") or document.get("type", "")).casefold()
        not in {"warranty", "garantie"}
    ):
        return False
    sources = policy.get("sources")
    if not isinstance(sources, dict):
        return False
    all_sources = [
        source
        for value in sources.values()
        for source in (value if isinstance(value, list) else [value])
    ]
    for source in all_sources:
        if not isinstance(source, dict):
            return False
        cid = source.get("chunk_id")
        anchor = anchors.get(cid) if isinstance(cid, str) else None
        if (
            not isinstance(anchor, dict)
            or anchor.get("kind") != "policy_text"
            or anchor.get("source_sha256") != sha
            or any(anchor.get(k) != source.get(k) for k in ("text", "lang", "section"))
            or anchor.get("source_page") != source.get("page")
        ):
            return False
    overview = sources.get("overview")
    if not isinstance(overview, dict) or value.get("source_chunk_id") != overview.get(
        "chunk_id"
    ):
        return False
    brand = str(products[pid].get("brand", ""))
    if (
        not brand
        or re.search(rf"\b{re.escape(brand)}\b", str(overview.get("text", "")), re.I)
        is None
    ):
        return False
    ids = scope.get("source_chunk_ids", [])
    if not isinstance(ids, list):
        return False
    rendered = render_named_terms(value, ids)
    if rendered is None or rendered[0] != text:
        return False
    digest = hashlib.sha256(
        f"{value['model']}\0{overview['chunk_id']}\0{text}".encode()
    ).hexdigest()[:16]
    return chunk_id == f"{sha[:12]}-p1-warranty-terms-{digest}"
