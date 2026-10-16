"""Tests of 12-site-chrome.py's replacement pairs and its run phases.

The 2026-10-14 production run renamed the words on the pages and left the
tools' addresses behind (the link rules did not carry them), plus the
retired pages, the media alts, and — through the 2026-10-15 deploy's 9-i18n
import, which rewrites German pages from the stale `_linker_de_content`
metas — every German rename. These tests pin the repairs: the link rules,
the retired pages' cleanup, the alt rules and the meta-refresh rule, and
that internal identifiers and media file names stay untouched.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent


def load_script() -> ModuleType:
    """12-site-chrome.py is a script, not an importable module name."""
    spec = importlib.util.spec_from_file_location(
        "twelve_site_chrome", HERE.parent / "12-site-chrome.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


chrome = load_script()


def fake_ids() -> dict[str, dict[str, int]]:
    """steps() reads one entry per step key."""
    keys = [
        "header",
        "footer",
        "linker-advisor",
        "linker-planner",
        "design-canvas",
        "quote-configurator",
        "quote-configurator-2",
        "request-a-project",
    ]
    keys += list(chrome.SURFACES)
    return {key: {"en": 100 + i, "de": 300 + i} for i, key in enumerate(keys)}


def step_named(step_key: str) -> Any:
    return next(step for step in chrome.steps(fake_ids()) if step.key == step_key)


def with_rules(content: str, link_rules: list[tuple[str, str]]) -> str:
    for old, new in link_rules:
        content = content.replace(old, new)
    return content


def pairs_containing(step_key: str, needle: str) -> list[tuple[str, str]]:
    return [(old, new) for old, new in step_named(step_key).pairs if needle in old]


def test_the_link_rules_move_each_tool_address() -> None:
    en = with_rules(
        '<a href="/linker-advisor/">Open Genie →</a>'
        ' <a href="/linker-planner/">Open the Solution Configurator →</a>',
        chrome.LINK_RULES_EN,
    )
    assert en == (
        '<a href="/genie/">Open Genie →</a>'
        ' <a href="/solution-configurator/">Open the Solution Configurator →</a>'
    )
    de = with_rules(
        '<a href="/linker-advisor/">Linker Berater öffnen →</a>'
        ' <a href="/linker-planner/">Lösungskonfigurator öffnen →</a>',
        chrome.LINK_RULES_DE,
    )
    assert de == (
        '<a href="/de/genie/">Linker Berater öffnen →</a>'
        ' <a href="/de/loesungskonfigurator/">Lösungskonfigurator öffnen →</a>'
    )


def test_the_link_rules_catch_the_plain_address_forms() -> None:
    """The retired pages spell their address in comments and in the
    redirect script, not only in hrefs (the live 2026-10-16 check)."""
    en = with_rules(
        '<script>window.location.replace("/linker-planner/");</script>'
        " (measured 1440 on /de/linker-planer/, 2026-08-28)",
        chrome.LINK_RULES_EN,
    )
    assert en == (
        '<script>window.location.replace("/solution-configurator/");</script>'
        " (measured 1440 on /de/loesungskonfigurator/, 2026-08-28)"
    )
    de = with_rules(
        '<script>window.location.replace("/linker-planner/");</script>'
        " (measured 1440 on /de/linker-planer/, 2026-08-28)",
        chrome.LINK_RULES_DE,
    )
    assert de == (
        '<script>window.location.replace("/de/loesungskonfigurator/");</script>'
        " (measured 1440 on /de/loesungskonfigurator/, 2026-08-28)"
    )


def test_the_internal_identifiers_and_media_files_survive() -> None:
    """data-lk-ask, data-linker-assistant-open, data-linker-planner-film,
    the lk-advisor-* classes and the media file names are internal
    identifiers with live consumers; the rules must not touch them."""
    survivor = (
        '<a class="lk-capsule" href="/genie/" data-lk-ask="">10 kW storage</a>'
        '<video data-linker-planner-film poster="/wp-content/uploads/2026/09/'
        'linker-advisor-lookup-for-installers-poster.webp"></video>'
        '<a class="rd-btn" href="/de/genie/" data-linker-assistant-open>'
        "Genie öffnen</a>"
        '<span class="lk-advisor-badge"><source src="/wp-content/uploads/2026/09/'
        'linker-advisor-lookup-for-installers.mp4"></span>'
    )
    assert with_rules(survivor, chrome.LINK_RULES_EN) == survivor
    assert with_rules(survivor, chrome.LINK_RULES_DE) == survivor


def test_the_roof_button_opens_the_roof_step() -> None:
    """The German for-installer page's roof button opened /de/; its renamed
    label says the roof step, and the target now matches."""
    snippet = (
        '<div class="lk-btn-row">\n'
        '<a class="lk-btn-primary" href="/de/">\n'
        "        Linker Standortdetails öffnen →\n"
        "       </a>\n</div>"
    )
    pairs = pairs_containing("for-installer-de", 'href="/de/"')
    pairs += pairs_containing("for-installer-de", "öffnen →")
    out = snippet
    for old, new in pairs:
        assert out.count(old) == 1
        out = out.replace(old, new)
    assert 'href="/de/loesungskonfigurator/?step=roof"' in out
    assert "Dachdetail-Schritt öffnen →" in out
    assert "Linker Standortdetails" not in out


def test_the_faq_cta_keeps_its_hook_and_opens_genie() -> None:
    """#6863's CTA should open Genie; the data-linker-assistant-open hook
    the new tree consumes stays on the element."""
    pairs = pairs_containing("faq-download-de", "data-linker-assistant-open")
    assert pairs == [
        (
            'href="/de/produkte/" data-linker-assistant-open',
            'href="/de/genie/" data-linker-assistant-open',
        )
    ]
    snippet = (
        '<a class="rd-btn" href="/de/produkte/" '
        "data-linker-assistant-open>Linker Berater öffnen</a>"
    )
    assert snippet.replace(*pairs[0]) == (
        '<a class="rd-btn" href="/de/genie/" '
        "data-linker-assistant-open>Linker Berater öffnen</a>"
    )


def test_the_tool_page_steps_carry_the_link_rules() -> None:
    """The offline rehearsal of the 2026-10-16 live dump found the tool
    pages' comments kept '/linker-planner/' and '/de/linker-planer/': the
    tool-page steps carried no link rules. Each carries its language's
    now, and its comments get rewritten."""
    for key, rule in (
        ("linker-advisor-en", 'href="/linker-advisor/"'),
        ("linker-berater-de", 'href="/linker-advisor/"'),
        ("linker-planner-en", 'href="/linker-planner/"'),
        ("linker-planer-de", 'href="/linker-planner/"'),
    ):
        assert any(old == rule for old, _new in step_named(key).rules), key
    step = step_named("linker-planer-de")
    content = (
        '<a href="#" data-qcfg-i18n="">unsicher? Linker Berater fragen</a>'
        "(measured 1440 on /de/linker-planer/, 2026-08-28)"
        "(measured 2026-08-27, /linker-planner/ 1440 en anon)"
    )
    out = step.planned(content)
    assert "unsicher? Genie fragen" in out
    assert "/de/loesungskonfigurator/" in out
    assert "/linker-planner/" not in out
    assert "/linker-planer/" not in out


def test_the_design_canvas_drafts_lose_the_old_names() -> None:
    en = step_named("design-canvas-en")
    content = (
        "<p>Change these conditions in Linker Planner.</p>"
        '<p class="dcv-honesty">Your drawing stays with the Project,'
        " for Linker Planner and your Project request.</p>"
    )
    out = en.planned(content)
    assert "Linker Planner" not in out
    assert "Change these conditions in the Solution Configurator." in out
    assert "for the Solution Configurator and your Project request." in out
    assert en.planned(out) == out  # a re-run finds nothing left to pair

    de = step_named("design-canvas-de")
    german = (
        "<button>Linker Planer öffnen</button>"
        "<p>Ändern Sie diese Bedingungen im Linker Planer.</p>"
        "<p>Ihre Zeichnung bleibt beim Projekt, für Linker Planer und Ihre"
        " Projektanfrage.</p>"
    )
    out_de = de.planned(german)
    assert "Linker Planer" not in out_de
    assert "Lösungskonfigurator öffnen" in out_de
    assert "im Lösungskonfigurator." in out_de
    assert "für den Lösungskonfigurator und Ihre Projektanfrage." in out_de
    assert de.planned(out_de) == out_de


def test_the_moved_notices_rename_to_the_new_address() -> None:
    en = step_named("quote-configurator-en")
    content = (
        "<!-- Retired address. The Linker Planner moved to /linker-planner/"
        " on 2026-08-02. -->"
        '<script>window.location.replace("/linker-planner/");</script>'
        "<p>The Linker Planner has moved."
        ' <a href="/linker-planner/" rel="canonical">Open the Linker Planner</a>.</p>'
    )
    out = en.planned(content)
    assert "Linker Planner" not in out
    assert "/linker-planner/" not in out
    assert 'window.location.replace("/solution-configurator/")' in out
    assert 'href="/solution-configurator/" rel="canonical"' in out
    assert en.title == ("Linker Planner has moved", "Solution Configurator has moved")
    assert en.seo_desc is not None
    assert "Solution Configurator" in en.seo_desc[1]
    assert "Linker Planner" not in en.seo_desc[1]


def test_the_german_moved_notices_use_the_german_address() -> None:
    step = step_named("quote-configurator-2-de")
    content = (
        "<!-- Retired address. The Linker Planner moved to /linker-planner/"
        " on 2026-08-02. -->"
        '<script>window.location.replace("/linker-planner/");</script>'
        "<p>Der Linker Planner ist umgezogen."
        ' <a href="/linker-planner/" rel="canonical">'
        "Öffnen Sie den Linker Planner</a>.</p>"
    )
    out = step.planned(content)
    assert "Linker Planner" not in out
    assert "/linker-planner/" not in out
    assert 'window.location.replace("/de/loesungskonfigurator/")' in out
    assert "Der Lösungskonfigurator ist umgezogen." in out
    assert "Öffnen Sie den Lösungskonfigurator</a>." in out
    assert step.title == (
        "Der Linker Planner ist umgezogen",
        "Der Lösungskonfigurator ist umgezogen",
    )


def test_the_alt_rules_rename_the_media_alts() -> None:
    assert chrome.renamed_alt("Linker Advisor technical lookup result preview") == (
        "Genie technical lookup result preview"
    )
    assert chrome.renamed_alt(
        "Linker Planner: site details and the first sizing result"
    ) == ("Solution Configurator: site details and the first sizing result")
    assert chrome.renamed_alt(
        "Linker Site Detail tutorial: tracing the roof on aerial imagery and"
        " saving the design basis"
    ) == (
        "Solution Configurator tutorial: tracing the roof on aerial imagery and"
        " saving the design basis"
    )
    assert chrome.renamed_alt("Linker team in Germany") == "Linker team in Germany"


def test_the_german_sources_metas_follow_the_german_pages() -> None:
    """The 9-i18n import reads `_linker_de_content` / `_linker_de_title` as
    its German source; a stale copy reverts the page on the import's next
    run (measured: the 2026-10-15 deploy did exactly that). The update
    takes the German page's new state."""
    plan = [
        chrome.Step("for-installer-de", 6869, 826),
        chrome.Step(
            "quote-configurator-de",
            6637,
            3998,
            title=(
                "Der Linker Planner ist umgezogen",
                "Der Lösungskonfigurator ist umgezogen",
            ),
        ),
        chrome.Step("home-en", 13, 13),
    ]
    german = {6869: "…Genie…", 6637: "…neuer Text…", 13: "unused"}
    metas = {
        "826": {"content": "…Linker Berater…", "title": "Für Installateure"},
        "3998": {
            "content": "…Der Linker Planner ist umgezogen…",
            "title": "Der Linker Planner ist umgezogen",
        },
        "13": {"content": "…", "title": "Startseite"},
    }
    updates = chrome.legacy_meta_updates(plan, german, metas)
    assert updates == [
        (826, {"_linker_de_content": "…Genie…"}),
        (
            3998,
            {
                "_linker_de_content": "…neuer Text…",
                "_linker_de_title": "Der Lösungskonfigurator ist umgezogen",
            },
        ),
    ]
    # A meta already equal to the German page, and an English-only step,
    # produce nothing.
    assert (
        chrome.legacy_meta_updates(
            [chrome.Step("home-de", 6913, 13)],
            {6913: "same"},
            {"13": {"content": "same"}},
        )
        == []
    )
    # Absent metas produce nothing: the refresh writes only what exists.
    assert chrome.legacy_meta_updates(plan, german, {}) == []


