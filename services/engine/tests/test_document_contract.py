"""Explicit native Woo document metadata, rather than a permissive schema."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from conftest import publication_feed, publication_manifest

from linker_engine.compatibility import Compatibility
from linker_engine.engine import Engine, documents_of
from linker_engine.models import Locale
from linker_engine.products import Document, FeedError, Products
from linker_engine.publication import Publication
from linker_engine.pvgis import Pvgis

FIXTURES = Path(__file__).parent / "fixtures"


def native_shape() -> dict[str, Any]:
    sample: dict[str, Any] = json.loads(
        (FIXTURES / "woo-document-shape.json").read_text()
    )
    return sample


def native_feed() -> dict[str, Any]:
    feed: dict[str, Any] = json.loads((FIXTURES / "feed.json").read_text())
    sample = native_shape()
    feed["products"][0]["documents"] = [sample["document"]]
    first = next(iter(feed["products"][0]["figures"].values()))
    first["citation"] = sample["citation"]
    return feed


def test_explicit_alias_and_source_label_survive_native_loader() -> None:
    sample = native_shape()
    product = Products.from_feed(native_feed()).products[0]
    assert product.documents[0].aliases == sample["document"]["aliases"]
    assert product.documents[0].citation_aliases == ["engineering-datasheet-en.pdf"]
    citation = next(iter(product.figures.values())).citation
    assert citation.doc == sample["citation"]["doc"]
    assert citation.url == sample["citation"]["url"] and citation.page == 2


@pytest.mark.parametrize("language", ["en", "de", "es", "mul", "und"])
def test_producer_canonical_languages_are_explicitly_accepted(language: str) -> None:
    feed = native_feed()
    feed["products"][0]["documents"][0]["lang"] = language
    assert Products.from_feed(feed).products[0].documents[0].lang == language


@pytest.mark.parametrize(
    "language", ["EN", "DE", "MUL", "", "EN/DE", "MULTI", "DE/EN", "unknown"]
)
def test_unprojected_or_unknown_language_is_not_silently_guessed(language: str) -> None:
    feed = native_feed()
    feed["products"][0]["documents"][0]["lang"] = language
    with pytest.raises(FeedError, match="lang"):
        Products.from_feed(feed)


@pytest.mark.parametrize(
    "field",
    [
        "foreign_alias",
        "unlisted_doc_key",
        "unlisted_citation_key",
        "nontext_source_label",
    ],
)
def test_recognized_metadata_does_not_open_arbitrary_properties(field: str) -> None:
    feed = native_feed()
    if field == "foreign_alias":
        feed["products"][0]["documents"][0]["aliases"].append(
            "https://other.invalid/same.pdf"
        )
    elif field == "unlisted_doc_key":
        feed["products"][0]["documents"][0]["unreviewed_source"] = True
    else:
        citation = next(iter(feed["products"][0]["figures"].values()))["citation"]
        if field == "unlisted_citation_key":
            citation["unreviewed_source"] = True
        else:
            citation["doc"] = ["not a label"]
    with pytest.raises(FeedError):
        Products.from_feed(feed)


@pytest.mark.parametrize("locale", ["en", "de"])
def test_report_selects_exact_language_before_multilingual_or_unknown(
    products: Products, locale: Locale
) -> None:
    sample = native_shape()["document"]
    variants = [
        Document(**{**sample, "lang": language, "url": sample["url"] + "#" + language})
        for language in native_shape()["canonical_languages"]
    ]
    product = replace(products.products[0], documents=tuple(variants))
    assert [doc.url for doc in documents_of(product, "datasheet", locale)] == [
        sample["url"] + "#" + locale
    ]
    product = replace(
        product, documents=tuple(d for d in variants if d.lang in {"mul", "und"})
    )
    assert [doc.url for doc in documents_of(product, "datasheet", locale)] == [
        sample["url"] + "#mul",
        sample["url"] + "#und",
    ]


def test_citation_alias_requires_its_current_document_permission(
    monkeypatch: pytest.MonkeyPatch, pvgis: Pvgis
) -> None:
    contract = json.loads((FIXTURES / "compatibility.json").read_text())
    feed = publication_feed(json.loads((FIXTURES / "feed.json").read_text()), contract)
    product = next(
        p for p in feed["products"] if p["device_class"] == "inverters" and p["figures"]
    )
    citation = next(iter(product["figures"].values()))["citation"]
    document = next(d for d in product["documents"] if d["url"] == citation["url"])
    alias = "https://de-linker.com/wp-content/uploads/fixtures/authorized-alias.pdf"
    document["aliases"] = [document["url"], alias]
    citation.update(url=alias, doc="original-datasheet-name.pdf")
    engine = Engine(Products.from_feed(feed), Compatibility(contract), pvgis)
    publication = Publication(feed)
    assert product["id"] in publication.view(engine).engine.products.by_id
    current = copy.deepcopy(publication_manifest(feed))
    # A source filename and matching content cannot grant a missing URL alias.
    next(
        d for d in current["documents"] if d["document_id"] == document["document_id"]
    )["aliases"] = []
    monkeypatch.setattr(Publication, "read", lambda self: current)
    assert product["id"] not in publication.view(engine).engine.products.by_id
