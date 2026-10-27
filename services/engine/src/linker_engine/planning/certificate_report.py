"""Present only frozen Woo document associations; applicability stays open."""

from __future__ import annotations

from typing import cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from linker_engine.models import ReportRow, ReportSection

from .canonical import Object
from .report_copy import text


def certificate_sections(
    evidence: Object, locale: str, source_context: Object | None = None
) -> list[ReportSection]:
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
        inspections = evidence.get("inspections")
        inspection = (
            inspections.get(str(doc["document_id"]))
            if isinstance(inspections, dict)
            else None
        )
        if isinstance(inspection, dict):
            if inspection.get("status") == "read":
                for declaration in cast(list[Object], inspection["declarations"]):
                    rows.append(
                        ReportRow(
                            label=text(
                                "certificate_" + str(declaration["kind"]), locale
                            ),
                            value=str(declaration["value"]),
                            href=urlunsplit(
                                parts._replace(
                                    query=urlencode(query), fragment="page=1"
                                )
                            ),
                        )
                    )
            else:
                rows.append(
                    ReportRow(
                        label=text("certificate_declarations", locale),
                        value=text(
                            "certificate_inspection_limit"
                            if inspection.get("status") == "resource_limit"
                            else "certificate_inspection_unavailable",
                            locale,
                        ),
                    )
                )
            annex = inspection.get("annex")
            if isinstance(annex, dict):
                rows.append(
                    ReportRow(
                        label=text("certificate_annex", locale),
                        value=text("certificate_annex_unverified", locale).format(
                            body=annex["cover_pages_stated"],
                            annex=annex["annex_pages_stated"],
                            retained=annex["retained_pdf_pages"],
                        ),
                    )
                )
    return [
        ReportSection(
            id="product-certificates",
            title=text("certificate_title", locale),
            paragraphs=[text("certificate_scope", locale)]
            + (
                [text("certificate_inspection_scope", locale)]
                if evidence.get("inspections")
                else []
            )
            + ([] if rows else [text("certificate_empty", locale)]),
            rows=rows,
        )
    ] + _condition_sections(evidence, locale, source_context)


def _document_url(document: Object, page: int | None = None) -> str:
    parts = urlsplit(str(document["url"]))
    query = dict(parse_qsl(parts.query))
    query["linker_document_sha256"] = str(document["blob_sha256"])
    return urlunsplit(
        parts._replace(
            query=urlencode(query),
            fragment=f"page={page}" if page is not None else parts.fragment,
        )
    )


def _device_reference(reference: Object, locale: str) -> str:
    if reference["kind"] == "plant_controller":
        return text("certificate_condition_controller", locale).format(
            identity=reference["group_id"]
        )
    selection = (
        text("certificate_condition_single", locale)
        if reference["kind"] == "single"
        else text("certificate_condition_unit", locale).format(
            identity=reference["unit_id"]
        )
    )
    return (
        selection
        + " · "
        + text("certificate_condition_" + str(reference["role"]), locale)
    )


