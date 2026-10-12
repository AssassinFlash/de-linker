// Identify the element at a page point (x, y) on live and t16 — used to name
// the check-card that renders soft-green on live and white on t16 at 390.
import { createRequire } from 'node:module';
import path from 'node:path';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const browser = await chromium.launch({ channel: 'chromium' });
const out = {};
for (const [side, url] of [
  ['live', 'https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
  ['t16', 'http://127.0.0.1:8924/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
]) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.goto(url + '?cbq=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(2200);
  out[side] = await page.evaluate(() => {
    const rect = (el) => { const r = el.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)]; };
    const el = document.elementFromPoint(350, 1600 - 0) || document.elementFromPoint(350, 800);
    // walk the chain from the top element at that page point (scroll so the point is on screen)
    window.scrollTo(0, 1600 - 400);
    const e2 = document.elementFromPoint(350, 400);
    const chain = [];
    let cur = e2;
    while (cur && chain.length < 6) {
      const cs = getComputedStyle(cur);
      chain.push({
        tag: cur.tagName, cls: String(cur.className).slice(0, 60), rect: rect(cur),
        bg: cs.backgroundColor, border: cs.borderColor, radius: cs.borderRadius,
      });
      cur = cur.parentElement;
    }
    window.scrollTo(0, 0);
    return chain;
  });
  await ctx.close();
}
await browser.close();
console.log(JSON.stringify(out, null, 1));
