"""Inventory: hosted PDFs deduplicated by sha256, described by the products' documents field."""

import json
from typing import Any

import pytest

from index.inventory import (
    build_documents,
    doc_type_of,
    document_kind_of,
    lang_of,
    product_links,
    product_of,
)


def media(media_id: int, name: str, size: int = 1000) -> dict[str, Any]:
    return {
        "id": media_id,
        "source_url": f"https://de-linker.com/wp-content/uploads/2026/10/{name}",
        "title": {"rendered": name.removesuffix(".pdf")},
        "modified_gmt": "2026-10-07T00:00:00",
        "media_details": {"filesize": size},
    }


def product(
    product_id: int,
    model: str,
    downloads: list[dict[str, Any]],
    de_titles: dict[int, str],
) -> dict[str, Any]:
    acf = {"downloads": downloads}
    acf_de = {
        "downloads": [
            {"download_file": file, "download_title": title}
            for file, title in de_titles.items()
        ]
    }
    return {
        "id": product_id,
        "status": "publish",
        "brands": [],
        "attributes": [
            {"name": "Brand", "options": ["GoodWe"]},
            {"name": "Model", "options": [model]},
        ],
        "meta_data": [
            {"key": "_tv_legacy_acf_json", "value": json.dumps(acf)},
            {"key": "_linker_de_acf_json", "value": json.dumps(acf_de)},
        ],
    }


def download(
    file: int, title: str, kind: str, role: str | None, lang: str
) -> dict[str, Any]:
    return {
        "download_file": file,
        "download_title": title,
        "download_type": kind,
        "download_role": role,
        "download_language": lang,
    }


def test_types_follow_the_documents_field_vocabulary() -> None:
    assert doc_type_of("Datasheet", "") == "datasheet"
    assert doc_type_of("Installation Manual", "") == "manual"
    assert doc_type_of("document", "compatibility_list") == "compatibility"
    assert doc_type_of("certificate", "certificate") == "certificate"
    assert doc_type_of("brochure", "brochure") == "other"
    assert doc_type_of("warranty", "") == "other"
    assert doc_type_of("Handbuch", "") == "manual"
    assert doc_type_of("Datenblatt", "") == "datasheet"
    assert doc_type_of("Kompatibilität", "") == "compatibility"
    assert doc_type_of("Dokument", "quick_guide") == "other"
    assert doc_type_of("Datenblatt", "user_manual") == "manual"
    assert document_kind_of("Garantie", "") == "warranty"
    assert document_kind_of("Zertifikat", "") == "certificate"


def test_languages_follow_the_documents_field_vocabulary() -> None:
    assert [
        lang_of(label)
        for label in ("EN", "DE", "ES", "MUL", "MULTI", "EN/DE", "DE/EN", "")
    ] == [
        "en",
        "de",
        "es",
        "mul",
        "mul",
        "mul",
        "mul",
        "und",
    ]


def test_unknown_woo_metadata_is_explicit_instead_of_inferred() -> None:
    with pytest.raises(ValueError, match="unknown Woo document language"):
        lang_of("not-a-language")
    with pytest.raises(ValueError, match="unknown Woo document purpose"):
        doc_type_of("not-a-document-purpose", "unknown-role")


def test_a_draft_without_attributes_takes_brand_and_model_from_its_meta() -> None:
    draft = {
        "id": 7,
        "status": "draft",
        "brands": [{"name": "Pylontech"}],
        "attributes": [],
        "meta_data": [{"key": "_delinker_model", "value": "Powercube-H1"}],
    }

    assert product_of(draft).brand == "Pylontech"
    assert product_of(draft).model == "Powercube-H1"


def test_byte_identical_attachments_become_one_document_described_by_its_products() -> (
    None
):
    items = [
        media(10, "GW_ET_Datasheet.pdf"),
        media(11, "goodwe-et-copy.pdf"),
        media(12, "S9.pdf"),
    ]
    shas = {10: "a" * 64, 11: "a" * 64, 12: "b" * 64}
    products = [
        product(
            1,
            "GW10K-ET",
            [download(10, "GoodWe ET datasheet", "Datasheet", None, "EN")],
            {10: "GoodWe ET Datenblatt"},
        ),
        product(
            2,
            "GW8K-ET",
            [download(11, "GoodWe ET datasheet", "datasheet", "datasheet", "EN")],
            {},
        ),
    ]

    documents = build_documents(items, shas, product_links(products))

    by_sha = {document.sha256: document for document in documents}
    et = by_sha["a" * 64]
    assert et.media_ids == [10, 11]
    assert et.urls[0].endswith("GW_ET_Datasheet.pdf")
    assert (et.title_en, et.title_de) == ("GoodWe ET datasheet", "GoodWe ET Datenblatt")
    assert (et.brands, et.models, et.product_ids) == (
        ["GoodWe"],
        ["GW10K-ET", "GW8K-ET"],
        [1, 2],
    )
    assert (et.doc_type, et.lang, et.linked) == ("datasheet", "en", True)
    unlinked = by_sha["b" * 64]
    assert (unlinked.title_en, unlinked.doc_type, unlinked.models, unlinked.linked) == (
        "S9",
        "other",
        [],
        False,
    )
