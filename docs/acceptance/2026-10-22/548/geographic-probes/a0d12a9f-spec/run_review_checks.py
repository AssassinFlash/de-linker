from pathlib import Path
import json,os,subprocess
ROOT=Path(__file__).resolve().parent
python=ROOT/'services/engine/.venv/bin/python'
checks=[('target-py18',[str(python),'-m','pytest','-q','-p','no:cacheprovider','tests/planning/test_geographic.py','tests/planning/test_geometry_import.py'],ROOT/'services/engine',0),('target-ts6',['node','--test','src/domain/geographic.test.ts','src/domain/geometryImports.test.ts'],ROOT/'apps/planner',0),('counterexamples-py4',[str(python),'-m','pytest','-q','-p','no:cacheprovider','test_spec_geographic_counterexamples.py'],ROOT,1),('counterexample-browser-plane',['node','--test','probe_plane.test.mjs'],ROOT,1)]
rows=[];env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'services/engine/src')
for name,cmd,cwd,expected in checks:
 r=subprocess.run(cmd,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (ROOT/(name+'.log')).write_text(r.stdout);rows.append({'name':name,'command':cmd,'cwd':str(cwd),'returncode':r.returncode,'expected_on_a0_fixed':expected});assert r.returncode==expected,(name,r.stdout)
(ROOT/'check_runs.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
