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
from linker_cutover.target import HOST, CutoverError, Target


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
        self.rsyncs: list[tuple[str, str]] = []
        self.plugins: str = "name\tstatus\n"
        self.tables: str = "wp_posts,wp_options\n"
        self.options: str = "option_name\nsiteurl\n"
        self.shell_replies: dict[str, str] = {}
        self.eval_reply: str = "[]"
        self.existing: set[str] = set()

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

    def exists(self, relative: str) -> bool:  # noqa: D102 - a set, not a filesystem
        return relative in self.existing

    def rsync(  # noqa: D102 - records instead of copying
        self, source: str, destination: str, *, extra: list[str] | None = None
    ) -> str:
        del extra
        self.rsyncs.append((source, destination))
        return ""

    def wp_json(self, *args: str) -> object:  # noqa: D102 - only `plugin list` is asked for JSON
        return json.loads(self.wp(*args, "--format=json"))


class _Pages(FakeTarget):
    """A target whose reads are a fixed map of path to (status, body)."""

    def __init__(  # noqa: D107
        self, root: Path, pages: dict[str, str], statuses: dict[str, int] | None = None
    ) -> None:
        super().__init__(root)
        self.pages = pages
        self.statuses = statuses or {}

    def http(  # noqa: D102 - canned answers
        self, path: str, *, cache_buster: str | None = None
    ) -> tuple[int, str]:
        del cache_buster
        return self.statuses.get(path, 200), self.pages.get(
            path, '<html lang="de">ok</html>'
        )

    @staticmethod
    def redirects_are_served() -> dict[str, int]:
        """The statuses the redirect subset expects, so only the body is under test."""
        return dict(plan.VERIFY_REDIRECTS)


def _fake(tmp_path: Path) -> FakeTarget:
    target = FakeTarget(tmp_path)
    target.plugins = (
        "name\tstatus\n"
        + "".join(f"{slug}\tactive\n" for slug in plan.LEGACY_PLUGINS)
        + "linker-i18n\tactive\nlivecanvas\tactive\n"
    )
    return target


def _snippets(tmp_path: Path) -> Path:
    """The export `remove_legacy` refuses to run without."""
    snippets = tmp_path / "snippets.json"
    snippets.write_text("[]", encoding="utf-8")
    return snippets


def _acceptance(tmp_path: Path) -> Path:
    """The day's acceptance directory, where the mu archive lands."""
    return tmp_path / "docs" / "acceptance" / "2026-10-11" / "17"


def _repository(tmp_path: Path, *, recorder: bool = True, themes: bool = True) -> Path:
    """A checkout with the three plugins, the must-use directory #80 adds, and the theme file."""
    repository = tmp_path / "repo"
    for slug in plan.NEW_PLUGINS:
        source = repository / plan.REPO / slug
        source.mkdir(parents=True)
        (source / f"{slug}.php").write_text("<?php", encoding="utf-8")
    if recorder:
        must_use = repository / plan.MU_PLUGINS_REPO
        must_use.mkdir()
        (must_use / "linker-error-recorder.php").write_text(
            "<?php // the recorder", encoding="utf-8"
        )
    if themes:
        theme = repository / plan.THEMES_REPO / "picostrap5-child-base"
        theme.mkdir(parents=True)
        (theme / "functions.php").write_text(
            "<?php // the theme file", encoding="utf-8"
        )
    return repository


def _product_page(*nodes: object) -> str:
    """A page carrying one JSON-LD block per node given."""
    blocks = "".join(
        f'<script type="application/ld+json">{json.dumps(node)}</script>'
        for node in nodes
    )
    return f'<html lang="de"><head>{blocks}</head><body></body></html>'


_PRODUCT = {"@context": "https://schema.org", "@type": "Product", "name": "x"}
_WEBSITE = {"@context": "https://schema.org", "@type": "WebSite"}


def test_removal_deactivates_everything_before_deleting_anything(
    tmp_path: Path,
) -> None:
    """A plugin still active while its neighbour is deleted can fatal mid-window."""
    target = _fake(tmp_path)
    steps.remove_legacy(
        target, snippets=_snippets(tmp_path), acceptance=_acceptance(tmp_path)
    )
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
        steps.remove_legacy(
            target,
            snippets=tmp_path / "missing.json",
            acceptance=_acceptance(tmp_path),
        )
    assert not [call for call in target.calls if call[1][0] == "plugin"]


