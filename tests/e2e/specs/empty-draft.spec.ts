/** Empty solution draft and public inquiry stay usable without an account. */

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
		note: 'Browse products and add them to your solution draft. You can send an inquiry without an account.',
		browse: 'Browse products',
		signIn: 'Sign in',
		create: 'Create account',
		account: '/my-account/',
	},
	de: {
		path: '/de/warenkorb/',
		title: 'Ihr Lösungsentwurf ist leer.',
		note: 'Wählen Sie Produkte für Ihren Lösungsentwurf aus. Sie können Ihre Anfrage ohne Konto senden.',
		browse: 'Zu den Produkten',
		signIn: 'Anmelden',
		create: 'Konto erstellen',
		account: '/de/mein-konto/',
	},
} as const;

const REQUESTS = {
	en: {
		path: '/proforma-request/',
		title: 'Send an inquiry',
		signIn: 'Have an approved account? Log in for net prices and saved details.',
		create: 'Create account',
		account: '/my-account/',
	},
	de: {
		path: '/de/proforma-anfrage/',
		title: 'Anfrage senden',
		signIn: 'Sie haben bereits ein freigegebenes Partnerkonto? Melden Sie sich an, um Nettopreise zu sehen und Ihre gespeicherten Angaben zu verwenden.',
		create: 'Konto erstellen',
		account: '/de/mein-konto/',
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
		const entries = page.locator('.sf-cart-empty__actions');
		await expect(
			entries.getByRole('link', { name: pageCopy.signIn, exact: true })
		).toHaveAttribute('href', instance().url + pageCopy.account);
		await expect(
			entries.getByRole('link', { name: pageCopy.create, exact: true })
		).toHaveAttribute(
			'href',
			instance().url + pageCopy.account + 'register/'
		);
		await expect(page.locator('.sf-cart-btn')).toHaveCount(2);
		// The retired batch import is neither a button nor a promise (GAP-11).
		await expect(body).not.toContainText('item-number');
		await expect(body).not.toContainText('Artikelnummern');
	});
}

for (const [locale, pageCopy] of Object.entries(REQUESTS)) {
	test(`${locale}: an empty Proforma request stays public with optional account entries`, async ({
		page,
	}) => {
		await page.context().clearCookies();
		const response = await page.goto(`${instance().url}${pageCopy.path}`);
		expect(response?.status(), 'the request page answers').toBe(200);
		const body = page.locator('body');
		await expect(body).not.toContainText('Invalid condition function');
		await expect(page.locator('.linker-gate')).toHaveCount(0);
		await expect(page.locator('.linker-inquiry-form')).toBeVisible();
		await expect(page.locator('h1')).toHaveText(pageCopy.title);
		const entries = page.locator('.linker-inquiry-guest');
		await expect(
			entries.getByRole('link', { name: pageCopy.signIn, exact: true })
		).toHaveAttribute('href', instance().url + pageCopy.account);
		await expect(
			entries.getByRole('link', { name: pageCopy.create, exact: true })
		).toHaveAttribute(
			'href',
			instance().url + pageCopy.account + 'register/'
		);
	});
}
