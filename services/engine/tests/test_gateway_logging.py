"""Dedicated gateway logging deployment: real files/tar, no live services."""

import hashlib
import io
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

OPS = Path(__file__).resolve().parents[1] / "ops"
RELATIVE = "etc/linker-engine-tls/nginx.conf"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    root, tools = tmp_path / "root", tmp_path / "bin"
    tools.mkdir()
    target = root / RELATIVE
    target.parent.mkdir(parents=True)
    target.write_bytes(b"original dedicated configuration\n")
    target.chmod(0o640)
    shared = root / "etc/nginx/nginx.conf"
    shared.parent.mkdir()
    shared.write_text("unrelated shared proxy")
    calls = tmp_path / "calls"
    for name in ("nginx", "systemctl"):
        tool = tools / name
        tool.write_text(
            "#!/bin/sh\n"
            f'echo "{name} $*" >> "{calls}"\n'
            + ('test -z "$REFUSE_SYNTAX"\n' if name == "nginx" else "")
        )
        tool.chmod(0o755)
    return (
        {
            **os.environ,
            "LINKER_TLS_ROOT": str(root),
            "NGINX": str(tools / "nginx"),
            "SYSTEMCTL": str(tools / "systemctl"),
        },
        target,
        calls,
    )


def invoke(
    env: dict[str, str], *args: str, archive: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["bash", str(OPS / "gateway-logging.sh"), *args],
        env=env,
        input=archive,
        capture_output=True,
        check=False,
    )


def test_backup_guarded_apply_and_rollback_only_touch_dedicated_proxy(
    tmp_path: Path,
) -> None:
    env, target, calls = fixture(tmp_path)
    before = target.read_bytes()
    backup = invoke(env, "backup")
    assert backup.returncode == 0, backup.stderr.decode()
    assert not calls.exists()
    with tarfile.open(fileobj=io.BytesIO(backup.stdout)) as archive:
        assert archive.getnames() == [RELATIVE]
    applied = invoke(env, "apply", digest(before))
    assert applied.returncode == 0, applied.stderr.decode()
    candidate = (OPS / "nginx.conf").read_bytes()
    assert target.read_bytes() == candidate
    assert target.stat().st_mode & 0o777 == 0o640
    restored = invoke(env, "rollback", digest(candidate), archive=backup.stdout)
    assert restored.returncode == 0, restored.stderr.decode()
    assert target.read_bytes() == before
    assert target.stat().st_mode & 0o777 == 0o640
    assert (Path(env["LINKER_TLS_ROOT"]) / "etc/nginx/nginx.conf").read_text() == (
        "unrelated shared proxy"
    )
    commands = calls.read_text()
    assert commands.count("systemctl reload linker-engine-tls.service") == 2
    assert "restart" not in commands and "daemon-reload" not in commands
    assert "reload nginx" not in commands and "linker-engine.service" not in commands
    assert not list(target.parent.glob(".linker-tls-log.*"))


@pytest.mark.parametrize("failure", ["stale_hash", "bad_syntax"])
def test_failed_guard_or_candidate_never_installs_or_reloads(
    tmp_path: Path, failure: str
) -> None:
    env, target, calls = fixture(tmp_path)
    before = target.read_bytes()
    expected = digest(before)
    if failure == "stale_hash":
        expected = "0" * 64
    else:
        env["REFUSE_SYNTAX"] = "1"
    result = invoke(env, "apply", expected)
    assert result.returncode != 0
    assert target.read_bytes() == before
    assert not calls.exists() or "systemctl" not in calls.read_text()
    assert not list(target.parent.glob(".linker-tls-log.*"))


def test_rollback_extracts_only_known_configuration_not_other_archive_entries(
    tmp_path: Path,
) -> None:
    env, target, calls = fixture(tmp_path)
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        for name, body in [(RELATIVE, b"restored"), ("etc/unrelated", b"forbidden")]:
            info = tarfile.TarInfo(name)
            info.size = len(body)
            archive.addfile(info, io.BytesIO(body))
    result = invoke(
        env, "rollback", digest(target.read_bytes()), archive=data.getvalue()
    )
    assert result.returncode == 0, result.stderr.decode()
    assert target.read_bytes() == b"restored"
    assert not (Path(env["LINKER_TLS_ROOT"]) / "etc/unrelated").exists()
    assert "reload linker-engine-tls.service" in calls.read_text()


def test_invalid_rollback_archive_never_replaces_or_reloads(tmp_path: Path) -> None:
    env, target, calls = fixture(tmp_path)
    before = target.read_bytes()
    result = invoke(env, "rollback", digest(before), archive=b"not an archive")
    assert result.returncode != 0
    assert target.read_bytes() == before
    assert not calls.exists() or "systemctl" not in calls.read_text()
    assert not list(target.parent.glob(".linker-tls-log.*"))
