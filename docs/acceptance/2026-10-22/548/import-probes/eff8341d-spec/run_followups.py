from pathlib import Path
import hashlib
import json
import subprocess
import concurrent.futures
import datetime
import sys

out = Path(__file__).resolve().parent
manifest = json.loads((out / 'snapshot-manifest.json').read_text())
snapshot = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(manifest['temporary_root'])
prior = {}
for entry in manifest['prior_probes']:
    name = Path(entry['path']).name
    assert hashlib.sha256(Path(entry['archive']).read_bytes()).hexdigest() == entry['sha256']
    prior[name] = Path(entry['archive'])
prefix = prior['independent-roof-import.mjs'].read_bytes()
suffix = (out / 'followup-additions.mjs').read_bytes()
composed = snapshot / 'apps/planner/tests/composed-eff-probe.mjs'
composed.write_bytes(prefix + b'\n' + suffix)
revision = prior['independent-revision-refusal.mjs'].read_text()
assert revision.count("let failure={status:400,code:'request_failed'}") == 1
assert revision.count("if(failure)return json({error:{code:failure.code}},failure.status);") == 1
revision = revision.replace("let failure={status:400,code:'request_failed'}", "let failure={status:422,payload:[]}")
revision = revision.replace("if(failure)return json({error:{code:failure.code}},failure.status);", "if(failure)return json(Object.hasOwn(failure,'payload')?failure.payload:{error:{code:failure.code}},failure.status);")
revision = revision.replace('real revision transport keeps unknown or wrong-pair intents', 'real revision response parsing keeps unknown or wrong-pair intents')
(out / 'revision-parser-probe.mjs').write_text(revision)
parser = snapshot / 'apps/planner/tests/revision-parser-probe.mjs'
parser.write_text(revision)
node = ['node', '--no-warnings=ExperimentalWarning', '--loader', './tests/tsx-loader.mjs', '--test']
jobs = [('followup', node + ['--test-name-pattern=^followup:', 'tests/composed-eff-probe.mjs'], composed), ('revision-parser', node + ['tests/revision-parser-probe.mjs'], parser)]

def run(job):
    name, command, generated = job
    attempt = 1
    while (out / f'{name}-attempt-{attempt}.log').exists():
        attempt += 1
    result = subprocess.run(command, cwd=snapshot / 'apps/planner', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (out / f'{name}-attempt-{attempt}.log').write_text(result.stdout)
    meta = {'command': command, 'target': manifest['target'], 'cwd': 'apps/planner', 'exit_code': result.returncode, 'retained_probes_unchanged': True, 'prefix_sha256': hashlib.sha256(prefix).hexdigest(), 'suffix_sha256': hashlib.sha256(suffix).hexdigest(), 'generated_path': generated.relative_to(snapshot).as_posix(), 'generated_sha256': hashlib.sha256(generated.read_bytes()).hexdigest(), 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out / f'{name}-attempt-{attempt}.json').write_text(json.dumps(meta, indent=2) + '\n')
    return {'name': name, 'attempt': attempt, 'exit_code': result.returncode, 'output': result.stdout}

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(run, jobs))
for result in results:
    print(json.dumps(result))
raise SystemExit(0 if all(result['exit_code'] == 0 for result in results) else 1)
