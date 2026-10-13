"""The decision of 69-seopress-schema.py: which schema rows get drafted.

The script's effect — a product page carrying one Product node — is checked
against a running instance (t110, `verify` and tools/checks/product-schema.py).
What a unit test can pin down is the decision itself: a published custom
template whose body is a Product node is retired, a draft of the same body is
already done, and a Product template stored as any other type is refused
rather than guessed at.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def load() -> ModuleType:
    """The script is a file, not an importable module name."""
    path = Path(__file__).resolve().parent.parent / "69-seopress-schema.py"
    spec = importlib.util.spec_from_file_location("seopress_schema", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = load()


def row(
    *,
    status: str = "publish",
    product: bool = True,
    template: str = "custom",
    title: str = "TerraVolt Product Entity Schema",
    row_id: int = 978,
) -> dict[str, object]:
    return {
        "id": row_id,
        "title": title,
        "status": status,
        "type": template,
        "product": product,
    }


def test_a_published_product_template_is_the_one_that_goes() -> None:
    """The stored product row is retired; the article row beside it is not."""
    listed = [
        row(),
        row(
            product=False, template="articles", title="Blog Article Schema", row_id=979
        ),
    ]

    found = script.stale(listed)

    assert found == [listed[0]]


def test_a_draft_product_template_is_already_retired() -> None:
    """Second run: the plugin's query reads published rows, so a draft is done."""
    assert script.stale([row(status="draft")]) == []


def test_a_product_template_of_an_unknown_type_is_refused() -> None:
    """Drafting a shape this migration has not seen would be a guess."""
    with pytest.raises(SystemExit, match="nothing is written"):
        script.refuse_unknown([row(template="products")])


def test_the_known_custom_template_is_not_refused() -> None:
    """The row this migration exists for is the stored custom body."""
    script.refuse_unknown([row(template="custom")])
