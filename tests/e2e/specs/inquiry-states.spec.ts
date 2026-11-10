/**
 * The inquiry page's signed-in summary and the confirmation-key states
 * (state-matrix family inquiry: signed-in-summary,
 * confirmation-key-invalid-expired-and-owner).
 *
 * Two facts the rows stand for, both read off the live surfaces rather than
 * inferred:
 *
 * - A signed-in customer whose reply details are stored sees them folded into
 *   one summary line above the message field (owner ruling 2026-10-17: the
 *   details collapse to one row); `Change` opens the prefilled fields.
 * - The confirmation link carries WooCommerce's order key. A wrong or missing
 *   key — and an order id that does not exist — answers the recovery notice
 *   and no inquiry data. A correct key still needs the owner: the anonymous
 *   visitor gets WooCommerce's own verification gate (email verification for a
 *   guest inquiry, sign-in for a customer-owned one), and another signed-in
 *   customer gets the sign-in gate again. Keys do not expire (the key is the
 *   order key), so an inquiry backdated by more than a year opens for its
 *   owner exactly like a fresh one.
 *
 * State-matrix rows: inquiry:signed-in-summary:{en:390,de:1440,de:390} and
 * inquiry:confirmation-key-invalid-expired-and-owner:{en:390,de:390}; the
 * 1440-en siblings of both states run here too, so the suite covers the state
 * instead of only its missing shapes.
 *
 * Every record is made through WP-CLI for the one test that reads it and
 * deleted with it. Fixture orders are created (never submitted), so their
 * status notification hooks are removed inside the same request: no mail job
 * is queued for a record that no customer sent.
 */

/**
 * External dependencies
 */
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Internal dependencies
 */
import { instance, REPO_ROOT, wp } from '../lib/instance';
import { seedConsentCookies } from '../lib/consent';

/** The site's own sign-in form; the account is made through WP-CLI. */
const PASSWORD = 'e2e-Inquiry-States-2026!';

/** The published inverter the fixture inquiry carries. */
const PRODUCT = 4107;

const evidence = join(
	REPO_ROOT,
	'.scratch/e2e-shots/inquiry-states',
	process.env.LINKER_INQUIRY_STATES_RUN ?? 'latest'
);

interface Language {
	lang: 'en' | 'de';
	locale: 'en_US' | 'de_DE_formal';
	request: string;
	account: string;
	summaryLabel: string;
	change: string;
	recovery: string;
	gate: string;
	verify: RegExp;
	success: string;
	promise: string;
}

const LANGUAGES: Language[] = [
	{
		lang: 'en',
		locale: 'en_US',
		request: '/proforma-request/',
		account: '/my-account/',
		summaryLabel: 'Your reply details',
		change: 'Change',
		recovery:
			'This confirmation link did not open. Please use the link from your inquiry confirmation email, or write to sales@de-linker.com and we will send it again.',
		gate: 'Please log in to your account to view this inquiry.',
		verify: /To view this page, you must either login or verify the email address associated with the order\./,
		success: 'Inquiry received',
		promise: 'We reply within one business day.',
	},
	{
		lang: 'de',
		locale: 'de_DE_formal',
		request: '/de/proforma-anfrage/',
		account: '/de/mein-konto/',
		summaryLabel: 'Ihre Kontaktdaten',
		change: 'Ändern',
		recovery:
			'Dieser Bestätigungslink ließ sich nicht öffnen. Bitte verwenden Sie den Link aus Ihrer Anfragebestätigung, oder schreiben Sie an sales@de-linker.com. Wir senden Ihnen den Link gerne erneut.',
		gate: 'Bitte melden Sie sich in Ihrem Konto an, um diese Anfrage anzuzeigen.',
		verify: /Um diese Seite anzuzeigen, müssen Sie sich entweder anmelden oder die E-Mail-Adresse verifizieren, die mit der Bestellung verknüpft ist\./,
		success: 'Anfrage eingegangen',
		promise: 'Wir antworten innerhalb eines Arbeitstags.',
	},
];

/** Read one element's rendered text with the browser's soft hyphens removed. */
async function text(page: Page, selector: string): Promise<string> {
	return (
		(await page
			.locator(selector)
			.first()
			.evaluate((el) => (el as HTMLElement).innerText ?? '')) ?? ''
	)
		.replace(/\u00AD/g, '')
		.replace(/\s+/g, ' ')
		.trim();
}

/** A customer made through WP-CLI, never through the interface. */
interface Customer {
	id: number;
	login: string;
	email: string;
}

