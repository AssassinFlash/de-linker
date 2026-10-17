"""Print a markdown table of raw-intl/pages/*.md: file, source URL, load time (UTC), Apify run."""
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
rows = []
for p in sorted(root.glob("*.md")):
    head = p.read_text()[:600]
    url = re.search(r"source: (\S+)", head)
    t = re.search(r"loadedTime\(UTC\): (\S+)", head)
    run = re.search(r"apifyRun: (\S+) \(([^)]+)\)", head)
    rows.append((url.group(1) if url else "?", t.group(1) if t else "?", f"{run.group(1)} ({run.group(2)})" if run else "?", p.name))
print("| 来源 URL | 抓取时间（UTC） | Apify run | raw 文件 |")
print("|---|---|---|---|")
for url, t, run, name in sorted(rows):
    print(f"| {url} | {t} | {run} | `pages/{name}` |")
