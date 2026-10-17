/**
 * Shared full-page capture + exact RGB comparison. See README.md for usage.
 * Capture conditions preserve the measured repeatable setup in the site's
 * acceptance records: software raster, sRGB, decoded images/fonts, no motion.
 */
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { execFileSync } from 'node:child_process';

const here = path.dirname(fileURLToPath(import.meta.url));
const { chromium } = createRequire(path.join(here, '../e2e/package.json'))(
	'playwright'
);
const { values, positionals } = parseArgs({
	allowPositionals: true,
	options: {
		widths: { type: 'string' },
		paths: { type: 'string' },
		'allow-header': { type: 'string', multiple: true, default: [] },
	},
});
const [out, liveBase, localBase] = positionals;
if (!out || !liveBase || !localBase || !values.widths || !values.paths) {
	throw new Error(
		'usage: node tests/visual/pixel-parity.mjs <outdir> <live-base> <local-base> --widths <comma-list> --paths <comma-list> [--allow-header <path>:<widths>:<height>]'
	);
}
const widths = values.widths.split(',').map(Number);
const paths = values.paths.split(',');
const allowedHeaderChanges = values['allow-header'].map((rule) => {
	const [route, widthList, height] = rule.split(':');
	return {
		path: route,
		widths: widthList.split(',').map(Number),
		height: Number(height),
	};
});
fs.mkdirSync(out, { recursive: true });
const cases = [];
for (const width of widths) {
	for (const route of paths) {
		const stem =
			route.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'home';
		let language;
		let headerHeight;
		for (const [base, label] of [
			[liveBase, 'live'],
			[localBase, 'local'],
		]) {
			// GPU dithering produced 24,117 differing pixels on identical pages;
			// software raster + sRGB eliminated it. One browser per capture.
			const browser = await chromium.launch({
				channel: 'chromium',
				args: [
					'--disable-gpu',
					'--force-color-profile=srgb',
					'--disable-partial-raster',
					'--disable-gpu-rasterization',
				],
			});
			try {
				// 900px is the established desktop/mobile acceptance viewport height.
				const context = await browser.newContext({
					viewport: { width, height: 900 },
					reducedMotion: 'reduce',
					deviceScaleFactor: 1,
				});
				await context.addInitScript(() => {
					// Exercise the page at rest during the full-page scroll, without
					// the preview card's 8s dwell. Only this disposable browser stores it.
					localStorage.setItem(
						'linker-genie-peek-dismissed-until',
						String(Date.now() + 30 * 86400000)
					);
				});
				const page = await context.newPage();
				// The existing snapshot capture budget also covers live lazy media.
				await page.goto(base + route, {
					waitUntil: 'networkidle',
					timeout: 120000,
				});
				await page.addStyleTag({
					content:
						'*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}',
				});
				await page.evaluate(async () => {
					// Overlapping 600px scroll steps with 120ms for lazy-load observers
					// are the established full-page capture procedure.
					for (let y = 0; y < document.body.scrollHeight; y += 600) {
						window.scrollTo(0, y);
						await new Promise((resolve) =>
							setTimeout(resolve, 120)
						);
					}
					window.scrollTo(0, 0);
				});
				// sizes="auto" images select again at full height. Set that height,
				// request eagerly, then decode before the full-page screenshot.
				const full = await page.evaluate(
					() => document.documentElement.scrollHeight
				);
				await page.setViewportSize({ width, height: full });
				await page.waitForLoadState('networkidle');
				await page.evaluate(async () => {
					document
						.querySelectorAll('img[loading="lazy"]')
						.forEach((img) => {
							img.loading = 'eager';
						});
					await Promise.all(
						[...document.images].map((img) =>
							img.decode().catch(() => {})
						)
					);
				});
				await page.waitForLoadState('networkidle');
				await page.evaluate(async () => {
					await Promise.all(
						[...document.images].map((img) =>
							img.decode().catch(() => {})
						)
					);
					await document.fonts.ready;
				});
				// Existing capture setup settles fonts/layout for 800ms after decode.
				await page.waitForTimeout(800);
				const metadata = await page.evaluate(() => ({
					language: document.documentElement.lang.split(/[-_]/)[0],
					headerHeight: Math.ceil(
						document
							.querySelector('#lc-header')
							.getBoundingClientRect().height
					),
				}));
				if (label === 'live') ({ language, headerHeight } = metadata);
				const name = `${stem}-${width}-${label}.png`;
				await page.screenshot({
					path: path.join(out, name),
					fullPage: true,
				});
				console.log(name);
			} finally {
				await browser.close();
			}
		}
		cases.push({ path: route, stem, width, language, headerHeight });
	}
}
fs.writeFileSync(
	path.join(out, 'capture.json'),
	JSON.stringify({ cases, allowedHeaderChanges }, null, 2) + '\n'
);
execFileSync('python3', [path.join(here, 'compare.py'), out], {
	stdio: 'inherit',
});
