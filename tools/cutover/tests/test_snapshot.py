"""The deploy's database snapshot (#305): taken here, verified, never left half-written."""

from __future__ import annotations

import gzip
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
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
    assert snapshot.available(tmp_path) == [taken.name]
    assert not list((tmp_path / "snapshots").glob("*.partial"))


def test_a_dump_that_does_not_read_to_the_end_is_not_a_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    whole = gzip.compress(b"select 1;\n" * 1000)
    _dump(monkeypatch, whole[: len(whole) // 2])

    with pytest.raises(CutoverError, match="not a readable gzip"):
        snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT)

    assert snapshot.available(tmp_path) == []
    assert not list((tmp_path / "snapshots").glob("*.partial"))


def test_new_snapshot_changed_during_hash_is_not_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    original = backup.sha256

    def changed(path: Path) -> str:
        digest = original(path)
        path.write_bytes(gzip.compress(b"different contents"))
        return digest

    monkeypatch.setattr(backup, "sha256", changed)
    with pytest.raises(CutoverError, match="changed during verification"):
        snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT)
    assert not (snapshot.directory(tmp_path) / snapshot.STATE).exists()


def test_a_failed_transport_leaves_no_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(target: Target, script: str, **_: object) -> None:
        raise CutoverError("set -euo pipefail: mysqldump: access denied")

    monkeypatch.setattr(backup, "stream", failing)

    with pytest.raises(CutoverError, match="access denied"):
        snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT)

    assert snapshot.available(tmp_path) == []
    assert not list((tmp_path / "snapshots").glob("*.partial"))


@pytest.mark.parametrize("pending", ["partial", "state"])
def test_an_existing_interrupted_artifact_is_never_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pending: str
) -> None:
    scripts = _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    folder = snapshot.directory(tmp_path)
    folder.mkdir()
    name = (
        f".{snapshot.name_at(AT)}.partial"
        if pending == "partial"
        else snapshot.STATE + ".next"
    )
    existing = folder / name
    existing.write_bytes(b"unfinished recovery evidence")

    with pytest.raises(CutoverError, match="unfinished snapshot"):
        snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT)

    assert existing.read_bytes() == b"unfinished recovery evidence"
    assert scripts == []


def test_snapshot_refuses_a_linked_snapshot_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    other = tmp_path / "other-source"
    other.mkdir()
    (tmp_path / "snapshots").symlink_to(other, target_is_directory=True)

    with pytest.raises(CutoverError, match="not a real directory"):
        snapshot.take(_site(tmp_path / "site"), tmp_path, now=AT)

    assert scripts == [] and list(other.iterdir()) == []


def test_only_the_newest_keep_snapshots_stay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    old = [
        snapshot.take(site, tmp_path, now=datetime(2026, 9, day, tzinfo=UTC))
        for day in range(1, snapshot.KEEP + 3)
    ]
    folder = tmp_path / "snapshots"
    (folder / "notes.txt").write_text("not a snapshot", encoding="utf-8")
    taken = snapshot.take(site, tmp_path, now=AT)

    kept = snapshot.available(tmp_path)
    assert set(kept) == {taken.name, old[-1].name, old[-2].name}
    assert (folder / "notes.txt").is_file()


@pytest.mark.parametrize("protected_count", [0, 1, 3, 4])
def test_retention_unions_latest_three_with_explicit_protections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, protected_count: int
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    old_names = [
        snapshot.take(site, tmp_path, now=datetime(2026, 9, day, tzinfo=UTC)).name
        for day in range(1, 7)
    ]
    protected = set(old_names[:protected_count])
    # A missing name and the newly created snapshot consume no extra slot.
    protect = frozenset(protected | {snapshot.name_at(AT), "missing"})
    taken = snapshot.take(site, tmp_path, now=AT, protect=protect)

    kept = set(snapshot.available(tmp_path))
    assert protected | {taken.name} <= kept
    assert kept == protected | {taken.name, old_names[-1], old_names[-2]}


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
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    future = [
        snapshot.take(site, tmp_path, now=datetime(2099, 10, day, tzinfo=UTC))
        for day in range(1, snapshot.KEEP + 2)
    ]
    taken = snapshot.take(site, tmp_path, now=AT)

    assert taken.path.is_file()
    assert set(snapshot.available(tmp_path)) == {
        taken.name,
        *(item.name for item in future[-3:]),
    }


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
    assert len(snapshot.available(tmp_path)) == snapshot.KEEP + 1


