// 五段终审 reviewer's own landmarks probe: section geometry on live and t16 so
// the exempt regions (P1 #stats, P2 .pdp-pairings, P3 .pdp-faqs, P4 390
// .pdp-spec-list, chips rows, rail-help card, DE intro, Genie dock) can be
// located in the pixel space of the paired captures.
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const browser = await chromium.launch({ channel: 'chromium' });
const out = {};
const PAGES = [
  ['shop-en', 'https://de-linker.com/products/', 'http://127.0.0.1:8924/products/'],
  ['shop-de', 'https://de-linker.com/de/produkte/', 'http://127.0.0.1:8924/de/produkte/'],
  ['archive-en', 'https://de-linker.com/product-category/inverters/', 'http://127.0.0.1:8924/product-category/inverters/'],
  ['archive-de', 'https://de-linker.com/de/produkt-kategorie/wechselrichter/', 'http://127.0.0.1:8924/de/produkt-kategorie/wechselrichter/'],
  ['pdp-en', 'https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/', 'http://127.0.0.1:8924/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
  ['pdp-de', 'https://de-linker.com/de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/', 'http://127.0.0.1:8924/de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
];
const SELECTORS = [
  '.wb-acts', '.catalog-mobile-actions', '.rail-help', '.linker-contact-invitation',
  '.woocommerce-pagination', '.catalog-pagination', '.catalog-pagination-pill',
  '.pdp-overview', '.pdp-overview-intro', '.pdp-overview-copy', '.pdp-benefits',
  '.pdp-stats-layout', '#stats', '.pdp-info-tabs', '.pdp-info-deck', '.pdp-pairings',
  '.pdp-faqs', '.pdp-docs', '.pdp-spec-list', '.pdp-project-check', '.pdp-gallery-main-wrap',
  '.pdp-hero', '.site-footer', 'footer', '.genie-launcher', '.linker-genie-bubble',
  '[class*="genie"]',
];
for (const [key, liveUrl, t16Url] of PAGES) {
  for (const width of [1440, 390]) {
    for (const [side, url] of [['live', liveUrl], ['t16', t16Url]]) {
      const ctx = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 } });
      const page = await ctx.newPage();
      await page.goto(url + (url.includes('?') ? '&' : '?') + 'cbq=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 90000 });
      await page.waitForTimeout(2200);
      await page.evaluate(async () => {
        const step = () => new Promise((r) => setTimeout(r, 40));
        for (let t = 0; t < document.body.scrollHeight + 800; t += 700) { window.scrollTo(0, t); await step(); }
        window.scrollTo(0, 0);
      });
      await page.waitForTimeout(800);
      out[`${key}-${width}-${side}`] = await page.evaluate((SELECTORS) => {
        const res = {};
        const rect = (el) => { const r = el.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)]; };
        for (const sel of SELECTORS) {
          try {
            const els = [...document.querySelectorAll(sel)];
            if (els.length) res[sel] = els.slice(0, 3).map(rect);
          } catch (e) { /* invalid selector */ }
        }
        res['#pageH'] = [0, 0, document.documentElement.clientWidth, document.documentElement.scrollHeight];
        const intro = document.querySelector('.pdp-overview-intro');
        if (intro) res['introText'] = intro.textContent.trim().replace(/\s+/g, ' ').slice(0, 160);
        const dock = [...document.querySelectorAll('[class*="genie"], [id*="genie"]')]
          .map((e) => [e.tagName + '.' + String(e.className).slice(0, 40), rect(e)])
          .filter(([, r]) => r[2] > 0 && r[3] > 0).slice(0, 8);
        res['genieEls'] = dock;
        return res;
      }, SELECTORS);
      await ctx.close();
    }
  }
}
await browser.close();
fs.writeFileSync(process.argv[2] || 'landmarks-v5.json', JSON.stringify(out, null, 1));
console.log('written', process.argv[2] || 'landmarks-v5.json');
