"""Summarize observation timelines: per page, per step, the visible chat/assistant elements."""
import json
import pathlib
import sys

for it in json.loads(pathlib.Path(sys.argv[1]).read_text()):
    print("\n###", it["url"], "->", it.get("loadedUrl"), "|", it.get("loadedAt"), "|", it.get("viewport"), "| consent:", it.get("consent"))
    for s in it.get("timeline", []):
        els = [f"{e['tag']}#{e['id']}.{e['cls'][:40]} [{e['pos']}] {e['x']},{e['y']} {e['w']}x{e['h']} '{e['text'][:80]}'" for e in s["elements"]]
        ifr = [f"iframe '{f['title']}' {f['w']}x{f['h']} @{f['x']},{f['y']}" for f in s["iframes"]]
        print(f"  {s['label']:>13} t={s['seconds']:>3}s depth={s['scrollDepthPct']:>3}% n={len(els)}")
        for line in (els[:6] + ifr[:3]):
            print("      ", line[:220])
