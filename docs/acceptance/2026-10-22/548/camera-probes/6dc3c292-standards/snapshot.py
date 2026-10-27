#!/usr/bin/env python3
"""One bounded, reproducible fixed-source snapshot. No Git worktree or server."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

REPO = Path('/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548')
EVIDENCE = Path(__file__).resolve().parent
SHA = '6dc3c292079ec4f654113ecd3e11b631906e6c04'
BASE = 'eff8341d5a0eaf24999f42854da6339032c65c9c'

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])

manifest_path = EVIDENCE / 'snapshot-manifest.json'
if manifest_path.exists():
    raise SystemExit('Preserve the original manifest. Reproduce from copied scripts in a fresh owned evidence directory.')
now = dt.datetime.now(dt.timezone.utc)
root = Path(tempfile.mkdtemp(prefix='camera-standards-6dc3-'))
prefixes = ('apps/planner/src/', 'apps/planner/tests/', 'apps/planner/bin/',
            'fixtures/planning/', 'plugins/linker-tools/build/planner/')
extras = {'apps/planner/package.json', 'apps/planner/package-lock.json',
          'apps/planner/tsconfig.json', 'apps/planner/vite.config.ts',
          'AGENTS.md', 'CONTEXT.md', 'docs/adr/0002-isolated-planner-runtime.md',
          'docs/specs/548-roof-import-workflow.md',
          'plugins/linker-commerce/content/windpress/planner.css',
          'plugins/linker-commerce/content/windpress/chrome.css',
          'plugins/linker-tools/languages/linker-tools-de_DE_formal.po',
          'plugins/linker-tools/languages/linker-tools-de_DE_formal.mo',
          'plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json',
          'docs/acceptance/2026-10-22/548/camera-copy-final.json',
          'docs/acceptance/2026-10-22/548/camera-copy-feedback.json'}
files = []
for name in git('ls-tree', '-r', '--name-only', SHA).decode().splitlines():
    if name not in extras and not name.startswith(prefixes):
        continue
    blob = git('show', f'{SHA}:{name}')
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)
    files.append({'path': name, 'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()})
deps = REPO / 'apps/planner/node_modules'
assert deps.is_dir()
(root / 'apps/planner/node_modules').symlink_to(deps, target_is_directory=True)
manifest = {'sha': SHA, 'base': BASE, 'owner': '/root/geographic_standards_e138',
            'purpose': 'Camera Standards fixed-source lifecycle and catalog probes; no native/GPU acceptance',
            'created_utc': now.isoformat(), 'expires_utc': (now + dt.timedelta(hours=2)).isoformat(),
            'reclaim': 'Immediately after retaining unique scripts, logs and SHA/readback evidence',
            'temp_root': str(root), 'dependency_symlink': str(deps),
            'free_bytes_before': shutil.disk_usage(root).free, 'files': files}
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'temp_root': str(root), 'files': len(files), 'bytes': sum(f['bytes'] for f in files)}, indent=2))
