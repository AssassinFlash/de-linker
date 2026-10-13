/** Read-only mobile behavior proof on t110; no fixtures or page writes. */
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../../..');
const { chromium } = createRequire(path.join(root, 'tests/e2e/package.json'))('playwright');
const user = process.argv[2] ?? 'e2e-en-1791887434348';
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(execFileSync('just', ['login', 't110', `--user=${user}`], { cwd: root, encoding: 'utf8' }).trim().split('\n').pop());
const results = [];
const onlyShortcuts = process.env.CHECK_SHORTCUTS_ONLY === '1';
for (const width of (onlyShortcuts ? [] : [390, 430])) {
 await page.setViewportSize({ width, height: width === 390 ? 844 : 932 });
 for (const locale of ['en', 'de']) {
  const base = 'http://127.0.0.1:8975' + (locale === 'de' ? '/de/mein-konto/' : '/my-account/');
  for (const [endpoint, name] of [['', 'overview'], ['inquiries/', 'inquiries'], ['documents/', 'documents'], ['saved-solutions/', 'saved-solutions'], ['company/billing/', 'company'], ['edit-account/', 'account-details'], ['inquiries/', 'inquiry-detail']]) {
   await page.goto(base + endpoint, { waitUntil: 'load' });
   await page.evaluate(() => document.fonts.ready);
   if (name === 'inquiry-detail') await page.locator('a[href*="/inquiry/"], a[href*="/anfrage/"]').first().click();
   await page.locator('.linker-account-menu-toggle').click();
   const menuLinks = await page.locator('.linker-account-mobile-menu a').count();
   if (menuLinks !== 7) throw new Error(`${locale}/${name}: menu lost a destination (${menuLinks})`);
   await page.locator('.linker-account-menu-toggle').click();
   const targets = await page.locator('.linker-account').evaluate(root => [...root.querySelectorAll('a, button, input:not([type="hidden"]), select, summary, [role="combobox"]')].filter(e => e.getBoundingClientRect().height > 0 && e.getAttribute('aria-hidden') !== 'true').map(e => { const r = e.getBoundingClientRect(); return { label: e.textContent.trim() || e.id, width: r.width, height: r.height }; }));
   const small = targets.filter(e => e.height < 44 || e.width < 44);
   if (small.length) throw new Error(`${locale}/${name}/${width}: small targets ${JSON.stringify(small)}`);
   if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error(`${name}: horizontal overflow`);
   const bottom = await page.locator('.linker-account-bottom-nav').boundingBox();
   const cta = await page.locator('button[name="save_address"], button[name="save_account_details"], .linker-account-proforma').first().boundingBox().catch(() => null);
   if (cta && cta.y + cta.height >= bottom.y) throw new Error(`${name}: CTA collides with tabs`);
   const last = page.locator('.linker-account-main a, .linker-account-main input:not([type="hidden"]), .linker-account-main select').last();
   await last.scrollIntoViewIfNeeded();
   const lastBox = await last.boundingBox();
   // Final content can be brought above the fixed UI, proved by hit testing.
   await page.evaluate(() => window.scrollBy(0, 250));
   const hit = await last.evaluate(e => { const r = e.getBoundingClientRect(); const found = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return found === e || e.contains(found); });
   if (!hit) throw new Error(`${name}: last content is covered`);
   await page.screenshot({ path: path.join(here, `ours-${locale}-${name}-bottom-${width}.png`) });
   results.push({ name, locale, width, menuLinks, navigation: '4 fixed tabs + complete collapsible menu', minTarget: Math.min(...targets.map(t => t.height)), gutter: await page.locator('.linker-account-main').evaluate(e => e.getBoundingClientRect().x), bottomHeight: bottom.height, cta, lastBox, lastContentHit: hit });
   console.log(`PASS ${locale}/${name}/${width}: targets >=44, no overflow, menu=7, final content reachable`);
  }
 }
}
await page.setViewportSize({ width: 390, height: 844 });
await page.goto('http://127.0.0.1:8975/my-account/');
for (const status of ['inquiry-received', 'proforma-issued', 'completed', 'cancelled']) {
 await page.goto('http://127.0.0.1:8975/my-account/');
 const expected = Number(await page.locator(`.linker-account-tile[data-status="${status}"] .linker-account-tile-count`).innerText());
 await page.locator(`.linker-account-tile[data-status="${status}"]`).click();
 if (!page.url().includes(`inquiry-status=${status}`)) throw new Error(`tile ${status}: missing state`);
 const actual = await page.locator('.linker-account-table-inquiries .linker-account-row-status').evaluateAll(es => es.map(e => e.dataset.status));
 if (actual.some(s => s !== status)) throw new Error(`tile ${status}: other state leaked`);
 if (expected > 0 && actual.length === 0) throw new Error(`tile ${status}: ${expected} stored inquiries vanished`);
 console.log(`PASS shortcut ${status}: ownership query narrowed to state (${actual.length} rows)`);
}
if (!onlyShortcuts) fs.writeFileSync(path.join(here, 'mobile-check.json'), JSON.stringify(results, null, '\t'));
await browser.close();
