"""List this session's Apify runs (all three tokens) as provenance; prints JSON, no token.

Usage: python3 -I runs.py <out.json>
"""

import json
import os
import pathlib
import sys
import urllib.request

API = "https://api.apify.com/v2"
rows = []
for var in ("APIFY_TOKEN", "APIFY_TOKEN_PREV", "APIFY_TOKEN_ALT"):
    req = urllib.request.Request(API + "/actor-runs?desc=1&limit=10", headers={"Authorization": "Bearer " + os.environ[var]})
    with urllib.request.urlopen(req, timeout=60) as resp:
        items = json.loads(resp.read())["data"]["items"]
    for run in items:
        if run.get("startedAt", "") >= "2026-10-16T17:10":
            detail_req = urllib.request.Request(API + f"/actor-runs/{run['id']}", headers={"Authorization": "Bearer " + os.environ[var]})
            with urllib.request.urlopen(detail_req, timeout=60) as resp:
                detail = json.loads(resp.read())["data"]
            rows.append({
                "token_variable": var,
                "actor_id": run.get("actId"),
                "run_id": run["id"],
                "status": run.get("status"),
                "started_at_utc": run.get("startedAt"),
                "finished_at_utc": run.get("finishedAt"),
                "dataset_id": run.get("defaultDatasetId"),
                "status_message": detail.get("statusMessage"),
            })
rows.sort(key=lambda r: r["started_at_utc"])
pathlib.Path(sys.argv[1]).write_text(json.dumps(rows, indent=1) + "\n")
for r in rows:
    print(r["started_at_utc"], r["token_variable"], r["run_id"], r["status"], r["dataset_id"])
