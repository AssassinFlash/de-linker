"""Conditional claims instructions, bound to two current manufacturer originals.

A series match establishes only the provenance of a procedure. It never grants
coverage, a warranty period, a technical parameter or an individual entitlement.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from linker_genie.source_models import model_pattern
from linker_genie.table_projection import (
    cells_digest,
    display_cell_text,
    model_axis,
    read_cells,
    subtitle_above_title,
)

# Literal manufacturer cover vocabulary in the hosted GoodWe and SAJ originals.
# An ESA family name alone cannot cross its ranges.
FAMILY = re.compile(
    r"\b([a-z][a-z0-9]*)[-\s]+(?:series|serie|"
    r"three[ -]+phase\s+all[- ]in[- ]one\s+solution)\b",
    re.IGNORECASE,
)
POWER_RANGE = re.compile(
    r"(?<!\w)(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*kW\b",
    re.IGNORECASE,
)
# The two hosted STS covers use these immediately adjacent subtitle forms.
# Their manufacturer-original PDFs, not filenames or compatibility mentions,
# are the evidence for accepting an otherwise unqualified series title.
STS_COVER_SUBTITLE = re.compile(
    r"(?:Static[ \t]+Transfer[ \t]+Switch[ \t]+I[ \t]+"
    r"GW\d+(?:[.,]\d+)?K-STS-G\d+|"
    r"\d+(?:[.,]\d+)?kW/\d+(?:[.,]\d+)?kW[ \t]+I[ \t]+"
    r"Static[ \t]+Transfer[ \t]+Switch)",
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


def procedure_series_matches(cell: str, family: Sequence[str], model: str) -> bool:
    """Permit an explicit whole series only for a directly named model family.

    This weaker chain supports the manufacturer's first-contact procedure only.
    It is never used to infer a duration, performance guarantee or other term.
    Range-qualified families whose product code names another family (e.g. an
    ESA system containing an ETA inverter) continue to require the exact range.
    """
    if series_matches(cell, family):
        return True
    if len(family) != 3 or not family[1] or not family[2]:
        return False
    name = family[0]
    return bool(
        model.casefold().startswith(name.casefold() + "-")
        and re.fullmatch(rf"\s*{re.escape(name)}[-\s]+(?:series|serie)\s*", cell, re.I)
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


def terms_id(sha: str, page: int, model: str, original: str, text: str) -> str:
    digest = hashlib.sha256(f"{model}\0{original}\0{text}".encode()).hexdigest()[:16]
    return f"{sha[:12]}-p{page}-warranty-terms-{digest}"


def _series_token(cell: str, family: Sequence[str]) -> str | None:
    if len(family) != 3 or not series_matches(cell, family):
        return None
    name, lower, upper = family
    if lower and upper:
        pattern = (
            rf"\b{re.escape(name)}\s+(\d+(?:[.,]\d+)?)\s*[-–]\s*"
            r"(\d+(?:[.,]\d+)?)\s*k(?:W)?\b"
        )
        matches = [
            m.group(0)
            for m in re.finditer(pattern, cell, re.I)
            if tuple(str(Decimal(n.replace(",", ".")).normalize()) for n in m.groups())
            == (lower, upper)
        ]
    else:
        pattern = rf"\b{re.escape(name)}[-\s]+(?:series|serie)\b"
        matches = [m.group(0) for m in re.finditer(pattern, cell, re.I)]
    return matches[0] if len(matches) == 1 else None


def _text_source(source: Any, sha: str, ids: Sequence[str]) -> bool:
    if not isinstance(source, dict):
        return False
    text, cid, page = source.get("text"), source.get("chunk_id"), source.get("page")
    if not isinstance(text, str) or not text or type(page) is not int or page < 1:
        return False
    digest = hashlib.sha256(("text\0" + text).encode()).hexdigest()[:8]
    return cid == f"{sha[:12]}-p{page}-{digest}" and cid in ids


def exclusion_category(text: str) -> str:
    """Recognize explicit, complete examples in the manufacturer's exceptions."""
    if re.search(r"\b(?:disassembly|demontage)\b", text, re.I):
        return "modification"
    if re.search(r"\b(?:force majeure|höhere Gewalt)\b", text, re.I):
        return "force_majeure"
    if re.search(
        r"inverter damage.+not compatible|wechselrichterschaden.+nicht.+kompatibel",
        text,
        re.I,
    ):
        return "battery_compatibility"
    if re.search(
        r"reported.+(?:one|1) month.+first|gemeldet.+(?:eines Monats|1 Monat).+Auftreten",
        text,
        re.I,
    ):
        return "reporting"
    return ""