function makeCustomer(tag: string): Customer {
	const login = `e2e-inquiry-${tag}-${Date.now()}`;
	const email = `${login}@example.test`;
	const id = Number(
		wp([
			'eval',
			`$id = wp_insert_user( array( 'user_login' => '${login}', 'user_email' => '${email}', 'user_pass' => '${PASSWORD}', 'role' => 'customer' ) );` +
				`if ( is_wp_error( $id ) ) { echo '0'; return; }` +
				`update_user_meta( $id, 'linker_approval_status', 'approved' ) ;` +
				`foreach ( array( 'first_name' => 'Maria', 'last_name' => 'Beispiel', 'email' => '${email}', 'company' => 'E2E Solar GmbH' ) as $key => $value ) { update_user_meta( $id, 'billing_' . $key, $value ); }` +
				`echo $id;`,
		]).trim()
	);
	if (id <= 0) {
		throw new Error(`the fixture customer ${login} was not created`);
	}
	return { id, login, email };
}

/** The inquiry records the confirmation-key states read. */
interface Fixture {
	owner: Customer;
	other: Customer;
	product: string;
	guestEmail: string;
	order: Receipt;
	guest: Receipt;
	old: Receipt;
}

interface Receipt {
	id: number;
	key: string;
	url: string;
}

/**
 * One inquiry per owner, guest and backdated case, in this language's locale.
 * The notification hooks of the status transition are removed for this request
 * alone: a fixture order never went through the inquiry form, so no mail job may
 * be queued for it.
 */
function makeFixture(language: Language, tag: string): Fixture {
	const owner = makeCustomer(`${tag}-owner`);
	const other = makeCustomer(`${tag}-other`);
	const guestEmail = `e2e-inquiry-${tag}-guest-${Date.now()}@example.test`;
	const created = JSON.parse(
		wp([
			'eval',
			`remove_all_actions( 'woocommerce_order_status_pending_to_inquiry-received' );` +
				`remove_all_actions( 'woocommerce_order_status_pending_to_inquiry-received_notification' );` +
				`$order = wc_create_order( array( 'customer_id' => ${owner.id} ) );` +
				`$order->set_payment_method( 'linker_inquiry' );` +
				`$order->set_billing_email( '${owner.email}' );` +
				`$order->set_billing_first_name( 'Maria' );` +
				`$order->set_billing_last_name( 'Beispiel' );` +
				`$order->set_billing_company( 'E2E Solar GmbH' );` +
				`$order->add_product( wc_get_product( ${PRODUCT} ), 1 );` +
				`$order->update_meta_data( '_linker_locale', '${language.locale}' );` +
				`$order->set_status( 'inquiry-received' );` +
				`$order->calculate_totals( false );` +
				`$order->save();` +
				`$old = wc_create_order( array( 'customer_id' => ${owner.id} ) );` +
				`$old->set_payment_method( 'linker_inquiry' );` +
				`$old->set_billing_email( '${owner.email}' );` +
				`$old->set_billing_first_name( 'Maria' );` +
				`$old->set_billing_last_name( 'Beispiel' );` +
				`$old->set_billing_company( 'E2E Solar GmbH' );` +
				`$old->add_product( wc_get_product( ${PRODUCT} ), 1 );` +
				`$old->update_meta_data( '_linker_locale', '${language.locale}' );` +
				`$old->set_status( 'inquiry-received' );` +
				`$old->set_date_created( time() - 400 * DAY_IN_SECONDS );` +
				`$old->calculate_totals( false );` +
				`$old->save();` +
				`$guest_order = wc_create_order( array( 'customer_id' => 0 ) );` +
				`$guest_order->set_payment_method( 'linker_inquiry' );` +
				`$guest_order->set_billing_email( '${guestEmail}' );` +
				`$guest_order->set_billing_first_name( 'Gast' );` +
				`$guest_order->set_billing_last_name( 'Beispiel' );` +
				`$guest_order->add_product( wc_get_product( ${PRODUCT} ), 1 );` +
				`$guest_order->update_meta_data( '_linker_locale', '${language.locale}' );` +
				`$guest_order->set_status( 'inquiry-received' );` +
				// WooCommerce skips the email-verification step within ten
				// minutes of an order (`woocommerce_order_email_verification_
				// grace_period`). A customer opens the emailed link later than
				// that, so this inquiry is an hour old.
				`$guest_order->set_date_created( time() - HOUR_IN_SECONDS );` +
				`$guest_order->calculate_totals( false );` +
				`$guest_order->save();` +
				`$receipt = function ( $order ) {` +
				`return array( 'id' => $order->get_id(), 'key' => $order->get_order_key(), 'url' => $order->get_checkout_order_received_url() ); };` +
				`echo wp_json_encode( array( 'order' => $receipt( $order ), 'old' => $receipt( $old ), 'guest' => $receipt( $guest_order ), 'product' => get_the_title( ${PRODUCT} ) ) );`,
		]).trim()
	) as {
		order?: Receipt;
		old?: Receipt;
		guest?: Receipt;
		product?: string;
	};
	if (!created.order || !created.old || !created.guest || !created.product) {
		throw new Error('the confirmation-key fixture was not created');
	}
	return {
		owner,
		other,
		product: created.product,
		guestEmail,
		order: created.order,
		guest: created.guest,
		old: created.old,
	};
}

