"""The step runner's own bookkeeping: which directory a step works from.

No WordPress is started and no step is run. What these tests can find is what
the window would find at the worst moment: a step handed the tool's own work
directory as "the newest backup", which is a directory with no backup in it.
"""

from __future__ import annotations

import gzip
import json
from argparse import Namespace
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from native_planner import planner_wp

from linker_cutover import atomic, backup, cli, plan, steps
from linker_cutover.target import CutoverError, Target


class CliTarget(Target):
    """Real filesystem transport, with WP/HTTP boundaries isolated."""

    def wp_on_target(self) -> list[str]:
        return planner_wp()

    def wp(self, *args: str, check: bool = True) -> str:
        del check
        return json.dumps(
            [{"name": slug, "status": "active"} for slug in plan.NEW_PLUGINS]
        )

    def http(self, path: str, *, cache_buster: str | None = None) -> tuple[int, str]:
        del cache_buster
        if path in plan.VERIFY_LEGAL_PATHS:
            return (
                200,
                r"""<html lang="de"><script id="tv-legal-js">var svg='\u003csvg>';var space=/\s+/g;</script></html>""",
            )
        return (
            dict(plan.VERIFY_REDIRECTS).get(path, 200),
            '<html lang="de"><script type="application/ld+json">{"@type":"Product"}</script></html>',
        )


def _target(tmp_path: Path) -> Target:
    return CliTarget(
        "local:test", str(tmp_path), "http://127.0.0.1:9999", (), None, None
    )


def _arguments(**overrides: object) -> Namespace:
    """The options `_backup` reads, without argparse."""
    values: dict[str, object] = {"backup": None, "write": False, "command": "rollback"}
    values.update(overrides)
    return Namespace(**values)


def _dump(directory: Path) -> Path:
    """Give a directory the dump that makes it a backup."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / backup.DUMP).write_bytes(gzip.compress(b"select 1;"))
    return directory


@pytest.fixture
def data_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A data root of this test's own, so the real one is never read."""
    home = tmp_path / "de-linker-data"
    home.mkdir()
    monkeypatch.setattr(cli, "DATA_HOME", home)
    return home


def test_the_work_directory_is_not_the_newest_backup(data_home: Path) -> None:
    """`cutover-workspace` sorts after every `cutover-<date>` and holds no backup.

    `w` comes after any digit, so the lexical "newest" was the workspace: every
    step that takes its own backup would have been handed a directory with no
    dump in it, and the rollback reads a backup by default.
    """
    older = _dump(data_home / "cutover-20261011-1154")
    newer = _dump(data_home / "cutover-20261011-1157")
    (data_home / "cutover-workspace" / "staging").mkdir(parents=True)

    # The workspace really does sort last: this is the trap, not a guess.
    assert sorted(path.name for path in data_home.glob("cutover-*"))[-1] == (
        "cutover-workspace"
    )

    assert cli._newest() == newer
    assert older != newer
    assert cli._backup(_target(data_home), _arguments()) == newer


def test_a_directory_without_a_dump_is_not_a_backup(data_home: Path) -> None:
    """A run that died before the dump leaves a directory that must not be chosen."""
    (data_home / "cutover-20261011-1157").mkdir(parents=True)
    assert cli._newest() is None


def test_a_rollback_with_no_backup_at_all_says_so(data_home: Path) -> None:
    """ "The newest backup" of nothing is not a directory: the window has to run `backup`."""
    with pytest.raises(CutoverError, match="run `backup` first"):
        cli._backup(_target(data_home), _arguments())


def test_an_explicit_backup_directory_is_still_checked(
    data_home: Path, tmp_path: Path
) -> None:
    """`--backup` names the state to restore; a directory without a dump is not one."""
    given = tmp_path / "elsewhere"
    given.mkdir()
    with pytest.raises(CutoverError, match=f"has no {backup.DUMP}"):
        cli._backup(_target(tmp_path), _arguments(backup=given))

    _dump(given)
    assert cli._backup(_target(tmp_path), _arguments(backup=given)) == given


