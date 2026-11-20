"""The Contact migration detaches only the reviewed bilingual style block."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "contact_page_styles", Path(__file__).parents[1] / "contact-page-styles.py"
)
assert spec and spec.loader
contact = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contact)


def test_reviewed_block_is_detached_without_changing_either_localized_body():
    block = contact.original_block()
    bodies = {
        "28": '<div id="tv-contact-v1">Contact us</div>',
        "6907": '<div id="tv-contact-v1">Kontakt</div>',
    }
    pages = {post: block + content for post, content in bodies.items()}
    changes = contact.plan(pages)
    assert {str(row["id"]): row["after"] for row in changes} == bodies
    assert contact.plan(bodies) == []
    pages["6907"] = bodies["6907"]
    with pytest.raises(ValueError, match="different migration states"):
        contact.plan(pages)
    pages["6907"] = pages["28"].replace("#tv-contact-v1{", "#other{")
    with pytest.raises(ValueError, match="stylesheet changed"):
        contact.plan(pages)
