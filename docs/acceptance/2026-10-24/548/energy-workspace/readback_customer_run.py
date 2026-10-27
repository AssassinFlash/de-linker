"""Read only: reconcile a known native p548 customer run with HTTP/CAS/jobs.

This never creates projects, changes inputs or enqueues/cancels a calculation.
The local service credential is captured privately and never written to evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
INSTANCE = Path('/Users/chesterjohn/de-linker-local/p548')
EVIDENCE = Path(__file__).resolve().parent
PROJECT = '334e269920d540fe8573a66a1031e0be'
assert ROOT.name == 'unified-planner-548'


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('run')
    parser.add_argument('name')
    args = parser.parse_args()
    assert re.fullmatch('[a-f0-9]{32}', args.run)
    assert re.fullmatch('[a-z0-9-]+', args.name)
    wp = ['/opt/homebrew/opt/php@8.3/bin/php', '-c', str(INSTANCE/'php.ini'),
          '/opt/homebrew/bin/wp', '--path='+str(INSTANCE/'wordpress')]
    token = subprocess.run(
        [*wp, 'config', 'get', 'LINKER_GENIE_SERVICE_TOKEN', '--type=constant'],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert token

    def post(path: str, body: dict) -> dict:
        request = urllib.request.Request(
            'http://127.0.0.1:9348/planning/'+path,
            data=json.dumps({'schema_version': 1, **body}).encode(),
            headers={'Content-Type': 'application/json', 'X-Linker-Service-Token': token,
                     'X-Linker-Planner-Principal-Kind': 'user',
                     'X-Linker-Planner-Principal-Subject': 'wp:1:user:66'},
        )
        with urllib.request.urlopen(request, timeout=20) as reply:
            assert reply.status == 200
            assert reply.headers['cache-control'] == 'no-store, private'
            return json.load(reply)

    version = post('version', {})
    ready = json.loads((INSTANCE/'run/planner-worker.ready.json').read_bytes())
    os.kill(ready['pid'], 0)
    for name in ('runtime_sha256', 'execution_key', 'storage_binding'):
        assert version[name] == ready[name]
    run = post('runs/read', {'run_id': args.run})
    assert run['project_id'] == PROJECT
    project = post('projects/read', {'project_id': PROJECT, 'revision': run['revision']})
    assert project['input_sha256'] == run['manifest']['input_sha256']
    workspace = INSTANCE/'planner/workspace'

    def blob(sha: str) -> dict:
        raw = (workspace/'blobs'/sha[:2]/sha).read_bytes()
        assert digest(raw) == sha
        return json.loads(raw)

    with sqlite3.connect('file:'+str(workspace/'workspace.sqlite')+'?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        stored = dict(db.execute('select * from runs where id=?', (args.run,)).fetchone())
        job = dict(db.execute(
            'select id,state,attempt,worker,output_sha256,error_sha256 from jobs where run_id=?',
            (args.run,),
        ).fetchone())
        before = json.loads((EVIDENCE/'runtime-before.json').read_bytes())
        for original in before['projects']:
            current = db.execute(
                'select p.title,p.revision,r.input_sha256 from projects p join revisions r '
                'on p.id=r.project_id and p.revision=r.number where p.id=?',
                (original['id'],),
            ).fetchone()
            assert current and current['revision'] == original['revision']
            assert current['input_sha256'] == original['input_sha256']
            assert digest(current['title'].encode()) == original['title_sha256']
        added = [row[0] for row in db.execute('select id from projects')
                 if row[0] not in {p['id'] for p in before['projects']}]
        assert added == [PROJECT]
    assert stored['manifest_sha256'] == run['manifest_sha256']
    assert blob(run['manifest_sha256']) == run['manifest']
    output = {'source_pin': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                          check=True, capture_output=True, text=True).stdout.strip(),
              'project': project, 'run': run, 'job': job, 'version': version, 'ready': ready,
              'preserved_original_projects': len(before['projects']), 'new_projects': added}
    assert job['state'] == run['state']
    if run['result_sha256']:
        assert blob(run['result_sha256']) == run['result']
        assert job['output_sha256'] == run['result_sha256']
        result = run['result']
        trace_sha = result['dependencies']['energy_trace']
        output['trace'] = blob(trace_sha)
        if args.run in {'2c360c4679fe41cf8bd8f874036e58c4', '14dacb74cda2451a95d00df374532af8'}:
            assert job['attempt'] == 1 and job['worker'] == 'local-p548'
            metrics = result['metrics']
            for key, expected in {'gross_load_kwh': 4, 'solar_load_kwh': 3.62,
                                  'grid_import_kwh': .38, 'pv_direct_load_kwh': 2,
                                  'pv_battery_to_load_kwh': 1.62}.items():
                assert math.isclose(metrics[key], expected, rel_tol=0.0, abs_tol=1e-12)
            assert math.isclose(metrics['solar_autarky']['value'], .905,
                                rel_tol=0.0, abs_tol=1e-12)
            assert metrics['pv_input_self_use']['value'] == 1
            assert result['interval_count'] == 2
            assert result['equipment_release']['status'] == 'not_assessed'
            assert result['country_assessment']['status'] == 'not_assessed'
    if job['error_sha256']:
        output['stored_job_error'] = blob(job['error_sha256'])
    (EVIDENCE/(args.name+'.json')).write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps({'state': run['state'], 'revision': run['revision'],
                      'run_id': args.run, 'result_sha256': run['result_sha256'],
                      'preserved_original_projects': len(before['projects'])}))


if __name__ == '__main__':
    main()
