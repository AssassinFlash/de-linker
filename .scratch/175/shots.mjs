/**
 * Self-verification shots for ticket #175: the blog index, the search face and
 * the category archive, EN and DE, at 1440 and 390. Same browser and settle
 * protocol for the before and the after run, so the pair is comparable:
 * lazy images loaded by a full scroll to the bottom and back, fonts ready,
 * animations off, then the full-page shot.
 *
 *   node .scratch/175/shots.mjs <out-dir> [base-url]
 */

import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';

const require = createRequire(
	'/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-blogs/tests/e2e/package.json'
);
const { chromium } = require('playwright');

const base = process.argv[3] ?? 'http://127.0.0.1:9027';
const out = process.argv[2] ?? '.';
mkdirSync(out, { recursive: true });

const faces = [
	{ name: 'blog-en', path: '/blog/', marker: 'tv-blog-index-v1' },
	{ name: 'blog-de', path: '/de/blog/', marker: 'tv-blog-index-v1' },
	{ name: 'search-en', path: '/?s=inverter', marker: 'tv-blog-search-v1' },
	{ name: 'search-de', path: '/de/?s=wechselrichter', marker: 'tv-blog-search-v1' },
	{ name: 'category-en', path: '/category/system-design/', marker: 'tv-blog-category-v1' },
	{ name: 'category-de', path: '/de/category/system-design/', marker: 'tv-blog-category-v1' },
];

const viewports = [
	{ suffix: '1440', width: 1440, height: 1000 },
	{ suffix: '390', width: 390, height: 844 },
];

const settle = async (page) => {
	await page.addStyleTag({
		content:
			'*,*::before,*::after{animation:none!important;transition:none!important}' +
			'html{scroll-behavior:auto!important}',
	});
	// Lazy images below the fold only load when they enter the viewport.
	await page.evaluate(async () => {
		const step = window.innerHeight;
		for (let y = 0; y < document.body.scrollHeight; y += step) {
			window.scrollTo(0, y);
			await new Promise((resolve) => setTimeout(resolve, 60));
		}
		window.scrollTo(0, 0);
	});
	await page.evaluate(
		async () =>
			await Promise.race([
				(async () => {
					await document.fonts.ready;
					await Promise.all(
						Array.from(document.images)
							.filter((image) => !image.complete)
							.map(
								(image) =>
									new Promise((resolve) => {
										image.addEventListener('load', resolve, { once: true });
										image.addEventListener('error', resolve, { once: true });
									})
							)
					);
				})(),
				new Promise((resolve) => setTimeout(resolve, 20_000)),
			])
	);
	await page.waitForTimeout(400);
};

const browser = await chromium.launch();
const report = [];
for (const face of faces) {
	for (const viewport of viewports) {
		const context = await browser.newContext({
			viewport: { width: viewport.width, height: viewport.height },
			deviceScaleFactor: 1,
			reducedMotion: 'reduce',
		});
		const page = await context.newPage();
		const file = `${out}/${face.name}-${viewport.suffix}.png`;
		try {
			const response = await page.goto(base + face.path, {
				waitUntil: 'load',
				timeout: 60_000,
			});
			await settle(page);
			const html = await page.content();
			const seen = html.includes(face.marker);
			await page.screenshot({ path: file, fullPage: true });
			report.push({
				shot: `${face.name}-${viewport.suffix}`,
				status: response ? response.status() : 0,
				marker: seen,
				file,
			});
			console.log(
				`${face.name}-${viewport.suffix}: http ${response ? response.status() : 0}, ${face.marker} ${seen ? 'present' : 'MISSING'}`
			);
		} catch (error) {
			report.push({ shot: `${face.name}-${viewport.suffix}`, status: 0, marker: false, error: String(error) });
			console.log(`${face.name}-${viewport.suffix}: FAILED ${error}`);
		}
		await context.close();
	}
}
await browser.close();
writeFileSync(`${out}/shots.json`, `${JSON.stringify(report, null, 2)}\n`);
console.log(`report: ${out}/shots.json`);
if (report.some((row) => !row.marker)) {
	process.exitCode = 1;
}
