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
import { instance, wp, REPO_ROOT } from '../lib/instance';

const PASSWORD = 'e2e-Account-2026!';

/** The password the reset chain writes and then signs in with. */
const NEW_PASSWORD = 'e2e-Reset-2026!x';

/**
 * The account's own register page (owner ruling 2026-10-16: sign-in and
 * sign-up are two pages). The endpoint is WooCommerce's, so the page sits
 * under the account page's URL.
 */
const REGISTER = '/my-account/register/';

function url(path: string): string {
	return `${instance().url}${path}`;
}

/**
 * A face's screenshot, into the run's own scratch directory under the repo
 * root (`.scratch/`, the repository's working area — `.gitignore` keeps
 * `.scratch/e2e-shots/` out of version control). The shots are evidence of
 * what this run rendered, not a record to commit: they used to be written
 * into `docs/acceptance/2026-10-13/account-auth/shots/`, where every run
 * rewrote the committed PNGs and left a version-noise diff behind (ledger
 * H10). The historical PNGs stay where they are, as that ticket's record;
 * this spec no longer writes to them.
 */
function shot(page: Page, name: string): Promise<Buffer> {
	return page.screenshot({
		path: `${REPO_ROOT}/.scratch/e2e-shots/account-auth/${name}.png`,
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
	// the menu opens — the count is the signal, not its visibility). The entry
	// is the one-click URL (ticket #184): WordPress's own logout action with
	// its nonce, not the endpoint URL that asks for confirmation first.
	await page.waitForFunction(
		() => document.querySelectorAll('a[href*="action=logout"]').length >= 1,
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

	test(`${locale}: the lost-password request answers and its link opens the new-password card`, async ({
		page,
	}) => {
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

		// The link the mail carries, opened for real. The key is the account's
		// own (get_password_reset_key through WP-CLI) and the fixture is the
		// account this test just created — never a made-up key the chain would
		// only have to reject.
		const id = wp(['user', 'get', login, '--field=ID']).trim();
		if (!/^\d+$/.test(id)) {
			throw new Error(`the fixture account has no id: ${id}`);
		}
		const key = wp([
			'eval',
			`$u = get_user_by( 'login', '${login}' ); echo get_password_reset_key( $u );`,
		]).trim();
		expect(key, 'the fixture account carries a reset key').not.toBe('');

		await page.goto(
			url(
				`${lost}?show-reset-form=true&key=${encodeURIComponent(key)}&id=${id}`
			)
		);
		await page.waitForLoadState('load');

		// The redesigned card, with Woo's own hidden credentials inside it.
		const card = page.locator('.linker-auth-inner--solo .linker-auth-card');
		await expect(
			card,
			'the reset link lands on the card, not on bare WooCommerce markup'
		).toBeVisible();
		await expect(
			card.locator('h1'),
			'the card titles the new password'
		).toHaveText(
			locale === 'de'
				? 'Wählen Sie ein neues Passwort'
				: 'Choose a new password'
		);
		await expect(page.locator('#password_1')).toBeVisible();
		await expect(page.locator('#password_2')).toBeVisible();
		await expect(
			page.locator('input[name="reset_key"]'),
			'the key from the link rides along'
		).toHaveValue(key);
		await expect(
			page.locator('input[name="reset_login"]'),
			'the login from the link rides along'
		).toHaveValue(login);
		await expect(
			page.locator('input[name="woocommerce-reset-password-nonce"]'),
			'the form posts with WooCommerce own nonce'
		).not.toHaveValue('');
		await shot(page, `${locale}-reset-form`);

		// A password below the site's minimum never leaves the page: the meter
		// is WooCommerce's own (min_password_strength 3) and it holds the form's
		// button. There is no server-side strength gate to reach — WooCommerce
		// refuses nothing weaker than the empty string.
		await page.fill('#password_1', 'abc');
		await page.fill('#password_2', 'abc');
		await expect(
			page.locator(
				'form.woocommerce-ResetPassword button[type="submit"]'
			),
			'WooCommerce own meter holds a weak password on the page'
		).toBeDisabled();

		// Two different passwords: the chain's own line names the mismatch and
		// the form stays put (no round trip, no lost key).
		await page.fill('#password_1', NEW_PASSWORD);
		await page.fill('#password_2', `${NEW_PASSWORD}x`);
		await page.locator('button[type="submit"]').click();
		await expect(
			page.locator('[data-password-mismatch]'),
			'the mismatch is named under the field it belongs to'
		).toBeVisible();
		await expect(page).toHaveURL(/show-reset-form/);
		await shot(page, `${locale}-reset-mismatch`);

		// The real save: the same card resets the password, WooCommerce's own
		// confirmation opens the sign-in card, and the new password signs in —
		// the whole chain, with the account this test created.
		await page.fill('#password_2', NEW_PASSWORD);
		await page.locator('button[type="submit"]').click();
		await page.waitForLoadState('load');
		await expect(
			page.locator('.woocommerce-message, .woocommerce-info').first(),
			'the reset is confirmed on the sign-in card'
		).toBeVisible();
		await expect(page.locator('#username')).toBeVisible();
		await shot(page, `${locale}-reset-done`);

		await page.fill('#username', login);
		await page.fill('#password', NEW_PASSWORD);
		await page.locator('button[name="login"]').focus();
		await page.keyboard.press('Enter');
		await page.waitForLoadState('load');
		await expect(
			page.locator('a[href*="action=logout"]'),
			'the password the reset saved is the one that signs in'
		).not.toHaveCount(0);
	});
}

test('en: the register form carries its client constraints and refuses a bad email server-side', async ({
	page,
}) => {
	// The sign-up card lives on the register page (owner ruling 2026-10-16),
	// not below the sign-in card; a refused registration stays on it.
	await page.goto(url(REGISTER));

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
	await expect(page).toHaveURL(new RegExp('/register/?$'));
	await expect(
		page.locator('.woocommerce-error').first(),
		'the impossible address is refused on the register page'
	).toBeVisible();
	await expect(
		page.locator('#reg_email'),
		'the refused sign-up stays on its own card'
	).toBeVisible();
	await expect(
		page.locator('#username'),
		'the sign-in card is not on the register page'
	).toHaveCount(0);
	await shot(page, 'en-register-invalid-email');
});

test('en: sign-in and sign-up are two pages and link to each other', async ({
	page,
}) => {
	// The sign-in page carries the sign-in card and the link to the sign-up.
	await page.goto(url('/my-account/'));
	await expect(
		page.locator('#username'),
		'the account page opens the sign-in card'
	).toBeVisible();
	await expect(
		page.locator('#reg_email'),
		'the sign-up card is not on the account page'
	).toHaveCount(0);
	const toRegister = page.locator('.linker-auth-links a', {
		hasText: 'Create your business account',
	});
	await expect(toRegister).toHaveAttribute(
		'href',
		new RegExp('/my-account/register/?$')
	);
	await toRegister.click();
	await page.waitForLoadState('load');

	// The register page is the sign-up card alone, and links back.
	await expect(page.locator('.linker-auth-register')).toBeVisible();
	await expect(page.locator('#reg_email')).toBeVisible();
	await expect(
		page.locator('#password'),
		'the sign-in password field is not on the register page'
	).toHaveCount(0);
	const toSignIn = page.locator('.linker-auth-links a', {
		hasText: 'Already have a partner account?',
	});
	await expect(toSignIn).toHaveAttribute(
		'href',
		new RegExp('/my-account/?$')
	);
	await toSignIn.click();
	await page.waitForLoadState('load');
	await expect(page.locator('#username')).toBeVisible();
});

test('en: an approved partner saves account details and company, and signs out', async ({
	page,
}) => {
	const login = createCustomer(Date.now(), 'en');
	await signIn(page, login, PASSWORD);
	await expect(
		page.locator('a[href*="action=logout"]'),
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

	// Sign out is one click (ticket #184): the menu's own link carries
	// WordPress's logout nonce, the sign-in form opens with the signed-out
	// notice, and no confirmation page stands in between.
	const logout = await page
		.locator('a[href*="action=logout"]')
		.first()
		.getAttribute('href');
	await page.goto(logout ?? url('/my-account/'));
	await page.waitForLoadState('load');
	await expect(
		page.locator('#username'),
		'the sign-out lands back on the form'
	).toBeVisible();
	await expect(
		page.locator('.woocommerce-info'),
		'the page says the visitor has been signed out'
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
 * form lives on the account's register page (owner ruling 2026-10-16), and its
 * button submits on the keyboard (commerce.spec's pattern); the register hook
 * checks the VAT ID without ever blocking.
 */
async function registerPartner(
	page: Page,
	email: string,
	vat: string
): Promise<void> {
	await page.goto(url(REGISTER));
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
		page.locator('a[href*="action=logout"]'),
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
	// The reason is a coloured notice card, and the contact sentence links its
	// own address (the message carries the placeholder, so the wording cannot
	// drop the link): both as the prototype draws them.
	const notice = gate.locator('.notice-info');
	await expect(notice, "the reason is the card's info notice").toBeVisible();
	await expect(notice, 'the notice names the reason').toContainText(
		/Our reason:/
	);
	await expect(
		gate.locator('a[href="mailto:sales@de-linker.com"]'),
		'the gate links the team mailbox'
	).toBeVisible();
	const noticeBackground = await notice.evaluate(
		(node) => getComputedStyle(node).backgroundColor
	);
	expect(noticeBackground, 'the notice is tinted, not bare text').not.toBe(
		'rgba(0, 0, 0, 0)'
	);
	await shot(page, 'en-restricted-proforma-gate');
});

test('de: the restricted gate speaks German and links its own address', async ({
	page,
}) => {
	const login = createCustomer(Date.now(), 'de');
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
		'E2E: Unterlagen in Prüfung',
	]);

	await signIn(page, login, PASSWORD);
	await page.goto(url('/de/proforma-anfrage/'));
	await page.waitForLoadState('load');

	const gate = page.locator(
		'section[aria-label="Konto mit eingeschränktem Zugriff"]'
	);
	await expect(
		gate,
		'the German Proforma request reads the gate'
	).toBeVisible();
	await expect(gate, 'the gate names the limit in German').toContainText(
		/Zugriff derzeit eingeschränkt/
	);
	await expect(gate, 'the gate carries the team reason').toContainText(
		/E2E: Unterlagen in Prüfung/
	);
	// The German sentence carries the placeholder, so the reviewed wording is
	// what shows and the address is still the link (ticket #184 review, St-4).
	await expect(
		gate.locator('a[href="mailto:sales@de-linker.com"]'),
		'the German sentence links the team mailbox'
	).toBeVisible();
	await expect(gate, 'the sentence reads as reviewed').toContainText(
		/Schreiben Sie an sales@de-linker.com/
	);
	await shot(page, 'de-restricted-proforma-gate');
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
		page.locator('a[href*="action=logout"]'),
		'no session was opened'
	).toHaveCount(0);
	await shot(page, 'en-rejected-sign-in');
});
