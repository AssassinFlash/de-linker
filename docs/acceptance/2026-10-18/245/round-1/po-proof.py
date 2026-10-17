import ast
import json
import re
import subprocess
from pathlib import Path

path = Path('plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po')
base = subprocess.check_output(['git', 'show', '61253564:' + str(path)], text=True)

def read(text):
    entries = {}
    record = {}
    field = None
    def flush():
        if record.get('msgid'):
            key = (record.get('msgctxt', ''), record['msgid'], record.get('msgid_plural', ''))
            entries[key] = {k: v for k, v in record.items() if k.startswith('msgstr')}
    for raw in text.splitlines() + ['']:
        line = raw.removeprefix('#~ ')
        if not line:
            flush()
            record = {}
            field = None
        elif line.startswith('#'):
            continue
        elif line.startswith('"'):
            if field:
                record[field] += ast.literal_eval(line)
        else:
            match = re.match(r'(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(".*")$', line)
            if match:
                field = match[1]
                record[field] = ast.literal_eval(match[2])
    return entries

before = read(base)
after = read(path.read_text())
changes = []
for key, value in before.items():
    if key not in after or value != after[key]:
        changes.append({'msgid': key[1], 'before': value, 'after': after.get(key)})
allowed = {
    'You are signed in as %s (customer account).': 'Sie sind mit Ihrem Kundenkonto %s angemeldet.',
    'Sign out and sign in as staff': 'Abmelden und mit einem Mitarbeiterkonto anmelden',
}
passed = len(changes) == 2 and all(c['msgid'] in allowed and c['after'] == {'msgstr': allowed[c['msgid']]} for c in changes)
report = {'baseline': '61253564', 'command': 'wp i18n make-pot, then msgmerge --update --no-fuzzy-matching; msgfmt --check', 'existing_entries': len(before), 'unchanged_existing_entries': len(before) - len(changes), 'changes': changes, 'unexpected_changes': [c for c in changes if c['msgid'] not in allowed], 'pass': passed}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if passed else 1)
