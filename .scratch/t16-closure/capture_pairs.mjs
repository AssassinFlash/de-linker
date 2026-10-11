// Paired live|t16 full-page screenshots: one browser, one machine, identical
// viewport and wait protocol for both sides. Usage:
//
//   node capture_pairs.mjs <out-dir>
//
// Writes <page>-<lang>-<width>-<side>.png for side in {live,t16}.
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');

const out = process.argv[2] || path.join(repo, '.scratch/t16-closure/pairs');
fs.mkdirSync(out, { recursive: true });

const PAGES = [
	{ name: 'shop', live: 'https://de-linker.com/products/', t16: 'http://127.0.0.1:8924/products/', de: 'de/produkte/' },
	{ name: 'archive', live: 'https://de-linker.com/product-category/inverters/', t16: 'http://127.0.0.1:8924/product-category/inverters/', de: 'de/produkt-kategorie/wechselrichter/' },
	{ name: 'pdp', live: 'https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/', t16: 'http://127.0.0.1:8924/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/', de: 'de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/' },
];

const WIDTHS = [1440, 390];

const browser = await chromium.launch({ channel: 'chromium' });

async function shoot(url, file, width) {
	const context = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 } });
	const page = await context.newPage();
	const target = url.includes('?') ? url : url + '?cbq=' + Date.now();
	await page.goto(target, { waitUntil: 'networkidle', timeout: 90_000 }).catch(() => page.waitForTimeout(4000));
	await page.waitForTimeout(1200);
	// Walk the page so lazy images decode, then return to the top.
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
	await page.waitForTimeout(1200);
	await page.screenshot({ path: file, fullPage: true });
	const box = await page.evaluate(() => ({ w: document.documentElement.scrollWidth, h: document.body.scrollHeight }));
	await context.close();
	return box;
}

for (const spec of PAGES) {
	for (const lang of ['en', 'de']) {
		for (const width of WIDTHS) {
			const liveUrl = lang === 'en' ? spec.live : spec.live.replace('/product/', '/de/produkt/').replace('/products/', '/de/produkte/').replace('/product-category/inverters/', '/de/produkt-kategorie/wechselrichter/');
			const t16Url = 'http://127.0.0.1:8924/' + (lang === 'en' ? spec.t16.replace('http://127.0.0.1:8924/', '') : spec.de);
			const base = `${spec.name}-${lang}-${width}`;
			const liveBox = await shoot(liveUrl, path.join(out, `${base}-live.png`), width);
			const t16Box = await shoot(t16Url, path.join(out, `${base}-t16.png`), width);
			console.log(base, 'live', JSON.stringify(liveBox), 't16', JSON.stringify(t16Box));
		}
	}
}
await browser.close();
console.log('done');
