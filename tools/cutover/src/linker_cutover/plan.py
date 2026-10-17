"""What the one-time switch changes, in one place (docs/specs/17-cutover.md).

Spec 17 is the requirement; this module is its inventory. Every list below is
read by exactly one step and by the drill, so what the drill proves and what
the maintenance window runs cannot drift apart.

Two kinds of entry:

- Things the script does (`NEW_PLUGINS`, `THEMES_REPO`, `LEGACY_*`, `MIGRATIONS`,
  `HYGIENE`, `VERIFY_PATHS`).
- Things only a person at the host's control panel can do (`MANUAL`). They are
  listed here so the checklist is complete, and `steps.hygiene` prints them
  instead of pretending to have run them.
"""

from __future__ import annotations

from dataclasses import dataclass

# The repository's plugins, deployed by `steps.deploy`. `vendor/` and `build/`
# ship (spec 17 §3); the development dependencies of composer do not, which is
# why the deploy builds a staging tree instead of rsyncing the checkout
# (docs/local-stack.md "与线上一致的部分": production carries no dev deps).
NEW_PLUGINS = ("linker-commerce", "linker-i18n", "linker-tools")
# Never pushed to the host: the checkout's own bookkeeping and the projects a
# published plugin does not run.
DEPLOY_EXCLUDES = (
    ".git/",
    "node_modules/",
    "vendor/",
    "tests/",
    ".phpunit.result.cache",
    "phpcs.xml.dist",
    "phpstan.neon.dist",
    "phpunit.xml.dist",
    "phpunit.integration.xml.dist",
)
# Where the three plugins come from, and where they land under the WordPress root.
REPO = "plugins"
PLUGINS_DIR = "wp-content/plugins"
# The repository's must-use plugins, and the site directory they land in (#80):
# one file today, the error recorder, installed over the live file of the same
# name — the host runs with `log_errors` off and has no error log this project
# can read, so what is there is the old version of this file, not a different
# plugin. `steps.deploy` copies the top level `*.php`; the directory's own
# project files (composer.json, tests/) are not deployed.
MU_PLUGINS_REPO = "mu-plugins"
MU_PLUGINS_DIR = "wp-content/mu-plugins"
# The repository's files inside the live theme: `themes/<slug>/<file>` mirrors
# `wp-content/themes/<slug>/<file>`. The child theme's functions.php is this
# repository's file — the site renders through the LiveCanvas templates and the
# linker-* plugins, so the theme file carries only the theme's own behaviours —
# and the live site's copy of it carries another site's. `steps.deploy` copies
# every file under `themes/`; the theme's rendering assets (its templates,
# styles, scripts) come with the live theme and are not this repository's to
# deploy.
THEMES_REPO = "themes"
THEMES_DIR = "wp-content/themes"

# Installed from wordpress.org and activated: the free base of the i18n chain
# (docs/specs/9-i18n.md). WP-CLI's own installer is the native mechanism, and it
# verifies the package against wordpress.org; a copy rsynced from a checkout
# would be an unverifiable second source of the same plugin.
INSTALLED_PLUGINS = ("polylang",)

# The German (Formal) language packs, installed by WP-CLI from the translation
# API (like INSTALLED_PLUGINS, the native installer is the verified channel):
# WordPress core's and WooCommerce's de_DE_formal. The site is English and
# German at equal rank and German runs in the formal register (AGENTS.md §3);
# without these packs every string of the `default` and `woocommerce` text
# domains falls back to English on the German pages (the 2026-10-15 incident:
# the switch had left the host without any pack, and the German account pages
# read English until the packs were installed by hand). The local stack
# installs the same two packs at instance creation (tools/local
# linker_local/wordpress.py install_language_packs), so a drill proves the
# step the window runs. Install only, never activate: Polylang switches the
# front-end locale per page, the site's own default stays English.
LANGUAGE_PACK_LOCALE = "de_DE_formal"
LANGUAGE_PACK_PLUGINS = ("woocommerce",)

# Deactivated and deleted: the old tree's plugins, plus the two the new tree
# does not use. Order matters — deactivate everything first, then delete, so a
# plugin that still holds a hook cannot fatal while its neighbour disappears.
LEGACY_PLUGINS = (
    "terravolt-b2b-core",
    "linker-ai-assistant",
    "code-snippets",
    "woocommerce-gateway-stripe",
)
# `linker-i18n` is not in that list: the new plugin carries the same slug, so
# the deploy replaces it in place and the activation stays.
REPLACED_PLUGINS = ("linker-i18n",)

# Files and directories under wp-content/plugins that are dead weight; spec 17
# §3 names them.
LEGACY_PLUGIN_PATHS = (
    "terravolt-b2b-core-broken-20260704",
    "terravolt-b2b-core.zip",
    "linker-runtime-backup-20260723-before-remediation.zip",
)
# `*.bak-*` files the host's own edits left behind. One rule, and spec 17 §3
# applies it to both directories the switch touches: `wp-content/plugins` and
# `wp-content/mu-plugins` (the recorder's own backups are named like this).
LEGACY_GLOBS = ("*.bak-*",)
# What `remove_legacy` takes out of the mu directory is archived before it goes
# (spec 17 §3, under the day's acceptance record): the old i18n loader and the
# recorder's backups exist nowhere else, and the record of what the window
# deleted is worth more than the bytes are.
MU_ARCHIVE = "mu"

