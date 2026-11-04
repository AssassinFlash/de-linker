"""ops/release.sh: publish, current symlink, rollback."""

import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "ops" / "release.sh"


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GENIE_RELEASE_ROOT": str(root), "GENIE_RELEASE_KEEP": "3"}
    result = subprocess.run(  # noqa: UP022 — do not use capture_output: pytest would print env.
        ["bash", str(SCRIPT), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"release.sh {' '.join(args)} exited {result.returncode}: {result.stderr.strip()}"
        )
    return result


def test_publish_makes_current_and_rollback_returns(tmp_path: Path) -> None:
    first = tmp_path / "src-a"
    second = tmp_path / "src-b"
    first.mkdir()
    second.mkdir()
    (first / "app").write_text("a")
    (second / "app").write_text("b")
    root = tmp_path / "opt" / "linker-genie"
    SCRIPT.chmod(SCRIPT.stat().st_mode | stat.S_IXUSR)

    one = _run(root, "publish", str(first))
    assert "current=" in one.stdout
    live = (root / "current").resolve()
    assert (live / "app").read_text() == "a"

    _run(root, "publish", str(second))
    assert (root / "current" / "app").read_text() == "b"

    rolled = _run(root, "rollback")
    assert "current=" in rolled.stdout
    assert (root / "current" / "app").read_text() == "a"


def test_status_lists_the_root(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "x").write_text("1")
    root = tmp_path / "releases"
    _run(root, "publish", str(src))
    status = _run(root, "status")
    assert f"root={root}" in status.stdout
    assert "current=" in status.stdout


def test_failed_copy_keeps_current_and_removes_partial_release(tmp_path: Path) -> None:
    """An interrupted copy must never become a rollback candidate."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "app").write_text("working")
    root = tmp_path / "releases"
    _run(root, "publish", str(source))
    live = (root / "current").resolve()
    commands = tmp_path / "commands"
    commands.mkdir()
    copier = commands / "cp"
    copier.write_text('#!/bin/sh\nprintf partial > "$3/partial"\nexit 17\n')
    copier.chmod(0o700)
    result = subprocess.run(  # noqa: UP022 — keep inherited environment out of pytest output.
        ["bash", str(SCRIPT), "publish", str(source)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={
            **os.environ,
            "GENIE_RELEASE_ROOT": str(root),
            "PATH": f"{commands}{os.pathsep}{os.environ['PATH']}",
        },
    )
    assert result.returncode == 17
    assert (root / "current").resolve() == live
    assert (live / "app").read_text() == "working"
    assert sorted(path.name for path in root.iterdir()) == [live.name, "current"]


def test_retention_and_rollback_ignore_persistent_directories(tmp_path: Path) -> None:
    root = tmp_path / "releases"
    for name in ("index", "ops", "state", "unrelated"):
        folder = root / name
        folder.mkdir(parents=True)
        (folder / "keep").write_text(name)
    source = tmp_path / "source"
    source.mkdir()
    published = []
    for value in range(4):
        (source / "version").write_text(str(value))
        _run(root, "publish", str(source))
        published.append((root / "current").resolve())

    assert not published[0].exists()
    assert all(folder.is_dir() for folder in published[1:])
    for name in ("index", "ops", "state", "unrelated"):
        assert (root / name / "keep").read_text() == name
    releases = _run(root, "status").stdout.split("releases=", 1)[1].strip()
    assert releases.split(",") == [folder.name for folder in published[1:]]
    _run(root, "rollback")
    assert (root / "current").resolve() == published[-2]
    assert (root / "current" / "version").read_text() == "2"


def test_publish_can_roll_back_to_existing_paired_release(tmp_path: Path) -> None:
    """The existing production release uses a timestamp plus source revision."""
    root = tmp_path / "releases"
    previous = root / "20261029T024800000000Z-02cedf18"
    previous.mkdir(parents=True)
    (previous / "app").write_text("previous runtime")
    (root / "current").symlink_to(previous.name)
    source = tmp_path / "source"
    source.mkdir()
    (source / "app").write_text("new runtime")
    _run(root, "publish", str(source))
    _run(root, "rollback")
    assert (root / "current").resolve() == previous.resolve()
    assert (root / "current" / "app").read_text() == "previous runtime"


def test_shared_release_refuses_a_managed_pair_before_copy_or_selection(
    tmp_path: Path,
) -> None:
    for kind in ("engine", "genie"):
        root = tmp_path / kind
        old = root / "20261101T000000000000Z"
        old.mkdir(parents=True)
        (old / "original").write_text("preserve")
        (root / "current").symlink_to(old.name)
        if kind == "engine":
            (old / "src/linker_engine").mkdir(parents=True)
        else:
            (root / "index").mkdir()
            (root / "index/.activation.json").write_text("{}")
        source = tmp_path / ("source-" + kind)
        source.mkdir()
        (source / "new").write_text("candidate")
        for arguments in [("publish", str(source)), ("rollback",)]:
            result = subprocess.run(
                ["bash", str(SCRIPT), *arguments],
                env={"PATH": "/usr/bin:/bin", "GENIE_RELEASE_ROOT": str(root)},
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1
            assert "managed runtime" in result.stderr
            assert (root / "current").resolve() == old
            assert (old / "original").read_text() == "preserve"
        assert len([p for p in root.iterdir() if p.name.startswith("2026")]) == 1


def _managed_root(root: Path, versions: list[str], current: str) -> None:
    for name in versions:
        release = root / name
        release.mkdir(parents=True)
        (release / "app").write_text(name)
    (root / "index").mkdir()
    (root / "index" / ".activation.json").write_text("{}")
    (root / "state").mkdir()
    (root / "state" / "work.sqlite").write_text("state")
    (root / "current").symlink_to(current)


def _release_names(root: Path) -> list[str]:
    return sorted(
        path.name
        for path in root.iterdir()
        if path.name.startswith("2026") and not path.is_symlink()
    )


def test_prune_bounds_a_managed_production_root(tmp_path: Path) -> None:
    """The paired flow never runs publish, so retention needs its own entry.

    The layout mirrors the audited production root: eight `-<sha>` releases,
    current on the newest, persistent index and state directories.
    """
    versions = [
        "20261102T090944139352Z-b10202da",
        "20261102T184000000000Z-b43f1e99",
        "20261103T120800000000Z-5ca0b6a8c",
        "20261103T130000000000Z-6b04acaea",
        "20261103T142000000000Z-5a5b21d6c",
        "20261104T075945874165Z-abd3b26a",
        "20261104T084415175869Z-c8160ead",
        "20261104T094242259491Z-8c9e6d80",
    ]
    root = tmp_path / "releases"
    _managed_root(root, versions, versions[-1])

    result = _run(root, "prune")

    assert _release_names(root) == versions[-3:]
    assert (root / "current").resolve() == (root / versions[-1]).resolve()
    assert (root / "index" / ".activation.json").read_text() == "{}"
    assert (root / "state" / "work.sqlite").read_text() == "state"
    assert (
        f"removed={versions[0]},{versions[1]},{versions[2]},{versions[3]},{versions[4]}"
        in (result.stdout)
    )
    assert f"releases={versions[-3]},{versions[-2]},{versions[-1]}" in result.stdout


def test_prune_keeps_the_rollback_target_when_current_is_not_newest(
    tmp_path: Path,
) -> None:
    versions = [
        "20261101T000000000000Z-11111111",
        "20261102T000000000000Z-22222222",
        "20261103T000000000000Z-33333333",
        "20261104T000000000000Z-44444444",
        "20261105T000000000000Z-55555555",
    ]
    root = tmp_path / "releases"
    current = versions[2]
    _managed_root(root, versions, current)

    _run(root, "prune")

    # current and its rollback target survive; the oldest and one newer
    # superseded release are removed.
    assert _release_names(root) == [versions[1], current, versions[4]]
    assert (root / "current").resolve() == (root / current).resolve()


def test_prune_is_a_noop_within_the_bound(tmp_path: Path) -> None:
    versions = [
        "20261101T000000000000Z-11111111",
        "20261102T000000000000Z-22222222",
    ]
    root = tmp_path / "releases"
    _managed_root(root, versions, versions[-1])

    result = _run(root, "prune")

    assert _release_names(root) == versions
    assert "removed=\n" in result.stdout
