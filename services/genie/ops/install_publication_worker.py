"""Generate/install the user launchd preparation schedule from an existing private env.

The plist contains a private env-file path, never secrets. The file is not sourced
as shell code: its explicit KEY=value entries become process environment values.

Both the interpreter and the worker source must live outside every `releases/`
root: a schedule pinned into one keeps running only until that release is reaped,
then exits 78 (EX_CONFIG) on every wakeup.
"""

from __future__ import annotations

import argparse
import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import getproxies

LABEL = "com.linker.knowledge-publication"


def missing_definition(result: subprocess.CompletedProcess[str]) -> bool:
    # Actual launchctl print on this Mac returns 113 with this exact diagnostic
    # for an absent label. Other nonzero responses do not establish absence.
    return (
        result.returncode == 113
        and f'Could not find service "{LABEL}"' in result.stderr
    )


def stable_interpreter(python: Path) -> Path:
    """Reject an interpreter that a release rotation can delete under the plist.

    Each service prunes its own ``releases/`` to a bounded number of versions
    (``ops/release.sh`` keeps the live one, its rollback target and one spare).
    An interpreter there satisfies the renderer while that release is current and
    then disappears, leaving launchd exiting 78 (EX_CONFIG) before the worker
    starts. The schedule therefore needs a dedicated environment outside every
    release root, which no rotation reaps.
    """
    resolved = python.resolve()
    # Inspect both the given and the resolved path: a symlink can lead into a
    # release root, and a release root can hold a symlink out of it.
    if "releases" in python.parts or "releases" in resolved.parts:
        raise ValueError("interpreter must outlive release rotation")
    # Keep the given path. Resolving a virtual environment's bin/python symlink
    # selects the base interpreter, which cannot see that environment's packages.
    return python


def stable_source(source: Path) -> Path:
    """Reject a worker source that another service's release rotation can delete.

    The interpreter alone is not enough here: the plist names this root for the
    launcher script, the worker, ``index/`` and its own working directory. Pinning
    the interpreter outside rotation while leaving the source inside only moves
    the exit 78 deadline to the next prune.
    """
    resolved = source.resolve()
    if "releases" in source.parts or "releases" in resolved.parts:
        raise ValueError("worker source must outlive release rotation")
    return source


