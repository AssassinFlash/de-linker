"""Print one crawled page's markdown (or grep across all) from Apify dataset files.

Usage:
  python3 -I show.py page <url> <dataset.json>...
  python3 -I show.py grep <regex> <dataset.json>...
"""

import json
import re
import sys

mode, arg, files = sys.argv[1], sys.argv[2], sys.argv[3:]
items = [i for f in files for i in json.load(open(f))]
if mode == "page":
    for i in items:
        if i["url"].rstrip("/") == arg.rstrip("/"):
            print("URL:", i["url"], "| loadedAt:", i.get("crawl", {}).get("loadedTime") or i.get("crawl", {}).get("loadedAt"))
            print(i.get("markdown") or i.get("text"))
else:
    rx = re.compile(arg, re.I)
    for i in items:
        txt = i.get("markdown") or i.get("text") or ""
        for m in rx.finditer(txt):
            print(i["url"], "::", txt[max(0, m.start() - 220): m.end() + 260].replace("\n", " "))
