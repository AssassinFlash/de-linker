/**
 * The account workspace's own states at 390 and in German (state-matrix
 * family account: inquiries-empty, inquiries-populated,
 * saved-solutions-empty, documents-empty, account-details, validation,
 * logout, customer-admin-explanation, owner-other-customer-guest-access).
 *
 * account.spec.ts walks several of these once at 1440 and in English; this
 * file walks them on the phone tier and in German too, because the workspace
 * swaps its sidebar for a bottom tab bar below 1024px (account.css) and
 * linker-i18n rewrites every endpoint slug (`anfragen/`, `dokumente/`,
 * `gespeicherte-loesungen/`, `kontodaten/`, `unternehmen/…`). The records a
 * state needs — a customer, its inquiry, its saved solution — are made
 * through WP-CLI for that one test and deleted with it; nothing is shared.
 */

/**
 * External dependencies
 */
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Internal dependencies
 */
import { instance, REPO_ROOT, wp } from '../lib/instance';
import { seedConsentCookies } from '../lib/consent';

/** The site's own sign-in form; the logout test signs in through it. */
const PASSWORD = 'e2e-Account-States-2026!';

/** The product the inquiry fixture buys (a published inverter). */
const PRODUCT = 4107;

const output = join(
	REPO_ROOT,
	'.scratch/e2e-shots/account-states',
	process.env.LINKER_ACCOUNT_STATES_RUN ?? 'latest'
);

/** One language's account surface: slugs and the strings the page renders. */
interface Language {
	lang: 'en' | 'de';
	account: string;
	inquiries: string;
	documents: string;
	solutions: string;
	details: string;
	company: string;
	products: string;
	pendingTitle: string;
	emptyInquiries: string;
	browse: string;
	emptyDocuments: string;
	emptySolutions: string;
	configurator: string;
	configuratorPath: string;
	signedOut: string;
	adminTitle: string;
	adminExplanation: string;
	adminAccount: string;
	requiredFirst: string;
	statusReceived: string;
	productCount: string;
	invalidOrder: string;
	newProject: string;
	createProject: string;
}

const LANGUAGES: Language[] = [
	{
		lang: 'en',
		account: '/my-account/',
		inquiries: '/my-account/inquiries/',
		documents: '/my-account/documents/',
		solutions: '/my-account/saved-solutions/',
		details: '/my-account/edit-account/',
		company: '/my-account/company/billing/',
		products: '/products/',
		pendingTitle: 'Your account is under review',
		emptyInquiries: 'No inquiries yet.',
		browse: 'Browse products',
		emptyDocuments:
			'Your quotations and the design reports of your saved solutions will appear here.',
		emptySolutions:
			'Solutions you save in the Solution Configurator appear here, with their design report.',
		configurator: 'Open the Solution Configurator',
		configuratorPath: '/solution-configurator/',
		signedOut: 'You have been signed out.',
		adminTitle: 'Linker staff only',
		adminExplanation: 'The admin area is for Linker staff only.',
		adminAccount: 'Go to my account',
		requiredFirst: 'First name is a required field.',
		statusReceived: 'Inquiry received',
		productCount: '1 product',
		invalidOrder: 'Invalid order.',
		newProject: 'New project',
		createProject: 'Create project',
	},
	{
		lang: 'de',
		account: '/de/mein-konto/',
		inquiries: '/de/mein-konto/anfragen/',
		documents: '/de/mein-konto/dokumente/',
		solutions: '/de/mein-konto/gespeicherte-loesungen/',
		details: '/de/mein-konto/kontodaten/',
		company: '/de/mein-konto/unternehmen/rechnungsadresse/',
		products: '/de/produkte/',
		pendingTitle: 'Ihr Konto wird geprüft',
		emptyInquiries: 'Noch keine Anfragen.',
		browse: 'Zu den Produkten',
		emptyDocuments:
			'Ihre Angebote und die Entwurfsberichte Ihrer gespeicherten Lösungen erscheinen hier.',
		emptySolutions:
			'Lösungen, die Sie im Lösungskonfigurator speichern, erscheinen hier mit ihrem Auslegungsbericht.',
		configurator: 'Lösungskonfigurator öffnen',
		configuratorPath: '/de/loesungskonfigurator/',
		signedOut: 'Sie wurden abgemeldet.',
		adminTitle: 'Bereich für Linker-Mitarbeitende',
		adminExplanation:
			'Der Verwaltungsbereich ist ausschließlich für Linker-Mitarbeitende vorgesehen.',
		adminAccount: 'Zu meinem Konto',
		requiredFirst: 'Vorname ist ein Pflichtfeld.',
		statusReceived: 'Anfrage eingegangen',
		productCount: '1 Produkt',
		invalidOrder: 'Ungültige Bestellung.',
		newProject: 'Neues Projekt',
		createProject: 'Projekt anlegen',
	},
];

