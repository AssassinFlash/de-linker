/**
 * #229: the full primary navigation and contact button share the English
 * desktop breakpoint. Run against a snapshot instance, without services:
 * LINKER_E2E_SKIP_SERVICES=1 just e2e c229 header-parity.spec.ts
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from '../lib/instance';

// Header-only checks never wait for a model. The 90-width sweep takes ~7s;
// 45s also allows snapshot page loads, instead of the suite's 300s model budget.
test.describe.configure({ timeout: 45_000 });

test.afterEach(async ({ page }, info) => {
	if (process.env.LINKER_HEADER_CAPTURE && page.url() !== 'about:blank') {
		await page.screenshot({
			path: `${process.env.LINKER_HEADER_CAPTURE}/${info.title.replace(/[^\w-]+/g, '-')}.png`,
			fullPage: false,
			animations: 'disabled',
		});
	}
});

// Live English at 1280 is folded, even though CSS enables desktop at 1280.
// #229 keeps those pixels; 1440/1920 show the full row in both languages.
// 900px is the viewport height fixed by the original #229 live/local captures
// and the reviewer's boundary probe; changing it would change the baseline.
const viewportHeight = 900;
const navKeys = ['products', 'solutions', 'ai', 'partners', 'about'] as const;
const viewports = [
	[1280, false],
	[1440, true],
	[1920, true],
	[390, false],
] as const;

test('German navigation uses the largest spacing that fits', async ({
	page,
}) => {
	await page.goto(`${instance().url}/de/`);
	await page.evaluate(() => document.fonts.ready);
	// Independent bounds from the review's rendered-width measurements.
	for (const [width, minimum] of [
		[1300, 6],
		[1366, 11.3],
		[1440, 13.3],
		[1920, 12.9],
	]) {
		await page.setViewportSize({ width: width!, height: viewportHeight });
		const header = page.locator('#tv-header-v2');
		await expect(header.locator('.tv-desktop-nav')).toBeVisible();
		const padding = await header
			.locator('.tv-nav-link')
			.first()
			.evaluate((link) => parseFloat(getComputedStyle(link).paddingLeft));
		expect(padding).toBeGreaterThanOrEqual(minimum!);
		expect(padding).toBeLessThanOrEqual(14);
		// Chromium lays out in 1/64px units. One more unit per side must overflow;
		// otherwise the current spacing left usable space on the table.
		// CSSOM serializes 12.953125 as 12.9531; restore the layout unit before
		// adding one, so the probe does not accidentally round down again.
		const nextPadding = (Math.round(padding * 64) + 1) / 64;
		const probe = await page.addStyleTag({
			content: `html[lang^="de"] #tv-header-v2 .tv-nav-link{padding-inline:${nextPadding}px!important}`,
		});
		await page.evaluate(() => window.dispatchEvent(new Event('resize')));
		await expect(header).toHaveAttribute('data-tv-nav-folded', 'true');
		await probe.evaluate((style) => style.remove());
		await page.evaluate(() => window.dispatchEvent(new Event('resize')));
		await expect(header.locator('.tv-desktop-nav')).toBeVisible();
		if (process.env.LINKER_HEADER_CAPTURE) {
			await page.screenshot({
				path: `${process.env.LINKER_HEADER_CAPTURE}/de-${width}-spacing.png`,
				animations: 'disabled',
			});
		}
	}
});

test('EN/DE share every header fold boundary', async ({ browser }, info) => {
	const en = await browser.newPage();
	const de = await browser.newPage();
	// Review round 1: every pixel around the 1282 fold boundary, then every
	// 10px through 1940, plus mobile. 1300 is included once: 90 widths total.
	const widths = [
		390,
		...Array.from({ length: 25 }, (_, index) => 1276 + index),
		...Array.from({ length: 64 }, (_, index) => 1310 + index * 10),
	];
	const rows = [];
	try {
		await Promise.all([
			en.goto(`${instance().url}/`),
			de.goto(`${instance().url}/de/`),
		]);
		await Promise.all(
			[en, de].map((page) => page.evaluate(() => document.fonts.ready))
		);
		for (const width of widths) {
			const states = await Promise.all(
				[en, de].map(async (page) => {
					await page.setViewportSize({
						width,
						height: viewportHeight,
					});
					// ResizeObserver schedules fit() for the following animation frame.
					await page.evaluate(
						() =>
							new Promise<void>((resolve) => {
								requestAnimationFrame(() =>
									requestAnimationFrame(() => resolve())
								);
							})
					);
					return page.locator('#tv-header-v2').evaluate((header) => {
						const nav = header.querySelector('.tv-desktop-nav')!;
						const cta = header.querySelector(
							'.tv-header-cta:not(.tv-mobile-cta)'
						)!;
						const toggle =
							header.querySelector('#tv-mobile-toggle')!;
						const desktop =
							getComputedStyle(nav).display !== 'none';
						const boxes = [
							...header.querySelectorAll(
								'.tv-brand, .tv-desktop-nav, .tv-desktop-actions, .tv-header-cta:not(.tv-mobile-cta)'
							),
						].map((element) => element.getBoundingClientRect());
						return {
							folded:
								header.getAttribute('data-tv-nav-folded') ===
								'true',
							desktop,
							cta: getComputedStyle(cta).display !== 'none',
							toggle: getComputedStyle(toggle).display !== 'none',
							links: nav.querySelectorAll('.tv-nav-link').length,
							padding: getComputedStyle(
								header.querySelector('.tv-nav-link')!
							).paddingLeft,
							// Painted boxes verify usable layout independently of fit().
							overlap:
								desktop &&
								boxes.some(
									(box, index) =>
										box.left <
											(index
												? boxes[index - 1]!.right
												: 0) || box.right > innerWidth
								),
						};
					});
				})
			);
			const [english, german] = states;
			rows.push({ width, en: english, de: german });
			expect
				.soft(german!.folded, `${width}px: DE fold matches EN`)
				.toBe(english!.folded);
			expect
				.soft(german!.desktop, `${width}px: DE visibility matches EN`)
				.toBe(english!.desktop);
			for (const state of states) {
				expect
					.soft(
						state.cta,
						`${width}px: contact follows primary navigation`
					)
					.toBe(state.desktop);
				expect
					.soft(state.toggle, `${width}px: menu remains reachable`)
					.toBe(!state.desktop);
				expect
					.soft(
						state.links,
						`${width}px: all six primary entries remain`
					)
					.toBe(6);
				expect
					.soft(state.overlap, `${width}px: no painted boxes overlap`)
					.toBe(false);
			}
		}
		console.log(
			'| Width | EN folded | DE folded | EN desktop | DE desktop | DE padding |'
		);
		console.log('|---:|---|---|---|---|---:|');
		for (const row of rows) {
			console.log(
				`| ${row.width} | ${row.en!.folded} | ${row.de!.folded} | ${row.en!.desktop} | ${row.de!.desktop} | ${row.de!.padding} |`
			);
		}
		await info.attach('header-boundary-sweep.json', {
			body: JSON.stringify(rows, null, 2),
			contentType: 'application/json',
		});
	} finally {
		await en.close();
		await de.close();
	}
});

for (const locale of ['en', 'de'] as const) {
	const path = locale === 'de' ? '/de/' : '/';
	for (const width of [1440, 390]) {
		test(`${locale}-${width}: navigation disclosures remain usable`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: viewportHeight });
			await page.goto(`${instance().url}${path}`);
			await page.evaluate(() => document.fonts.ready);
			const header = page.locator('#tv-header-v2');
			if (width === 1440) {
				for (const key of navKeys) {
					const item = header.locator(
						`.tv-nav-item[data-tv-nav-primary="${key}"]`
					);
					const button = item.locator('.tv-nav-link');
					await button.press('ArrowDown');
					await expect(button).toHaveAttribute(
						'aria-expanded',
						'true'
					);
					await expect(item.locator('.tv-mega-menu')).toBeVisible();
					if (process.env.LINKER_HEADER_CAPTURE) {
						await page.screenshot({
							path: `${process.env.LINKER_HEADER_CAPTURE}/${locale}-${width}-${key}.png`,
							animations: 'disabled',
						});
					}
					await button.press('Escape');
					await expect(button).toHaveAttribute(
						'aria-expanded',
						'false'
					);
				}
			} else {
				await header.locator('#tv-mobile-toggle').click();
				await expect(header.locator('#tv-mobile-panel')).toBeVisible();
				for (const key of navKeys) {
					const section = header.locator(
						`details[data-tv-mobile-primary="${key}"]`
					);
					await section.locator('summary').click();
					await expect(section).toHaveAttribute('open', '');
					if (process.env.LINKER_HEADER_CAPTURE) {
						await page.screenshot({
							path: `${process.env.LINKER_HEADER_CAPTURE}/${locale}-${width}-${key}.png`,
							animations: 'disabled',
						});
					}
					await section.locator('summary').click();
				}
			}
		});
	}
	test(`${locale}: resizing restores the correct navigation`, async ({
		page,
	}) => {
		await page.goto(`${instance().url}${path}`);
		await page.evaluate(() => document.fonts.ready);
		for (const [width, desktop] of [...viewports, [1440, true] as const]) {
			await page.setViewportSize({ width, height: viewportHeight });
			await expect(page.locator('.tv-desktop-nav')).toBeVisible({
				visible: desktop,
			});
			await expect(page.locator('#tv-mobile-toggle')).toBeVisible({
				visible: !desktop,
			});
		}
	});
}
