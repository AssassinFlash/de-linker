/**
 * The account surface's edges (matrix rows: Lost password, Registration's
 * validation, Account details, Company, Documents/Inquiries empty states).
 *
 * The commercial chain (commerce.spec.ts) walks the happy path; this file
 * pins the refusals and the account forms: a wrong password is refused, the
 * password reset answers, the register form refuses a bad email server-side,
 * an approved partner's details and company forms save, and a fresh account
 * reads the designed empty states. A customer is made per test through
 * WP-CLI and approved (Registration\Approval::STATUS_META) — no shared state.
 */

/**
 * External dependencies
 */
import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, wp } from '../lib/instance';

const PASSWORD = 'e2e-Account-2026!';

function url(path: string): string {
	return `${instance().url}${path}`;
}

function shot(page: Page, name: string): Promise<Buffer> {
	return page.screenshot({
		path: `../../docs/acceptance/2026-10-13/account-auth/shots/${name}.png`,
		fullPage: true,
	});
}

/** An approved customer, made through WP-CLI, never through the UI. */
function createCustomer(stamp: number, locale: string): string {
	const login = `e2e-acct-${locale}-${stamp}`;
	const id = wp([
		'user',
		'create',
		login,
		`${login}@example.test`,
		'--role=customer',
		`--user_pass=${PASSWORD}`,
		'--porcelain',
	]).trim();
	if (!/^\d+$/.test(id)) {
		throw new Error(`user create did not return an id: ${id}`);
	}
	wp(['user', 'meta', 'update', id, 'linker_approval_status', 'approved']);
	return login;
}

/** The site's own sign-in form, submitted the way commerce.spec submits. */
async function signIn(
	page: Page,
	login: string,
	password: string
): Promise<void> {
	await page.goto(url('/my-account/'));
	await page.fill('#username', login);
	await page.fill('#password', password);
	await page.locator('button[name="login"]').focus();
	await page.keyboard.press('Enter');
	await page.waitForLoadState('load');
	// The session settles on the rendered page: the account menu carries the
	// sign-out link once WordPress has the cookie (its own row, hidden until
	// the menu opens — the count is the signal, not its visibility).
	await page.waitForFunction(
		() =>
			document.querySelectorAll('a[href*="customer-logout"]').length >= 1,
		null,
		{ timeout: 30_000 }
	);
}

const LOCALES = [
	{
		locale: 'en',
		account: '/my-account/',
		lost: '/my-account/lost-password/',
	},
	{
		locale: 'de',
		account: '/de/mein-konto/',
		lost: '/de/mein-konto/lost-password/',
	},
] as const;

for (const { locale, account, lost } of LOCALES) {
	test(`${locale}: a wrong password is refused with the form's own error`, async ({
		page,
	}) => {
		const login = createCustomer(Date.now(), locale);
		await page.goto(url(account));
		await page.fill('#username', login);
		await page.fill('#password', 'not-the-password');
		await page.locator('button[name="login"]').focus();
		await page.keyboard.press('Enter');
		await page.waitForLoadState('load');

		const error = page.locator('.woocommerce-error');
		await expect(
			error.first(),
			'the throwaway password is refused with a notice'
		).toBeVisible();
		await expect(
			page.locator('#username'),
			'the visitor stays on the sign-in form'
		).toBeVisible();
		await shot(page, `${locale}-wrong-password`);
	});

	test(`${locale}: the lost-password request answers`, async ({ page }) => {
		const login = createCustomer(Date.now(), locale);
		await page.goto(url(lost));
		const field = page.locator(
			'input#user_login, input[name="user_login"]'
		);
		await expect(
			field.first(),
			'the reset form asks for the account'
		).toBeVisible();
		await field.first().fill(login);
		await page.locator('button[type="submit"]').first().click();
		await page.waitForLoadState('load');
		await expect(
			page.locator('.woocommerce-message, .woocommerce-info').first(),
			'the request is answered'
		).toBeVisible();
		await expect(
			page.locator('.woocommerce-error'),
			'an existing account is not refused'
		).toHaveCount(0);
		await shot(page, `${locale}-lost-password`);
	});
}

test('en: the register form carries its client constraints and refuses a bad email server-side', async ({
	page,
}) => {
	await page.goto(url('/my-account/'));

	// The form's own constraints: the fields a visitor must fill are marked,
	// the email field is typed (the browser reports what it cannot answer).
	const email = page.locator('#reg_email, input[name="email"]').first();
	await expect(email).toHaveAttribute('required', /.*/);
	await expect(email).toHaveAttribute('type', 'email');
	await expect(
		page.locator('#reg_password, input[name="password"]').first()
	).toHaveAttribute('required', /.*/);

	// The browser's own gate refuses what it can see is not an address
	// (requestSubmit runs the constraints: no request leaves the page). The
	// server's gate is reached with an address the browser accepts but the
	// site refuses: x@y has no domain WordPress accepts. Submitted with the
	// keyboard, the way commerce.spec submits this build's register button.
	await page.fill('#billing_first_name', 'Erika');
	await page.fill('#billing_last_name', 'Mustermann');
	await email.fill('x@y');
	await page.fill('#reg_password', PASSWORD);
	await page.locator('button[name="register"]').focus();
	await page.keyboard.press('Enter');
	await page.waitForLoadState('load');
	await expect(
		page.locator('.woocommerce-error').first(),
		'the impossible address is refused'
	).toBeVisible();
	await shot(page, 'en-register-invalid-email');
});

