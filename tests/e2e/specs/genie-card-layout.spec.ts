/** The unchanged four-card hero still reads as a comparison after singleton repair. */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';
import { instance, REPO_ROOT } from '../lib/instance';

const OUTPUT = join(
	REPO_ROOT,
	'docs/acceptance/2026-10-22/genie-history-locale'
);
// Four published local products; cards/model/images/commerce stay native.
const PRODUCTS = [3573, 3556, 4107, 1957];

test.use({ reducedMotion: 'reduce' });

for (const locale of ['en', 'de'] as const) {
	test(`hero-${locale}-1440: four native products retain readable comparison columns`, async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1440, height: 1000 });
		const stream = [
			[
				'meta',
				{
					language: locale,
					grounded: true,
					fallback: false,
					attempts: 1,
					failures: [],
				},
			],
			[
				'block',
				{
					type: 'text',
					text: locale === 'de' ? 'Vier Produkte.' : 'Four products.',
					refs: [],
				},
			],
			['block', { type: 'cards', product_ids: PRODUCTS }],
			['done', { ok: true }],
		]
			.map(
				([event, data]) =>
					`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
			)
			.join('');
		let turns = 0;
		await page.route('**/wp-json/linker-ai/v1/genie/turn', (route) => {
			turns++;
			return route.abort();
		});
		await page.route(
			'**/wp-json/linker-ai/v1/genie/conversation',
			(route) =>
				route.fulfill({
					json: {
						messages: [
							{ role: 'user', content: 'Four fixture products' },
						],
						stream,
					},
				})
		);
		await page.route(
			'**/wp-json/linker-ai/v1/genie/conversations',
			(route) =>
				route.fulfill({ json: { current_id: 0, conversations: [] } })
		);
		await page.goto(`${instance().url}${locale === 'de' ? '/de/' : '/'}`);
		const reject = page.getByRole('button', {
			name: /^(Reject all|Alle ablehnen)$/,
		});
		if (await reject.isVisible()) await reject.click();
		await expect(
			page.locator('.hero-cinematic[data-linker-genie-hero="ready"]')
		).toHaveCount(1);
		const choosing = page.waitForEvent('filechooser');
		await page
			.locator('.hero-cinematic [data-linker-assistant-open="attach"]')
			.click();
		await (await choosing).setFiles([]);
		const surface = page.locator('.linker-genie-hero__surface');
		const grid = surface.locator('.linker-genie-hero__cards');
		const cards = grid.locator('.linker-card');
		await expect(cards).toHaveCount(4);
		await expect(cards.first().locator('.linker-card__price')).toHaveText(
			locale === 'de'
				? 'Nettopreis nach Partner-Anmeldung'
				: 'Net price after partner sign-in'
		);
		await expect(cards.locator('.linker-card__model')).toHaveCount(4);
		const primaryRows = await cards
			.locator('.linker-genie-app__card-action--primary')
			.evaluateAll((elements) =>
				elements.map((element) =>
					Math.round(element.getBoundingClientRect().top)
				)
			);
		const secondaryRows = await cards
			.locator(
				'.linker-genie-app__card-action:not(.linker-genie-app__card-action--primary)'
			)
			.evaluateAll((elements) =>
				elements.map((element) =>
					Math.round(element.getBoundingClientRect().top)
				)
			);
		expect(
			new Set(primaryRows).size,
			'all Add actions align on one comparison row'
		).toBe(1);
		expect(
			new Set(secondaryRows).size,
			'all Save actions align on one comparison row'
		).toBe(1);
		const boxes = await cards.evaluateAll((elements) =>
			elements.map((element) => {
				const box = element.getBoundingClientRect();
				return {
					left: box.left,
					right: box.right,
					top: box.top,
					width: box.width,
				};
			})
		);
		expect(new Set(boxes.map((box) => Math.round(box.top))).size).toBe(1);
		for (let index = 1; index < boxes.length; index++)
			expect(boxes[index]!.left).toBeGreaterThan(boxes[index - 1]!.right);
		for (const card of await cards.all()) {
			await expect(card.locator('.linker-card__title')).toBeVisible();
			for (const button of await card
				.locator('.linker-genie-app__card-action')
				.all()) {
				expect(
					(await button.boundingBox())!.height
				).toBeGreaterThanOrEqual(44);
				expect(
					await button.evaluate(
						(element) =>
							element.scrollWidth <= element.clientWidth + 1
					)
				).toBe(true);
			}
		}
		mkdirSync(OUTPUT, { recursive: true });
		writeFileSync(
			join(OUTPUT, `hero-${locale}-1440-four-products-geometry.json`),
			JSON.stringify(
				{
					products: PRODUCTS,
					columns: boxes,
					primaryRows,
					secondaryRows,
				},
				null,
				2
			)
		);
		await grid.scrollIntoViewIfNeeded();
		await surface.screenshot({
			path: join(OUTPUT, `hero-${locale}-1440-four-products.png`),
		});
		await cards
			.first()
			.locator('.linker-genie-app__card-action--primary')
			.scrollIntoViewIfNeeded();
		await surface.screenshot({
			path: join(OUTPUT, `hero-${locale}-1440-four-products-actions.png`),
		});
		expect(turns).toBe(0);
		await page.unrouteAll({ behavior: 'wait' });
	});
}