def test_deploy_dry_run_describes_staging_rename_and_all_owned_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The operator can see the switch strategy without touching the target."""
    monkeypatch.setattr(cli, "_target", lambda _: _target(tmp_path))
    assert cli.main(["deploy"]) == 0
    output = capsys.readouterr().out
    assert "rename" in output
    assert ".prev" in output
    assert "themes/" in output
    assert not list(tmp_path.iterdir())


def test_probe_dry_run_names_all_endpoints_without_starting_deploy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_target", lambda _: _target(tmp_path))
    assert cli.main(["probe"]) == 0
    output = capsys.readouterr().out
    for name in (
        "home",
        "contact",
        "proforma",
        "product",
        "commerce-rest",
        "i18n-rest",
        "tools-rest",
    ):
        assert name in output
    assert not list(tmp_path.iterdir())


def test_rollback_deploy_command_is_dry_unless_write_is_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The single operator command uses the same local filesystem switch."""
    target = _target(tmp_path / "site")
    repository = tmp_path / "repo"
    repository.mkdir()
    mu = repository / plan.MU_PLUGINS_REPO
    mu.mkdir()
    (mu / "recorder.php").write_text("new")
    theme = repository / plan.THEMES_REPO / "child"
    theme.mkdir(parents=True)
    (theme / "functions.php").write_text("new")
    for slug in plan.NEW_PLUGINS:
        plugin = repository / plan.REPO / slug
        plugin.mkdir(parents=True)
        (plugin / f"{slug}.php").write_text("new")
    artifacts = steps.deployment_artifacts(repository)
    for artifact in artifacts:
        live = Path(target.path_of(artifact.relative))
        live.parent.mkdir(parents=True, exist_ok=True)
        if artifact.source.is_dir():
            live.mkdir()
            (live / f"{artifact.source.name}.php").write_text("old")
        else:
            live.write_text("old")
    atomic.publish(target, artifacts, deploy_id="20261018T000000Z-cli")
    monkeypatch.setattr(cli, "_target", lambda _: target)
    monkeypatch.setattr(cli, "_local_operation", lambda _: nullcontext())
    monkeypatch.setattr(cli, "repository_root", lambda: repository)
    assert cli.main(["rollback-deploy", "--target", "local:c298"]) == 0
    assert (live / f"{plan.NEW_PLUGINS[-1]}.php").read_text() == "new"
    assert cli.main(["rollback-deploy", "--target", "local:c298", "--write"]) == 0
    assert (live / f"{plan.NEW_PLUGINS[-1]}.php").read_text() == "old"


