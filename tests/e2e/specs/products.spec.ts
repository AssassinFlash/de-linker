/**
 * The product pages of the review site (docs/specs/16-review-acceptance.md):
 * the category page's filters, the gated price, the button copy, once as a
 * guest and once as a signed-in, approved customer, in both languages — and
 * the page frame the redesign fixes (docs/specs/174-pdp.md): the inquiry rail
 * sticks inside the upper half only, at 1440 and at 390.
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { withoutFreightEstimate } from '../lib/copy';
import { instance, loginLink, wp } from '../lib/instance';
import { approveCustomer } from '../lib/approval';

type Locale = 'en' | 'de';

const SHOP: Record<Locale, string> = { en: '/products/', de: '/de/produkte/' };
const PRODUCT: Record<Locale, string> = {
	en: '/product/saj-h2-10k-t3/',
	de: '/de/produkt/saj-h2-10k-t3/',
};
/**
 * The product without a stats claim (docs/specs/174-pdp.md): its technical
 * data is the three-card deck with an empty summary, the case the redesign
 * had to lay out without leaving the container half empty.
 */
const NO_CLAIM: Record<Locale, string> = {
	en: '/product/goodwe-gw60k-sts-g10/',
	de: '/de/produkt/goodwe-gw60k-sts-g10/',
};
const GATED: Record<Locale, RegExp> = {
	en: /sign in|log in/i,
	de: /anmeldung|anmelden/i,
};
const DRAFT_BUTTON: Record<Locale, RegExp> = {
	en: /Add to solution draft/i,
	de: /Zum Lösungsentwurf hinzufügen/i,
};
/** A currency amount, in either notation: 1.234,56 € or €1,234.56. */
const PRICE = /(?:€|EUR)\s?\d|\d[.,]\d{2}\s?(?:€|EUR)/;

const CUSTOMER = 'e2e-catalogue@example.test';

/**
 * One customer account both locales can sign in as. Its approval is the
 * team's own step (docs/specs/11-commerce.md §3), applied by the test through
 * `approveCustomer`.
 */
function ensureCustomer(): void {
	const existing = wp([
		'user',
		'list',
		`--search=${CUSTOMER}`,
		'--field=user_login',
	]).trim();
	if (existing === '') {
		wp([
			'user',
			'create',
			CUSTOMER,
			CUSTOMER,
			'--role=customer',
			'--user_pass=local-Catalogue-2026!',
		]);
	}
}

function signInLink(): string {
	return loginLink(undefined, CUSTOMER);
}

