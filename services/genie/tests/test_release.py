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
