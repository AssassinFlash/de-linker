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
