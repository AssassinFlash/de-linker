#!/usr/bin/env python3
"""Read the fixed published catalogs, not the parent's regenerated worktree MO."""
import ast
import gettext
import hashlib
import io
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
directory = root / 'plugins/linker-tools/languages'
final = json.loads((root / 'docs/acceptance/2026-10-22/548/camera-copy-final.json').read_text())
mo_bytes = (directory / 'linker-tools-de_DE_formal.mo').read_bytes()
mo = gettext.GNUTranslations(io.BytesIO(mo_bytes))
wp = json.loads((directory / 'linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json').read_text())
messages = wp['locale_data']['messages']
po = {}; key = value = ''; field = None
for line in (directory / 'linker-tools-de_DE_formal.po').read_text().splitlines() + ['']:
    if line.startswith('msgid '): key = ast.literal_eval(line[6:]); field = 'key'
    elif line.startswith('msgstr '): value = ast.literal_eval(line[7:]); field = 'value'
    elif line.startswith('"'):
        if field == 'key': key += ast.literal_eval(line)
        elif field == 'value': value += ast.literal_eval(line)
    elif not line.strip():
        if key: po[key] = value
        key = value = ''; field = None
source = (root / 'apps/planner/src/components/design/SceneViewport.tsx').read_text()
manifest = json.loads((root / 'plugins/linker-tools/build/planner/vite-manifest.json').read_text())
chunk = (root / 'plugins/linker-tools/build/planner' / manifest['src/components/design/SceneViewport.tsx']['file']).read_text()
checks = []
for pair in final:
    key, value = pair['en'], pair['de']
    checks.append({'id': pair['id'], 'source': key in source, 'emitted': key in chunk,
                   'po': po.get(key) == value, 'wp_json': messages.get(key) == [value],
                   'gnu_mo': key in mo._catalog and mo.gettext(key) == value,
                   'actual_gnu': mo.gettext(key), 'expected_de': value})
print(json.dumps({'mo_sha256': hashlib.sha256(mo_bytes).hexdigest(), 'checks': checks}, ensure_ascii=False, indent=2))
assert all(all(item[k] for k in ('source', 'emitted', 'po', 'wp_json', 'gnu_mo')) for item in checks), 'Approved camera copy must reach source, emitted module, PO, WP JSON and GNU MO'