/** The customer one test works as. */
interface Customer {
	id: number;
	login: string;
	email: string;
}

/** The owner's records, for the populated and the isolation states. */
interface Owner extends Customer {
	order: number;
	solution: number;
}

function base(): string {
	return instance().url;
}

/**
 * A customer made through WP-CLI, never through the interface: every test
 * owns its own account, so no test can read another's workspace.
 */
function makeCustomer(status: 'approved' | 'pending', tag: string): Customer {
	const login = `e2e-states-${tag}-${Date.now()}`;
	const email = `${login}@example.test`;
	const id = Number(
		wp([
			'eval',
			`$id = wp_insert_user( array( 'user_login' => '${login}', 'user_email' => '${email}', 'user_pass' => '${PASSWORD}', 'role' => 'customer' ) );` +
				`if ( is_wp_error( $id ) ) { echo '0'; return; }` +
				`update_user_meta( $id, 'linker_approval_status', '${status}' ); echo $id;`,
		]).trim()
	);
	if (id <= 0) {
		throw new Error(`the fixture customer ${login} was not created`);
	}
	return { id, login, email };
}

/**
 * An approved customer with one inquiry and one saved solution, plus a second
 * approved customer who owns neither — the two accounts the isolation state
 * contrasts.
 */
function makeOwner(tag: string): { owner: Owner; other: Customer } {
	const stamp = Date.now();
	const login = `e2e-states-owner-${tag}-${stamp}`;
	const email = `${login}@example.test`;
	const other = `e2e-states-other-${tag}-${stamp}`;
	const otherEmail = `${other}@example.test`;
	const fixture = JSON.parse(
		wp([
			'eval',
			`$id = wp_insert_user( array( 'user_login' => '${login}', 'user_email' => '${email}', 'user_pass' => '${PASSWORD}', 'role' => 'customer' ) );` +
				`$b = wp_insert_user( array( 'user_login' => '${other}', 'user_email' => '${otherEmail}', 'user_pass' => '${PASSWORD}', 'role' => 'customer' ) );` +
				`if ( is_wp_error( $id ) || is_wp_error( $b ) ) { echo '{}'; return; }` +
				`update_user_meta( $id, 'linker_approval_status', 'approved' );` +
				`update_user_meta( $b, 'linker_approval_status', 'approved' );` +
				`$order = wc_create_order( array( 'customer_id' => $id ) );` +
				`$order->add_product( wc_get_product( ${PRODUCT} ), 1 );` +
				`$order->set_status( 'inquiry-received' );` +
				`$order->calculate_totals( false ); $order->save();` +
				`$solution = wp_insert_post( array( 'post_type' => 'linker_solution', 'post_status' => 'private', 'post_author' => $id, 'post_title' => 'E2E saved solution' ) );` +
				`echo wp_json_encode( array( 'owner' => $id, 'other' => $b, 'order' => $order->get_id(), 'solution' => $solution ) );`,
		]).trim()
	) as {
		owner?: number;
		other?: number;
		order?: number;
		solution?: number;
	};
	if (!fixture.owner || !fixture.other || !fixture.order) {
		throw new Error('the isolation fixture was not created');
	}
	return {
		owner: {
			id: fixture.owner,
			login,
			email,
			order: fixture.order,
			solution: fixture.solution ?? 0,
		},
		other: { id: fixture.other, login: other, email: otherEmail },
	};
}

