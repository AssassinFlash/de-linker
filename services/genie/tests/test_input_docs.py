"""The tool descriptions the model sees match the abilities' PHP schemas.

The REST introspection of an ability is permission-protected, so agent.py
carries the shapes as text (INPUT_DOCS). This file locks that text against
the PHP sources of truth in plugins/linker-commerce, so the two descriptions
cannot drift (review 2026-10-10, must-fix 9). The document search and the page
read are this service's own tools; the search's description is the one
`knowledge.validate` reads, and the page read takes no input.
"""

import re
from pathlib import Path

import pytest

from linker_genie import knowledge, page, planning
from linker_genie.abilities import ABILITY_NAMES
from linker_genie.agent import INPUT_DOCS, TOOL_NAMES

COMMERCE = Path(__file__).resolve().parents[3] / "plugins" / "linker-commerce"

# The device-class enum, from the one definition the search filters read.
DEVICE_CLASSES = (
    "inverters",
    "home-storage",
    "battery-systems",
    "all-in-one-systems",
    "ems-monitoring",
    "ev-chargers",
    "accessories",
)


def _read(name: str) -> str:
    return (COMMERCE / "includes" / "Abilities" / name).read_text(encoding="utf-8")


def _device_classes_in_php() -> tuple[str, ...]:
    source = (COMMERCE / "includes" / "Products" / "SelectionFacts.php").read_text(
        encoding="utf-8"
    )
    block = re.search(r"DEVICE_CLASSES = array\((.*?)\);", source, re.DOTALL)
    assert block is not None, "DEVICE_CLASSES not found in SelectionFacts.php"
    return tuple(re.findall(r"'([^']+)'", block.group(1)))


def test_input_docs_covers_every_tool() -> None:
    assert set(INPUT_DOCS) == set(TOOL_NAMES)
    assert set(TOOL_NAMES) - set(ABILITY_NAMES) == {
        knowledge.NAME,
        page.NAME,
        planning.NAME,
    }


def test_the_document_search_input_doc_names_the_fields_it_validates() -> None:
    doc = INPUT_DOCS[knowledge.NAME]
    for field in ("query", "lang", "product_ids"):
        assert field in doc
    assert knowledge.validate({"query": "q", "lang": "de", "product_ids": [3]}) == (
        "q",
        "de",
        [3],
    )


def test_search_products_lists_the_full_device_class_enum() -> None:
    doc = INPUT_DOCS["linker/search-products"]
    php = _device_classes_in_php()
    assert php == DEVICE_CLASSES, "update DEVICE_CLASSES here when PHP changes"
    for device_class in php:
        assert f"'{device_class}'" in doc, f"{device_class} missing from INPUT_DOCS"


def test_search_products_documents_the_extreme_fields() -> None:
    doc = INPUT_DOCS["linker/search-products"]
    source = _read("SearchProducts.php")
    for field in ("ac_power_min", "extreme", "device_classes"):
        assert re.search(rf"'{field}'\s*=>\s*array", source), (
            f"{field} vanished from the ability's input_schema"
        )
        assert field in doc, f"{field} missing from INPUT_DOCS"


def test_check_compatibility_describes_both_input_forms() -> None:
    doc = INPUT_DOCS["linker/check-compatibility"]
    source = _read("CheckCompatibility.php")
    for field in ("inverter_id", "battery_id", "product_ids"):
        assert re.search(rf"'{field}'\s*=>\s*array", source), (
            f"{field} vanished from the ability's input_schema"
        )
        assert field in doc, f"{field} missing from INPUT_DOCS"
    assert "or" in doc and "product_ids" in doc


@pytest.mark.parametrize(
    ("ability", "file_name"),
    [
        ("linker/search-products", "SearchProducts.php"),
        ("linker/get-product", "GetProduct.php"),
        ("linker/compare-products", "CompareProducts.php"),
        ("linker/check-compatibility", "CheckCompatibility.php"),
        ("linker/size-hint", "SizeHint.php"),
        ("linker/inquiry-status", "InquiryStatus.php"),
        ("linker/read-solution", "ReadSolution.php"),
        ("linker/handoff-team", "HandoffTeam.php"),
    ],
)
def test_every_ability_file_declares_an_input_schema(
    ability: str, file_name: str
) -> None:
    assert ability in ABILITY_NAMES
    assert "input_schema" in _read(file_name)
