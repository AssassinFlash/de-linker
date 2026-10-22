"""Project network migration: real streamed tar backup and native shell rollback."""

import os
import subprocess
from pathlib import Path

import pytest

OPS = Path(__file__).resolve().parents[1] / "ops"
FILES = ("etc/linker-engine-tls/nginx.conf", "etc/systemd/system/linker-engine.service")


def setup(tmp_path: Path) -> tuple[dict[str, str], Path]:
    root, tools = tmp_path / "root", tmp_path / "bin"
    tools.mkdir()
    for relative in FILES:
        p = root / relative
        p.parent.mkdir(parents=True)
        p.write_text("original " + relative)
        p.chmod(0o640)
    unrelated = root / "etc/nginx/nginx.conf"
    unrelated.parent.mkdir()
    unrelated.write_text("unrelated proxy stays intact")
    calls = tmp_path / "calls"
    for tool in ["nginx", "systemctl"]:
        p = tools / tool
        p.write_text(
            "#!/bin/sh\n"
            f'echo "{tool} $*" >> "{calls}"\n'
            + ('test -z "$REFUSE_SYNTAX"\n' if tool == "nginx" else "")
        )
        p.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{tools}:{os.environ['PATH']}",
        "NGINX": str(tools / "nginx"),
        "LINKER_BOUNDARY_ROOT": str(root),
    }, root


def run(env: dict[str, str], command: str, archive: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["bash", str(OPS / "network-boundary.sh"), command],
        env=env,
        input=archive,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    return result.stdout


def test_streamed_backup_apply_and_rollback_preserve_other_services(
    tmp_path: Path,
) -> None:
    env, root = setup(tmp_path)
    original = [(root / f).read_bytes() for f in FILES]
    archive = run(env, "backup")
    assert archive and not (tmp_path / "calls").exists()
    run(env, "apply")
    assert (root / FILES[0]).read_bytes() == (OPS / "nginx.conf").read_bytes()
    assert (root / FILES[1]).read_bytes() == (
        OPS / "linker-engine.service"
    ).read_bytes()
    run(env, "rollback", archive)
    assert [(root / f).read_bytes() for f in FILES] == original
    assert all((root / f).stat().st_mode & 0o777 == 0o640 for f in FILES)
    assert (root / "etc/nginx/nginx.conf").read_text() == "unrelated proxy stays intact"
    calls = (tmp_path / "calls").read_text()
    assert calls.count("systemctl restart linker-engine.service") == 2
    assert calls.count("systemctl reload linker-engine-tls.service") == 2
    assert "iptables" not in calls and "sshd" not in calls


def test_invalid_candidate_leaves_config_and_services_untouched(tmp_path: Path) -> None:
    env, root = setup(tmp_path)
    env["REFUSE_SYNTAX"] = "1"
    original = [(root / f).read_bytes() for f in FILES]
    with pytest.raises(AssertionError):
        run(env, "apply")
    assert [(root / f).read_bytes() for f in FILES] == original
    assert "systemctl" not in (tmp_path / "calls").read_text()
