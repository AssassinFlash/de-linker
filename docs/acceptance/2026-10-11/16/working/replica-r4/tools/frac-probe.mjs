import { createRequire } from 'node:module';
import path from 'node:path';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const browser = await chromium.launch({ channel: 'chromium' });
for (const url of process.argv.slice(2)) {
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  await page.goto(url + (url.includes('?') ? '' : '?cbq=' + Date.now()), { waitUntil: 'networkidle', timeout: 90000 }).catch(()=>{});
  await page.evaluate(async () => { await new Promise((r) => { let t = 0; const s = () => { window.scrollTo(0, t); t += 800; if (t < document.body.scrollHeight + 800) setTimeout(s, 35); else r(); }; s(); }); });
  await page.waitForTimeout(800);
  const out = await page.evaluate(() => {
    const y = (sel) => { const el = document.querySelector(sel); return el ? +(el.getBoundingClientRect().y + scrollY).toFixed(2) : null; };
    const h = (sel) => { const el = document.querySelector(sel); return el ? +el.getBoundingClientRect().height.toFixed(2) : null; };
    return {
      layoutY: y('.pdp-layout'), layoutH: h('.pdp-layout'),
      galleryH: h('.pdp-gallery'), purchaseH: h('.pdp-purchase'),
      contentY: y('.pdp-content'), contentH: h('.pdp-content'),
      overviewY: y('.pdp-overview'), overviewH: h('.pdp-overview'),
      benefitsY: y('.pdp-benefits'), benefitsH: h('.pdp-benefits'),
      disclose0Y: y('.pdp-disclose'), disclose0H: h('.pdp-disclose'),
      statsY: y('#stats'), statsH: h('#stats'),
      docsY: y('#downloads'), docsH: h('#downloads'),
      faqY: y('.pdp-faqs'), faqH: h('.pdp-faqs'),
      pairingsY: y('.pdp-pairings'), pairingsH: h('.pdp-pairings'),
      card0Y: y('.pdp-pairing'), card0H: h('.pdp-pairing'),
      pageH: document.body.scrollHeight,
    };
  });
  console.log((url.includes('de-linker.com') ? 'LIVE' : 'T16 '), JSON.stringify(out));
  await page.close();
}
await browser.close();
