/**
 * The #484/#485 local walk: real pointer clicks on the roof map, real
 * guest save through the Store API, EN/DE at 1440 and 390. Writes record.json
 * and shots/ next to this file. Run against a snapshot instance whose engine
 * answers (/roof/pack, /roof/outline):
 *
 *     just up w480 && just serve w480
 *     node docs/acceptance/2026-10-21/484-485/walk.mjs
 */
import { createRequire } from 'node:module';
import { writeFileSync, mkdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const require = createRequire(
  fileURLToPath(new URL('../../../../plugins/linker-tools/package.json', import.meta.url))
);
const { chromium } = require('playwright');

const BASE = 'http://127.0.0.1:9252';
const OUT = fileURLToPath(new URL('.', import.meta.url)).replace(/\/$/, '');
mkdirSync(OUT + '/shots', { recursive: true });
const asset = readFileSync(
  fileURLToPath(new URL('../../../../plugins/linker-tools/build/configurator.asset.php', import.meta.url)),
  'utf8'
);
const build = asset.match(/'version' => '([^']+)'/)[1];

const locales = {
  en: {
    path: '/solution-configurator/',
    labels: { plz: /Postcode of the site/, kwh: /Annual household consumption/, kwp: /^PV array/ },
    buttons: { calculate: 'Calculate system', add: 'Add all to solution draft', save: 'Save solution', roof: /Estimate from the roof/, draw: 'Draw plane' },
    saved: /Saved to your account\./,
    drawStatus: 'The plane you drew is in the list.',
    refusal: 'Draw the plane on one roof: this one is too large or outside Germany.',
  },
  de: {
    path: '/de/loesungskonfigurator/',
    labels: { plz: /Postleitzahl des Standorts/, kwh: /Jahresverbrauch des Haushalts/, kwp: /^PV-Leistung/ },
    buttons: { calculate: 'System berechnen', add: 'Alles zum Lösungsentwurf hinzufügen', save: 'Lösung speichern', roof: /Noch keine PV-Leistung\? Aus dem Dach/, draw: 'Fläche zeichnen' },
    saved: /In Ihrem Konto gespeichert\./,
    drawStatus: 'Die gezeichnete Fläche steht in der Liste.',
    refusal: 'Zeichnen Sie die Fläche auf einem einzelnen Dach ein: Diese ist zu groß oder liegt außerhalb Deutschlands.',
  },
};

const record = { ticket: [484, 485], instance: 'w480', origin: BASE, snapshot: '20261021-1023', build, startedAt: new Date().toISOString(), runs: [] };

async function captureChrome(page) {
  // The sticky site header, step rail and mobile bar paint over the status
  // line; hide them for the captures (they still hold their layout space).
  await page.addStyleTag({ content: 'header#lc-header, .linker-steps, #linker-mobile-nav { visibility: hidden !important; }' });
}

async function dismiss(page) {
  for (const name of [/Reject all/, /Alle ablehnen/]) {
    const button = page.getByRole('button', { name });
    if (await button.count()) { await button.first().click(); await page.waitForTimeout(400); return; }
  }
}

async function saveFlow(browser, lang, width) {
  const conf = locales[lang];
  const page = await browser.newPage({ viewport: { width, height: width === 390 ? 844 : 1000 } });
  const reqs = [];
  page.on('request', (r) => { if (r.method() === 'POST' && /linker\/v1\/solutions/.test(r.url())) reqs.push(r.url()); });
  await page.goto(BASE + conf.path, { waitUntil: 'networkidle' });
  await dismiss(page);
  await captureChrome(page);
  await page.getByLabel(conf.labels.plz).fill(lang === 'de' ? '80331' : '80538');
  await page.getByLabel(conf.labels.kwh).fill('4500');
  await page.getByLabel(conf.labels.kwp).fill('10');
  await page.getByRole('button', { name: conf.buttons.calculate }).click();
  const add = page.getByRole('button', { name: conf.buttons.add });
  await add.waitFor({ timeout: 20000 });
  await add.click();
  await page.waitForTimeout(3000);
  const addStatus = (await page.locator('.linker-actions__status').textContent()).replace(/\s+/g, ' ').trim();
  if (!/solution draft\.$|Lösungsentwurf\.$/.test(addStatus)) {
    throw new Error('add did not settle: ' + JSON.stringify(addStatus));
  }
  await page.getByRole('button', { name: conf.buttons.save }).click();
  await page.getByText(conf.saved).waitFor({ timeout: 20000 });
  const status = (await page.locator('.linker-actions__status').textContent()).replace(/\s+/g, ' ').trim();
  const shot = `485-${lang}-${width}.png`;
  await page.locator('.linker-actions').scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  await page.locator('.linker-actions').screenshot({ path: `${OUT}/shots/${shot}` });
  const run = { fix: 485, lang, width, path: conf.path, status, saveRequests: reqs, shot };
  await page.close();
  return run;
}