def test_stale_tokens_count_names_and_addresses() -> None:
    assert chrome.stale_tokens("nothing here") == []
    tokens = chrome.stale_tokens("x Linker Advisor x /de/linker-planner/ y")
    assert "1x 'Linker Advisor'" in tokens
    assert "1x '/linker-planner/'" in tokens
    assert (
        chrome.stale_tokens(
            '<source src="/wp-content/uploads/2026/09/'
            'linker-advisor-lookup-for-installers.mp4">'
        )
        == []
    )
    assert chrome.stale_tokens("data-linker-planner-film") == []
    assert chrome.stale_tokens('class="lk-advisor-badge"') == []


def test_every_php_snippet_declaring_wpdb_declares_it_global() -> None:
    """`wp eval-file` runs inside a function scope: a snippet that reads
    $wpdb without `global $wpdb;` is a critical error on the site (measured
    on the 2026-10-16 live plan, the media-alts phase). Every PHP constant
    must keep the rule."""
    snippets = {
        name: value
        for name, value in vars(chrome).items()
        if name.endswith("_PHP") and isinstance(value, str)
    }
    assert snippets, "the PHP constant scan found nothing"
    for name, code in snippets.items():
        if "$wpdb" in code:
            assert "global $wpdb;" in code, name


def test_the_steps_carry_the_new_surfaces_and_retired_pages() -> None:
    keys = {step.key for step in chrome.steps(fake_ids())}
    for key in (
        "thank-you-en",
        "thank-you-de",
        "request-a-project-en",
        "request-a-project-de",
        "quote-configurator-2-en",
        "quote-configurator-2-de",
        "design-canvas-de",
    ):
        assert key in keys
    roof = step_named("for-installer-de")
    assert (
        '<a class="lk-btn-primary" href="/de/">',
        '<a class="lk-btn-primary" href="/de/loesungskonfigurator/?step=roof">',
    ) in roof.pairs
    faq = step_named("faq-download-de")
    assert (
        'href="/de/produkte/" data-linker-assistant-open',
        'href="/de/genie/" data-linker-assistant-open',
    ) in faq.pairs
    # the retired pages' steps are drafts, and their SEO pairs exist
    canvas = step_named("design-canvas-en")
    assert canvas.status == "draft"
    assert canvas.seo == (
        "Linker Site Detail: Trace the Roof, Sharpen the Sizing",
        "Solution Configurator: Trace the Roof, Sharpen the Sizing",
    )
    moved = step_named("quote-configurator-de")
    assert moved.status == "draft"
    assert moved.seo_desc is not None
    assert "Lösungskonfigurator" in moved.seo_desc[1]
    assert "Linker Planer" not in moved.seo_desc[1]
