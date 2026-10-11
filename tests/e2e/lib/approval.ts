/**
 * The team's side of account approval (docs/specs/11-commerce.md §§2–3, ticket
 * 73): every registration starts pending and reads the site like a guest —
 * no price, no solution draft, no inquiry — until the team approves the
 * account. This drives the team's own users list, whose one-click "Approve"
 * is the highest-frequency action; the link is located by its href, so the
 * suite does not depend on the admin screen's language.
 */

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
		await page.goto(
			`${instance().url}/wp-admin/users.php?s=${encodeURIComponent(email)}`
		);
		const row = page.locator('#the-list tr', { hasText: email });
		await expect(row, `the users list shows ${email}`).toHaveCount(1);
		const approve = row.locator(
			'a[href*="linker_approval_action=approve"]'
		);
		if ((await approve.count()) > 0) {
			// WordPress reveals a row's actions on hover, and the link is
			// outside the viewport until then (a click alone times out).
			await row.hover();
			await approve.first().click();
			await page.waitForLoadState('load');
		}
		// The row action renders only while the account is not approved
		// (ApprovalAdmin::row_action): its absence is the state.
		await expect(approve, `${email} is approved`).toHaveCount(0);
	} finally {
		await context.close();
	}
}
