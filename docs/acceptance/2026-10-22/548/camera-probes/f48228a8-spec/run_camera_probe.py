from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

out = Path(__file__).resolve().parent
manifest = json.loads((out / 'snapshot-manifest.json').read_text())
root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(manifest['temporary_root'])
files = ['camera-loader.mjs', 'camera-host.mjs', 'camera-probe.mjs']
for name in files:
    (root / 'apps/planner/tests' / name).write_bytes((out / name).read_bytes())
attempt = 1
while (out / f'independent-attempt-{attempt}.log').exists():
    attempt += 1
command = ['node', '--no-warnings=ExperimentalWarning', '--loader', './tests/camera-loader.mjs', '--test', 'tests/camera-probe.mjs']
result = subprocess.run(command, cwd=root / 'apps/planner', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
(out / f'independent-attempt-{attempt}.log').write_text(result.stdout)
(out / f'independent-attempt-{attempt}.json').write_text(json.dumps({'command': command, 'cwd': 'apps/planner', 'target': manifest['target'], 'exit_code': result.returncode, 'probes': {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in files}, 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2) + '\n')
print(result.stdout)
raise SystemExit(result.returncode)
