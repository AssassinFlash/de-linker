"""Send up to two messages to Knocket's OWN AI agent on its own product page and record the replies.

This does not touch the owner's Knocket tenant. Visitor credentials in vendor responses are redacted.

Usage: python3 -I ai_probe.py <page_url> <out_json> <screenshot_prefix> <message1> [message2]
"""

import json
import re
import sys
import time

from playwright.sync_api import sync_playwright

page_url, out_json, shot = sys.argv[1], sys.argv[2], sys.argv[3]
messages = sys.argv[4:6]
SECRET_KEYS = re.compile(r'("(?:userSig|usersig|UserSig|a2Key|A2Key|authKey|token|Token|ticket)"\s*:\s*)"[^"]*"')
events: list[dict] = []
leaf_js = "() => { const r = window.contactWidget && window.contactWidget.shadowRoot; if (!r) return []; return [...r.querySelectorAll('*')].filter(e => e.children.length === 0).map(e => (e.innerText || '').trim()).filter(Boolean) }"

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="de-DE")
    page = ctx.new_page()
    page.on("request", lambda r: events.append({"t": round(time.time(), 2), "req": r.method + " " + r.url.split("?")[0], "post": SECRET_KEYS.sub(r'\1"<redacted>"', r.post_data or "")[:2000]}) if "portal" in r.url else None)
    page.goto(page_url, wait_until="load")
    page.wait_for_timeout(9000)
    page.mouse.click(1440 - 44, 900 - 44)
    page.wait_for_timeout(3000)
    # Enter the chat view if the widget opens on its home tab.
    for label in ["Start a Chat", "Chat starten", "Chat"]:
        loc = page.locator(f"#contact-widget-auto >> text={label}").first
        if loc.count():
            loc.click()
            break
    page.wait_for_timeout(4000)
    page.screenshot(path=f"{shot}-0.png")
    transcript = []
    for n, msg in enumerate(messages, 1):
        box = page.locator("#contact-widget-auto textarea, #contact-widget-auto [contenteditable=true], #contact-widget-auto input[type=text]").first
        box.click()
        box.fill(msg)
        page.keyboard.press("Enter")
        sent = time.time()
        page.wait_for_timeout(40000)
        page.screenshot(path=f"{shot}-{n}.png")
        transcript.append({"sent_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(sent)), "message": msg, "widget_text_after": page.evaluate(leaf_js)})
    browser.close()

with open(out_json, "w") as fh:
    json.dump({"page_url": page_url, "transcript": transcript, "portal_requests": events}, fh, ensure_ascii=False, indent=1)
print("done", len(transcript))
