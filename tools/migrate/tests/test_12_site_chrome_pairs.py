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

import pytest

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
        "utility-storage",
        "terms-of-sale",
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


class SlugSite:
    """WP-CLI's two answers for the slug phase: a page's slug, and its update."""

    def __init__(self, slugs: dict[int, str]) -> None:
        self.slugs = slugs
        self.renamed: list[tuple[int, str]] = []

    def run(self, *args: str, **kwargs: object) -> str:
        if args[:2] == ("post", "get") and args[3] == "--field=post_name":
            return self.slugs[int(args[2])]
        if args[:2] == ("post", "update"):
            self.renamed.append((int(args[2]), args[3].removeprefix("--post_name=")))
            return ""
        raise AssertionError(args)


def test_rename_slugs_accepts_the_german_pages_english_slug() -> None:
    """The German configurator carried the English /solution-configurator/
    from the same-slug rename until the 2026-10-16 move to its own German
    slug; a snapshot taken in that window (the 2026-10-15 one the review
    suite loads) holds the English slug on the German page. The phase
    renames it like the German slug it replaced, and still refuses anything
    else rather than renaming a page it does not recognize."""
    ids = {
        "linker-planner": {"en": 3302, "de": 6693},
        "linker-advisor": {"en": 3303, "de": 6635},
    }
    site = SlugSite(
        {
            3302: "solution-configurator",
            6693: "solution-configurator",
            3303: "genie",
            6635: "genie",
        }
    )
    chrome.rename_slugs(site, ids, write=True)
    assert site.renamed == [(6693, "loesungskonfigurator")]

    # The German slug it replaced, and the target itself: both handled.
    site = SlugSite(
        {
            3302: "solution-configurator",
            6693: "linker-planer",
            3303: "genie",
            6635: "genie",
        }
    )
    chrome.rename_slugs(site, ids, write=True)
    assert site.renamed == [(6693, "loesungskonfigurator")]

    site = SlugSite(
        {
            3302: "solution-configurator",
            6693: "loesungskonfigurator",
            3303: "genie",
            6635: "genie",
        }
    )
    chrome.rename_slugs(site, ids, write=True)
    assert site.renamed == []

    # Anything else is refused. pytest.raises catches SystemExit.
    site = SlugSite(
        {
            3302: "solution-configurator",
            6693: "some-other-slug",
            3303: "genie",
            6635: "genie",
        }
    )
    with pytest.raises(SystemExit):
        chrome.rename_slugs(site, ids, write=True)
    assert site.renamed == []


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


# ---------------------------------------------------------------------------
# The M2 copy batch (docs/acceptance/2026-10-16/m2-copy/copy-review.md):
# 43 literal pairs, 42 via the exactly-once pair channel, "the Advisor zone"
# (two hits per privacy page) via the rule channel.
# ---------------------------------------------------------------------------

