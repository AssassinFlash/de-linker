from pathlib import Path
import hashlib
import json
import subprocess
import datetime
import sys

evidence = Path(__file__).resolve().parent
manifest = json.loads((evidence / 'snapshot-manifest.json').read_text())
snapshot = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(manifest['temporary_root'])
source = evidence / 'independent-roof-import.mjs'
generated = snapshot / 'apps/planner/tests/independent-roof-import.mjs'
generated.write_bytes(source.read_bytes())
attempt = 1
while (evidence / f'independent-attempt-{attempt}.log').exists():
    attempt += 1
command = ['node', '--no-warnings=ExperimentalWarning', '--loader', './tests/tsx-loader.mjs', '--test', 'tests/independent-roof-import.mjs']
result = subprocess.run(command, cwd=snapshot / 'apps/planner', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
(evidence / f'independent-attempt-{attempt}.log').write_text(result.stdout)
metadata = {'command': command, 'cwd': 'apps/planner', 'target': manifest['target'], 'base': manifest['base'], 'exit_code': result.returncode, 'probe_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'generated_path': generated.relative_to(snapshot).as_posix(), 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
(evidence / f'independent-attempt-{attempt}.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(result.stdout)
raise SystemExit(result.returncode)
