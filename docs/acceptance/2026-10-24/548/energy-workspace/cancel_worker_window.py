"""Owned-local operator fixture: bounded scheduler hold for a real UI cancel.

No customer pause feature, queue/DB state injection or service-policy change.
The verified p548 worker is always resumed after stdin or a 45-second failsafe.
"""
import hashlib
import json
import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

instance = Path('/Users/chesterjohn/de-linker-local/p548')
evidence = Path(__file__).resolve().parent
ready_raw = (instance/'run/planner-worker.ready.json').read_bytes()
ready = json.loads(ready_raw)
assert ready['name'] == 'local-p548'
pid = ready['pid']


def identity():
    return subprocess.run(['ps', '-p', str(pid), '-o', 'lstart=,command='],
                          check=True, capture_output=True, text=True).stdout.strip()


original = identity()
assert 'linker_engine.planning.worker_host serve' in original
for field in ('runtime_sha256', 'execution_key', 'storage_binding', 'generation'):
    assert ready[field] in original
record = {'ready': ready, 'ready_sha256': hashlib.sha256(ready_raw).hexdigest(),
          'identity_sha256': hashlib.sha256(original.encode()).hexdigest(),
          'started_at': time.time(), 'maximum_hold_seconds': 45}
try:
    os.kill(pid, signal.SIGSTOP)
    record['stopped_status'] = subprocess.run(['ps', '-p', str(pid), '-o', 'stat='],
                                            check=True, capture_output=True, text=True).stdout.strip()
    assert record['stopped_status'].startswith('T')
    print(json.dumps({'owned_worker_held': pid, 'failsafe_seconds': 45}), flush=True)
    if select.select([sys.stdin], [], [], 45)[0]:
        sys.stdin.readline()
finally:
    assert identity() == original, 'Do not signal a reused or replaced process'
    os.kill(pid, signal.SIGCONT)
    record['resumed_at'] = time.time()
    record['resumed_status'] = subprocess.run(['ps', '-p', str(pid), '-o', 'stat='],
                                            check=True, capture_output=True, text=True).stdout.strip()
    assert not record['resumed_status'].startswith('T')
    (evidence/'worker-cancel-control.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({'owned_worker_resumed': pid}), flush=True)
