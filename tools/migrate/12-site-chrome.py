#!/usr/bin/env python3
"""#12 migration: the site chrome names the two tools.

Runs against a WordPress through WP-CLI (the pattern of 9-i18n.py):

    python3 tools/migrate/12-site-chrome.py --wp ~/de-linker-local/t12/wp.sh plan
    python3 tools/migrate/12-site-chrome.py --wp ~/de-linker-local/t12/wp.sh --user local-admin apply --write
    python3 tools/migrate/12-site-chrome.py --wp ~/de-linker-local/t12/wp.sh verify

What changes (docs/specs/12-site-chrome.md items 1, 2, 4 and the ticket's
German-twin line; the copy decisions and their adversarial review are
recorded in docs/acceptance/2026-10-10/12/copy-review.md):

1. The header partial (EN "header", DE twin): the tools menu keeps two
   cards, Genie ("Genie - Linker's AI assistant" / "Genie – der
   KI-Assistent von Linker") and the Solution Configurator, whose
   description carries the Roof detail / Dachdetails sentence (the Site
   Detail card folded in). The Site Detail card and mobile link go; their
   addresses redirect (plugin code, Redirects.php).
2. The footer partial's planning panel: Genie and Solution Configurator
   links, the Site Detail link removed, the count badge 04 -> 03.
3. The tool pages rename and the configurator's page moves to its own
   address ("Linker Planner" -> "Solution Configurator", /linker-planner/
   -> /solution-configurator/; "Linker Planer" -> "Lösungskonfigurator",
   /de/linker-planer/ -> /de/loesungskonfigurator/; owner ruling
   2026-10-12 — the former addresses 301 through the plugin's map.
   "Linker Advisor" -> "Genie - Linker's AI assistant"; "Linker Berater"
   -> "Genie – der KI-Assistent von Linker"), the configurator's SEO
   title drops the price promise (prices are partner-gated, #11), and
   the assistant page's no-JavaScript fallback names Genie.
4. The retired pages become drafts: design-canvas / Entwurfsfläche and
   the two "has moved" notices (quote-configurator /
   angebots-konfigurator); Redirects.php sends their addresses to the
   configurator.
5. Every other published surface that names a tool keeps its layout and
   wording, with the names swapped (NAME_RULES) and Site Detail
   references folded into the configurator's roof step (BESPOKE). A
   marketing sentence that does not name a tool is not touched.
6. The links follow the names. The 2026-10-14 production run renamed the
   words and left every href on the retired addresses (`/linker-advisor/`,
   `/linker-planner/` and their pre-move German forms) — the link rules
   did not carry the addresses until now. The retired pages' comments and
   redirect scripts spell the addresses in plain text too, and the FAQ
   page's CTA opens Genie rather than the products page.
7. The retired pages (design-canvas / Entwurfsfläche, the two "has moved"
   notices) lose the old names and addresses from their content, titles
   and SEO metas as well; they stay drafts.
8. The media library's alternative texts that name an old tool get the
   new names (file names stay), and the German sources' `_linker_de_content`
   / `_linker_de_title` metas are refreshed to the German pages' new state:
   the 9-i18n import reads them as its source, so a stale copy reverts
   every rename here — the 2026-10-15 deploy's import did exactly that.
9. The M2 copy batch's 43 sentence pairs (reviewed and settled in
   docs/acceptance/2026-10-16/m2-copy/copy-review.md; the review's table
   is the authority for each string): the bare Planner/Advisor uses the
   name rules did not reach (the two "Design with Planner" / "Model
   Project in Planner" CTAs, the "Planner Sizing" stage tab, the two
   "Storage packages, Planner tools" cells), the helper tools' remaining
   sentences, the Privacy Policy's visible rows and its CSS comments (the
   two mirrors stay byte-identical), the FAQ CTA's English twin, and the
   banned cart/Warenkorb words (home bullet, the large-project answer,
   the cookie sentence, the prices sentence; AGENTS.md §3). Both privacy
   pages are legal copy, EN written first and DE independently — the
   review records both sides.

After the writes, the German versions' translation state is marked
hand-edited (all fields reviewed) with the new English fingerprint, so a
later automatic translation keeps this copy. The migration is idempotent:
every literal pair must be found exactly once before it is applied, and a
second run finds the new strings and reports nothing to do.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shlex
import subprocess
import sys
from typing import Any, overload

# The old tool names that must not survive in any published post body or
# SEO title once this migration has run.
OLD_NAMES = (
    "Linker Advisor",
    "Linker Planner",
    "Linker Site Detail",
    "Linker Berater",
    "Linker Planer",
    "Linker Standortdetails",
)

# The retired addresses of the two tools, in every spelling the content and
# metas carry them (the `/de/` forms are covered as their own substrings).
# The link rules rewrite them; verify refuses them.
LEGACY_ADDRESSES = (
    "/linker-advisor/",
    "/linker-planner/",
    "/linker-planer/",
    "/linker-berater/",
)


def stale_tokens(text: str) -> list[str]:
    """The old names and addresses still in one string, each with its count:
    the report unit of plan, apply and verify."""
    found: list[str] = []
    for token in (*OLD_NAMES, *LEGACY_ADDRESSES):
        count = text.count(token)
        if count:
            found.append(f"{count}x {token!r}")
    return found


# Published pages, posts and LiveCanvas templates whose content or title
# names a tool (or, for the thank-you page, opens its address), by step
# key: English slug. The header and footer partials and the two tool pages
# resolve separately below.
SURFACES: dict[str, str] = {
    "home": "home",
    "solution": "solution",
    "residential-storage": "residential-storage",
    "commercial-storage": "commercial-storage",
    "for-installer": "for-installer",
    "about": "about",
    "capability": "capability",
    "faq-download": "faq-download",
    "privacy-policy": "privacy-policy",
    "services-support": "services-support",
    "gateway-post": "gateway-meter-cloud-monitoring-data-layer",
    "blog-index-template": "template-for-blog-posts-index",
    "thank-you": "thank-you",
}

# Page titles, English slug (or German slug) -> (old, new).
PAGE_TITLES: dict[str, tuple[str, str]] = {
    "linker-planner": ("Linker Planner", "Solution Configurator"),
    "linker-planer": ("Linker Planer", "Lösungskonfigurator"),
    "linker-advisor": ("Linker Advisor", "Genie - Linker's AI assistant"),
    "linker-berater": ("Linker Berater", "Genie – der KI-Assistent von Linker"),
}

# Browser titles that carry a tool promise. The configurator's old title
# promised a price; prices are partner-gated (#11), so the promise narrows.
SEO_TITLES: dict[str, tuple[str, str]] = {
    "linker-planner": (
        "Configure a Storage System and Get a Price | Linker",
        "Configure a Storage System | Linker",
    ),
    "linker-planer": (
        "Speichersystem konfigurieren und Nettopreise einsehen | Linker",
        "Speichersystem konfigurieren | Linker",
    ),
}

# ---------------------------------------------------------------------------
# The header partial.
# ---------------------------------------------------------------------------
HEADER_EN: list[tuple[str, str]] = [
    (
        '<span class="tv-tool-name">Linker Advisor</span>',
        '<span class="tv-tool-name">Genie - Linker\'s AI assistant</span>',
    ),
    (
        '<span class="tv-tool-desc">Bring a model, compatibility question or project detail. Linker finds the next useful step.</span>',
        '<span class="tv-tool-desc">Bring a model, a compatibility question or a project detail. Genie finds the next useful step.</span>',
    ),
    (
        '<span class="tv-tool-name">Linker Planner</span>',
        '<span class="tv-tool-name">Solution Configurator</span>',
    ),
    (
        '<span class="tv-tool-desc">Organise the goal, site and existing equipment into a project direction you can keep refining.</span>',
        '<span class="tv-tool-desc">Bring your goal, site and existing equipment into a complete solution with a bill of materials. The Roof detail step adds the building\'s layout.</span>',
    ),
    (
        '<span class="tv-mobile-link-title">Linker Advisor</span>',
        '<span class="tv-mobile-link-title">Genie - Linker\'s AI assistant</span>',
    ),
    (
        '<span class="tv-mobile-link-title">Linker Planner</span>',
        '<span class="tv-mobile-link-title">Solution Configurator</span>',
    ),
    (
        '<span class="tv-mobile-link-desc">Organise the project direction and keep refining it.</span>',
        '<span class="tv-mobile-link-desc">Configure a complete solution with a bill of materials. The Roof detail step adds the layout.</span>',
    ),
]

HEADER_EN_REMOVE: list[str] = [
    r'<a href="/design-canvas/" class="tv-tool" role="menuitem">.*?</a>\s*',
    r'<a href="/design-canvas/" class="tv-mobile-link">.*?</a>\s*',
]

HEADER_DE: list[tuple[str, str]] = [
    (
        '<span class="tv-tool-name">Linker Berater</span>',
        '<span class="tv-tool-name">Genie – der KI-Assistent von Linker</span>',
    ),
    (
        '<span class="tv-tool-desc">Bringen Sie ein Modell, eine Kompatibilitätsfrage oder ein Projektdetail ein. Linker findet den nächsten nützlichen Schritt.</span>',
        '<span class="tv-tool-desc">Bringen Sie ein Modell, eine Kompatibilitätsfrage oder ein Projektdetail ein. Genie findet den nächsten nützlichen Schritt.</span>',
    ),
    (
        '<span class="tv-tool-name">Linker Planer</span>',
        '<span class="tv-tool-name">Lösungskonfigurator</span>',
    ),
    (
        '<span class="tv-tool-desc">Organisieren Sie Ziel, Standort und vorhandene Ausrüstung in eine Projektrichtung, die Sie weiter verfeinern können.</span>',
        '<span class="tv-tool-desc">Führen Sie Ziel, Standort und vorhandene Ausrüstung zu einer vollständigen Lösung mit Stückliste zusammen. Der Schritt Dachdetails nimmt die Dachfläche auf.</span>',
    ),
    (
        '<span class="tv-mobile-link-title">Linker Berater</span>',
        '<span class="tv-mobile-link-title">Genie – der KI-Assistent von Linker</span>',
    ),
    (
        '<span class="tv-mobile-link-title">Linker Planer</span>',
        '<span class="tv-mobile-link-title">Lösungskonfigurator</span>',
    ),
    (
        '<span class="tv-mobile-link-desc">Organisieren Sie die Projektrichtung und verfeinern Sie sie weiter.</span>',
        '<span class="tv-mobile-link-desc">Konfigurieren Sie eine vollständige Lösung mit Stückliste. Der Schritt Dachdetails nimmt die Dachfläche auf.</span>',
    ),
]

HEADER_DE_REMOVE: list[str] = [
    r'<a href="/de/entwurfsflache/" class="tv-tool" role="menuitem">.*?</a>\s*',
    r'<a href="/de/entwurfsflache/" class="tv-mobile-link">.*?</a>\s*',
]

# ---------------------------------------------------------------------------
# The footer partial's planning panel.
# ---------------------------------------------------------------------------
FOOTER_EN: list[tuple[str, str]] = [
    ("<span>Linker Advisor</span>", "<span>Genie - Linker's AI assistant</span>"),
    ("<span>Linker Planner</span>", "<span>Solution Configurator</span>"),
    (
        '<h2>Plan with Linker</h2><span class="footer-panel-count" aria-hidden="true">04</span>',
        '<h2>Plan with Linker</h2><span class="footer-panel-count" aria-hidden="true">03</span>',
    ),
]

FOOTER_EN_REMOVE: list[str] = [r'<li><a href="/design-canvas/">.*?</li>\s*']

FOOTER_DE: list[tuple[str, str]] = [
    ("<span>Linker Berater</span>", "<span>Genie – der KI-Assistent von Linker</span>"),
    ("<span>Linker Planer</span>", "<span>Lösungskonfigurator</span>"),
    (
        '<h2>Planen mit Linker</h2><span class="footer-panel-count" aria-hidden="true">04</span>',
        '<h2>Planen mit Linker</h2><span class="footer-panel-count" aria-hidden="true">03</span>',
    ),
]

FOOTER_DE_REMOVE: list[str] = [r'<li><a href="/de/entwurfsflache/">.*?</li>\s*']

# The configurator page's old app carries one static helper link to the
# assistant inside its markup (the app itself leaves with #14; the static
# text is what the page shows before the bundle runs).
PLANNER_INLINE_EN: list[tuple[str, str]] = [
    ("not sure? ask Linker Advisor", "not sure? ask Genie"),
]

PLANNER_INLINE_DE: list[tuple[str, str]] = [
    ("unsicher? Linker Berater fragen", "unsicher? Genie fragen"),
]

# ---------------------------------------------------------------------------
# The assistant page's no-JavaScript fallback.
# ---------------------------------------------------------------------------
NOSCRIPT_EN: list[tuple[str, str]] = [
    ("The Linker Advisor needs JavaScript to run.", "Genie needs JavaScript to run."),
]

NOSCRIPT_DE: list[tuple[str, str]] = [
    (
        "Der Linker Berater benötigt JavaScript, um ausgeführt zu werden.",
        "Genie benötigt JavaScript, um zu funktionieren.",
    ),
    (
        'Ohne dieses können Sie <a href="/products/">unsere Produkte</a> ansehen oder an <a href="mailto:sales@de-linker.com">sales@de-linker.com</a> schreiben, und ein Spezialist wird antworten.',
        'Ohne JavaScript können Sie <a href="/de/produkte/">unsere Produkte</a> ansehen oder an <a href="mailto:sales@de-linker.com">sales@de-linker.com</a> schreiben; ein Spezialist antwortet Ihnen.',
    ),
]

# ---------------------------------------------------------------------------
# Site Detail folds and tool-renaming pairs that are specific to one surface.
# Each pair names the SURFACES keys it belongs to. Every pair must be found
# there exactly once.
# ---------------------------------------------------------------------------
BESPOKE_EN: list[tuple[str, str, tuple[str, ...]]] = [
    # For Installer: the tool switcher's first slot becomes the configurator's
    # roof step, the other two rename.
    (
        "<span>01</span>Site Detail</button>",
        "<span>01</span>Roof detail</button>",
        ("for-installer",),
    ),
    (
        "<span>02</span>Planner</button>",
        "<span>02</span>Configurator</button>",
        ("for-installer",),
    ),
    (
        "<span>03</span>Advisor</button>",
        "<span>03</span>Genie</button>",
        ("for-installer",),
    ),
    (
        "Linker Site Detail</h3>",
        "Solution Configurator – Roof detail</h3>",
        ("for-installer",),
    ),
    ("Linker Planner</h3>", "Solution Configurator</h3>", ("for-installer",)),
    ("Linker Advisor</h3>", "Genie</h3>", ("for-installer",)),
    ("Open Linker Site Detail →", "Open the Roof detail step →", ("for-installer",)),
    (
        'aria-label="Play Linker Site Detail preview"',
        'aria-label="Play the Roof detail preview"',
        ("for-installer",),
    ),
    (
        'alt="Linker Site Detail roof planning preview"',
        'alt="Roof detail planning preview in the Solution Configurator"',
        ("for-installer",),
    ),
    (
        'aria-label="Linker Site Detail roof planning"',
        'aria-label="Roof detail planning in the Solution Configurator"',
        ("for-installer",),
    ),
    (
        "Three Linker tools to prepare the installation before you order.",
        "Two Linker tools to prepare the installation before you order.",
        ("for-installer",),
    ),
    (
        "Site Detail maps the layout, Linker Planner sizes the electrical side, and Linker supplies",
        "The Roof detail step maps the layout, the Solution Configurator sizes the electrical side, and Linker supplies",
        ("for-installer",),
    ),
    (
        "Linker Advisor · Technical Resources",
        "Genie · Technical Resources",
        ("for-installer",),
    ),
    (
        "Linker Planner · Solution Sizing",
        "Solution Configurator · System Sizing",
        ("for-installer",),
    ),
    # The M2 copy batch (docs/acceptance/2026-10-16/m2-copy/copy-review.md,
    # the 43-pair table). The strings the 2026-10-14 run's rules did not
    # reach: bare Planner/Advisor uses, the cart ban, and the sentence
    # rewrites the review settled.
    (
        "Site Detail maps usable roof space, module placement around obstructions, and physical dimensions before electrical sizing.",
        "The Roof detail step maps usable roof space, module placement around obstructions, and physical dimensions before electrical sizing.",
        ("for-installer",),
    ),
    # Services & Support: the stage tab keeps its neighbours' shape — a
    # stage name, not the tool's.
    (
        "<h3>Planner Sizing &amp; Compatibility Lists</h3>",
        "<h3>System Sizing &amp; Compatibility Lists</h3>",
        ("services-support",),
    ),
    (
        'aria-label="Planner sizing and compatibility lists"',
        'aria-label="System sizing and compatibility lists"',
        ("services-support",),
    ),
    (
        "<b>Planner Sizing and Compatibility Lists</b>",
        "<b>System Sizing and Compatibility Lists</b>",
        ("services-support",),
    ),
    (
        '<h3 class="lk-sstage-h3">Planner Sizing and Compatibility Lists</h3>',
        '<h3 class="lk-sstage-h3">System Sizing and Compatibility Lists</h3>',
        ("services-support",),
    ),
    (
        "<strong>Deliverable:</strong> Planner Sizing · Complete Parts List",
        "<strong>Deliverable:</strong> System Sizing · Complete Parts List",
        ("services-support",),
    ),
    # FAQ & documents: the English twin of 6863's CTA (the no-JS fallback
    # opens Genie's page, as the German one does).
    (
        'href="/products/" data-linker-assistant-open',
        'href="/genie/" data-linker-assistant-open',
        ("faq-download",),
    ),
    # Services & Support: the three-tool pitch becomes two, the roof folds in.
    (
        "Three tools built for your own pace: size a system in the Linker Planner, map your roof with Site Detail, and ask the Advisor anything about a product or datasheet.",
        "Two tools built for your own pace: size a system and map your roof in the Solution Configurator, and ask Genie anything about a product or datasheet.",
        ("services-support",),
    ),
    (
        "Roof mapping with Linker Site Detail",
        "Roof mapping in the Solution Configurator",
        ("services-support",),
    ),
    (
        "Linker Planner · Site Detail · Advisor",
        "Solution Configurator · Genie",
        ("services-support",),
    ),
    # Application: the tool labels and the satellite-map sentences.
    ("Linker Advisor:", "Genie:", ("solution",)),
    ("Linker Planner:", "Solution Configurator:", ("solution",)),
    (
        "Planner models suitable inverter",
        "The Solution Configurator models suitable inverter",
        ("solution",),
    ),
    ("Site Detail:</strong>", "Roof detail:</strong>", ("solution",)),
    (
        "Site Detail lets you verify",
        "The Roof detail step lets you verify",
        ("solution",),
    ),
    ("Advisor answers instantly", "Genie answers instantly", ("solution",)),
    # Application, M2: the two CTAs and the table cell the name rules did not
    # reach (bare Planner), and the large-project answer's positive form
    # ("cart" is banned outright; AGENTS.md §3).
    (
        "Design with Planner →",
        "Plan with the Solution Configurator →",
        ("solution",),
    ),
    (
        "<td>Storage packages, Planner tools, and Partner pricing</td>",
        "<td>Storage packages, sizing tools, and Partner pricing</td>",
        ("solution",),
    ),
    (
        "cannot simply be placed into an online shopping cart.",
        "are quoted per project.",
        ("solution",),
    ),
    # Commercial Storage, M2: the same bare-Planner CTA.
    (
        "Model Project in Planner →",
        "Model the project in the Solution Configurator →",
        ("commercial-storage",),
    ),
    # Home, M2: the utility card's fourth bullet loses the cart negation.
    (
        "<li>Quoted per site, not from the cart</li>",
        "<li>A project quote for each site</li>",
        ("home",),
    ),
    # Privacy policy, M2: the bare Advisor uses (the visible table, the
    # cookie sentence, the caption's article leftover) and the CSS comments
    # that keep the two mirrors byte-identical. "the Advisor zone" appears
    # twice and travels in the rule channel (BESPOKE_RULES_EN); these
    # strings do not overlap it.
    (
        "put to the Genie",
        "put to Genie",
        ("privacy-policy",),
    ),
    (
        "the Advisor button",
        "the Genie button",
        ("privacy-policy",),
    ),
    (
        "Advisor button zone",
        "Genie button zone",
        ("privacy-policy",),
    ),
    (
        "(session, cart, and login cookies)",
        "(session, solution draft, and login cookies)",
        ("privacy-policy",),
    ),
    (
        "When you ask the Advisor a question",
        "When you ask Genie a question",
        ("privacy-policy",),
    ),
    (
        "not sent with Advisor messages",
        "not sent with your messages to Genie",
        ("privacy-policy",),
    ),
    (
        "Advisor conversations belonging to a signed-in account",
        "Conversations with Genie belonging to a signed-in account",
        ("privacy-policy",),
    ),
    (
        "from the Advisor's history",
        "from your Genie history",
        ("privacy-policy",),
    ),
    # The retired design canvas: one sentence needs the article the renamed
    # tool takes ("for the Solution Configurator") for its English to read
    # whole; the rest of its old names follow the name rules.
    (
        "for Linker Planner and your Project request.",
        "for the Solution Configurator and your Project request.",
        ("design-canvas",),
    ),
]

# Ordered catch-alls for the remaining English mentions. Zero hits in a
# given post are fine; every hit is reported.
NAME_RULES_EN: list[tuple[str, str]] = [
    ("Open the Linker Planner →", "Open the Solution Configurator →"),
    ("in the Linker Planner", "in the Solution Configurator"),
    ("Open Linker Planner →", "Open the Solution Configurator →"),
    ("Open Linker Planner", "Open the Solution Configurator"),
    ("Start in Linker Planner →", "Start in the Solution Configurator →"),
    ("Design in Linker Planner →", "Design in the Solution Configurator →"),
    ("Design in Linker Planner", "Design in the Solution Configurator"),
    (
        "Linker Planner and the compatibility lists",
        "the Solution Configurator and the compatibility lists",
    ),
    ("in Linker Planner", "in the Solution Configurator"),
    ("Linker Planner sizes", "The Solution Configurator sizes"),
    ("Linker Planner takes", "The Solution Configurator takes"),
    ("Linker Planner calculates", "The Solution Configurator calculates"),
    ("Linker Planner can help", "The Solution Configurator can help"),
    ("The Linker Advisor", "Genie"),
    ("the Linker Planner", "the Solution Configurator"),
    ("Linker Advisor", "Genie"),
    ("Linker Planner", "Solution Configurator"),
    ("Linker Site Detail", "Solution Configurator"),
]

BESPOKE_DE: list[tuple[str, str, tuple[str, ...]]] = [
    # Für Installateure.
    (
        "<span>01</span>Standortdetails</button>",
        "<span>01</span>Dachdetails</button>",
        ("for-installer",),
    ),
    (
        "<span>02</span>Planer</button>",
        "<span>02</span>Konfigurator</button>",
        ("for-installer",),
    ),
    (
        "<span>03</span>Berater</button>",
        "<span>03</span>Genie</button>",
        ("for-installer",),
    ),
    (
        "Linker Standortdetails</h3>",
        "Lösungskonfigurator – Dachdetails</h3>",
        ("for-installer",),
    ),
    ("Linker Planer</h3>", "Lösungskonfigurator</h3>", ("for-installer",)),
    ("Linker Berater</h3>", "Genie</h3>", ("for-installer",)),
    (
        "Linker Standortdetails öffnen →",
        "Dachdetail-Schritt öffnen →",
        ("for-installer",),
    ),
    (
        'aria-label="Vorschau von Linker Standortdetails abspielen"',
        'aria-label="Vorschau des Dachdetail-Schritts abspielen"',
        ("for-installer",),
    ),
    (
        'alt="Vorschau der Dachplanung in Linker Standortdetails"',
        'alt="Vorschau der Dachplanung im Lösungskonfigurator"',
        ("for-installer",),
    ),
    (
        'aria-label="Linker Standortdetails Dachplanung"',
        'aria-label="Dachplanung im Lösungskonfigurator"',
        ("for-installer",),
    ),
    (
        "Site Detail erfasst das Layout, der Linker Planer legt die Elektrik aus, und Linker liefert",
        "Der Schritt Dachdetails erfasst das Layout, der Lösungskonfigurator legt die Elektrik aus, und Linker liefert",
        ("for-installer",),
    ),
    (
        "Die Linker Standortdetails erfassen die nutzbare Dachfläche",
        "Der Schritt Dachdetails im Lösungskonfigurator erfasst die nutzbare Dachfläche",
        ("for-installer",),
    ),
    (
        "Linker Berater · Technische Ressourcen",
        "Genie · Technische Ressourcen",
        ("for-installer",),
    ),
    (
        "Linker Planer · Lösungsauslegung",
        "Lösungskonfigurator · Lösungsauslegung",
        ("for-installer",),
    ),
    # The roof step button: it opened the language home ("/de/"); it opens
    # the configurator's roof step, as its renamed label says.
    (
        '<a class="lk-btn-primary" href="/de/">',
        '<a class="lk-btn-primary" href="/de/loesungskonfigurator/?step=roof">',
        ("for-installer",),
    ),
    # FAQ & documents: the Genie tile's CTA keeps its hook (the new tree
    # consumes data-linker-assistant-open) and opens the Genie page rather
    # than the products page when JavaScript does not run.
    (
        'href="/de/produkte/" data-linker-assistant-open',
        'href="/de/genie/" data-linker-assistant-open',
        ("faq-download",),
    ),
    # Service & Support.
    (
        "Drei Werkzeuge für Ihr eigenes Tempo: Legen Sie ein System im Linker Planer aus, erfassen Sie Ihr Dach mit den Linker Standortdetails und fragen Sie den Linker Berater alles zu einem Produkt oder Datenblatt.",
        "Zwei Werkzeuge für Ihr eigenes Tempo: Legen Sie ein System aus und erfassen Sie Ihr Dach im Lösungskonfigurator, und fragen Sie Genie alles zu einem Produkt oder Datenblatt.",
        ("services-support",),
    ),
    (
        "Dacherfassung mit Linker Standortdetails",
        "Dacherfassung im Lösungskonfigurator",
        ("services-support",),
    ),
    (
        "Linker Planer · Linker Standortdetails · Linker Berater",
        "Lösungskonfigurator · Genie",
        ("services-support",),
    ),
    # Service & Support, M2: the stage tab keeps its neighbours' shape — a
    # stage name (Systemauslegung is the German site's own word), not the
    # 56-character tool name.
    (
        "<h3>Planer-Auslegung &amp; Kompatibilitätslisten</h3>",
        "<h3>Systemauslegung &amp; Kompatibilitätslisten</h3>",
        ("services-support",),
    ),
    (
        'aria-label="Planer-Auslegung und Kompatibilitätslisten"',
        'aria-label="Systemauslegung und Kompatibilitätslisten"',
        ("services-support",),
    ),
    (
        "<b>Planer-Auslegung und Kompatibilitätslisten</b>",
        "<b>Systemauslegung und Kompatibilitätslisten</b>",
        ("services-support",),
    ),
    (
        '<h3 class="lk-sstage-h3">Planer-Auslegung und Kompatibilitätslisten</h3>',
        '<h3 class="lk-sstage-h3">Systemauslegung und Kompatibilitätslisten</h3>',
        ("services-support",),
    ),
    (
        "<strong>Ergebnis:</strong> Auslegung im Planer · Vollständige Stückliste",
        "<strong>Ergebnis:</strong> Systemauslegung · Vollständige Stückliste",
        ("services-support",),
    ),
    # Anwendung.
    (
        "Linker Standortdetails:</strong>",
        "Lösungskonfigurator, Schritt Dachdetails:</strong>",
        ("solution",),
    ),
    ("mit den Linker Standortdetails", "im Schritt Dachdetails", ("solution",)),
    ("Linker Berater:</strong>", "Genie:</strong>", ("solution",)),
    ("Linker Planer:</strong>", "Lösungskonfigurator:</strong>", ("solution",)),
    ("antwortet der Berater sofort", "antwortet Genie sofort", ("solution",)),
    # Anwendung, M2: the bare Planer use and the table cell (the German
    # mirrors of 746's pair), and the large-project answer's positive form
    # (Warenkorb is banned outright; banned-de.json).
    (
        "Der Planer modelliert geeignete",
        "Der Lösungskonfigurator modelliert geeignete",
        ("solution",),
    ),
    (
        "<td>Speicherpakete, Planer-Werkzeuge und Partnerpreise</td>",
        "<td>Speicherpakete, Auslegungswerkzeuge und Partnerpreise</td>",
        ("solution",),
    ),
    (
        "lassen sich nicht einfach in einen Online-Warenkorb legen.",
        "werden projektbezogen angeboten.",
        ("solution",),
    ),
    # Startseite, M2: the utility card's fourth bullet loses the cart
    # negation (the German mirror of 13's pair).
    (
        "<li>Angebot pro Standort, nicht aus dem Warenkorb</li>",
        "<li>Projektangebot pro Standort</li>",
        ("home",),
    ),
    # Datenschutz, M2: the German mirrors of 1673's sentence rewrites and
    # the cookie sentence; the CSS comments stay English and byte-identical
    # with the English page's. "the Advisor zone" appears twice and travels
    # in the rule channel (BESPOKE_RULES_DE).
    (
        "(Session-, Warenkorb- und Login-Cookies)",
        "(Session-, Lösungsentwurf- und Login-Cookies)",
        ("privacy-policy",),
    ),
    (
        "Wenn Sie dem Berater eine Frage stellen",
        "Wenn Sie Genie eine Frage stellen",
        ("privacy-policy",),
    ),
    (
        "nicht mit Berater-Nachrichten übermittelt",
        "nicht mit Ihren Nachrichten an Genie übermittelt",
        ("privacy-policy",),
    ),
    (
        "Berater-Konversationen, die zu einem angemeldeten Konto gehören",
        "Konversationen mit Genie, die zu einem angemeldeten Konto gehören",
        ("privacy-policy",),
    ),
    (
        "aus dem Verlauf des Beraters löschen",
        "aus Ihrem Genie-Verlauf löschen",
        ("privacy-policy",),
    ),
    (
        "the Advisor button",
        "the Genie button",
        ("privacy-policy",),
    ),
    (
        "Advisor button zone",
        "Genie button zone",
        ("privacy-policy",),
    ),
    # The retired design canvas: the honesty line needs the article the
    # renamed tool takes ("für den Lösungskonfigurator").
    (
        "für Linker Planer und Ihre Projektanfrage.",
        "für den Lösungskonfigurator und Ihre Projektanfrage.",
        ("design-canvas",),
    ),
]

# German keeps the article, so the configurator is one catch-all; the
# assistant drops its article with the name. The English spelling stays in
# the rules for the retired pages, whose bodies and comments kept it.
NAME_RULES_DE: list[tuple[str, str]] = [
    ("Der Linker Berater", "Genie"),
    ("der Linker Berater", "Genie"),
    ("den Linker Berater", "Genie"),
    ("dem Linker Berater", "Genie"),
    ("des Linker Beraters", "von Genie"),
    ("im Linker Berater", "von Genie"),
    ("Linker Berater", "Genie"),
    ("Linker Planer", "Lösungskonfigurator"),
    ("Linker Planner", "Lösungskonfigurator"),
    ("Linker Standortdetails", "Dachdetails"),
]

# M2 sentence pairs that occur more than once in one page and therefore
# travel in the rule channel (any count, one report line per count), the
# same shape as the name rules. Every entry is scoped to its surfaces and
# must have hit: verify refuses both a leftover old string and a missing
# new one.
BESPOKE_RULES_EN: list[tuple[str, str, tuple[str, ...]]] = [
    ("the Advisor zone", "the Genie zone", ("privacy-policy",)),
]

BESPOKE_RULES_DE: list[tuple[str, str, tuple[str, ...]]] = [
    ("the Advisor zone", "the Genie zone", ("privacy-policy",)),
]

# M2's pair for each of the two posts outside the surfaces above — the
# utility page's meta description and the terms page's price sentence (the
# copy review's table C3, C4, D34, D35).
UTILITY_STORAGE_DESC_EN = (
    "CRRC, Pylontech and GoodWe container BESS from 1.0 to 6.9 MWh, with datasheets on file, quoted per project, not from the cart.",
    "CRRC, Pylontech and GoodWe container BESS from 1.0 to 6.9 MWh, with datasheets on file, quoted per project.",
)
UTILITY_STORAGE_DESC_DE = (
    "Container-Batteriespeicher von CRRC, Pylontech und GoodWe mit 1,0 bis 6,9 MWh, mit hinterlegten Datenblättern, projektbezogen angeboten statt über den Warenkorb.",
    "Container-Batteriespeicher von CRRC, Pylontech und GoodWe mit 1,0 bis 6,9 MWh, mit hinterlegten Datenblättern, projektbezogen angeboten.",
)
TERMS_PRICES_EN = (
    "apply automatically in the cart",
    "apply automatically in the solution draft",
)
TERMS_PRICES_DE = (
    "werden im Warenkorb automatisch",
    "werden im Lösungsentwurf automatisch",
)

# A PHP diagnostic the WP-CLI phar may print into stdout ahead of the value
# (9-i18n.py, same phar, same machine).
PHP_DIAGNOSTIC = re.compile(
    r"^(?:PHP )?(?:Deprecated|Warning|Notice|Fatal error|Parse error): "
    r".+ in .+ on line \d+$"
)

# Resolves every slug this migration touches to (English id, German id)
# through Polylang; the payload arrives as argv[1], base64.
RESOLVE_PHP = """
$pairs = json_decode(base64_decode($args[0]), true);
$out = array();
foreach ($pairs as $key => $slug) {
    $candidates = is_array($slug) ? $slug : array($slug);
    // The pages and partials this migration edits first: a presented site's
    // LiveCanvas template carries the page's own slug as its post_name (the
    // per-post template lookup is by that slug), and the template is not
    // what this migration edits — it is only a fallback for older sites
    // whose headers were templates.
    $query = array(
        'post_name__in' => $candidates, 'post_status' => 'any', 'numberposts' => 1,
        'post_type' => array('page', 'post', 'lc_partial'),
        'lang' => 'en', 'fields' => 'ids', 'suppress_filters' => false,
    );
    $found = get_posts($query);
    if (!$found) {
        $query['post_type'] = array('lc_dynamic_template');
        $found = get_posts($query);
    }
    $en = $found ? (int) reset($found) : 0;
    $twin = $en ? pll_get_post_translations($en) : array();
    $out[$key] = array('en' => $en, 'de' => (int) ($twin['de'] ?? 0));
}
echo wp_json_encode($out);
"""

# Marks the German twins of the given English ids as hand-edited: every
# field reviewed (a machine never overwrites them) and the fingerprint of
# the new English, so the pair counts as synced.
STATE_PHP = """
$ids = json_decode(base64_decode($args[0]), true);
$state = new Linker\\I18n\\Translation\\State();
$fingerprint = new ReflectionMethod(
    Linker\\I18n\\Translation\\Translator::class, 'fingerprint'
);
$fingerprint->setAccessible(true);
$done = 0;
foreach ($ids as $id) {
    $post = get_post((int) $id);
    if (!$post instanceof WP_Post) { continue; }
    $twin = pll_get_post_translations((int) $id);
    if (empty($twin['de'])) { continue; }
    $values = array(
        'post_title' => array($post->post_title, false),
        'post_excerpt' => array($post->post_excerpt, true),
        'post_content' => array($post->post_content, true),
    );
    $state->save('post', (int) $twin['de'], $fingerprint->invoke(null, $values), array(), array(
        'post_title' => '*', 'post_excerpt' => '*', 'post_content' => '*',
    ));
    $state->set_status('post', (int) $id, 'synced', '#12: hand-written German');
    $done++;
}
echo wp_json_encode(array('marked' => $done));
"""

# Reads the German sources' legacy metas: `_linker_de_content` on every
# listed English post, `_linker_de_title` where the key exists. The 9-i18n
# import (tools/migrate/9-i18n.py, TRANSLATED_TYPES page/post/product) reads
# exactly these when it makes or refreshes a German twin, so they must say
# what the German page says — the 2026-10-15 deploy re-imported them and
# reverted the 2026-10-14 rename of every German page.
LEGACY_META_PHP = """
$ids = json_decode(base64_decode($args[0]), true);
$out = array();
foreach ($ids as $id) {
    $row = array(
        'content' => (string) get_post_meta((int) $id, '_linker_de_content', true),
    );
    if (metadata_exists('post', (int) $id, '_linker_de_title')) {
        $row['title'] = (string) get_post_meta((int) $id, '_linker_de_title', true);
    }
    $out[(string) $id] = $row;
}
echo wp_json_encode($out);
"""

# Writes metas: {post_id: {meta_key: value}}, skipping values already in
# place. The payload arrives base64 in $args[0]; the German sources carry
# whole page bodies (the header partial is 125 KB), so callers deliver it
# through eval_php_embedded, where the payload rides the stdin PHP text
# instead of one execve argument (2026-10-16: the argv channel died with
# `/bin/bash: Argument list too long` mid-apply).
META_WRITE_PHP = """
$payload = json_decode(base64_decode($args[0]), true);
$written = 0;
foreach ($payload as $id => $values) {
    foreach ($values as $key => $value) {
        if (get_post_meta((int) $id, $key, true) === $value) { continue; }
        update_post_meta((int) $id, $key, wp_slash($value));
        $written++;
    }
}
echo wp_json_encode(array('written' => $written));
"""

# The media library's alternative texts that name an old tool, renamed with
# the tool. Rules (every hit), aimed at `_wp_attachment_image_alt` alone:
# the file names stay as they are — six pages reference the `linker-advisor-*`
# media, and renaming files is link-breaking work this migration must not do.
ALT_RULES: list[tuple[str, str]] = [
    ("Linker Site Detail", "Solution Configurator"),
    ("Linker Advisor", "Genie"),
    ("Linker Planner", "Solution Configurator"),
]

ALT_READ_PHP = """
// eval-file runs inside a function scope: $wpdb needs declaring (measured
// 2026-10-16 — without this line the live plan ended in a critical error).
global $wpdb;
$needles = json_decode(base64_decode($args[0]), true);
$conds = array();
foreach ($needles as $needle) {
    $conds[] = $wpdb->prepare('meta_value LIKE %s', '%' . $wpdb->esc_like($needle) . '%');
}
$rows = $wpdb->get_results(
    "SELECT post_id, meta_value FROM {$wpdb->postmeta}"
    . " WHERE meta_key = '_wp_attachment_image_alt' AND (" . implode(' OR ', $conds) . ")"
);
$out = array();
foreach ($rows as $row) {
    $out[(string) $row->post_id] = $row->meta_value;
}
echo wp_json_encode($out);
"""


def renamed_alt(alt: str) -> str:
    """One alternative text with every old tool name replaced."""
    for old, new in ALT_RULES:
        alt = alt.replace(old, new)
    return alt


def legacy_meta_updates(
    plan: list[Step],
    german: dict[int, str],
    metas: dict[str, dict[str, str]],
) -> list[tuple[int, dict[str, str]]]:
    """What the German sources' metas must say once this migration has run:
    the German page's new content, and the new title where the source's
    `_linker_de_title` still carries the old one. This is what keeps the
    9-i18n import from writing the stale German back onto the pages."""
    updates: list[tuple[int, dict[str, str]]] = []
    for step in plan:
        if step.lang != "de":
            continue
        row = metas.get(str(step.english_id)) or {}
        values: dict[str, str] = {}
        content = row.get("content", "")
        if content and content != german.get(step.post_id, ""):
            values["_linker_de_content"] = german.get(step.post_id, "")
        if step.title and row.get("title") == step.title[0]:
            values["_linker_de_title"] = step.title[1]
        if any(values.values()):
            updates.append((step.english_id, values))
    return updates


class WP:
    """WP-CLI, as a command prefix (the 9-i18n.py wrapper)."""

    def __init__(self, command: str, user: str | None) -> None:
        self.prefix = shlex.split(command)
        self.user = user

    def run(self, *args: str, stdin: str | None = None, as_user: bool = False) -> str:
        """Run one command.

        A prefix that starts with `ssh` is remote, and its arguments travel
        quoted as one word: ssh joins its argv with spaces and the login shell
        splits again, so `--post_title=Genie - Linker's AI assistant` would
        break apart (the same rule 9-i18n.py states; measured on this site
        2026-10-14). A local prefix keeps argv semantics.
        """
        tail = list(args)
        if as_user and self.user:
            tail.append(f"--user={self.user}")
        if self.prefix and self.prefix[0] == "ssh":
            command = [
                *self.prefix[:-1],
                " ".join([self.prefix[-1], *(shlex.quote(arg) for arg in tail)]),
            ]
        else:
            command = [*self.prefix, *tail]
        result = subprocess.run(
            command, input=stdin, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            raise SystemExit(
                f"wp {' '.join(args[:3])} failed:\n{result.stderr.strip()}"
            )
        lines = result.stdout.splitlines()
        return "\n".join(line for line in lines if not PHP_DIAGNOSTIC.match(line))

    def json(self, *args: str, stdin: str | None = None, as_user: bool = False) -> Any:
        out = self.run(*args, stdin=stdin, as_user=as_user)
        start = min((i for i in (out.find("["), out.find("{")) if i >= 0), default=-1)
        return json.loads(out[start:]) if start >= 0 else None

    def eval_php(self, code: str, payload: Any) -> Any:
        """Runs PHP with the payload as base64 argv[1]; returns its JSON.

        The code travels on standard input (`eval-file -`): a temp path exists
        on this machine, and a remote WP-CLI cannot open it (measured
        2026-10-14, this migration's first production run — the remote wp
        answered "'/var/folders/…' does not exist"). The base64 payload is an
        argument and stays safe either way.

        For payloads measured in kilobytes rather than bytes use
        `eval_php_embedded`: one execve argument has a size ceiling, and the
        German source metas carry whole page bodies.
        """
        return self.json(
            "eval-file",
            "-",
            base64.b64encode(json.dumps(payload).encode()).decode(),
            stdin="<?php\n" + code,
        )

    def eval_php_embedded(self, code: str, payload: Any) -> Any:
        """Runs PHP with the payload embedded in the source, which travels
        on standard input (`eval-file -`).

        For payloads measured in kilobytes rather than bytes: one execve
        argument has a size ceiling, and the German source metas carry whole
        page bodies. Measured 2026-10-16 (this migration's second production
        apply): the first German-source batch, led by the 125 KB header
        partial, died in `/bin/bash: Argument list too long` on the ssh
        command line and the write phase never ran. Base64 inside the PHP
        text has no such ceiling — stdin is a pipe, not an argument — and
        `$args[0]` is set the same way, so the snippets stay one form.
        """
        blob = base64.b64encode(json.dumps(payload).encode()).decode()
        return self.json(
            "eval-file",
            "-",
            stdin=f"<?php\n$args = array(0 => '{blob}');\n" + code,
        )


def resolve(wp: WP) -> dict[str, dict[str, int]]:
    slugs = {
        **SURFACES,
        "header": "header",
        "footer": "footer",
        # The configurator's slug before and after the 2026-10-12 move, so
        # plan and apply run on a site at either address.
        "linker-planner": ("linker-planner", "solution-configurator"),
        # The advisor's slug before and after the 2026-10-13 move, so plan
        # and apply run on a site at either address.
        "linker-advisor": ("linker-advisor", "genie"),
        "design-canvas": "design-canvas",
        "quote-configurator": "quote-configurator",
        # The duplicate "has moved" notice and the request-a-project
        # placeholder: retired pages, but their content and metas still
        # name the old tools, and the grep gate counts drafts too.
        "quote-configurator-2": "quote-configurator-2",
        "request-a-project": "request-a-project",
        # M2's two pages outside the marketing surfaces (the utility page's
        # meta description, the terms page's price sentence).
        "utility-storage": "utility-storage",
        "terms-of-sale": "terms-of-sale",
    }
    resolved: dict[str, dict[str, int]] = wp.eval_php(RESOLVE_PHP, slugs)
    missing = sorted(k for k, v in resolved.items() if not v["en"])
    if missing:
        raise SystemExit(f"English post not found for: {', '.join(missing)}")
    no_de = sorted(k for k, v in resolved.items() if not v["de"])
    if no_de:
        raise SystemExit(f"German twin not found for: {', '.join(no_de)}")
    return resolved


class Step:
    """One post's edit: literal pairs (each exactly once), regex removals
    (each exactly once) and ordered catch-all rules (any count). The
    english_id is the source whose translation state the write marks.

    required_rules are the rules this step's page must have taken once the
    migration has run — the M2 sentence pairs that occur more than once.
    They are checked by verify exactly like pairs' new strings; the rules
    themselves are applied as part of `rules`."""

    def __init__(
        self,
        key: str,
        post_id: int,
        english_id: int,
        pairs: list[tuple[str, str]] | None = None,
        removes: list[str] | None = None,
        rules: list[tuple[str, str]] | None = None,
        required_rules: list[tuple[str, str]] | None = None,
        title: tuple[str, str] | None = None,
        seo: tuple[str, str] | None = None,
        seo_desc: tuple[str, str] | None = None,
        status: str | None = None,
    ) -> None:
        self.key = key
        self.post_id = post_id
        self.english_id = english_id
        self.lang = key.rsplit("-", 1)[-1]
        self.pairs = pairs or []
        self.removes = removes or []
        self.rules = rules or []
        self.required_rules = required_rules or []
        self.title = title
        self.seo = seo
        self.seo_desc = seo_desc
        self.status = status

    def planned(self, content: str) -> str:
        return self.apply(content, report=lambda message: None)

    def apply(self, content: str, report: Any) -> str:
        for old, new in self.pairs:
            count = content.count(old)
            if count == 0:
                if new in content:
                    continue  # a re-run: this pair is already in place
                raise SystemExit(
                    f"{self.key}: neither old nor new string found: {old[:100]!r}"
                )
            if count != 1:
                raise SystemExit(
                    f"{self.key}: expected 1x, found {count}x: {old[:100]!r}"
                )
            content = content.replace(old, new)
            report(f"{self.key}: {self._brief(old)} -> {self._brief(new)}")
        for pattern in self.removes:
            found = re.findall(pattern, content, flags=re.S)
            if not found:
                continue  # a re-run: already removed
            if len(found) != 1:
                raise SystemExit(
                    f"{self.key}: removal expected 1x, found {len(found)}x: {pattern}"
                )
            content = re.sub(pattern, "", content, flags=re.S)
            report(f"{self.key}: removed {self._brief(pattern)}")
        for old, new in self.rules:
            count = content.count(old)
            if count:
                content = content.replace(old, new)
                report(f"{self.key}: {count}x {self._brief(old)} -> {self._brief(new)}")
        return content

    @staticmethod
    def _brief(text: str) -> str:
        return repr(text[:72])


# ---------------------------------------------------------------------------
# The header partials' images.
# ---------------------------------------------------------------------------
IMAGE_TAG = re.compile(r"<img\b[^>]*>", re.S)


def unresolved_menu_images(content: str) -> list[str]:
    """The header's images that would not load, one fault per image.

    Spec 12 item 8 (2026-10-14, closed out 2026-10-15) is the live site's
    own form: every menu image resolves through a plain src, and the
    browser's own loading attribute decides when it is fetched (the live
    checkpoint carries the desktop menu cards as `src=... loading="lazy"`
    and the drawer rail as plain `src`; see docs/specs/12-site-chrome.md
    item 8). There is no hydration script at all — menu-images.js retired
    with its enqueue (closure decision 8 of 2026-10-15): the review
    harness proved the plain src resolves at load time (13/13 loaded) and
    the script was inert without data-src. A deferred data-src renders as
    an empty box on every open path, which is how the panel and drawer
    thumbnails broke. This is the guard that keeps a re-run or a hand edit
    from writing that form back. The src check reads the attribute value
    quote-independently, so single- and double-quoted markup are both
    judged by the value, not the quoting.
    """

    faults: list[str] = []
    for tag in IMAGE_TAG.findall(content):
        if "data-src" in tag:
            faults.append(f"deferred to data-src: {tag[:90]}")
            continue
        src = re.search(r"""\bsrc\s*=\s*(["'])(.*?)\1""", tag)
        if src is None or "" == src.group(2):
            faults.append(f"no resolving src: {tag[:90]}")
    return faults


# The Site Detail links fold into the configurator's roof step, and the two
# tools' addresses follow the pages. Rules, not pairs: the targets moved with
# the pages (owner ruling 2026-10-12), and a page an earlier run already
# rewrote carries the intermediate address — a rule upgrades it, a strict
# pair would refuse the page. The bare address forms come last: they catch
# the retired pages' comments and redirect scripts, and the media file names
# (`linker-advisor-….mp4`) never match them because the pattern ends in a
# slash.
LINK_RULES_EN: list[tuple[str, str]] = [
    ('href="/design-canvas/"', 'href="/solution-configurator/?step=roof"'),
    ('href="/linker-planner/?step=roof"', 'href="/solution-configurator/?step=roof"'),
    ('href="/linker-advisor/"', 'href="/genie/"'),
    ('href="/linker-planner/"', 'href="/solution-configurator/"'),
    ("/de/linker-planer/", "/de/loesungskonfigurator/"),
    ("/linker-planner/", "/solution-configurator/"),
]
LINK_RULES_DE: list[tuple[str, str]] = [
    ('href="/de/entwurfsflache/"', 'href="/de/loesungskonfigurator/?step=roof"'),
    (
        'href="/de/linker-planer/?step=roof"',
        'href="/de/loesungskonfigurator/?step=roof"',
    ),
    ('href="/linker-advisor/"', 'href="/de/genie/"'),
    ('href="/linker-planner/"', 'href="/de/loesungskonfigurator/"'),
    ("/de/linker-planer/", "/de/loesungskonfigurator/"),
    ("/linker-planer/", "/de/loesungskonfigurator/"),
    ("/linker-planner/", "/de/loesungskonfigurator/"),
]


def bespoke_pairs(
    key: str, bespoke: list[tuple[str, str, tuple[str, ...]]]
) -> list[tuple[str, str]]:
    """The surface-specific pairs of one step key, in order."""
    return [(old, new) for old, new, where in bespoke if key in where]


def steps(ids: dict[str, dict[str, int]]) -> list[Step]:
    """The whole edit, in write order: partials, tool pages, the retired
    pages, then the marketing surfaces.

    The header's menu images are not this migration's business. Both
    partials resolve their thumbnails through their own src — the live
    site's own form (spec 12 item 8, rewritten 2026-10-14) — and an
    earlier version of this file deferred them to data-src after its
    pairs ran, so a re-run wrote the empty-box form back onto the
    instance. That transform is retired and `do_verify` refuses the
    deferred form; instance content that still carries it heals through
    `present`, which writes the repo partials verbatim.
    """
    plan: list[Step] = [
        Step(
            "header-en",
            ids["header"]["en"],
            ids["header"]["en"],
            HEADER_EN,
            HEADER_EN_REMOVE,
        ),
        Step(
            "header-de",
            ids["header"]["de"],
            ids["header"]["en"],
            HEADER_DE,
            HEADER_DE_REMOVE,
        ),
        Step(
            "footer-en",
            ids["footer"]["en"],
            ids["footer"]["en"],
            FOOTER_EN,
            FOOTER_EN_REMOVE,
        ),
        Step(
            "footer-de",
            ids["footer"]["de"],
            ids["footer"]["en"],
            FOOTER_DE,
            FOOTER_DE_REMOVE,
        ),
        Step(
            "linker-advisor-en",
            ids["linker-advisor"]["en"],
            ids["linker-advisor"]["en"],
            NOSCRIPT_EN,
            rules=LINK_RULES_EN,
            title=PAGE_TITLES["linker-advisor"],
        ),
        Step(
            "linker-berater-de",
            ids["linker-advisor"]["de"],
            ids["linker-advisor"]["en"],
            NOSCRIPT_DE,
            rules=LINK_RULES_DE,
            title=PAGE_TITLES["linker-berater"],
        ),
        Step(
            "linker-planner-en",
            ids["linker-planner"]["en"],
            ids["linker-planner"]["en"],
            PLANNER_INLINE_EN,
            rules=LINK_RULES_EN,
            title=PAGE_TITLES["linker-planner"],
            seo=SEO_TITLES["linker-planner"],
        ),
        Step(
            "linker-planer-de",
            ids["linker-planner"]["de"],
            ids["linker-planner"]["en"],
            PLANNER_INLINE_DE,
            rules=LINK_RULES_DE,
            title=PAGE_TITLES["linker-planer"],
            seo=SEO_TITLES["linker-planer"],
        ),
        # The retired pages: their bodies, titles and SEO metas lose the old
        # tool names and addresses; they stay drafts.
        Step(
            "design-canvas-en",
            ids["design-canvas"]["en"],
            ids["design-canvas"]["en"],
            bespoke_pairs("design-canvas", BESPOKE_EN),
            rules=NAME_RULES_EN + LINK_RULES_EN,
            seo=(
                "Linker Site Detail: Trace the Roof, Sharpen the Sizing",
                "Solution Configurator: Trace the Roof, Sharpen the Sizing",
            ),
            status="draft",
        ),
        Step(
            "design-canvas-de",
            ids["design-canvas"]["de"],
            ids["design-canvas"]["en"],
            bespoke_pairs("design-canvas", BESPOKE_DE),
            rules=NAME_RULES_DE + LINK_RULES_DE,
            seo=(
                "Linker Standortdetails: Dach einzeichnen, Auslegung schärfen",
                "Dachdetails: Dach einzeichnen, Auslegung schärfen",
            ),
            status="draft",
        ),
        Step(
            "quote-configurator-en",
            ids["quote-configurator"]["en"],
            ids["quote-configurator"]["en"],
            rules=NAME_RULES_EN + LINK_RULES_EN,
            title=("Linker Planner has moved", "Solution Configurator has moved"),
            seo_desc=(
                "The Linker Planner has moved: open the Linker Planner to size an inverter and battery system from your site data and get a bill of materials.",
                "The Solution Configurator has moved: open the Solution Configurator to size an inverter and battery system from your site data and get a bill of materials.",
            ),
            status="draft",
        ),
        Step(
            "quote-configurator-de",
            ids["quote-configurator"]["de"],
            ids["quote-configurator"]["en"],
            rules=NAME_RULES_DE + LINK_RULES_DE,
            title=(
                "Der Linker Planner ist umgezogen",
                "Der Lösungskonfigurator ist umgezogen",
            ),
            seo_desc=(
                "Der Linker Planer ist umgezogen: Öffnen Sie den Linker Planer, um ein Wechselrichter- und Batteriesystem anhand Ihrer Standortdaten auszulegen und eine Stückliste zu erhalten.",
                "Der Lösungskonfigurator ist umgezogen: Öffnen Sie den Lösungskonfigurator, um ein Wechselrichter- und Batteriesystem anhand Ihrer Standortdaten auszulegen und eine Stückliste zu erhalten.",
            ),
            status="draft",
        ),
        Step(
            "quote-configurator-2-en",
            ids["quote-configurator-2"]["en"],
            ids["quote-configurator-2"]["en"],
            rules=NAME_RULES_EN + LINK_RULES_EN,
            title=("Linker Planner has moved", "Solution Configurator has moved"),
            status="draft",
        ),
        Step(
            "quote-configurator-2-de",
            ids["quote-configurator-2"]["de"],
            ids["quote-configurator-2"]["en"],
            rules=NAME_RULES_DE + LINK_RULES_DE,
            title=(
                "Der Linker Planner ist umgezogen",
                "Der Lösungskonfigurator ist umgezogen",
            ),
            status="draft",
        ),
        Step(
            "request-a-project-en",
            ids["request-a-project"]["en"],
            ids["request-a-project"]["en"],
            rules=NAME_RULES_EN + LINK_RULES_EN,
            title=("Linker Planner", "Solution Configurator"),
            status="draft",
        ),
        Step(
            "request-a-project-de",
            ids["request-a-project"]["de"],
            ids["request-a-project"]["en"],
            rules=NAME_RULES_DE + LINK_RULES_DE,
            title=("Linker Planner", "Lösungskonfigurator"),
            status="draft",
        ),
        # M2's two posts outside the marketing surfaces: the utility page's
        # meta description and the terms page's price sentence (the copy
        # review's table C3, C4, D34, D35). These steps carry no name or
        # link rules: the review scoped these pages to exactly these strings.
        Step(
            "utility-storage-en",
            ids["utility-storage"]["en"],
            ids["utility-storage"]["en"],
            seo_desc=UTILITY_STORAGE_DESC_EN,
        ),
        Step(
            "utility-storage-de",
            ids["utility-storage"]["de"],
            ids["utility-storage"]["en"],
            seo_desc=UTILITY_STORAGE_DESC_DE,
        ),
        Step(
            "terms-of-sale-en",
            ids["terms-of-sale"]["en"],
            ids["terms-of-sale"]["en"],
            [TERMS_PRICES_EN],
        ),
        Step(
            "terms-of-sale-de",
            ids["terms-of-sale"]["de"],
            ids["terms-of-sale"]["en"],
            [TERMS_PRICES_DE],
        ),
    ]
    for key in SURFACES:
        for lang, rules, bespoke, links, surface_rules in (
            (
                "en",
                NAME_RULES_EN,
                BESPOKE_EN,
                LINK_RULES_EN,
                BESPOKE_RULES_EN,
            ),
            (
                "de",
                NAME_RULES_DE,
                BESPOKE_DE,
                LINK_RULES_DE,
                BESPOKE_RULES_DE,
            ),
        ):
            post_id = ids[key][lang]
            if not post_id:
                continue
            pairs = bespoke_pairs(key, bespoke)
            required = [(old, new) for old, new, where in surface_rules if key in where]
            plan.append(
                Step(
                    f"{key}-{lang}",
                    post_id,
                    ids[key]["en"],
                    pairs,
                    rules=rules + links + required,
                    required_rules=required,
                )
            )
    return plan


def rename_slugs(wp: WP, ids: dict[str, dict[str, int]], write: bool) -> None:
    """The configurator's page answers its new address: the page moves from
    /linker-planner/ to /solution-configurator/ and its German twin from
    /de/linker-planer/ to /de/loesungskonfigurator/ (owner ruling
    2026-10-12, the slug is not kept); the former addresses 301 through the
    plugin's map. Idempotent: a page already at its new slug is reported
    and left, and anything else is refused rather than renamed.

    The German configurator carries a second historical slug: the same-slug
    rule left it on the English /solution-configurator/ from the rename
    until 2026-10-16, when the deployment window moved it to its own
    /de/loesungskonfigurator/. A snapshot taken in that window — e.g. the
    2026-10-15 one the review suite loads — holds the English slug on the
    German page, so both slugs are accepted going in; anything else is
    still refused."""
    for key, post_id, before, after in (
        (
            "linker-planner-en",
            ids["linker-planner"]["en"],
            ("linker-planner",),
            "solution-configurator",
        ),
        (
            "linker-planer-de",
            ids["linker-planner"]["de"],
            ("linker-planer", "solution-configurator"),
            "loesungskonfigurator",
        ),
        (
            "linker-advisor-en",
            ids["linker-advisor"]["en"],
            ("linker-advisor",),
            "genie",
        ),
        (
            "linker-berater-de",
            ids["linker-advisor"]["de"],
            ("linker-berater",),
            "genie",
        ),
    ):
        current = wp.run("post", "get", str(post_id), "--field=post_name").strip()
        if current == after:
            print(f"{key} #{post_id}: slug already {after}", flush=True)
            continue
        if current not in before:
            raise SystemExit(f"{key} #{post_id}: unexpected slug {current!r}")
        print(f"{key} #{post_id}: slug {current} -> {after}", flush=True)
        if write:
            wp.run("post", "update", str(post_id), f"--post_name={after}", as_user=True)


def read_post(wp: WP, post_id: int) -> dict[str, str]:
    fields = wp.json("post", "get", str(post_id), "--format=json")
    return {
        "post_title": fields["post_title"],
        "post_content": fields["post_content"],
        "post_status": fields["post_status"],
    }


def apply_meta_pair(
    wp: WP,
    post_id: int,
    field: str,
    key: str,
    pair: tuple[str, str],
    write: bool,
) -> str:
    """One SEO meta pair, reported and — when asked — written. The three
    states are the old value, the new value and absent; anything else is
    refused rather than overwritten.

    Absent is not a failure: the 2026-10-15 i18n import deletes a German
    twin's SEO meta where the English carries one and the dictionary has
    no German (Twins::meta deletes on an empty value; measured on #6693's
    title and #6633's description). Writing it back would be deleted again
    on that import's next run, so this reports it and leaves it alone."""
    current = seo_meta(wp, post_id).get(field, "")
    if current == pair[1]:
        return f"seo {field}: already new"
    if current == "":
        return f"seo {field}: meta absent (the i18n import wipes it); left alone"
    if current != pair[0]:
        raise SystemExit(
            f"post #{post_id}: seo {field} is neither old nor new: {current[:90]!r}"
        )
    if write:
        wp.run("post", "meta", "update", str(post_id), key, pair[1], as_user=True)
    return f"seo {field}: {pair[0][:60]!r} -> {pair[1][:60]!r}"


def meta_lines(wp: WP, step: Step, write: bool) -> list[str]:
    """The SEO meta pairs of one step, reported (and written when asked)."""
    lines: list[str] = []
    for field, key, pair in (
        ("title", "_seopress_titles_title", step.seo),
        ("desc", "_seopress_titles_desc", step.seo_desc),
    ):
        if pair:
            lines.append(apply_meta_pair(wp, step.post_id, field, key, pair, write))
    return lines


def german_sources_phase(
    wp: WP, plan: list[Step], german: dict[int, str], write: bool
) -> set[int]:
    """The German sources' legacy metas: report the stale copies, and (on a
    write) point them at the German pages' new state, so the 9-i18n import
    keeps the rename instead of reverting it from them. Returns the English
    ids it refreshed — the hand-edited marking needs them on a re-run,
    where no content is `touched` any more."""
    sources = sorted({step.english_id for step in plan if step.lang == "de"})
    metas: dict[str, dict[str, str]] = wp.eval_php(LEGACY_META_PHP, sources) or {}
    updates = legacy_meta_updates(plan, german, metas)
    wanted = {post_id for post_id, _values in updates}
    for step in plan:
        if step.lang != "de":
            continue
        row = metas.get(str(step.english_id)) or {}
        if not row:
            continue
        new_title = (
            step.title[1] if step.title and row.get("title") == step.title[0] else None
        )
        stale = stale_tokens(row.get("content", ""))
        if step.english_id not in wanted and not stale and not new_title:
            continue
        state = (
            "-> follows the German page"
            if step.english_id in wanted
            else "(already in step)"
        )
        print(
            f"    german source #{step.english_id} `_linker_de_content`:"
            f" {', '.join(stale) if stale else 'no old tokens'} {state}"
        )
        if new_title:
            print(
                f"    german source #{step.english_id} `_linker_de_title`:"
                f" -> {new_title!r}"
            )
    if not write or not updates:
        return set()
    written = 0
    # One post per call, payload embedded in the source (eval_php_embedded): the
    # largest `_linker_de_content` is the 125 KB header partial, past
    # the one-argument ceiling of the base64 channel (2026-10-16).
    for post_id, values in updates:
        batch = {str(post_id): values}
        out = wp.eval_php_embedded(META_WRITE_PHP, batch)
        written += int(out.get("written", 0)) if isinstance(out, dict) else 0
    print(f"german source metas: {written} values refreshed", flush=True)
    return {post_id for post_id, _values in updates}


def attachment_alts_phase(wp: WP, write: bool) -> None:
    """The media library's alternative texts: report each stale alt, and
    (on a write) store the renamed one. File names stay untouched."""
    alts: dict[str, str] = wp.eval_php(ALT_READ_PHP, list(OLD_NAMES)) or {}
    changes: dict[str, str] = {}
    for post_id, alt in sorted(alts.items(), key=lambda row: int(row[0])):
        new = renamed_alt(alt)
        if new == alt:
            continue
        changes[post_id] = new
        print(f"media #{post_id}: {alt[:72]!r} -> {new[:72]!r}")
    if write and changes:
        written = 0
        items = list(changes.items())
        # Eight alts per call; the payload travels as a file, the alts are
        # short.
        for start in range(0, len(items), 8):
            batch = {
                post_id: {"_wp_attachment_image_alt": alt}
                for post_id, alt in items[start : start + 8]
            }
            out = wp.eval_php_embedded(META_WRITE_PHP, batch)
            written += int(out.get("written", 0)) if isinstance(out, dict) else 0
        print(f"media alts: {written} refreshed", flush=True)


def do_plan(wp: WP) -> int:
    ids = resolve(wp)
    plan = steps(ids)
    german: dict[int, str] = {}
    for step in plan:
        post = read_post(wp, step.post_id)
        changes: list[str] = []
        new = step.apply(post["post_content"], changes.append)
        fields = []
        if new != post["post_content"]:
            fields.append("content")
        if step.title and post["post_title"] == step.title[0]:
            fields.append("title")
        if step.status and post["post_status"] != step.status:
            fields.append(f"status->{step.status}")
        metas = meta_lines(wp, step, write=False)
        changing = [line for line in metas if "->" in line]
        label = (
            ", ".join(fields) if fields else ("meta only" if changing else "no change")
        )
        print(f"{step.key} #{step.post_id}: {label}")
        for change in changes:
            print(f"    {change}")
        for line in metas:
            print(f"    {line}")
        if step.lang == "de":
            german[step.post_id] = new
    german_sources_phase(wp, plan, german, write=False)
    attachment_alts_phase(wp, write=False)
    return 0


def do_apply(wp: WP, write: bool) -> int:
    ids = resolve(wp)
    plan = steps(ids)
    touched: list[int] = []
    german: dict[int, str] = {}
    for step in plan:
        post = read_post(wp, step.post_id)
        changes: list[str] = []
        new_content = step.apply(post["post_content"], changes.append)
        fields = []
        if new_content != post["post_content"]:
            fields.append("content")
        if step.title and post["post_title"] == step.title[0]:
            fields.append(f"title -> {step.title[1]!r}")
        if step.status and post["post_status"] != step.status:
            fields.append(f"status -> {step.status}")
        metas = meta_lines(wp, step, write=write)
        changing = [line for line in metas if "->" in line]
        if step.lang == "de":
            german[step.post_id] = new_content
        if not fields and not changing:
            print(f"{step.key} #{step.post_id}: nothing to do", flush=True)
            for line in metas:
                print(f"    {line}", flush=True)
            continue
        print(
            f"{step.key} #{step.post_id}:"
            f" {', '.join(fields) if fields else 'meta only'}",
            flush=True,
        )
        for change in changes:
            print(f"    {change}", flush=True)
        for line in metas:
            print(f"    {line}", flush=True)
        if not write:
            continue
        if new_content != post["post_content"] or (
            step.title and post["post_title"] == step.title[0]
        ):
            args = ["post", "update", str(step.post_id)]
            if step.title and post["post_title"] == step.title[0]:
                args.append(f"--post_title={step.title[1]}")
            if step.status:
                args.append(f"--post_status={step.status}")
            wp.run(*args, "-", stdin=new_content, as_user=True)
        elif step.status and post["post_status"] != step.status:
            wp.run(
                "post",
                "update",
                str(step.post_id),
                f"--post_status={step.status}",
                as_user=True,
            )
        touched.append(step.post_id)
    for step in plan:
        # The SEOPress description names the tools too; it gets the same
        # name rules as the body of its post.
        if not write or step.status:
            continue
        current = seo_meta(wp, step.post_id).get("desc", "")
        if not any(name in current for name in OLD_NAMES):
            continue
        rules = NAME_RULES_EN if step.lang == "en" else NAME_RULES_DE
        new = current
        for old, new_value in rules:
            new = new.replace(old, new_value)
        if new != current:
            wp.run(
                "post",
                "meta",
                "update",
                str(step.post_id),
                "_seopress_titles_desc",
                new,
                as_user=True,
            )
            print(f"{step.key}: seo desc renamed", flush=True)
            touched.append(step.post_id)
    refreshed = german_sources_phase(wp, plan, german, write=write)
    attachment_alts_phase(wp, write=write)
    rename_slugs(wp, ids, write)
    if write and (touched or refreshed):
        # The German twins of every edited English post are marked as
        # hand-edited, with the fingerprint of the new English. A re-run
        # after an interrupted apply finds no content `touched` any more
        # but still refreshes the sources; those count as edited here.
        english = sorted(
            {step.english_id for step in plan if step.post_id in touched} | refreshed
        )
        marked = wp.eval_php(STATE_PHP, english)
        print(f"translation state: {marked}", flush=True)
    if not write:
        print("dry run; pass --write to apply")
    return 0


@overload
def seo_meta(wp: WP, post_id: int) -> dict[str, str]: ...
@overload
def seo_meta(wp: WP, post_id: None = None) -> dict[str, dict[str, str]]: ...
def seo_meta(
    wp: WP, post_id: int | None = None
) -> dict[str, str] | dict[str, dict[str, str]]:
    """SEOPress title and description of one post, or of every post
    ({post_id: {title, desc}}), one tab-separated query."""
    where = f"post_id = {post_id}" if post_id else "1=1"
    prefix = wp.run("db", "prefix").strip()
    out = wp.run(
        "db",
        "query",
        f"SELECT post_id, meta_key, meta_value FROM {prefix}postmeta "
        f"WHERE meta_key IN ('_seopress_titles_title', '_seopress_titles_desc') "
        f"AND {where}",
        "--skip-column-names",
        "--batch",
    )
    meta: dict[str, dict[str, str]] = {}
    for line in out.splitlines():
        if line.count("\t") != 2:
            continue
        row_id, key, value = line.split("\t")
        field = "title" if key.endswith("_title") else "desc"
        meta.setdefault(row_id, {})[field] = value
    if post_id:
        return meta.get(str(post_id), {})
    return meta


def do_verify(wp: WP) -> int:
    ids = resolve(wp)
    plan = steps(ids)
    ok = True
    for step in plan:
        post = read_post(wp, step.post_id)
        if step.key.startswith("header-"):
            # The menu thumbnails of both header partials must resolve
            # through their own src (spec 12 item 8): the deferred form is
            # the empty-box defect, and `present` is what rewrites the
            # instance's partial from the repository.
            for fault in unresolved_menu_images(post["post_content"]):
                print(
                    f"FAIL {step.key}: menu image would not resolve ({fault});"
                    " run `present` to write the repo partials"
                )
                ok = False
        for token in stale_tokens(post["post_content"]):
            print(f"FAIL {step.key}: {token} still present")
            ok = False
        for _old, new in step.pairs:
            if new not in post["post_content"]:
                print(f"FAIL {step.key}: new string missing: {new[:80]!r}")
                ok = False
        # The multi-hit sentence rules (M2): once applied, the old string is
        # gone and the new one is there. verify refuses both halves a miss —
        # a typo in the old string would otherwise apply silently never.
        for old, new in step.required_rules:
            if old in post["post_content"]:
                print(f"FAIL {step.key}: rule old string still present: {old[:80]!r}")
                ok = False
            if new not in post["post_content"]:
                print(f"FAIL {step.key}: rule new string missing: {new[:80]!r}")
                ok = False
        if step.title and post["post_title"] != step.title[1]:
            print(f"FAIL {step.key}: title is {post['post_title']!r}")
            ok = False
        if step.status and post["post_status"] != step.status:
            print(f"FAIL {step.key}: status is {post['post_status']!r}")
            ok = False
        for field, _key, pair in (
            ("title", "_seopress_titles_title", step.seo),
            ("desc", "_seopress_titles_desc", step.seo_desc),
        ):
            if not pair:
                continue
            current = seo_meta(wp, step.post_id).get(field, "")
            if current == pair[0]:
                print(
                    f"FAIL {step.key}: old seo {field} still present: {current[:80]!r}"
                )
                ok = False
            elif current == "":
                print(
                    f"note {step.key}: seo {field} meta is absent"
                    " (the i18n import wipes it)"
                )
            elif current != pair[1]:
                print(f"FAIL {step.key}: seo {field} is {current[:80]!r}")
                ok = False
    for key, post_id, after in (
        ("linker-planner-en", ids["linker-planner"]["en"], "solution-configurator"),
        ("linker-planer-de", ids["linker-planner"]["de"], "loesungskonfigurator"),
        ("linker-advisor-en", ids["linker-advisor"]["en"], "genie"),
        ("linker-berater-de", ids["linker-advisor"]["de"], "genie"),
    ):
        current = wp.run("post", "get", str(post_id), "--field=post_name").strip()
        if current != after:
            print(f"FAIL {key} #{post_id}: slug is {current!r}, expected {after!r}")
            ok = False
    # Nothing published anywhere may still name a retired tool or open a
    # retired address.
    posts = wp.json(
        "post",
        "list",
        "--post_type=page,post,lc_partial,lc_dynamic_template",
        "--post_status=publish",
        "--fields=ID,post_title",
        "--format=json",
        "--posts_per_page=-1",
    )
    meta = seo_meta(wp)
    for row in posts:
        content = wp.run("post", "get", str(row["ID"]), "--field=post_content")
        seo = meta.get(str(row["ID"]), {})
        seen = (
            stale_tokens(content)
            + stale_tokens(seo.get("title", ""))
            + stale_tokens(seo.get("desc", ""))
        )
        if seen:
            print(f"FAIL post #{row['ID']} ({row['post_title']}): {', '.join(seen)}")
            ok = False
    # The German sources' legacy metas are what the 9-i18n import reads;
    # a stale copy there reverts the German pages on the import's next run.
    sources = sorted({step.english_id for step in plan if step.lang == "de"})
    legacy = wp.eval_php(LEGACY_META_PHP, sources) or {}
    for source_id, row in sorted(legacy.items(), key=lambda item: int(item[0])):
        seen = stale_tokens(row.get("content", "")) + stale_tokens(row.get("title", ""))
        if seen:
            print(f"FAIL source #{source_id} legacy meta: {', '.join(seen)}")
            ok = False
    # The media alts too.
    alts = wp.eval_php(ALT_READ_PHP, list(OLD_NAMES)) or {}
    for post_id, alt in sorted(alts.items(), key=lambda item: int(item[0])):
        seen = stale_tokens(alt)
        if seen:
            print(f"FAIL media #{post_id} alt: {', '.join(seen)} in {alt[:60]!r}")
            ok = False
    print("verify: OK" if ok else "verify: FAILED")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--wp", required=True, help="WP-CLI command, e.g. ~/de-linker-local/t12/wp.sh"
    )
    parser.add_argument(
        "--user", default=None, help="administrator login, for unfiltered writes"
    )
    parser.add_argument("command", choices=["plan", "apply", "verify"])
    parser.add_argument("--write", action="store_true", help="apply for real")
    args = parser.parse_args()
    wp = WP(args.wp, args.user)
    if args.command == "plan":
        return do_plan(wp)
    if args.command == "apply":
        return do_apply(wp, args.write)
    return do_verify(wp)


if __name__ == "__main__":
    sys.exit(main())
