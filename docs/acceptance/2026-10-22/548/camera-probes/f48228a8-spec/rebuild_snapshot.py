"""Rebuild this review's small pinned snapshot; never copy dependencies."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

out = Path(__file__).resolve().parent
manifest = json.loads((out / "snapshot-manifest.json").read_text())
if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 rebuild_snapshot.py ABSENT_ABSOLUTE_DIRECTORY | --verify-git")
verify_only = sys.argv[1] == "--verify-git"
destination = None if verify_only else Path(sys.argv[1])
if destination is not None and (not destination.is_absolute() or destination.exists()):
    raise SystemExit("Destination must be an absent absolute path; reuse/reclaim any active snapshot first.")
blobs = []
for entry in manifest["entries"]:
    payload = subprocess.check_output(
        ["git", "show", f'{manifest["target"]}:{entry["path"]}'],
        cwd=manifest["repository"],
    )
    if len(payload) != entry["bytes"] or hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise SystemExit(f'Pinned-source mismatch: {entry["path"]}')
    blobs.append((entry["path"], payload))
if verify_only:
    print(f"Verified {len(blobs)} pinned git blobs without creating a snapshot.")
    raise SystemExit(0)
for dependency in manifest["dependency_symlinks"]:
    if not Path(dependency["target"]).is_dir():
        raise SystemExit(f'Existing dependency directory unavailable: {dependency["target"]}')
destination.mkdir()
for name, payload in blobs:
    target = destination / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
for dependency in manifest["dependency_symlinks"]:
    (destination / dependency["path"]).symlink_to(dependency["target"], target_is_directory=True)
for name in ["camera-loader.mjs", "camera-host.mjs", "camera-probe.mjs"]:
    (destination / "apps/planner/tests" / name).write_bytes((out / name).read_bytes())
print(destination)
