"""Open the Knocket panel on the throwaway page and screenshot it; optionally send ONE message.

Usage: python3 -I open_probe.py <page_url> <out_dir> <width> <height> [message]
Visitor credentials in vendor responses are redacted before writing.
"""

import json
import pathlib
import re
import sys
import time

from playwright.sync_api import sync_playwright

page_url, out_dir, width, height = sys.argv[1], pathlib.Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
message = sys.argv[5] if len(sys.argv) > 5 else None
SECRET_KEYS = re.compile(r'("(?:userSig|usersig|UserSig|a2Key|A2Key|authKey|token|Token|ticket)"\s*:\s*)"[^"]*"')
log: list[dict] = []
tag = f"{width}{'-msg' if message else ''}"

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, locale="de-DE")
    page = ctx.new_page()

    hosts: dict[str, int] = {}

    def on_request(req):
        host = req.url.split("/")[2] if "://" in req.url else req.url[:30]
        hosts[host] = hosts.get(host, 0) + 1
        if "portal" in req.url:
            log.append({"t": round(time.time(), 3), "method": req.method, "url": req.url.split("?")[0], "post": SECRET_KEYS.sub(r'\1"<redacted>"', req.post_data or "")})

    def on_response(resp):
        if "portal-api-lc" in resp.url:
            try:
                body = resp.text()
            except Exception as err:  # noqa: BLE001
                body = f"<unreadable {err}>"
            log.append({"t": round(time.time(), 3), "status": resp.status, "body": SECRET_KEYS.sub(r'\1"<redacted>"', body)[:6000]})

    page.on("request", on_request)
    page.on("response", on_response)
    page.goto(page_url, wait_until="load")
    page.wait_for_timeout(9000)
    page.screenshot(path=str(out_dir / f"closed-{tag}.png"))
    # Click the launcher bubble: the last clickable element in the widget's shadow root.
    page.mouse.click(width - 44, height - 44)
    page.wait_for_timeout(4000)
    page.screenshot(path=str(out_dir / f"open-{tag}.png"))
    texts = page.evaluate("() => { const r = window.contactWidget && window.contactWidget.shadowRoot; return r ? [...r.querySelectorAll('button,a,h1,h2,h3,p,span,div[role],textarea,input')].map(e => (e.innerText || e.placeholder || e.getAttribute('aria-label') || '').trim()).filter(Boolean).slice(0, 80) : null }")
    if message:
        box = page.locator("#contact-widget-auto textarea, #contact-widget-auto input[type=text], #contact-widget-auto [contenteditable=true]").first
        box.click()
        box.fill(message)
        page.keyboard.press("Enter")
        page.wait_for_timeout(45000)
        page.screenshot(path=str(out_dir / f"after-{tag}.png"))
        texts_after = page.evaluate("() => { const r = window.contactWidget.shadowRoot; return [...r.querySelectorAll('*')].filter(e => e.children.length === 0).map(e => (e.innerText || e.placeholder || '').trim()).filter(Boolean).slice(0, 120) }")
    else:
        texts_after = None
    browser.close()

(out_dir / f"open-{tag}.json").write_text(json.dumps({"page_url": page_url, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "message": message, "panel_texts": texts, "texts_after": texts_after, "hosts": hosts, "portal_log": log}, ensure_ascii=False, indent=1))
print("ok", tag)
