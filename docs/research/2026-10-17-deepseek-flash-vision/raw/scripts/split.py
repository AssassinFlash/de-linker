"""Split an Apify website-content-crawler dataset into one Markdown file per page.

Usage: python3 -I split.py <items.json> <outdir>
Each file starts with a provenance header: URL, page title, Apify load time (UTC).
"""

import json
import pathlib
import sys

items = json.loads(pathlib.Path(sys.argv[1]).read_text())
out = pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for it in items:
    url = it.get("url", "")
    slug = url.replace("https://api-docs.deepseek.com/", "").strip("/").replace("/", "__") or "index"
    header = (
        f"<!-- source: {url}\n"
        f"     title: {(it.get('metadata') or {}).get('title', '')}\n"
        f"     fetched (UTC, Apify apify/website-content-crawler): {(it.get('crawl') or {}).get('loadedTime')} -->\n\n"
    )
    (out / f"{slug}.md").write_text(header + (it.get("markdown") or ""))
print(len(items))
