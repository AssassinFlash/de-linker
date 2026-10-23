#!/usr/bin/env python3
"""Independent fixed-source correction replay; never overwrite previous FAILs."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

proof = Path(__file__).resolve().parent
assert not (proof / 'execution-results.json').exists(), 'Use a fresh owned evidence directory'
manifest = json.loads((proof / 'snapshot-manifest.json').read_text())
root = Path(manifest['temp_root']); package = root / 'apps/planner'
previous = proof.parent / 'f48228a8-standards'
originals = {}
for name in ('camera-lifecycle.test.mjs', 'selected-panel.test.mjs', 'controlled-fiber-loader.mjs', 'catalogs.py'):
    blob = (proof / name).read_bytes()
    assert blob == (previous / name).read_bytes(), name
    originals[name] = hashlib.sha256(blob).hexdigest()
(proof / 'original-replay-hashes.json').write_text(json.dumps(originals, indent=2) + '\n')
generated = []
def install(name, blob):
    path = package / 'tests' / name
    assert not path.exists()
    path.write_bytes(blob)
    generated.append({'path': str(path.relative_to(root)), 'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()})
for name in ('controlled-fiber-loader.mjs', 'controlled-fiber.mjs', 'camera-lifecycle.test.mjs', 'selected-panel.test.mjs', 'reveal-focus.test.mjs'):
    install(name, (proof / name).read_bytes())
prefix = (proof / 'camera-lifecycle.test.mjs').read_text().split('\ntest(', 1)[0]
install('camera-lifetime.test.mjs', (prefix + '\n' + (proof / 'camera-lifetime.append.mjs').read_text()).encode())
(proof / 'generated-probes.json').write_text(json.dumps(generated, indent=2) + '\n')
dom_files = [f['path'].removeprefix('apps/planner/') for f in manifest['files'] if f['path'].startswith('apps/planner/tests/') and f['path'].endswith('.test.mjs')]
loader = ['node', '--no-warnings=ExperimentalWarning', '--loader', './tests/tsx-loader.mjs']
controlled = loader + ['--loader', './tests/controlled-fiber-loader.mjs', '--test']
commands = [
    ('targeted-domain', ['node', '--test', 'src/domain/sceneCamera.test.ts', 'src/domain/renderGeometry.test.ts', 'src/domain/renderLifetime.test.ts']),
    ('emitted-graph', ['npm', 'run', 'build:check']),
    ('original-lifecycle-replay', controlled + ['tests/camera-lifecycle.test.mjs']),
    ('real-controls-lifetime', controlled + ['tests/camera-lifetime.test.mjs']),
    ('original-panel-replay', ['node', '--test', 'tests/selected-panel.test.mjs']),
    ('reveal-focus', loader + ['--test', 'tests/reveal-focus.test.mjs']),
    ('fixed-dom-suite', loader + ['--test', *dom_files]),
    ('catalogs', [sys.executable, str(proof / 'catalogs.py'), str(root)]),
]
def run(item):
    name, command = item; start = time.monotonic()
    result = subprocess.run(command, cwd=package, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
    (proof / f'{name}.log').write_text(result.stdout)
    return {'name': name, 'command': command, 'cwd': str(package), 'exit_code': result.returncode,
            'elapsed_s': time.monotonic() - start, 'log': f'{name}.log', 'log_sha256': hashlib.sha256(result.stdout.encode()).hexdigest()}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(run, commands))
(proof / 'execution-results.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
