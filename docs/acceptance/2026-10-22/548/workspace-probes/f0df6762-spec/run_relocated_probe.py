from pathlib import Path
import json,hashlib,subprocess
r=Path(__file__).resolve().parent;m=json.loads((r/'archive_manifest.json').read_text())
for entry in m['prior_review_files']:
    if hashlib.sha256((r/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
        raise RuntimeError('Prior fixed probe changed')
parts=[r/'apps/planner/tests/independent-journal-probe.mjs',r/'mobile-probe-additions.mjs',r/'refusal-probe-additions.mjs',r/'relocated-probe-additions.mjs']
generated=r/'apps/planner/tests/composed-relocated-probe.mjs'
generated.write_bytes(b'\n'.join(p.read_bytes() for p in parts))
cmd=['node','--no-warnings=ExperimentalWarning','--loader','./tests/tsx-loader.mjs','--test','--test-name-pattern=^relocated','tests/composed-relocated-probe.mjs']
p=subprocess.run(cmd,cwd=r/'apps/planner',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(r/'relocated-probe.log').write_text(p.stdout)
(r/'relocated-probe-run.json').write_text(json.dumps({'command':cmd,'cwd':'apps/planner','exit_code':p.returncode,'prior_files_unchanged':True,'new_additions_sha256':hashlib.sha256(parts[-1].read_bytes()).hexdigest(),'generated_path':generated.relative_to(r).as_posix(),'generated_sha256':hashlib.sha256(generated.read_bytes()).hexdigest()},indent=2)+'\n')
print(p.stdout);raise SystemExit(p.returncode)
