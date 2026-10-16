"""Minimal Apify REST helper; the token comes from the environment and is never printed.

Usage:
  python3 -I apify.py me [TOKENVAR]
  python3 -I apify.py start <actor> <input.json> [TOKENVAR]          -> prints run id
  python3 -I apify.py status <runId> [TOKENVAR]                       -> prints status + dataset id
  python3 -I apify.py items <datasetId> <out.json> [TOKENVAR]         -> writes items
  python3 -I apify.py sync <actor> <input.json> <out.json> [TOKENVAR] -> run-sync-get-dataset-items
"""

import datetime
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

API = "https://api.apify.com/v2"


def call(method: str, path: str, token_var: str, body: bytes | None = None, timeout: int = 120) -> tuple[int, bytes]:
    token = os.environ.get(token_var, "")
    if not token:
        raise SystemExit(f"{token_var} missing")
    req = urllib.request.Request(API + path, data=body, method=method, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def main() -> None:
    cmd = sys.argv[1]
    if cmd == "me":
        var = sys.argv[2] if len(sys.argv) > 2 else "APIFY_TOKEN"
        status, raw = call("GET", "/users/me", var)
        data = json.loads(raw).get("data", {}) if status == 200 else {}
        print(status, data.get("username"), data.get("plan", {}).get("id") if isinstance(data.get("plan"), dict) else data.get("plan"))
        if status != 200:
            print(raw.decode()[:500])
    elif cmd == "start":
        actor, inp = sys.argv[2], sys.argv[3]
        var = sys.argv[4] if len(sys.argv) > 4 else "APIFY_TOKEN"
        status, raw = call("POST", f"/acts/{actor}/runs", var, pathlib.Path(inp).read_bytes())
        data = json.loads(raw)
        if status >= 300:
            print(status, raw.decode()[:800])
            return
        run = data["data"]
        print(run["id"], run["status"], run["defaultDatasetId"], run["startedAt"])
    elif cmd == "status":
        run_id = sys.argv[2]
        var = sys.argv[3] if len(sys.argv) > 3 else "APIFY_TOKEN"
        status, raw = call("GET", f"/actor-runs/{run_id}", var)
        run = json.loads(raw)["data"]
        print(run["status"], run["defaultDatasetId"], run.get("startedAt"), run.get("finishedAt"), run.get("statusMessage"))
    elif cmd == "items":
        ds, out = sys.argv[2], sys.argv[3]
        var = sys.argv[4] if len(sys.argv) > 4 else "APIFY_TOKEN"
        status, raw = call("GET", f"/datasets/{ds}/items?format=json&clean=true", var, timeout=300)
        pathlib.Path(out).write_bytes(raw)
        items = json.loads(raw)
        print(status, len(items))
    elif cmd == "sync":
        actor, inp, out = sys.argv[2], sys.argv[3], sys.argv[4]
        var = sys.argv[5] if len(sys.argv) > 5 else "APIFY_TOKEN"
        started = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        status, raw = call("POST", f"/acts/{actor}/run-sync-get-dataset-items?timeout=280", var, pathlib.Path(inp).read_bytes(), timeout=300)
        pathlib.Path(out).write_bytes(raw)
        try:
            items = json.loads(raw)
            n = len(items) if isinstance(items, list) else "obj"
        except Exception:
            n = "unparsable"
        print(status, n, "started", started)
        if status >= 300:
            print(raw.decode()[:800])


main()
