"""The backup is the rollback: if it is not restorable, step 8 is a plan, not a fallback.

What these tests can find without a WordPress: a manifest that does not cover a
file it wrote, a dump script that names a path only one machine has, a password
that would appear in a process listing, and a restore that would accept a
backup whose dump no longer matches.
"""

from __future__ import annotations

import gzip
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import IO

import pytest

from linker_cutover import backup
from linker_cutover.target import (
    HTACCESS,
    MU_PLUGINS,
    PLUGINS,
    UPLOADS,
    CutoverError,
    Target,
)


def _target(root: Path) -> Target:
    return Target(
        label="local:test",
        root=str(root),
        base_url="http://127.0.0.1:9999",
        prefix=("php", "wp", f"--path={root}"),
        shell_prefix=None,
        rsync_remote=None,
    )


class _Site(Target):
    """A target on a real directory tree whose WP-CLI answers are canned.

    `create` and `restore` are mostly file operations, and those should run for
    real: what these tests are about is whether a file ends up in the archive
    and whether it comes back.
    """

    def wp(self, *args: str, check: bool = True) -> str:  # noqa: D102 - canned answers
        del args, check
        return ""


def _streams_a_stand_in_dump(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let the file halves run without a database: the dump is a stand-in gzip."""

    def fake(
        target: Target,
        script: str,
        *,
        stdin: IO[bytes] | None = None,
        stdout: IO[bytes] | None = None,
    ) -> None:
        del target, script
        if stdout is not None:
            stdout.write(gzip.compress(b"select 1;\n"))
        if stdin is not None:
            stdin.read()

    monkeypatch.setattr(backup, "stream", fake)


def _site(tmp_path: Path, *, must_use: bool = True) -> tuple[_Site, Path]:
    """A site on disk, with the four shapes a cutover has to move."""
    root = tmp_path / "root"
    files = {
        f"{UPLOADS}/2026/09/a.png": "png",
        f"{PLUGINS}/linker-commerce/linker-commerce.php": "<?php // plugin",
        f"{HTACCESS}": "# rules\n",
    }
    if must_use:
        files |= {
            f"{MU_PLUGINS}/linker-error-recorder.php": "<?php // recorder",
            f"{MU_PLUGINS}/linker-error-recorder.php.bak-20260808T174655Z": "<?php // old",
            f"{MU_PLUGINS}/livecanvas-must-use-plugin.php": "<?php // theme",
        }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return _Site(
        label="local:test",
        root=str(root),
        base_url="http://127.0.0.1:9999",
        prefix=("php", "wp", f"--path={root}"),
        shell_prefix=None,
        rsync_remote=None,
    ), root


def test_the_backup_carries_the_must_use_directory_and_puts_it_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The switch writes the mu directory, so a rollback that cannot restore it is not one.

    `.htaccess` is in the same test because it was the same defect from the
    other side: a backup that reported "no .htaccess" for a site that has one,
    because rsync was handed the directory form of a file.
    """
    _streams_a_stand_in_dump(monkeypatch)
    target, root = _site(tmp_path)
    home = tmp_path / "de-linker-data"

    taken = backup.create(target, home)
    recorded = backup.manifest_of(taken.directory)
    assert f"{MU_PLUGINS}/linker-error-recorder.php" in recorded
    assert HTACCESS in recorded
    assert (taken.directory / HTACCESS).read_text(encoding="utf-8") == "# rules\n"

    # The switch as it touches the site: the recorder is replaced, the old
    # backups are deleted, and the rewrite rules are rewritten.
    (root / MU_PLUGINS / "linker-error-recorder.php").write_text(
        "<?php // the recorder, replaced", encoding="utf-8"
    )
    (root / MU_PLUGINS / "linker-error-recorder.php.bak-20260808T174655Z").unlink()
    (root / HTACCESS).write_text("# rewritten\n", encoding="utf-8")

    backup.restore(target, taken.directory)
    assert (root / MU_PLUGINS / "linker-error-recorder.php").read_text(
        encoding="utf-8"
    ) == "<?php // recorder"
    assert (
        root / MU_PLUGINS / "linker-error-recorder.php.bak-20260808T174655Z"
    ).is_file()
    assert (root / HTACCESS).read_text(encoding="utf-8") == "# rules\n"


def test_a_site_without_a_must_use_directory_is_backed_up_anyway(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mu directory is optional; a backup that cannot run without one is a new failure."""
    _streams_a_stand_in_dump(monkeypatch)
    target, root = _site(tmp_path, must_use=False)

    taken = backup.create(target, tmp_path / "de-linker-data")
    assert not (taken.directory / MU_PLUGINS).exists()
    backup.restore(target, taken.directory)
    assert not (root / MU_PLUGINS).exists(), "restoring must not invent the directory"


def test_the_dump_script_keeps_the_password_on_the_target() -> None:
    """A password in an argv is a password in `ps` on a shared host."""
    script = backup.dump_script(_target(Path("/srv/site")))
    assert "MYSQL_PWD=" in script
    assert "config get DB_PASSWORD" in script
    assert "--single-transaction" in script
    # The site's database user has neither PROCESS (reading tablespaces) nor
    # SYSTEM_VARIABLES_ADMIN (the binlog session variable), and both would make
    # the backup unusable at one end or the other.
    assert "--no-tablespaces" in script
    assert "--set-gtid-purged" in script
    # The dump is not written to a path: it streams, so one script serves a
    # local instance and the host.
    assert ".sql" not in script
    assert "| gzip" in script


def test_the_restore_script_reads_the_dump_from_standard_input() -> None:
    """A dump path in the script would be a path the host may not have."""
    script = backup.restore_script(_target(Path("/srv/site")))
    assert "gunzip -c |" in script
    assert "mysql" in script
    assert "/tmp" not in script


def test_the_manifest_covers_every_file_written_and_detects_a_changed_dump(
    tmp_path: Path,
) -> None:
    """A dump edited after the backup must not be importable as if nothing happened."""
    (tmp_path / "db.sql.gz").write_bytes(gzip.compress(b"select 1;\n"))
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "a.php").write_text("<?php", encoding="utf-8")
    files = backup.directory_manifest(tmp_path)
    assert set(files) == {"db.sql.gz", "plugins/a.php"}
    assert files["db.sql.gz"]["sha256"] == backup.sha256(tmp_path / "db.sql.gz")

    (tmp_path / "manifest.json").write_text(
        json.dumps({"files": files}), encoding="utf-8"
    )
    assert (
        backup.manifest_of(tmp_path)["db.sql.gz"]["sha256"]
        == files["db.sql.gz"]["sha256"]
    )

    (tmp_path / "db.sql.gz").write_bytes(gzip.compress(b"select 2;\n"))
    target = _target(tmp_path)
    with pytest.raises(CutoverError, match="modified since"):
        backup.restore(target, tmp_path)


def test_a_backup_without_a_dump_is_refused_before_anything_is_replaced(
    tmp_path: Path,
) -> None:
    """Restoring a half-made backup would leave the site with someone else's database."""
    with pytest.raises(CutoverError, match="missing"):
        backup.restore(_target(tmp_path), tmp_path)


def test_the_directory_is_the_one_spec_17_names(tmp_path: Path) -> None:
    """The window looks for `~/de-linker-data/cutover-<date>/`; the name is the contract."""
    at = datetime(2026, 10, 12, 3, 15, tzinfo=UTC)
    assert backup.destination(tmp_path, now=at) == tmp_path / "cutover-20261012-0315"


def test_a_truncated_dump_is_not_a_backup(tmp_path: Path) -> None:
    """gzip's header survives a truncated stream; only decompressing finds it."""
    path = tmp_path / "half.sql.gz"
    path.write_bytes(gzip.compress(b"a" * 100_000)[:60])
    assert backup.readable_gzip(path) is False
    path.write_bytes(b"not gzip at all")
    assert backup.readable_gzip(path) is False
    path.write_bytes(gzip.compress(b"select 1;"))
    assert backup.readable_gzip(path) is True


def test_a_second_backup_does_not_merge_into_the_first(tmp_path: Path) -> None:
    """Two runs in one minute must not share a manifest — the later one's files would be unchecked."""
    at = datetime(2026, 10, 12, 3, 15, tzinfo=UTC)
    taken = backup.destination(tmp_path, now=at)
    taken.mkdir(parents=True)
    (taken / "db.sql.gz").write_bytes(gzip.compress(b"select 1;"))
    (taken / backup.MANIFEST).write_text('{"files": {}}', encoding="utf-8")
    with pytest.raises(CutoverError, match="already holds a complete backup"):
        backup.create(_target(tmp_path), tmp_path, now=at)


def test_a_partial_backup_from_a_dead_run_is_named_as_one(tmp_path: Path) -> None:
    """The refusal has to say which of the two it found: a backup, or a run that died."""
    at = datetime(2026, 10, 12, 3, 15, tzinfo=UTC)
    taken = backup.destination(tmp_path, now=at)
    taken.mkdir(parents=True)
    (taken / "db.sql.gz").write_bytes(gzip.compress(b"select 1;"))
    with pytest.raises(CutoverError, match="already holds a partial backup"):
        backup.create(_target(tmp_path), tmp_path, now=at)


def test_a_directory_a_dead_run_left_empty_is_reused(tmp_path: Path) -> None:
    """The window would otherwise be blocked for a minute by a run that wrote nothing."""
    at = datetime(2026, 10, 12, 3, 15, tzinfo=UTC)
    taken = backup.destination(tmp_path, now=at)
    taken.mkdir(parents=True)
    with pytest.raises(CutoverError, match="Could not open input file"):
        # The directory is taken (nothing in it to protect); the dump then fails
        # for its own reason, which is what a stand-in target does here.
        backup.create(_target(tmp_path), tmp_path, now=at)


def test_the_dump_script_runs_on_a_bash_without_the_flag(tmp_path: Path) -> None:
    """macOS's /bin/bash is 3.2, where "${a[@]}" of an empty array is unbound under `set -u`.

    The flag probe finds nothing on a mysqldump that does not know
    `--set-gtid-purged` (MariaDB's, the host's), and that is when the array is
    empty. Run the script's own shell, with a stand-in mysqldump that prints no
    help, rather than reading it: the failure is a shell's, not a string's.
    """
    binaries = tmp_path / "bin"
    binaries.mkdir()
    stand_in = binaries / "mysqldump"
    stand_in.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stand_in.chmod(0o755)

    script = (
        backup._DUMP_FLAGS  # noqa: SLF001 - the shell under test is this module's own
        + "\n"
        + "dump_extra\n"
        + "printf 'probe:%s\\n' ${DUMP_EXTRA[@]+\"${DUMP_EXTRA[@]}\"}\n"
    )
    completed = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{binaries}:{os.environ['PATH']}"},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "probe:"


def test_a_mysqldump_that_knows_the_flag_gets_it(tmp_path: Path) -> None:
    """The same script must pass the flag where the server's mysqldump takes it (MySQL's)."""
    binaries = tmp_path / "bin"
    binaries.mkdir()
    stand_in = binaries / "mysqldump"
    stand_in.write_text("#!/bin/sh\necho '--set-gtid-purged=OFF'\n", encoding="utf-8")
    stand_in.chmod(0o755)

    script = (
        backup._DUMP_FLAGS  # noqa: SLF001 - the shell under test is this module's own
        + "\n"
        + "dump_extra\n"
        + "printf 'probe:%s\\n' ${DUMP_EXTRA[@]+\"${DUMP_EXTRA[@]}\"}\n"
    )
    completed = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{binaries}:{os.environ['PATH']}"},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "probe:--set-gtid-purged=OFF"


def test_the_scripts_use_the_wp_prefix_as_an_array() -> None:
    """A string assignment plus unquoted `$wp` splits the remote prefix apart.

    Measured 2026-10-14: the production dump's first word reached the host as
    `set` and the "dump" was the shell's environment listing.
    """
    target = _target(Path("/srv/site"))

    dump = backup.dump_script(target)
    assert "wp=(" in dump
    assert '"${wp[@]}" config get DB_HOST' in dump
    assert '"${wp[@]}" config get DB_NAME' in dump

    restore = backup.restore_script(target)
    assert "wp=(" in restore
    assert '"${wp[@]}" config get DB_PASSWORD' in restore


def test_the_gate_folds_case_because_this_mac_has_one_slot(tmp_path: Path) -> None:
    """The Linux host holds `jobs.php` and `Jobs.php`; this Mac holds one file.

    Measured 2026-10-14 on linker-i18n: the site counts 18295 files under
    wp-content/plugins, the pulled tree 18294, and the only difference is
    that pair — a case-folded set comparison is the strongest claim this
    filesystem can make, and it still refuses a genuinely missing file.
    """

    class _SiteWithListing(_Site):
        listing: str = ""

        def shell(self, script: str) -> str:  # noqa: D102 - the site's own answer
            del script
            return self.listing

    local = tmp_path / "archive" / PLUGINS
    (local / "linker-i18n" / "includes").mkdir(parents=True)
    (local / "linker-i18n" / "includes" / "Jobs.php").write_text(
        "<?php", encoding="utf-8"
    )
    target = _SiteWithListing(
        label="local:test",
        root=str(tmp_path / "root"),
        base_url="http://127.0.0.1:9999",
        prefix=("php", "wp"),
        shell_prefix=None,
        rsync_remote=None,
    )

    target.listing = (
        "./linker-i18n/includes/Jobs.php\n./linker-i18n/includes/jobs.php\n"
    )
    backup._prove_the_tree_arrived(target, PLUGINS, local)

    target.listing = (
        "./linker-i18n/includes/Jobs.php\n"
        "./linker-i18n/includes/jobs.php\n"
        "./linker-i18n/includes/Missing.php\n"
    )
    with pytest.raises(CutoverError, match="missing like"):
        backup._prove_the_tree_arrived(target, PLUGINS, local)


def test_a_second_backup_hard_links_what_did_not_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#305: only what changed travels; every backup is still a whole tree of its own."""
    _streams_a_stand_in_dump(monkeypatch)
    site, root = _site(tmp_path)
    home = tmp_path / "home"
    first = backup.create(site, home, now=datetime(2026, 10, 18, 1, 0, tzinfo=UTC))
    changed = root / PLUGINS / "linker-commerce" / "linker-commerce.php"
    changed.write_text("<?php // plugin, new version", encoding="utf-8")

    second = backup.create(site, home, now=datetime(2026, 10, 18, 2, 0, tzinfo=UTC))

    upload = Path(UPLOADS) / "2026" / "09" / "a.png"
    assert (first.directory / upload).stat().st_ino == (
        second.directory / upload
    ).stat().st_ino
    plugin = Path(PLUGINS) / "linker-commerce" / "linker-commerce.php"
    assert (first.directory / plugin).stat().st_ino != (
        second.directory / plugin
    ).stat().st_ino
    assert (
        (second.directory / plugin).read_text(encoding="utf-8").endswith("new version")
    )
    assert (first.directory / plugin).read_text(encoding="utf-8") == "<?php // plugin"


def test_an_unfinished_backup_is_not_linked_from(tmp_path: Path) -> None:
    home = tmp_path
    (home / "cutover-20261018-0100").mkdir()
    done = home / "cutover-20261017-0100"
    done.mkdir()
    (done / backup.MANIFEST).write_text("{}", encoding="utf-8")

    assert backup.latest_complete(home) == done
