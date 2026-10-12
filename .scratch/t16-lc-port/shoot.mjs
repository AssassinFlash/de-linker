import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');

const [, , outDir] = process.argv;
const shots = [
	// [label, url]
	['shop-en', 'http://127.0.0.1:8924/products/'],
	['archive-en', 'http://127.0.0.1:8924/product-category/inverters/'],
	['pdp-en', 'http://127.0.0.1:8924/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
	['pdp-en-scenes', 'http://127.0.0.1:8924/product/saj-hs2-6k-t2-x/'],
	['shop-de', 'http://127.0.0.1:8924/de/produkte/'],
	['pdp-de', 'http://127.0.0.1:8924/de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
	['pdp-de-scenes', 'http://127.0.0.1:8924/de/produkt/saj-hs2-6k-t2-x/'],
	['live-shop', 'https://de-linker.com/products/'],
	['live-pdp', 'https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
	['live-archive', 'https://de-linker.com/product-category/inverters/'],
	['live-pdp-scenes', 'https://de-linker.com/product/saj-hs2-6k-t2-x/'],
];

const browser = await chromium.launch({ channel: 'chromium' });
try {
	const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const page = await context.newPage();
	for (const [label, url] of shots) {
		const target = url.includes('de-linker.com') ? `${url}?cbq=${Date.now()}` : `${url}?cbq=${Date.now()}`;
		await page.goto(target, { waitUntil: 'networkidle', timeout: 60_000 }).catch(() => page.waitForTimeout(3000));
		await page.waitForTimeout(800);
		await page.screenshot({ path: `${outDir}/${label}.png`, fullPage: true });
		console.log(label, 'ok');
	}
} finally {
	await browser.close();
}
