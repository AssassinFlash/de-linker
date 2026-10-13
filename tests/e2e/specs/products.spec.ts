/**
 * The product pages of the review site (docs/specs/16-review-acceptance.md):
 * the category page's filters, the gated price, and the button copy, once as
 * a guest and once as a signed-in, approved customer, in both languages.
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
				const power = /(?:AC power|AC-Leistung)\s*([\d.,]+)\s*kW/i.exec(
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
			expect(text, 'the customer sees a price').toMatch(PRICE);
			expect(text, 'the product page offers the solution draft').toMatch(
				DRAFT_BUTTON[locale]
			);

			// The price the customer sees is an amount, not a placeholder: four
			// digits or more once the separators are gone (1.234,56 € or
			// €1,234.56 — a battery module is never cheaper than 100).
			const price = /(?:€|EUR)\s?\d[\d.,]*|\d[\d.,]*\s?(?:€|EUR)/.exec(
				text
			)?.[0];
			expect(price, 'a price is on the page').toBeTruthy();
			expect(
				Number(price!.replace(/[^\d]/g, '')),
				`the price is an amount (${price})`
			).toBeGreaterThan(1000);
		});
	}
});