test('en: an approved partner saves account details and company, and signs out', async ({
	page,
}) => {
	const login = createCustomer(Date.now(), 'en');
	await signIn(page, login, PASSWORD);
	await expect(
		page.locator('a[href*="customer-logout"]'),
		'the customer is signed in'
	).not.toHaveCount(0);

	// Account details: the first name round-trips through the form.
	await page.goto(url('/my-account/edit-account/'));
	const stamp = `${Date.now()}`.slice(-6);
	await page.fill('#account_first_name', `Erika${stamp}`);
	await page.fill('#account_last_name', `Mustermann${stamp}`);
	await page.locator('button[name="save_account_details"]').click();
	await page.waitForLoadState('load');
	await expect(
		page.locator('.woocommerce-message').first(),
		'the details save is confirmed'
	).toBeVisible();
	await page.goto(url('/my-account/edit-account/'));
	await expect(page.locator('#account_first_name')).toHaveValue(
		`Erika${stamp}`
	);
	await expect(page.locator('#account_last_name')).toHaveValue(
		`Mustermann${stamp}`
	);
	await shot(page, 'en-account-details-saved');

	// Company — Woo's billing address form, under the endpoint slug the
	// site's own menu uses (`edit-address` is renamed to `company`).
	await page.goto(url('/my-account/company/billing/'));
	const company = page.locator('#billing_company');
	await expect(company, 'the company field is on its page').toBeVisible();
	// The form's own required fields: a fresh account has none of them.
	await page.fill('#billing_first_name', 'Erika');
	await page.fill('#billing_last_name', 'Mustermann');
	await page.selectOption('#billing_country', 'DE');
	await page.fill('#billing_address_1', 'Triftstraße 5');
	await page.fill('#billing_postcode', '80538');
	await page.fill('#billing_city', 'München');
	await company.fill(`E2E ${stamp} GmbH`);
	await page.locator('button[name="save_address"]').click();
	await page.waitForLoadState('load');
	await expect(
		page.locator('.woocommerce-message').first(),
		'the company save is confirmed'
	).toBeVisible();
	await page.goto(url('/my-account/company/billing/'));
	await expect(page.locator('#billing_company')).toHaveValue(
		`E2E ${stamp} GmbH`
	);
	await shot(page, 'en-company-saved');

	// Sign out returns to the form — through the menu's own link, which
	// carries the nonce WooCommerce's endpoint requires.
	const logout = await page
		.locator('a[href*="customer-logout"]')
		.first()
		.getAttribute('href');
	await page.goto(logout ?? url('/my-account/customer-logout/'));
	await page.waitForLoadState('load');
	await expect(
		page.locator('#username'),
		'the sign-out lands back on the form'
	).toBeVisible();
	await shot(page, 'en-signed-out');
});

test('en: a fresh account reads the designed empty states', async ({
	page,
}) => {
	const login = createCustomer(Date.now(), 'en');
	await signIn(page, login, PASSWORD);

	// Overview: the status groups, each with nothing to show yet.
	await expect(
		page.locator('body'),
		'the dashboard speaks to the partner'
	).toContainText(/Overview/);

	await page.goto(url('/my-account/inquiries/'));
	await expect(
		page.locator('body'),
		'inquiries say they are empty'
	).toContainText(/No inquiries yet/i);
	await shot(page, 'en-inquiries-empty');

	await page.goto(url('/my-account/documents/'));
	await expect(
		page.locator('body'),
		'documents explain what will appear'
	).toContainText(/will appear here/);
	await shot(page, 'en-documents-empty');

	await page.goto(url('/my-account/saved-solutions/'));
	await expect(
		page.locator('body'),
		'saved solutions render their own screen'
	).toContainText(
		/Solutions you save in the Solution Configurator appear here/i
	);
	await shot(page, 'en-saved-solutions');
});

/**
 * The register form's own fields, filled the way the form carries them. The
 * register button of this build submits on the keyboard (commerce.spec's
 * pattern), and the register hook checks the VAT ID without ever blocking.
 */
async function registerPartner(
	page: Page,
	email: string,
	vat: string
): Promise<void> {
	await page.goto(url('/my-account/'));
	await page.fill('#billing_company', 'E2E Partner GmbH');
	await page
		.locator('select[name="linker_customer_role"]')
		.selectOption('installer');
	await page.fill('#billing_vat_id', vat);
	await page.fill('#billing_first_name', 'Erika');
	await page.fill('#billing_last_name', 'Mustermann');
	await page.selectOption('#billing_country', 'DE');
	await page.fill('#billing_address_1', 'Triftstraße 5');
	await page.fill('#billing_postcode', '80538');
	await page.fill('#billing_city', 'München');
	await page.fill('#reg_email', email);
	await page.fill('#reg_password', PASSWORD);
	await page.locator('button[name="register"]').focus();
	await page.keyboard.press('Enter');
	await page.waitForLoadState('load');
}

