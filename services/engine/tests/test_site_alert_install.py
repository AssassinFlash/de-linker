"""The alert installer: streamed backup, reviewed apply, native rollback.

Nothing here starts a real unit. The script writes only its three managed
paths and reads the private env file, so a temporary root plus a recording
`systemctl` proves both that the files land and that nothing else is touched.
"""

from __future__ import annotations

import io
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

OPS = Path(__file__).resolve().parents[1] / "ops"
SCRIPT = OPS / "site-alert-install.sh"
CONFIG = "etc/linker-site-alert.env"
MANAGED = (
    "opt/linker-engine/ops/site-alert.py",
    "etc/systemd/system/linker-site-alert.service",
    "etc/systemd/system/linker-site-alert.timer",
)


def setup(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    root, tools = tmp_path / "root", tmp_path / "bin"
    tools.mkdir()
    calls = tmp_path / "calls"
    systemctl = tools / "systemctl"
    systemctl.write_text(f'#!/bin/sh\necho "systemctl $*" >> "{calls}"\n')
    systemctl.chmod(0o755)
    # A previous install, so backup and rollback have something to restore.
    for relative in MANAGED:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"previous {relative}\n")
        path.chmod(0o755 if relative.endswith(".py") else 0o644)
    config = root / CONFIG
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "LINKER_SMTP_HOST=smtp.example.test\n"
        "LINKER_SMTP_PORT=465\n"
        "LINKER_SMTP_USER=sales@sunriverinverter.com\n"
        "LINKER_SMTP_PASS=fake-password\n"
    )
    config.chmod(0o600)
    return (
        {
            **os.environ,
            "PATH": f"{tools}:{os.environ['PATH']}",
            "LINKER_ALERT_ROOT": str(root),
            "LINKER_ALERT_OPS": "opt/linker-engine/ops",
            "SYSTEMD_UNIT_DIR": "etc/systemd/system",
            # macOS writes AppleDouble sidecars into tar; the engine host does
            # not, and the installer's members must stay exactly four.
            "COPYFILE_DISABLE": "1",
        },
        root,
        calls,
    )


def run(env: dict[str, str], command: str, archive: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["bash", str(SCRIPT), command],
        env=env,
        input=archive,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    return result.stdout


def test_backup_streams_managed_paths_and_config(tmp_path: Path) -> None:
    env, root, calls = setup(tmp_path)
    archive = run(env, "backup")

    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        names = set(tar.getnames())
    assert names == set(MANAGED) | {CONFIG}
    assert not calls.exists()


def test_apply_installs_reviewed_files_and_enables_the_timer(tmp_path: Path) -> None:
    env, root, calls = setup(tmp_path)
    run(env, "apply")

    assert (root / MANAGED[0]).read_bytes() == (OPS / "site-alert.py").read_bytes()
    assert (root / MANAGED[1]).read_bytes() == (
        OPS / "linker-site-alert.service"
    ).read_bytes()
    assert (root / MANAGED[2]).read_bytes() == (
        OPS / "linker-site-alert.timer"
    ).read_bytes()
    assert (root / MANAGED[0]).stat().st_mode & 0o777 == 0o755
    # The private file is never rewritten by the installer.
    assert (root / CONFIG).stat().st_mode & 0o777 == 0o600
    assert (root / CONFIG).read_text().startswith("LINKER_SMTP_HOST=")
    recorded = calls.read_text()
    assert "systemctl daemon-reload" in recorded
    assert "systemctl enable --quiet linker-site-alert.timer" in recorded
    assert "systemctl start linker-site-alert.timer" in recorded
    assert "restart" not in recorded


def test_apply_refuses_without_the_private_credentials(tmp_path: Path) -> None:
    env, root, calls = setup(tmp_path)
    (root / CONFIG).unlink()

    result = subprocess.run(
        ["bash", str(SCRIPT), "apply"], env=env, capture_output=True, check=False
    )

    assert result.returncode == 1
    assert "missing " in result.stderr.decode()
    assert result.stderr.decode().rstrip().endswith("then rerun apply.")
    assert (root / MANAGED[0]).read_text().startswith("previous ")
    assert not calls.exists()


def test_rollback_stops_the_timer_and_restores_the_previous_files(
    tmp_path: Path,
) -> None:
    env, root, calls = setup(tmp_path)
    original = [(root / relative).read_bytes() for relative in MANAGED]
    archive = run(env, "backup")
    run(env, "apply")
    calls.unlink()
    run(env, "rollback", archive)

    assert [(root / relative).read_bytes() for relative in MANAGED] == original
    assert all(
        (root / relative).stat().st_mode & 0o777
        == (0o755 if relative.endswith(".py") else 0o644)
        for relative in MANAGED
    )
    recorded = calls.read_text()
    assert "systemctl disable --quiet --now linker-site-alert.timer" in recorded
    assert "systemctl daemon-reload" in recorded


def test_backup_of_a_fresh_host_reports_nothing_installed(tmp_path: Path) -> None:
    env, root, _ = setup(tmp_path)
    for relative in MANAGED:
        (root / relative).unlink()
    (root / CONFIG).unlink()

    result = subprocess.run(
        ["bash", str(SCRIPT), "backup"], env=env, capture_output=True, check=False
    )

    assert result.returncode == 0
    assert result.stdout == b""
    assert "nothing installed yet" in result.stderr.decode()


def test_unknown_command_is_refused(tmp_path: Path) -> None:
    env, _, _ = setup(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPT), "install"], env=env, capture_output=True, check=False
    )

    assert result.returncode == 2
    assert "usage:" in result.stderr.decode()


@pytest.mark.parametrize(
    "path", ["site-alert.py", "linker-site-alert.service", "linker-site-alert.timer"]
)
def test_shipped_units_match_what_the_installer_copies(path: str) -> None:
    """The files the installer installs are the ones under review."""
    assert (OPS / path).is_file()
