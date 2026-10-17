"""Re-collect the Apify runs of this dossier into raw-intl/ (slimmed).

Tokens come from the environment (APIFY_TOKEN_PREV / APIFY_TOKEN_ALT) and are never printed
or written. For every run: run metadata -> apify/runs.json; dataset items -> apify/<name>.json
(slimmed: no html/text duplicates, image links and signed CDN URLs removed); for crawler runs
one markdown file per page -> pages/<slug>.md with a source header (URL + load time UTC);
the run input -> apify/inputs/<name>.input.json.

Usage: python3 -I collect.py <raw-intl dir>
"""
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.apify.com/v2"
RUNS = [
    # (name, token var, run id)
    ("serp-en-retail", "APIFY_TOKEN_PREV", "wMiryS2Msj89wxsxS"),
    ("serp-en-b2b-ux", "APIFY_TOKEN_PREV", "nHX4krqE6orRQgckQ"),
    ("serp-de", "APIFY_TOKEN_PREV", "knr4azgOa2H5Yj4Ac"),
    ("wcc-known-1", "APIFY_TOKEN_PREV", "TrRwuJPIOXuAAY33r"),
    ("wcc-protected-residential", "APIFY_TOKEN_PREV", "6ep3kFtfDlq2qhpn0"),
    ("wcc-b1", "APIFY_TOKEN_PREV", "RprqhMkO9aiKCS8l1"),
    ("wcc-b3", "APIFY_TOKEN_PREV", "nhYEE2N8zACk3aduc"),
    ("wcc-b4-lists", "APIFY_TOKEN_PREV", "441FEIMGdGRPUOGLw"),
    ("serp-round2", "APIFY_TOKEN_ALT", "E1sNAhO4fHbn0XWme"),
    ("wcc-amazon-de-uk", "APIFY_TOKEN_ALT", "YpnX9oE6RPNjc2bk2"),
    ("widgets-1", "APIFY_TOKEN_ALT", "FKuKcGSqqiocOoheg"),
    ("serp-round3", "APIFY_TOKEN_ALT", "6cWvgsX21KLnfovkN"),
    ("wcc-b5", "APIFY_TOKEN_ALT", "OMFaxlpG6yfbQwyQN"),
    ("wcc-b6", "APIFY_TOKEN_PREV", "d19YtZUInid3VHh3l"),
    ("observe-eu-desktop", "APIFY_TOKEN_ALT", "ATaPSVjATuEW9qBlM"),
    ("observe-voelkner-mobile", "APIFY_TOKEN_PREV", "SkeeRx9DrKVHOo2pF"),
    ("observe-voelkner-desktop", "APIFY_TOKEN_PREV", "dzXoHxcufaFQGN6NR"),
] + [tuple(x) for x in json.loads(os.environ.get("EXTRA_RUNS", "[]"))]

SIGNED = re.compile(r"\S*(signature=|X-Amz-Signature|sig=|expires=)\S*")
IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")


def get(path: str, var: str) -> bytes:
    req = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + os.environ[var]})
    for attempt in range(5):
        try:
            return urllib.request.urlopen(req, timeout=300).read()
        except urllib.error.URLError:
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def clean_md(md: str) -> str:
    md = IMG.sub("", md)
    md = SIGNED.sub("<signed-url-removed>", md)
    return re.sub(r"\n{3,}", "\n\n", md)


def main() -> None:
    root = pathlib.Path(sys.argv[1])
    (root / "apify").mkdir(parents=True, exist_ok=True)
    (root / "pages").mkdir(parents=True, exist_ok=True)
    meta = []
    for name, var, run_id in RUNS:
        run = json.loads(get(f"/actor-runs/{run_id}", var))["data"]
        actor = json.loads(get(f"/acts/{run['actId']}", var))["data"]
        items = json.loads(get(f"/datasets/{run['defaultDatasetId']}/items?format=json&clean=true", var))
        (root / "apify" / "inputs").mkdir(exist_ok=True)
        run_input = get(f"/key-value-stores/{run['defaultKeyValueStoreId']}/records/INPUT", var)
        (root / "apify" / "inputs" / f"{name}.input.json").write_bytes(run_input)
        meta.append({"name": name, "runId": run_id, "actor": f"{actor['username']}/{actor['name']}",
                     "status": run["status"], "startedAt": run["startedAt"], "finishedAt": run["finishedAt"],
                     "items": len(items)})
        slim = []
        for it in items:
            it = {k: v for k, v in it.items() if k not in ("html", "text", "screenshotUrl", "debug")}
            if "markdown" in it and it["markdown"]:
                md = clean_md(it["markdown"])
                url = it.get("url", "")
                crawl = it.get("crawl", {}) or {}
                slug = re.sub(r"[^a-zA-Z0-9]+", "-", url.split("://", 1)[-1])[:100].strip("-")
                head = (f"<!-- source: {url}\n     loadedTime(UTC): {crawl.get('loadedTime')}\n"
                        f"     httpStatus: {crawl.get('httpStatusCode')}\n     apifyRun: {run_id} ({name}) -->\n\n")
                (root / "pages" / f"{slug}.md").write_text(head + md)
                it["markdown"] = f"<see pages/{slug}.md>"
            slim.append(it)
        text = SIGNED.sub("<signed-url-removed>", json.dumps(slim, ensure_ascii=False, indent=1))
        (root / "apify" / f"{name}.json").write_text(text)
        print(name, run["status"], len(items))
    (root / "apify" / "runs.json").write_text(json.dumps(meta, indent=1))


main()
