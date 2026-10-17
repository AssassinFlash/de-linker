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

// Header-only checks never wait for a model or a background service.
test.describe.configure({ timeout: 45_000 });

test.afterEach(async ({ page }, info) => {
	if (process.env.LINKER_HEADER_CAPTURE) {
		await page.screenshot({
			path: `${process.env.LINKER_HEADER_CAPTURE}/${info.title.replace(/[^\w-]+/g, '-')}.png`,
			fullPage: false,
			animations: 'disabled',
		});
	}
});

// Live English at 1280 is folded, even though CSS enables desktop at 1280.
// #229 keeps those pixels; 1440/1920 show the full row in both languages.
const viewports = [
	[1280, false],
	[1440, true],
	[1920, true],
	[390, false],
] as const;

for (const locale of ['en', 'de'] as const) {
	const path = locale === 'de' ? '/de/' : '/';
	for (const [width, desktop] of viewports) {
		test(`${locale}-${width}: matching navigation structure without overlap`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 900 });
			await page.goto(`${instance().url}${path}`);
			await page.evaluate(() => document.fonts.ready);
			const header = page.locator('#tv-header-v2');
			const nav = header.locator('.tv-desktop-nav');
			const cta = header.locator('.tv-header-cta:not(.tv-mobile-cta)');
			const toggle = header.locator('#tv-mobile-toggle');
			await expect(nav).toBeVisible({ visible: desktop });
			await expect(cta).toBeVisible({ visible: desktop });
			await expect(toggle).toBeVisible({ visible: !desktop });
			if (desktop) {
				await expect(nav.locator('.tv-nav-link')).toHaveCount(6);
				for (const link of await nav.locator('.tv-nav-link').all()) {
					await expect(link).toBeVisible();
				}
				// Test painted boxes, not class names or the implementation of fit().
				const boxes = await header
					.locator(
						'.tv-brand, .tv-desktop-nav, .tv-desktop-actions, .tv-header-cta:not(.tv-mobile-cta)'
					)
					.evaluateAll((elements) =>
						elements.map((element) => {
							const rect = element.getBoundingClientRect();
							return { left: rect.left, right: rect.right };
						})
					);
				for (let index = 0; index < boxes.length; index++) {
					const box = boxes[index]!;
					expect(box.left).toBeGreaterThanOrEqual(
						index === 0 ? 0 : boxes[index - 1]!.right
					);
					expect(box.right).toBeLessThanOrEqual(width);
				}
			} else {
				await toggle.click();
				const panel = header.locator('#tv-mobile-panel');
				await expect(panel).toBeVisible();
				await expect(
					panel.locator('[data-tv-mobile-primary]')
				).toHaveCount(6);
				for (const item of await panel
					.locator('.tv-mobile-summary')
					.all()) {
					await expect(item).toBeVisible();
				}
				await expect(panel.locator('.tv-mobile-cta')).toBeVisible();
				await toggle.press('Escape');
				await expect(panel).toBeHidden();
			}
		});
	}
	for (const width of [1440, 390]) {
		test(`${locale}-${width}: navigation disclosures remain usable`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 900 });
			await page.goto(`${instance().url}${path}`);
			await page.evaluate(() => document.fonts.ready);
			const header = page.locator('#tv-header-v2');
			if (width === 1440) {
				for (const key of [
					'products',
					'solutions',
					'ai',
					'partners',
					'about',
				]) {
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
				for (const key of [
					'products',
					'solutions',
					'ai',
					'partners',
					'about',
				]) {
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
			await page.setViewportSize({ width, height: 900 });
			await expect(page.locator('.tv-desktop-nav')).toBeVisible({
				visible: desktop,
			});
			await expect(page.locator('#tv-mobile-toggle')).toBeVisible({
				visible: !desktop,
			});
		}
	});
}