/** Removes a fixture's records and accounts, whatever the test did. */
function remove(customers: Customer[], orders: number[] = []): void {
	const ids = customers.map((customer) => customer.id).join(',');
	if ('' === ids) {
		return;
	}
	wp([
		'eval',
		`foreach ( array( ${orders.length ? orders.join(',') : '0'} ) as $order_id ) { $order = wc_get_order( $order_id ); if ( $order ) { $order->delete( true ); } }` +
			`foreach ( array( ${ids} ) as $user_id ) {` +
			`foreach ( get_posts( array( 'post_type' => 'linker_solution', 'author' => $user_id, 'post_status' => 'private', 'numberposts' => -1, 'fields' => 'ids' ) ) as $post_id ) { wp_delete_post( $post_id, true ); }` +
			`require_once ABSPATH . 'wp-admin/includes/user.php'; wp_delete_user( $user_id ); } echo 'removed';`,
	]);
}

/** A full-page shot into the run's own scratch directory. */
async function shot(page: Page, name: string): Promise<void> {
	await page.evaluate(async () => {
		await document.fonts.ready;
		await Promise.all(
			Array.from(document.images, async (image) => {
				image.loading = 'eager';
				await image.decode().catch(() => undefined);
			})
		);
	});
	await page.screenshot({
		path: join(output, `${name}.png`),
		fullPage: true,
		animations: 'disabled',
	});
}

/** The phone tier is the narrowest the design supports; nothing may spill. */
async function expectNoOverflow(page: Page, width: number): Promise<void> {
	expect(
		await page.evaluate(() => document.documentElement.scrollWidth),
		`the page fits ${width}px`
	).toBeLessThanOrEqual(width);
}

/**
 * Signs in through the site's own form on the language's account page.
 *
 * The one-time link `just login` prints redirects to `admin_url()`, which for
 * a customer is WooCommerce's admin refusal — the explanation page, not the
 * workspace. Signing in on the account page also sets the language cookie, so
 * the `/wp-admin/` refusal that the explanation test walks resolves to the
 * same language's account twin.
 */
async function signIn(
	page: Page,
	customer: Customer,
	account: string
): Promise<void> {
	await page.goto(base() + account);
	await page.fill('#username', customer.login);
	await page.fill('#password', PASSWORD);
	// PublicGuard's minimum fill time is three seconds; every suite that posts
	// through these doors waits for it before submitting.
	await page.waitForTimeout(3_300);
	await page.locator('button[name="login"]').click();
	await page.waitForLoadState('load');
	await page.waitForFunction(
		() => document.querySelectorAll('a[href*="action=logout"]').length >= 1,
		null,
		{ timeout: 30_000 }
	);
}

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
	mkdirSync(output, { recursive: true });
});

