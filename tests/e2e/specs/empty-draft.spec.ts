/**
 * The empty solution draft and the empty Proforma request, EN and DE.
 *
 * The commercial-chain spec only opens /cart/ after a line has been added.
 * This one opens the chain's two empty states with no lines and no account:
 * the cart's designed empty state (the live cart-en/de captures' icon, title,
 * note and actions), and the request page's left column with its Genie pill.
 * Neither page talks to the engine or Genie's agent loop, so the suite runs
 * with LINKER_E2E_SKIP_SERVICES=1.
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from '../lib/instance';

const DRAFTS = {
	en: {
		path: '/cart/',
		title: 'Your solution draft is empty.',
		note: 'Browse the products now.',
		browse: 'Browse products',
		signIn: 'Sign in or register',
	},
	de: {
		path: '/de/warenkorb/',
		title: 'Ihr Lösungsentwurf ist leer.',
		note: 'Durchsuchen Sie jetzt die Produkte.',
		browse: 'Zu den Produkten',
		signIn: 'Anmelden oder registrieren',
	},
} as const;

const REQUESTS = {
	en: {
		path: '/proforma-request/',
		title: 'Get your Proforma',
		signIn: 'Sign in to get your Proforma.',
	},
	de: {
		path: '/de/proforma-anfrage/',
		title: 'Proformarechnung anfordern',
		signIn: 'Melden Sie sich an, um Ihre Proformarechnung zu erhalten.',
	},
} as const;

for (const [locale, pageCopy] of Object.entries(DRAFTS)) {
	test(`${locale}: an empty draft is the designed empty state`, async ({
		page,
	}) => {
		await page.context().clearCookies();
		const response = await page.goto(`${instance().url}${pageCopy.path}`);
		expect(response?.status(), 'the draft page answers').toBe(200);
		const body = page.locator('body');
		// LiveCanvas resolves [lc_if] with function_exists(); a renamed
		// condition printed this error in both branches (recheck family 13/20).
		await expect(body).not.toContainText('Invalid condition function');
		await expect(
			page.locator('.sf-cart-empty'),
			'the empty state, not WooCommerce’s bare notice row'
		).toBeVisible();
		await expect(page.locator('h1')).toHaveText(pageCopy.title);
		await expect(page.locator('.sf-cart-empty__icon')).toBeVisible();
		await expect(body).toContainText(pageCopy.note);
		await expect(
			page.getByRole('link', { name: pageCopy.browse })
		).toBeVisible();
		await expect(
			page.getByRole('link', { name: pageCopy.signIn })
		).toBeVisible();
		await expect(page.locator('.sf-cart-btn')).toHaveCount(2);
		// The retired batch import is neither a button nor a promise (GAP-11).
		await expect(body).not.toContainText('item-number');
		await expect(body).not.toContainText('Artikelnummern');
	});
}

for (const [locale, pageCopy] of Object.entries(REQUESTS)) {
	test(`${locale}: an empty Proforma request is the left column with its Genie pill`, async ({
		page,
	}) => {
		await page.context().clearCookies();
		const response = await page.goto(`${instance().url}${pageCopy.path}`);
		expect(response?.status(), 'the request page answers').toBe(200);
		const body = page.locator('body');
		await expect(body).not.toContainText('Invalid condition function');
		await expect(
			page.locator('.sf-checkout-empty'),
			'the gate column, not a centred card'
		).toBeVisible();
		await expect(page.locator('h1')).toHaveText(pageCopy.title);
		await expect(
			page.locator('.sf-checkout-genie__pill'),
			'the dark pill under the title, in the site’s current name'
		).toHaveText(/Genie/);
		await expect(body).toContainText(pageCopy.signIn);

		// The pill is an anchor whose href is the no-JavaScript fallback.
		// With the dock present the click opens Genie here, so the page must
		// not navigate away.
		await page.locator('.sf-checkout-genie__pill').click();
		expect(
			new URL(page.url()).pathname,
			'the pill keeps the visitor on the request page'
		).not.toBe('/genie/');
	});
}
