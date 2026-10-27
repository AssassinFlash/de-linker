from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

out = Path(__file__).resolve().parent
manifest = json.loads((out / 'snapshot-manifest.json').read_text())
if len(sys.argv) != 2:
    raise SystemExit('Pass one new absolute temporary snapshot path')
root = Path(sys.argv[1])
if not root.is_absolute() or root.exists():
    raise SystemExit('Preserving existing files: pass an absent absolute path')
root.mkdir()
for entry in manifest['entries']:
    value = subprocess.check_output(['git', 'show', manifest['target'] + ':' + entry['path']], cwd=manifest['repository'])
    assert hashlib.sha256(value).hexdigest() == entry['sha256'], entry['path']
    path = root / entry['path']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
for entry in manifest['dependency_symlinks']:
    (root / entry['path']).symlink_to(entry['target'], target_is_directory=True)
for entry in manifest['prior_probes']:
    value = Path(entry['archive']).read_bytes()
    assert hashlib.sha256(value).hexdigest() == entry['sha256']
    (root / entry['path']).write_bytes(value)
(root / 'reconstruction-manifest.json').write_text(json.dumps({'owner': manifest['owner'], 'target': manifest['target'], 'root': str(root), 'source_manifest': str(out / 'snapshot-manifest.json'), 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'reclaim_condition': 'After unique evidence readback SHA-clean all listed sources, generated test copies and dependency symlinks; remove this manifest and empty root'}, indent=2) + '\n')
print(root)
