// Paired full-page captures: live|t16, same browser, same viewport, same settle
// protocol — shop, archive and PDP in EN and DE at 1440 and 390.
import { createRequire } from 'node:module';
import path from 'node:path';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const out = process.argv[2];
const PAGES = [
  ['shop', 'http://127.0.0.1:8924/products/', 'https://de-linker.com/products/', 'http://127.0.0.1:8924/de/produkte/', 'https://de-linker.com/de/produkte/'],
  ['archive', 'http://127.0.0.1:8924/product-category/inverters/', 'https://de-linker.com/product-category/inverters/', 'http://127.0.0.1:8924/de/produkt-kategorie/wechselrichter/', 'https://de-linker.com/de/produkt-kategorie/wechselrichter/'],
  ['pdp', 'http://127.0.0.1:8924/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/', 'https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/', 'http://127.0.0.1:8924/de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/', 'https://de-linker.com/de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
];
const browser = await chromium.launch({ channel: 'chromium' });
for (const [name, t16en, liveen, t16de, livede] of PAGES) {
  for (const [lang, t16, live] of [['en', t16en, liveen], ['de', t16de, livede]]) {
    for (const width of [1440, 390]) {
      for (const [side, url] of [['live', live], ['t16', t16]]) {
        const context = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 } });
        const page = await context.newPage();
        try {
          await page.goto(url + '?cbq=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 90000 });
          await page.waitForTimeout(2500);
          await page.evaluate(async () => {
            const step = () => new Promise((r) => setTimeout(r, 40));
            for (let t = 0; t < document.body.scrollHeight + 800; t += 700) { window.scrollTo(0, t); await step(); }
            window.scrollTo(0, 0);
          }).catch(() => {});
          await page.waitForTimeout(1500);
          await page.screenshot({ path: `${out}/${name}-${lang}-${width}-${side}.png`, fullPage: true });
          const h = await page.evaluate(() => document.body.scrollHeight).catch(() => 0);
          console.log(`${name}-${lang}-${width}-${side} h=${h}`);
        } catch (e) {
          console.log(`${name}-${lang}-${width}-${side} ERROR ${e.message.slice(0, 80)}`);
        }
        await context.close();
      }
    }
  }
}
await browser.close();
console.log('done');
