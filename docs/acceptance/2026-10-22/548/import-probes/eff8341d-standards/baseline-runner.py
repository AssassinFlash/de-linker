from pathlib import Path
import json,subprocess
proof=Path(__file__).resolve().parent;meta=json.loads((proof/'snapshot-manifest.json').read_text());cwd=Path(meta['temporary_root'])/'apps/planner';results=[]
for name,args in [('fixed-client-suite',['npm','test']),('fixed-build-check',['npm','run','build:check'])]:
 result=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (proof/(name+'.log')).write_text(result.stdout)
 item={'name':name,'command':args,'cwd':str(cwd),'exit_code':result.returncode,'log':name+'.log','summary':result.stdout[-1800:]};results.append(item);(proof/'execution-results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(item),flush=True)
