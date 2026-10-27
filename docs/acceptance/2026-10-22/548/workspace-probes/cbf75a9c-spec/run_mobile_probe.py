from pathlib import Path
import hashlib,json,subprocess
r=Path(__file__).resolve().parent
manifest=json.loads((r/'archive_manifest.json').read_text())
prefix=r/manifest['prior_probe']['path']
original=prefix.read_bytes()
if hashlib.sha256(original).hexdigest()!=manifest['prior_probe']['sha256']:
    raise RuntimeError('Prior563 probe has changed')
suffix=(r/'mobile-probe-additions.mjs').read_bytes()
generated=prefix.with_name('composed-mobile-probe.mjs')
generated.write_bytes(original+b'\n'+suffix)
cmd=['node','--no-warnings=ExperimentalWarning','--loader','./tests/tsx-loader.mjs','--test','tests/composed-mobile-probe.mjs']
result=subprocess.run(cmd,cwd=r/'apps/planner',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(r/'mobile-probe.log').write_text(result.stdout)
(r/'mobile-probe-run.json').write_text(json.dumps({'command':cmd,'cwd':'apps/planner','exit_code':result.returncode,'unchanged_prior_probe_sha256':hashlib.sha256(original).hexdigest(),'appended_probe_sha256':hashlib.sha256(suffix).hexdigest(),'generated_path':generated.relative_to(r).as_posix(),'generated_sha256':hashlib.sha256(generated.read_bytes()).hexdigest()},indent=2)+'\n')
print(result.stdout)
raise SystemExit(result.returncode)
