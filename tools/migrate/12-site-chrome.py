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
3. The tool pages rename ("Linker Planner" -> "Solution Configurator",
   slug stays; "Linker Planer" -> "Lösungskonfigurator"; "Linker Advisor"
   -> "Genie - Linker's AI assistant"; "Linker Berater" -> "Genie – der
   KI-Assistent von Linker"), the configurator's SEO title drops the
   price promise (prices are partner-gated, #11), and the assistant
   page's no-JavaScript fallback names Genie.
4. The retired pages become drafts: design-canvas / Entwurfsfläche and
   the two "has moved" notices (quote-configurator /
   angebots-konfigurator); Redirects.php sends their addresses to the
   configurator.
5. Every other published surface that names a tool keeps its layout and
   wording, with the names swapped (NAME_RULES) and Site Detail
   references folded into the configurator's roof step (BESPOKE). A
   marketing sentence that does not name a tool is not touched.

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
import tempfile
from pathlib import Path
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

# Published pages, posts and LiveCanvas templates whose content or title
# names a tool, by step key: English slug. The header and footer partials
# and the two tool pages resolve separately below.
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
    ('href="/design-canvas/"', 'href="/linker-planner/?step=roof"', ("for-installer",)),
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
        'href="/de/entwurfsflache/"',
        'href="/de/linker-planer/?step=roof"',
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
]

# German keeps the article, so the configurator is one catch-all; the
# assistant drops its article with the name.
NAME_RULES_DE: list[tuple[str, str]] = [
    ("Der Linker Berater", "Genie"),
    ("der Linker Berater", "Genie"),
    ("den Linker Berater", "Genie"),
    ("dem Linker Berater", "Genie"),
    ("des Linker Beraters", "von Genie"),
    ("im Linker Berater", "von Genie"),
    ("Linker Berater", "Genie"),
    ("Linker Planer", "Lösungskonfigurator"),
    ("Linker Standortdetails", "Dachdetails"),
]

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
    $found = get_posts(array(
        'name' => $slug, 'post_status' => 'any', 'numberposts' => 1,
        'post_type' => array('page', 'post', 'lc_partial', 'lc_dynamic_template'),
        'lang' => 'en', 'fields' => 'ids', 'suppress_filters' => false,
    ));
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


class WP:
    """WP-CLI, as a command prefix (the 9-i18n.py wrapper)."""

    def __init__(self, command: str, user: str | None) -> None:
        self.prefix = shlex.split(command)
        self.user = user

    def run(self, *args: str, stdin: str | None = None, as_user: bool = False) -> str:
        command = [*self.prefix, *args]
        if as_user and self.user:
            command.append(f"--user={self.user}")
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
        """Runs PHP with the payload as base64 argv[1]; returns its JSON."""
        with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False) as handle:
            handle.write("<?php\n" + code)
            path = handle.name
        try:
            return self.json(
                "eval-file",
                path,
                base64.b64encode(json.dumps(payload).encode()).decode(),
            )
        finally:
            Path(path).unlink(missing_ok=True)


