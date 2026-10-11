import { createRequire } from 'node:module';
import path from 'node:path';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const browser = await chromium.launch({ channel: 'chromium' });
for (const url of process.argv.slice(2)) {
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  await page.goto(url + (url.includes('?') ? '' : '?cbq=' + Date.now()), { waitUntil: 'networkidle', timeout: 90000 }).catch(()=>{});
  await page.waitForTimeout(1200);
  const out = await page.evaluate(() => {
    const info = (sel) => { const el = document.querySelector(sel); if (!el) return 'none'; const s = getComputedStyle(el); const r = el.getBoundingClientRect(); return { h: +r.height.toFixed(2), mt: s.marginTop, mb: s.marginBottom, pt: s.paddingTop, pb: s.paddingBottom, y: +(r.y + scrollY).toFixed(2) }; };
    return {
      nav: info('.pdp-section-nav'),
      descBlock: info('#description.pdp-block'),
      purchase: info('.pdp-purchase'),
      buyInner: info('.pdp-buy-inner'),
      specList: info('.pdp-spec-list'),
      avail: info('.pdp-avail'),
      cta: info('.pdp-btn-dark'),
      ask: info('.pdp-btn-secondary'),
      tools: info('.pdp-product-tools'),
      plan: info('.pdp-project-check'),
      faqBlock: info('.pdp-faqs'),
      faqRow: info('.pdp-faqs .pdp-disclose'),
      faqSummary: info('.pdp-faqs .pdp-disclose summary'),
      deck: info('.pdp-info-deck'),
      tabs: info('.pdp-info-tabs'),
      panel: info('.pdp-info-panel'),
      benefits: info('.pdp-benefits'),
      benefit: info('.pdp-benefit'),
    };
  });
  console.log((url.includes('de-linker.com') ? 'LIVE' : 'T16 '), JSON.stringify(out, null, 0));
  await page.close();
}
await browser.close();
