#!/usr/bin/env python3
"""Reclaim this exact reconstructible snapshot only after SHA verification."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil

proof = Path(__file__).resolve().parent
manifest = json.loads((proof / 'snapshot-manifest.json').read_text())
root = Path(manifest['temp_root'])
assert root.name.startswith('camera-standards-6dc3-') and root.parent.name == 'T'
assert root.is_dir() and not root.is_symlink()
expected = manifest['files'] + json.loads((proof / 'generated-probes.json').read_text())
expected_paths = set()
for item in expected:
    name = item['path']; expected_paths.add(name)
    path = root / name
    assert path.is_file() and not path.is_symlink(), name
    blob = path.read_bytes()
    assert len(blob) == item['bytes'] and hashlib.sha256(blob).hexdigest() == item['sha256'], name
actual = set()
links = []
for directory, dirs, files in os.walk(root, followlinks=False):
    for name in dirs[:]:
        path = Path(directory) / name
        if path.is_symlink():
            links.append(path)
            dirs.remove(name)
    for name in files:
        actual.add(str((Path(directory) / name).relative_to(root)))
deps_link = root / 'apps/planner/node_modules'
assert links == [deps_link], links
deps = Path(manifest['dependency_symlink'])
assert deps_link.resolve() == deps.resolve() and deps.is_dir()
assert actual == expected_paths, sorted(actual ^ expected_paths)
for item in json.loads((proof / 'execution-results.json').read_text()):
    assert hashlib.sha256((proof / item['log']).read_bytes()).hexdigest() == item['log_sha256'], item['log']
free_before = shutil.disk_usage(root).free
shutil.rmtree(root)
assert not root.exists() and deps.is_dir()
free_after = shutil.disk_usage(root.parent).free
result = {'at_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'removed_snapshot': str(root),
    'sha_clean_original_files': len(manifest['files']), 'original_bytes': sum(f['bytes'] for f in manifest['files']),
    'generated_unique_probe_files': len(expected) - len(manifest['files']),
    'generated_probe_bytes': sum(f['bytes'] for f in expected[len(manifest['files']):]),
    'dependency_symlink_removed': True, 'existing_dependency_directory_retained': str(deps),
    'snapshot_absent': not root.exists(), 'free_bytes_before': free_before, 'free_bytes_after': free_after,
    'observed_free_delta_bytes': free_after - free_before,
    'space_note': 'Observed filesystem delta includes concurrent activity and APFS effects; not an attribution of deleted logical bytes.',
    'retained': 'Only unique executable probes, complete original logs, fixed-SHA manifests and reports in this evidence directory.'}
(proof / 'cleanup.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
