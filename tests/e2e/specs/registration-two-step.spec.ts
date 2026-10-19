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

test('the business-type radios answer on the input itself, in English and German', async ({
	page,
}) => {
	// #351: the pill styling had parked the native inputs at 1px with
	// pointer-events:none, so only the wrapping label answered — Playwright's
	// actionability check, keyboard users and screen readers hit the same
	// wall. The fix keeps the input the pill's own hit and focus target
	// (RoleField nests it inside its label, auth.css overlays the label with
	// it), and this walk repeats the original repro against both languages.
	for (const locale of ['en', 'de'] as const) {
		const path =
			locale === 'de'
				? '/de/mein-konto/register/'
				: '/my-account/register/';
		await page.goto(instance().url + path);
		await expect(page.locator('form[data-linker-register]')).toHaveClass(
			/is-split/
		);

		// The ticket's repro: check() runs the full actionability gauntlet on
		// the INPUT (visible, stable, receiving events) before clicking it.
		const epc = page.locator('#linker_customer_role_epc');
		await epc.check();
		await expect(epc).toBeChecked();
		await expect(
			page.locator('label.radio[for="linker_customer_role_epc"]')
		).toHaveCSS('border-color', 'rgb(12, 127, 115)');

		// The keyboard path: Tab from the company name reaches the group —
		// the browser's tab stop is the checked input — and the arrows move
		// the checked state along with focus, with the chain's focus ring on
		// the focused pill.
		await page.locator('[name="billing_company"]').focus();
		await page.keyboard.press('Tab');
		expect(await page.evaluate(() => document.activeElement?.id)).toBe(
			'linker_customer_role_epc'
		);
		const installerPill = page.locator(
			'label.radio[for="linker_customer_role_installer"]'
		);
		const epcPill = page.locator(
			'label.radio[for="linker_customer_role_epc"]'
		);
		await expect(epcPill).toHaveCSS('outline-style', 'solid');
		await expect(epcPill).toHaveCSS('outline-color', 'rgb(12, 127, 115)');
		await page.keyboard.press('ArrowLeft');
		await expect(
			page.locator('#linker_customer_role_installer')
		).toBeChecked();
		await expect(installerPill).toHaveCSS('outline-style', 'solid');
		await expect(epcPill).toHaveCSS('outline-style', 'none');
	}
});

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
