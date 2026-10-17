"""Fill the appendix placeholders of INTL.md from raw-intl/apify/runs.json and raw-intl/pages/.

Usage: python3 -I fill_appendix.py <INTL.md> <raw-intl dir>
"""
import json
import pathlib
import re
import subprocess
import sys

doc = pathlib.Path(sys.argv[1])
raw = pathlib.Path(sys.argv[2])
runs = json.loads((raw / "apify" / "runs.json").read_text())
lines = ["| run id | actor | 用途 | 状态 | 开始 / 结束（UTC） | 条目 | raw 文件 |", "|---|---|---|---|---|---|---|"]
for r in runs:
    lines.append(f"| `{r['runId']}` | {r['actor']} | {r['name']} | {r['status']} | {r['startedAt']} / {r['finishedAt']} | {r['items']} | `apify/{r['name']}.json` |")
index = subprocess.run([sys.executable, "-I", str(raw / "scripts" / "index_pages.py"), str(raw / "pages")],
                       capture_output=True, text=True, check=True).stdout
text = doc.read_text()
text = re.sub(r"<!-- RUNS -->(.|\n)*?(?=\n## 附录 B)", "<!-- RUNS -->\n\n" + "\n".join(lines) + "\n", text)
text = re.sub(r"<!-- INDEX -->(.|\n)*\Z", "<!-- INDEX -->\n\n" + index, text)
doc.write_text(text)
print(len(runs), "runs;", index.count("\n") - 2, "pages")