def test_pr833_retention_keeps_latest_three_and_oct31_daily(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The October 31 daily point cannot consume a latest-three slot."""
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    previous: list[str] = []
    times = [
        datetime(2026, 10, 31, 1, tzinfo=UTC),
        datetime(2026, 10, 31, 17, 46, 4, tzinfo=UTC),
        datetime(2026, 11, 1, 1, tzinfo=UTC),
        datetime(2026, 11, 1, 5, 7, 58, tzinfo=UTC),
        datetime(2026, 11, 1, 7, 21, 14, tzinfo=UTC),
    ]
    for at in times:
        previous.append(
            snapshot.take(site, tmp_path, now=at, protect=frozenset(previous)).name
        )
    # Legacy filenames have no source proof; even a very old one is preserved.
    unknown = snapshot.directory(tmp_path) / "db-20261001T000000Z.sql.gz"
    unknown.write_bytes(gzip.compress(b"unregistered source"))
    taken = snapshot.take(
        site, tmp_path, now=datetime(2026, 11, 1, 9, 17, 35, tzinfo=UTC)
    )

    assert set(snapshot.available(tmp_path)) == {
        unknown.name,
        previous[1],
        previous[3],
        previous[4],
        taken.name,
    }
    assert not (snapshot.directory(tmp_path) / previous[0]).exists()
    assert not (snapshot.directory(tmp_path) / previous[2]).exists()


def test_daily_retention_covers_today_and_six_previous_utc_days(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    previous: list[str] = []
    for days_ago in range(8, 0, -1):
        previous.append(
            snapshot.take(
                site,
                tmp_path,
                now=AT - timedelta(days=days_ago),
                protect=frozenset(previous),
            ).name
        )
    taken = snapshot.take(site, tmp_path, now=AT)

    assert set(snapshot.available(tmp_path)) == {taken.name, *previous[-6:]}
    assert not (snapshot.directory(tmp_path) / previous[0]).exists()
    assert not (snapshot.directory(tmp_path) / previous[1]).exists()


def test_other_source_and_active_checkpoint_are_never_retired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site-a")
    other = _site(tmp_path / "site-b")
    foreign = snapshot.take(other, tmp_path, now=AT - timedelta(days=20))
    previous: list[str] = []
    for day in range(5):
        previous.append(
            snapshot.take(
                site,
                tmp_path,
                now=AT - timedelta(days=15 - day),
                protect=frozenset(previous),
            ).name
        )
    checkpoint = tmp_path / "cutover-workspace/staging/.deploy.json"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text(
        json.dumps(
            {"snapshot": {"path": str(snapshot.directory(tmp_path) / previous[0])}}
        )
    )

    taken = snapshot.take(site, tmp_path, now=AT)

    assert set(snapshot.available(tmp_path)) == {
        foreign.name,
        previous[0],
        previous[-1],
        previous[-2],
        taken.name,
    }
    assert not (snapshot.directory(tmp_path) / previous[1]).exists()


def test_baseline_and_protect_are_a_union_with_latest_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    old: list[str] = []
    for day in range(5):
        old.append(
            snapshot.take(
                site,
                tmp_path,
                now=AT - timedelta(days=20 - day),
                protect=frozenset(old),
            ).name
        )
    snapshot.set_baseline(site, tmp_path, old[0])

    taken = snapshot.take(site, tmp_path, now=AT, protect=frozenset({old[1], old[2]}))

    assert set(snapshot.available(tmp_path)) == {
        old[0],
        old[1],
        old[2],
        old[3],
        old[4],
        taken.name,
    }


def test_unknown_baseline_is_pinned_and_damage_blocks_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    folder = snapshot.directory(tmp_path)
    folder.mkdir()
    legacy = folder / "db-20260901T000000Z.sql.gz"
    legacy.write_bytes(gzip.compress(b"legacy recovery point"))
    snapshot.set_baseline(site, tmp_path, legacy.name)
    old: list[str] = []
    for day in range(4):
        old.append(
            snapshot.take(
                site,
                tmp_path,
                now=AT - timedelta(days=20 - day),
                protect=frozenset(old),
            ).name
        )
    legacy.write_bytes(gzip.compress(b"changed recovery point"))
    before = set(snapshot.available(tmp_path))

    taken = snapshot.take(site, tmp_path, now=AT)

    assert set(snapshot.available(tmp_path)) == before | {taken.name}


@pytest.mark.parametrize("damage", ["changed", "removed", "unreadable-reference"])
def test_damaged_proof_prevents_any_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    old: list[str] = []
    for day in range(4):
        old.append(
            snapshot.take(
                site,
                tmp_path,
                now=AT - timedelta(days=20 - day),
                protect=frozenset(old),
            ).name
        )
    if damage == "changed":
        (snapshot.directory(tmp_path) / old[0]).write_bytes(b"changed")
    elif damage == "removed":
        (snapshot.directory(tmp_path) / old[0]).unlink()
    else:
        checkpoint = tmp_path / "cutover-workspace/staging/.deploy.json"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text("invalid json")

    before = set(snapshot.available(tmp_path))
    taken = snapshot.take(site, tmp_path, now=AT)

    assert set(snapshot.available(tmp_path)) == before | {taken.name}


def test_noncooperating_reader_keeps_its_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    site = _site(tmp_path / "site")
    old: list[str] = []
    for day in range(4):
        old.append(
            snapshot.take(
                site,
                tmp_path,
                now=AT - timedelta(days=20 - day),
                protect=frozenset(old),
            ).name
        )
    monkeypatch.setattr(snapshot, "_unused", lambda path: path.name != old[0])

    taken = snapshot.take(site, tmp_path, now=AT)

    assert set(snapshot.available(tmp_path)) == {old[0], old[-1], old[-2], taken.name}


def test_interrupted_unlink_is_reconciled_without_another_dump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    old: list[str] = []
    for day in range(4):
        old.append(
            snapshot.take(
                site,
                tmp_path,
                now=AT - timedelta(days=20 - day),
                protect=frozenset(old),
            ).name
        )
    victim = snapshot.directory(tmp_path) / old[0]
    original_save = snapshot._save

    def interrupted(folder: Path, state: dict[str, object]) -> None:
        if not victim.exists():
            raise SystemExit("after unlink before registry update")
        original_save(folder, state)

    saved: list[snapshot.Snapshot] = []
    monkeypatch.setattr(snapshot, "_save", interrupted)
    with pytest.raises(SystemExit, match="after unlink"):
        snapshot.take(site, tmp_path, now=AT, on_verified=saved.append)

    assert len(saved) == 1 and saved[0].path.is_file()
    assert len(scripts) == 5 and not victim.exists()
    state = json.loads((snapshot.directory(tmp_path) / snapshot.STATE).read_text())
    assert state["snapshots"][old[0]]["retiring"] is True

    monkeypatch.setattr(snapshot, "_save", original_save)
    owned = snapshot.directory(tmp_path) / (snapshot.TRANSACTION + "interrupted")
    owned.write_bytes(snapshot.TRANSACTION_MARKER + b'"state":')
    owned.chmod(0o600)
    unknown = snapshot.directory(tmp_path) / (snapshot.TRANSACTION + "unknown")
    unknown.write_bytes(b"unidentified evidence")
    unknown.chmod(0o600)
    snapshot.reconcile(site, tmp_path, saved[0].name)
    state = json.loads((snapshot.directory(tmp_path) / snapshot.STATE).read_text())
    assert old[0] not in state["snapshots"]
    assert not owned.exists() and unknown.read_bytes() == b"unidentified evidence"
    assert set(snapshot.available(tmp_path)) == {old[-2], old[-1], saved[0].name}
    assert len(scripts) == 5


def test_unchanged_registered_snapshots_reuse_verified_stamps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    old = [
        snapshot.take(site, tmp_path, now=AT - timedelta(days=day)) for day in (3, 2, 1)
    ]
    hashed: list[Path] = []
    uncompressed: list[Path] = []
    original_hash = backup.sha256
    original_gzip = backup.readable_gzip

    def hashed_once(path: Path) -> str:
        hashed.append(path)
        return original_hash(path)

    def gzip_once(path: Path) -> bool:
        uncompressed.append(path)
        return original_gzip(path)

    monkeypatch.setattr(backup, "sha256", hashed_once)
    monkeypatch.setattr(backup, "readable_gzip", gzip_once)
    snapshot.take(site, tmp_path, now=AT)

    assert not {item.path for item in old} & set(hashed)
    assert not {item.path for item in old} & set(uncompressed)


def test_interrupted_retirement_rechecks_new_baseline_before_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dump(monkeypatch, gzip.compress(b"select 1;\n"))
    monkeypatch.setattr(snapshot, "_unused", lambda _path: True)
    site = _site(tmp_path / "site")
    old: list[str] = []
    for day in range(4):
        old.append(
            snapshot.take(
                site,
                tmp_path,
                now=AT - timedelta(days=20 - day),
                protect=frozenset(old),
            ).name
        )
    victim = snapshot.directory(tmp_path) / old[0]
    unlink = Path.unlink

    def interrupt(path: Path, *args: object, **kwargs: object) -> None:
        if path == victim:
            raise SystemExit("before unlink")
        unlink(path, *args, **kwargs)

    saved: list[snapshot.Snapshot] = []
    monkeypatch.setattr(Path, "unlink", interrupt)
    with pytest.raises(SystemExit, match="before unlink"):
        snapshot.take(site, tmp_path, now=AT, on_verified=saved.append)
    assert victim.exists()
    state = json.loads((snapshot.directory(tmp_path) / snapshot.STATE).read_text())
    assert state["snapshots"][victim.name]["retiring"] is True

    monkeypatch.setattr(Path, "unlink", unlink)
    snapshot.set_baseline(site, tmp_path, victim.name)
    snapshot.reconcile(site, tmp_path, saved[0].name)
    state = json.loads((snapshot.directory(tmp_path) / snapshot.STATE).read_text())
    assert victim.exists()
    assert "retiring" not in state["snapshots"][victim.name]
