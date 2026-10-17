"""ops/activate.sh: venvs, the judge unit, restarts, and the token rule.

`uv` and `systemctl` are stand-ins on PATH that record their calls; the
stand-in systemctl reports every unit active unless the test says otherwise.
"""

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "ops" / "activate.sh"
UNIT = Path(__file__).resolve().parents[1] / "ops" / "linker-genie-judge.service"


def _tree(tmp_path: Path, token: bool) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls.txt"
    (bin_dir / "uv").write_text(f'#!/bin/sh\necho "uv $PWD $*" >> {calls}\n')
    (bin_dir / "systemctl").write_text(
        "#!/bin/sh\n"
        f'echo "systemctl $*" >> {calls}\n'
        'if [ "$1" = is-active ] && [ -n "$DOWN" ] && [ "$3" = "$DOWN" ]; then exit 3; fi\n'
    )
    for tool in ("uv", "systemctl"):
        (bin_dir / tool).chmod(0o755)
    for root in ("engine", "genie"):
        (tmp_path / root / "current" / "ops").mkdir(parents=True)
    (tmp_path / "genie" / "current" / "ops" / UNIT.name).write_text(UNIT.read_text())
    (tmp_path / "units").mkdir()
    env_file = tmp_path / "linker-genie.env"
    env_file.write_text(
        "GENIE_WP_URL=https://site.example\n"
        + ("GENIE_JUDGE_TOKEN=abc\n" if token else "")
    )
    return {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "UV": str(bin_dir / "uv"),
        "SYSTEMD_UNIT_DIR": str(tmp_path / "units"),
        "GENIE_ENV_FILE": str(env_file),
        "ENGINE_RELEASE_ROOT": str(tmp_path / "engine"),
        "GENIE_RELEASE_ROOT": str(tmp_path / "genie"),
        "ACTIVATE_SETTLE_SECONDS": "0",
    }


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: UP022 — do not use capture_output: pytest would print env.
        ["bash", str(SCRIPT)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def _calls(tmp_path: Path) -> list[str]:
    return (tmp_path / "calls.txt").read_text().splitlines()


def test_a_deploy_syncs_installs_and_restarts_all_three(tmp_path: Path) -> None:
    result = _run(_tree(tmp_path, token=True))

    assert result.returncode == 0, result.stderr
    calls = _calls(tmp_path)
    assert calls[0] == f"uv {tmp_path}/engine/current sync --locked --quiet"
    assert calls[1] == f"uv {tmp_path}/genie/current sync --locked --quiet"
    assert (tmp_path / "units" / UNIT.name).read_text() == UNIT.read_text()
    assert "systemctl daemon-reload" in calls
    assert "systemctl enable --quiet linker-genie-judge.service" in calls
    assert (
        "systemctl restart linker-engine.service linker-genie.service "
        "linker-genie-judge.service"
    ) in calls
    assert "active linker-genie-judge.service" in result.stdout


def test_without_the_token_the_worker_is_installed_but_not_started(
    tmp_path: Path,
) -> None:
    result = _run(_tree(tmp_path, token=False))

    assert result.returncode == 3
    assert "GENIE_JUDGE_TOKEN is not set" in result.stderr
    calls = _calls(tmp_path)
    assert (tmp_path / "units" / UNIT.name).is_file()
    assert "systemctl restart linker-engine.service linker-genie.service" in calls
    assert not any("enable" in call for call in calls)


def test_a_unit_that_does_not_come_up_fails_the_run(tmp_path: Path) -> None:
    env = _tree(tmp_path, token=True)
    env["DOWN"] = "linker-genie-judge.service"
    result = _run(env)

    assert result.returncode == 1
    assert "NOT ACTIVE linker-genie-judge.service" in result.stderr
