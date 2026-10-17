"""The step runner's own bookkeeping: which directory a step works from.

No WordPress is started and no step is run. What these tests can find is what
the window would find at the worst moment: a step handed the tool's own work
directory as "the newest backup", which is a directory with no backup in it.
"""

from __future__ import annotations

import gzip
import json
from argparse import Namespace
from pathlib import Path

import pytest

from linker_cutover import atomic, backup, cli, plan, steps
from linker_cutover.target import CutoverError, Target


class CliTarget(Target):
    """Real filesystem transport, with WP/HTTP boundaries isolated."""

    def wp(self, *args: str, check: bool = True) -> str:
        del check
        return json.dumps(
            [{"name": slug, "status": "active"} for slug in plan.NEW_PLUGINS]
        )

    def http(self, path: str, *, cache_buster: str | None = None) -> tuple[int, str]:
        del cache_buster
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
    monkeypatch.setattr(cli, "repository_root", lambda: repository)
    assert cli.main(["rollback-deploy", "--target", "local:c298"]) == 0
    assert (live / f"{plan.NEW_PLUGINS[-1]}.php").read_text() == "new"
    assert cli.main(["rollback-deploy", "--target", "local:c298", "--write"]) == 0
    assert (live / f"{plan.NEW_PLUGINS[-1]}.php").read_text() == "old"
