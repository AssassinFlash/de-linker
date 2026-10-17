/**
 * Full-page screenshots for the live|local pixel comparison (#252).
 *
 *   node docs/acceptance/2026-10-17/252/shoot.mjs <outdir> <width> <base>=<label> ... -- <path> ...
 *   python3 docs/acceptance/2026-10-17/252/pixdiff.py <outdir>
 *
 * Playwright resolves from plugins/linker-tools/node_modules (`npm ci` there).
 * Measured 2026-10-17 before a capture counted as evidence:
 * - Chromium's GPU raster dithers gradients differently between contexts
 *   (the same local page twice: 24,117 pixels apart in the account page's
 *   brand panel, ±1–4 levels): software raster and sRGB make it 0.
 * - sizes="auto" lazy images re-pick their candidate when the full-page
 *   capture lays the page out at full height; the local PHP server answers
 *   the new requests after the capture: the viewport goes to the full height
 *   first, then every image loads eagerly and decodes.
 * - One browser per capture; no animation, no transition, no caret.
 */
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');

const args = process.argv.slice(2);
const out = args.shift();
const width = Number(args.shift());
const sep = args.indexOf('--');
const bases = args.slice(0, sep).map((b) => b.split('='));
const paths = args.slice(sep + 1);
fs.mkdirSync(out, { recursive: true });

for (const [base, label] of bases) {
	for (const p of paths) {
		const browser = await chromium.launch({
			channel: 'chromium',
			args: ['--disable-gpu', '--force-color-profile=srgb', '--disable-partial-raster', '--disable-gpu-rasterization'],
		});
		const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce', deviceScaleFactor: 1 });
		const page = await context.newPage();
		await page.goto(base + p, { waitUntil: 'networkidle', timeout: 120000 });
		await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}' });
		await page.evaluate(async () => {
			for (let y = 0; y < document.body.scrollHeight; y += 600) {
				window.scrollTo(0, y);
				await new Promise((r) => setTimeout(r, 120));
			}
			window.scrollTo(0, 0);
		});
		const full = await page.evaluate(() => document.documentElement.scrollHeight);
		await page.setViewportSize({ width, height: full });
		await page.waitForLoadState('networkidle');
		await page.evaluate(async () => {
			document.querySelectorAll('img[loading="lazy"]').forEach((i) => { i.loading = 'eager'; });
			await Promise.all([...document.images].map((i) => i.decode().catch(() => {})));
		});
		await page.waitForLoadState('networkidle');
		await page.evaluate(async () => {
			await Promise.all([...document.images].map((i) => i.decode().catch(() => {})));
		});
		await page.evaluate(() => document.fonts.ready);
		await page.waitForTimeout(800);
		const name = (p.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'home') + `-${width}-${label}.png`;
		await page.screenshot({ path: path.join(out, name), fullPage: true });
		console.log(name);
		await browser.close();
	}
}