async function roofFlow(browser, lang, width, refusal = false) {
  const conf = locales[lang];
  const page = await browser.newPage({ viewport: { width, height: width === 390 ? 844 : 1000 } });
  const reqs = [];
  page.on('response', (r) => { if (r.request().method() === 'POST' && /roof\/(pack|outline)/.test(r.url())) reqs.push(`${r.url().split('/engine/')[1]} ${r.status()}`); });
  await page.goto(BASE + conf.path, { waitUntil: 'networkidle' });
  await dismiss(page);
  await captureChrome(page);
  // The roof fixture is Triftstraße 5 at 80538, the same in both languages.
  await page.getByLabel(conf.labels.plz).fill('80538');
  await page.getByRole('button', { name: conf.buttons.roof }).click();
  await page.locator('.linker-roof').waitFor({ timeout: 20000 });
  const map = page.locator('.linker-roof__map');
  // Centre the map so the sticky header and step rail never cover a corner.
  await map.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
  await page.waitForTimeout(1500);
  const box = await map.boundingBox();
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;
  // Triftstraße 5 sits about 11 px west and 27 px north of the postcode
  // centre at zoom 17 (fixture outline against the place coordinate).
  await page.mouse.click(cx - 11, cy - 27);
  await page.locator('.linker-roof__status', { hasText: /Triftstraße 5/ }).waitFor({ timeout: 20000 });
  const selected = (await page.locator('.linker-roof__status').textContent()).trim();
  const planesBefore = await page.locator('.linker-planes li').count();
  const totalBefore = (await page.locator('.linker-roof__total').textContent()).trim();
  const afterSelect = reqs.slice();

  if (refusal) {
    // The refusal is about a plane over 3000 m²; the selection fitted the
    // map to the roof, so zoom out far enough for 200 px to exceed that.
    await page.mouse.move(cx, cy);
    for (let i = 0; i < 12; i++) {
      await page.mouse.wheel(0, 400);
      await page.waitForTimeout(120);
    }
    await page.waitForTimeout(1000);
  }
  await page.getByRole('button', { name: conf.buttons.draw }).click();
  // Clicking the button may scroll it into view; measure the map again.
  await map.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
  await page.waitForTimeout(600);
  const fresh = await map.boundingBox();
  const dx = fresh.x + fresh.width / 2;
  const dy = fresh.y + fresh.height / 2;
  const half = refusal ? 100 : 30;
  const corner = [dx - half, dy - half];
  for (const [x, y] of [[dx - half, dy - half], [dx + half, dy - half], [dx + half, dy + half], [dx - half, dy + half]]) {
    await page.mouse.click(x, y);
    await page.waitForTimeout(150);
  }
  // The closing click on the first corner: pack (and, before the fix, outline).
  await page.mouse.click(corner[0], corner[1]);
  await page.getByText(confusal(lang, refusal), { exact: false }).first().waitFor({ timeout: 20000 });
  await page.waitForTimeout(1200);
  const statusAfterFinish = (await page.locator('.linker-roof__status').textContent()).trim();
  const planesAfter = await page.locator('.linker-planes li').count();
  const totalAfter = (await page.locator('.linker-roof__total').textContent()).trim();
  const afterFinish = reqs.slice();

  // Capture the drawn state before the next click replaces it.
  const suffix = refusal ? 'refused' : 'drawn';
  const shot = `484-${suffix}-${lang}-${width}.png`;
  const panel = page.locator('.linker-roof__panel');
  await panel.evaluate((el) => el.scrollIntoView({ block: 'start', behavior: 'instant' }));
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/shots/${shot}` });
  let shotTotal = null;
  if (!refusal) {
    shotTotal = `484-${suffix}-${lang}-${width}-total.png`;
    await page.locator('.linker-roof__total').evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${OUT}/shots/${shotTotal}` });
  }

  let afterGenuine = null;
  if (!refusal) {
    // A new click on the roof is a selection again (a different pixel of the
    // same building); it must fire its own outline.
    await map.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await page.waitForTimeout(500);
    const again = await map.boundingBox();
    await page.mouse.click(again.x + again.width / 2 - 25, again.y + again.height / 2 - 35);
    await page.waitForTimeout(2000);
    afterGenuine = reqs.slice();
  }
  const run = { fix: 484, lang, width, refusal, path: conf.path, selected, planesBefore, totalBefore, afterSelect, statusAfterFinish, planesAfter, totalAfter, afterFinish, afterGenuine, shot, shotTotal };
  await page.close();
  return run;
}

function confusal(lang, refusal) {
  return refusal ? locales[lang].refusal : locales[lang].drawStatus;
}

const browser = await chromium.launch();
for (const lang of ['en', 'de']) {
  for (const width of [1440, 390]) {
    record.runs.push(await saveFlow(browser, lang, width));
  }
}
for (const lang of ['en', 'de']) {
  for (const width of [1440, 390]) {
    record.runs.push(await roofFlow(browser, lang, width));
  }
}
record.runs.push(await roofFlow(browser, 'en', 1440, true));
record.runs.push(await roofFlow(browser, 'de', 1440, true));
record.finishedAt = new Date().toISOString();
writeFileSync(`${OUT}/record.json`, JSON.stringify(record, null, 2) + '\n');
console.log(JSON.stringify(record.runs, null, 2));
await browser.close();