for (const language of LANGUAGES) {
	for (const width of [1440, 390]) {
		const tag = `${language.lang}-${width}`;

		test(`${tag}: the empty account endpoints read their designed empty states`, async ({
			browser,
		}) => {
			const customer = makeCustomer('pending', tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, customer, language.account);

				// A pending account keeps its workspace (owner ruling 2026-10-17):
				// the notice rides every endpoint, and the endpoints still render.
				const gate = page.locator('.linker-account-status');
				await expect(gate).toBeVisible();
				await expect(gate).toContainText(language.pendingTitle);
				await expect(
					page
						.locator(
							width === 390
								? '.linker-account-bottom-nav'
								: '.linker-account-nav'
						)
						.first()
				).toBeVisible();
				await expect(
					page.locator('.linker-account-main')
				).not.toContainText(/€|EUR/);

				await page.goto(base() + language.inquiries);
				const emptyInquiries = page.locator(
					'.linker-account-empty-inquiries'
				);
				await expect(emptyInquiries).toBeVisible();
				await expect(emptyInquiries.locator('p')).toHaveText(
					language.emptyInquiries
				);
				const browse = emptyInquiries.getByRole('link', {
					name: language.browse,
				});
				await expect(browse).toHaveAttribute(
					'href',
					new RegExp(`${language.products}$`)
				);
				await expect(gate).toBeVisible();
				await expectNoOverflow(page, width);
				await shot(page, `${language.lang}-${width}-inquiries-empty`);

				await page.goto(base() + language.documents);
				const emptyDocuments = page.locator('.linker-account-empty');
				await expect(emptyDocuments).toContainText(
					language.emptyDocuments
				);
				await expect(gate).toBeVisible();
				await expectNoOverflow(page, width);
				await shot(page, `${language.lang}-${width}-documents-empty`);

				await page.goto(base() + language.solutions);
				const emptySolutions = page.locator('.linker-account-empty');
				await expect(emptySolutions).toContainText(
					language.emptySolutions
				);
				await expect(
					emptySolutions.getByRole('link', {
						name: language.configurator,
					}),
					'the empty state offers the configurator'
				).toBeVisible();
				await expect(gate).toBeVisible();
				await expectNoOverflow(page, width);
				await shot(page, `${language.lang}-${width}-solutions-empty`);

				// The session survives the whole sweep: the workspace is the
				// customer's, not a page that only looked signed in once.
				await expect(
					page.locator('a[href*="action=logout"]').first()
				).toBeAttached();
			} finally {
				await context.close();
				remove([customer]);
			}
		});

		test(`${tag}: the language switch keeps the account section the visitor is reading`, async ({
			browser,
		}) => {
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				// Both cards the account chain opens by fragment: the sign-in card
				// and the lost-password card. The server builds every language
				// link from the request, which never carries a fragment, so the
				// switch has to carry it (assets/language-hash.js).
				const other = language.lang === 'en' ? 'de' : 'en';
				const signInHash = '#linker-auth-signin';
				const resetHash = '#linker-auth-reset';
				await page.goto(base() + language.account + signInHash);
				await page.waitForLoadState('load');
				await page
					.locator(
						`header a[data-linker-language-choice="${other}"]:visible`
					)
					.first()
					.click();
				await page.waitForLoadState('load');
				expect(
					new URL(page.url()).hash,
					'the sign-in card survives the language switch'
				).toBe(signInHash);

				await page.goto(
					base() +
						(language.lang === 'en'
							? '/my-account/lost-password/'
							: '/de/mein-konto/passwort-zuruecksetzen/') +
						resetHash
				);
				await page.waitForLoadState('load');
				await page
					.locator(
						`header a[data-linker-language-choice="${other}"]:visible`
					)
					.first()
					.click();
				await page.waitForLoadState('load');
				const switched = new URL(page.url());
				expect(
					switched.hash,
					'the lost-password card survives the language switch'
				).toBe(resetHash);
				expect(
					switched.pathname,
					'the account endpoint is translated, not dropped'
				).toMatch(/lost-password|passwort-zuruecksetzen/);
				await expectNoOverflow(page, width);
				await shot(
					page,
					`${language.lang}-${width}-language-switch-fragment`
				);
			} finally {
				await context.close();
			}
		});

		test(`${tag}: a saved planning project appears in the account and opens`, async ({
			browser,
		}) => {
			const customer = makeCustomer('approved', tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			const title = `E2E plan ${tag}`;
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, customer, language.account);

				// A project made while signed in belongs to this account's own
				// principal, so the account row reads it back from the planner's
				// private index - never from a second store.
				await page.goto(base() + language.configuratorPath, {
					waitUntil: 'networkidle',
				});
				await page
					.getByRole('button', { name: language.newProject })
					.first()
					.click();
				await page
					.locator('input[maxlength="256"]')
					.first()
					.fill(title);
				await page
					.getByRole('button', { name: language.createProject })
					.click();
				await expect(page).toHaveURL(/project=[a-f0-9]{32}/, {
					timeout: 60_000,
				});
				const projectId = new URL(page.url()).searchParams.get(
					'project'
				)!;
				await expect(page.locator('.lp-save-state')).toBeVisible({
					timeout: 30_000,
				});

				await page.goto(base() + language.solutions);
				const panel = page.locator(
					'section[aria-labelledby="linker-account-projects-title"]'
				);
				await expect(
					panel,
					'the account lists the planning projects'
				).toBeVisible();
				const row = panel
					.locator('.linker-account-products li')
					.filter({ hasText: title });
				await expect(
					row,
					'the project row carries its title'
				).toBeVisible();
				const href = await row
					.locator('a')
					.first()
					.getAttribute('href');
				expect(href, 'the row opens the project it names').toContain(
					`project=${projectId}#lp-overview`
				);
				await row.locator('a').first().click();
				await page.waitForLoadState('load');
				await expect(page).toHaveURL(
					new RegExp(`project=${projectId}`)
				);
				await expectNoOverflow(page, width);
				await shot(
					page,
					`${language.lang}-${width}-solutions-populated`
				);
			} finally {
				await context.close();
				remove([customer]);
			}
		});

		test(`${tag}: a customer's own inquiry is listed and opens`, async ({
			browser,
		}) => {
			const { owner, other } = makeOwner(tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, owner, language.account);
				await page.goto(base() + language.inquiries);

				const row = page.locator(`[data-inquiry="${owner.order}"]`);
				await expect(
					row,
					'the inquiry the customer sent is on their own list'
				).toBeVisible();
				await expect(row.locator('.linker-account-pill')).toHaveText(
					language.statusReceived
				);
				await expect(
					row.locator('.linker-account-row-count')
				).toHaveText(language.productCount);
				await expect(
					row.locator('.linker-account-row-number')
				).toHaveText(`#${owner.order}`);
				await expect(
					row.locator('.linker-account-row-amount')
				).toContainText(/[0-9]/);
				await expect(
					page.locator('.linker-account-empty'),
					'a populated list shows no empty state'
				).toHaveCount(0);
				await expectNoOverflow(page, width);
				await shot(
					page,
					`${language.lang}-${width}-inquiries-populated`
				);

				// The row's own action opens the inquiry it names (consumer
				// read-back: the list's link is the record the customer owns).
				const view = row.locator('.linker-account-row-view');
				const href = await view.getAttribute('href');
				expect(href).toContain(
					language.lang === 'de'
						? `/anfrage/${owner.order}/`
						: `/inquiry/${owner.order}/`
				);
				await view.click();
				await expect(page).toHaveURL(
					new RegExp(
						`${language.lang === 'de' ? 'anfrage' : 'inquiry'}/${owner.order}/`
					)
				);
				await expect(
					page.locator('.linker-account-main')
				).toContainText(`#${owner.order}`);
				await shot(page, `${language.lang}-${width}-inquiry-detail`);
			} finally {
				await context.close();
				remove([owner, other], [owner.order]);
			}
		});

		test(`${tag}: account details save and read back`, async ({
			browser,
		}) => {
			const customer = makeCustomer('approved', tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, customer, language.account);
				await page.goto(base() + language.details);

				// WooCommerce's own form, under the site's designed card.
				await expect(page.locator('#account_first_name')).toBeVisible();
				await expect(page.locator('#account_last_name')).toBeVisible();
				await expect(page.locator('#account_email')).toBeVisible();
				await expect(page.locator('#account_email')).toHaveValue(
					customer.email
				);
				await expect(
					page.locator('#password_1, input[name="password_1"]'),
					'the save form carries the password change too'
				).toHaveCount(1);
				await shot(page, `${language.lang}-${width}-account-details`);

				const stamp = `${Date.now()}`.slice(-6);
				await page.fill('#account_first_name', `Erika${stamp}`);
				await page.fill('#account_last_name', `Mustermann${stamp}`);
				await page
					.locator('button[name="save_account_details"]')
					.click();
				await page.waitForLoadState('load');
				await expect(
					page
						.locator('.woocommerce-message, [role="status"]')
						.first(),
					'the save is confirmed'
				).toBeVisible();

				// Read back from the record, not from the confirmation: a reload
				// asks WordPress again what the customer's name is.
				await page.goto(base() + language.details);
				await expect(page.locator('#account_first_name')).toHaveValue(
					`Erika${stamp}`
				);
				await expect(page.locator('#account_last_name')).toHaveValue(
					`Mustermann${stamp}`
				);
				await expectNoOverflow(page, width);
				await shot(
					page,
					`${language.lang}-${width}-account-details-saved`
				);
			} finally {
				await context.close();
				remove([customer]);
			}
		});

		test(`${tag}: the company form names every required field it refuses`, async ({
			browser,
		}) => {
			const customer = makeCustomer('approved', tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, customer, language.account);
				await page.goto(base() + language.company);

				const save = page.locator('button[name="save_address"]');
				await expect(save).toBeVisible();
				// A value in an optional field: the refused save keeps the typing.
				const company = page.locator('#billing_company');
				await company.fill('E2E States GmbH');

				// The form is WooCommerce's own (`novalidate`), so an empty save
				// reaches the server: the refusal names each missing field.
				await save.click();
				await page.waitForLoadState('load');

				const error = page.locator('.woocommerce-error').first();
				await expect(error, 'the empty save is refused').toBeVisible();
				await expect(error).toContainText(language.requiredFirst);
				const named = await error
					.locator('li[data-id]')
					.evaluateAll((items) =>
						items.map((item) => item.getAttribute('data-id') ?? '')
					);
				// Exactly the six fields a new account has not filled: the email
				// arrives prefilled from the account, so it is not among them.
				expect(named).toEqual([
					'billing_first_name',
					'billing_last_name',
					'billing_country',
					'billing_address_1',
					'billing_postcode',
					'billing_city',
				]);
				await expect(page).toHaveURL(base() + language.company);
				await expect(
					company,
					'the refused save keeps the typing'
				).toHaveValue('E2E States GmbH');
				await expectNoOverflow(page, width);
				await shot(
					page,
					`${language.lang}-${width}-company-validation`
				);
			} finally {
				await context.close();
				remove([customer]);
			}
		});

		test(`${tag}: sign-out is one click and lands on the form with its notice`, async ({
			browser,
		}) => {
			const customer = makeCustomer('approved', tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();

				// Sign in through the form the customers use, not a link.
				await page.goto(base() + language.account);
				await page.fill('#username', customer.login);
				await page.fill('#password', PASSWORD);
				await page.locator('button[name="login"]').click();
				await page.waitForLoadState('load');
				await expect(
					page
						.locator('.linker-account-status, .linker-account-main')
						.first(),
					'the customer is in the workspace'
				).toBeVisible();
				await page.waitForFunction(
					() =>
						document.querySelectorAll('a[href*="action=logout"]')
							.length >= 1,
					null,
					{ timeout: 30_000 }
				);

				// One click (no confirmation page in between): WordPress's own
				// nonce-protected logout, as the menu carries it.
				const logout = await page
					.locator('a[href*="action=logout"]')
					.first()
					.getAttribute('href');
				if (!logout) throw new Error('no logout link on the account');
				await page.goto(logout);
				await page.waitForLoadState('load');

				await expect(
					page.locator('#username'),
					'the sign-out lands back on the form'
				).toBeVisible();
				await expect(
					page.locator('.woocommerce-info').first(),
					'the page says the visitor has been signed out'
				).toContainText(language.signedOut);
				await expect(
					page.locator('a[href*="action=logout"]'),
					'the session is gone'
				).toHaveCount(0);
				expect(
					(await context.cookies())
						.map((cookie) => cookie.name)
						.filter((name) =>
							name.startsWith('wordpress_logged_in_')
						),
					'WordPress dropped its login cookie'
				).toEqual([]);
				await expectNoOverflow(page, width);
				await shot(page, `${language.lang}-${width}-signed-out`);
			} finally {
				await context.close();
				remove([customer]);
			}
		});

		test(`${tag}: a customer's /wp-admin visit explains itself`, async ({
			browser,
		}) => {
			const customer = makeCustomer('approved', tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, customer, language.account);

				// WooCommerce keeps refusing customers the admin area; the site's
				// adapter sends the refusal to the explanation beside the account.
				await page.goto(`${base()}/wp-admin/`);
				await page.waitForLoadState('load');
				expect(page.url()).toContain('admin-access=staff');
				expect(new URL(page.url()).pathname).toBe(language.account);

				const notice = page.locator(
					'section.linker-admin-access[data-linker-admin-notice]'
				);
				await expect(notice).toBeVisible();
				await expect(notice.locator('h1')).toHaveText(
					language.adminTitle
				);
				await expect(notice).toContainText(customer.email);
				await expect(notice).toContainText(language.adminExplanation);
				await expect(
					notice.getByRole('link', { name: language.adminAccount })
				).toHaveAttribute('href', base() + language.account);
				await expect(
					notice.locator('.linker-gate-btn.is-primary'),
					'the other way out is a staff sign-in'
				).toHaveAttribute('href', /action=logout/);
				await expectNoOverflow(page, width);
				await shot(page, `${language.lang}-${width}-admin-explanation`);

				// The explanation is for a signed-in customer only: a guest asking
				// for the same URL gets the ordinary sign-in card.
				const guest = await browser.newContext({
					viewport: { width, height: width === 390 ? 844 : 900 },
				});
				try {
					await seedConsentCookies(guest);
					const anonymous = await guest.newPage();
					await anonymous.goto(
						`${base()}${language.account}?admin-access=staff`
					);
					await expect(anonymous.locator('#username')).toBeVisible();
					await expect(
						anonymous.locator('.linker-admin-access')
					).toHaveCount(0);
				} finally {
					await guest.close();
				}
			} finally {
				await context.close();
				remove([customer]);
			}
		});

		test(`${tag}: another customer and a guest cannot read the owner's records`, async ({
			browser,
		}) => {
			const { owner, other } = makeOwner(tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, other, language.account);

				// The owner's documents answer their owner only, whoever asks.
				const report = `${base()}/?linker-document=report&id=${owner.solution}`;
				const quotation = `${base()}/?linker-document=quotation&id=${owner.order}`;
				const status = async (url: string) =>
					(await page.goto(url))?.status();
				expect(await status(report), 'another customer: report').toBe(
					403
				);
				expect(
					await status(quotation),
					'another customer: quotation'
				).toBe(403);

				// The owner's saved solution is not on the other customer's list.
				await page.goto(base() + language.solutions);
				await expect(
					page.locator(`#linker-solution-${owner.solution}`)
				).toHaveCount(0);
				await expect(
					page.locator('.linker-account-empty')
				).toContainText(language.emptySolutions);

				// Nor is the owner's inquiry readable through its view URL: Woo's
				// own check refuses it and the page stays on the account.
				await page.goto(
					`${base()}${language.inquiries.replace(
						/inquiries\/$|anfragen\/$/,
						language.lang === 'de' ? 'anfrage/' : 'inquiry/'
					)}${owner.order}/`
				);
				await page.waitForLoadState('load');
				await expect(
					page.locator('.woocommerce-error').first(),
					'the other customer gets no inquiry content'
				).toContainText(language.invalidOrder);
				await expect(page.locator(`[data-inquiry]`)).toHaveCount(0);
				await expectNoOverflow(page, width);
				await shot(page, `${language.lang}-${width}-isolation-other`);

				// A guest is refused the same documents and gets the sign-in card
				// instead of any account content.
				const guest = await browser.newContext({
					viewport: { width, height: width === 390 ? 844 : 900 },
				});
				try {
					await seedConsentCookies(guest);
					const anonymous = await guest.newPage();
					for (const url of [report, quotation]) {
						expect(
							(await anonymous.goto(url))?.status(),
							`a guest is refused ${url}`
						).toBe(403);
					}
					await anonymous.goto(base() + language.solutions);
					await expect(anonymous.locator('#username')).toBeVisible();
					await expect(
						anonymous.locator(`#linker-solution-${owner.solution}`)
					).toHaveCount(0);
					await shot(
						page,
						`${language.lang}-${width}-isolation-guest`
					);
				} finally {
					await guest.close();
				}
			} finally {
				await context.close();
				remove([owner, other], [owner.order]);
			}
		});
	}
}