def test_removal_keeps_the_plugin_that_shares_a_slug_with_the_new_tree(
    tmp_path: Path,
) -> None:
    """linker-i18n is replaced in place: deleting it would delete the new plugin."""
    target = _fake(tmp_path)
    snippets, acceptance = _snippets(tmp_path), _acceptance(tmp_path)
    steps.remove_legacy(target, snippets=snippets, acceptance=acceptance)
    named = [arg for call in target.calls for arg in call[1]]
    assert "linker-i18n" not in named
    assert any(
        "linker-i18n" in action
        for action in steps.remove_legacy(
            target, snippets=snippets, acceptance=acceptance
        ).actions
    )


def test_the_must_use_cleanup_archives_before_it_deletes(tmp_path: Path) -> None:
    """What the mu rule takes out exists nowhere else: archive it, then remove it.

    The old i18n loader and the recorder's own `.bak-*` are the only copies of
    what the site had (spec 17 §3), so the order of those two verbs is the
    finding: a file removed before it is copied out is a file nothing can
    produce again. The plugins directory gets the same rule without the
    archive — a leftover of a plugin that is itself deleted.
    """
    target = _fake(tmp_path)
    old_recorder_backup = "linker-error-recorder.php.bak-20260808T174655Z"
    loader = "linker-i18n-mu-loader.php"
    mu = target.path_of(plan.MU_PLUGINS_DIR)
    # The real files, so the copy-out's own "is this a file" check runs; the
    # copy itself is recorded instead of made.
    (Path(mu)).mkdir(parents=True)
    for name in (old_recorder_backup, loader):
        (Path(mu) / name).write_text("<?php // the old file", encoding="utf-8")
    target.existing |= {
        f"{plan.MU_PLUGINS_DIR}/{loader}",
        f"{plan.MU_PLUGINS_DIR}/{old_recorder_backup}",
    }
    target.shell_replies[f"find {mu}"] = f"{mu}/{old_recorder_backup}\n"

    acceptance = _acceptance(tmp_path)
    result = steps.remove_legacy(
        target, snippets=_snippets(tmp_path), acceptance=acceptance
    )

    archive = acceptance / plan.MU_ARCHIVE
    assert target.rsyncs == [
        (f"{mu}/{old_recorder_backup}", str(archive / old_recorder_backup)),
        (f"{mu}/{loader}", str(archive / loader)),
    ]
    assert [script for script in target.shells if script.startswith("rm ")] == [
        f"rm -rf {mu}/{old_recorder_backup}",
        f"rm -f {mu}/{loader}",
    ]
    assert 2 == sum("archived" in action for action in result.actions)


def test_the_deploy_installs_the_recorder_over_the_live_file(tmp_path: Path) -> None:
    """#80's recorder is the successor of the live file of the same name.

    It goes first, before the plugins: it is the file whose job is to be
    recording while the rest of the switch runs, and the live site's own copy
    is the old version of it, not a different plugin.
    """
    target = _fake(tmp_path)
    recorder = "linker-error-recorder.php"
    target.existing.add(f"{plan.MU_PLUGINS_DIR}/{recorder}")
    repository = _repository(tmp_path)

    result = steps.deploy(target, repository=repository, staging=tmp_path / "staging")

    source, destination = target.rsyncs[0]
    assert Path(source).name == recorder
    assert destination == f"{target.root}/{plan.MU_PLUGINS_DIR}/{recorder}"
    assert len(target.rsyncs) == 5, "the recorder, the theme file and the three plugins"
    assert result.actions[0] == (
        f"deployed {plan.MU_PLUGINS_REPO}/{recorder} to "
        f"{plan.MU_PLUGINS_DIR}/{recorder} (replaced the live file)"
    )


