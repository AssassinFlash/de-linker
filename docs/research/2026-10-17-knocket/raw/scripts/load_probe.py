"""Load the owner's Knocket snippet once in a throwaway local page and record what it does.

No chat message is sent by this script. Visitor credentials returned by the
vendor (userSig and similar) are redacted before anything is written.

Usage: python3 -I load_probe.py <page_url> <out_dir> <width> <height>
"""

import json
import pathlib
import re
import sys
import time

from playwright.sync_api import sync_playwright

page_url, out_dir, width, height = sys.argv[1], pathlib.Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
out_dir.mkdir(parents=True, exist_ok=True)
SECRET_KEYS = re.compile(r'("(?:userSig|usersig|UserSig|a2Key|A2Key|authKey|token|Token|ticket)"\s*:\s*)"[^"]*"')


def redact(text: str) -> str:
    return SECRET_KEYS.sub(r'\1"<redacted>"', text)


log: list[dict] = []
ws_log: list[dict] = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, locale="de-DE")
    page = ctx.new_page()

    def on_request(req):
        entry = {"t": round(time.time(), 3), "method": req.method, "url": req.url, "type": req.resource_type}
        if "portal-api-lc" in req.url and req.post_data:
            entry["post"] = redact(req.post_data)
        log.append(entry)

    def on_response(resp):
        if "portal-api-lc" in resp.url:
            try:
                body = resp.text()
            except Exception as err:  # noqa: BLE001
                body = f"<unreadable {err}>"
            log.append({"t": round(time.time(), 3), "response_for": resp.url, "status": resp.status, "body": redact(body)[:20000]})

    page.on("request", on_request)
    page.on("response", on_response)
    page.on("websocket", lambda ws: ws_log.append({"url": ws.url.split("?")[0], "query_keys": re.findall(r"[?&]([^=&]+)=", ws.url)}))

    before = page.evaluate("() => null")
    page.goto(page_url, wait_until="load")
    body_before = page.evaluate("() => getComputedStyle(document.body).cssText || [getComputedStyle(document.body).fontFamily, getComputedStyle(document.body).fontSize, getComputedStyle(document.body).margin].join('|')")
    page.wait_for_timeout(12000)
    body_after = page.evaluate("() => [getComputedStyle(document.body).fontFamily, getComputedStyle(document.body).fontSize, getComputedStyle(document.body).margin].join('|')")
    state = page.evaluate(
        """() => ({
        headLinks: [...document.head.querySelectorAll('link,style,script')].map(e => e.outerHTML.slice(0, 200)),
        bodyChildren: [...document.body.children].map(e => e.tagName + '#' + e.id + '.' + e.className),
        localStorageKeys: Object.keys(localStorage),
        cookie: document.cookie,
        widgetText: (window.contactWidget && window.contactWidget.shadowRoot) ? window.contactWidget.shadowRoot.textContent.slice(0, 3000) : null,
      })"""
    )
    cookies = ctx.cookies()
    page.screenshot(path=str(out_dir / f"load-{width}.png"))
    browser.close()

(out_dir / f"load-{width}.json").write_text(
    json.dumps(
        {
            "page_url": page_url,
            "viewport": [width, height],
            "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "body_style_before": body_before,
            "body_style_after": body_after,
            "state": state,
            "cookies": [{"name": c["name"], "domain": c["domain"], "expires": c["expires"]} for c in cookies],
            "websockets": ws_log,
            "requests": log,
        },
        ensure_ascii=False,
        indent=1,
    )
)
print("requests", len([e for e in log if "url" in e]), "ws", len(ws_log))