M2_PAIRS: dict[str, list[tuple[str, str]]] = {
    "home-en": [
        (
            "<li>Quoted per site, not from the cart</li>",
            "<li>A project quote for each site</li>",
        ),
    ],
    "home-de": [
        (
            "<li>Angebot pro Standort, nicht aus dem Warenkorb</li>",
            "<li>Projektangebot pro Standort</li>",
        ),
    ],
    "services-support-en": [
        (
            "<h3>Planner Sizing &amp; Compatibility Lists</h3>",
            "<h3>System Sizing &amp; Compatibility Lists</h3>",
        ),
        (
            'aria-label="Planner sizing and compatibility lists"',
            'aria-label="System sizing and compatibility lists"',
        ),
        (
            "<b>Planner Sizing and Compatibility Lists</b>",
            "<b>System Sizing and Compatibility Lists</b>",
        ),
        (
            '<h3 class="lk-sstage-h3">Planner Sizing and Compatibility Lists</h3>',
            '<h3 class="lk-sstage-h3">System Sizing and Compatibility Lists</h3>',
        ),
        (
            "<strong>Deliverable:</strong> Planner Sizing · Complete Parts List",
            "<strong>Deliverable:</strong> System Sizing · Complete Parts List",
        ),
    ],
    "services-support-de": [
        (
            "<h3>Planer-Auslegung &amp; Kompatibilitätslisten</h3>",
            "<h3>Systemauslegung &amp; Kompatibilitätslisten</h3>",
        ),
        (
            'aria-label="Planer-Auslegung und Kompatibilitätslisten"',
            'aria-label="Systemauslegung und Kompatibilitätslisten"',
        ),
        (
            "<b>Planer-Auslegung und Kompatibilitätslisten</b>",
            "<b>Systemauslegung und Kompatibilitätslisten</b>",
        ),
        (
            '<h3 class="lk-sstage-h3">Planer-Auslegung und Kompatibilitätslisten</h3>',
            '<h3 class="lk-sstage-h3">Systemauslegung und Kompatibilitätslisten</h3>',
        ),
        (
            "<strong>Ergebnis:</strong> Auslegung im Planer · Vollständige Stückliste",
            "<strong>Ergebnis:</strong> Systemauslegung · Vollständige Stückliste",
        ),
    ],
    "for-installer-en": [
        (
            "Site Detail maps usable roof space, module placement around obstructions, and physical dimensions before electrical sizing.",
            "The Roof detail step maps usable roof space, module placement around obstructions, and physical dimensions before electrical sizing.",
        ),
    ],
    "solution-en": [
        ("Design with Planner →", "Plan with the Solution Configurator →"),
        (
            "<td>Storage packages, Planner tools, and Partner pricing</td>",
            "<td>Storage packages, sizing tools, and Partner pricing</td>",
        ),
        (
            "cannot simply be placed into an online shopping cart.",
            "are quoted per project.",
        ),
    ],
    "solution-de": [
        (
            "Der Planer modelliert geeignete",
            "Der Lösungskonfigurator modelliert geeignete",
        ),
        (
            "<td>Speicherpakete, Planer-Werkzeuge und Partnerpreise</td>",
            "<td>Speicherpakete, Auslegungswerkzeuge und Partnerpreise</td>",
        ),
        (
            "lassen sich nicht einfach in einen Online-Warenkorb legen.",
            "werden projektbezogen angeboten.",
        ),
    ],
    "commercial-storage-en": [
        (
            "Model Project in Planner →",
            "Model the project in the Solution Configurator →",
        ),
    ],
    "faq-download-en": [
        (
            'href="/products/" data-linker-assistant-open',
            'href="/genie/" data-linker-assistant-open',
        ),
    ],
    "faq-download-de": [
        (
            'href="/de/produkte/" data-linker-assistant-open',
            'href="/de/genie/" data-linker-assistant-open',
        ),
    ],
    "privacy-policy-en": [
        ("put to the Genie", "put to Genie"),
        ("the Advisor button", "the Genie button"),
        ("Advisor button zone", "Genie button zone"),
        (
            "(session, cart, and login cookies)",
            "(session, solution draft, and login cookies)",
        ),
        ("When you ask the Advisor a question", "When you ask Genie a question"),
        ("not sent with Advisor messages", "not sent with your messages to Genie"),
        (
            "Advisor conversations belonging to a signed-in account",
            "Conversations with Genie belonging to a signed-in account",
        ),
        ("from the Advisor's history", "from your Genie history"),
    ],
    "privacy-policy-de": [
        (
            "(Session-, Warenkorb- und Login-Cookies)",
            "(Session-, Lösungsentwurf- und Login-Cookies)",
        ),
        (
            "Wenn Sie dem Berater eine Frage stellen",
            "Wenn Sie Genie eine Frage stellen",
        ),
        (
            "nicht mit Berater-Nachrichten übermittelt",
            "nicht mit Ihren Nachrichten an Genie übermittelt",
        ),
        (
            "Berater-Konversationen, die zu einem angemeldeten Konto gehören",
            "Konversationen mit Genie, die zu einem angemeldeten Konto gehören",
        ),
        ("aus dem Verlauf des Beraters löschen", "aus Ihrem Genie-Verlauf löschen"),
        ("the Advisor button", "the Genie button"),
        ("Advisor button zone", "Genie button zone"),
    ],
    "terms-of-sale-en": [
        ("apply automatically in the cart", "apply automatically in the solution draft")
    ],
    "terms-of-sale-de": [
        ("werden im Warenkorb automatisch", "werden im Lösungsentwurf automatisch")
    ],
}