/** Removes a fixture's accounts and records, whatever the test did. */
function remove(fixture: { customers: Customer[]; orders: number[] }): void {
	const ids = fixture.customers.map((customer) => customer.id).join(',');
	if ('' === ids) {
		return;
	}
	wp([
		'eval',
		`foreach ( array( ${[...fixture.orders, 0].join(',')} ) as $order_id ) {` +
			`$order = wc_get_order( $order_id ); if ( $order ) { $order->delete( true ); } }` +
			`foreach ( array( ${ids} ) as $user_id ) {` +
			`require_once ABSPATH . 'wp-admin/includes/user.php'; wp_delete_user( $user_id ); } echo 'removed';`,
	]);
}

/** Signs in through the site's own form on the language's account page. */
async function signIn(
	page: Page,
	customer: Customer,
	account: string
): Promise<void> {
	await page.goto(instance().url + account);
	await page.fill('#username', customer.login);
	await page.fill('#password', PASSWORD);
	// PublicGuard's minimum fill time; every suite that posts through these
	// doors waits for it before submitting.
	await page.waitForTimeout(3_300);
	await page.locator('button[name="login"]').click();
	await page.waitForLoadState('load');
	await page.waitForFunction(
		() => document.querySelectorAll('a[href*="action=logout"]').length >= 1,
		null,
		{ timeout: 30_000 }
	);
}

/** The confirmation URL with the key replaced, or dropped. */
function withKey(url: string, key: string | null): string {
	const target = new URL(url);
	if (null === key) {
		target.searchParams.delete('key');
	} else {
		target.searchParams.set('key', key);
	}
	return target.toString();
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
		path: join(evidence, `${name}.png`),
		fullPage: true,
		animations: 'disabled',
	});
}

/** The inquiry page's folded reply details. */
for (const language of LANGUAGES) {
	for (const width of [1440, 390]) {
		test(`${language.lang} ${width}: a signed-in customer's reply details fold into one summary row`, async ({
			browser,
		}) => {
			test.setTimeout(120_000);
			const tag = `${language.lang}-${width}`;
			mkdirSync(evidence, { recursive: true });
			const customer = makeCustomer(tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, customer, language.account);
				await page.goto(instance().url + language.request);

				const details = page.locator('details.linker-inquiry-details');
				const summary = details.locator('summary');
				const fields = page.locator('.linker-inquiry-fields');
				await expect(summary).toBeVisible();
				// The ruling: the details are one row, closed, with the stored
				// name and address on it and the fields out of the way.
				expect(
					await details.evaluate(
						(el) => (el as HTMLDetailsElement).open
					),
					'the reply details are folded for a complete account'
				).toBe(false);
				await expect(fields).toBeHidden();
				await expect(summary).toContainText(language.summaryLabel);
				await expect(summary).toContainText('Maria Beispiel');
				await expect(summary).toContainText(customer.email);
				await expect(summary).toContainText(language.change);
				// The message stays the page's own open field.
				await expect(page.locator('#inquiry-message')).toBeVisible();
				// The guest-only surface is gone for a signed-in customer.
				await expect(page.locator('.linker-form-consent')).toBeHidden();
				await expect(
					page.locator('.linker-inquiry-guest')
				).toBeHidden();

				const folded = {
					open: false,
					summary: await text(
						page,
						'details.linker-inquiry-details summary'
					),
					fieldsVisible: await fields.isVisible(),
				};
				if (390 === width) {
					// The folded row is the shape this tier is judged on, so it
					// fits before the row is opened as well as after.
					expect(
						await page.evaluate(
							() => document.documentElement.scrollWidth
						),
						`the folded details fit ${width}px`
					).toBeLessThanOrEqual(width);
				}

				await summary.click();
				expect(
					await details.evaluate(
						(el) => (el as HTMLDetailsElement).open
					),
					'Change opens the stored reply details'
				).toBe(true);
				await expect(fields).toBeVisible();
				// Opened, the fields carry the account's own values.
				await expect(page.locator('#inquiry-name')).toHaveValue(
					'Maria Beispiel'
				);
				await expect(page.locator('#inquiry-email')).toHaveValue(
					customer.email
				);
				await expect(page.locator('#inquiry-company')).toHaveValue(
					'E2E Solar GmbH'
				);
				const opened = {
					open: true,
					name: await page.locator('#inquiry-name').inputValue(),
					email: await page.locator('#inquiry-email').inputValue(),
					company: await page
						.locator('#inquiry-company')
						.inputValue(),
				};

				if (390 === width) {
					expect(
						await page.evaluate(
							() => document.documentElement.scrollWidth
						),
						`the opened details fit ${width}px`
					).toBeLessThanOrEqual(width);
				}
				await shot(page, `summary-${tag}`);

				writeFileSync(
					join(evidence, `summary-${tag}.json`),
					JSON.stringify(
						{
							state: 'inquiry:signed-in-summary',
							language: language.lang,
							width,
							url: instance().url + language.request,
							folded,
							opened,
						},
						null,
						2
					)
				);
			} finally {
				await context.close();
				remove({ customers: [customer], orders: [] });
			}
		});
	}
}

