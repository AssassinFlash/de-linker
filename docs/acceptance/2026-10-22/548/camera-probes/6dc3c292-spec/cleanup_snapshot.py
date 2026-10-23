"""Reclaim only manifest-matching review copies; preserve source and evidence."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

out = Path(__file__).resolve().parent
manifest = json.loads((out / "snapshot-manifest.json").read_text())
root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(manifest["temporary_root"])
if not root.is_absolute() or not root.is_dir() or root.is_symlink():
    raise SystemExit("An existing absolute snapshot directory is required.")
if root.resolve() in [out.resolve(), Path(manifest["repository"]).resolve()]:
    raise SystemExit("Refusing repository/evidence deletion.")
expected = {entry["path"]: entry["sha256"] for entry in manifest["entries"]}
generated = {}
for name in ["camera-loader.mjs", "camera-host.mjs", "camera-probe.mjs", "orbit-followup.mjs", "focus-followup.mjs"]:
    relative = f"apps/planner/tests/{name}"
    digest = hashlib.sha256((out / name).read_bytes()).hexdigest()
    expected[relative] = digest
    generated[relative] = digest
links = {entry["path"]: entry["target"] for entry in manifest["dependency_symlinks"]}
actual_files, actual_links = set(), {}
for directory, directories, files in os.walk(root, followlinks=False):
    for name in list(directories) + files:
        path = Path(directory) / name
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            actual_links[relative] = os.readlink(path)
        elif path.is_file():
            actual_files.add(relative)
if actual_files != set(expected) or actual_links != links:
    raise SystemExit(f"Unexpected snapshot contents; extras={actual_files-set(expected)} missing={set(expected)-actual_files} links={actual_links}")
for relative, digest in expected.items():
    if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
        raise SystemExit(f"Changed snapshot file preserved: {relative}")
old_archive = Path(manifest["previous_fail_archive"])
old_verified = {}
for name, digest in manifest["previous_fail_files"].items():
    if hashlib.sha256((old_archive / name).read_bytes()).hexdigest() != digest:
        raise SystemExit(f"Prior evidence changed: {name}")
    old_verified[name] = digest
processes = subprocess.check_output(["ps", "ax", "-o", "pid=,ppid=,command="], text=True)
records = {}
for line in processes.splitlines():
    parts = line.strip().split(None, 2)
    if len(parts) == 3:
        records[int(parts[0])] = (int(parts[1]), parts[2])
ancestors = {os.getpid()}
pid = os.getpid()
while pid in records and records[pid][0] not in ancestors:
    pid = records[pid][0]
    ancestors.add(pid)
paths = {str(root), str(root.resolve())}
references = [
    {"pid": pid, "command": command}
    for pid, (_, command) in records.items()
    if pid not in ancestors and any(path in command for path in paths)
]
if references:
    raise SystemExit(f"Live snapshot references; preserve: {references}")
free_before = shutil.disk_usage(root).free
payload_bytes = sum((root / relative).stat().st_size for relative in expected)
for relative in expected:
    (root / relative).unlink()
for relative in links:
    (root / relative).unlink()
for directory, _, _ in os.walk(root, topdown=False, followlinks=False):
    Path(directory).rmdir()
assert not root.exists()
free_after = shutil.disk_usage(out).free
result = {
    "owner": manifest["owner"],
    "target": manifest["target"],
    "removed_temporary_root": str(root),
    "purpose_complete": "Fixed-source checks and independent camera counterexamples durably archived",
    "reclaim_condition": manifest["reclaim_condition"],
    "source_files_sha_verified_and_removed": len(manifest["entries"]),
    "generated_probe_copies_sha_verified_and_removed": generated,
    "dependency_symlinks_removed_only": links,
    "removed_file_payload_bytes": payload_bytes,
    "active_process_references_excluding_cleanup_ancestors": references,
    "previous_fail_archive_files_sha_verified_unchanged": len(old_verified),
    "temporary_root_absent_after": not root.exists(),
    "disk_free_before_bytes": free_before,
    "disk_free_after_bytes": free_after,
    "observed_disk_free_change_bytes": free_after-free_before,
    "disk_delta_caveat": "Shared APFS volume and other active work may change free space concurrently; payload bytes are not physical allocation claims.",
    "new_worktree_site_database_or_runtime_instances": 0,
    "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
(out / "cleanup.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
