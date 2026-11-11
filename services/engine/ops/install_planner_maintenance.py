"""Render one native launchd wakeup for the bounded Planner maintenance command.

Default only prints a plist. Installation is an explicit separate deployment.
Hourly wakeups are local time checks; at most one remote attempt per UTC day
is admitted, in the configured 02:00–03:00 UTC default quiet window.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import plistlib
import re
import subprocess
import sys
import time
from pathlib import Path

from planner_maintenance import Archives, Policy, _write, interruption_signals

LABEL = "com.linker.planner-maintenance"


def missing_definition(result: subprocess.CompletedProcess[str]) -> bool:
    # Actual launchctl print on this Mac returns113 with this exact diagnostic
    # for an absent label. Other nonzero responses do not establish absence.
    return (
        result.returncode == 113
        and f'Could not find service "{LABEL}"' in result.stderr
    )


def loaded_arguments(text: str) -> list[str] | None:
    """An unrecognised native print format is unknown, never permission to stop."""
    section = re.search(r"^\s*arguments = \{\n(.*?)^\s*\}", text, re.M | re.S)
    if section is None:
        return None
    return [
        re.sub(r"^\d+\s*=\s*", "", line.strip()).strip('"')
        for line in section.group(1).splitlines()
        if line.strip()
    ]


def undo_bootstrap(domain: str, arguments: list[str]) -> None:
    observed = subprocess.run(
        ["launchctl", "print", domain + "/" + LABEL],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if missing_definition(observed):
        return
    if observed.returncode:
        raise RuntimeError("scheduler_lookup_unconfirmed")
    if loaded_arguments(observed.stdout) != arguments:
        raise RuntimeError("loaded_definition_is_foreign_or_unknown")
    match = re.search(r"^\s*pid = ([0-9]+)$", observed.stdout, re.M)
    try:
        subprocess.run(
            ["launchctl", "bootout", domain + "/" + LABEL], check=True, timeout=15
        )
    except (subprocess.SubprocessError, OSError):
        pass  # A lost bootout response is resolved by readback, never replayed.
    absent = subprocess.run(
        ["launchctl", "print", domain + "/" + LABEL],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if not missing_definition(absent):
        raise RuntimeError("owned_scheduler_unload_unconfirmed")
    if match:
        deadline = time.monotonic() + 15
        while True:
            try:
                os.kill(int(match[1]), 0)
            except ProcessLookupError:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("owned_scheduler_process_exit_unconfirmed")
            time.sleep(0.1)


def stable_interpreter(python: Path) -> Path:
    """Reject an interpreter that a release rotation can delete under the plist.

    Each service prunes its own ``releases/`` to a bounded number of versions
    (``ops/release.sh`` keeps the live one, its rollback target and one spare).
    An interpreter there satisfies the renderer while that release is current and
    then disappears, leaving launchd exiting 78 (EX_CONFIG) before the runner
    starts. The scheduler therefore needs an environment outside every release
    root, which no rotation reaps.
    """
    resolved = python.resolve()
    # Inspect both the given and the resolved path: a symlink can lead into a
    # release root, and a release root can hold a symlink out of it.
    if "releases" in python.parts or "releases" in resolved.parts:
        raise ValueError("interpreter must outlive release rotation")
    # Keep the given path. Resolving a virtual environment's bin/python symlink
    # selects the base interpreter, which cannot see that environment's
    # site-packages: the runner then fails on its first third-party import.
    return python


def verify_interpreter(python: Path, runner: Path) -> None:
    """Prove the exact deployed source imports before a scheduler owns it.

    A readable file is not a working interpreter for this runner: the archive
    verifier needs Pydantic and the sampling modules need the locked scientific
    set. Checking the real import here turns a silent post-install exit 78 into
    an installation error.
    """
    modules = "linker_engine.planning.archive, linker_engine.planning.retention, linker_engine.planning.workspace"
    completed = subprocess.run(
        [str(python), "-B", "-c", f"import {modules}"],
        cwd=str(runner.parent),
        env={
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(runner.parent.parent / "src"),
        },
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode:
        detail = completed.stderr.strip().splitlines()[-1:] or ["unknown failure"]
        raise RuntimeError(
            "interpreter cannot import the maintenance source: " + detail[0]
        )


def rendered(policy: Policy, python: Path, runner: Path) -> bytes:
    policy.validate()
    Archives(policy)  # Existing source/owner binding; rendering changes no data.
    if not python.is_absolute() or not python.is_file() or not runner.is_file():
        raise ValueError("existing absolute interpreter and runner required")
    python = stable_interpreter(python)
    arguments = [
        str(python),
        "-B",
        str(runner.resolve()),
        "--host",
        policy.host,
        "--root",
        str(policy.root),
        "--archives",
        str(policy.archives),
        "--owner",
        policy.owner,
        "--hour-utc",
        str(policy.hour_utc),
        "--window-minutes",
        str(policy.window_minutes),
        "--budget-seconds",
        str(policy.budget_seconds),
    ]
    return plistlib.dumps(
        {
            "Label": LABEL,
            "ProgramArguments": arguments,
            "WorkingDirectory": str(runner.resolve().parent),
            # Never KeepAlive/retry a failed maintenance. Reboot/wake may run once
            # locally; run() independently enforces window and daily-attempt limits.
            "RunAtLoad": True,
            "StartInterval": policy.window_minutes * 60,
            "EnvironmentVariables": {
                "PYTHONDONTWRITEBYTECODE": "1",
                # The stable utility source is distinct from a shared interpreter's
                # editable package. Deployment verifies this exact import first.
                "PYTHONPATH": str(runner.resolve().parent.parent / "src"),
            },
        }
    )


def main() -> int:
    with interruption_signals():
        return _main()


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--root", type=Path, default=Path("/opt/linker-planner"))
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--hour-utc", type=int, default=2)
    parser.add_argument("--window-minutes", type=int, default=60)
    parser.add_argument("--budget-seconds", type=int, default=600)
    parser.add_argument(
        "--python",
        type=Path,
        help="stable interpreter for the scheduled runner (default: this one)",
    )
    parser.add_argument("--install", action="store_true")
    args = vars(parser.parse_args())
    install = args.pop("install")
    python = args.pop("python") or Path(sys.executable)
    policy = Policy(**args)
    runner = Path(__file__).with_name("planner_maintenance.py")
    content = rendered(policy, python, runner)
    if not install:
        sys.stdout.buffer.write(content)
        return 0
    if sys.platform != "darwin":
        parser.error("launchd maintenance installation requires the Mac build host")
    verify_interpreter(stable_interpreter(python), runner.resolve())
    # A RunAtLoad child must not begin remote maintenance before the installer
    # has committed its definition. Reuse the runner's singleton inode.
    with (policy.archives / "maintenance.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        install_definition(content)
    return 0


def confirm_installed(domain: str, target: Path, arguments: list[str]) -> None:
    """Read back the definition the scheduler actually owns.

    A label can hold a different *file* than the one on disk: bootstrapping the
    retained ``.previous.plist`` leaves that path loaded while the current plist
    is never consulted, so an edited plist silently changes nothing. Comparing
    the loaded path and argument list makes the installed file the one that runs.
    """
    observed = subprocess.run(
        ["launchctl", "print", domain + "/" + LABEL],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if observed.returncode:
        raise RuntimeError("installed_schedule_readback_failed")
    loaded_path = re.search(r"^\s*path = (.+)$", observed.stdout, re.M)
    if loaded_path is None or Path(loaded_path.group(1).strip()) != target:
        raise RuntimeError("installed_schedule_owns_a_different_definition")
    if loaded_arguments(observed.stdout) != arguments:
        raise RuntimeError("installed_schedule_arguments_not_loaded")


def install_definition(content: bytes) -> None:
    target = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
    domain = f"gui/{os.getuid()}"
    # Refuse replacing a running definition. The operator can inspect the one
    # original plist and stop its idle schedule explicitly before an upgrade.
    current = subprocess.run(
        ["launchctl", "print", domain + "/" + LABEL],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if current.returncode == 0:
        raise RuntimeError("existing maintenance schedule must be retired first")
    if not missing_definition(current):
        raise RuntimeError("scheduler_lookup_unconfirmed")
    arguments = plistlib.loads(content)["ProgramArguments"]
    prior = target.read_bytes() if target.exists() else None
    if prior is not None:
        _write(target.with_suffix(".previous.plist"), prior)
    try:
        _write(target, content)
        subprocess.run(
            ["launchctl", "bootstrap", domain, str(target)], check=True, timeout=15
        )
        confirm_installed(domain, target, arguments)
    except BaseException as error:
        try:
            undo_bootstrap(domain, arguments)
        except BaseException as cleanup_error:
            # The disk definition stays inspectable until native ownership and
            # exit are confirmed; never silently replace a loaded foreign job.
            error.add_note(
                "scheduler cleanup unconfirmed: " + type(cleanup_error).__name__
            )
            raise error from cleanup_error
        if prior is None:
            target.unlink(missing_ok=True)
        else:
            _write(target, prior)
        raise


if __name__ == "__main__":
    sys.exit(main())
