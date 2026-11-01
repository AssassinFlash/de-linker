"""Small hard-linked site copies prove retention without real backup deletion."""

from __future__ import annotations

import gzip
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from linker_cutover import backup, cli
from linker_cutover import backup_retention as retention
from linker_cutover.target import HTACCESS, PLUGINS, UPLOADS, CutoverError, Target

NOW = datetime(2026, 11, 1, 12, tzinfo=UTC)


@pytest.fixture
def home(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    # Owner: this test. One small root per test, deadline the test's return;
    # TemporaryDirectory's finally removes it on failures/interruption too.
    with tempfile.TemporaryDirectory(prefix="linker-backup-retention-") as folder:
        root = Path(folder)
        monkeypatch.setenv("LINKER_LOCAL_HOME", str(root / "local"))
        yield root


def target(home: Path) -> Target:
    return Target(
        "same-label", str(home / "site"), "http://localhost:9999", (), None, None
    )


def saved(
    home: Path,
    at: datetime,
    *,
    previous: Path | None = None,
    legacy: bool = False,
    site: Target | None = None,
) -> Path:
    directory = backup.destination(home, now=at)
    directory.mkdir()
    (directory / backup.DUMP).write_bytes(gzip.compress(b"SELECT 1;\n"))
    (directory / backup.OPTIONS).write_text("[]")
    (directory / HTACCESS).write_text("# rules")
    (directory / PLUGINS).mkdir(parents=True)
    upload = directory / UPLOADS / "image.png"
    upload.parent.mkdir(parents=True)
    if previous is None:
        upload.write_bytes(b"unchanged image")
    else:
        os.link(previous / UPLOADS / "image.png", upload)
    data: dict[str, object] = {
        "taken_at": at.isoformat(),
        "target": (site or target(home)).label,
        "files": backup.directory_manifest(directory),
    }
    if not legacy:
        data["source"] = retention.identity(site or target(home))
    (directory / backup.MANIFEST).write_text(json.dumps(data))
    return directory


def sweep(home: Path, current: Path, **kwargs: object) -> list[str]:
    return retention.prune(home, target(home), current, now=NOW, **kwargs)  # type: ignore[arg-type]


def test_union_keeps_daily_latest_baseline_references_and_unknowns(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(retention, "_unused", lambda *_: True)
    oldest = saved(home, NOW - timedelta(days=20))
    retention.register(oldest, target(home), baseline=True)
    referenced = saved(home, NOW - timedelta(days=19), previous=oldest)
    retire = saved(home, NOW - timedelta(days=18), previous=oldest)
    legacy = saved(home, NOW - timedelta(days=17), legacy=True)
    foreign = saved(
        home, NOW - timedelta(days=16), site=replace(target(home), root="/other/site")
    )
    partial = backup.destination(home, now=NOW - timedelta(days=15))
    partial.mkdir()
    (partial / backup.DUMP).write_text("interrupted")
    daily = [
        saved(home, NOW - timedelta(days=days), previous=oldest)
        for days in range(6, 0, -1)
    ]
    early_today = saved(home, NOW - timedelta(hours=3), previous=oldest)
    latest = [
        saved(home, NOW - timedelta(minutes=minutes), previous=oldest)
        for minutes in (2, 1, 0)
    ]
    metadata = home / "local" / "unregistered" / "snapshot.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps({"name": referenced.name}))

    assert sweep(home, latest[-1]) == [early_today.name, retire.name]
    assert all(
        path.exists()
        for path in [oldest, referenced, legacy, foreign, partial, *daily, *latest]
    )
    assert (latest[-1] / UPLOADS / "image.png").read_bytes() == b"unchanged image"
    assert (latest[-1] / UPLOADS / "image.png").stat().st_ino == (
        oldest / UPLOADS / "image.png"
    ).stat().st_ino


def test_legacy_adoption_allows_rotation_and_binds_the_manifest(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retention, "_unused", lambda *_: True)
    copies = [
        saved(home, NOW - timedelta(minutes=minutes), legacy=True)
        for minutes in (5, 4, 3, 2, 1)
    ]
    assert (
        sweep(home, copies[-1]) == []
    )  # Before: unproven legacy source cannot be deleted.
    for path in copies:
        retention.register(path, target(home), baseline=path == copies[0])
    assert sweep(home, copies[-1]) == [
        copies[1].name
    ]  # After: confirmed old source rotates.
    assert copies[0].exists()
    assert backup.latest_complete(home, target=target(home)) == copies[-1]
    data = json.loads((copies[0] / backup.MANIFEST).read_text())
    data["taken_at"] = NOW.isoformat()
    (copies[0] / backup.MANIFEST).write_text(json.dumps(data))
    assert not retention.same_source(copies[0], target(home))
    with pytest.raises(CutoverError, match="source mismatch"):
        retention.register(copies[-1], replace(target(home), label="different"))


def test_corrupt_retained_dump_blocks_every_deletion(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retention, "_unused", lambda *_: True)
    copies = [
        saved(home, NOW - timedelta(minutes=minutes)) for minutes in (4, 3, 2, 1, 0)
    ]
    (copies[-2] / backup.DUMP).write_bytes(b"broken")
    assert sweep(home, copies[-1]) == []
    assert all(path.exists() for path in copies)


def test_verified_dump_cache_avoids_repeated_hash_and_gzip(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copies = [saved(home, NOW - timedelta(minutes=minutes)) for minutes in (2, 1, 0)]
    sweep(home, copies[-1])

    def forbidden(*_: object) -> str:
        raise AssertionError("unchanged dump was read twice")

    monkeypatch.setattr(backup, "sha256", forbidden)
    monkeypatch.setattr(backup, "readable_gzip", forbidden)
    sweep(home, copies[-1])


def test_cooperating_reader_blocks_retention_and_writer_contention_is_explicit(
    home: Path,
) -> None:
    copies = [
        saved(home, NOW - timedelta(minutes=minutes)) for minutes in (4, 3, 2, 1, 0)
    ]
    with retention.locked(home, reader=True):
        assert sweep(home, copies[-1]) == []
    with (
        retention.locked(home, writer=True),
        pytest.raises(CutoverError, match="in use"),
    ):
        backup.create(target(home), home, now=NOW + timedelta(minutes=1))
    assert all(path.exists() for path in copies)


def test_actual_open_file_reader_is_preserved_then_reclaimed(home: Path) -> None:
    copies = [saved(home, NOW - timedelta(minutes=minutes)) for minutes in (3, 2, 1, 0)]
    with (copies[0] / backup.DUMP).open("rb"):
        assert sweep(home, copies[-1]) == []
        assert copies[0].exists()
    assert sweep(home, copies[-1]) == [copies[0].name]


def test_unreadable_observer_and_unknown_files_cannot_authorize_deletion(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copies = [saved(home, NOW - timedelta(minutes=minutes)) for minutes in (3, 2, 1, 0)]
    monkeypatch.setattr(retention, "_unused", lambda *_: False)
    assert sweep(home, copies[-1]) == []
    monkeypatch.setattr(retention, "_unused", lambda *_: True)
    (copies[0] / "unique-evidence.txt").write_text("preserve")
    assert sweep(home, copies[-1]) == []
    assert all(path.exists() for path in copies)


def test_checkpoint_reference_and_broken_metadata_are_fail_closed(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retention, "_unused", lambda *_: True)
    copies = [saved(home, NOW - timedelta(minutes=minutes)) for minutes in (3, 2, 1, 0)]
    checkpoint = home / "cutover-workspace" / "staging" / ".deploy.json"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text(
        json.dumps({"snapshot": {"path": str(copies[0] / backup.DUMP)}})
    )
    assert sweep(home, copies[-1]) == []
    checkpoint.write_text("interrupted json")
    assert sweep(home, copies[-1]) == []
    assert all(path.exists() for path in copies)


def test_restoring_holds_reader_lock_for_entire_import(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copies = [saved(home, NOW - timedelta(minutes=minutes)) for minutes in (3, 2, 1, 0)]

    def import_database(*_: object) -> None:
        assert sweep(home, copies[-1]) == []
        assert copies[0].exists()
        raise CutoverError("stop before real site operations")

    monkeypatch.setattr(backup, "restore_database", import_database)
    with pytest.raises(CutoverError, match="stop before real"):
        backup.restore(target(home), copies[0])
    with retention.locked(home):
        pass  # Reader was released on failure.


@pytest.mark.parametrize("shared", [False, True])
def test_same_size_change_even_with_restored_mtime_is_not_a_valid_recovery_point(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    shared: bool,
) -> None:
    monkeypatch.setattr(retention, "_unused", lambda *_: True)
    copies = [saved(home, NOW - timedelta(minutes=minutes)) for minutes in (3, 2, 1, 0)]
    changed = copies[-1] / UPLOADS / "image.png"
    if shared:
        sibling = copies[-2] / UPLOADS / "image.png"
        sibling.unlink()
        os.link(changed, sibling)
    sweep(home, copies[-1])
    # Recreate the expired point to show that a second sweep cannot delete it
    # on the strength of the cached proof from before the edit.
    expired = saved(home, NOW - timedelta(minutes=4))
    stat = changed.stat()
    changed.write_bytes(b"different image")
    os.utime(changed, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert sweep(home, copies[-1]) == []
    assert expired.exists()


def test_damaged_explicit_baseline_blocks_deletion(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retention, "_unused", lambda *_: True)
    baseline = saved(home, NOW - timedelta(days=20), legacy=True)
    retention.register(baseline, target(home), baseline=True)
    copies = [saved(home, NOW - timedelta(minutes=minutes)) for minutes in (3, 2, 1, 0)]
    (baseline / backup.MANIFEST).write_text("broken")
    assert sweep(home, copies[-1]) == []
    assert all(path.exists() for path in copies)


def test_legacy_registration_cannot_change_an_already_bound_source(home: Path) -> None:
    legacy = saved(home, NOW, legacy=True)
    retention.register(legacy, target(home), baseline=True)
    before = (home / retention.STATE).read_bytes()
    with pytest.raises(CutoverError, match="source mismatch"):
        retention.register(legacy, replace(target(home), root="/different"))
    assert (home / retention.STATE).read_bytes() == before


def test_proof_cache_discards_expired_and_superseded_stat_keys(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retention, "_unused", lambda *_: True)
    copies = [saved(home, NOW - timedelta(minutes=minutes)) for minutes in (3, 2, 1, 0)]
    sweep(home, copies[-1])
    state = json.loads((home / retention.STATE).read_text())
    key = json.dumps(retention.identity(target(home)))
    initial_count = len(state["proofs"][key])
    state["proofs"][key]["obsolete-stat"] = "a" * 64
    (home / retention.STATE).write_text(json.dumps(state))
    sweep(home, copies[-1])
    after = json.loads((home / retention.STATE).read_text())
    assert len(after["proofs"][key]) == initial_count
    assert "obsolete-stat" not in after["proofs"][key]


def test_unproven_unique_candidate_content_is_hashed_before_deletion(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retention, "_unused", lambda *_: True)
    copies = [saved(home, NOW - timedelta(minutes=minutes)) for minutes in (3, 2, 1, 0)]
    changed = copies[0] / UPLOADS / "image.png"
    changed.write_bytes(b"different image")
    assert sweep(home, copies[-1]) == []
    assert copies[0].exists()


@pytest.mark.parametrize("failure", [CutoverError("failed transfer"), SystemExit(130)])
def test_failed_or_interrupted_create_does_not_rotate_existing_copies(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
) -> None:
    copies = [saved(home, NOW - timedelta(minutes=minutes)) for minutes in (4, 3, 2, 1)]

    def fail(*_: object, **__: object) -> None:
        raise failure

    monkeypatch.setattr(backup, "dump_to", fail)
    with pytest.raises(type(failure)):
        backup.create(target(home), home, now=NOW)
    assert all(path.exists() for path in copies)
    with retention.locked(home, writer=True), retention.locked(home):
        pass


def test_multiple_expired_hard_links_share_one_content_verification(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(retention, "_unused", lambda *_: True)
    oldest = saved(home, NOW - timedelta(minutes=6))
    copies = [oldest] + [
        saved(home, NOW - timedelta(minutes=m), previous=oldest)
        for m in (5, 4, 3, 2, 1, 0)
    ]
    for path in copies:
        manifest = path / backup.MANIFEST
        data = json.loads(manifest.read_text())
        data["files"][f"{UPLOADS}/image.png"].pop("verified_stat")
        manifest.write_text(json.dumps(data))
    original = backup.sha256
    checked: list[Path] = []

    def observe(path: Path) -> str:
        if path.name == "image.png":
            checked.append(path)
        return original(path)

    monkeypatch.setattr(backup, "sha256", observe)
    assert len(sweep(home, copies[-1])) == 4
    assert len(checked) == 1
    assert all(
        (path / UPLOADS / "image.png").read_bytes() == b"unchanged image"
        for path in copies[-3:]
    )


def test_state_write_failure_authorizes_no_deletion(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copies = [saved(home, NOW - timedelta(minutes=m)) for m in (3, 2, 1, 0)]

    def fail(*_: object) -> None:
        raise OSError("full disk")

    monkeypatch.setattr(retention, "_save", fail)
    assert sweep(home, copies[-1]) == []
    assert all(path.exists() for path in copies)


@pytest.mark.parametrize(
    "command,write,sessions",
    [("backup", True, 1), ("backup", False, 0), ("register-backup", True, 0)],
)
def test_backup_write_dispatch_owns_one_task_session_without_deploy_workspace(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    write: bool,
    sessions: int,
) -> None:
    entered: list[Target] = []

    class Connected(Target):
        @contextmanager
        def session(self) -> Iterator[Target]:
            entered.append(self)
            yield replace(self, label="connected")

    site = Connected(**target(home).__dict__)
    monkeypatch.setattr(cli, "_target", lambda _: site)
    parser = cli._parser()
    args = parser.parse_args([command] + (["--write"] if write else []))
    observed: list[str] = []

    def run_steps(*args: object) -> int:
        connected = args[2]
        assert isinstance(connected, Target)
        observed.append(connected.label)
        return 0

    monkeypatch.setattr(cli, "_run_steps", run_steps)
    assert cli._run(args, parser) == 0
    assert len(entered) == sessions
    assert observed == ["connected" if sessions else site.label]
