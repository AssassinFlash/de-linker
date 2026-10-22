"""Reproduce this investigation's Apify-only source collection.

APIFY_TOKEN is read from the environment or the existing user config. Never
persist credentials. This script only calls api.apify.com; source-page requests
are made by the selected Apify actor. Call with search|crawl and an input JSON.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent


def token() -> str:
    value = os.environ.get("APIFY_TOKEN")
    if value:
        return value
    config = Path.home() / ".config/terravolt-builder/apify.env"
    match = re.search(r"^(?:export\s+)?APIFY_TOKEN\s*=\s*(['\"]?)([^\s'\"]+)\1", config.read_text(), re.M)
    if not match:
        raise RuntimeError("APIFY_TOKEN unavailable in environment or existing config")
    return match.group(2)


def api(path: str, payload: dict | None = None) -> dict | list:
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        "https://api.apify.com/v2/" + path,
        data=data,
        headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=50) as response:
            return json.load(response)
    except HTTPError as exc:
        # API errors may include the URL but no credentials are ever in it.
        detail = exc.read().decode(errors="replace")[:1000]
        raise RuntimeError(f"Apify HTTP {exc.code}: {detail}") from None


def main() -> None:
    mode, input_path, name = sys.argv[1:]
    actor = "apify~google-search-scraper" if mode == "search" else "apify~website-content-crawler"
    payload = json.loads(Path(input_path).read_text())
    raw = BASE / "raw"
    raw.mkdir(exist_ok=True)
    (raw / f"{name}-input.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    run = api(f"acts/{actor}/runs", payload)["data"]
    run_id = run["id"]
    print(json.dumps({"actor": actor, "runId": run_id, "status": run["status"]}), flush=True)
    while run["status"] in {"READY", "RUNNING"}:
        time.sleep(3)
        run = api(f"actor-runs/{run_id}")["data"]
    metadata = {k: run.get(k) for k in ["id", "actId", "status", "startedAt", "finishedAt", "defaultDatasetId", "usageTotalUsd", "statusMessage"]}
    (raw / f"{name}-run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    if run["status"] != "SUCCEEDED":
        raise RuntimeError(json.dumps(metadata))
    items = api(f"datasets/{run['defaultDatasetId']}/items?clean=true&format=json")
    (raw / f"{name}-items.json").write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({**metadata, "items": len(items)}), flush=True)


if __name__ == "__main__":
    main()
