import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const [, , url, sel, out] = process.argv;
const browser = await chromium.launch({ channel: 'chromium' });
try {
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  await page.goto(url, { waitUntil: 'networkidle', timeout: 90000 }).catch(()=>{});
  await page.waitForTimeout(2500);
  const html = await page.evaluate((s) => { const el = document.querySelector(s); return el ? el.outerHTML : 'NOT FOUND'; }, sel);
  fs.writeFileSync(out, html);
  console.log('wrote', out, html.length);
} finally { await browser.close(); }
