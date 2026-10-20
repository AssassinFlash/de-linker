"""Stock status a customer may be told (docs/specs/69-stock.md).

The words are the product page's, reused as the whole sentence: "In stock" /
"Currently unavailable", and "Auf Lager" / "Derzeit nicht verfügbar". A
quantity is never one of them. `asks` is the questions that mean this status.
"available", "unavailable", "verfügbar" and "ausverkauft" are stock asks when
a product is named. "stock status" and "Lagerstatus" are stock asks either
way. Delivery words, including "lieferbar", stay on the logistics route
(route._LOGISTICS) and are not stock asks.
"""

from __future__ import annotations

import re

# ProductView's badge pair (spec 69). EN and DE are the page's own lines.
STATUS = {
    "en": {True: "In stock", False: "Currently unavailable"},
    "de": {True: "Auf Lager", False: "Derzeit nicht verfügbar"},
}

# Status words that mean stock with or without a named product. "stock
# status" and "Lagerstatus" are the deciding sentence's own words: a
# customer who answers with them is still asking about stock. Delivery
# words, including "lieferbar", are not here.
_EXPLICIT = re.compile(
    r"\b(?:in stock|out of stock|stock status|availability|auf lager|"
    r"lagerstatus|vorr(?:ä|ae|a)tig|lagerbestand)\b",
    re.IGNORECASE,
)
# Stock only when a product is named. "Is 3-phase available?" and
# "Is 3-phase unavailable?" name no product and stay where Jev put them.
# "unavailable" does not contain the word "available".
_AVAILABLE = re.compile(
    r"\b(?:available|unavailable|verf(?:ü|ue|u)gbar|ausverkauft)\b",
    re.IGNORECASE,
)


def language(locale: str) -> str:
    """`de` for a German locale, otherwise `en`."""
    return "de" if locale.startswith("de") else "en"


def phrase(locale: str, in_stock: bool) -> str:
    """The page's status sentence for this locale and flag."""
    return STATUS[language(locale)][in_stock]


def explicit(message: str) -> bool:
    """Whether `message` uses a status word that is stock with no product.

    "stock status" and "Lagerstatus" count. "available", "unavailable",
    "verfügbar" and "ausverkauft" do not: those are stock only when a
    product is named.
    """
    return _EXPLICIT.search(message) is not None


def asks(message: str) -> bool:
    """Whether `message` asks for a product's stock status.

    Delivery words are not stock. "available", "unavailable", "verfügbar"
    and "ausverkauft" are, and so are "stock status" and "Lagerstatus".
    """
    return explicit(message) or _AVAILABLE.search(message) is not None