# The old i18n plugin's must-use bootstrap: it requires the old plugin's class
# and is gone with it.
LEGACY_MU_PLUGINS = ("linker-i18n-mu-loader.php",)
# `linker-error-recorder.php` is NOT removed: the host runs with `log_errors`
# off and no readable error log, so it is the only thing that answers "why did
# the site break", and the switch replaces it in place instead — the current
# file (mu-plugins/linker-error-recorder.php, 票 #80 / PR #86) ships over the
# same name, and only its own older backups go with the rest of the leftovers.

# Dropped after the backup; nothing in the new tree reads them. The names are
# relative to the site's own table prefix (read with `wp db prefix`), so the
# rule does not assume `wp_`.
LEGACY_TABLE_PREFIXES = ("tv_b2b_", "tv_woo_b2b_", "linker_")
# The old tree's options. Nothing the new tree reads starts with any of these
# prefixes — the new options are `linker_commerce_*`, `linker_genie_url`,
# `linker_engine_url` and `linker_i18n_*` — so the rule is a prefix and the
# report prints every name it would take before `--write` takes it.
LEGACY_OPTION_PREFIXES = ("tv_", "dlk_", "linker_ai_", "terravolt_")


@dataclass(frozen=True)
class Migration:
    """One data migration of spec 17 §4, and what its own command line needs.

    Every migration takes `--wp <prefix>`; the rest of its command line differs
    (tools/migrate/<票号>-<名>.py owns it), so the difference is recorded here
    rather than guessed at the call site. The split between the two tuples is
    argparse's: an option written after a subcommand belongs to that subcommand,
    so `--user` has to precede `apply` and `--write` has to follow it.
    """

    script: str
    # Options of the migration itself, before any subcommand.
    options: tuple[str, ...] = ()
    # The subcommand, if it has one.
    subcommand: tuple[str, ...] = ()
    # The migration writes the products' previous values somewhere outside the
    # repository and refuses `--write` without that directory.
    needs_backup_dir: bool = False
    # Steps that act as an administrator need a login.
    needs_admin: bool = False
    # The migration refuses to write to the production host without
    # `--production` (its own guard; measured 2026-10-14 — a window run without
    # the flag writes nothing). The step adds the flag exactly when the target
    # IS the production host.
    production_guard: bool = False


# In order (spec 17 §4). `--write` is added by the step when it writes.
# c15-facts.json is the same writer as 7-facts.json, on the products that plan
# does not cover. It has to run in this list: a file the cutover never names
# does not land.
MIGRATIONS = (
    Migration("7-facts.py", needs_backup_dir=True, production_guard=True),
    Migration(
        "7-facts.py",
        options=("--plan", "tools/migrate/c15-facts.json"),
        needs_backup_dir=True,
        production_guard=True,
    ),
    Migration("8-engineering.py", needs_backup_dir=True, production_guard=True),
    Migration("9-i18n.py", subcommand=("apply",), needs_admin=True),
)

# Host hygiene that needs WP-CLI (spec 17 §6). Each is (label, args…). The
# revisions are handled by name in `steps.hygiene` instead: their ids have to
# be read first, and the count is part of what the step reports.
HYGIENE = (
    ("revisions: keep five", ("config", "set", "WP_POST_REVISIONS", "5", "--raw")),
    (
        "cron: disable the loopback runner",
        ("config", "set", "DISABLE_WP_CRON", "true", "--raw"),
    ),
    # Soft, not `--hard`: nothing in this switch changes the permalink
    # structure, so the stored rules are what needs refreshing, and a hard
    # flush rewrites the `.htaccess` this backup exists to put back.
    ("permalinks: flush", ("rewrite", "flush")),
    ("object cache: flush", ("cache", "flush")),
)
# The object cache plugin: installed where it is missing, activated where it is
# already there. The local instances ship it (docs/local-stack.md) and their
# isolation layer blocks wordpress.org on purpose, so "install" cannot be the
# only path; `steps.ensure_plugins` owns the rule for this and for Polylang.
OBJECT_CACHE_PLUGIN = "redis-cache"
# Where WordPress keeps the drop-in that makes an object cache work; WP-CLI
# calls the same file `wp-content/object-cache.php` (wp cache flush).
OBJECT_CACHE_DROPIN = "wp-content/object-cache.php"

# What only the host's control panel can do. The script prints these; it does
# not claim them. (Spec 17 §6 names the first two; the third is LiteSpeed's
# purge, which the plugin exposes as a WP-CLI command when it is installed.)
MANUAL = (
    "hPanel: cron every minute runs `wp cron event run --due-now`",
    "LiteSpeed: purge the whole cache (or `wp litespeed-purge all`) after the switch",
    "VPS: run the engine with LINKER_ENGINE_CORS_ORIGINS=https://de-linker.com — the "
    "configurator calls the engine cross-origin, and without the allowance the browser "
    "blocks every call (the roof step first)",
)

