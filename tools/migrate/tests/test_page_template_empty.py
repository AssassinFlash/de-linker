"""The decision of page-template-empty.py: which pages get the empty template.

The script's effect — the theme page title gone, the page's own heading still
there — is checked against a running instance (t110, 2026-10-12). What a unit
test can pin down is the decision itself: only a page the live site renders
through page-templates/empty.php, only where the local meta is empty, and the
German twin along with it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


def load() -> ModuleType:
    """The script is a file, not an importable module name."""
    path = Path(__file__).resolve().parent.parent / "page-template-empty.py"
    spec = importlib.util.spec_from_file_location("page_template_empty", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = load()


def page(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 1,
        "slug": "about",
        "language": "en",
        "template": "",
        "twin_id": 0,
        "twin_slug": "",
        "twin_template": "",
    }
    base.update(over)
    return base


def actions(writes: list[dict[str, Any]]) -> dict[str, str]:
    return {f"{item['id']}:{item['slug']}": item["action"] for item in writes}


def test_empty_meta_is_filled_for_the_page_and_its_twin() -> None:
    writes = script.plan(
        [page(id=862, slug="about", twin_id=6875, twin_slug="ueber-uns")],
        [page(id=862, slug="about", template=script.EMPTY_TEMPLATE)],
    )
    assert actions(writes) == {"862:about": "set", "6875:ueber-uns": "set"}


def test_a_page_the_live_site_does_not_render_empty_is_left_alone() -> None:
    """The blog index and the shop carry no such template on the live site."""
    writes = script.plan(
        [
            page(id=14, slug="blog"),
            page(id=1034, slug="products"),
            page(id=5385, slug="compare-products", template=""),
        ],
        [
            page(id=14, slug="blog", template=""),
            page(id=1034, slug="products", template=""),
            page(id=5385, slug="compare-products", template=""),
        ],
    )
    assert writes == []


def test_an_existing_template_is_reported_not_overwritten() -> None:
    writes = script.plan(
        [page(id=14, slug="blog", template="dynamic-template.php")],
        [page(id=14, slug="blog", template=script.EMPTY_TEMPLATE)],
    )
    assert actions(writes) == {"14:blog": "skip-existing"}
    assert writes[0]["current"] == "dynamic-template.php"


def test_a_page_already_set_produces_nothing() -> None:
    writes = script.plan(
        [
            page(
                id=862,
                slug="about",
                template=script.EMPTY_TEMPLATE,
                twin_id=6875,
                twin_slug="ueber-uns",
                twin_template=script.EMPTY_TEMPLATE,
            )
        ],
        [page(id=862, slug="about", template=script.EMPTY_TEMPLATE)],
    )
    assert writes == []


def test_a_german_page_is_not_planned_twice() -> None:
    """The twin is written from the English page's row, not from its own."""
    writes = script.plan(
        [
            page(id=862, slug="about", twin_id=6875, twin_slug="ueber-uns"),
            page(id=6875, slug="ueber-uns", language="de"),
        ],
        [
            page(id=862, slug="about", template=script.EMPTY_TEMPLATE),
            page(id=6875, slug="ueber-uns", language="de", template=""),
        ],
    )
    assert actions(writes) == {"862:about": "set", "6875:ueber-uns": "set"}


def test_a_site_without_polylang_still_plans_its_pages() -> None:
    writes = script.plan(
        [page(id=13, slug="home", language="")],
        [page(id=13, slug="home", language="", template=script.EMPTY_TEMPLATE)],
    )
    assert actions(writes) == {"13:home": "set"}
