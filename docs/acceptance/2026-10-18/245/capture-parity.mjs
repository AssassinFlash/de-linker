// Run from this worktree: node docs/acceptance/2026-10-18/245/capture-parity.mjs
// Read-only live comparison of the existing account login design; no live sign-in.
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, join } from 'node:path';
const directory = dirname(fileURLToPath(import.meta.url));
const repo = resolve(directory, '../../../..');
const { chromium } = createRequire(join(repo, 'tests/e2e/package.json'))('playwright');
const browser = await chromium.launch();
try {
  for (const width of [1440, 390]) {
    for (const language of ['en', 'de']) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
      const page = await context.newPage();
      for (const [site, origin] of [['live', 'https://de-linker.com'], ['local', 'http://127.0.0.1:9096']]) {
        await page.goto(origin + (language === 'de' ? '/de/mein-konto/' : '/my-account/'), { waitUntil: 'networkidle' });
        await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}' });
        await page.evaluate(async () => {
          await document.fonts.ready;
          await Promise.all(Array.from(document.images).filter(image => image.getClientRects().length > 0).map(image => { image.loading = 'eager'; return image.decode().catch(() => {}); }));
        });
        await page.screenshot({ path: join(directory, `parity-${site}-${language}-${width}.png`), fullPage: true, animations: 'disabled' });
      }
      await context.close();
    }
  }
} finally { await browser.close(); }
