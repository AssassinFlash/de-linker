/** The employee approves through the canonical account-review card. */

/**
 * External dependencies
 */
import { expect, type Browser } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, loginLink, wp } from './instance';

/** The staff account the admin screens open for: the instance's administrator. */
function staff(): string {
	return wp(['user', 'list', '--role=administrator', '--field=user_login'])
		.trim()
		.split('\n')
		.pop()!
		.trim();
}

/**
 * Approves one customer through the team's own screen. Idempotent: a customer
 * the list no longer offers "Approve" for is already approved.
 *
 * Runs in its own browser context, so the caller's session (a customer's)
 * stays what it is.
 */
export async function approveCustomer(
	driver: Browser,
	email: string
): Promise<void> {
	const context = await driver.newContext();
	const page = await context.newPage();
	try {
		await page.goto(loginLink(undefined, staff()));
		const id = wp(['user', 'get', email, '--field=ID']).trim();
		await page.goto(
			`${instance().url}/wp-admin/admin.php?page=linker-accounts&focus=${id}`
		);
		const card = page.locator(
			`#linker-accounts-focus [data-account-id="${id}"]`
		);
		await expect(card).toBeVisible();
		const response = page.waitForResponse(
			(result) =>
				result.url().includes(`/accounts/${id}/approval`) &&
				result.request().method() === 'POST'
		);
		await card
			.getByRole('button', { name: /^(Approve|Freigeben)$/ })
			.click();
		expect((await response).ok()).toBe(true);
		await expect(card.getByRole('status')).toContainText(
			/Decision saved|Entscheidung wurde gespeichert/
		);
		expect(
			wp(['user', 'meta', 'get', id, 'linker_approval_status']).trim()
		).toBe('approved');
	} finally {
		await context.close();
	}
}
