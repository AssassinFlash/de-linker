import { createRequire } from 'node:module';
import path from 'node:path';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const out = process.argv[2];
const PAGES = [
  ['eta-en', 'https://de-linker.com/product/goodwe-esa-gw5k-eta-g20-5-kw-three-phase-power-module/', 'http://127.0.0.1:8924/product/goodwe-esa-gw5k-eta-g20-5-kw-three-phase-power-module/'],
  ['eta-de', 'https://de-linker.com/de/produkt/goodwe-esa-gw5k-eta-g20-5-kw-three-phase-power-module/', 'http://127.0.0.1:8924/de/produkt/goodwe-esa-gw5k-eta-g20-5-kw-three-phase-power-module/'],
];
const browser = await chromium.launch({ channel: 'chromium' });
for (const [name, live, t16] of PAGES) {
  for (const [side, url] of [['live', live], ['t16', t16]]) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    try {
      await page.goto(url + '?cbq=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 90000 });
      await page.waitForTimeout(2500);
      await page.evaluate(async () => { const step = () => new Promise((r) => setTimeout(r, 40)); for (let t = 0; t < document.body.scrollHeight + 800; t += 700) { window.scrollTo(0, t); await step(); } window.scrollTo(0, 0); }).catch(() => {});
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${out}/${name}-1440-${side}.png`, fullPage: true });
      console.log(name, side, 'ok');
    } catch (e) { console.log(name, side, 'ERROR', e.message.slice(0, 70)); }
    await context.close();
  }
}
await browser.close();