/** The registered account's id, read through WP-CLI, never the UI. */
function registeredId(email: string): string {
	const id = wp(['user', 'get', email, '--field=ID']).trim();
	if (!/^\d+$/.test(id)) {
		throw new Error(`registration did not produce an account: ${id}`);
	}
	return id;
}

test('en: a VAT ID VIES cannot check never blocks registration, and the account is flagged', async ({
	page,
}) => {
	const stamp = Date.now();
	const email = `e2e-vat-noneu-${stamp}@example.test`;
	// Not an EU member-state prefix: the verdict is deterministic, no VIES call.
	await registerPartner(page, email, 'US-1234567');

	await shot(page, 'en-register-vat-not-eu');
	const id = registeredId(email);
	expect(
		wp(['user', 'meta', 'get', id, 'linker_vat_status']).trim(),
		'the unchecked number is flagged, not refused'
	).toBe('unverified');
	expect(
		wp(['user', 'meta', 'get', id, 'linker_vat_detail']).trim(),
		'the flag says why'
	).toBe('not an EU VAT ID');
	expect(
		wp(['user', 'meta', 'get', id, 'linker_vat_checked_number']).trim(),
		'the flag belongs to the typed number'
	).toBe('US1234567');
});

test('en: an EU-format VAT ID is checked at registration and the verdict kept', async ({
	page,
}) => {
	const stamp = Date.now();
	const email = `e2e-vat-eu-${stamp}@example.test`;
	await registerPartner(page, email, 'DE123456789');

	await shot(page, 'en-register-vat-eu-checked');
	const id = registeredId(email);
	// The check ran and its verdict is stored with the number it is for. The
	// verdict itself (valid, invalid or unverified) is VIES's answer and
	// depends on the instance's reachability — the behavior pinned here is
	// that registration went through and the account carries a verdict.
	expect(
		wp(['user', 'meta', 'get', id, 'linker_vat_checked_number']).trim(),
		'the stored number is the typed one'
	).toBe('DE123456789');
	expect(
		wp(['user', 'meta', 'get', id, 'linker_vat_status']).trim(),
		'a verdict exists'
	).toMatch(/^(valid|invalid|unverified)$/);
});

test('en: a restricted account signs in, keeps the workplace and reads its gate on the Proforma request', async ({
	page,
}) => {
	const login = createCustomer(Date.now(), 'en');
	wp([
		'user',
		'meta',
		'update',
		login,
		'linker_approval_status',
		'restricted',
	]);
	wp([
		'user',
		'meta',
		'update',
		login,
		'linker_approval_reason',
		'E2E: documents under review',
	]);

	await signIn(page, login, PASSWORD);
	await expect(
		page.locator('a[href*="customer-logout"]'),
		'a restricted account still signs in'
	).not.toHaveCount(0);
	await expect(
		page.locator('body'),
		'the workplace stays open'
	).toContainText(/Overview/);

	await page.goto(url('/proforma-request/'));
	await page.waitForLoadState('load');
	const gate = page.locator(
		'section[aria-label="Account with limited access"]'
	);
	await expect(
		gate,
		'the Proforma request reads the restriction gate'
	).toBeVisible();
	await expect(gate, 'the gate names the limit').toContainText(
		/Access currently limited/
	);
	await expect(gate, 'the gate carries the reason').toContainText(
		/E2E: documents under review/
	);
	await shot(page, 'en-restricted-proforma-gate');
});

test('en: a rejected account cannot sign in and reads the refusal', async ({
	page,
}) => {
	const login = createCustomer(Date.now(), 'en');
	wp(['user', 'meta', 'update', login, 'linker_approval_status', 'rejected']);
	wp([
		'user',
		'meta',
		'update',
		login,
		'linker_approval_reason',
		'E2E: not a business customer',
	]);

	await page.goto(url('/my-account/'));
	await page.fill('#username', login);
	await page.fill('#password', PASSWORD);
	await page.locator('button[name="login"]').focus();
	await page.keyboard.press('Enter');
	await page.waitForLoadState('load');

	const error = page.locator('.woocommerce-error');
	await expect(
		error.first(),
		'the rejection is the sign-in refusal'
	).toBeVisible();
	await expect(error.first(), 'the refusal names the way back').toContainText(
		/not approved for sign-in/
	);
	await expect(
		page.locator('#username'),
		'the rejected account stays on the form'
	).toBeVisible();
	await expect(
		page.locator('a[href*="customer-logout"]'),
		'no session was opened'
	).toHaveCount(0);
	await shot(page, 'en-rejected-sign-in');
});
