"""Rebuild the small fixed-source review graph after its disposable copy is reclaimed."""
from pathlib import Path
import subprocess, json, hashlib, tempfile, sys
proof=Path(__file__).resolve().parent
meta=json.loads((proof/'snapshot-manifest.json').read_text())
repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=proof,text=True).strip())
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(tempfile.mkdtemp(prefix='geographic-standards-e138-rebuild-'))
if root.exists() and any(root.iterdir()):raise SystemExit('destination must be empty')
root.mkdir(parents=True,exist_ok=True)
for entry in meta['files']:
 data=subprocess.check_output(['git','show',meta['fixed_sha']+':'+entry['path']],cwd=repo)
 if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise SystemExit('fixed source hash mismatch')
 path=root/entry['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
(root/'apps/planner/node_modules').symlink_to(meta['dependencies']['node_modules'],target_is_directory=True)
meta['temporary_root']=str(root)
(proof/'snapshot-manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
print(root)
