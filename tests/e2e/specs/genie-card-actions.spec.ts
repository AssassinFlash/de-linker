/** Answer controls in the real app; responses and writes stay in browser fixtures. */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { instance, REPO_ROOT } from '../lib/instance';

const PRODUCT_ID = 3556;
const SHOTS = join(REPO_ROOT, 'docs/acceptance/2026-10-22/genie-card-actions');

const releases = new WeakMap<Page, () => void>();

test.describe.configure({ timeout: 75_000 });
test.use({ reducedMotion: 'reduce' });
test.afterEach(async ({ page }) => {
	releases.get(page)?.();
	await page.unrouteAll({ behavior: 'wait' });
});

type Outcome = 'added' | 'retry' | 'unverified';
type Surface = 'workspace' | 'dock' | 'hero';

async function fixtures(page: Page, locale: 'en' | 'de') {
	let outcome: Outcome = 'added';
	let wrote = false;
	let release: (() => void) | null = null;
	let savingFails = true;
	const german = locale === 'de';
	const stream = [
		[
			'meta',
			{
				grounded: true,
				fallback: false,
				attempts: 1,
				failures: [],
				language: locale,
			},
		],
		[
			'block',
			{
				type: 'text',
				text: german
					? 'Hier finden Sie das Produkt und sein Datenblatt.'
					: 'Here is the product and its datasheet.',
				refs: [],
			},
		],
		[
			'block',
			{
				type: 'cards',
				product_ids: [PRODUCT_ID],
				prices: [
					{
						product_id: PRODUCT_ID,
						text: german
							? 'Nettopreis nach Partneranmeldung'
							: 'Net price after partner sign-in',
						reason: 'login',
					},
				],
			},
		],
		[
			'block',
			{
				type: 'document',
				ref: 'fixture',
				label: german
					? 'SAJ eSolar AIO3 – Datenblatt für den Wi-Fi/Ethernet/Bluetooth-Datenkollektor'
					: 'SAJ eSolar AIO3 datasheet for the Wi-Fi/Ethernet/Bluetooth data collector',
				url: `${instance().url}/fixture-datasheet.pdf`,
			},
		],
		[
			'block',
			{
				type: 'action',
				name: 'open_configurator',
				args: {
					url: `${instance().url}${german ? '/de/loesungskonfigurator/' : '/solution-configurator/'}`,
				},
			},
		],
		[
			'block',
			{
				type: 'parts',
				rows: [
					{
						line: 1,
						text: 'eSolar AIO3',
						quantity: 1,
						status: 'matched',
						product_id: PRODUCT_ID,
						label: 'eSolar AIO3',
					},
				],
				add: {
					products: 1,
					rows: 1,
					items: [{ product_id: PRODUCT_ID, quantity: 1 }],
				},
			},
		],
		['done', { ok: true }],
	]
		.map(
			([event, data]) =>
				`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
		)
		.join('');
	await page.route('**/wp-json/linker-ai/v1/genie/conversation', (route) =>
		route.fulfill({ json: { messages: [] } })
	);
	await page.route('**/wp-json/linker-ai/v1/genie/conversations', (route) =>
		route.fulfill({ json: { current_id: 0, conversations: [] } })
	);
	await page.route('**/wp-json/linker-ai/v1/genie/turn', (route) =>
		route.fulfill({ json: { conversation_id: 223, stream } })
	);
	await page.route('**/wp-json/wc/store/v1/products?*', (route) =>
		route.fulfill({
			json: [
				{
					id: PRODUCT_ID,
					name: german
						? 'SAJ eSolar AIO3 Datenkollektor (Wi-Fi/Ethernet/Bluetooth)'
						: 'SAJ eSolar AIO3 data collector (Wi-Fi/Ethernet/Bluetooth)',
					permalink: `${instance().url}${german ? '/de/produkt/' : '/product/'}saj-esolar-aio3/`,
					images: [],
					is_in_stock: true,
				},
			],
		})
	);
	await page.route(
		'**/wp-json/wp-abilities/v1/abilities/linker/get-product/run?*',
		(route) => route.fulfill({ json: { result: { model: 'eSolar AIO3' } } })
	);
	await page.route('**/wp-json/wc/store/v1/cart', (route) =>
		route.fulfill({
			headers: { Nonce: 'fixture-nonce' },
			json: {
				items:
					wrote && outcome === 'added'
						? [{ id: PRODUCT_ID, quantity: 1 }]
						: [],
			},
		})
	);
	await page.route('**/wp-json/wc/store/v1/cart/add-item', async (route) => {
		await new Promise<void>((resolve) => {
			release = resolve;
			releases.set(page, resolve);
		});
		wrote = true;
		await route.fulfill({
			status: outcome === 'retry' ? 503 : 200,
			json: {},
		});
	});
	await page.route('**/wp-json/linker/v1/solutions?*', async (route) => {
		await new Promise<void>((resolve) => {
			release = resolve;
			releases.set(page, resolve);
		});
		await route.fulfill({
			status: savingFails ? 503 : 200,
			json: { id: 1, url: '/my-account/saved-solutions/' },
		});
	});
	return {
		release: async () => {
			await expect.poll(() => release !== null).toBe(true);
			release!();
			release = null;
			releases.delete(page);
		},
		next: (next: Outcome) => {
			wrote = false;
			outcome = next;
		},
		saveSucceeds: () => {
			savingFails = false;
		},
	};
}

async function answer(
	page: Page,
	locale: 'en' | 'de',
	surface: Surface,
	width: number
) {
	const german = locale === 'de';
	await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
	const route =
		surface === 'hero'
			? german
				? '/de/'
				: '/'
			: surface === 'workspace'
				? german
					? '/de/genie/'
					: '/genie/'
				: german
					? '/de/produkte/'
					: '/products/';
	await page.goto(instance().url + route, { waitUntil: 'load' });
	const reject = page.getByRole('button', {
		name: /^(Reject all|Alle ablehnen)$/,
	});
	if (await reject.isVisible()) await reject.click();
	await expect(page.locator('.cky-consent-container')).not.toBeVisible();
	if (surface === 'hero') {
		await expect(
			page.locator('.hero-cinematic[data-linker-genie-hero="ready"]')
		).toHaveCount(1);
		await page.locator('.hero-prompt').fill('SAJ eSolar AIO3');
		await page.locator('.hero-prompt').press('Enter');
		return page.locator('.linker-genie-hero__surface');
	}
	if (surface === 'dock') {
		await page
			.locator(
				width === 390
					? '.linker-genie-chip:visible'
					: '.linker-genie-open'
			)
			.click();
	}
	const app = page.locator('.linker-genie-app:visible');
	await app.locator('.linker-genie-app__input').fill('SAJ eSolar AIO3');
	await app.locator('.linker-genie-app__send').click();
	return app;
}

async function fits(locator: Locator) {
	const box = await locator.boundingBox();
	expect(box).not.toBeNull();
	expect(box!.height).toBeGreaterThanOrEqual(44);
	expect(
		await locator.evaluate(
			(element) => element.scrollWidth <= element.clientWidth + 1
		)
	).toBe(true);
}

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		for (const surface of ['workspace', 'dock', 'hero'] as const) {
			test(`${locale}-${width}-${surface}: answer actions retain hierarchy through every write state`, async ({
				page,
			}) => {
				const fixture = await fixtures(page, locale);
				const app = await answer(page, locale, surface, width);
				const card = app.locator('.linker-card').first();
				await expect(card).toBeVisible();
				const shotTarget =
					surface === 'hero'
						? card.locator('.linker-card__actions')
						: card;
				const primary = card.locator(
					'.linker-genie-app__card-action--primary'
				);
				const secondary = card
					.locator('.linker-genie-app__card-action')
					.nth(1);
				await expect(primary).toHaveCSS(
					'background-color',
					'rgb(24, 24, 24)'
				);
				await expect(primary).toHaveCSS('color', 'rgb(255, 255, 255)');
				await expect(secondary).toHaveCSS(
					'background-color',
					'rgb(255, 255, 255)'
				);
				await expect(primary).toHaveText(
					locale === 'de'
						? 'Zum Lösungsentwurf hinzufügen'
						: 'Add to solution draft'
				);
				await expect(secondary).toHaveText(
					locale === 'de' ? 'Lösung speichern' : 'Save solution'
				);
				await fits(primary);
				await fits(secondary);
				if (surface === 'hero' && width === 390) {
					const gridBox = await app
						.locator('.linker-genie-hero__cards')
						.boundingBox();
					const cardBox = await card.boundingBox();
					const bodyBox = await card
						.locator('.linker-card__body')
						.boundingBox();
					const buttonBox = await primary.boundingBox();
					// One subpixel tolerance: the card must use the answer column and
					// the action must use its body, not half of either available width.
					expect(cardBox!.width).toBeGreaterThanOrEqual(
						gridBox!.width - 1
					);
					expect(buttonBox!.width).toBeGreaterThanOrEqual(
						bodyBox!.width - 1
					);
					const word =
						locale === 'de' ? 'Lösungsentwurf' : 'solution';
					const wordLayout = await primary.evaluate(
						(element, value) => {
							const walker = globalThis.document.createTreeWalker(
								element,
								NodeFilter.SHOW_TEXT
							);
							let node: Node | null;
							while ((node = walker.nextNode())) {
								const start = (node.textContent ?? '').indexOf(
									value
								);
								if (start < 0) continue;
								const range = globalThis.document.createRange();
								range.setStart(node, start);
								range.setEnd(node, start + value.length);
								const style = getComputedStyle(element);
								const canvas =
									globalThis.document.createElement('canvas');
								const context = canvas.getContext('2d')!;
								context.font = style.font;
								return {
									lines: [
										...new Set(
											Array.from(
												range.getClientRects(),
												(rect) => Math.round(rect.top)
											)
										),
									].length,
									minimumButtonWidth:
										context.measureText(value).width +
										parseFloat(style.paddingLeft) +
										parseFloat(style.paddingRight) +
										parseFloat(style.borderLeftWidth) +
										parseFloat(style.borderRightWidth),
								};
							}
							throw new Error(`Missing action word: ${value}`);
						},
						word
					);
					expect(wordLayout.lines).toBe(1);
					expect(buttonBox!.width).toBeGreaterThanOrEqual(
						wordLayout.minimumButtonWidth
					);
				}
				expect(
					parseFloat(
						await card
							.locator('.linker-card__actions')
							.evaluate((el) => getComputedStyle(el).gap)
					)
				).toBeGreaterThanOrEqual(10);
				mkdirSync(SHOTS, { recursive: true });
				await page.mouse.move(0, 0);
				await shotTarget.screenshot({
					path: join(
						SHOTS,
						`${locale}-${width}-${surface}-normal.png`
					),
					animations: 'disabled',
				});
				await primary.hover();
				await expect(primary).toHaveCSS(
					'background-color',
					'rgb(48, 48, 48)'
				);
				await secondary.hover();
				await expect(secondary).toHaveCSS(
					'background-color',
					'rgb(247, 248, 248)'
				);
				await primary.focus();
				await page.keyboard.press('Tab');
				await expect(secondary).toBeFocused();
				await expect(secondary).toHaveCSS('outline-style', 'solid');
				await expect(secondary).toHaveCSS('outline-width', '2px');

				for (const outcome of [
					'added',
					'retry',
					'unverified',
				] as const) {
					fixture.next(outcome);
					await primary.click();
					await expect(card).toHaveAttribute('data-state', 'pending');
					await expect(primary).toBeDisabled();
					await expect(secondary).toBeDisabled();
					await expect(primary).toHaveCSS(
						'background-color',
						'rgb(237, 237, 237)'
					);
					await expect(primary).toHaveCSS('color', 'rgb(93, 93, 93)');
					if (outcome === 'added')
						await shotTarget.screenshot({
							path: join(
								SHOTS,
								`${locale}-${width}-${surface}-pending.png`
							),
							animations: 'disabled',
						});
					await fixture.release();
					await expect(card).toHaveAttribute('data-state', outcome);
					await expect(primary).toBeEnabled();
					await expect(
						card.locator('[role="status"]')
					).not.toBeEmpty();
					if (outcome === 'added')
						await expect(card).toHaveCSS(
							'border-top-color',
							'rgb(42, 122, 88)'
						);
					else
						await expect(card.locator('[role="status"]')).toHaveCSS(
							'color',
							'rgb(146, 67, 47)'
						);
				}
				await shotTarget.screenshot({
					path: join(
						SHOTS,
						`${locale}-${width}-${surface}-unverified.png`
					),
					animations: 'disabled',
				});
				for (const succeeds of [false, true]) {
					if (succeeds) fixture.saveSucceeds();
					await secondary.click();
					await expect(card).toHaveAttribute('data-state', 'pending');
					await expect(secondary).toBeDisabled();
					await fixture.release();
					await expect(card).toHaveAttribute(
						'data-state',
						succeeds ? 'added' : 'retry'
					);
				}
				const document = app.locator('.linker-genie-app__document');
				await expect(document).toHaveAttribute(
					'href',
					`${instance().url}/fixture-datasheet.pdf`
				);
				await expect(document).toHaveAttribute('target', '_blank');
				await fits(document);
				await expect(document).toHaveCSS('display', 'flex');
				await document.screenshot({
					path: join(
						SHOTS,
						`${locale}-${width}-${surface}-document.png`
					),
					animations: 'disabled',
				});
				const action = app
					.locator('a.linker-genie-app__action')
					.first();
				await page.mouse.move(0, 0);
				await fits(action);
				await expect(action).toHaveCSS(
					'background-color',
					'rgb(24, 24, 24)'
				);
				await expect(action).toHaveCSS('color', 'rgb(255, 255, 255)');
				const parts = app.locator(
					'.linker-genie-parts__add .linker-genie-app__action'
				);
				fixture.next(width === 390 ? 'unverified' : 'added');
				await parts.click();
				await expect(parts).toBeDisabled();
				await expect(parts).toHaveAttribute('aria-busy', 'true');
				await expect(parts).toHaveCSS('cursor', 'wait');
				await fixture.release();
				await expect(parts).not.toHaveAttribute('aria-busy');
				await expect(parts).toBeDisabled();
				await expect(parts).toHaveCSS('cursor', 'default');
				await shotTarget.screenshot({
					path: join(
						SHOTS,
						`${locale}-${width}-${surface}-success.png`
					),
					animations: 'disabled',
				});
			});
		}
	}
}
