// Reviewer probe: what filter sections the rail carries on shop vs archive, live vs t16.
import { createRequire } from 'node:module';
import path from 'node:path';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const browser = await chromium.launch({ channel: 'chromium' });
const out = {};
for (const [key, live, t16] of [
  ['shop-en', 'https://de-linker.com/products/', 'http://127.0.0.1:8924/products/'],
  ['archive-en', 'https://de-linker.com/product-category/inverters/', 'http://127.0.0.1:8924/product-category/inverters/'],
]) {
  out[key] = {};
  for (const [side, url] of [['live', live], ['t16', t16]]) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(url + '?cbq=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(2500);
    out[key][side] = await page.evaluate(() => {
      const rail = document.querySelector('.sidebar-filters, .rail, aside');
      const rect = (el) => { const r = el.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)]; };
      const sections = rail ? [...rail.querySelectorAll('details')].map((s) => {
        const sum = s.querySelector(':scope > summary');
        return {
          title: (sum?.textContent || '').trim(),
          open: s.hasAttribute('open'),
          rect: rect(s),
          options: [...s.querySelectorAll('.filter-option')].length,
        };
      }) : null;
      // non-details blocks inside the rail (e.g. the help card, search box, sort)
      const others = rail ? [...rail.children].filter((c) => c.tagName !== 'DETAILS').map((c) => ({
        tag: c.tagName, cls: String(c.className).slice(0, 50), rect: rect(c),
        text: c.textContent.trim().replace(/\s+/g, ' ').slice(0, 60),
      })) : null;
      return { railCls: rail ? String(rail.className) : null, railRect: rail ? rect(rail) : null, sections, others };
    });
    await ctx.close();
  }
}
await browser.close();
console.log(JSON.stringify(out, null, 1));
