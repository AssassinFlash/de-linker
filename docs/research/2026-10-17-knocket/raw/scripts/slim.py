"""Assemble slimmed raw captures for the dossier from the scratch working directory.

Usage: python3 -I slim.py <scratch_dir> <raw_dir>
Writes: apify/runs.json (labelled), apify/search-N.json, apify/dns.json, apify/pages/*.md,
sdk/sdk-facts.json, probe/*.json + screenshots. No tokens are read or written here.
"""

import hashlib
import json
import pathlib
import re
import shutil
import sys

scratch, raw = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
(raw / "apify" / "pages").mkdir(parents=True, exist_ok=True)
(raw / "sdk").mkdir(exist_ok=True)
(raw / "probe").mkdir(exist_ok=True)

# 1. run ledger
runs_p = raw / "apify" / "runs.json"
not_mine = {"gNdCSRyQ9x5ugc542", "W85rO1sb6tCj3vOOx"}
purpose = {
    "fw7kk0LTdFvVoiogi": "search1: Knocket basics (6 queries) -> search-1.json",
    "Y7JRbdd7gB2IcS4yc": "crawl1: knocket.trtc.io whole site (254 pages) -> pages/",
    "7xDAlsHj2cz4VpDVo": "search2: privacy/terms/DPA/reviews (10 queries) -> search-2.json",
    "mbY3O6TmjbmIxKRmi": "crawl2: trtc.io legal pages, Tencent privacy policy, third parties -> pages/",
    "eFovbtqXA5VnG0KOe": "DNS attempt 1 (rag-web-browser could not parse JSON; discarded)",
    "0jmZ3tZpwRpKTL7LI": "DNS attempt 2 (same; discarded)",
    "WBSLuaY1C0jxLOymW": "DNS-over-HTTPS via dns.google for 4 hosts -> dns.json",
    "7KbwTc8plR9nuOBqb": "search3: DPSA/reviews/data centres (8 queries) -> search-3.json",
    "mYBrQU3NMTdZzU8Hf": "crawl3: DPSA, Chat data-centre doc, WP plugin, third-party write-ups -> pages/",
    "XqDd6ON57iU5QgrOx": "search4: LG Muenchen Google Fonts / adequacy / TDDDG -> search-4.json",
    "TwB4Y6rAB7OePpHfu": "EU adequacy decisions page -> pages/",
}
rows = [r for r in json.loads(runs_p.read_text()) if r["run_id"] not in not_mine]
for r in rows:
    r["purpose"] = purpose.get(r["run_id"], "")
runs_p.write_text(json.dumps(rows, ensure_ascii=False, indent=1))

# 2. searches
for n in range(1, 5):
    src = scratch / f"search{n}.out.json"
    out = []
    for q in json.loads(src.read_text()):
        out.append({"query": q["searchQuery"]["term"], "results": [{"url": r["url"], "title": r["title"], "description": r.get("description")} for r in q.get("organicResults", [])]})
    (raw / "apify" / f"search-{n}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

# 3. DNS
dns = [{"url": i["url"], "loadedAt": i["loadedAt"], "body": json.loads(i["text"])} for i in json.loads((scratch / "dns-pw.out.json").read_text())]
(raw / "apify" / "dns.json").write_text(json.dumps(dns, indent=1))

# 4. pages (only the ones the dossier cites)
wanted = {
    "https://knocket.trtc.io/": "knocket-home",
    "https://knocket.trtc.io/tutorials/ai-agent/": "knocket-tutorial-ai-agent",
    "https://knocket.trtc.io/tutorials/add-ai-assistant-to-website/": "knocket-tutorial-complete-guide",
    "https://knocket.trtc.io/tutorials/web-widget/": "knocket-tutorial-web-widget",
    "https://knocket.trtc.io/tutorials/ai_agent_handoff_phrases/": "knocket-handoff-phrases",
    "https://knocket.trtc.io/why-free/": "knocket-why-free",
    "https://knocket.trtc.io/legal/privacy/": "knocket-legal-privacy",
    "https://knocket.trtc.io/legal/terms/": "knocket-legal-terms",
    "https://knocket.trtc.io/blog/woocommerce-live-chat/": "knocket-blog-woocommerce",
    "https://knocket.trtc.io/blog/javascript-live-chat/": "knocket-blog-javascript-consent",
    "https://knocket.trtc.io/products/mobile-widget/": "knocket-product-mobile-widget",
    "https://knocket.trtc.io/products/web-widget/": "knocket-product-web-widget",
    "https://knocket.trtc.io/de/": "knocket-home-de",
    "https://www.tencentcloud.com/document/product/301/17347": "tencent-dpsa",
    "https://www.tencentcloud.com/document/product/301/17345": "tencent-privacy-policy",
    "https://www.tencentcloud.com/document/product/1047/33513": "tencent-chat-overview-data-centres",
    "https://trtc.io/company/compliance-privacy": "trtc-compliance",
    "https://wordpress.org/plugins/knocket-live-chat-widget/": "wporg-knocket-plugin",
    "https://chatgate.ai/de/post/knocket": "chatgate-knocket",
    "https://peerpush.com/p/knocket": "peerpush-knocket",
    "https://tencentrtc.medium.com/how-i-added-ai-auto-reply-to-a-free-website-chat-widget-in-openclaw-aa99789f2aae": "medium-tencentrtc-openclaw",
    "https://www.linkedin.com/posts/tencentrtc_ai-vibecoding-openclaw-activity-7442900598418661376-mzsI": "linkedin-tencentrtc-launch",
    "https://www.reddit.com/r/buildinpublic/comments/1rq0130/i_launched_knocket_a_free_oneline_widget_for_chat/": "reddit-buildinpublic-launch",
    "https://eusovereigntyscore.eu/en/vendors/tencent-cloud": "eusovereigntyscore-tencent",
}
items = []
for f in ["crawl1.out.json", "crawl2.out.json", "crawl3.out.json"]:
    items += json.loads((scratch / f).read_text())
for i in json.loads((scratch / "adeq.out.json").read_text()):
    items.append({"url": i["metadata"]["url"], "markdown": i.get("markdown"), "crawl": {"loadedTime": i["crawl"].get("loadedAt")}})
wanted["https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en"] = "ec-adequacy-decisions"
done = set()
for i in items:
    name = wanted.get(i["url"])
    if not name or name in done:
        continue
    done.add(name)
    md = i.get("markdown") or i.get("text") or ""
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)  # drop image embeds
    when = i.get("crawl", {}).get("loadedTime") or i.get("crawl", {}).get("loadedAt")
    (raw / "apify" / "pages" / f"{name}.md").write_text(f"<!-- source: {i['url']} | fetched (UTC): {when} | via Apify -->\n\n{md}\n")
