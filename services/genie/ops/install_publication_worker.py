"""Generate/install the user launchd preparation schedule from an existing private env.

The plist contains a private env-file path, never secrets. The file is not sourced
as shell code: its explicit KEY=value entries become process environment values.
"""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import getproxies

LABEL = "com.linker.knowledge-publication"


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
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    env_file = args.env_file.expanduser().resolve(strict=True)
    if env_file.stat().st_mode & 0o077:
        parser.error("private env file must have mode 0600")
    if args.interval_seconds <= 0 or args.lease_seconds <= 0:
        parser.error("interval and lease must be positive")
    program = [
        sys.executable,
        str(Path(__file__).resolve()),
        "run",
        str(env_file),
        "--worker-id",
        args.worker_id,
        "--lease-seconds",
        str(args.lease_seconds),
        "--loaded-url",
        args.loaded_url,
    ]
    if args.host:
        program += ["--host", args.host]
    plist = {
        "Label": LABEL,
        "ProgramArguments": program,
        "StartInterval": args.interval_seconds,
        "RunAtLoad": True,
        "WorkingDirectory": str(Path(__file__).resolve().parents[1]),
    }
    target = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    if args.install:
        target.parent.mkdir(parents=True, exist_ok=True)
        # Read the current launch definition before replacing it. Retain only one
        # small previous plist for recovery; secrets are in neither definition.
        subprocess.run(
            ["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"],
            check=False,
            capture_output=True,
        )
        if target.exists():
            previous = target.with_suffix(".previous.plist")
            previous.write_bytes(target.read_bytes())
        target.write_bytes(plistlib.dumps(plist))
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(target)], check=True
        )
    else:
        sys.stdout.buffer.write(plistlib.dumps(plist))
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
