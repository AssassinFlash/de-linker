from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

out = Path(__file__).resolve().parent
manifest = json.loads((out / 'snapshot-manifest.json').read_text())
root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(manifest['temporary_root'])
for name in ['orbit-followup.mjs', 'focus-followup.mjs']:
    (root / 'apps/planner/tests' / name).write_bytes((out / name).read_bytes())
code = 0
for name in ['orbit', 'focus']:
    attempt = 1
    while (out / f'{name}-attempt-{attempt}.log').exists():
        attempt += 1
    command = ['node', '--no-warnings=ExperimentalWarning', '--loader', './tests/tsx-loader.mjs', '--test', f'tests/{name}-followup.mjs']
    result = subprocess.run(command, cwd=root / 'apps/planner', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (out / f'{name}-attempt-{attempt}.log').write_text(result.stdout)
    (out / f'{name}-attempt-{attempt}.json').write_text(json.dumps({'command': command, 'target': manifest['target'], 'exit_code': result.returncode, 'probe_sha256': hashlib.sha256((out / f'{name}-followup.mjs').read_bytes()).hexdigest(), 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2) + '\n')
    print(result.stdout, flush=True)
    code = code or result.returncode
raise SystemExit(code)
