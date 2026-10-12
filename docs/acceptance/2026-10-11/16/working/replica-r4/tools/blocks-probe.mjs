// Block-level parity facts: container margins, the spec deck area, the Genie
// entry chips — live vs t16, shop and PDP, EN and DE.
import { createRequire } from 'node:module';
import path from 'node:path';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const browser = await chromium.launch({ channel: 'chromium' });
const urls = process.argv.slice(2);
for (const url of urls) {
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  await page.goto(url + (url.includes('?') ? '' : '?cbq=' + Date.now()), { waitUntil: 'networkidle', timeout: 90000 }).catch(()=>{});
  await page.evaluate(async () => { await new Promise((r) => { let t = 0; const s = () => { window.scrollTo(0, t); t += 800; if (t < document.body.scrollHeight + 800) setTimeout(s, 35); else r(); }; s(); }); });
  await page.waitForTimeout(800);
  const out = await page.evaluate(() => {
    const box = (sel) => { const el = document.querySelector(sel); if (!el) return 'none'; const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return { x: Math.round(r.x), w: Math.round(r.width), h: Math.round(r.height), pad: s.padding, mx: s.marginLeft + '/' + s.marginRight }; };
    const labels = (sel) => Array.from(document.querySelectorAll(sel)).slice(0, 6).map((el) => (el.textContent || '').trim().slice(0, 30));
    return {
      containerCatalog: box('#tv-woo-b2b-catalog .container, #tv-woo-b2b-catalog .sf-container'),
      containerPdp: box('#tv-storefront-pdp .sf-container'),
      catalogSection: box('.catalog-section'),
      pdpBlock: box('.pdp-block'),
      specDeckTabs: box('.pdp-info-tabs'),
      specDeck: box('.pdp-info-deck'),
      specRowSample: (() => { const r = document.querySelector('.pdp-stat-row'); if (!r) return 'none'; const s = getComputedStyle(r); return { h: +r.getBoundingClientRect().height.toFixed(1), pad: s.padding, fs: s.fontSize }; })(),
      genieChipsShop: labels('.catalog-mobile-actions a, .catalog-mobile-actions button, [data-linker-genie] a, [data-linker-genie] button'),
      genieChipsPdp: labels('.pdp-tool, [data-linker-genie] a, [data-linker-genie] button'),
      genieWrapCount: document.querySelectorAll('[data-linker-genie], .linker-genie-chips, .catalog-mobile-actions').length,
      headerH: (() => { const h = document.querySelector('header'); return h ? Math.round(h.getBoundingClientRect().height) : 'none'; })(),
      footerH: (() => { const f = document.querySelector('footer'); return f ? Math.round(f.getBoundingClientRect().height) : 'none'; })(),
    };
  });
  console.log((url.includes('de-linker.com') ? 'LIVE' : 'T16 '), url.replace('https://de-linker.com', '').replace('http://127.0.0.1:8924', ''), JSON.stringify(out));
  await page.close();
}
await browser.close();
