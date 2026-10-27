"""Read literal cover declarations from the exact Woo-associated PDF bytes.

This is a rebuildable source projection, never a certificate registry or an
applicability decision. Unrecognised layouts and incomplete annexes remain
explicit. No firmware, standard edition or model suffix is inferred.
"""

from __future__ import annotations

import io
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .canonical import Json, Object, digest
from .errors import ProductEvidenceChanged

_STANDARD = re.compile(
    r"(?<!\w)(?:VDE-AR-N\s+\d{4}|DIN\s+VDE\s+V\s+\d{4}-\d+|EN\s+50549-\d+)"
    r"(?:\s*[:/]\s*\d+(?:[.-]\d+)*)?"
    r"(?:\s*\+\s*(?:Corr\.\d+|A\d+)(?:\s*:\s*\d+(?:-\d+)*)?)*",
    re.I,
)


def _block(text: str, start: str, end: str) -> str | None:
    match = re.search(start + r"\s*(.*?)\s*(?=" + end + r")", text, re.S | re.I)
    return match[1].strip() if match and match[1].strip() else None


def _standard_field(text: str) -> str:
    guide = _block(
        text,
        r"VDE\s+application\s+guide\s*/",
        r"Certification\s+programme\s*/",
    )
    if guide is not None:
        return guide
    label = re.search(r"Tested\s+acc\.\s*to\s*:\s*", text, re.I)
    if label is None:
        return ""
    lines: list[str] = []
    for line in text[label.end() :].splitlines():
        if not line.strip():
            continue
        # These covers list one or more references on consecutive lines.
        # Remarks/footer prose, even if it mentions a standard, is not a field.
        if not _STANDARD.search(line) or _STANDARD.sub("", line).strip(" ,;\t"):
            break
        lines.append(line)
    return "\n".join(lines)


def inspect_certificate(content: bytes, document: Object) -> Object:
    """Only fields with a recognised literal label receive an extraction.

    The complete original is retained by the caller. Reading the cover does
    not establish that the remaining pages, test reports or conditions pass.
    """
    if digest(content) != document["blob_sha256"]:
        raise ProductEvidenceChanged("certificate bytes differ from the Woo source")
    result: Object = {
        "schema_version": 1,
        "method": "literal_certificate_cover_v1",
        "document_id": document["document_id"],
        "document_revision": document["document_revision"],
        "blob_sha256": document["blob_sha256"],
        "applicability": "not_assessed",
        "declarations": [],
        "annex": None,
    }
    try:
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted or not reader.pages:
            return {**result, "status": "unreadable"}
        # Resource policy, not an engineering or certification limit. Only
        # the labelled cover is parsed; the complete file remains the source.
        text = reader.pages[0].extract_text() or ""
        if len(text) > 100_000:
            return {**result, "status": "resource_limit"}
        page_count = len(reader.pages)
        declarations: list[Json] = []
        models = _block(
            text,
            r"Type\s+Designation\s*:",
            r"Firmware\s+Version\s*:",
        ) or _block(text, r"Models\s*/\s*Modelle", r"Technical\s+Data\s*/")
        firmware = re.search(
            r"(?:Firmware\s+Version\s*:|Software\s+version\s*/\s*Softwareversion)"
            r"[ \t]*([^\r\n]+)",
            text,
            re.I,
        )
        if models:
            declarations.append({"kind": "models", "value": models, "page": 1})
        if firmware and firmware[1].strip():
            declarations.append(
                {"kind": "firmware", "value": firmware[1].strip(), "page": 1}
            )
        # Retain printed references, including amendments and their actual
        # notation. A short /11.18 is not rewritten into a claimed new edition.
        references: dict[str, str] = {}
        for reference in _STANDARD.finditer(_standard_field(text)):
            written = reference[0].strip()
            references.setdefault(re.sub(r"\s+", "", written).casefold(), written)
        if references:
            declarations.append(
                {
                    "kind": "standards",
                    "value": "\n".join(references.values()),
                    "page": 1,
                }
            )
        annex = re.search(
            r"certificate\s+is\s+comprised\s+of\s+(\d+)\s+pages?\s+and\s+an\s+Annex\s+of\s+(\d+)\s+pages",
            text,
            re.I,
        )
        if annex:
            # Embedded files and extra PDF pages are not proof that a named
            # annex/revision is complete. Record counts; leave verification open.
            result["annex"] = {
                "status": "not_verified",
                "cover_pages_stated": int(annex[1]),
                "annex_pages_stated": int(annex[2]),
                "retained_pdf_pages": page_count,
                "quote": annex[0],
                "page": 1,
            }
        result.update(
            status="read" if declarations else "unrecognised",
            retained_pdf_pages=page_count,
            declarations=declarations,
        )
        # An inspectable fingerprint belongs to the derived projection, not
        # the product or document's publication identity.
        result["cover_text_sha256"] = digest(text.encode())
        return result
    except (PdfReadError, ValueError, TypeError, KeyError, IndexError, OSError):
        return {**result, "status": "unreadable"}
