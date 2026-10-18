/**
 * Service hero regression: capability cards cannot cover copy or either CTA.
 * Run against the ticket snapshot with LINKER_E2E_SKIP_SERVICES=1.
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from '../lib/instance';

// 390/1440 are the agreed visual viewports; 768/1000/1280 exercise existing
// responsive bands. 1490 is the owner's supplied overlapping-hero screenshot.
const widths = [390, 768, 1000, 1280, 1440, 1490];
for (const path of ['/services-support/', '/de/kundendienst/']) {
	for (const width of widths) {
		test(`service hero keeps copy and actions clear: ${path} ${width}`, async ({
			page,
		}) => {
			// 900 is the site's established acceptance height.
			await page.setViewportSize({ width, height: 900 });
			await page.goto(`${instance().url}${path}`);
			await page.evaluate(() => document.fonts.ready);
			const hero = page.locator('#service-redesign .lk-hero-ss');
			const links = hero.locator('.lk-hero-actions > a');
			await expect(links).toHaveCount(2);
			const layout = await hero.evaluate((root) => {
				const copy = [
					...root.querySelectorAll(
						'h1,.lk-hero-desc,.lk-hero-actions'
					),
				];
				const cards = [
					...root.querySelectorAll('.lk-hero-proof > span'),
				];
				const overlaps: string[] = [];
				for (const card of cards) {
					const a = card.getBoundingClientRect();
					if (!a.width || !a.height) {
						continue;
					}
					for (const text of copy) {
						const b = text.getBoundingClientRect();
						if (
							a.left < b.right &&
							a.right > b.left &&
							a.top < b.bottom &&
							a.bottom > b.top
						) {
							overlaps.push(
								`${card.textContent?.trim()} covers ${text.className}`
							);
						}
					}
				}
				return {
					overlaps,
					cardTops: cards.map(
						(card) => card.getBoundingClientRect().top
					),
					overflow: document.documentElement.scrollWidth > innerWidth,
				};
			});
			expect(layout.overlaps).toEqual([]);
			expect(layout.overflow).toBe(false);
			if (width >= 1000) {
				expect(layout.cardTops).toHaveLength(4);
				expect(layout.cardTops[0]).toBe(layout.cardTops[1]);
				expect(layout.cardTops[2]).toBe(layout.cardTops[3]);
			}
			for (const link of await links.all()) {
				await link.scrollIntoViewIfNeeded();
				expect(
					await link.evaluate((anchor) => {
						const box = anchor.getBoundingClientRect();
						return (
							document
								.elementFromPoint(
									box.x + box.width / 2,
									box.y + box.height / 2
								)
								?.closest('a') === anchor
						);
					})
				).toBe(true);
			}
		});
	}
}
