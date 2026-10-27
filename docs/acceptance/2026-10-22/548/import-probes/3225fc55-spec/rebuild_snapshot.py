from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

evidence = Path(__file__).resolve().parent
manifest = json.loads((evidence / 'snapshot-manifest.json').read_text())
if len(sys.argv) != 2:
    raise SystemExit('Pass one new absolute temporary snapshot path')
root = Path(sys.argv[1])
if not root.is_absolute() or root.exists():
    raise SystemExit('Preserving existing files; pass an absent absolute path')
root.mkdir()
for entry in manifest['entries']:
    value = subprocess.check_output(['git', 'show', manifest['target'] + ':' + entry['path']], cwd=manifest['repository'])
    if hashlib.sha256(value).hexdigest() != entry['sha256']:
        raise RuntimeError('Fixed source blob mismatch: ' + entry['path'])
    path = root / entry['path']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
for link in manifest['dependency_symlinks']:
    (root / link['path']).symlink_to(link['target'], target_is_directory=True)
probes = []
for name in ['independent-roof-import.mjs', 'independent-revision-refusal.mjs']:
    value = (evidence / name).read_bytes()
    path = root / 'apps/planner/tests' / name
    path.write_bytes(value)
    probes.append({'path': path.relative_to(root).as_posix(), 'sha256': hashlib.sha256(value).hexdigest()})
(root / 'reconstruction-manifest.json').write_text(json.dumps({'owner': manifest['owner'], 'target': manifest['target'], 'root': str(root), 'source_manifest': str(evidence / 'snapshot-manifest.json'), 'generated_probes': probes, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'reclaim_condition': 'After preserving unique run evidence, SHA-check and delete the listed fixed files, generated probes and dependency link; remove this reconstruction manifest and empty root'}, indent=2) + '\n')
print(root)
