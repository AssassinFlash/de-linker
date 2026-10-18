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

// Header-only checks never wait for a model. The 95-width sweep takes ~7s;
// 45s also allows snapshot page loads, instead of the suite's 300s model budget.
test.describe.configure({ timeout: 45_000 });

test.afterEach(async ({ page }, info) => {
	if (process.env.LINKER_HEADER_CAPTURE && page.url() !== 'about:blank') {
		await page.screenshot({
			path: `${process.env.LINKER_HEADER_CAPTURE}/${info.project.name}/${info.title.replace(/[^\w-]+/g, '-')}.png`,
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

test('German desktop retains cross-engine safety headroom', async ({
	page,
}, info) => {
	await page.goto(`${instance().url}/de/`);
	await page.evaluate(() => document.fonts.ready);
	const spacing = [];
	// Round 2 measured worst-engine width + inter-engine spread + 1px per
	// padding side on six links. Bounds preserve usable spacing after that
	// reserve: docs/acceptance/2026-10-18/229/round2/layout-metrics.json.
	// 1288 is the first width above the review's protected boundary zone;
	// 1940 is the sweep's upper endpoint, not a new responsive breakpoint.
	for (const [width, minimum] of [
		[1288, 3.9],
		[1300, 4.9],
		[1366, 10.2],
		[1440, 12.2],
		[1920, 11.8],
		[1940, 11.8],
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
		spacing.push({ width, padding });
		// Add 12px of real layout pressure (1px on each padding side), rather
		// than duplicating the stylesheet's fit formula in the assertion.
		const probe = await page.addStyleTag({
			content: `html[lang^="de"] #tv-header-v2 .tv-nav-link{padding-inline:${padding + 1}px!important}`,
		});
		await page.evaluate(() => window.dispatchEvent(new Event('resize')));
		// A visible row before the scheduled fit() is not pressure-test proof.
		await page.evaluate(
			() =>
				new Promise<void>((resolve) => {
					requestAnimationFrame(() =>
						requestAnimationFrame(() => resolve())
					);
				})
		);
		await expect(header.locator('.tv-desktop-nav')).toBeVisible();
		await expect(header).not.toHaveAttribute('data-tv-nav-folded', 'true');
		await expect(
			header.locator('.tv-header-cta:not(.tv-mobile-cta)')
		).toBeVisible();
		await probe.evaluate((style) => (style as HTMLStyleElement).remove());
		await page.evaluate(() => window.dispatchEvent(new Event('resize')));
		if (process.env.LINKER_HEADER_CAPTURE) {
			await page.screenshot({
				path: `${process.env.LINKER_HEADER_CAPTURE}/${info.project.name}/de-${width}-spacing.png`,
				animations: 'disabled',
			});
		}
	}
	await info.attach('header-spacing.json', {
		body: JSON.stringify(spacing, null, 2),
		contentType: 'application/json',
	});
});

test('EN/DE follow the ruled header fold boundaries', async ({
	browser,
	browserName,
}, info) => {
	const en = await browser.newPage();
	const de = await browser.newPage();
	// PR #294 round 3 rules exactly these Firefox widths: EN stays expanded,
	// DE folds. Both the fold and visibility mismatch sets must match exactly.
	// https://github.com/AssassinFlash/de-linker/pull/294#issuecomment-6244186438
	const expectedMismatches =
		browserName === 'firefox' ? [1283, 1284, 1285, 1286, 1287] : [];
	// Review round 1: every pixel around the 1282 fold boundary, then every
	// 10px through 1940, plus mobile. 1300 is included once: 95 widths total after #223 adds mobile and boundary neighbours.
	const widths = [
		389,
		390,
		391,
		1275,
		1301,
		1366,
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
						// Firefox reports a viewport-aligned right edge as
						// 1283.0000305175781: observed noise is 1/32768px.
						// Allow 32x that noise, still below a 1/64px layout step.
						// Source: docs/acceptance/2026-10-18/229/round2/firefox-rects.jsonl.
						// The independent RGB pixel gate has zero tolerance.
						const rectangleEpsilon = 1 / 1024;
						const nav = header.querySelector('.tv-desktop-nav')!;
						const cta = header.querySelector(
							'.tv-header-cta:not(.tv-mobile-cta)'
						)!;
						const toggle =
							header.querySelector('#tv-mobile-toggle')!;
						const desktop =
							getComputedStyle(nav).display !== 'none';
						const parts = [
							...header.querySelectorAll(
								'.tv-brand, .tv-desktop-nav, .tv-desktop-actions, .tv-header-cta:not(.tv-mobile-cta)'
							),
						];
						const boxes = parts.map((part) =>
							part.getBoundingClientRect()
						);
						const frame = header.querySelector('.tv-nav-frame')!;
						const frameStyle = getComputedStyle(frame);
						const available = Math.floor(
							frame.clientWidth -
								parseFloat(frameStyle.paddingLeft) -
								parseFloat(frameStyle.paddingRight)
						);
						const required =
							parts.reduce(
								(sum, part, index) =>
									sum +
									boxes[index]!.width +
									(parseFloat(
										getComputedStyle(part).marginRight
									) || 0),
								0
							) +
							(parts.length - 1) *
								parseFloat(frameStyle.columnGap);
						return {
							folded:
								header.getAttribute('data-tv-nav-folded') ===
								'true',
							desktop,
							cta: getComputedStyle(cta).display !== 'none',
							toggle: getComputedStyle(toggle).display !== 'none',
							links: nav.querySelectorAll('.tv-nav-link').length,
							registration: [
								...header.querySelectorAll(
									'.tv-b2b-acct-menu>.linker-create-account, .tv-mobile-utility-row>.linker-create-account'
								),
							].map(
								(link) => (link as HTMLAnchorElement).pathname
							),
							padding: getComputedStyle(
								header.querySelector('.tv-nav-link')!
							).paddingLeft,
							headroom: desktop ? available - required : null,
							// Painted boxes verify usable layout independently of fit().
							overlap:
								desktop &&
								boxes.some(
									(box, index) =>
										box.left <
											(index
												? boxes[index - 1]!.right
												: 0) -
												rectangleEpsilon ||
										box.right >
											innerWidth + rectangleEpsilon
								),
						};
					});
				})
			);
			const [english, german] = states;
			expect
				.soft(english!.registration, `${width}px: EN guest entries`)
				.toEqual(['/my-account/register/', '/my-account/register/']);
			expect
				.soft(german!.registration, `${width}px: DE guest entries`)
				.toEqual([
					'/de/mein-konto/registrieren/',
					'/de/mein-konto/registrieren/',
				]);
			rows.push({ width, en: english, de: german });
			if (expectedMismatches.includes(width)) {
				expect
					.soft(
						english!.folded,
						`${width}px: ruled EN stays unfolded`
					)
					.toBe(false);
				expect
					.soft(
						english!.desktop,
						`${width}px: ruled EN stays visible`
					)
					.toBe(true);
				expect
					.soft(german!.folded, `${width}px: ruled DE folds`)
					.toBe(true);
				expect
					.soft(german!.desktop, `${width}px: ruled DE hides the row`)
					.toBe(false);
			}
			if (width >= 1288) {
				// Independent measured spread + six links' 12px pressure reserve;
				// round2/safety-margin.json records the precise source calculation.
				expect
					.soft(german!.headroom, `${width}px: sourced DE reserve`)
					.toBeGreaterThanOrEqual(12.35);
			}
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
			if (
				browserName === 'firefox' &&
				width === 1285 &&
				process.env.LINKER_HEADER_CAPTURE
			) {
				for (const [locale, page] of [
					['en', en],
					['de', de],
				] as const) {
					await page.screenshot({
						path: `${process.env.LINKER_HEADER_CAPTURE}/${info.project.name}/${locale}-1285-boundary.png`,
						animations: 'disabled',
					});
				}
			}
		}
		console.log(
			'| Width | EN folded | DE folded | EN desktop | DE desktop | DE padding | DE headroom |'
		);
		console.log('|---:|---|---|---|---|---:|---:|');
		for (const row of rows) {
			console.log(
				`| ${row.width} | ${row.en!.folded} | ${row.de!.folded} | ${row.en!.desktop} | ${row.de!.desktop} | ${row.de!.padding} | ${row.de!.headroom} |`
			);
		}
		await info.attach('header-boundary-sweep.json', {
			body: JSON.stringify(rows, null, 2),
			contentType: 'application/json',
		});
		expect(
			rows
				.filter((row) => row.en!.folded !== row.de!.folded)
				.map((row) => row.width),
			`${browserName}: exact ruled fold mismatch set`
		).toEqual(expectedMismatches);
		expect(
			rows
				.filter((row) => row.en!.desktop !== row.de!.desktop)
				.map((row) => row.width),
			`${browserName}: exact ruled visibility mismatch set`
		).toEqual(expectedMismatches);
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
		}, info) => {
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
							path: `${process.env.LINKER_HEADER_CAPTURE}/${info.project.name}/${locale}-${width}-${key}.png`,
							animations: 'disabled',
						});
					}
					await button.press('Escape');
					await expect(button).toHaveAttribute(
						'aria-expanded',
						'false'
					);
				}
				const account = header.locator('.tv-b2b-acct-btn');
				await account.press('End');
				await expect(
					header.locator('.tv-b2b-acct-menu>.linker-create-account')
				).toBeFocused();
				await account.press('Escape');
				await expect(account).toBeFocused();
			} else {
				await header.locator('#tv-mobile-toggle').click();
				await expect(header.locator('#tv-mobile-panel')).toBeVisible();
				await expect(
					header.locator(
						'.tv-mobile-utility-row>.linker-create-account'
					)
				).toBeVisible();
				for (const key of navKeys) {
					const section = header.locator(
						`details[data-tv-mobile-primary="${key}"]`
					);
					await section.locator('summary').click();
					await expect(section).toHaveAttribute('open', '');
					if (process.env.LINKER_HEADER_CAPTURE) {
						await page.screenshot({
							path: `${process.env.LINKER_HEADER_CAPTURE}/${info.project.name}/${locale}-${width}-${key}.png`,
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
