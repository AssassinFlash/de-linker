/** Capture the same stable pages before and after this consent change. */
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const [stage, base = 'http://127.0.0.1:9156'] = process.argv.slice(2);
if (!['before', 'after', 'live'].includes(stage))
	throw new Error('stage: before | after | live');
const output = resolve('docs/acceptance/2026-10-19/201-consent', stage);
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const geometry = {};
for (const width of [1440, 390]) {
	for (const lang of ['en', 'de']) {
		const context = await browser.newContext({
			viewport: { width, height: 960 },
			reducedMotion: 'reduce',
		});
		const page = await context.newPage();
		await page.goto(base + (lang === 'de' ? '/de/' : '/'), {
			waitUntil: 'networkidle',
		});
		await page.addStyleTag({
			content:
				'*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}',
		});
		await page.evaluate(async () => {
			await document.fonts.ready;
			for (
				let y = 0;
				y < document.body.scrollHeight;
				y += window.innerHeight
			) {
				window.scrollTo(0, y);
				await new Promise((done) => requestAnimationFrame(done));
			}
			await Promise.all(
				Array.from(document.images)
					.filter((img) => img.loading !== 'lazy' || img.complete)
					.map((img) => img.decode().catch(() => {}))
			);
			window.scrollTo(0, 0);
		});
		if (stage === 'after') {
			await page
				.locator('.cky-consent-container')
				.waitFor({ state: 'visible' });
			await page.screenshot({
				path: `${output}/${lang}-${width}-banner.png`,
				animations: 'disabled',
			});
			await page.locator('[data-cky-tag="settings-button"]').click();
			await page.screenshot({
				path: `${output}/${lang}-${width}-purposes.png`,
				animations: 'disabled',
			});
			await page.locator('[data-cky-tag="detail-reject-button"]').click();
			await page
				.locator('.cky-consent-container')
				.waitFor({ state: 'hidden' });
		}
		await page.mouse.move(0, 0);
		await page.screenshot({
			path: `${output}/${lang}-${width}-page.png`,
			fullPage: true,
			animations: 'disabled',
		});
		geometry[`${lang}-${width}`] = await page
			.locator('.tv-footer-bar')
			.boundingBox();
		await context.close();
	}
}
await writeFile(
	`${output}/geometry.json`,
	JSON.stringify(geometry, null, 2) + '\n'
);
await browser.close();
