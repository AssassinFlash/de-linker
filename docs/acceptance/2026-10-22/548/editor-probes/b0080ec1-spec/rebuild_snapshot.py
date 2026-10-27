#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).resolve().parent
manifest=json.loads((root/'archive_manifest.json').read_text())
for entry in manifest['entries']:
    rel=entry['path']
    payload=subprocess.check_output(['git','cat-file','blob',manifest['target']+':'+rel],cwd=manifest['repository'])
    if hashlib.sha256(payload).hexdigest()!=entry['sha256']:raise RuntimeError('Fixed blob mismatch: '+rel)
    p=root/rel
    if p.exists()and p.read_bytes()!=payload:raise RuntimeError('Preserving changed file: '+rel)
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(payload)
link=manifest['dependency_symlink'];p=root/link['path']
if not p.exists()and not p.is_symlink():p.parent.mkdir(parents=True,exist_ok=True);p.symlink_to(link['target'],target_is_directory=True)
print('Rebuilt',len(manifest['entries']),'fixed files at',root)
