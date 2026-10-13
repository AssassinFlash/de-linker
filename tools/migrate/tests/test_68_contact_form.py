"""The decision of 68-contact-form.py: the mount edit and the name edit.

The script's effect — the form rendering from this repository's shortcode,
and the page's script comment no longer crediting the previous runtime — is
checked against a running instance (t110, `verify`). What a unit test can pin
down is the decision itself: the two edits applied independently, idempotent
on a second run, and a page that still names the previous tree elsewhere
refused rather than guessed at.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def load() -> ModuleType:
    """The script is a file, not an importable module name."""
    path = Path(__file__).resolve().parent.parent / "68-contact-form.py"
    spec = importlib.util.spec_from_file_location("contact_form", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = load()

OLD_MOUNT = (
    '<div data-linker-contact-mount><div class="cp-contact-fallback" '
    "data-contact-fallback>…</div></div>"
)
OLD_SCRIPT = (
    '<script data-site-js="contact-page.js">\n'
    "/* Contact page presentation over the real enquiry runtime "
    "(terravolt-b2b-core contact-request.js).\n"
    "   The runtime owns state, validation, submission and receipts. */\n"
    "</script>"
)


def test_the_unmigrated_page_gets_both_edits() -> None:
    """The fallback becomes the shortcode, and the comment loses the name."""
    new, changes = script.planned(OLD_MOUNT + "\n" + OLD_SCRIPT)

    assert script.SHORTCODE in new
    assert "cp-contact-fallback" not in new.split(script.SHORTCODE)[0][-200:]
    assert "(terravolt-b2b-core contact-request.js)" not in new
    assert "over the real enquiry runtime." in new
    assert changes == [
        "mount: fallback -> " + script.SHORTCODE,
        "script comment: the previous runtime's name removed",
    ]


def test_an_already_migrated_page_still_gets_the_name_edit() -> None:
    """The mount edit is one-shot; the name edit applies to pages it already ran on."""
    migrated = OLD_MOUNT.replace(
        '<div class="cp-contact-fallback" data-contact-fallback>…</div>',
        script.SHORTCODE,
    )

    new, changes = script.planned(migrated + "\n" + OLD_SCRIPT)

    assert script.SHORTCODE in new
    assert "contact-request.js" not in new
    assert changes == ["script comment: the previous runtime's name removed"]


def test_a_clean_page_is_left_alone() -> None:
    """Second run of a finished page: nothing to do."""
    clean = (
        "<div data-linker-contact-mount>" + script.SHORTCODE + "</div>\n"
        '<script data-site-js="contact-page.js">\n'
        "/* Contact page presentation over the real enquiry runtime. */\n"
        "</script>"
    )

    new, changes = script.planned(clean)

    assert new == clean
    assert changes == []


def test_a_region_that_matches_neither_shape_is_refused() -> None:
    """A mount the step does not recognize is never guessed at."""
    with pytest.raises(SystemExit, match="matches neither the old mount"):
        script.planned("<div data-linker-contact-mount>something else</div>")


def test_a_page_naming_the_previous_tree_elsewhere_is_refused() -> None:
    """The name must not survive in a place this step does not know."""
    with pytest.raises(SystemExit, match="still names the previous tree"):
        script.planned(
            "<div data-linker-contact-mount>" + script.SHORTCODE + "</div>"
            "<p>TerraVolt support</p>"
        )