@pytest.mark.parametrize("failure", ["lost-reply", "verify"])
def test_resume_deploy_finishes_pending_batch_without_republishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Lost SSH replies and transient verify failures need no new upload/rename."""

    class PendingTarget(CliTarget):
        unavailable = failure == "verify"

        def shell(self, script: str) -> str:
            output = super().shell(script)
            if failure == "lost-reply" and "TIMEFORMAT=" in script:
                raise CutoverError("fixture lost ssh reply")
            return output

        def http(
            self, path: str, *, cache_buster: str | None = None
        ) -> tuple[int, str]:
            if self.unavailable:
                return 503, "temporarily unavailable"
            return super().http(path, cache_buster=cache_buster)

    target = PendingTarget(
        "fixture", str(tmp_path / "site"), "http://127.0.0.1", (), None, None
    )
    repository = tmp_path / "repo"
    mu = repository / plan.MU_PLUGINS_REPO
    mu.mkdir(parents=True)
    (mu / "recorder.php").write_text("new")
    theme = repository / plan.THEMES_REPO / "child"
    theme.mkdir(parents=True)
    (theme / "functions.php").write_text("new")
    for slug in plan.NEW_PLUGINS:
        plugin = repository / plan.REPO / slug
        plugin.mkdir(parents=True)
        (plugin / f"{slug}.php").write_text("new")
    artifacts = steps.deployment_artifacts(repository)
    for artifact in artifacts:
        live = Path(target.path_of(artifact.relative))
        live.parent.mkdir(parents=True, exist_ok=True)
        if artifact.source.is_dir():
            live.mkdir()
            (live / f"{artifact.source.name}.php").write_text("old")
        else:
            live.write_text("old")
    if failure == "lost-reply":
        with pytest.raises(CutoverError, match="lost ssh reply"):
            atomic.publish(target, artifacts, deploy_id="20261018T000000Z-resume")
    else:
        receipt = atomic.publish(target, artifacts, deploy_id="20261018T000000Z-resume")
        assert steps.finish_deploy(target, receipt, cache_buster="fixture").notes
    directory, pending = atomic.latest_manifest(target)
    live_paths = [target.path_of(item.relative) for item in artifacts]
    before = atomic.identities(target, live_paths)
    monkeypatch.setattr(cli, "_target", lambda _: target)
    monkeypatch.setattr(cli, "repository_root", lambda: repository)

    assert cli.main(["resume-deploy"]) == 0
    assert atomic.latest_manifest(target)[1].state == "pending"
    if failure == "verify":
        assert cli.main(["resume-deploy", "--write"]) == 1
        assert atomic.latest_manifest(target)[1].state == "pending"
    target.unavailable = False
    assert cli.main(["resume-deploy", "--write"]) == 0

    archived = atomic.latest_manifest(target)[1]
    assert archived.state == "archived"
    assert archived.deploy_id == pending.deploy_id
    assert atomic.identities(target, live_paths) == before
    assert all(
        (Path(directory) / "files" / item.relative).exists() for item in artifacts
    )
    assert not list(Path(target.root).rglob("*.prev"))


def test_schema_takes_a_full_backup_before_it_writes(
    tmp_path: Path, data_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drafting SEO rows is a data write: a full backup first (AGENTS.md §5, #305)."""
    order: list[str] = []
    site = Target("local:test", str(tmp_path), "http://127.0.0.1:9999", (), None, None)
    monkeypatch.setattr(cli, "_target", lambda name: site)

    def backed_up(target: Target, home: Path) -> SimpleNamespace:
        order.append("backup")
        return SimpleNamespace(directory=_dump(home / "cutover-20261018-0300"))

    def schema(target: Target, *, writes: bool) -> steps.Result:
        order.append(f"schema writes={writes}")
        return steps.Result("schema", [], [])

    monkeypatch.setattr(backup, "create", backed_up)
    monkeypatch.setattr(steps, "retire_stale_schema", schema)

    assert cli.main(["schema"]) == 0
    assert order == ["schema writes=False"]
    assert cli.main(["schema", "--write"]) == 0
    assert order[1:] == ["backup", "schema writes=True"]


def test_a_restore_preview_refuses_a_name_that_is_not_a_snapshot(
    data_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["restore-snapshot", "../db.sql.gz"]) == 1
    assert "not a snapshot name" in capsys.readouterr().err


@pytest.mark.parametrize("operation", ["deploy", "drill"])
def test_local_operation_blocks_retirement_for_entire_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    from linker_local import retirement

    monkeypatch.setenv("LINKER_LOCAL_HOME", str(tmp_path))
    args = Namespace(command=operation, target="local:owned", instance="owned")
    with cli._local_operation(args):
        with pytest.raises(RuntimeError, match="already being managed"):
            retirement.retire(
                tmp_path, "owned", write=True, preserve=[], discard=[], preserve_to=None
            )
    marker = retirement.marker_path(tmp_path, "owned")
    marker.write_text("{}")
    with pytest.raises(RuntimeError, match="retirement is incomplete"):
        with cli._local_operation(args):
            raise AssertionError("pending retirement must not enter a cutover step")


def test_local_probe_leaves_site_write_lock_to_deploy_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from linker_local import retirement

    monkeypatch.setenv("LINKER_LOCAL_HOME", str(tmp_path))
    with cli._local_operation(Namespace(command="probe", target="local:owned")):
        with retirement.available(tmp_path, "owned"):
            pass
