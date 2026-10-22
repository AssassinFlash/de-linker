"""Collect primary-method evidence through Apify, never persisting credentials."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent


def apify_request(path: str, payload: dict | None = None):
    secret = os.environ.get("APIFY_TOKEN")
    if not secret:
        config = Path.home() / ".config/terravolt-builder/apify.env"
        match = re.search(r"^(?:export\s+)?APIFY_TOKEN\s*=\s*(['\"]?)([^\s'\"]+)\1", config.read_text(), re.M)
        if not match:
            raise RuntimeError("Apify credential is unavailable")
        secret = match[2]
    request = Request("https://api.apify.com/v2/" + path,
                      data=None if payload is None else json.dumps(payload).encode(),
                      headers={"Authorization": "Bearer " + secret, "Content-Type": "application/json"})
    with urlopen(request, timeout=50) as response:
        return json.load(response)


def main():
    name, mode, input_file = sys.argv[1:]
    payload = json.loads(Path(input_file).read_text())
    raw = BASE / "raw"
    raw.mkdir(exist_ok=True)
    (raw / (name + "-input.json")).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    actor = "apify~google-search-scraper" if mode == "search" else "apify~website-content-crawler"
    # Per-run memory adapts to the account's concurrent-memory ceiling;
    # this does not change account limits or purchase additional resources.
    suffix = "?memory=2048" if mode != "search" else ""
    run = apify_request("acts/" + actor + "/runs" + suffix, payload)["data"]
    print(json.dumps({"name": name, "runId": run["id"], "status": run["status"]}), flush=True)
    while run["status"] in ("READY", "RUNNING"):
        time.sleep(3)
        run = apify_request("actor-runs/" + run["id"])["data"]
    metadata = {key: run.get(key) for key in ("id", "status", "defaultDatasetId", "startedAt", "finishedAt", "usageTotalUsd", "statusMessage")}
    (raw / (name + "-run.json")).write_text(json.dumps(metadata, indent=2) + "\n")
    if run["status"] != "SUCCEEDED":
        raise RuntimeError("Apify run did not succeed: " + run["status"])
    items = apify_request("datasets/" + run["defaultDatasetId"] + "/items?clean=true&format=json")
    (raw / (name + "-items.json")).write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"name": name, "runId": run["id"], "datasetId": run["defaultDatasetId"], "items": len(items)}), flush=True)


if __name__ == "__main__":
    main()
