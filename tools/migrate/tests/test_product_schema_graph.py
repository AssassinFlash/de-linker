"""The product audit reads product, series and site identity from a single graph."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "checks" / "product-schema.py"
spec = importlib.util.spec_from_file_location("product_schema", SCRIPT)
assert spec is not None and spec.loader is not None
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def html(*blocks: object) -> str:
    return "".join(
        f'<script type="application/ld+json">{json.dumps(block)}</script>'
        for block in blocks
    )


def test_reads_website_name_from_graph() -> None:
    with patch.object(
        checker,
        "fetch",
        return_value=(200, html({"@graph": [{"@type": "WebSite", "name": "Linker"}]})),
    ):
        assert checker.site_name("https://example.org") == "Linker"


def test_product_and_group_must_share_one_graph_without_site_organization() -> None:
    url = "https://example.org/product/test/"
    model = {"sku": "S", "name": "Model", "url": url, "@id": url + "#product"}
    group = {
        "@type": "ProductGroup",
        "@id": "#series",
        "productGroupID": "#series",
        "hasVariant": [model],
    }
    product = {
        "@type": "Product",
        **model,
        "brand": {"@type": "Brand", "name": "Manufacturer"},
        "inProductGroupWithID": "#series",
        "isVariantOf": {"@id": "#series"},
    }
    for body, valid in (
        (html({"@graph": [product, group]}), True),
        (html(product, group), False),
        (html({"@graph": [product, group, {"@type": "Organization"}]}), False),
        (html({"@graph": [product, product, group]}), False),
        (html({"@graph": [product, {**group, "url": url}]}), False),
    ):
        with patch.object(checker, "fetch", return_value=(200, body)):
            passed, message = checker.check(
                "https://example.org", "/product/test/", "Linker"
            )
        assert passed == valid, message
