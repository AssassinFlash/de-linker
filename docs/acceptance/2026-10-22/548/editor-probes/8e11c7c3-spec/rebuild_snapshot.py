#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).resolve().parent;m=json.loads((root/'archive_manifest.json').read_text())
for e in m['entries']:
    b=subprocess.check_output(['git','cat-file','blob',m['target']+':'+e['path']],cwd=m['repository'])
    if hashlib.sha256(b).hexdigest()!=e['sha256']:raise RuntimeError('Fixed blob mismatch')
    p=root/e['path']
    if p.exists()and p.read_bytes()!=b:raise RuntimeError('Preserving changed file: '+e['path'])
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
l=m['dependency_symlink'];p=root/l['path']
if not p.exists()and not p.is_symlink():p.parent.mkdir(parents=True,exist_ok=True);p.symlink_to(l['target'],target_is_directory=True)
print('Rebuilt',len(m['entries']),'files at',root)
