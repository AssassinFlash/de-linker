"""The deploy's database snapshot (#305): taken here, verified, never left half-written."""

from __future__ import annotations

import gzip
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import IO

import pytest

from linker_cutover import backup, snapshot
from linker_cutover.target import CutoverError, Target

AT = datetime(2026, 10, 18, 2, 0, 0, tzinfo=UTC)


class _Site(Target):
    """A target whose WP-CLI calls are recorded instead of run."""

    calls: list[tuple[str, ...]]

    def wp(self, *args: str, check: bool = True) -> str:  # noqa: D102 - recorded
        del check
        self.calls.append(args)
        return ""


def _site(root: Path) -> _Site:
    site = _Site(
        label="local:test",
        root=str(root),
        base_url="http://127.0.0.1:9999",
        prefix=("php", "wp", f"--path={root}"),
        shell_prefix=None,
        rsync_remote=None,
    )
    object.__setattr__(site, "calls", [])
    return site


def _dump(monkeypatch: pytest.MonkeyPatch, payload: bytes) -> list[str]:
    """Stand in for the transport: the dump arrives as `payload`; scripts are recorded."""
    scripts: list[str] = []

    def fake(
        target: Target,
        script: str,
        *,
        stdin: IO[bytes] | None = None,
        stdout: IO[bytes] | None = None,
    ) -> None:
        del target
        scripts.append(script)
        if stdout is not None:
            stdout.write(payload)
        if stdin is not None:
            stdin.read()

    monkeypatch.setattr(backup, "stream", fake)
    return scripts


def test_a_snapshot_is_written_here_and_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = _dump(monkeypatch, gzip.compress(b"select 1;\n"))

    taken = snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT)

    assert taken.name == "db-20261018T020000Z.sql.gz"
    assert taken.path == tmp_path / "snapshots" / taken.name
    assert taken.path.is_file() and taken.size == taken.path.stat().st_size
    assert len(taken.sha256) == 64
    # The retired index is left out; nothing is written on the host.
    assert '--ignore-table="$name.$prefix"genie_chunks' in scripts[0]
    assert "> " not in scripts[0].split("mysqldump", 1)[1].split("| gzip", 1)[0]
    assert list((tmp_path / "snapshots").iterdir()) == [taken.path]


def test_a_dump_that_does_not_read_to_the_end_is_not_a_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    whole = gzip.compress(b"select 1;\n" * 1000)
    _dump(monkeypatch, whole[: len(whole) // 2])

    with pytest.raises(CutoverError, match="not a readable gzip"):
        snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT)

    assert list((tmp_path / "snapshots").iterdir()) == []


def test_a_failed_transport_leaves_no_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(target: Target, script: str, **_: object) -> None:
        raise CutoverError("set -euo pipefail: mysqldump: access denied")

    monkeypatch.setattr(backup, "stream", failing)

    with pytest.raises(CutoverError, match="access denied"):
        snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT)

    assert list((tmp_path / "snapshots").iterdir()) == []


def test_only_the_newest_keep_snapshots_stay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "snapshots"
    folder.mkdir()
    for day in range(1, snapshot.KEEP + 3):
        (folder / f"db-202609{day:02d}T000000Z.sql.gz").write_bytes(b"old")
    (folder / "notes.txt").write_text("not a snapshot", encoding="utf-8")
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))

    taken = snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT)

    kept = snapshot.available(tmp_path)
    assert len(kept) == snapshot.KEEP
    assert kept[0] == taken.name
    assert (folder / "notes.txt").is_file()


@pytest.mark.parametrize("protected_count", [0, 1, 3, 4])
def test_retention_counts_only_existing_distinct_protected_snapshots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, protected_count: int
) -> None:
    folder = snapshot.directory(tmp_path)
    folder.mkdir()
    old_names = [f"db-202609{day:02d}T000000Z.sql.gz" for day in range(1, 7)]
    for name in old_names:
        (folder / name).write_bytes(gzip.compress(b"select 1;\n"))
    protected = set(old_names[:protected_count])
    # A missing name and the newly created snapshot consume no extra slot.
    protect = frozenset(protected | {snapshot.name_at(AT), "missing"})
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))

    taken = snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT, protect=protect)

    kept = set(snapshot.available(tmp_path))
    assert protected | {taken.name} <= kept
    assert len(kept) == max(3, protected_count + 1)
    unprotected = sorted(set(old_names) - protected, reverse=True)
    assert kept - protected - {taken.name} == set(
        unprotected[: max(0, 3 - protected_count - 1)]
    )


