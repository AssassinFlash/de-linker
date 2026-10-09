"""Publish a built index, or roll back to the previous one (docs/specs/10-knowledge-index.md).

    uv run python ops/publish_index.py publish <build dir> [--host user@vps] [--root DIR]
    uv run python ops/publish_index.py rollback [--host user@vps] [--root DIR]
    uv run python ops/publish_index.py status [--host user@vps] [--root DIR]

Without --host the root is a directory on this machine: the local rehearsal of the
VPS layout. With --host the same `index_release.py` runs on the VPS over ssh and the
files go up with rsync. The service reads `<root>/current/index.sqlite`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

RELEASE_SCRIPT = Path(__file__).with_name("index_release.py")
# The VPS layout of the spec (Build 5); `linker_genie.retrieval.DEFAULT_INDEX` reads it.
DEFAULT_ROOT = "/opt/linker-genie/index"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def release(host: str | None, *args: str) -> dict[str, object]:
    """Run index_release.py with `args` on the host (or here) and return its report."""
    if host is None:
        command = [sys.executable, str(RELEASE_SCRIPT), *args]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    else:
        command = ["ssh", host, "python3", "-", *args]
        result = subprocess.run(
            command,
            input=RELEASE_SCRIPT.read_text(encoding="utf-8"),
            check=True,
            capture_output=True,
            text=True,
        )
    report: dict[str, object] = json.loads(result.stdout)
    return report


def publish(build_dir: Path, root: str, host: str | None) -> dict[str, object]:
    """Upload one build as a release, verify it, and make it current."""
    manifest = json.loads((build_dir / "manifest.json").read_text(encoding="utf-8"))
    version = str(manifest["version"])
    expected = str(manifest["file"]["sha256"])
    if _sha256(build_dir / str(manifest["file"]["name"])) != expected:
        raise SystemExit(f"{build_dir}: index.sqlite does not match its manifest")
    incoming = str(release(host, "prepare", root, version)["incoming"])
    target = incoming if host is None else f"{host}:{incoming}"
    subprocess.run(
        [
            "rsync",
            "-a",
            str(build_dir / "index.sqlite"),
            str(build_dir / "manifest.json"),
            f"{target}/",
        ],
        check=True,
    )
    report = release(host, "activate", root, version, expected)
    if (
        report.get("current") != version
        or report.get("index_version") != version
        or not report.get("sha256_ok")
    ):
        raise SystemExit(f"published {version}, but the host reports {report}")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish or roll back the document index."
    )
    parser.add_argument("command", choices=["publish", "rollback", "status"])
    parser.add_argument("build_dir", nargs="?", type=Path)
    parser.add_argument(
        "--host", default=None, help="ssh destination; omit for a local root"
    )
    parser.add_argument("--root", default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    if args.command == "publish":
        if args.build_dir is None:
            parser.error("publish needs the build directory")
        report = publish(args.build_dir, args.root, args.host)
    else:
        report = release(args.host, args.command, args.root)
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