M2_SEO_DESC: dict[str, tuple[str, str]] = {
    "utility-storage-en": (
        "CRRC, Pylontech and GoodWe container BESS from 1.0 to 6.9 MWh, with datasheets on file, quoted per project, not from the cart.",
        "CRRC, Pylontech and GoodWe container BESS from 1.0 to 6.9 MWh, with datasheets on file, quoted per project.",
    ),
    "utility-storage-de": (
        "Container-Batteriespeicher von CRRC, Pylontech und GoodWe mit 1,0 bis 6,9 MWh, mit hinterlegten Datenblättern, projektbezogen angeboten statt über den Warenkorb.",
        "Container-Batteriespeicher von CRRC, Pylontech und GoodWe mit 1,0 bis 6,9 MWh, mit hinterlegten Datenblättern, projektbezogen angeboten.",
    ),
}

# "the Advisor zone" hits twice per privacy page: the rule channel, with
# verify's required-rules check.
M2_RULE = ("the Advisor zone", "the Genie zone")


def test_the_m2_copy_pairs_are_the_review_table() -> None:
    """Every content pair of the review's 43-row table sits in its step's
    pair channel, byte for byte."""
    count = 0
    for step_key, pairs in M2_PAIRS.items():
        step = step_named(step_key)
        for pair in pairs:
            assert pair in step.pairs, (step_key, pair)
            count += 1
    for step_key, pair in M2_SEO_DESC.items():
        assert step_named(step_key).seo_desc == pair, step_key
        count += 1
    # 43 rows in the review's table: 41 count-1 pairs here, the zone's
    # two rows (1673 + 6827) as one rule, and the two utility descs above.
    assert count == 41, f"table drift: {count} pairs"


def test_the_advisor_zone_travels_in_the_rule_channel() -> None:
    """The review: two occurrences per privacy page, so a rule (any count),
    never the exactly-once pair channel."""
    for step_key in ("privacy-policy-en", "privacy-policy-de"):
        step = step_named(step_key)
        assert M2_RULE not in step.pairs
        assert M2_RULE in step.rules
        assert M2_RULE in step.required_rules


def test_the_m2_sentence_pairs_rewrite_and_re_run_clean() -> None:
    """Apply-then-re-apply on the settled strings: the pairs take, and a
    re-run (the review's apply on an already-migrated site) writes nothing
    and refuses nothing."""
    step = step_named("privacy-policy-en")
    content = (
        "<td>When you ask the Advisor a question, your message travels on.</td>"
        "<p>not sent with Advisor messages</p>"
        "<p>Advisor conversations belonging to a signed-in account</p>"
        "<p>from the Advisor's history</p>"
        "<p>To answer a question put to the Genie, and to run the planning tools.</p>"
        "<p>This shop uses only technically necessary cookies"
        " (session, cart, and login cookies).</p>"
        "/* focus clear of the Advisor button */"
        "/* rails stop above the bottom 88px: the Advisor zone */"
        "/* rails stop above the bottom 88px: the Advisor zone */"
        "/* above the bottom-right Advisor button zone (88px) */"
    )
    out = step.planned(content)
    assert "Advisor" not in out
    assert "When you ask Genie a question" in out
    assert "not sent with your messages to Genie" in out
    assert out.count("the Genie zone") == 2
    assert step.planned(out) == out  # re-run: pairs skip, rules find nothing


def test_the_zone_rule_and_the_button_pairs_do_not_overlap() -> None:
    """ "the Advisor button", "Advisor button zone" and "the Advisor zone"
    are three distinct strings in the two mirrors; none contains the other,
    so the pair's list order and the rule pass cannot consume each other."""
    button = "the Advisor button"
    both = "Advisor button zone"
    zone = "the Advisor zone"
    assert button not in both and both not in button
    assert zone not in button and button not in zone
    assert zone not in both and both not in zone
