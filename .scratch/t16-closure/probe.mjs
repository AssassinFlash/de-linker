import { createRequire } from 'node:module';
import path from 'node:path';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const [, , url, expr] = process.argv;
const browser = await chromium.launch({ channel: 'chromium' });
try {
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  await page.goto(url, { waitUntil: 'networkidle', timeout: 90000 }).catch(()=>{});
  await page.waitForTimeout(2000);
  const out = await page.evaluate(e => eval(e), expr);
  console.log(typeof out === 'string' ? out : JSON.stringify(out, null, 1));
} finally { await browser.close(); }