/** The confirmation link: invalid, missing, expired and owner access. */
for (const language of LANGUAGES) {
	for (const width of [1440, 390]) {
		test(`${language.lang} ${width}: a bad, missing or foreign confirmation key leaks nothing and the owner still opens its inquiry`, async ({
			browser,
		}) => {
			test.setTimeout(240_000);
			const tag = `keys-${language.lang}-${width}`;
			mkdirSync(evidence, { recursive: true });
			const fixture = makeFixture(language, tag);
			const cases: Array<Record<string, unknown>> = [];
			const recoveries = [
				{
					name: 'invalid-key',
					url: withKey(fixture.order.url, 'wc_order_e2e_wrongkey'),
				},
				{ name: 'missing-key', url: withKey(fixture.order.url, null) },
				{
					name: 'unknown-order',
					url: withKey(
						fixture.order.url.replace(/\/(\d+)\//, '/999999991/'),
						null
					),
				},
			];
			const contexts: Array<
				Awaited<ReturnType<typeof browser.newContext>>
			> = [];
			const open = async (signedIn?: Customer) => {
				const context = await browser.newContext({
					viewport: { width, height: width === 390 ? 844 : 900 },
					reducedMotion: 'reduce',
				});
				contexts.push(context);
				await seedConsentCookies(context);
				const page = await context.newPage();
				if (signedIn) {
					await signIn(page, signedIn, language.account);
				}
				return { page };
			};
			/**
			 * The inquiry's data must not be in the page at all — the whole
			 * document, not only what renders, because a hidden leak is still a
			 * leak. The order key is the exception: a visitor who supplies it
			 * gets it echoed back inside the verification and sign-in forms'
			 * own fields, so only the cases that never carried a key assert its
			 * absence.
			 */
			const leakCheck = async (
				page: Page,
				name: string,
				keySupplied: boolean
			): Promise<boolean> => {
				const html = await page.evaluate(
					() => document.documentElement.outerHTML
				);
				const signals = [
					fixture.owner.email,
					'E2E Solar GmbH',
					fixture.product,
					fixture.guestEmail,
				];
				if (!keySupplied) {
					signals.push(fixture.order.key);
				}
				const found = signals.filter((signal) => html.includes(signal));
				expect(
					found,
					`${name} carries none of the inquiry's data in its document`
				).toEqual([]);
				return found.length > 0;
			};
			try {
				for (const entry of recoveries) {
					const { page } = await open();
					await page.goto(entry.url);
					const notice = page.locator(
						'.woocommerce-thankyou-order-received'
					);
					await expect(
						notice,
						`${entry.name} shows the recovery notice`
					).toBeVisible();
					expect(await text(page, '#theme-main')).toContain(
						language.recovery
					);
					await expect(
						page.locator('.linker-form-success')
					).toHaveCount(0);
					await leakCheck(page, entry.name, false);
					cases.push({
						name: entry.name,
						url: entry.url,
						notice: true,
						success: false,
						leak: false,
					});
					await shot(page, `${tag}-${entry.name}`);
				}

				// The correct key without the owner's session: WooCommerce's own
				// verification gate, and none of the inquiry's data.
				{
					const { page } = await open();
					await page.goto(fixture.guest.url);
					await expect(
						page.locator('form.woocommerce-verify-email'),
						'a guest inquiry asks the visitor to verify the address'
					).toBeVisible();
					expect(await text(page, '#theme-main')).toMatch(
						language.verify
					);
					await expect(
						page.locator('.woocommerce-thankyou-order-received')
					).toBeHidden();
					await leakCheck(page, 'guest-key-anonymous', false);
					cases.push({
						name: 'guest-key-anonymous',
						url: fixture.guest.url,
						gate: 'verify-email',
						notice: false,
						success: false,
						leak: false,
					});
					await shot(page, `${tag}-guest-key-anonymous`);
				}
				{
					const { page } = await open();
					await page.goto(fixture.order.url);
					await expect(
						page.locator('form.woocommerce-form-login'),
						'a customer-owned inquiry asks the visitor to sign in'
					).toBeVisible();
					expect(await text(page, '#theme-main')).toContain(
						language.gate
					);
					await expect(
						page.locator('.woocommerce-thankyou-order-received')
					).toBeHidden();
					await leakCheck(page, 'owner-key-anonymous', true);
					cases.push({
						name: 'owner-key-anonymous',
						url: fixture.order.url,
						gate: 'sign-in',
						notice: false,
						success: false,
						leak: false,
					});
					await shot(page, `${tag}-owner-key-anonymous`);
				}
				{
					const { page } = await open(fixture.other);
					await page.goto(fixture.order.url);
					// WooCommerce's gate notice, and deliberately no login form:
					// global/form-login.php returns for any signed-in user, so a
					// customer who is already signed in as somebody else reads
					// the generic gate and nothing more. The notice is Woo's own
					// generic wording — it never names the owner, which is what
					// keeps the order id unprobeable.
					expect(await text(page, '#theme-main')).toContain(
						language.gate
					);
					await expect(
						page.locator('form.woocommerce-form-login')
					).toHaveCount(0);
					await expect(
						page.locator('.woocommerce-thankyou-order-received')
					).toBeHidden();
					await expect(
						page.locator('.linker-form-success')
					).toHaveCount(0);
					await leakCheck(page, 'other-customer-key', true);
					cases.push({
						name: 'other-customer-key',
						url: fixture.order.url,
						gate: 'notice-only-signed-in',
						notice: false,
						success: false,
						leak: false,
					});
					await shot(page, `${tag}-other-customer-key`);
				}
				// The owner, and the owner of an inquiry older than a year:
				// the key is the order key and does not expire.
				for (const entry of [
					{ name: 'owner', receipt: fixture.order },
					{ name: 'owner-backdated', receipt: fixture.old },
				]) {
					const { page } = await open(fixture.owner);
					await page.goto(entry.receipt.url);
					const success = page.locator('.linker-form-success');
					await expect(
						success,
						`${entry.name} opens the inquiry confirmation`
					).toBeVisible();
					await expect(success).toContainText(language.success);
					await expect(success).toContainText(language.promise);
					await expect(
						page.locator('.woocommerce-form-login')
					).toHaveCount(0);
					await expect(
						page.locator('.woocommerce-thankyou-order-received')
					).toBeHidden();
					// The owner sees their own inquiry — and no payment line,
					// since an inquiry has none.
					expect(await text(page, '#theme-main')).toContain(
						fixture.product
					);
					expect(await text(page, '#theme-main')).not.toMatch(
						/payment method|Zahlungsart/i
					);
					cases.push({
						name: entry.name,
						url: entry.receipt.url,
						gate: null,
						notice: false,
						success: true,
						leak: false,
					});
					await shot(page, `${tag}-${entry.name}`);
				}

				if (390 === width) {
					// Every shape this phone-tier row stands for fits: the
					// recovery notice, both gates and the owner's confirmation.
					for (const context of contexts) {
						for (const page of context.pages()) {
							expect(
								await page.evaluate(
									() => document.documentElement.scrollWidth
								),
								`${await page.title()} fits ${width}px`
							).toBeLessThanOrEqual(width);
						}
					}
				}
				writeFileSync(
					join(evidence, `${tag}.json`),
					JSON.stringify(
						{
							state: 'inquiry:confirmation-key-invalid-expired-and-owner',
							language: language.lang,
							width,
							product: fixture.product,
							cases,
						},
						null,
						2
					)
				);
			} finally {
				for (const context of contexts) {
					await context.close();
				}
				remove({
					customers: [fixture.owner, fixture.other],
					orders: [
						fixture.order.id,
						fixture.guest.id,
						fixture.old.id,
					],
				});
			}
		});
	}
}
