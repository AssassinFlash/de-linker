// Real cold PDP entry; fail one shipped script, then retry the existing loader.
// Genie REST is a local fixture, never a model call.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdir, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const out = dirname(fileURLToPath(import.meta.url));
const repo = resolve(out, '../../../..');
const {chromium} = createRequire(resolve(repo, 'plugins/linker-tools/package.json'))('playwright');
const phase = process.argv[2] || 'retry-after';
const browser = await chromium.launch({channel: 'chromium'});
const results = [];
await mkdir(out, {recursive: true});
for (const mode of ['app', 'dependency']) {
  console.log(`START retry ${mode}`);
  const context = await browser.newContext({viewport: {width: 390, height: 844}, serviceWorkers: 'block'});
  const page = await context.newPage();
  const posts = [];
  let failures = 0;
  let appLoads = 0;
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/genie.js*', async route => {
    appLoads++;
    if (mode === 'app' && failures === 0) { failures++; await route.abort('failed'); }
    else await route.continue();
  });
  await page.route('**/wp-includes/js/dist/element.min.js*', async route => {
    if (mode === 'dependency' && failures === 0) { failures++; await route.abort('failed'); }
    else await route.continue();
  });
  await page.route('**/linker-ai/v1/genie/**', async route => {
    if (route.request().url().includes('/conversation')) { await route.fulfill({json: {messages: [], stream: ''}}); return; }
    posts.push(route.request().postDataJSON());
    await route.fulfill({json: {stream: 'event: meta\ndata: {"turn_id":1,"grounded":true,"fallback":false,"attempts":1,"failures":[],"language":"en"}\n\nevent: block\ndata: {"type":"text","text":"Retry fixture answer.","refs":[]}\n\nevent: done\ndata: {"ok":true}\n\n'}});
  });
  try {
    const response = await page.goto('http://127.0.0.1:8984/product/goodwe-gw60k-sts-g10/?cbq=' + Date.now(), {waitUntil: 'domcontentloaded'});
    assert.equal(response.status(), 200);
    const trigger = page.locator('[data-pdp-ask]').first();
    const question = await trigger.getAttribute('data-ask-message');
    await trigger.click();
    const error = page.locator('[data-linker-genie-load-error]');
    await error.waitFor({state: 'visible', timeout: 3000});
    assert.equal(failures, 1);
    assert.equal(posts.length, 0);
    await page.screenshot({path: resolve(out, `${phase}-${mode}-failed.png`)});
    // Retry the same loader, without issuing another product ask.
    await error.locator('[data-linker-genie-open]').click();
    await page.locator('.linker-genie-app__composer').waitFor({state: 'visible', timeout: 5000});
    await page.waitForFunction(() => document.querySelectorAll('.linker-genie-app__votes').length === 1);
    assert.equal(posts.length, 1);
    assert.equal(posts[0].messages.at(-1).content, question, 'original question survives failure and retry');
    assert.equal(await error.count(), 0);
    assert.equal(appLoads, mode === 'app' ? 2 : 1);
    assert.deepEqual(errors, [], 'failed dependency never executes a broken app');
    await page.screenshot({path: resolve(out, `${phase}-${mode}-recovered.png`)});
    await page.locator('.linker-genie-app__toggle').click();
    assert.equal(await page.locator('.linker-genie-app').isVisible(), false);
    await trigger.click();
    await page.waitForFunction(() => document.querySelectorAll('.linker-genie-app__votes').length === 2);
    assert.equal(posts.length, 2, 'one subsequent explicit ask');
    assert.equal(appLoads, mode === 'app' ? 2 : 1, 'success never loads a second app');
    results.push({mode, pass: true, appLoads, failures, posts});
    console.log(`PASS retry ${mode}`);
  } catch (error) {
    results.push({mode, pass: false, message: error.message, errors, appLoads, failures, posts});
    await page.screenshot({path: resolve(out, `${phase}-${mode}-unrecovered.png`)});
    console.log(`FAIL retry ${mode}: ${error.message}`);
  } finally { await context.close(); }
}
await browser.close();
await writeFile(resolve(out, `${phase}-results.json`), JSON.stringify(results, null, 2) + '\n');
assert.ok(results.every(result => result.pass));