def valid_pdf_cover(anchor: Any, sha: str, chunk_id: str, text: str) -> bool:
    """Check a persisted physical title anchor against its source and text."""
    if not isinstance(anchor, dict) or anchor.get("kind") != "pdf_cover":
        return False
    start, end, size = (
        anchor.get("line_start"),
        anchor.get("line_end"),
        anchor.get("page_size"),
    )
    if (
        anchor.get("source_sha256") != sha
        or anchor.get("source_page") != 1
        or anchor.get("text") != text
        or chunk_id
        != f"{sha[:12]}-p1-pdf-cover-{hashlib.sha256(('text' + chr(0) + text).encode()).hexdigest()[:8]}"
        or type(start) is not int
        or type(end) is not int
        or start < 0
        or end - start != len(text)
        or not isinstance(size, (list, tuple))
        or len(size) != 2
        or any(
            type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in size
        )
    ):
        return False
    standalone_sts = (
        re.fullmatch(r"STS[ \t]+Series", text, re.IGNORECASE) is not None
        and "power" not in anchor
    )
    spans = []
    for name in ("family",) if standalone_sts else ("family", "power"):
        span = anchor.get(name)
        if not isinstance(span, dict):
            return False
        a, b, box = span.get("char_start"), span.get("char_end"), span.get("bbox")
        if (
            type(a) is not int
            or type(b) is not int
            or not start <= a < b <= end
            or span.get("text") != text[a - start : b - start]
            or not isinstance(box, (list, tuple))
            or len(box) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)
            or not (0 <= box[0] < box[2] <= size[0] and 0 <= box[1] < box[3] <= size[1])
        ):
            return False
        spans.append(span)
    if standalone_sts:
        family = spans[0]
        subtitle = anchor.get("subtitle")
        if not isinstance(subtitle, dict):
            return False
        sub_text, sub_start, sub_end, box = (
            subtitle.get("text"),
            subtitle.get("char_start"),
            subtitle.get("char_end"),
            subtitle.get("bbox"),
        )
        if (
            not isinstance(sub_text, str)
            or STS_COVER_SUBTITLE.fullmatch(sub_text) is None
            or type(sub_start) is not int
            or type(sub_end) is not int
            or not 1 <= sub_start - end <= 2  # PDF text line separator: LF or CRLF.
            or sub_end - sub_start != len(sub_text)
            or not isinstance(box, (list, tuple))
            or len(box) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)
            or not (0 <= box[0] < box[2] <= size[0] and 0 <= box[1] < box[3] <= size[1])
        ):
            return False
        family_box = family["bbox"]
        return (
            start == 0
            and family["char_start"] == start
            and family["char_end"] == end
            and family["text"] == text
            and family_signature(text) == ("sts", "", "")
            and subtitle_above_title(box, family_box)
        )
    family, power = spans
    return (
        family["char_end"] <= power["char_start"]
        and family["bbox"][2] < power["bbox"][0]
        and max(family["bbox"][1], power["bbox"][1])
        < min(family["bbox"][3], power["bbox"][3])
        and family_signature(text) is not None
    )


def _policy_fragments(
    row: Mapping[str, Any], sha: str, source_ids: Sequence[str]
) -> list[dict[str, Any]] | None:
    """Reconstruct the original pieces of a row without trusting their metadata."""
    fragments, source, number = row.get("fragments"), row.get("source"), row.get("row")
    if not isinstance(fragments, list) or not fragments or not isinstance(source, dict):
        return None
    page = source.get("page")
    if type(page) is not int or page < 1 or type(number) is not int:
        return None
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, fragment in enumerate(fragments):
        if not isinstance(fragment, dict):
            return None
        cid = source.get("chunk_id") if index == 0 else fragment.get("chunk_id")
        text = source.get("text") if index == 0 else fragment.get("text")
        rows = fragment.get("rows")
        if (
            not isinstance(cid, str)
            or cid in seen
            or cid not in source_ids
            or not isinstance(text, str)
            or not isinstance(rows, list)
            or any(type(item) is not int or item < 0 for item in rows)
            or number not in rows
            or len(rows) != len(text.splitlines())
            or cid
            != f"{sha[:12]}-p{page}-{hashlib.sha256(('table' + chr(0) + text).encode()).hexdigest()[:8]}"
        ):
            return None
        seen.add(cid)
        result.append({"chunk_id": cid, "text": text, "rows": rows})
    return result


