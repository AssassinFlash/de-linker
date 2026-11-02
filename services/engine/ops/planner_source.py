#!/usr/bin/env python3
"""Pack and verify the reviewed Git source closure for a Planner release."""

from __future__ import annotations

import argparse
import json
import re
import runpy
import sys
from pathlib import Path
from typing import Any

MANIFEST = ".git-source-manifest.json"
REQUIRED = {
    ".python-version",
    "pyproject.toml",
    "uv.lock",
    "data/plz_de.csv.gz",
    "ops/planner_source.py",
    "ops/planner_release.py",
    "ops/legacy_release.py",
}
ROOTS = {"src", "schemas", "data", "ops"}


def legacy() -> dict[str, Any]:
    # Use the same Git object inventory, byte checks and verifier as Engine.
    return runpy.run_path(str(Path(__file__).with_name("legacy_release.py")))


def check_manifest(path: Path) -> None:
    """Reject incomplete, changed, linked or extra inputs in a new release."""
    manifest_file = path / MANIFEST
    if manifest_file.is_symlink() or not manifest_file.is_file():
        raise ValueError("reviewed Planner source manifest required")
    manifest = json.loads(manifest_file.read_bytes())
    if not isinstance(manifest, dict) or set(manifest) != {
        "revision",
        "blobs",
        "baseline",
    }:
        raise ValueError("invalid Planner source manifest")
    revision, blobs, baseline = (manifest[k] for k in ("revision", "blobs", "baseline"))
    if (
        not isinstance(revision, str)
        or re.fullmatch(r"[0-9a-f]{40}", revision) is None
        or not isinstance(blobs, dict)
        or not REQUIRED.issubset(blobs)
        or not ROOTS.issubset(
            {Path(k).parts[0] for k in blobs if isinstance(k, str) and k}
        )
        or any(
            not isinstance(k, str)
            or not isinstance(v, str)
            or re.fullmatch(r"[0-9a-f]{40}", v) is None
            for k, v in blobs.items()
        )
        or baseline != {"revision": revision, "blobs": blobs}
    ):
        raise ValueError("incomplete Planner Git closure")
    allowed = {Path(name).parts[0] for name in blobs} | {MANIFEST, ".venv", ".deploy"}
    if any(entry.name not in allowed for entry in path.iterdir()):
        raise ValueError("untracked Planner root input")
    legacy()["verify_source"](path, blobs)


def archive(repository: Path, revision: str) -> bytes:
    """Return one in-memory archive from the exact reviewed Git commit."""
    ops = legacy()
    blobs = ops["git_blobs"](repository, revision)
    if not REQUIRED.issubset(blobs) or not ROOTS.issubset(
        {Path(k).parts[0] for k in blobs}
    ):
        raise ValueError("incomplete Planner Git closure")
    operator = ops["command"](
        [
            "git",
            "-C",
            str(repository),
            "show",
            revision + ":services/engine/ops/planner_source.py",
        ]
    )
    if operator != Path(__file__).read_bytes():
        raise ValueError("Planner source operator is not the reviewed Git entrypoint")
    payload = ops["archive"](repository, revision, revision)
    if not isinstance(payload, bytes):
        raise ValueError("invalid reviewed source archive")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    sys.stdout.buffer.write(archive(args.repository, args.revision))


if __name__ == "__main__":
    main()
