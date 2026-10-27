"""Present only frozen Woo document associations; applicability stays open."""

from __future__ import annotations

from typing import cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from linker_engine.models import ReportRow, ReportSection

from .canonical import Object
from .report_copy import text


def certificate_sections(evidence: Object, locale: str) -> list[ReportSection]:
    if (
        evidence.get("scope") != "associated_product_documents"
        or evidence.get("applicability") != "not_assessed"
    ):
        raise ValueError(
            "certificate document associations cannot assert applicability"
        )
    products = {
        cast(int, p["product_id"]): p for p in cast(list[Object], evidence["products"])
    }
    rows: list[ReportRow] = []
    for doc in cast(list[Object], evidence["documents"]):
        names = [
            str(products[identity]["model"])
            for identity in cast(list[int], doc["product_ids"])
        ]
        parts = urlsplit(str(doc["url"]))
        # Native DocumentAccess.VERSION_QUERY_VAR; ordinary and recorded-source
        # downloads share current permission and reject different file bytes.
        query = dict(parse_qsl(parts.query))
        query["linker_document_sha256"] = str(doc["blob_sha256"])
        url = urlunsplit(parts._replace(query=urlencode(query)))
        rows.extend(
            [
                ReportRow(label=" · ".join(names), value=str(doc["title"]), href=url),
                ReportRow(label="SHA-256", value=str(doc["blob_sha256"])),
                ReportRow(
                    label=text("certificate_revision", locale),
                    value=str(doc["document_revision"]),
                ),
            ]
        )
    return [
        ReportSection(
            id="product-certificates",
            title=text("certificate_title", locale),
            paragraphs=[text("certificate_scope", locale)]
            + ([] if rows else [text("certificate_empty", locale)]),
            rows=rows,
        )
    ]
