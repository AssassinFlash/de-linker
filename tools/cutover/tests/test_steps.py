"""The steps: what each one runs, and the safety rules that are not visible in a dry run.

No WordPress is started. What these tests can find: a deletion rule that would
take a live table or a live option, a staging build that ships the development
dependencies or drops the plugin file, a migration run with the wrong command
line, and a step that reports work it did not do.

`step_calls` records what a step asked the target to run, so the assertions are
about the command line itself rather than about the step's prose.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from linker_cutover import plan, steps
from linker_cutover.target import CutoverError, Target


class FakeTarget(Target):
    """A Target that records instead of running, for the steps that only build commands."""

    def __init__(self, root: Path) -> None:  # noqa: D107 - a fixture, not a public type
        super().__init__(
            label="fake",
            root=str(root),
            base_url="http://127.0.0.1:9999",
            prefix=("wp",),
            shell_prefix=None,
            rsync_remote=None,
        )
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.shells: list[str] = []
        self.plugins: str = "name\tstatus\n"
        self.tables: str = "wp_posts,wp_options\n"
        self.options: str = "option_name\nsiteurl\n"
        self.shell_replies: dict[str, str] = {}
        self.eval_reply: str = "[]"

    def wp(self, *args: str, check: bool = True) -> str:  # noqa: D102
        del check
        self.calls.append(("wp", args))
        if args[:2] == ("plugin", "list"):
            return json.dumps(
                [
                    {"name": line.split("\t")[0]}
                    for line in self.plugins.splitlines()[1:]
                    if line.strip()
                ]
            )
        if args[:2] == ("db", "tables"):
            return self.tables
        if args[:2] == ("db", "prefix"):
            return "wp_"
        if args[:2] == ("option", "list") and "--fields=option_name" in args:
            return self.options
        if args[0] == "option" and args[1] == "list" and "--autoload=on" in args:
            return json.dumps(
                [
                    {
                        "option_name": "big",
                        "option_value": "a-long-value",
                        "autoload": "on",
                    },
                    {"option_name": "small", "option_value": "x", "autoload": "on"},
                    {"option_name": "empty", "option_value": "", "autoload": "on"},
                ]
            )
        if args[:2] == ("option", "list"):
            return "option_name,size\nsiteurl,10\n"
        if args[0] == "eval":
            return self.eval_reply
        if args[:2] == ("post", "list"):
            return "42 43"
        if args[:2] == ("maintenance-mode",):
            return "Maintenance mode is not active."
        return ""

    def shell(self, script: str) -> str:  # noqa: D102
        self.shells.append(script)
        for key, value in self.shell_replies.items():
            if key in script:
                return value
        return ""

    def wp_json(self, *args: str) -> object:  # noqa: D102 - only `plugin list` is asked for JSON
        return json.loads(self.wp(*args, "--format=json"))


def _fake(tmp_path: Path) -> FakeTarget:
    target = FakeTarget(tmp_path)
    target.plugins = (
        "name\tstatus\n"
        + "".join(f"{slug}\tactive\n" for slug in plan.LEGACY_PLUGINS)
        + "linker-i18n\tactive\nlivecanvas\tactive\n"
    )
    return target


def test_removal_deactivates_everything_before_deleting_anything(
    tmp_path: Path,
) -> None:
    """A plugin still active while its neighbour is deleted can fatal mid-window."""
    target = _fake(tmp_path)
    snippets = tmp_path / "snippets.json"
    snippets.write_text("[]", encoding="utf-8")
    steps.remove_legacy(target, snippets=snippets)
    verbs = [
        call[1][1]
        for call in target.calls
        if call[1][0] == "plugin" and call[1][1] in ("activate", "deactivate", "delete")
    ]
    assert verbs == ["deactivate", "delete"], (
        "every deactivation must precede every deletion"
    )
    deactivated = next(
        call[1] for call in target.calls if call[1][:2] == ("plugin", "deactivate")
    )
    deleted = next(
        call[1] for call in target.calls if call[1][:2] == ("plugin", "delete")
    )
    assert sorted(deactivated[2:]) == sorted(plan.LEGACY_PLUGINS)
    assert sorted(deleted[2:]) == sorted(plan.LEGACY_PLUGINS)


def test_removal_refuses_to_delete_the_snippet_plugin_without_an_export(
    tmp_path: Path,
) -> None:
    """The export is the evidence that the snippets' work has an owner; without it, stop."""
    target = _fake(tmp_path)
    with pytest.raises(CutoverError, match="export the snippets"):
        steps.remove_legacy(target, snippets=tmp_path / "missing.json")
    assert not [call for call in target.calls if call[1][0] == "plugin"]


