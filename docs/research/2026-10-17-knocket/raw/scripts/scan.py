"""Byte-compare every file under a directory against the Apify tokens (env) and the DeepSeek key
(local credential file). Prints only counts, never the secrets.

Usage: python3 -I scan.py <dir> <deepseek_env_file>
"""

import os
import pathlib
import re
import sys

root, ds_file = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
secrets = [os.environ.get(v, "") for v in ("APIFY_TOKEN", "APIFY_TOKEN_PREV", "APIFY_TOKEN_ALT")]
if ds_file.exists():
    for line in ds_file.read_text().splitlines():
        m = re.match(r"\s*(?:export\s+)?[A-Z_]*KEY[A-Z_]*\s*=\s*['\"]?([^'\"\s]+)", line)
        if m:
            secrets.append(m.group(1))
secrets = [s.encode() for s in secrets if len(s) >= 16]
hits = 0
files = [p for p in root.rglob("*") if p.is_file()]
for p in files:
    data = p.read_bytes()
    for s in secrets:
        if s in data:
            hits += 1
            print("HIT in", p)
print(f"secrets checked: {len(secrets)}, files: {len(files)}, hits: {hits}")
