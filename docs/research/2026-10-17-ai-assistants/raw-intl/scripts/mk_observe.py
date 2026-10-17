"""Build an apify/playwright-scraper input that observes assistant/chat widgets over time.

The page function: waits, clicks a cookie-consent "accept all" button if one is present (the only
click it makes; no forms are submitted), then scrolls the page in steps and records, at each step,
the scroll depth, elapsed seconds, and every visible element whose id/class/aria/text names a chat
or assistant (including Conrad Group's KAI), with its geometry and text. This shows whether an
assistant opens or nudges by itself, when, and how large it is on desktop (1440x900) or mobile
(390x844, set by the third argument).

Usage: python3 -I mk_observe.py <urls.txt> <out.json> [desktop|mobile] [RESIDENTIAL] [COUNTRY]
"""
import json
import pathlib
import sys

urls = [u.strip() for u in pathlib.Path(sys.argv[1]).read_text().splitlines() if u.strip() and not u.startswith("#")]
mode = sys.argv[3] if len(sys.argv) > 3 else "desktop"
group = sys.argv[4] if len(sys.argv) > 4 else ""
country = sys.argv[5] if len(sys.argv) > 5 else ""
vw, vh = (390, 844) if mode == "mobile" else (1440, 900)

PAGE_FUNCTION = r"""
async function pageFunction(context) {
    const { page, request } = context;
    const VW = __VW__, VH = __VH__;
    await page.setViewportSize({ width: VW, height: VH });
    const t0 = Date.now();
    await page.waitForTimeout(6000);
    const consentSelectors = ['#onetrust-accept-btn-handler', '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
        '#CybotCookiebotDialogBodyButtonAccept', 'button[data-testid="uc-accept-all-button"]', '#uc-btn-accept-banner',
        'button#accept-all', '.cmpboxbtnyes', 'button[aria-label*="Alle akzeptieren"]', 'button[aria-label*="Accept all"]'];
    let consent = null;
    for (const sel of consentSelectors) {
        try { const el = await page.$(sel); if (el && await el.isVisible()) { await el.click(); consent = sel; break; } } catch (e) {}
    }
    if (!consent) {
        try {
            const btn = page.locator('button:visible', { hasText: /^(Alle akzeptieren|Alles akzeptieren|Accept all|Accept All Cookies|Alle zulassen|Akzeptieren|Allow all|Accept)$/i }).first();
            if (await btn.count()) { await btn.click({ timeout: 3000 }); consent = 'text-button'; }
        } catch (e) {}
    }
    const snap = async (label) => page.evaluate(([label, t0]) => {
        const re = /(chat|assist|assistent|chatbot|\bkai\b|genie|copilot|messenger|live-?chat|helpbot|\bki\b|ask-ai|ai-assist)/i;
        const out = [];
        document.querySelectorAll('body *').forEach(el => {
            const id = el.id || '';
            const cls = (typeof el.className === 'string') ? el.className : '';
            const aria = el.getAttribute('aria-label') || '';
            const title = el.getAttribute('title') || '';
            if (!re.test(id + ' ' + cls + ' ' + aria + ' ' + title)) return;
            const r = el.getBoundingClientRect();
            if (r.width < 8 || r.height < 8) return;
            const cs = getComputedStyle(el);
            if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') return;
            out.push({ tag: el.tagName, id: id.slice(0, 60), cls: cls.slice(0, 100), aria: aria.slice(0, 80), title: title.slice(0, 80),
                       pos: cs.position, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
                       text: (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 240) });
        });
        const iframes = Array.from(document.querySelectorAll('iframe')).map(f => { const r = f.getBoundingClientRect();
            return { src: (f.src || '').slice(0, 140), title: f.title || '', w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) }; })
            .filter(f => f.w > 0 && /(chat|assist|bot|messenger|kai|ask|help)/i.test(f.src + ' ' + f.title));
        const depth = Math.round(100 * (window.scrollY + window.innerHeight) / Math.max(1, document.documentElement.scrollHeight));
        return { label, seconds: Math.round((Date.now() - t0) / 1000), scrollDepthPct: depth, elements: out.slice(0, 25), iframes };
    }, [label, t0]);
    const timeline = [await snap('after-consent')];
    for (let i = 1; i <= 8; i++) {
        await page.mouse.wheel(0, Math.round(VH * 0.6));
        await page.waitForTimeout(3500);
        timeline.push(await snap('scroll-' + i));
    }
    await page.waitForTimeout(15000);
    timeline.push(await snap('dwell-end'));
    return { url: request.url, loadedUrl: page.url(), loadedAt: new Date(t0).toISOString(), viewport: VW + 'x' + VH, consent, title: await page.title(), timeline };
}
""".replace("__VW__", str(vw)).replace("__VH__", str(vh))

proxy = {"useApifyProxy": True}
if group:
    proxy["apifyProxyGroups"] = [group]
if country:
    proxy["apifyProxyCountry"] = country
body = {
    "startUrls": [{"url": u} for u in urls],
    "pageFunction": PAGE_FUNCTION,
    "proxyConfiguration": proxy,
    "maxRequestRetries": 1,
    "maxConcurrency": 4,
    "pageLoadTimeoutSecs": 90,
    "pageFunctionTimeoutSecs": 150,
    "headless": True,
    "maxPagesPerCrawl": len(urls) + 2,
    "linkSelector": "",
}
pathlib.Path(sys.argv[2]).write_text(json.dumps(body, indent=1))
print(len(urls), mode, group or "datacenter", country)