def test_removal_keeps_the_plugin_that_shares_a_slug_with_the_new_tree(
    tmp_path: Path,
) -> None:
    """linker-i18n is replaced in place: deleting it would delete the new plugin."""
    target = _fake(tmp_path)
    snippets = tmp_path / "snippets.json"
    snippets.write_text("[]", encoding="utf-8")
    steps.remove_legacy(target, snippets=snippets)
    named = [arg for call in target.calls for arg in call[1]]
    assert "linker-i18n" not in named
    assert any(
        "linker-i18n" in action
        for action in steps.remove_legacy(target, snippets=snippets).actions
    )


def test_a_legacy_table_rule_takes_the_old_tree_and_not_woocommerce() -> None:
    """The rule is a prefix; a live table matched by it would be dropped at the window."""
    for legacy in (
        "wp_tv_b2b_audit_log",
        "wp_tv_b2b_project_request",
        "wp_linker_string",
        "wp_linker_ai_conversation",
        "wp_snippets",
    ):
        assert steps.is_legacy_table(legacy, "wp_"), legacy
    for live in (
        "wp_wc_orders",
        "wp_woocommerce_order_items",
        "wp_actionscheduler_actions",
        "wp_seopress_content_analysis",
        "wp_posts",
        "wp_snippet_meta",
    ):
        assert not steps.is_legacy_table(live, "wp_"), live


def test_the_table_rules_follow_the_sites_own_prefix() -> None:
    """`wp_` is a site setting: a rule that hard-codes it matches nothing on a site that changed it."""
    assert steps.is_legacy_table("dlk_snippets", "dlk_")
    assert steps.is_legacy_table("dlk_linker_string", "dlk_")
    # The same names under a prefix the site does not use are somebody else's tables.
    assert not steps.is_legacy_table("wp_linker_string", "dlk_")


def test_a_legacy_option_rule_leaves_the_new_tree_alone() -> None:
    """Deleting a live option would empty a settings screen without saying so."""
    for legacy in ("tv_b2b_seller_email", "dlk_content_dirty", "linker_ai_settings_v1"):
        assert steps._is_legacy_option(legacy), legacy
    for live in (
        "linker_commerce_team_to",
        "linker_genie_url",
        "linker_engine_url",
        "linker_i18n_rewrite_fingerprint",
        "woocommerce_currency",
    ):
        assert not steps._is_legacy_option(live), live


def test_hygiene_reports_the_panel_steps_and_the_autoload_review(
    tmp_path: Path,
) -> None:
    """A window that believes cron was switched on would leave the site without cron."""
    target = _fake(tmp_path)
    result = steps.hygiene(target, backup=tmp_path, writes=False)
    for item in plan.MANUAL:
        assert item in result.notes
    report = json.loads((tmp_path / "autoload.json").read_text(encoding="utf-8"))
    assert report["total_bytes"] == len("a-long-value") + len("x")
    assert report["options"][0]["option_name"] == "big"
    assert any("autoload" in action for action in result.actions)


def test_hygiene_deletes_only_after_it_has_listed_the_names(tmp_path: Path) -> None:
    """The prefix is the rule; the printed list is what makes it reviewable."""
    target = _fake(tmp_path)
    target.options = "option_name\ntv_b2b_seller_email\ndlk_content_dirty\n"
    result = steps.hygiene(target, backup=tmp_path, writes=True)
    deleted = [call for call in target.calls if call[1][:2] == ("option", "delete")]
    assert deleted == [
        ("wp", ("option", "delete", "tv_b2b_seller_email", "dlk_content_dirty"))
    ]
    assert (tmp_path / "legacy-options.json").read_text(encoding="utf-8").count(
        "tv_b2b"
    ) == 1
    assert any("2 names" in action for action in result.actions)


