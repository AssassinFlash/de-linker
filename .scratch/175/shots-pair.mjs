/**
 * The live|local pair of the blog faces: same browser, same viewports, same
 * settle protocol as shots.mjs, shot against the instance and the live site so
 * the two images of a pair are comparable pixel by pixel.
 *
 *   node .scratch/175/shots-pair.mjs <out-dir> <language> [instance] [live]
 *
 * <language> is `de` or `en`. Shots are written
 * `<face>-<language>-<viewport>-local.png` / `-live.png`; the pairs committed
 * for #175 were produced with
 *
 *   node .scratch/175/shots-pair.mjs .scratch/175/pair-de de
 *   node .scratch/175/shots-pair.mjs .scratch/175/pair-en en
 */

import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';

const require = createRequire(
	'/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-blogs/tests/e2e/package.json'
);
const { chromium } = require('playwright');

const out = process.argv[2];
const language = process.argv[3] ?? 'de';
const bases = [
	['local', process.argv[4] ?? 'http://127.0.0.1:9027'],
	['live', process.argv[5] ?? 'https://de-linker.com'],
];
mkdirSync(out, { recursive: true });

const paths = {
	de: {
		blog: '/de/blog/',
		search: '/de/?s=wechselrichter',
		category: '/de/category/system-design/',
	},
	en: {
		blog: '/blog/',
		search: '/?s=inverter',
		category: '/category/system-design/',
	},
}[language];
const faces = Object.entries(paths).map(([face, path]) => ({
	name: `${face}-${language}`,
	path,
}));

const settle = async (page) => {
	await page.addStyleTag({
		content:
			'*,*::before,*::after{animation:none!important;transition:none!important}' +
			'html{scroll-behavior:auto!important}',
	});
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
for (const face of faces) {
	for (const [suffix, width, height] of [
		['1440', 1440, 1000],
		['390', 390, 844],
	]) {
		for (const [tag, base] of bases) {
			const context = await browser.newContext({
				viewport: { width, height },
				deviceScaleFactor: 1,
				reducedMotion: 'reduce',
			});
			const page = await context.newPage();
			try {
				const response = await page.goto(base + face.path, {
					waitUntil: 'load',
					timeout: 90_000,
				});
				await settle(page);
				await page.screenshot({
					path: `${out}/${face.name}-${suffix}-${tag}.png`,
					fullPage: true,
				});
				console.log(
					`${face.name}-${suffix}-${tag}: http ${response?.status() ?? 0}`
				);
			} catch (error) {
				console.log(`${face.name}-${suffix}-${tag}: FAILED ${error}`);
				process.exitCode = 1;
			}
			await context.close();
		}
	}
}
await browser.close();
