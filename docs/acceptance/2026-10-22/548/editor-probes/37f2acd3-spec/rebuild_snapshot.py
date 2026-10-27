from pathlib import Path
import subprocess,json,hashlib
p=Path(__file__).resolve().parent;m=json.loads((p/'archive_manifest.json').read_text());repo=Path(m['repo'])
for item in m['files']:
 raw=subprocess.check_output(['git','cat-file','blob',m['sha']+':'+item['path']],cwd=repo)
 assert hashlib.sha256(raw).hexdigest()==item['sha256']
 dest=p/item['path'];dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():assert dest.read_bytes()==raw, 'Refusing to overwrite changed file: '+str(dest)
 else:dest.write_bytes(raw)
deps=p/'apps/planner/node_modules'
if not deps.exists():deps.symlink_to(repo/'apps/planner/node_modules',target_is_directory=True)
print('Fixed minimal source restored',m['sha'])