def verify_interpreter(python: Path, source: Path) -> None:
    """Prove the exact scheduled entrypoint imports before a scheduler owns it.

    A readable file is not a working interpreter for this worker: preparation
    needs the locked ``index`` group (Docling, ONNX runtime,
    sentence-transformers) and the runtime package. Invoking the real entrypoint
    turns a silent post-install exit 78 into an installation error.
    """
    entrypoint = source / "ops/publication_worker.py"
    completed = subprocess.run(
        [str(python), "-B", str(entrypoint), "--help"],
        cwd=str(source),
        env={
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "PYTHONDONTWRITEBYTECODE": "1",
            # The dedicated environment is not the editable install a release
            # carried; the schedule names the source explicitly instead.
            "PYTHONPATH": str(source / "src"),
        },
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode:
        detail = completed.stderr.strip().splitlines()[-1:] or ["unknown failure"]
        raise RuntimeError(
            "interpreter cannot run the publication worker: " + detail[0]
        )


def rendered(
    env_file: Path, settings: dict[str, object], python: Path, source: Path
) -> bytes:
    python = stable_interpreter(python)
    source = stable_source(source)
    if not python.is_absolute() or not python.is_file():
        raise ValueError("existing absolute interpreter required")
    if not (source / "ops/install_publication_worker.py").is_file():
        raise ValueError("existing absolute worker source required")
    program = [
        str(python),
        "-B",
        str(source / "ops/install_publication_worker.py"),
        "run",
        str(env_file),
        "--worker-id",
        str(settings["worker_id"]),
        "--lease-seconds",
        str(settings["lease_seconds"]),
        "--loaded-url",
        str(settings["loaded_url"]),
    ]
    if settings["host"]:
        program += ["--host", str(settings["host"])]
    return plistlib.dumps(
        {
            "Label": LABEL,
            "ProgramArguments": program,
            "StartInterval": settings["interval_seconds"],
            "RunAtLoad": True,
            "WorkingDirectory": str(source),
            # The worker imports the runtime package from this source rather than
            # a release's editable .pth, which used to name a pruned directory.
            "EnvironmentVariables": {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(source / "src"),
            },
        }
    )


def confirm_installed(domain: str, target: Path, arguments: list[str]) -> None:
    """Read back the definition the scheduler actually owns.

    A label can hold a different *file* than the one on disk: the installer
    retains a ``.previous.plist``, and bootstrapping that one leaves its path
    loaded while the edited plist is never consulted. Comparing the loaded path
    and argument list makes the installed file the one that runs.
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


def install_definition(content: bytes) -> None:
    target = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    domain = f"gui/{os.getuid()}"
    arguments = plistlib.loads(content)["ProgramArguments"]
    prior = target.read_bytes() if target.exists() else None
    if prior is not None:
        target.with_suffix(".previous.plist").write_bytes(prior)
    try:
        target.write_bytes(content)
        # Retire the loaded definition only after the disk file is the new one,
        # so a failure here leaves an inspectable plist rather than a stale job.
        subprocess.run(
            ["launchctl", "bootout", f"{domain}/{LABEL}"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        subprocess.run(
            ["launchctl", "bootstrap", domain, str(target)], check=True, timeout=15
        )
        confirm_installed(domain, target, arguments)
    except BaseException as error:
        subprocess.run(
            ["launchctl", "bootout", f"{domain}/{LABEL}"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        # Restore the disk definition for inspection but never bootstrap it. This
        # installer replaces a definition precisely because it is wrong, and the
        # prior one on this host was a release path that exits 78 on every wakeup;
        # reloading it here would re-arm the failure the install was repairing.
        if prior is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(prior)
        observed = subprocess.run(
            ["launchctl", "print", domain + "/" + LABEL],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if not missing_definition(observed):
            error.add_note("schedule unload unconfirmed; no definition is loaded")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument(
        "--interval-seconds",
        required=True,
        type=int,
        help="Polling interval selected for the build machine's availability; revocation does not wait for it",
    )
    parser.add_argument("--lease-seconds", required=True, type=int)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--loaded-url", required=True)
    parser.add_argument("--host")
    parser.add_argument(
        "--python",
        type=Path,
        help="stable interpreter for the scheduled worker (default: this one)",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="immutable worker source outside every release root (default: this one)",
    )
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    env_file = args.env_file.expanduser().resolve(strict=True)
    if env_file.stat().st_mode & 0o077:
        parser.error("private env file must have mode 0600")
    if args.interval_seconds <= 0 or args.lease_seconds <= 0:
        parser.error("interval and lease must be positive")
    python = (args.python or Path(sys.executable)).expanduser()
    source = (args.source or Path(__file__).resolve().parents[1]).expanduser()
    settings: dict[str, object] = {
        "interval_seconds": args.interval_seconds,
        "lease_seconds": args.lease_seconds,
        "worker_id": args.worker_id,
        "loaded_url": args.loaded_url,
        "host": args.host,
    }
    try:
        content = rendered(env_file, settings, python, source)
    except ValueError as error:
        parser.error(str(error))
    if args.install:
        if sys.platform != "darwin":
            parser.error("launchd installation requires the Mac build host")
        verify_interpreter(stable_interpreter(python), stable_source(source))
        install_definition(content)
    else:
        sys.stdout.buffer.write(content)
    return 0


def load_private_environment(path: Path) -> None:
    """Load the existing private worker settings and preserve model proxy routing."""
    if path.stat().st_mode & 0o077:
        raise PermissionError("worker environment is not private")
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        os.environ[key.strip()] = value.strip().strip("'\"")
    direct = os.environ.get("LINKER_PUBLICATION_DIRECT_HOST", "")
    if direct:
        if urlsplit(os.environ["LINKER_PUBLICATION_JOBS_URL"]).hostname != direct:
            raise ValueError("direct publication host differs from configured site")
        # On macOS, NO_PROXY alone suppresses the system proxy map for every
        # domain. Preserve the currently effective defaults before bypassing
        # just our configured site; provider/model traffic keeps its route.
        proxies = getproxies()
        for scheme in ("http", "https", "all"):
            if scheme in proxies:
                os.environ[scheme.upper() + "_PROXY"] = proxies[scheme]
                os.environ[scheme + "_proxy"] = proxies[scheme]
        bypass = [
            item.strip() for item in proxies.get("no", "").split(",") if item.strip()
        ]
        if direct not in bypass:
            bypass.append(direct)
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = ",".join(bypass)


def run_private(path: Path, arguments: list[str]) -> int:
    load_private_environment(path)
    return subprocess.call(
        [
            sys.executable,
            str(Path(__file__).with_name("publication_worker.py")),
            *arguments,
        ],
        cwd=Path(__file__).resolve().parents[1],
    )


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "run":
        sys.exit(run_private(Path(sys.argv[2]), sys.argv[3:]))
    sys.exit(main())
