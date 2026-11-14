#!/usr/bin/env node
/*
 * Measure the rendered width of every <img> on a set of pages at the site's
 * real breakpoints, so the srcset pass can state each image's box instead of
 * guessing one global rule.
 *
 * Usage: node measure-image-boxes.mjs <out.json> <url>...
 *
 * Production 2026-11-14: 22 pages carry hand-written <img> tags with no
 * srcset, so the browser downloads 2-13x the pixels it displays. A sizes
 * attribute is only correct when it describes the real box, hence this pass.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';

const BREAKPOINTS = [390, 600, 768, 1024, 1280, 1440];
const COOKIE = {
	name: 'cookieyes-consent',
	value: 'consentid:s,consent:yes,action:yes,necessary:yes,functional:no,analytics:no,performance:no,advertisement:no',
	domain: 'de-linker.com',
	path: '/',
};

const out = process.argv[2];
const urls = process.argv.slice(3);
if (!out || urls.length === 0) {
	console.error('usage: node measure-image-boxes.mjs <out.json> <url>...');
	process.exit(2);
}

const browser = await chromium.launch();
const result = {};

for (const url of urls) {
	const perWidth = {};
	for (const width of BREAKPOINTS) {
		const context = await browser.newContext({
			viewport: { width, height: 900 },
		});
		await context.addCookies([COOKIE]);
		const page = await context.newPage();
		try {
			await page.goto(url, { waitUntil: 'networkidle', timeout: 120000 });
			await page.addStyleTag({
				content:
					'.cky-consent-container,.cky-revisit-bottom-left,#wpadminbar{display:none!important}',
			});
			await page.evaluate(async () => {
				await document.fonts.ready;
				for (const image of document.images) image.loading = 'eager';
			});
			// Lazy images report 0 width until they enter the viewport.
			await page.evaluate(async () => {
				const height = document.body.scrollHeight;
				for (let y = 0; y < height; y += 700) {
					window.scrollTo(0, y);
					await new Promise((r) => setTimeout(r, 60));
				}
				window.scrollTo(0, 0);
			});
			await page.waitForTimeout(1500);
			perWidth[width] = await page.evaluate(() =>
				[...document.images].map((image) => ({
					src: image.getAttribute('src') || '',
					dw: Math.round(image.getBoundingClientRect().width),
					hasSrcset: Boolean(image.getAttribute('srcset')),
				}))
			);
		} catch (error) {
			perWidth[width] = { error: String(error).slice(0, 120) };
		}
		await context.close();
	}
	result[url] = perWidth;
}

await browser.close();
fs.writeFileSync(out, JSON.stringify(result, null, 1));
console.log('wrote', out, 'pages:', Object.keys(result).length);
