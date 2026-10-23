from pathlib import Path
import subprocess, json, os, shutil, datetime
from concurrent.futures import ThreadPoolExecutor
proof=Path(__file__).resolve().parent
meta=json.loads((proof/'snapshot-manifest.json').read_text());root=Path(meta['temporary_root'])
shutil.copy2(proof/'probe_import_boundary.py',root/'services/engine/tests/planning/standards_import_boundary_probe.py')
shutil.copy2(proof/'probe_browser_boundary.mjs',root/'apps/planner/src/domain/standards_browser_boundary_probe.mjs')
python=meta['dependencies']['python']
jobs=[
('backend-fixed',[python,'-m','pytest','tests/planning/test_geographic.py','tests/planning/test_geometry_import.py','tests/planning/test_private_http.py','-q','--basetemp='+str(root/'pytest-runtime')],root/'services/engine'),
('independent-import',[python,'-m','pytest','tests/planning/standards_import_boundary_probe.py','-q','--basetemp='+str(root/'probe-runtime')],root/'services/engine'),
('frontend-fixed',['node','--test','src/domain/geographic.test.ts','src/domain/geometryImports.test.ts'],root/'apps/planner'),
('independent-browser',['node','--test','src/domain/standards_browser_boundary_probe.mjs'],root/'apps/planner'),
('editor-fixed',['node','--no-warnings=ExperimentalWarning','--loader','./tests/tsx-loader.mjs','--test','tests/design-editor.test.mjs'],root/'apps/planner')]
def run(job):
 name,args,cwd=job
 env=os.environ.copy();env['PYTHONPATH']=str(root/'services/engine/src')
 result=subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (proof/f'{name}.log').write_text(result.stdout)
 return {'name':name,'command':args,'cwd':str(cwd),'exit_code':result.returncode,'log':f'{name}.log','summary':result.stdout[-800:]}
with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,jobs))
# Probe source is not an application module; remove only the exact copied review file
# before checking the fixed published source manifest.
(root/'apps/planner/src/domain/standards_browser_boundary_probe.mjs').unlink()
results.append(run(('build-fixed',['npm','run','build:check'],root/'apps/planner')))
(proof/'check-results.json').write_text(json.dumps({'fixed_sha':meta['fixed_sha'],'run_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':results},indent=2)+'\n')
print(json.dumps(results,indent=2))
