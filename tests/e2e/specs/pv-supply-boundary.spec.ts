/**
 * Current Woo supply and project PV parameters, from a first visitor's entry.
 */
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { instance } from '../lib/instance';

const retiredPanel = /Trina|TSM[-_ ]?(?:45|46)0NEG|Vertex[- ]S\+/i;

async function screenshot(page: Page, name: string, subject: Locator) {
	const dir = process.env.LINKER_E2E_SHOTS;
	if (dir) {
		const reject = page.getByRole('button', {
			name: /^(Reject all|Alle ablehnen)$/i,
		});
		if (await reject.isVisible()) await reject.click();
		await subject.evaluate((node) =>
			node.scrollIntoView({ block: 'center' })
		);
		await mkdir(dir, { recursive: true });
		await page.screenshot({ path: join(dir, name + '.png') });
	}
}

async function menu(
	page: Page,
	german: boolean,
	mobile: boolean,
	label: string
) {
	if (mobile) {
		await page
			.getByRole('button', { name: german ? 'Menü öffnen' : 'Open menu' })
			.click();
		await page
			.locator('header summary')
			.getByText(label, { exact: true })
			.click();
	} else {
		await page.getByRole('button', { name: label, exact: true }).click();
	}
}

for (const locale of ['en', 'de'] as const) {
	const german = locale === 'de';
	const prefix = german ? '/de' : '';
	const shop = german ? '/de/produkte/' : '/products/';
	for (const width of [1440, 390]) {
		test.describe(`${locale} ${width} · PV supply`, () => {
			test.use({
				viewport: { width, height: width === 390 ? 844 : 900 },
			});

			test('a listed brand leads to a photographed Woo product', async ({
				page,
			}) => {
				const origin = instance().url;
				await page.goto(origin + prefix + '/');
				await menu(
					page,
					german,
					width === 390,
					german ? 'Produkte' : 'Products'
				);
				await page.locator(`header a[href="${shop}"]:visible`).click();
				await expect(page).toHaveURL(origin + shop);
				if (width === 390) {
					await page
						.getByRole('button', { name: /^Filters?\b/i })
						.click();
				}
				const brand = page
					.locator('a[href*="brand=goodwe"]:visible')
					.first();
				await expect(brand).toContainText('GoodWe');
				await expect(page.locator('main')).not.toContainText(
					retiredPanel
				);
				await brand.click();
				const card = page
					.locator('main a:has(img[alt*="GoodWe"]):visible')
					.first();
				await card.scrollIntoViewIfNeeded();
				await expect
					.poll(() =>
						card
							.locator('img')
							.evaluate(
								(image: HTMLImageElement) => image.naturalWidth
							)
					)
					.toBeGreaterThan(0);
				await screenshot(page, `brand-${locale}-${width}`, card);
				const product = await card.getAttribute('href');
				await card.click();
				expect(page.url()).toBe(product);
				await expect(
					page.getByRole('heading', { level: 1 })
				).toBeVisible();
				await expect(page.locator('main')).toContainText(
					german ? 'Produktnr.' : 'Item number'
				);
				const archive = await page.goto(
					origin + (german ? '/de/marke/' : '/brand/') + 'trina-solar/'
				);
				expect(archive?.status()).toBe(404);
				await page.goto(origin + shop + '?brand=trina-solar');
				await expect(page.locator('main')).not.toContainText(
					retiredPanel
				);
				const clear = page.locator('main .wbclear:visible').first();
				await clear.click();
				await expect(page).toHaveURL(origin + shop);
				await expect(
					page.locator('main a:has(img[alt*="GoodWe"])').first()
				).toBeVisible();
			});

			for (const entry of ['home', 'workspace'] as const) {
				test(`Genie explains panel supply and design through ${entry}`, async ({
					page,
				}) => {
					const origin = instance().url;
					await page.goto(origin + prefix + '/');
					const question = german
						? 'Kann ich bei Ihnen Solarmodule bestellen? Wie berücksichtigt der Konfigurator meine Module?'
						: 'Can I buy solar panels from you? How does the configurator use my panels?';
					if (entry === 'workspace') {
						await menu(
							page,
							german,
							width === 390,
							german ? 'Planen mit Linker' : 'Plan with Linker'
						);
						await page
							.locator(
								`header a[href="${prefix}/genie/"]:visible`
							)
							.first()
							.click();
					}
					const input = page.locator(
						entry === 'home'
							? '.hero-prompt'
							: '#linker-genie-input'
					);
					await expect(input).toBeEnabled();
					await input.fill(question);
					const response = page.waitForResponse(
						(r) =>
							r.request().method() === 'POST' &&
							r.url().includes('/genie/turn'),
						{ timeout: 100_000 }
					);
					await input.press('Enter');
					const received = await response;
					expect(received.ok()).toBeTruthy();
					const { stream } = await received.json();
					const meta = /^event: meta\r?\ndata: ([^\n]+)/m.exec(
						stream
					);
					if (!meta?.[1])
						throw new Error('Missing Genie turn metadata');
					expect(JSON.parse(meta[1])).toMatchObject({
						grounded: true,
						fallback: false,
						language: locale,
					});
					const answer = page
						.locator('.linker-genie-reply:visible')
						.last();
					await expect(answer).toContainText(
						german ? /nicht|keine/i : /not|don.t|no\b/i
					);
					await expect(answer).toContainText(
						german
							? /Leistung|Abmessung|Maße|Modulgröße/i
							: /power|wattage|dimensions|panel size/i
					);
					await expect(answer).not.toContainText(retiredPanel);
					await expect(answer).not.toContainText(
						/I (?:will|can) (?:automatically )?(?:transfer|enter) .{0,100}(?:saved project|configurator)|(?:trage ich|ich trage|lese ich).{0,100}(?:trage sie in die Auslegung ein|in Ihr Projekt ein)/i
					);
					await answer.scrollIntoViewIfNeeded();
					await screenshot(
						page,
						`genie-${entry}-${locale}-${width}`,
						answer
					);
					await expect(
						answer.locator(
							'a[href*="/product/"],a[href*="/produkt/"]'
						)
					).toHaveCount(0);
				});
			}
		});
	}
}
