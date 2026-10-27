#!/usr/bin/env python3
"""Rebuild only the exact fixed files removed from this review evidence directory."""
from pathlib import Path
import subprocess, json, hashlib
root=Path(__file__).resolve().parent
manifest=json.loads((root/'archive_manifest.json').read_text())
repo=Path(manifest['repository'])
for entry in manifest['entries']:
    relative=entry['path']
    payload=subprocess.check_output(['git','cat-file','blob',manifest['target']+':'+relative],cwd=repo)
    if hashlib.sha256(payload).hexdigest()!=entry['sha256']:
        raise RuntimeError('Fixed blob hash mismatch: '+relative)
    dest=root/relative
    if dest.exists() and dest.read_bytes()!=payload:
        raise RuntimeError('Preserving modified local file: '+relative)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(payload)
link=manifest['dependency_symlink']
location=root/link['path']
if not location.exists() and not location.is_symlink():
    location.parent.mkdir(parents=True,exist_ok=True)
    location.symlink_to(link['target'],target_is_directory=True)
print('Rebuilt',len(manifest['entries']),'fixed files at',root)
