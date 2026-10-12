import { createRequire } from 'node:module';
import path from 'node:path';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const [, , url] = process.argv;
const browser = await chromium.launch({ channel: 'chromium' });
const script = () => {
  const cs = getComputedStyle;
  const tabs = document.querySelector('.pdp-info-tabs');
  const btns = Array.from(document.querySelectorAll('.pdp-info-tabs button'));
  const rows = Array.from(document.querySelectorAll('.pdp-info-panel .pdp-stat-row')).slice(0, 2);
  const out = {
    tabs: { w: tabs.getBoundingClientRect().width, h: tabs.getBoundingClientRect().height, wrap: cs(tabs).flexWrap, bg: cs(tabs).backgroundColor, radius: cs(tabs).borderRadius, pad: cs(tabs).padding, gap: cs(tabs).gap },
    buttons: btns.map(b => ({ w: +b.getBoundingClientRect().width.toFixed(1), h: +b.getBoundingClientRect().height.toFixed(1), bg: cs(b).backgroundColor, color: cs(b).color, fs: cs(b).fontSize, fw: cs(b).fontWeight, radius: cs(b).borderRadius, pad: cs(b).padding, sel: b.getAttribute('aria-selected'), text: b.textContent })),
    panel: (() => { const p = document.querySelector('.pdp-info-panel'); return { mt: cs(p).marginTop, w: p.getBoundingClientRect().width }; })(),
    rows: rows.map(r => ({ h: +r.getBoundingClientRect().height.toFixed(1), pad: cs(r).padding, border: cs(r).borderBottom, fs: cs(r).fontSize, color: cs(r).color })),
  };
  return out;
};
for (const width of [1440, 390]) {
  const page = await (await browser.newContext({ viewport: { width, height: 900 } })).newPage();
  await page.goto(url, { waitUntil: 'networkidle', timeout: 90000 }).catch(()=>{});
  await page.waitForTimeout(2000);
  console.log('=== width', width, JSON.stringify(await page.evaluate(script)));
  await page.close();
}
await browser.close();
