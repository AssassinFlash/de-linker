"""Tests of 201-consent.py's page edit against the shapes it must refuse.

The migration writes the privacy statement's two sections. Both live pages are
edited elsewhere too (12-site-chrome.py renames the tools), so the anchors are
exact strings and a page that matches neither the old nor the new shape stops
the run instead of being half-rewritten. These tests pin that: the happy path
makes the three edits once and is idempotent, and a drifted page raises.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE.parent / "201-consent.json").read_text(encoding="utf-8"))


def load_script() -> ModuleType:
    """201-consent.py is a script, not an importable module name."""
    spec = importlib.util.spec_from_file_location(
        "consent_migration", HERE.parent / "201-consent.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


consent = load_script()

# One page in the shape both languages share: the section, the caption, the
# last fixed row of the processor table.
PAGE = (
    '<section id="section-3">\n'
    '        <h2><span class="lg-num">3.</span> Cookies</h2>\n'
    "        {cookies}\n"
    "      </section>\n"
    "<table>\n"
    "          {caption}\n"
    "          <tbody>\n"
    "              {vies}\n"
    "          </tbody>\n"
    "        </table>\n"
)


def page(language: str) -> str:
    spec = PLAN["privacy"][language]
    return PAGE.format(
        cookies=spec["cookies_old"],
        caption=spec["caption_old"],
        vies=(
            '<tr>\n                <th scope="row">'
            + (
                "European Commission VIES"
                if language == "en"
                else "Europäische Kommission VIES"
            )
            + "</th>\n                <td>EU</td>\n                <td>VAT IDs.</td>\n              </tr>"
        ),
    )


@pytest.mark.parametrize("language", ["en", "de"])
def test_the_three_edits_land_once_and_the_second_run_is_a_no_op(language: str) -> None:
    spec = PLAN["privacy"][language]
    first, changes = consent.planned_privacy(page(language), spec)
    assert len(changes) == 3
    assert spec["cookies_new"] in first
    assert spec["caption_new"] in first
    assert spec["google_row"] in first
    # The rows around it are untouched.
    assert first.count("<tbody>") == 1

    second, changes_again = consent.planned_privacy(first, spec)
    assert changes_again == []
    assert second == first


@pytest.mark.parametrize(
    "drift",
    [
        # The Cookies section was rewritten by someone else.
        ("<p>A different sentence about cookies.</p>", "cookies"),
        # The caption changed with the retired tool name.
        (
            "<caption>Um eine an den Linker Berater gerichtete Frage</caption>",
            "caption",
        ),
    ],
)
def test_a_drifted_page_is_refused(drift: tuple[str, str]) -> None:
    text, which = drift
    spec = dict(PLAN["privacy"]["de"])
    drifted = page("de")
    if which == "cookies":
        drifted = drifted.replace(spec["cookies_old"], text)
    else:
        drifted = drifted.replace(spec["caption_old"], text)
    with pytest.raises(SystemExit):
        consent.planned_privacy(drifted, spec)


def test_a_page_without_the_last_fixed_row_is_refused() -> None:
    """The Google row goes after VIES; without that anchor nothing is written."""
    spec = PLAN["privacy"]["en"]
    without_vies = page("en").replace(
        '<tr>\n                <th scope="row">European Commission VIES</th>\n'
        "                <td>EU</td>\n                <td>VAT IDs.</td>\n              </tr>",
        '<tr>\n                <th scope="row">Someone else</th>\n                <td>x</td>\n              </tr>',
    )
    with pytest.raises(SystemExit):
        consent.planned_privacy(without_vies, spec)


def test_the_plan_carries_both_languages_and_their_strings() -> None:
    """The data file is the copy's single source; a missing half is a defect."""
    for language in ("en", "de"):
        for key in (
            "cookies_old",
            "cookies_new",
            "caption_old",
            "caption_new",
            "vies_row",
            "google_row",
        ):
            assert PLAN["privacy"][language][key].strip(), (language, key)
    # The German banner strings cover every English banner string that is
    # translatable, so no purpose renders English on /de/.
    for key in (
        "message_optin",
        "statistics_text",
        "marketing_text",
        "accept",
        "dismiss",
        "revoke",
    ):
        value = PLAN["banner"][key]
        if isinstance(value, dict):
            value = value["text"]
        assert value in PLAN["banner_de_strings"], key