# The read-only regression subset of spec 17 §7. German URLs come from the
# snapshot's sitemap at cutover time; these are the fixed entry points.
# The product page of each language is listed apart because it carries a
# second assertion, on the body and not on the status: exactly one `Product`
# node. The switch retires the retained SEO plugin's own Product template
# (SCHEMA_RETIRED) so that the page has one node speaking for the product
# instead of two, one of which says this company manufactures it — and a page
# that answers 200 looks exactly the same either way (#81, GAP-7).
VERIFY_PRODUCT_PATHS = (
    "/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/",
    "/de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/",
)
VERIFY_PATHS = (
    "/",
    "/de/",
    "/products/",
    "/de/produkte/",
    "/proforma-request/",
    "/de/proforma-anfrage/",
    "/my-account/",
    "/de/mein-konto/",
    *VERIFY_PRODUCT_PATHS,
)
# The schema.org type the product pages must carry exactly once.
VERIFY_PRODUCT_TYPE = "Product"
# `/design-canvas/` is a redirect the new tree keeps (spec 17 acceptance);
# it is checked as a 301, by `steps.verify`.
VERIFY_REDIRECTS = (("/design-canvas/", 301),)
# The Search Console property (#145, docs/specs/145-search-console.md): Site
# Kit by Google holds the verification, and the marketing feedback loop reads
# the property. `steps.search_console` checks it after every `verify`.
SEARCH_CONSOLE_STEP = "search-console"
SITE_KIT = "google-site-kit"
SEARCH_CONSOLE_PROPERTY = "https://de-linker.com/"
# Site Kit's own names: the module's settings option ({propertyID, ownerID})
# and the user option, behind the table prefix, holding the file token.
SITE_KIT_SEARCH_CONSOLE_OPTION = "googlesitekit_search-console_settings"
SITE_KIT_VERIFICATION_FILE_META = "googlesitekit_site_verification_file"

# The service releases of spec 17 §5. Both use one release script — the genie's
# `ops/release.sh`, whose root is its parameter — so the release rule has one
# implementation for two services.
RELEASE_SCRIPT = "services/genie/ops/release.sh"
# Run on the VPS after both publishes: each release's venv, the quality
# worker's unit, daemon-reload, the restarts, and the check that every unit
# is up (#258). Exit 3 means the worker is installed but not started because
# its token is not set yet — the one step a deploy leaves to a person.
ACTIVATE_SCRIPT = "services/genie/ops/activate.sh"
ACTIVATE_NO_TOKEN = 3
# Where a publish stages on the VPS before release.sh lays it into its root:
# release.sh copies from a directory on the machine it runs on, and the release
# script and the two servicetrees travel there over ssh.
SERVICES_STAGING = "/root/linker-release"
# The services live on their own host, not on the WordPress host: the site's
# ssh alias reaches shared hosting as a plain user (no /root), while the
# releases land under /opt on the VPS. `linker-services` is the ssh-config
# alias for that VPS (root, its own key).
SERVICES_SSH = "linker-services"
SERVICES = (
    ("engine", "/opt/linker-engine", "services/engine"),
    ("genie", "/opt/linker-genie", "services/genie"),
)
# Written into the site's options at cutover; the values are the VPS addresses
# (docs/specs/13-genie.md, 14-solution-configurator.md, and spec 17's change
# record: local `just serve` writes the same two names). There is no service
# token yet: the assistant's user-context passthrough that will carry one is an
# open item elsewhere, and inventing the option here would be a second
# implementation of a rule nothing has written.
SERVICE_OPTIONS = (
    ("engine", "linker_engine_url", "LINKER_ENGINE_URL"),
    ("genie", "linker_genie_url", "LINKER_GENIE_URL"),
)


# The retained SEO plugin keeps a library of schema templates as a post type
# of its own, each with a rule saying which pages it applies to. Its product
# one is retired by the switch: the block it emits is a fixed template (brand
# "Linker", category "Energy storage system", no sku, no model, no image, no
# availability) and this plugin now emits the product page's Product node, so
# leaving the row in place would put two contradictory Product nodes on every
# product page. The rest of the library (the collection, article and site
# nodes) stays: nothing else emits those.
SCHEMA_POST_TYPE = "seopress_schemas"
SCHEMA_TEMPLATE_META = "_seopress_pro_rich_snippets_custom_manual_custom_global"
SCHEMA_RETIRED = "Product"


@dataclass(frozen=True)
class SnippetExport:
    """The code-snippets plugin's table, exported before the plugin is deleted.

    Only the suffix is recorded: the prefix is the site's own table prefix, and
    the step reads it from WP-CLI rather than assuming `wp_`. The table itself
    goes at hygiene time — the acceptance of spec 17 wants it gone or empty
    once the plugin that reads it is deleted, and by then its rows are in the
    export and in the database dump.
    """

    suffix: str = "snippets"
    columns: tuple[str, ...] = ("id", "name", "active", "scope", "code")


SNIPPETS = SnippetExport()