@pytest.mark.parametrize(
    "name",
    [
        "../db-20261018T020000Z.sql.gz",
        "db-latest.sql.gz",
        "x.sql.gz",
        "",
        "db-20261018T020000Z.sql.gz\n",
    ],
)
def test_restore_takes_only_snapshot_names(tmp_path: Path, name: str) -> None:
    with pytest.raises(CutoverError, match="not a snapshot name"):
        snapshot.restore(_site(tmp_path / "site"), tmp_path, name)


def test_restore_streams_the_file_back_and_flushes_the_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    site = _site(tmp_path / "site")
    taken = snapshot.take(site, tmp_path, now=AT)

    later = datetime(2026, 10, 18, 3, 0, 0, tzinfo=UTC)
    lines = snapshot.restore(site, tmp_path, taken.name, now=later)

    # The database being replaced is kept first, then the snapshot goes back.
    assert "mysqldump" in scripts[-2]
    assert "gunzip -c |" in scripts[-1]
    assert site.calls == [("cache", "flush")]
    assert lines[0] == "kept the replaced database as db-20261018T030000Z.sql.gz"
    assert lines[1] == f"restored {taken.path}"


def test_the_dump_script_names_the_left_out_table_with_the_sites_prefix(
    tmp_path: Path,
) -> None:
    """Run the real script: the database name and prefix are read on the site's machine."""
    binaries = tmp_path / "bin"
    binaries.mkdir()
    php = binaries / "php"
    php.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        "  *DB_HOST*) echo localhost ;;\n"
        "  *DB_USER*) echo site ;;\n"
        "  *DB_PASSWORD*) echo secret ;;\n"
        "  *DB_NAME*) echo shop ;;\n"
        "  *table_prefix*) echo wpx_ ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    dump = binaries / "mysqldump"
    dump.write_text(
        '#!/bin/sh\n[ "$1" = "--help" ] && exit 0\nfor a in "$@"; do echo "$a"; done\n',
        encoding="utf-8",
    )
    for tool in (php, dump):
        tool.chmod(0o755)
    root = tmp_path / "site"
    root.mkdir()

    script = backup.dump_script(_site(root), skip=snapshot.SKIPPED_TABLES)
    completed = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        env={**os.environ, "PATH": f"{binaries}:{os.environ['PATH']}"},
        check=False,
    )

    assert completed.returncode == 0, completed.stderr.decode()
    arguments = gzip.decompress(completed.stdout).decode().splitlines()
    assert "--ignore-table=shop.wpx_genie_chunks" in arguments
    assert arguments[-1] == "shop"
    assert "secret" not in arguments


def test_the_full_backup_leaves_nothing_out() -> None:
    script = backup.dump_script(_site(Path("/srv/site")))
    assert "SKIP+=" not in script


def test_pruning_never_removes_the_snapshot_just_taken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clock skew can give older files newer names; the new snapshot still stays."""
    folder = tmp_path / "snapshots"
    folder.mkdir()
    for day in range(1, snapshot.KEEP + 2):
        (folder / f"db-209910{day:02d}T000000Z.sql.gz").write_bytes(b"from the future")
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))

    taken = snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT)

    assert taken.path.is_file()
    assert len(snapshot.available(tmp_path)) == snapshot.KEEP


def test_a_restore_keeps_its_source_when_the_folder_is_full(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pre-restore snapshot must not prune the file the restore is about to read."""
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    site = _site(tmp_path / "site")
    oldest = snapshot.take(site, tmp_path, now=datetime(2026, 9, 1, tzinfo=UTC))
    for day in range(2, snapshot.KEEP + 1):
        snapshot.take(site, tmp_path, now=datetime(2026, 9, day, tzinfo=UTC))
    assert len(snapshot.available(tmp_path)) == snapshot.KEEP

    lines = snapshot.restore(site, tmp_path, oldest.name, now=AT)

    assert lines[1] == f"restored {oldest.path}"
    assert oldest.path.is_file()
    assert len(snapshot.available(tmp_path)) == snapshot.KEEP
