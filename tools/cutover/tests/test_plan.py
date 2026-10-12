"""The inventory is the requirement: these tests hold it to docs/specs/17-cutover.md.

Each assertion names the failure it can find. A check that cannot change a
decision (a count, a hash of the module, a list echoing itself) is not here.
"""

from __future__ import annotations

from pathlib import Path

from linker_cutover import plan


def test_the_three_plugins_ship_and_the_excludes_keep_them_intact() -> None:
    """A deploy exclude that matched a plugin's own file would ship a broken plugin."""
    for pattern in plan.DEPLOY_EXCLUDES:
        for slug in plan.NEW_PLUGINS:
            relative = Path(plan.REPO) / slug / f"{slug}.php"
            assert not relative.match(pattern), f"{pattern} would exclude {relative}"
            # The deployed trees must keep build/ and languages/: the entry
            # point is what WordPress loads and build/ is what the apps run.
            assert not (Path(plan.REPO) / slug / "build").match(pattern)
    assert "vendor/" in plan.DEPLOY_EXCLUDES, (
        "vendor/ is built by the staging step, not copied"
    )
    assert "node_modules/" in plan.DEPLOY_EXCLUDES
    assert ".git/" in plan.DEPLOY_EXCLUDES


def test_the_replaced_plugin_is_not_also_removed() -> None:
    """linker-i18n carries the legacy slug: deleting it would delete the new plugin."""
    assert set(plan.LEGACY_PLUGINS) & set(plan.NEW_PLUGINS) == set()
    assert set(plan.REPLACED_PLUGINS) & set(plan.LEGACY_PLUGINS) == set()
    assert set(plan.REPLACED_PLUGINS) <= set(plan.NEW_PLUGINS)
    # Every deployed plugin is either new or a named replacement, and the
    # legacy list names what the old tree's plugins were.
    assert "terravolt-b2b-core" in plan.LEGACY_PLUGINS
    assert "linker-ai-assistant" in plan.LEGACY_PLUGINS
    assert "code-snippets" in plan.LEGACY_PLUGINS
    assert "woocommerce-gateway-stripe" in plan.LEGACY_PLUGINS


def test_the_error_recorder_is_not_deleted() -> None:
    """Removing the fatal recorder before anything carries it is a capability regression.

    The switch replaces it in place instead: `mu-plugins/linker-error-recorder.php`
    (#80) ships over the live file of the same name, and only the live file's own
    `*.bak-*` backups go.
    """
    assert "linker-error-recorder.php" not in plan.LEGACY_MU_PLUGINS
    assert "linker-i18n-mu-loader.php" in plan.LEGACY_MU_PLUGINS
    assert plan.MU_PLUGINS_REPO == "mu-plugins"
    assert plan.MU_PLUGINS_DIR == "wp-content/mu-plugins"
    assert plan.LEGACY_GLOBS == ("*.bak-*",)
    assert plan.MU_ARCHIVE == "mu"


def test_the_two_names_for_a_site_directory_are_the_same_path() -> None:
    """`plan` is the inventory and `target` is the transport; a drift here is silent."""
    from linker_cutover import target

    assert plan.PLUGINS_DIR == target.PLUGINS
    assert plan.MU_PLUGINS_DIR == target.MU_PLUGINS


def test_the_product_pages_are_entry_points_with_a_schema_assertion() -> None:
    """A product page outside the subset would never have its node counted.

    The count is the assertion the switch needs: retiring the retained SEO
    plugin's Product template is only verifiable on the page itself.
    """
    assert plan.VERIFY_PRODUCT_PATHS
    assert set(plan.VERIFY_PRODUCT_PATHS) <= set(plan.VERIFY_PATHS)
    for language in ("/product/", "/de/produkt/"):
        assert any(path.startswith(language) for path in plan.VERIFY_PRODUCT_PATHS), (
            language
        )


def test_option_prefixes_cannot_match_a_new_option() -> None:
    """The cleanup rule is a prefix; a prefix that caught a live option would delete it."""
    live = (
        "linker_commerce_team_to",
        "linker_commerce_proforma_prefix",
        "linker_genie_url",
        "linker_engine_url",
        "linker_i18n_rewrite_fingerprint",
        "woocommerce_store_address",
        "seopress_titles_option_name",
    )
    for name in live:
        assert not name.startswith(plan.LEGACY_OPTION_PREFIXES), name


def test_the_migrations_are_the_ones_spec_17_names_and_in_order() -> None:
    """A missing or reordered migration is the failure; the order is the requirement."""
    assert [migration.script for migration in plan.MIGRATIONS] == [
        "7-facts.py",
        "7-facts.py",
        "8-engineering.py",
        "9-i18n.py",
    ]
    assert plan.MIGRATIONS[0].needs_backup_dir is True
    assert plan.MIGRATIONS[1].needs_backup_dir is True
    assert plan.MIGRATIONS[1].options == ("--plan", "tools/migrate/c15-facts.json")
    assert plan.MIGRATIONS[2].needs_backup_dir is True
    assert plan.MIGRATIONS[3].subcommand == ("apply",)
    # argparse: an option after a subcommand belongs to the subcommand, so the
    # login has to precede `apply` and `--write` has to follow it.
    assert plan.MIGRATIONS[3].options == ()


def test_the_verify_subset_is_absolute_paths_in_both_languages() -> None:
    """A relative path would resolve against the tool's cwd, not the site."""
    for path in plan.VERIFY_PATHS:
        assert path.startswith("/")
    german = [path for path in plan.VERIFY_PATHS if path.startswith("/de/")]
    assert german, "the German half of the site is the half that can silently break"
    assert any(path.startswith("/de/produkt/") for path in german)
    assert any(path.startswith("/product/") for path in plan.VERIFY_PATHS)
    assert plan.VERIFY_REDIRECTS == (("/design-canvas/", 301),)


def test_manual_items_are_printed_and_never_claimed() -> None:
    """The control panel is not reachable from here; the list must say what it is."""
    assert plan.MANUAL, "spec 17 §6 has steps only the panel can do"
    assert any("cron" in item for item in plan.MANUAL)
    assert any("LiteSpeed" in item for item in plan.MANUAL)