print("pages", len(done), "missing", sorted(set(wanted.values()) - done))

# 5. SDK facts (the 3 MB bundle itself is not committed)
sdk = (scratch / "sdk" / "sdk.js").read_bytes()
css = (scratch / "sdk" / "sdk.css").read_bytes()
s = sdk.decode("utf-8", "replace")
region = re.search(r"PRODUCTION:\{CHINA:.*?INDONESIA:\{[^}]*\}\}", s)
facts = {
    "url": "https://trtc.io/knocket-sdk/sdk.js?identifier=f145fd3b67d64f4704&v=1792224006909",
    "fetched_utc": "2026-10-17T08:17:58Z",
    "bytes": len(sdk),
    "bytes_brotli_transfer": 883074,
    "sha256": hashlib.sha256(sdk).hexdigest(),
    "response_headers": (scratch / "sdk" / "headers.txt").read_text(),
    "sdk_css": {"url": "https://trtc.io/knocket-sdk/sdk.css", "bytes": len(css), "sha256": hashlib.sha256(css).hexdigest()},
    "portal_api": "https://api.trtc.io/common/portal-api-lc",
    "portal_actions": sorted(set(re.findall(r'Action:"([A-Za-z]+)"', s))),
    "script_tag_params_read": ["identifier", "type", "autoShow"],
    "public_api_window_contactWidget": ["show", "hide", "toggle", "setContainerStyle", "openFloat", "hideFloat", "showChat", "hideChat", "showChatCard", "setOverlayStyle", "on", "once", "off", "emit"],
    "sticky_events": ["ready", "firstMessageSent", "chatReady"],
    "absent_strings": {k: s.count(k) for k in ["knocketConfig", "navigator.language", "documentElement.lang", "document.referrer", "proactive", "openai", "deepseek", "gdpr", "consent"]},
    "ui_locales": re.search(r'sg=\[[^\]]*\]', s).group(0)[:600],
    "german_strings_sample": re.search(r'"email-placeholder":"beispiel@domain\.de".{0,900}', s).group(0) if re.search(r'"email-placeholder":"beispiel@domain\.de"', s) else re.search(r'beispiel@domain\.de.{0,900}', s).group(0),
    "english_email_error_string": re.search(r'"email-error":"The order could not be found[^"]*"', s).group(0),
    "im_region_table_excerpt": region.group(0)[:4000] if region else None,
    "external_hosts_in_bundle": sorted(set(re.findall(r"https?://([a-zA-Z0-9.-]+)", s))),
}
(raw / "sdk" / "sdk-facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1))

# 6. probes
for name in ["load-1440.json", "load-390.json", "open-1440.json", "open-390.json", "ai.slim.json"]:
    data = json.loads((scratch / "probe" / name).read_text())
    if "state" in data and data["state"].get("widgetText"):
        data["state"]["widgetText"] = data["state"]["widgetText"][:200] + " ...<truncated: shadow-DOM style text>"
    text = json.dumps(data, ensure_ascii=False, indent=1)
    values = re.findall(r'userSig\\*"\s*:\s*\\*"([^"\\]*)', text)
    assert all(v == "<redacted>" for v in values), name
    (raw / "probe" / name).write_text(text)
for png in ["load-1440.png", "open-1440.png", "open-390.png", "ai-2.png"]:
    shutil.copy(scratch / "probe" / png, raw / "probe" / png)
print("ok")