def test_staging_ships_the_plugin_without_the_checkouts_baggage(tmp_path: Path) -> None:
    """`vendor/` and `tests/` arriving on the host is the failure; `build/` missing is too."""
    repository = tmp_path / "repo"
    source = repository / plan.REPO / "linker-commerce"
    (source / "build").mkdir(parents=True)
    (source / "node_modules").mkdir()
    (source / "tests").mkdir()
    (source / "linker-commerce.php").write_text("<?php", encoding="utf-8")
    (source / "build" / "app.js").write_text("// built", encoding="utf-8")
    (source / "node_modules" / "x.js").write_text("// dev", encoding="utf-8")
    (source / "tests" / "a.php").write_text("<?php", encoding="utf-8")
    (source / "phpcs.xml.dist").write_text("<ruleset/>", encoding="utf-8")

    staged = steps.stage_plugin(repository, "linker-commerce", tmp_path / "staging")
    assert (staged / "linker-commerce.php").is_file()
    assert (staged / "build" / "app.js").is_file()
    assert not (staged / "node_modules").exists()
    assert not (staged / "tests").exists()
    assert not (staged / "phpcs.xml.dist").exists()


def test_staging_refuses_a_directory_that_is_not_the_plugin(tmp_path: Path) -> None:
    """A typo in the plugin slug must not ship an empty directory over the live plugin."""
    with pytest.raises(CutoverError, match="does not look like"):
        steps.stage_plugin(tmp_path, "linker-commerce", tmp_path / "staging")


def test_the_migrations_run_in_plan_mode_until_the_window_says_write(
    tmp_path: Path,
) -> None:
    """A drill that wrote the data migrations would stop being a rehearsal."""
    repository = tmp_path / "repo"
    (repository / "tools" / "migrate").mkdir(parents=True)
    for migration in plan.MIGRATIONS:
        (repository / "tools" / "migrate" / migration.script).write_text(
            "", encoding="utf-8"
        )
    target = _fake(tmp_path)
    result = steps.migrations(
        repository, target, backup=tmp_path, administrator="admin", writes=False
    )
    assert len(result.actions) == len(plan.MIGRATIONS)
    assert all("(plan)" in action for action in result.actions)


def test_each_migration_gets_its_options_where_argparse_expects_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--user` written after `apply` is the bug this catches: argparse hands it to the subcommand.

    `tools/migrate` owns each command line, and they differ — 9-i18n takes a
    subcommand and a login, 7 and 8 take a backup directory. The order is not
    cosmetic: an option after a subcommand belongs to the subcommand, so
    `--user` has to come first and `--write` has to come last.
    """
    repository = tmp_path / "repo"
    (repository / "tools" / "migrate").mkdir(parents=True)
    for migration in plan.MIGRATIONS:
        (repository / "tools" / "migrate" / migration.script).write_text(
            "", encoding="utf-8"
        )

    seen: list[list[str]] = []

    def record(command: list[str], **kwargs: object) -> object:
        del kwargs
        seen.append(list(command))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("subprocess.run", record)
    steps.migrations(
        repository, _fake(tmp_path), backup=tmp_path, administrator="admin", writes=True
    )

    assert len(seen) == len(plan.MIGRATIONS)
    facts = seen[0]
    assert facts[1].endswith("7-facts.py")
    assert "--backup-dir" in facts
    assert facts[-1] == "--write"
    german = seen[2]
    assert german[1].endswith("9-i18n.py")
    assert german.index("--user") < german.index("apply")
    assert german[german.index("--user") + 1] == "admin"
    assert german[-1] == "--write"


def test_the_deploy_installs_polylang_and_activates_the_three() -> None:
    """A site whose i18n base is installed but inactive serves one language."""
    plan_plugins = plan.NEW_PLUGINS
    assert len(plan_plugins) == 3
    assert plan.INSTALLED_PLUGINS == ("polylang",)


def test_a_step_describes_exactly_what_it_did() -> None:
    """A note printed as an action would let a dry run read as a finished window."""
    result = steps.Result("x", ["did a"], ["could not do b"])
    assert result.describe().splitlines() == ["x: did a", "x: note: could not do b"]
