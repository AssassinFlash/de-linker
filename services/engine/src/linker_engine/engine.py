"""The loaded engine both design paths share: the products of the feed, the
compatibility contract and the yield source, plus the pieces that turn
products into answer objects.

Residential and commercial designs read the same products and the same
compatibility contract, so the product reference, the documents and the
release a manufacturer pairing carries live here rather than in either path.
"""

from __future__ import annotations

from dataclasses import dataclass

from .compatibility import Compatibility, DocumentRef, PairResult
from .models import Doc, Locale, ProductRef, Release
from .products import Product, Products, PvModule
from .pvgis import Pvgis


@dataclass(frozen=True)
class Engine:
    """The loaded products, compatibility contract and yield source."""

    products: Products
    compatibility: Compatibility
    pvgis: Pvgis


def ref(product: Product) -> ProductRef:
    """The product identity an answer carries, independent of the language."""
    return ProductRef(
        id=product.id,
        sku=product.sku,
        model=product.model,
        brand=product.brand,
        device_class=product.device_class,
    )


def docs(items: tuple[DocumentRef, ...]) -> list[Doc]:
    return [Doc(url=d.url, page=d.page) for d in items]


def release(pair: PairResult, locale: Locale) -> Release:
    return Release(
        verdict=pair.verdict,
        conditions=[condition.get(locale) for condition in pair.conditions],
        documents=docs(pair.documents),
    )


def documents_of(product: Product | PvModule, kind: str, locale: Locale) -> list[Doc]:
    """A product's documents of one kind as answer objects, in the report's
    language when the product data carries it (the feed marks each document's
    language; a language the product data has no document for keeps what there
    is, so an answer never loses its evidence)."""
    found = [document for document in product.documents if document.type == kind]
    matching = [document for document in found if document.lang == locale]
    return [Doc(url=document.url) for document in matching or found]
