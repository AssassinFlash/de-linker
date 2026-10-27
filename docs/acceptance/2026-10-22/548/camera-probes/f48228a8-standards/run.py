#!/usr/bin/env python3
"""Re-run only the camera scope, preserving complete independent logs."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

proof = Path(__file__).resolve().parent
assert not (proof / 'execution-results.json').exists(), 'Preserve original logs; reproduce in a fresh owned evidence directory'
manifest = json.loads((proof / 'snapshot-manifest.json').read_text())
root = Path(manifest['temp_root'])
assert root.is_dir()
package = root / 'apps/planner'
generated = []
for name in ('controlled-fiber-loader.mjs', 'controlled-fiber.mjs', 'camera-lifecycle.test.mjs', 'selected-panel.test.mjs'):
    data = (proof / name).read_bytes()
    path = package / 'tests' / name
    assert not path.exists()
    path.write_bytes(data)
    generated.append({'path': str(path.relative_to(root)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
(proof / 'generated-probes.json').write_text(json.dumps(generated, indent=2) + '\n')
commands = [
    ('targeted-domain', ['node', '--test', 'src/domain/sceneCamera.test.ts', 'src/domain/renderGeometry.test.ts', 'src/domain/renderLifetime.test.ts']),
    ('emitted-graph', ['npm', 'run', 'build:check']),
    ('controlled-lifecycle', ['node', '--no-warnings=ExperimentalWarning', '--loader', './tests/tsx-loader.mjs', '--loader', './tests/controlled-fiber-loader.mjs', '--test', 'tests/camera-lifecycle.test.mjs']),
    ('selected-panel', ['node', '--test', 'tests/selected-panel.test.mjs']),
    ('catalogs', [sys.executable, str(proof / 'catalogs.py'), str(root)]),
]
def run(item):
    name, command = item
    start = time.monotonic()
    result = subprocess.run(command, cwd=package, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
    (proof / f'{name}.log').write_text(result.stdout)
    return {'name': name, 'command': command, 'cwd': str(package), 'exit_code': result.returncode, 'elapsed_s': time.monotonic() - start,
            'log': f'{name}.log', 'log_sha256': hashlib.sha256(result.stdout.encode()).hexdigest()}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(run, commands))
(proof / 'execution-results.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