test.describe('the products', () => {
	for (const locale of ['en', 'de'] as Locale[]) {
		test(`${locale}: the filters narrow the product listing`, async ({
			page,
		}) => {
			await page.goto(`${instance().url}${SHOP[locale]}`);
			const panel = page
				.locator('.rail-head-label, .filter-section')
				.first();
			await expect(
				panel,
				'the filter panel is on the shop page'
			).toBeVisible();
			const panelText = await page.locator('body').innerText();
			const sections =
				locale === 'de'
					? ['Kategorie', 'Anwendung', 'Marke', 'Phase', 'Leistung']
					: ['Category', 'Application', 'Brand', 'Phase', 'Power'];
			for (const section of sections) {
				expect(
					panelText,
					`the panel has the ${section} filter`
				).toContain(section);
			}

			const cards = page.locator('.sf-card');
			const total = await cards.count();
			expect(total, 'the open shop lists products').toBeGreaterThan(0);

			// One facet the cards themselves state: the grid phases. The panel
			// lists every facet with its count, so the check reads the cards,
			// never the whole page.
			await page.goto(`${instance().url}${SHOP[locale]}?phase=1`);
			const filtered = await cards.allInnerTexts();
			expect(
				filtered.length,
				'the one-phase filter leaves products'
			).toBeGreaterThan(0);
			for (const card of filtered) {
				expect(card, `a one-phase card (${card.slice(0, 80)})`).toMatch(
					/phases?\s*1\b|single-phase|1-phasig|einphasig/i
				);
				expect(
					card,
					`no three-phase card survives (${card.slice(0, 80)})`
				).not.toMatch(/phases?\s*3\b|3-phasig|dreiphasig/i);
			}

			// A brand facet, visible in the card titles.
			await page.goto(`${instance().url}${SHOP[locale]}?brand=saj`);
			const links = await cards.allInnerTexts();
			expect(
				links.length,
				'the brand filter leaves products'
			).toBeGreaterThan(0);
			for (const text of links) {
				expect(
					text,
					`only SAJ products (${text.slice(0, 80)})`
				).toMatch(/SAJ/);
			}

			// The numeric range: a 15 kW floor leaves no card whose stated AC
			// power is below it. (The open page is paginated, so the filtered
			// list is not smaller in cards — the facet is what must hold.)
			await page.goto(`${instance().url}${SHOP[locale]}?kw_min=15`);
			const rated = await cards.allInnerTexts();
			expect(
				rated.length,
				'the range filter keeps products'
			).toBeGreaterThan(0);
			let stated = 0;
			for (const card of rated) {
				// The card's own label: "AC power" in English, "AC-Nennleistung"
				// in German — the words the live German cards print too
				// (measured 2026-10-13; "AC-Leistung" is the range form's).
				const power =
					/(?:AC power|AC-Nennleistung|AC-Leistung)\s*([\d.,]+)\s*kW/i.exec(
						card
					);
				if (!power) {
					continue;
				}
				stated += 1;
				expect(
					Number(power[1]!.replace(',', '.')),
					`a card at or above the 15 kW floor (${card.slice(0, 60)})`
				).toBeGreaterThanOrEqual(15);
			}
			expect(stated, 'the cards state their AC power').toBeGreaterThan(0);
		});

		test(`${locale}: a guest sees no price, and the page says how to get one`, async ({
			page,
		}) => {
			await page.goto(`${instance().url}${PRODUCT[locale]}`);
			const text = await page.locator('body').innerText();
			expect(text, 'the page states the prices are gated').toMatch(
				GATED[locale]
			);
			expect(
				withoutFreightEstimate(text),
				'no price reaches a guest'
			).not.toMatch(PRICE);
			expect(
				text,
				'a guest is not offered the solution draft button'
			).not.toMatch(DRAFT_BUTTON[locale]);
		});

		test(`${locale}: an approved customer sees the price and the draft button`, async ({
			page,
			browser,
		}) => {
			ensureCustomer();
			await approveCustomer(browser, CUSTOMER);
			await page.goto(signInLink());
			await page.goto(`${instance().url}${PRODUCT[locale]}`);
			const text = await page.locator('body').innerText();
			expect(text, 'the product page offers the solution draft').toMatch(
				DRAFT_BUTTON[locale]
			);

			// The price the customer sees is the product's own price, read from
			// the price element rather than the page text: the body carries a
			// freight estimate (14,90 €) whose digits would otherwise satisfy
			// any body-wide match, price or not.
			const priceText = await page
				.locator('.pdp-price')
				.first()
				.innerText();
			expect(priceText, 'the customer sees a price').toMatch(PRICE);
			// An amount, not a placeholder: four digits or more once the
			// separators are gone (1.234,56 € or €1,234.56 — a battery module is
			// never cheaper than 100).
			const price = /(?:€|EUR)\s?\d[\d.,]*|\d[\d.,]*\s?(?:€|EUR)/.exec(
				priceText
			)?.[0];
			expect(price, 'a price is on the page').toBeTruthy();
			expect(
				Number(price!.replace(/[^\d]/g, '')),
				`the price is an amount (${price})`
			).toBeGreaterThan(1000);
		});
	}

	/**
	 * The page's own frame (docs/specs/174-pdp.md): the inquiry rail sticks
	 * inside the upper half only, so no scroll position puts it over a block
	 * below, and the page keeps its one container at 390 as well. Both
	 * languages, both widths.
	 */
	for (const locale of ['en', 'de'] as Locale[]) {
		for (const viewport of [
			{ width: 1440, height: 900 },
			{ width: 390, height: 844 },
		]) {
			test(`${locale}: the inquiry rail never covers the blocks at ${viewport.width}`, async ({
				page,
			}) => {
				await page.setViewportSize(viewport);
				await page.goto(`${instance().url}${PRODUCT[locale]}`);

				// One container: nothing sticks out of the viewport.
				const overflow = await page.evaluate(
					() =>
						document.documentElement.scrollWidth - window.innerWidth
				);
				expect(overflow, 'no horizontal overflow').toBeLessThanOrEqual(
					1
				);

				// The upper half holds the rail; the nav and the blocks are
				// outside it.
				const structure = await page.evaluate(() => {
					const layout = document.querySelector('.pdp-layout');
					const blocks = document.querySelectorAll(
						'.pdp-content > .pdp-block'
					);
					return {
						upper: Boolean(layout?.querySelector('.pdp-purchase')),
						navOutside: !document
							.querySelector('.pdp-section-nav')
							?.closest('.pdp-layout'),
						allOutside: Array.from(blocks).every(
							(block) => !block.closest('.pdp-layout')
						),
						blocks: blocks.length,
					};
				});
				expect(structure.upper, 'the rail is in the upper grid').toBe(
					true
				);
				expect(structure.navOutside, 'the nav is below it').toBe(true);
				expect(structure.allOutside, 'the blocks are below it').toBe(
					true
				);
				expect(structure.blocks).toBeGreaterThan(0);

				// Walking the page: the rail's box stays inside the upper half,
				// and never intersects a block or the sticky nav.
				const overlaps = await page.evaluate(async () => {
					const rail = document.querySelector('.pdp-purchase');
					const seen: string[] = [];
					const step = Math.round(window.innerHeight / 2);
					for (
						let y = 0;
						y < document.documentElement.scrollHeight;
						y += step
					) {
						window.scrollTo(0, y);
						await new Promise((done) =>
							requestAnimationFrame(() => done(null))
						);
						const box = rail!.getBoundingClientRect();
						document
							.querySelectorAll(
								'.pdp-content > .pdp-block, .pdp-section-nav'
							)
							.forEach((other) => {
								const target = other.getBoundingClientRect();
								const hit =
									box.bottom > target.top + 1 &&
									box.top < target.bottom - 1 &&
									box.right > target.left + 1 &&
									box.left < target.right - 1;
								if (hit) {
									seen.push(
										`${other.className} at scrollY ${y}`
									);
								}
							});
					}
					window.scrollTo(0, 0);
					return Array.from(new Set(seen));
				});
				expect(
					overlaps,
					'the rail covers nothing below it'
				).toStrictEqual([]);
			});
		}
	}

	/**
	 * The technical data is the prototype's three cards side by side, at 1440
	 * and 390 (docs/specs/174-pdp.md): the tab strip is gone, every group is
	 * visible, and the row is as wide as the container's content box — the
	 * case that used to leave the deck in a narrow column beside empty space.
	 */
	for (const locale of ['en', 'de'] as Locale[]) {
		test(`${locale}: the technical data deck is three cards that fill the container`, async ({
			page,
		}) => {
			await page.setViewportSize({ width: 1440, height: 900 });
			await page.goto(`${instance().url}${NO_CLAIM[locale]}`);

			const deck = await page.evaluate(() => {
				const section = document.getElementById('stats')!;
				const style = getComputedStyle(section);
				const deckEl = section.querySelector('.pdp-spec-deck')!;
				const panels = Array.from(
					section.querySelectorAll('.pdp-info-panel')
				);
				const shown = panels.filter(
					(panel) => panel.getBoundingClientRect().height > 0
				);
				const boxes = shown.map((panel) =>
					panel.getBoundingClientRect()
				);
				const summary = section.querySelector('.pdp-stats-summary')!;
				return {
					strip: getComputedStyle(
						section.querySelector('.pdp-info-tabs')!
					).display,
					summaryEmpty: summary.children.length === 0,
					panels: panels.length,
					shown: shown.length,
					rows: new Set(boxes.map((box) => Math.round(box.top))).size,
					columns: getComputedStyle(deckEl)
						.gridTemplateColumns.split(' ')
						.filter((track) => parseFloat(track) > 0).length,
					deckWidth: deckEl.getBoundingClientRect().width,
					deckLeft: deckEl.getBoundingClientRect().left,
					sectionLeft: section.getBoundingClientRect().left,
					contentWidth:
						section.getBoundingClientRect().width -
						parseFloat(style.paddingLeft) -
						parseFloat(style.paddingRight),
					contentLeft:
						section.getBoundingClientRect().left +
						parseFloat(style.paddingLeft),
				};
			});

			expect(
				deck.summaryEmpty,
				'the product has no stats claim (the case this test pins)'
			).toBe(true);
			expect(deck.strip, 'the tab strip is hidden').toBe('none');
			expect(deck.panels, 'the deck holds every spec group').toBe(3);
			expect(deck.shown, 'every group is visible').toBe(3);
			expect(deck.rows, 'the three are one row').toBe(1);
			expect(deck.columns, 'the row is three columns').toBe(3);
			expect(
				Math.abs(deck.deckWidth - deck.contentWidth),
				`the deck fills the container (${deck.deckWidth} vs ${deck.contentWidth})`
			).toBeLessThanOrEqual(1);
			expect(
				Math.abs(deck.deckLeft - deck.contentLeft),
				'the deck starts at the container content edge'
			).toBeLessThanOrEqual(1);
		});

		test(`${locale}: a product with a stats claim keeps the three cards and its claim block`, async ({
			page,
		}) => {
			await page.setViewportSize({ width: 1440, height: 900 });
			await page.goto(`${instance().url}${PRODUCT[locale]}`);

			const deck = await page.evaluate(() => {
				const section = document.getElementById('stats')!;
				const style = getComputedStyle(section);
				const summary = section.querySelector('.pdp-stats-summary')!;
				const deckEl = section.querySelector('.pdp-spec-deck')!;
				const shown = Array.from(
					section.querySelectorAll('.pdp-info-panel')
				).filter((panel) => panel.getBoundingClientRect().height > 0);
				return {
					summaryShown: summary.getBoundingClientRect().height > 0,
					shown: shown.length,
					deckWidth: deckEl.getBoundingClientRect().width,
					contentWidth:
						section.getBoundingClientRect().width -
						parseFloat(style.paddingLeft) -
						parseFloat(style.paddingRight),
				};
			});

			expect(
				deck.summaryShown,
				'the stats claim is on the page above the cards'
			).toBe(true);
			expect(deck.shown, 'every spec group is visible').toBeGreaterThan(
				1
			);
			expect(
				Math.abs(deck.deckWidth - deck.contentWidth),
				'the cards fill the container beside the claim'
			).toBeLessThanOrEqual(1);
		});
	}

	/**
	 * The comparison chip and the phone action bar (#174): the chip clears the
	 * pill by the measured bar height, one implementation each. The selection
	 * is the real one — two products are put in the tab's comparison list
	 * before the chip is read, because an empty selection hides it.
	 */
	for (const locale of ['en', 'de'] as Locale[]) {
		test(`${locale}: the comparison chip clears the action pill at 390`, async ({
			page,
		}) => {
			await page.setViewportSize({ width: 390, height: 844 });
			await page.goto(`${instance().url}${PRODUCT[locale]}`);
			await page.locator('.pdp-tool[data-compare-product]').click();
			await page.goto(`${instance().url}${NO_CLAIM[locale]}`);
			await page.locator('.pdp-tool[data-compare-product]').click();

			const chip = page.locator('#compare-chip');
			await expect(chip).toBeVisible();

			const gap = await page.evaluate(() => {
				const chipEl = document.querySelector('#compare-chip')!;
				const bar = document.querySelector('.pdp-mobile-action')!;
				return {
					chipBottom: chipEl.getBoundingClientRect().bottom,
					barTop: bar.getBoundingClientRect().top,
					barDisplay: getComputedStyle(bar).display,
					count: chipEl.textContent?.trim() ?? '',
				};
			});
			expect(gap.barDisplay, 'the action pill is on the phone').toBe(
				'flex'
			);
			expect(gap.count, 'the chip counts both products').toContain('2/');
			expect(
				gap.barTop - gap.chipBottom,
				`the chip sits above the pill (gap ${gap.barTop - gap.chipBottom})`
			).toBeGreaterThanOrEqual(8);
		});
	}
});