def test_the_deploy_installs_the_theme_file_over_the_live_one(tmp_path: Path) -> None:
    """The child theme's functions.php is this repository's file.

    The live copy of the same path belongs to the site being replaced: the
    switch writes this one over it and says which of the two it did.
    """
    target = _fake(tmp_path)
    relative = "picostrap5-child-base/functions.php"
    target.existing.add(f"{plan.THEMES_DIR}/{relative}")
    repository = _repository(tmp_path)

    result = steps.deploy(target, repository=repository, staging=tmp_path / "staging")

    installed = [
        (source, destination)
        for source, destination in target.rsyncs
        if Path(source).name == "functions.php"
    ]
    assert len(installed) == 1
    source, destination = installed[0]
    assert source == str(repository / plan.THEMES_REPO / relative)
    assert destination == f"{target.root}/{plan.THEMES_DIR}/{relative}"
    assert (
        f"deployed {plan.THEMES_REPO}/{relative} to "
        f"{plan.THEMES_DIR}/{relative} (replaced the live file)" in result.actions
    )


def test_the_deploy_stops_when_the_checkout_has_no_theme_directory(
    tmp_path: Path,
) -> None:
    """The theme file is an input of the step, like the must-use directory.

    Shipping the three plugins while the live theme still carries the replaced
    site's functions.php would leave the old behaviours running (hreflang to
    the wrong domain among them) and report success.
    """
    target = _fake(tmp_path)
    with pytest.raises(CutoverError, match="carries no theme file"):
        steps.deploy(
            target,
            repository=_repository(tmp_path, themes=False),
            staging=tmp_path / "staging",
        )
    assert [Path(source).name for source, _ in target.rsyncs] == [
        "linker-error-recorder.php"
    ], "the recorder goes first; the theme failure stops everything after it"


def test_the_deploy_stops_when_the_checkout_has_no_must_use_directory(
    tmp_path: Path,
) -> None:
    """Three plugins shipped, the recorder never arriving, and a success line.

    The directory is an input of step 3 (#80 ships it); a checkout without it
    is not a checkout that can run the window's file half.
    """
    target = _fake(tmp_path)
    with pytest.raises(CutoverError, match="carries no must-use plugin"):
        steps.deploy(
            target,
            repository=_repository(tmp_path, recorder=False),
            staging=tmp_path / "staging",
        )
    assert target.rsyncs == []


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
    assert "--plan" not in facts
    assert facts[-1] == "--write"
    phase = seen[1]
    assert phase[1].endswith("7-facts.py")
    assert phase[phase.index("--plan") + 1].endswith("tools/migrate/c15-facts.json")
    assert Path(phase[phase.index("--plan") + 1]).is_absolute()
    assert phase[-1] == "--write"
    german = seen[3]
    assert german[1].endswith("9-i18n.py")
    assert german.index("--user") < german.index("apply")
    assert german[german.index("--user") + 1] == "admin"
    assert german[-1] == "--write"


def test_the_deploy_installs_polylang_and_activates_the_three() -> None:
    """A site whose i18n base is installed but inactive serves one language."""
    plan_plugins = plan.NEW_PLUGINS
    assert len(plan_plugins) == 3
    assert plan.INSTALLED_PLUGINS == ("polylang",)


def test_the_product_pages_must_carry_exactly_one_product_node(tmp_path: Path) -> None:
    """Both cases answer 200, so the status is not the check: the body is.

    Two Product nodes — one of them claiming this company manufactures the
    product — is what retiring the SEO plugin's own template exists to
    prevent, and a `verify` that only counted entry points could not see it.
    """
    statuses = _Pages.redirects_are_served()
    single = {
        path: _product_page(_PRODUCT, _WEBSITE) for path in plan.VERIFY_PRODUCT_PATHS
    }
    result = steps.verify(_Pages(tmp_path, single, statuses), cache_buster="x")
    assert result.notes == []
    assert [action for action in result.actions if "node(s)" in action] == [
        f"GET {path} -> 1 {plan.VERIFY_PRODUCT_TYPE} node(s) in ld+json"
        for path in plan.VERIFY_PRODUCT_PATHS
    ]

    doubled = {
        path: _product_page(_PRODUCT, _PRODUCT) for path in plan.VERIFY_PRODUCT_PATHS
    }
    result = steps.verify(_Pages(tmp_path, doubled, statuses), cache_buster="x")
    assert result.notes == [
        f"{path} carries 2 {plan.VERIFY_PRODUCT_TYPE} nodes, expected exactly 1"
        for path in plan.VERIFY_PRODUCT_PATHS
    ]