def terms_text(
    value: Mapping[str, Any], source_ids: Sequence[str]
) -> tuple[str, list[dict[str, Any]]] | None:
    """Render a single native policy row and its inseparable source conditions.

    This deliberately requires the complete purchaser, start-date, territory,
    installation-date and exclusion language. A different policy layout stays
    unprepared rather than receiving guessed terms.
    """
    policy = value.get("policy")
    if not isinstance(policy, dict):
        return None
    row = policy.get("term_row")
    sources = policy.get("term_sources")
    sha, family = policy.get("blob_sha256"), value.get("family")
    if (
        not isinstance(sha, str)
        or not isinstance(row, dict)
        or not isinstance(sources, dict)
        or not isinstance(family, list)
    ):
        return None
    cells = read_cells(row.get("cells", []))
    number, source = row.get("row"), row.get("source")
    if (
        cells is None
        or type(number) is not int
        or number < 1
        or not isinstance(source, dict)
    ):
        return None
    row_text, row_id, row_page = (
        source.get("text"),
        source.get("chunk_id"),
        source.get("page"),
    )
    if not isinstance(row_text, str) or type(row_page) is not int or row_page < 1:
        return None
    digest = hashlib.sha256(("table\0" + row_text).encode()).hexdigest()[:8]
    if row_id != f"{sha[:12]}-p{row_page}-{digest}" or row_id not in source_ids:
        return None
    headers = [c for c in cells if c["column_header"] and c["row_start"] == 0]
    labels = {c["col_start"]: re.sub(r"\s+", "", c["text"]).casefold() for c in headers}
    if labels != {
        0: "warrantyperiod",
        1: "dateofmanufacture",
        2: "product",
        3: "series",
    } and labels != {
        0: "garantiezeitraum",
        1: "herstellungsdatum",
        2: "produktgruppe",
        3: "serien",
    }:
        return None
    selected = []
    selected_cells = []
    for col in range(4):
        matches = [
            c
            for c in cells
            if not c["column_header"]
            and c["col_start"] == col
            and c["col_end"] == col + 1
            and c["row_start"] <= number < c["row_end"]
        ]
        if len(matches) != 1:
            return None
        selected_cells.append(matches[0])
        selected.append(matches[0]["text"])
    period, production, _product, series = selected
    token = _series_token(series, family)
    if not token or not period or not production:
        return None

    # Compare complete original cells at their column boundaries. Substring
    # containment would, for example, accept "0 years" inside "10 years".
    # Long native rows can span chunks; join only the recorded pieces of this
    # row, whose identities and order are checked against the external anchor.
    def norm(text: str) -> str:
        return " ".join(text.split()).casefold()

    if "fragments" in row:
        fragments = _policy_fragments(row, sha, source_ids)
        if fragments is None:
            return None
        pieces = [
            line
            for fragment in fragments
            for line, line_row in zip(
                fragment["text"].splitlines(), fragment["rows"], strict=True
            )
            if line_row == number
        ]
        candidates = [" ".join(pieces)]
    else:
        # Existing complete-row proofs do not need any continuation metadata.
        candidates = row_text.splitlines()
    expected = [norm(cell) for cell in selected]
    if not any(
        len(fields := line.split("|")) == 6
        and not fields[0].strip()
        and not fields[-1].strip()
        and [norm(cell) for cell in fields[1:-1]] == expected
        for line in candidates
    ):
        return None
    kinds = ("overview", "start", "effective", "geography", "exclusions")
    if set(sources) != set(kinds):
        return None
    notes: list[dict[str, Any]] = []
    for kind in kinds:
        item = sources[kind]
        if not _text_source(item, sha, source_ids) or item.get("lang") not in {
            "en",
            "de",
        }:
            return None
        original = str(item["text"])
        low = original.casefold()
        if kind == "overview":
            ok = (
                "original purchaser" in low
                and "non-transferable" in low
                and "exclusions" in low
            ) or (
                "ursprünglichen käufer" in low
                and "nicht übertragbar" in low
                and "ausschlüssen" in low
            )
            match = re.search(
                r"This warranty only applies.+?exclusions and limitations set out below"
                r"|diese Garantie nur für.+?Ausschlüssen und Begrenzungen",
                original,
                re.I | re.S,
            )
            ok = ok and match is not None
            excerpt = match.group(0) if match else ""
        elif kind == "start":
            ok = (
                "earlier" in low
                and "first installed" in low
                and "production" in low
                and "months" in low
            ) or (
                "früheren" in low
                and "installiert" in low
                and "herstellungsdatum" in low
                and "monate" in low
            )
            excerpt = original
        elif kind == "effective":
            match = re.search(
                r"This Limited Warranty is effective|Diese beschränkte Garantie gilt",
                original,
                re.I,
            )
            ok = bool(match) and (
                ("installed" in low and "unless" in low and "newer" in low)
                or ("installiert" in low and "es sei denn" in low and "neuere" in low)
            )
            excerpt = original[match.start() :] if match else ""
            excerpt = re.split(
                r"(?i)\s+(?:Always check|Prüfen Sie immer)\b", excerpt, maxsplit=1
            )[0]
        elif kind == "geography":
            ok = (
                "authorized" in low
                and "installed" in low
                and "norway" in low
                and "switzerland" in low
            ) or (
                "autorisierten" in low
                and "installiert" in low
                and "norwegen" in low
                and "schweiz" in low
            )
            excerpt = original.split(". ", 1)[0].rstrip(".") + "."
        else:
            ok = (
                "manufacturing and material defects" in low
                and "normal wear and tear" in low
            ) or (
                "herstellungs- und materialfehler" in low
                and "normaler verschleiss" in low
            )
            lines = original.splitlines()
            if len(lines) < 3:
                return None
            # Preserve the complete exclusion up to its illustrative example;
            # the remainder of this long source line describes only that example.
            installation = re.split(
                r",\s*(?:e\.g\.|z\.\s*B\.)", lines[2], maxsplit=1, flags=re.I
            )[0]
            excerpt = "\n".join([*lines[:2], installation])
            if policy.get("additional_exclusion") is not None:
                excerpt = lines[0].split(". ", 1)[0].rstrip(".") + "."
        if not ok:
            return None
        notes.append(
            {
                "quote": " ".join(excerpt.split()),
                "page": item["page"],
                "chunk_id": item["chunk_id"],
                "lang": item["lang"],
            }
        )
    # The native cell and its source chunk remain unchanged in the proof.
    # Only restore a one-letter physical wrap when another verified source
    # passage on this same page contains the complete word.
    witness_texts = [
        item["text"]
        for item in sources.values()
        if isinstance(item, dict)
        and item.get("page") == row_page
        and isinstance(item.get("text"), str)
    ]
    production_display = display_cell_text(
        selected_cells[1], sha, row_page, witness_texts
    )
    notes.insert(
        0,
        {
            "quote": production_display,
            "page": row_page,
            "chunk_id": row_id,
            "lang": sources["overview"]["lang"],
        },
    )
    extra = policy.get("additional_exclusion")
    if extra is not None:
        if (
            not _text_source(extra, sha, source_ids)
            or extra.get("lang") != sources["overview"]["lang"]
            or extra.get("section")
            not in {"WARRANTY EXCEPTIONS", "AUSSCHLUSSBEDINGUNGEN"}
            or type(extra.get("line")) is not int
        ):
            return None
        lines = extra["text"].splitlines()
        line = extra["line"]
        if not 0 <= line < len(lines):
            return None
        excerpt = lines[line].strip()
        if (
            not re.match(r"^[A-ZÄÖÜ]", excerpt)
            or not excerpt.endswith(".")
            or len(excerpt.split()) < 4
            or not exclusion_category(excerpt)
        ):
            return None
        notes.append(
            {
                "quote": " ".join(excerpt.split()),
                "page": extra["page"],
                "chunk_id": extra["chunk_id"],
                "lang": extra["lang"],
            }
        )
    annotations = [
        {**item, "quote": f"*{i}: {item['quote']}"} for i, item in enumerate(notes, 1)
    ]
    text = "\n".join(
        [
            f"| Warranty / Garantie | {period} |",
            f"| Series / Serie | {token} |",
            *(f"{n['quote']} (p. {n['page']})" for n in annotations),
        ]
    )
    return text, annotations


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
    external_axis_anchors: Mapping[str, Any] | None = None,
) -> bool:
    """Recheck both document grants and the exact model/series/procedure chain."""
    value = scope.get("warranty_scope")
    basis = scope.get("basis")
    if not isinstance(value, dict) or basis not in {
        "warranty_procedure",
        "warranty_terms",
    }:
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
        or (basis == "warranty_procedure" and not claims_procedure(text))
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
    cover_pdf = sheet.get("cover_pdf")
    if "-pdf-cover-" in str(sheet.get("cover_chunk_id", "")) and cover_pdf is None:
        return False
    if cover_pdf is not None:
        cover_id = sheet.get("cover_chunk_id")
        if (
            not isinstance(cover_id, str)
            or not isinstance(external_axis_anchors, Mapping)
            or external_axis_anchors.get(cover_id) != cover_pdf
            or not valid_pdf_cover(
                cover_pdf,
                sheet["blob_sha256"],
                cover_id,
                str(cover_pdf.get("text", "")) if isinstance(cover_pdf, dict) else "",
            )
            or str(sheet.get("cover_quote", "")).strip() != cover_pdf["text"]
        ):
            return False
    if "cover_source_text" in sheet:
        cover_source = {
            "chunk_id": sheet.get("cover_chunk_id"),
            "page": 1,
            "text": sheet["cover_source_text"],
        }
        if (
            not _text_source(cover_source, sheet["blob_sha256"], source_ids)
            or str(sheet.get("cover_quote", "")).strip()
            not in sheet["cover_source_text"]
        ):
            return False
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
        or not (
            procedure_series_matches(
                str(policy.get("series_cell", "")), family, str(value["model"])
            )
            if basis == "warranty_procedure"
            else series_matches(str(policy.get("series_cell", "")), family)
        )
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
    if basis == "warranty_terms":
        row = policy.get("term_row")
        if not isinstance(row, dict) or not isinstance(external_axis_anchors, Mapping):
            return False
        table_id, source = row.get("table_anchor_id"), row.get("source")
        anchor = (
            external_axis_anchors.get(table_id) if isinstance(table_id, str) else None
        )
        cells = read_cells(row.get("cells", []))
        if (
            not isinstance(anchor, dict)
            or anchor.get("kind") != "policy_table"
            or table_id not in source_ids
            or not isinstance(source, dict)
            or not isinstance(source.get("text"), str)
            or type(row.get("row")) is not int
            or row["row"] < 1
            or cells is None
            or anchor.get("source_sha256") != sha
            or anchor.get("source_page") != source.get("page")
            or anchor.get("source_table") != row.get("source_table")
            or anchor.get("source_cells_sha256") != cells_digest(cells)
            or not isinstance(anchor.get("fragments"), list)
            or not any(
                isinstance(fragment, dict)
                and fragment.get("chunk_id") == source.get("chunk_id")
                and fragment.get("text") == source.get("text")
                and isinstance(fragment.get("rows"), list)
                and row.get("row") in fragment["rows"]
                for fragment in anchor.get("fragments", [])
            )
        ):
            return False
        if "fragments" in row:
            fragments = _policy_fragments(row, sha, source_ids)
            if fragments is None or fragments != [
                fragment
                for fragment in anchor["fragments"]
                if isinstance(fragment, dict)
                and isinstance(fragment.get("rows"), list)
                and row.get("row") in fragment["rows"]
            ]:
                return False
        else:
            # Legacy proofs can use a single complete row only. Without the
            # recorded line-to-row mapping, a multi-row fragment could borrow
            # an identical-looking value from its neighbour.
            matching = [
                fragment
                for fragment in anchor["fragments"]
                if isinstance(fragment, dict)
                and fragment.get("chunk_id") == source.get("chunk_id")
                and fragment.get("text") == source.get("text")
            ]
            if len(matching) != 1:
                return False
            rows = matching[0].get("rows")
            if (
                not isinstance(rows, list)
                or len(rows) != len(source["text"].splitlines())
                or rows.count(row.get("row")) != 1
                or any(
                    type(item) is not int or item not in {0, row["row"]}
                    for item in rows
                )
            ):
                return False
        term_sources = policy.get("term_sources")
        if not isinstance(term_sources, dict):
            return False
        originals = [*term_sources.values()]
        if policy.get("additional_exclusion") is not None:
            originals.append(policy["additional_exclusion"])
        for source in originals:
            if not isinstance(source, dict):
                return False
            source_id = source.get("chunk_id")
            if not isinstance(source_id, str):
                return False
            source_anchor = external_axis_anchors.get(source_id)
            if (
                not isinstance(source_anchor, dict)
                or source_anchor.get("kind") != "policy_text"
                or source_anchor.get("source_sha256") != sha
                or source_anchor.get("source_page") != source.get("page")
                or source_anchor.get("text") != source.get("text")
                or source_anchor.get("lang") != source.get("lang")
                or (
                    "section" in source
                    and source_anchor.get("section") != source["section"]
                )
            ):
                return False
        rendered = terms_text(value, source_ids)
        return (
            rendered is not None
            and rendered[0] == text
            and original in source_ids
            and policy["blob_sha256"] == sha
            and chunk_id
            == terms_id(sha, value["source_page"], str(value["model"]), original, text)
        )
    return (
        original in source_ids
        and policy["blob_sha256"] == sha
        and chunk_id
        == procedure_id(sha, value["source_page"], str(value["model"]), original, text)
    )
