// Real snapshot pages and shipped JS. Only Genie REST responses are fixtures:
// this verifies the entry protocol, not a model's answer or grounding quality.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdir, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const out = dirname(fileURLToPath(import.meta.url));
const repo = resolve(out, '../../../..');
const {chromium} = createRequire(resolve(repo, 'plugins/linker-tools/package.json'))('playwright');
const base = process.env.GENIE_ENTRY_BASE || 'http://127.0.0.1:8984';
assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
const phase = process.argv[2] || 'after';
const smoke = process.argv.includes('--smoke');
const browser = await chromium.launch({channel: 'chromium'});
const results = [];
await mkdir(out, {recursive: true});

const scenarios = smoke
  ? [{locale: 'en', width: 1440, entry: 'bubble'}, {locale: 'en', width: 1440, entry: 'pdp'}, {locale: 'en', width: 390, entry: 'shop'}]
  : ['en', 'de'].flatMap(locale => [1440, 390].flatMap(width =>
      ['pdp', 'shop', 'search', ...(width === 1440 ? ['bubble'] : [])].map(entry => ({locale, width, entry}))));

for (const scenario of scenarios) {
  const {locale, width, entry} = scenario;
  const name = `${locale}-${width}-${entry}`;
  console.log(`START ${name}`);
  const context = await browser.newContext({viewport: {width, height: width === 390 ? 844 : 900}, serviceWorkers: 'block'});
  const page = await context.newPage();
  const posts = [];
  let appLoads = 0;
  let releaseApp;
  const appGate = new Promise(resolve => { releaseApp = resolve; });
  let releaseRestore;
  const restoreGate = new Promise(resolve => { releaseRestore = resolve; });
  let restoreStarted = false;
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/genie.js*', async route => {
    appLoads += 1;
    await appGate;
    await route.continue();
  });
  await page.route('**/linker-ai/v1/genie/**', async route => {
    const request = route.request();
    if (request.url().includes('/conversation')) {
      restoreStarted = true;
      await restoreGate;
      // A deliberately late old thread must not overwrite the new first ask.
      await route.fulfill({json: {messages: entry === 'pdp' ? [{role: 'user', content: 'Old fixture question'}] : [], stream: ''}});
      return;
    }
    assert.equal(request.method(), 'POST');
    const body = request.postDataJSON();
    posts.push(body);
    const text = locale === 'de' ? 'Antwort der Eingangs-Testfixture.' : 'Entry fixture response.';
    const stream = `event: meta\ndata: ${JSON.stringify({turn_id: posts.length, grounded: true, fallback: false, attempts: 1, failures: [], language: locale})}\n\nevent: block\ndata: ${JSON.stringify({type: 'text', text, refs: []})}\n\nevent: done\ndata: {"ok":true}\n\n`;
    await route.fulfill({json: {conversation_id: 1, stream}});
  });
  try {
    const product = entry === 'pdp' || entry === 'bubble';
    const path = product ? `/${locale === 'de' ? 'produkt' : 'product'}/goodwe-gw60k-sts-g10/` : `/${locale === 'de' ? 'produkte' : 'products'}/`;
    await page.goto(`${base}${locale === 'de' ? '/de' : ''}${path}?cbq=${Date.now()}`, {waitUntil: 'domcontentloaded'});
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('.linker-genie-app').count(), 0, 'fresh page must be lazy');
    assert.equal(appLoads, 0);
    let question = '';
    let trigger;
    if (entry === 'bubble') {
      trigger = page.locator('.linker-genie-open');
    } else if (entry === 'pdp') {
      trigger = page.locator('[data-pdp-ask]').first();
      question = await trigger.getAttribute('data-ask-message');
      assert.ok(question?.trim(), 'real PDP question exists');
    } else if (entry === 'search') {
      question = locale === 'de' ? 'Welcher Wechselrichter passt zu meinem Haus?' : 'Which inverter fits my home?';
      await page.locator('#search-box').fill(question);
      // Desktop uses the visible search chip; mobile submits the actual search
      // form because the desktop chip is hidden by the approved page layout.
      trigger = width === 1440 ? page.locator('[data-linker-ask-genie]') : page.locator('#search-box').locator('..').locator('button[type="submit"]');
    } else {
      trigger = page.locator('.linker-genie-chip:visible').first();
    }
    await trigger.click();
    await page.waitForFunction(() => [...document.scripts].some(script => /\/genie\.js/.test(script.src)), undefined, {timeout: 2500});
    // While the first click is still loading, an ordinary reopen must not
    // replace the queued question or cause a second bundle/request.
    if (width === 1440 && entry === 'pdp') await page.locator('.linker-genie-open').click();
    releaseApp();
    await page.locator('.linker-genie-app__composer').waitFor({state: 'visible', timeout: 5000});
    await page.waitForFunction(() => document.querySelector('.linker-genie-open')?.getAttribute('aria-expanded') === 'true');
    assert.equal(appLoads, 1, 'only one application load');
    await page.waitForFunction(() => document.querySelector('.linker-genie-app__disclosure'));
    assert.ok(restoreStarted, 'real app restores the thread');
    assert.equal(posts.length, 0, 'first ask waits for stored history');
    releaseRestore();
    if (question) {
      await page.waitForFunction(() => document.querySelectorAll('.linker-genie-app__votes').length === 1);
      assert.equal(posts.length, 1, 'one first question, one POST');
      assert.equal(posts[0].messages.at(-1).content, question);
      assert.equal(posts[0].locale, locale);
      assert.equal(posts[0].page.type, entry === 'pdp' ? 'product' : 'category');
    } else {
      assert.equal(posts.length, 0, 'opening is not an unsolicited question');
    }
    await page.waitForTimeout(150);
    if (question) {
      assert.equal(await page.locator('.linker-genie-app__message--user').last().innerText(), question, 'late restore preserves history and appends the first ask');
      assert.equal(await page.locator('.linker-genie-app__message--user').count(), entry === 'pdp' ? 2 : 1);
      if (entry === 'pdp') assert.equal(posts[0].messages[0].content, 'Old fixture question');
    }
    const skin = await page.locator('.linker-genie-app').evaluate(app => {
      const style = getComputedStyle(app), box = app.getBoundingClientRect();
      return {background: style.backgroundColor, border: style.borderTopColor, radius: style.borderRadius, maxHeight: style.maxHeight, rect: [box.x, box.y, box.width, box.height], viewport: [innerWidth, innerHeight], surfaceToken: getComputedStyle(document.documentElement).getPropertyValue('--proto-color-surface').trim(), lineToken: getComputedStyle(document.documentElement).getPropertyValue('--proto-color-line').trim()};
    });
    if (width === 390) {
      assert.equal(skin.background, 'rgb(255, 255, 255)');
      assert.equal(skin.border, 'rgb(226, 229, 229)');
      assert.equal(skin.radius, '14px');
      assert.ok(skin.rect[2] > 0 && skin.rect[3] > 100, 'mobile card contains conversation, not an empty box');
      assert.ok(skin.rect[3] <= Math.ceil(844 * .72));
    }
    await page.screenshot({path: resolve(out, `${phase}-${name}-first-open.png`)});
    await page.locator('.linker-genie-app__toggle').click();
    await page.waitForFunction(() => document.querySelector('.linker-genie-open')?.getAttribute('aria-expanded') === 'false');
    assert.equal(await page.locator('.linker-genie-app__composer').count(), 0);
    if (width === 390) assert.equal(await page.locator('.linker-genie-app').isVisible(), false, 'Hide removes the mobile card');
    if (entry === 'pdp' || entry === 'bubble') assert.equal(await page.locator('.linker-genie-app__bar').isVisible(), false, 'C1 closed PDP bar stays hidden');
    await page.screenshot({path: resolve(out, `${phase}-${name}-hidden.png`)});
    const before = posts.length;
    await trigger.click();
    await page.locator('.linker-genie-app__composer').waitFor({state: 'visible'});
    if (question) {
      await page.waitForFunction(() => document.querySelectorAll('.linker-genie-app__votes').length === 2);
      assert.equal(posts.length, before + 1, 'one explicit second ask, not a replay of the queued first ask');
      assert.equal(posts[1].messages.filter(message => message.role === 'user').length, entry === 'pdp' ? 3 : 2);
    } else assert.equal(posts.length, before, 'plain reopen sends no request');
    assert.equal(appLoads, 1, 'reopen keeps one React application');
    await page.screenshot({path: resolve(out, `${phase}-${name}-reopened.png`)});
    assert.deepEqual(errors, []);
    results.push({name, pass: true, appLoads, posts, skin});
    console.log(`PASS ${name}: ${appLoads} bundle, ${posts.length} turn POST(s)`);
  } catch (error) {
    releaseApp(); releaseRestore();
    await page.screenshot({path: resolve(out, `${phase}-${name}-failed.png`)});
    results.push({name, pass: false, error: error.message, appLoads, posts, errors});
    console.log(`FAIL ${name}: ${error.message}`);
  } finally {
    await context.close();
  }
}
await browser.close();
await writeFile(resolve(out, `${phase}-results.json`), JSON.stringify({base, phase, scope: 'entry protocol only; REST fixtures, no model calls', results}, null, 2) + '\n');
assert.ok(results.every(result => result.pass), 'all entry scenarios pass');
