/**
 * The empty solution draft, EN and DE.
 *
 * The commercial-chain spec only opens /cart/ after a line has been added.
 * This one opens it with no lines and checks the designed empty state.
 * It does not start the engine or Genie: those are not part of this page.
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from '../lib/instance';

const PAGES = {
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

for (const [locale, pageCopy] of Object.entries(PAGES)) {
	test(`${locale}: an empty draft is the designed empty state`, async ({
		page,
	}) => {
		await page.context().clearCookies();
		const response = await page.goto(
			`${instance().url}${pageCopy.path}`
		);
		expect(response?.status(), 'the draft page answers').toBe(200);
		const body = page.locator('body');
		await expect(body).not.toContainText('Invalid condition function');
		await expect(body).toContainText(pageCopy.title);
		await expect(body).toContainText(pageCopy.note);
		await expect(
			page.getByRole('link', { name: pageCopy.browse })
		).toBeVisible();
		await expect(
			page.getByRole('link', { name: pageCopy.signIn })
		).toBeVisible();
		await expect(page.locator('.sf-cart-empty__icon')).toBeVisible();
		await expect(page.locator('.sf-cart-btn')).toHaveCount(2);
		await expect(body).not.toContainText('item-number');
	});
}
