/**
 * The public registration card walked through the real button (#225).
 *
 * Owner ruling 2026-10-17 (variant B): step 1 asks the company and a website
 * or VAT ID, step 2 the person and the sign-in details. The accepted website
 * form includes a bare host, so this test fills `example.com` through the real
 * Register button and checks the account the server created; a second case
 * does the same with a full https URL. Both clear the shared public limit
 * first (three submissions per connection per hour) and remove their customer.
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, wp } from '../lib/instance';

test.describe.configure({ timeout: 120_000 });

/** The shared public-connection allowance, cleared between cases. */
const CLEAR_LIMITS =
	'global $wpdb; $wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( "linker_commerce_limit_" ) . "%" ) );';

/** Deletes a customer found by email, if one exists. */
function deleteCustomer(email: string): void {
	// A failed registration creates no user; the cleanup must not mask the
	// assertion that says so.
	try {
		const id = wp(['user', 'get', email, '--field=ID']).trim();
		if (/^\d+$/.test(id)) {
			wp(['user', 'delete', id, '--yes']);
		}
	} catch {
		// No such user: nothing to remove.
	}
}

for (const [label, website, stored] of [
	['bare host', 'example.com', 'https://example.com'],
	['full URL', 'https://example.com/legal', 'https://example.com/legal'],
] as const) {
	test(`a ${label} registers through the real button and starts pending`, async ({
		page,
	}) => {
		wp(['eval', CLEAR_LIMITS]);
		const email = `tester225-${Date.now()}-${label.replace(
			/\W+/g,
			'-'
		)}@example.test`;
		try {
			await page.goto(instance().url + '/my-account/register/');
			// The step script is live: the panes are split and the bar is shown.
			await expect(
				page.locator('form[data-linker-register]')
			).toHaveClass(/is-split/);

			await page
				.locator('[name="billing_company"]')
				.fill('Solarbau E2E GmbH');
			await page
				.locator('label.radio[for="linker_customer_role_installer"]')
				.click();
			// A bare host must pass the browser's own constraint validation too;
			// the accepted field is type=text, not type=url.
			await expect(
				page.locator('[name="linker_company_website"]')
			).toHaveAttribute('type', 'text');
			await page.locator('[name="linker_company_website"]').fill(website);
			await page.locator('[data-next]').click();
			await expect(
				page.locator('form[data-linker-register]')
			).toHaveAttribute('data-active-step', '2');

			await page.locator('[name="billing_first_name"]').fill('Maria');
			await page.locator('[name="billing_last_name"]').fill('Beispiel');
			await page.locator('[name="email"]').fill(email);
			await page.locator('[name="password"]').fill('Muster-Solar-2026!');
			// PublicGuard's minimum fill time is three seconds.
			await page.waitForTimeout(3_300);

			// The actual button, not a scripted form.submit(): the browser runs
			// its constraint validation and WooCommerce's own handler.
			await Promise.all([
				page.waitForURL(/\/my-account\/?$/, { timeout: 60_000 }),
				page.locator('button[name="register"]').click(),
			]);

			// The pending account stays signed in and reads its review status.
			await expect(page.locator('body')).toContainText(
				'Your account is under review'
			);
			const id = wp(['user', 'get', email, '--field=ID']).trim();
			expect(id).toMatch(/^\d+$/);
			expect(
				wp(['user', 'meta', 'get', id, 'linker_company_website']).trim()
			).toBe(stored);
			expect(
				wp(['user', 'meta', 'get', id, 'linker_approval_status']).trim()
			).toBe('pending');
		} finally {
			deleteCustomer(email);
		}
	});
}

test('only the register page adds the country-select script to the account chain', async ({
	page,
}) => {
	await page.goto(instance().url + '/my-account/register/');
	await expect(page.locator('script[src*="account-ui.js"]')).toHaveCount(1);
	await expect(page.locator('script[src*="country-select"]')).toHaveCount(1);

	// The login card still loads the chain's interaction file, and no extra
	// country script: the register field alone needed that dependency.
	await page.goto(instance().url + '/my-account/');
	await expect(page.locator('script[src*="account-ui.js"]')).toHaveCount(1);
	await expect(page.locator('script[src*="country-select"]')).toHaveCount(0);
});