def _condition_sections(
    evidence: Object, locale: str, source_context: Object | None
) -> list[ReportSection]:
    """Render the frozen review without comparing, fetching or changing sources."""
    if "condition_review" not in evidence:
        return []
    review = evidence["condition_review"]
    if (
        not isinstance(review, dict)
        or review.get("schema_version") != 1
        or review.get("method") != "literal_device_conditions_v1"
        or review.get("applicability") != "not_assessed"
    ):
        raise ValueError("device condition review cannot assert applicability")
    products = {
        row["product_id"]: row for row in cast(list[Object], evidence["products"])
    }
    documents = {
        row["document_id"]: row for row in cast(list[Object], evidence["documents"])
    }
    sections = [
        ReportSection(
            id="certificate-device-conditions",
            title=text("certificate_condition_title", locale),
            paragraphs=[text("certificate_condition_scope", locale)]
            + (
                [text("certificate_condition_recorded_scope", locale)]
                if source_context is not None
                else []
            ),
            rows=(
                [
                    ReportRow(
                        label=text("certificate_condition_source_run", locale),
                        value=str(source_context["run_id"]),
                    ),
                    ReportRow(
                        label=text("certificate_condition_source_revision", locale),
                        value=str(source_context["revision"]),
                    ),
                ]
                + (
                    [
                        ReportRow(
                            label=text(
                                "certificate_condition_source_candidate", locale
                            ),
                            value=str(source_context["candidate_id"]),
                        )
                    ]
                    if source_context.get("candidate_id") is not None
                    else []
                )
                if source_context is not None
                else []
            ),
        )
    ]

    def value(raw: object) -> str:
        return text("not_specified", locale) if raw is None else str(raw)

    def row(label: str, raw: object, href: str | None = None) -> ReportRow:
        return ReportRow(
            label=text("certificate_condition_" + label, locale),
            value=value(raw),
            href=href,
        )

    for index, device in enumerate(cast(list[Object], review["devices"])):
        product = products.get(device["product_id"])
        if (
            product is None
            or product["product_revision"] != device["product_revision"]
            or product["model"] != device["woo_model"]
        ):
            raise ValueError("device condition review product source changed")
        reference = _device_reference(cast(Object, device["selection_ref"]), locale)
        identity = cast(Object, device["model_identity"])
        if (
            identity.get("declared_value") != device["declared_model"]
            or identity.get("selected_woo_value") != device["woo_model"]
        ):
            raise ValueError("device model identity differs from its recorded values")
        sections.append(
            ReportSection(
                id=f"certificate-device-{index}",
                title=f"{reference} · {device['woo_model']}",
                rows=[
                    row("reference", reference),
                    row("product", device["product_id"]),
                    row("product_revision", device["product_revision"]),
                    row("woo_model", device["woo_model"]),
                    row("declared_model", device["declared_model"]),
                    row(
                        "identity",
                        text(
                            "certificate_condition_identity_" + str(identity["status"]),
                            locale,
                        ),
                    ),
                    row("declared_firmware", device["declared_firmware"]),
                    row("source_note", device["source_note"]),
                ],
                paragraphs=(
                    []
                    if device["documents"]
                    else [text("certificate_condition_device_empty", locale)]
                ),
            )
        )
        for document_index, compared in enumerate(
            cast(list[Object], device["documents"])
        ):
            document = documents.get(compared["document_id"])
            if (
                document is None
                or device["product_id"] not in cast(list[int], document["product_ids"])
                or compared.get("applicability") != "not_assessed"
                or any(
                    compared.get(key) != document[key]
                    for key in ("document_revision", "blob_sha256")
                )
            ):
                raise ValueError("device condition review document source changed")
            rows = [
                ReportRow(
                    label=text("source", locale),
                    value=str(document["title"]),
                    href=_document_url(document),
                ),
                row("document", document["document_id"]),
                ReportRow(label="SHA-256", value=str(document["blob_sha256"])),
                ReportRow(
                    label=text("certificate_revision", locale),
                    value=str(document["document_revision"]),
                ),
            ]
            for field in ("model", "firmware"):
                comparison = cast(Object, compared[field])
                status = str(comparison["status"])
                status_key = field + "_unresolved" if status == "unresolved" else status
                page = cast(int | None, comparison.get("page"))
                label = text("certificate_condition_" + field + "_comparison", locale)
                if page is not None:
                    label += f" · {text('page', locale)} {page}"
                rows.extend(
                    [
                        ReportRow(
                            label=label,
                            value=text("certificate_condition_" + status_key, locale),
                            href=_document_url(document, page),
                        ),
                        row("compared_" + field, comparison["compared_value"]),
                    ]
                )
                original: object
                if field == "model":
                    rows.append(
                        row(
                            "basis",
                            text(
                                "certificate_condition_"
                                + str(comparison["comparison_basis"]),
                                locale,
                            ),
                        )
                    )
                    stated = comparison["declared_values"]
                    original = (
                        " · ".join(cast(list[str], stated))
                        if isinstance(stated, list)
                        else None
                    )
                else:
                    original = comparison["declared_value"]
                rows.extend(
                    [
                        ReportRow(
                            label=text(
                                "certificate_"
                                + ("models" if field == "model" else field),
                                locale,
                            ),
                            value=value(original),
                            href=_document_url(document, page),
                        ),
                        row(
                            "detail",
                            text(
                                "certificate_condition_" + str(comparison["reason"]),
                                locale,
                            ),
                        ),
                    ]
                )
            annex = cast(Object, compared["annex"])
            if annex.get("status") != "unresolved":
                raise ValueError("device condition review cannot approve an annex")
            annex_source = annex.get("source")
            rows.append(
                ReportRow(
                    label=text("certificate_annex", locale),
                    value=(
                        text("certificate_annex_unverified", locale).format(
                            body=annex_source["cover_pages_stated"],
                            annex=annex_source["annex_pages_stated"],
                            retained=annex_source["retained_pdf_pages"],
                        )
                        if isinstance(annex_source, dict)
                        else text("certificate_condition_not_assessed", locale)
                    ),
                )
            )
            sections.append(
                ReportSection(
                    id=f"certificate-device-{index}-document-{document_index}",
                    title=f"{reference} · {device['woo_model']} · {document['title']}",
                    rows=rows,
                )
            )
    sections.append(
        ReportSection(
            id="certificate-device-open-checks",
            title=text("certificate_condition_open_title", locale),
            rows=[
                row(str(obligation), text("certificate_condition_not_assessed", locale))
                for obligation in cast(list[str], review["remaining_obligations"])
            ],
        )
    )
    return sections
