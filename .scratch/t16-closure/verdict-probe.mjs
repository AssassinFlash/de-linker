// Facts probe for the replication items under review. Usage:
//   node verdict-probe.mjs <url> [selector ...]
// Prints a JSON line per selector with geometry + the computed properties the
// review items concern, plus a screenshot of the element when --shot is given.
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');

const [, , url, ...rest] = process.argv;
const shot = rest.includes('--shot');
const selectors = rest.filter((s) => s !== '--shot');
const outDir = path.join(repo, '.scratch/t16-closure/inspect');
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ channel: 'chromium' });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
await page.goto(url.includes('?') ? url : url + '?cbq=' + Date.now(), { waitUntil: 'networkidle', timeout: 90_000 }).catch(() => page.waitForTimeout(4000));
await page.evaluate(async () => {
	await new Promise((resolve) => {
		let total = 0;
		const step = () => {
			window.scrollTo(0, total);
			total += 700;
			if (total < document.body.scrollHeight + 700) setTimeout(step, 50);
			else resolve();
		};
		step();
	});
	window.scrollTo(0, 0);
});
await page.waitForTimeout(800);

const facts = await page.evaluate((sels) => {
	const out = {};
	for (const sel of sels) {
		const els = Array.from(document.querySelectorAll(sel));
		out[sel] = els.slice(0, 4).map((el) => {
			const st = getComputedStyle(el);
			const r = el.getBoundingClientRect();
			return {
				rect: [Math.round(r.x), Math.round(r.y + window.scrollY), Math.round(r.width), Math.round(r.height)],
				display: st.display,
				color: st.color,
				bg: st.backgroundColor,
				fs: st.fontSize,
				fw: st.fontWeight,
				lh: st.lineHeight,
				radius: st.borderTopLeftRadius,
				overflow: st.overflow,
				overflowY: st.overflowY,
				visibility: st.visibility,
				opacity: st.opacity,
				overflowHidden: !!el.closest('[style*="overflow"], .pdp-buy-inner'),
				clientH: el.clientHeight,
				scrollH: el.scrollHeight,
				text: (el.textContent || '').trim().slice(0, 60),
				imgWH: el.tagName === 'IMG' ? [el.naturalWidth, el.naturalHeight] : undefined,
				cls: (el.getAttribute('class') || '').slice(0, 60),
			};
		});
	}
	const bodyBg = getComputedStyle(document.body).backgroundColor;
	const htmlBg = getComputedStyle(document.documentElement).backgroundColor;
	const shop = document.querySelector('#tv-woo-b2b-catalog');
	const compareCount = document.querySelectorAll('.card-compare-checkbox, [data-compare-article]').length;
	return { facts: out, bodyBg, htmlBg, docW: document.documentElement.scrollWidth, compareCount, path: location.pathname };
}, selectors);

console.log(JSON.stringify(facts, null, 1).slice(0, 12000));
if (shot) {
	for (const sel of selectors) {
		const el = await page.$(sel);
		if (el) {
			const name = sel.replace(/[^a-z0-9]+/gi, '_').slice(0, 40) + '-' + (url.includes('de-linker.com') ? 'live' : 'local') + '.png';
			await el.screenshot({ path: path.join(outDir, name) }).catch(() => {});
			console.log('shot:', path.join(outDir, name));
		}
	}
}
await browser.close();
