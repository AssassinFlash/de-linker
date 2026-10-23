"""Owned p548 only: actual composed HTTP -> managed process -> frozen energy.

Run with the existing engine environment. No credentials are printed or stored;
this is a synthetic private-service proof, not a customer UI acceptance.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

from linker_engine.planning.csv_mapping import CsvMapping

ROOT = Path(__file__).resolve().parents[5]
INSTANCE = Path('/Users/chesterjohn/de-linker-local/p548')
EVIDENCE = Path(__file__).resolve().parent
assert ROOT.name == 'unified-planner-548'
WP = [
    '/opt/homebrew/opt/php@8.3/bin/php', '-c', str(INSTANCE / 'php.ini'),
    '/opt/homebrew/bin/wp', '--path=' + str(INSTANCE / 'wordpress'),
]
TOKEN = subprocess.run(
    [*WP, 'config', 'get', 'LINKER_GENIE_SERVICE_TOKEN', '--type=constant'],
    check=True, text=True, capture_output=True,
).stdout.strip()
assert TOKEN
HEADERS = {
    'Content-Type': 'application/json',
    'X-Linker-Service-Token': TOKEN,
    'X-Linker-Planner-Principal-Kind': 'user',
    'X-Linker-Planner-Principal-Subject': 'synthetic:548-managed-worker',
}
PREFIX = 'worker-proof-' + uuid4().hex
REPLIES = []


def post(path: str, body: dict, expected: int = 200) -> dict:
    request = urllib.request.Request(
        'http://127.0.0.1:9348/planning' + path,
        data=json.dumps({'schema_version': 1, **body}).encode(), headers=HEADERS,
    )
    try:
        reply = urllib.request.urlopen(request, timeout=20)
    except urllib.error.HTTPError as error:
        reply = error
    with reply:
        raw = reply.read()
        assert reply.status == expected, (path, reply.status, raw.decode())
        assert reply.headers['cache-control'] == 'no-store, private'
        value = json.loads(raw)
        REPLIES.append({'path': path, 'status': reply.status, 'body': value})
        return value


def control(operation: str) -> dict:
    command = subprocess.run(
        [sys.executable, '-m', 'linker_engine.planning.worker_host', 'control', operation],
        env={'PATH': os.environ.get('PATH', os.defpath),
             'LINKER_PLANNER_CONFIG': str(INSTANCE / 'planner/runtime.json')},
        check=True, capture_output=True, text=True,
    )
    return json.loads(command.stdout)


def ready_identity() -> dict:
    ready = json.loads((INSTANCE / 'run/planner-worker.ready.json').read_bytes())
    os.kill(ready['pid'], 0)
    return ready


def main() -> None:
    before = json.loads((EVIDENCE / 'before.json').read_bytes())
    version = post('/version', {})
    ready = ready_identity()
    for key in ('runtime_sha256', 'execution_key', 'storage_binding'):
        assert ready[key] == version[key]
    assert control('status')['draining'] is False
    project = post('/projects/create', {
        'title': 'Managed worker · synthetic two-hour analytic acceptance',
        'inputs': {}, 'key': PREFIX + '-create',
    })
    project_id = project['id']
    selected = {}
    for role, powers in (('gross_load', (2, 2)), ('pv_available_ac', (4, 0)), ('aux_ac', (0, 0))):
        csv = f'time,power\n2024-03-30T23:00:00Z,{powers[0]}\n2024-03-31T00:00:00Z,{powers[1]}\n'.encode()
        asset = post('/profiles/csv', {
            'project_id': project_id, 'content_base64': base64.b64encode(csv).decode(),
            'mapping': CsvMapping('time', 'power', role, 'interval_average_kw', 'start',
                                  'Europe/Berlin', 'synthetic', 3600, ',', '.').document(),
            'source_label': 'Original synthetic analytic fixture; no actual site/weather',
            'rights_note': 'Created for owned p548 acceptance; retain and derive permitted',
            'key': PREFIX + '-' + role,
        })
        selected[role] = asset['id']
    battery = post('/battery/scenario', {
        'project_id': project_id, 'key': PREFIX + '-battery',
        'source_note': 'Explicit analytic scenario; no manufacturer or SKU approval',
        'parameters': {
            'schema_version': 1, 'model': 'constant_window_single_ac_bus_v1',
            'parameter_basis': 'explicit_scenario', 'usable_window_kwh': 5,
            'charge_ac_kw': 5, 'discharge_ac_kw': 5, 'eta_charge': 0.9,
            'eta_discharge': 0.9, 'internal_aux_kw': 0, 'standing_loss_rate_per_hour': 0,
        },
    })
    saved = post('/projects/revise', {
        'project_id': project_id, 'expected_revision': 1, 'key': PREFIX + '-scenario',
        'inputs': {'energy_replay': {
            'schema_version': 1, 'gross_load_asset_id': selected['gross_load'],
            'critical_load_asset_id': None, 'pv_available_asset_id': selected['pv_available_ac'],
            'aux_ac_asset_id': selected['aux_ac'], 'battery_parameters_asset_id': battery['id'],
            'initial_inventory': {'pv_kwh': 0, 'grid_kwh': 0, 'initial_unknown_kwh': 0,
                                  'basis': 'synthetic_fixture', 'source_note': 'Explicit empty initial state'},
            'schedule': [{'start_utc': '2024-03-30T23:00:00Z', 'end_utc': '2024-03-31T01:00:00Z',
                          'mode': 'connected', 'reserve_kwh': 0, 'import_cap_kw': None,
                          'export_cap_kw': 0, 'pv_enabled': True, 'allow_grid_charge': False}],
            'controller': 'self_consumption_with_reserve_v1', 'terminal_min_kwh': 0,
        }},
    })
    intent = {'project_id': project_id, 'expected_revision': 2, 'key': PREFIX + '-calculate'}
    queued = post('/runs/energy', intent)
    assert queued['state'] in ('queued', 'running', 'succeeded')
    assert queued['revision'] == 2
    deadline = time.monotonic() + 20
    while True:
        finished = post('/runs/read', {'run_id': queued['id']})
        if finished['state'] in ('succeeded', 'failed', 'cancelled'):
            break
        assert time.monotonic() < deadline, 'actual managed job did not finish'
        time.sleep(0.05)
    assert finished['state'] == 'succeeded', finished
    result = finished['result']
    assert result['input_sha256'] == saved['input_sha256']
    for key, expected in {'gross_load_kwh': 4, 'solar_load_kwh': 3.62, 'grid_import_kwh': 0.38}.items():
        assert math.isclose(result['metrics'][key], expected, abs_tol=1e-7)
    assert result['equipment_release']['status'] == 'not_assessed'
    assert post('/runs/energy', intent)['id'] == queued['id']
    drain = control('drain')
    assert drain['pending'] == 0 and drain['draining'] is True
    assert post('/runs/energy', intent)['result_sha256'] == finished['result_sha256']
    refusal = post('/runs/energy', {**intent, 'key': PREFIX + '-refused'}, expected=503)
    assert refusal['error']['code'] == 'service_draining'
    # Owned runner must itself verify both identities, start the worker and resume.
    restart = subprocess.run(
        ['just', 'serve', 'p548', '--service', 'engine'], cwd=ROOT,
        check=True, text=True, capture_output=True,
    )
    (EVIDENCE / 'restart.txt').write_text(restart.stdout + restart.stderr)
    ready_after = ready_identity()
    assert ready_after['generation'] != ready['generation']
    assert ready_after['pid'] != ready['pid']
    version_after = post('/version', {})
    for key in ('runtime_sha256', 'execution_key', 'storage_binding'):
        assert ready_after[key] == ready[key] == version_after[key]
    assert control('status')['draining'] is False
    assert post('/runs/energy', intent)['result_sha256'] == finished['result_sha256']
    with sqlite3.connect('file:'+str(INSTANCE/'planner/workspace/workspace.sqlite')+'?mode=ro',uri=True) as db:
        for project_id_before, revision_before, title_before in before['projects']:
            assert db.execute('select revision,title from projects where id=?',(project_id_before,)).fetchone() == (revision_before,title_before)
        for project_id_before, number, sha in before['revisions']:
            assert db.execute('select input_sha256 from revisions where project_id=? and number=?',(project_id_before,number)).fetchone()[0] == sha
        state = db.execute('select state,attempt,worker,output_sha256 from jobs where run_id=?',(queued['id'],)).fetchone()
        assert state[:3] == ('succeeded',1,'local-p548')
        assert state[3] == finished['result_sha256']
    assert {n:(INSTANCE/'run'/n).read_text() for n in before['preserved_process_records']} == before['preserved_process_records']
    assert hashlib.sha256((INSTANCE/'planner/runtime.json').read_bytes()).hexdigest() == before['runtime_config_sha256']
    (EVIDENCE / 'http.json').write_text(json.dumps({
        'source_pin': subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip(),
        'kind':'synthetic private-service HTTP and actual managed process; no customer UI or production claim',
        'project_id': project_id, 'run_id': queued['id'], 'queued': queued, 'finished': finished,
        'version_before': version, 'version_after': version_after,
        'ready_before': ready, 'ready_after': ready_after,
        'drain': drain, 'drain_refusal': refusal, 'job_row': state,
        'preserved_projects': len(before['projects']), 'preserved_revisions': len(before['revisions']),
        'genie_php_records_unchanged': True, 'runtime_config_unchanged': True,
        'replies': REPLIES,
    },indent=2)+'\n')
    print(json.dumps({'run_id':queued['id'],'state':finished['state'],'metrics':result['metrics'],
                      'attempt':state[1],'worker':state[2],'preserved_projects':len(before['projects']),
                      'preserved_revisions':len(before['revisions']),'worker_generation_changed':True}))


if __name__ == '__main__':
    main()