def test_one_block_can_hold_two_product_nodes(tmp_path: Path) -> None:
    """A `@graph` is one block; counting blocks would call that page a pass."""
    graph = {"@context": "https://schema.org", "@graph": [_PRODUCT, _PRODUCT]}
    assert steps.product_nodes(_product_page(graph)) == (2, 0)
    assert steps.product_nodes(_product_page(_PRODUCT, _WEBSITE)) == (1, 0)
    # The other nodes the site already emits are not the one under test.
    assert steps.product_nodes(_product_page(_WEBSITE)) == (0, 0)
    assert steps.product_nodes("<html lang='de'>no json-ld at all</html>") == (0, 0)


def test_the_block_is_found_however_the_script_tag_is_written() -> None:
    """The plugin writes the attribute; a check that assumed one spelling would miss it."""
    node = json.dumps(_PRODUCT)
    for tag in (
        f'<script type="application/ld+json">{node}</script>',
        f"<script class='x' type='application/ld+json'>{node}</script>",
        f'<script TYPE="Application/LD+JSON" id="a">{node}</script>',
        f'<script type="application/ld+json" class="a" data-x="1">{node}</script>',
    ):
        assert steps.product_nodes(tag) == (1, 0), tag


def test_a_block_that_does_not_parse_is_reported_not_read_as_zero(
    tmp_path: Path,
) -> None:
    """A block this cannot read is a check that did not run, not a page with no node."""
    broken = (
        '<html lang="de"><head><script type="application/ld+json">'
        '{"@type": Product}</script></head></html>'
    )
    assert steps.product_nodes(broken) == (0, 1)
    pages = dict.fromkeys(plan.VERIFY_PRODUCT_PATHS, broken)
    result = steps.verify(
        _Pages(tmp_path, pages, _Pages.redirects_are_served()), cache_buster="x"
    )
    assert result.notes == [
        note
        for path in plan.VERIFY_PRODUCT_PATHS
        for note in (
            f"{path} carries 0 {plan.VERIFY_PRODUCT_TYPE} nodes, expected exactly 1",
            f"{path}: 1 JSON-LD block(s) did not parse — the count above is not "
            "the whole page",
        )
    ]


def test_a_step_describes_exactly_what_it_did() -> None:
    """A note printed as an action would let a dry run read as a finished window."""
    result = steps.Result("x", ["did a"], ["could not do b"])
    assert result.describe().splitlines() == ["x: did a", "x: note: could not do b"]


def test_the_publish_stages_over_ssh_and_runs_there(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """release.sh copies from the machine it runs on, so the publish must too.

    Measured 2026-10-14: the old step ran the publish command with a local
    bash, which cannot reach /opt on the VPS; the drill never ran step 5.
    """
    repository = tmp_path / "repo"
    for _service, _root, directory in plan.SERVICES:
        (repository / directory).mkdir(parents=True)
        (repository / directory / "app.py").write_text("", encoding="utf-8")
    release = repository / plan.RELEASE_SCRIPT
    release.parent.mkdir(parents=True)
    release.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    seen: list[list[str]] = []

    def capture(command: list[str], *args: object, **kwargs: object) -> object:
        del args, kwargs
        seen.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("linker_cutover.steps.subprocess.run", capture)
    steps.services(repository=repository, addresses={}, run=True)

    assert [command[0] for command in seen] == ["rsync", "rsync", "ssh"] * 2
    engine_tree, engine_script, engine_publish = seen[0], seen[1], seen[2]
    assert engine_tree[-1] == f"{HOST}:{plan.SERVICES_STAGING}/engine/"
    assert engine_script[-1] == f"{HOST}:{plan.SERVICES_STAGING}/release.sh"
    assert engine_publish[-1] == (
        "GENIE_RELEASE_ROOT=/opt/linker-engine "
        f"bash {plan.SERVICES_STAGING}/release.sh publish {plan.SERVICES_STAGING}/engine"
    )
    assert seen[5][-1] == (
        "GENIE_RELEASE_ROOT=/opt/linker-genie "
        f"bash {plan.SERVICES_STAGING}/release.sh publish {plan.SERVICES_STAGING}/genie"
    )
