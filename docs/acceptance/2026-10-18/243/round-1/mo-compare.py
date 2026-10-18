"""Compare a branch's compiled catalogs with main's: lost, changed and added messages.

    python3 mo-compare.py <main.mo> <branch.mo>

Reads both with msgunfmt (gettext). Prints the counts and the added msgids.
"""

import subprocess
import sys


def messages(path: str) -> dict[str, str]:
    text = subprocess.run(
        ["msgunfmt", "--no-wrap", path], check=True, capture_output=True, text=True
    ).stdout
    found: dict[str, str] = {}
    msgid = None
    for line in text.splitlines():
        if line.startswith("msgid "):
            msgid = line[6:]
        elif line.startswith("msgstr ") and msgid is not None:
            found[msgid] = line[7:]
            msgid = None
    return found


main, branch = messages(sys.argv[1]), messages(sys.argv[2])
lost = [k for k in main if k not in branch]
changed = [k for k in main if k in branch and main[k] != branch[k]]
added = [k for k in branch if k not in main]
print(f"main {len(main)} · branch {len(branch)} · lost {len(lost)} · changed {len(changed)} · added {len(added)}")
for k in lost:
    print("LOST", k)
for k in changed:
    print("CHANGED", k)
for k in added:
    print("added", k)