def resolve(wp: WP) -> dict[str, dict[str, int]]:
    slugs = {
        **SURFACES,
        "header": "header",
        "footer": "footer",
        "linker-planner": "linker-planner",
        "linker-advisor": "linker-advisor",
        "design-canvas": "design-canvas",
        "quote-configurator": "quote-configurator",
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
    english_id is the source whose translation state the write marks."""

    def __init__(
        self,
        key: str,
        post_id: int,
        english_id: int,
        pairs: list[tuple[str, str]] | None = None,
        removes: list[str] | None = None,
        rules: list[tuple[str, str]] | None = None,
        title: tuple[str, str] | None = None,
        seo: tuple[str, str] | None = None,
        status: str | None = None,
        menu_images: bool = False,
    ) -> None:
        self.key = key
        self.post_id = post_id
        self.english_id = english_id
        self.lang = key.rsplit("-", 1)[-1]
        self.pairs = pairs or []
        self.removes = removes or []
        self.rules = rules or []
        self.title = title
        self.seo = seo
        self.status = status
        self.menu_images = menu_images

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
        if self.menu_images:
            content = self.defer_menu_images(content, report)
        return content

    @staticmethod
    def defer_menu_images(content: str, report: Any) -> str:
        """The header's menu images become data-src: no request before the
        visitor opens the menu (old ticket 193; assets/menu-images.js of
        linker-tools hydrates the open menu's). The eager brand logo keeps
        its src. Every other image of the partial defers: the desktop menu
        cards carry loading="lazy", the mobile rail cards carry no loading
        attribute at all (5 webp, about 1.4 MB together) -- matching the
        lazy ones alone left those loading on every page."""

        def defer(match: re.Match[str]) -> str:
            tag = match.group(0)
            tag = tag.replace('src="', 'data-src="', 1)
            tag = tag.replace('srcset="', 'data-srcset="', 1)
            return tag

        pattern = r'<img(?![^>]*loading="eager")(?![^>]*data-src=")[^>]*>'
        count = len(re.findall(pattern, content))
        if count:
            content = re.sub(pattern, defer, content)
            report(f"menu images: {count}x src -> data-src")
        return content

    @staticmethod
    def _brief(text: str) -> str:
        return repr(text[:72])


def steps(ids: dict[str, dict[str, int]]) -> list[Step]:
    """The whole edit, in write order: partials, tool pages, then the
    marketing surfaces."""
    plan: list[Step] = [
        Step(
            "header-en",
            ids["header"]["en"],
            ids["header"]["en"],
            HEADER_EN,
            HEADER_EN_REMOVE,
            menu_images=True,
        ),
        Step(
            "header-de",
            ids["header"]["de"],
            ids["header"]["en"],
            HEADER_DE,
            HEADER_DE_REMOVE,
            menu_images=True,
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
            title=PAGE_TITLES["linker-advisor"],
        ),
        Step(
            "linker-berater-de",
            ids["linker-advisor"]["de"],
            ids["linker-advisor"]["en"],
            NOSCRIPT_DE,
            title=PAGE_TITLES["linker-berater"],
        ),
        Step(
            "linker-planner-en",
            ids["linker-planner"]["en"],
            ids["linker-planner"]["en"],
            PLANNER_INLINE_EN,
            title=PAGE_TITLES["linker-planner"],
            seo=SEO_TITLES["linker-planner"],
        ),
        Step(
            "linker-planer-de",
            ids["linker-planner"]["de"],
            ids["linker-planner"]["en"],
            PLANNER_INLINE_DE,
            title=PAGE_TITLES["linker-planer"],
            seo=SEO_TITLES["linker-planer"],
        ),
        Step(
            "design-canvas-en",
            ids["design-canvas"]["en"],
            ids["design-canvas"]["en"],
            status="draft",
        ),
        Step(
            "design-canvas-de",
            ids["design-canvas"]["de"],
            ids["design-canvas"]["en"],
            status="draft",
        ),
        Step(
            "quote-configurator-en",
            ids["quote-configurator"]["en"],
            ids["quote-configurator"]["en"],
            status="draft",
        ),
        Step(
            "quote-configurator-de",
            ids["quote-configurator"]["de"],
            ids["quote-configurator"]["en"],
            status="draft",
        ),
    ]
    for key in SURFACES:
        for lang, rules, bespoke in (
            ("en", NAME_RULES_EN, BESPOKE_EN),
            ("de", NAME_RULES_DE, BESPOKE_DE),
        ):
            post_id = ids[key][lang]
            if not post_id:
                continue
            pairs = [(old, new) for old, new, where in bespoke if key in where]
            plan.append(
                Step(f"{key}-{lang}", post_id, ids[key]["en"], pairs, rules=rules)
            )
    return plan


def read_post(wp: WP, post_id: int) -> dict[str, str]:
    fields = wp.json("post", "get", str(post_id), "--format=json")
    return {
        "post_title": fields["post_title"],
        "post_content": fields["post_content"],
        "post_status": fields["post_status"],
    }


def do_plan(wp: WP) -> int:
    ids = resolve(wp)
    for step in steps(ids):
        post = read_post(wp, step.post_id)
        changes: list[str] = []
        new = step.apply(post["post_content"], changes.append)
        content_changed = new != post["post_content"]
        fields = []
        if content_changed:
            fields.append("content")
        if step.title and post["post_title"] == step.title[0]:
            fields.append("title")
        if step.status and post["post_status"] != step.status:
            fields.append(f"status->{step.status}")
        if step.seo:
            fields.append("seo")
        print(
            f"{step.key} #{step.post_id}: {', '.join(fields) if fields else 'no change'}"
        )
        for change in changes:
            print(f"    {change}")
    return 0


def do_apply(wp: WP, write: bool) -> int:
    ids = resolve(wp)
    touched: list[int] = []
    for step in steps(ids):
        post = read_post(wp, step.post_id)
        changes: list[str] = []
        new_content = step.apply(post["post_content"], changes.append)
        fields = []
        if new_content != post["post_content"]:
            fields.append("content")
        if step.title and post["post_title"] == step.title[0]:
            fields.append(f"title -> {step.title[1]!r}")
        if step.seo:
            fields.append("seo")
        if step.status and post["post_status"] != step.status:
            fields.append(f"status -> {step.status}")
        if not fields:
            print(f"{step.key} #{step.post_id}: nothing to do", flush=True)
            continue
        print(f"{step.key} #{step.post_id}: {', '.join(fields)}", flush=True)
        for change in changes:
            print(f"    {change}", flush=True)
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
        elif step.status:
            wp.run(
                "post",
                "update",
                str(step.post_id),
                f"--post_status={step.status}",
                as_user=True,
            )
        if step.seo:
            current = wp.run(
                "post", "meta", "get", str(step.post_id), "_seopress_titles_title"
            ).strip()
            if current == step.seo[0]:
                wp.run(
                    "post",
                    "meta",
                    "update",
                    str(step.post_id),
                    "_seopress_titles_title",
                    step.seo[1],
                    as_user=True,
                )
            elif current != step.seo[1]:
                raise SystemExit(
                    f"{step.key}: SEO title is neither old nor new: {current!r}"
                )
        touched.append(step.post_id)
    for step in steps(ids):
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
    if write and touched:
        # The German twins of every edited English post are marked as
        # hand-edited, with the fingerprint of the new English.
        english = sorted(
            {step.english_id for step in steps(ids) if step.post_id in touched}
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
    ok = True
    for step in steps(ids):
        post = read_post(wp, step.post_id)
        if step.status:  # drafted: its content is retired with the page
            continue
        for name in OLD_NAMES:
            if name in post["post_content"]:
                print(f"FAIL {step.key}: old name still present: {name!r}")
                ok = False
        for _old, new in step.pairs:
            if new not in post["post_content"]:
                print(f"FAIL {step.key}: new string missing: {new[:80]!r}")
                ok = False
        if step.title and post["post_title"] != step.title[1]:
            print(f"FAIL {step.key}: title is {post['post_title']!r}")
            ok = False
        if step.status and post["post_status"] != step.status:
            print(f"FAIL {step.key}: status is {post['post_status']!r}")
            ok = False
        if step.seo:
            current = seo_meta(wp, step.post_id).get("title", "")
            if current != step.seo[1]:
                print(f"FAIL {step.key}: SEO title is {current!r}")
                ok = False
    # Nothing published anywhere may still name a retired tool.
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
        for name in OLD_NAMES:
            if (
                name in content
                or name in seo.get("title", "")
                or name in seo.get("desc", "")
            ):
                print(f"FAIL post #{row['ID']} ({row['post_title']}): {name!r}")
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
