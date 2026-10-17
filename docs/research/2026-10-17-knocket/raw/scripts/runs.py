"""List today's Apify runs for each token variable (ids, actor, timings, status). Tokens are never printed.

Usage: python3 -I runs.py <since_iso> <out.json> TOKENVAR...
"""

import json
import os
import sys
import urllib.request

since, out, token_vars = sys.argv[1], sys.argv[2], sys.argv[3:]
rows = []
for var in token_vars:
    token = os.environ.get(var, "")
    req = urllib.request.Request("https://api.apify.com/v2/actor-runs?desc=1&limit=40", headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as resp:
        items = json.load(resp)["data"]["items"]
    for run in items:
        if run["startedAt"] < since:
            continue
        actor_req = urllib.request.Request(f"https://api.apify.com/v2/acts/{run['actId']}", headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(actor_req, timeout=60) as resp:
            act = json.load(resp)["data"]
        rows.append({"token_var": var, "run_id": run["id"], "actor": f"{act['username']}/{act['name']}", "status": run["status"], "startedAt": run["startedAt"], "finishedAt": run.get("finishedAt"), "dataset": run["defaultDatasetId"]})
rows.sort(key=lambda r: r["startedAt"])
with open(out, "w") as fh:
    json.dump(rows, fh, indent=1)
for r in rows:
    print(r["startedAt"], r["actor"], r["run_id"], r["status"])
