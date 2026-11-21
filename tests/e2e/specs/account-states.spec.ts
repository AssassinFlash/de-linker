/**
 * The account workspace's own states at 390 and in German (state-matrix
 * family account: inquiries-empty, inquiries-populated,
 * saved-solutions-empty, documents-empty, account-details, validation,
 * logout, customer-admin-explanation, owner-other-customer-guest-access).
 *
 * account.spec.ts walks several of these once at 1440 and in English; this
 * file walks them on the phone tier and in German too, because the workspace
 * offers one expandable account menu below 1024px (account.css) and
 * linker-i18n rewrites every endpoint slug (`anfragen/`, `dokumente/`,
 * `gespeicherte-loesungen/`, `kontodaten/`, `unternehmen/…`). The records a
 * state needs — a customer, its inquiry, its saved solution — are made
 * through WP-CLI for that one test and deleted with it; nothing is shared.
 */

/**
 * External dependencies
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync } from 'node:fs';
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
	compareProjects: string;
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
		compareProjects: 'Compare project options',
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
		compareProjects: 'Projektoptionen vergleichen',
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
				`wp_set_current_user( $id ); $order->add_product( wc_get_product( ${PRODUCT} ), 1 );` +
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

/** Stores an original file of each kind through the native file stores. */
function issueOwnerFiles(
	owner: Owner,
	locale: Language['lang']
): { number: string; quote_sha: string; report_sha: string; later: number } {
	return JSON.parse(
		wp([
			'eval',
			String.raw`
			$order = wc_get_order( ${owner.order} );
			foreach ( $order->get_items() as $item ) {
				$item->set_subtotal( '420.00' );
				$item->set_total( '420.00' );
				$item->save();
			}
			$order->set_billing_email( '${owner.email}' );
			$order->update_meta_data( \Linker\Commerce\Inquiry\OrderLocale::META, '${locale === 'de' ? 'de_DE_formal' : 'en_US'}' );
			$order->set_status( \Linker\Commerce\Inquiry\Statuses::QUOTATION );
			$order->save();

			$quote = wc_get_order( ${owner.order} );
			$quotes = new \Linker\Commerce\Account\PrivateFiles( \Linker\Commerce\Quotation\Issuer::DIRECTORY );
			$number = $quote->get_meta( \Linker\Commerce\Quotation\Issuer::NUMBER_META );
			$quote_path = $quotes->path( $quote->get_meta( \Linker\Commerce\Quotation\Issuer::FILE_META ) );
			if ( '' === $number || '' === $quote_path ) {
				throw new RuntimeException( 'Woo did not issue and store the quotation PDF' );
			}
			$reports = new \Linker\Commerce\Account\PrivateFiles( \Linker\Commerce\Account\SavedSolutions::REPORTS_DIRECTORY );
			$renderer = new \Linker\Commerce\Quotation\Renderer( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php' );
			$report = $renderer->pdf( '<h1>Saved solution archive</h1><p>Reference E2E-1142</p>' );
			$stored = $reports->write( ${owner.solution}, 'saved-solution-archive', $report );
			update_post_meta( ${owner.solution}, \Linker\Commerce\Account\SavedSolutions::REPORT_META, $stored );
			$later = wc_create_order( array( 'customer_id' => ${owner.id}, 'status' => 'cancelled' ) );
			echo wp_json_encode( [
				'number' => $number,
				'quote_sha' => hash_file( 'sha256', $quote_path ),
				'report_sha' => hash_file( 'sha256', $reports->path( $stored ) ),
				'later' => $later->get_id(),
			] );`,
		]).trim()
	);
}

function removeOwnerFiles(owner: Owner): void {
	wp([
		'eval',
		String.raw`
		(new \Linker\Commerce\Account\PrivateFiles( \Linker\Commerce\Quotation\Issuer::DIRECTORY ))->delete_owner( ${owner.order} );
		(new \Linker\Commerce\Account\PrivateFiles( \Linker\Commerce\Account\SavedSolutions::REPORTS_DIRECTORY ))->delete_owner( ${owner.solution} );`,
	]);
}

async function downloadPDF(
	page: Page,
	action: Locator,
	storedHash: string
): Promise<void> {
	const pending = page.waitForEvent('download');
	await action.click();
	const download = await pending;
	try {
		expect(await download.failure()).toBeNull();
		const pdf = readFileSync((await download.path())!);
		expect(pdf.subarray(0, 5).toString()).toBe('%PDF-');
		expect(createHash('sha256').update(pdf).digest('hex')).toBe(storedHash);
	} finally {
		await download.delete();
	}
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
	await page.goto(base() + (account.startsWith('/de/') ? '/de/' : '/'));
	await page.locator(`.hero-ops a[href$="${account}"]:visible`).click();
	await expect(page).toHaveURL(base() + account);
	await page.fill('#username', customer.login);
	await page.fill('#password', PASSWORD);
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

		test(`${tag}: the account keeps inquiry access while product prices follow its approval`, async ({
			page,
			context,
		}) => {
			const customer = makeCustomer('pending', `price-${tag}`);
			const reason =
				language.lang === 'de'
					? 'Bitte prüfen Sie Ihre Firmendaten.'
					: 'Please check your company details.';
			try {
				await page.setViewportSize({
					width,
					height: width === 390 ? 844 : 900,
				});
				await seedConsentCookies(context);
				await signIn(page, customer, language.account);
				const product = wp([
					'eval',
					`echo get_permalink(pll_get_post(${PRODUCT}, '${language.lang}'));`,
				]).trim();
				for (const state of ['pending', 'approved', 'restricted']) {
					if (state !== 'pending') {
						wp([
							'user',
							'meta',
							'update',
							String(customer.id),
							'linker_approval_status',
							state,
						]);
					}
					if (state === 'restricted') {
						wp([
							'user',
							'meta',
							'update',
							String(customer.id),
							'linker_approval_reason',
							reason,
						]);
					}
					await page.goto(product);
					const price = page.locator(
						width === 390
							? '.pdp-mobile-action .pdp-price'
							: '.pdp-purchase .pdp-price'
					);
					await expect(price).toBeVisible();
					const amount = price.locator('.woocommerce-Price-amount');
					if (state === 'approved') {
						await expect(amount.first()).toBeVisible();
					} else {
						await expect(amount).toHaveCount(0);
						await expect(price).toContainText(/\S/);
					}
					await page.goto(base() + language.account);
					const status = page.locator('.linker-account-status');
					if (state === 'restricted')
						await expect(status).toContainText(reason);
					if (state === 'pending')
						await expect(status).toContainText(
							language.pendingTitle
						);
					await expect(
						page.locator('.linker-account-mast a.is-primary')
					).toBeVisible();
					await shot(page, `${tag}-${state}-workspace`);
					await page
						.locator('.linker-account-mast a.is-primary')
						.click();
					await expect(
						page.locator('form.linker-inquiry-form')
					).toBeVisible();
					if (state === 'restricted')
						await expect(
							page.locator('.linker-inquiry-restriction')
						).toContainText(reason);
				}
			} finally {
				remove([customer]);
			}
		});

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
								? '.linker-account-mobile-menu > summary'
								: '.linker-account-sidebar'
						)
						.first()
				).toBeVisible();
				await expect(
					page.locator('.linker-account-main')
				).not.toContainText(/€|EUR/);

				await page
					.getByRole('link', {
						name:
							language.lang === 'de'
								? 'Neue Anfrage'
								: 'New inquiry',
						exact: true,
					})
					.click();
				await expect(
					page.locator('form.linker-inquiry-form')
				).toBeVisible();
				await expect(
					page.locator('form.linker-inquiry-form input[name="lang"]')
				).toHaveValue(language.lang);

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
				page.setDefaultTimeout(12_000);
				await signIn(page, customer, language.account);

				// A project made while signed in belongs to this account's own
				// principal, so the account row reads it back from the planner's
				// private index - never from a second store.
				await page.goto(base() + language.configuratorPath);
				const creation = page.getByRole('form', {
					name: language.compareProjects,
				});
				await expect(creation).toBeVisible();

				const projectName =
					language.lang === 'de' ? 'Projektname' : 'Project name';
				await creation
					.getByRole('textbox', { name: projectName })
					.fill(title);
				await creation
					.locator('select[name="country"]')
					.selectOption('DE');
				await creation
					.locator('input[name="location_label"]')
					.fill('Berlin');
				await creation.locator('button[type="submit"]').click();
				await expect(page).toHaveURL(/project=[a-f0-9]{32}/, {
					timeout: 60_000,
				});
				const projectId = new URL(page.url()).searchParams.get(
					'project'
				)!;
				await expect(
					page.getByRole('heading', {
						level: 1,
						name: title,
						exact: true,
					})
				).toBeVisible();

				await page.goto(
					base() + (language.lang === 'de' ? '/de/' : '/')
				);
				await page
					.locator(`.hero-ops a[href$="${language.account}"]:visible`)
					.click();
				await expect(page).toHaveURL(base() + language.account);
				await expectNoOverflow(page, width);
				await shot(page, `${language.lang}-${width}-overview`);
				const search = page.getByRole('search', {
					name:
						language.lang === 'de'
							? 'Gespeichertes Projekt finden'
							: 'Find a saved project',
				});
				await expect(search).toBeVisible();
				await search
					.getByRole('searchbox', { name: projectName })
					.fill(title);
				await search
					.getByRole('button', {
						name: language.lang === 'de' ? 'Suchen' : 'Search',
					})
					.click();
				await expect(page).toHaveURL(
					new RegExp(
						`${language.configuratorPath}\\?projects=1&project_search=`
					)
				);
				const row = page.getByRole('listitem').filter({
					has: page.getByRole('heading', {
						level: 3,
						name: title,
						exact: true,
					}),
				});
				const found = row.getByRole('button', {
					name:
						language.lang === 'de'
							? 'Projekt öffnen'
							: 'Open project',
					exact: true,
				});
				await expect(found).toBeVisible();
				await shot(page, `${language.lang}-${width}-solutions-search`);
				await found.click();
				await expect(page).toHaveURL(
					(url) => url.searchParams.get('project') === projectId
				);
				await expect(
					page.getByRole('heading', {
						level: 1,
						name: title,
						exact: true,
					})
				).toBeVisible();

				await page.goto(base() + language.solutions);
				const accountProject = page.getByRole('link', {
					name: new RegExp(title),
				});
				await expect(accountProject).toHaveAttribute(
					'href',
					new RegExp(`project=${projectId}#sc-project$`)
				);
				await accountProject.click();
				await expect(page).toHaveURL(
					(url) =>
						url.searchParams.get('project') === projectId &&
						url.hash === '#sc-project'
				);
				await expect(
					page.getByRole('heading', {
						level: 1,
						name: title,
						exact: true,
					})
				).toBeVisible();
				await expectNoOverflow(page, width);
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
				const contact = page.getByRole('region', {
					name:
						language.lang === 'de'
							? 'Ihre Ansprechperson'
							: 'Your contact person',
				});
				const shortcuts = page.locator('.linker-account-shortcuts');
				await expect(contact).toBeVisible();
				await expect(
					contact.locator('a[href^="mailto:"]')
				).toBeVisible();
				await expect(shortcuts.getByRole('link')).toHaveCount(4);
				await expect(
					shortcuts.getByRole('link', {
						name:
							language.lang === 'de'
								? 'Alle Projekte'
								: 'All projects',
						exact: true,
					})
				).toHaveAttribute('href', /[?&]projects=1$/);
				for (const path of [
					language.inquiries,
					language.solutions,
					language.documents,
				]) {
					await expect(
						shortcuts.locator(`a[href$="${path}"]`)
					).toBeVisible();
				}
				expect((await shortcuts.boundingBox())!.y).toBeLessThan(
					(await contact.boundingBox())!.y
				);

				await page
					.locator(
						'.linker-account-tile[data-status="inquiry-received"]'
					)
					.click();
				const otherLanguage = LANGUAGES.find(
					(entry) => entry.lang !== language.lang
				)!;
				await page
					.locator(
						`header a[data-linker-language-choice="${otherLanguage.lang}"]:visible`
					)
					.first()
					.click();
				await expect(page).toHaveURL(
					(url) =>
						url.pathname === otherLanguage.inquiries &&
						url.searchParams.get('inquiry-status') ===
							'inquiry-received'
				);
				await expect(
					page.locator(`[data-inquiry="${owner.order}"]`)
				).toBeVisible();
				await page.goto(base() + language.account);

				const inquiries = base() + language.inquiries;
				await shortcuts
					.locator(`a[href$="${language.inquiries}"]`)
					.click();
				await expect(page).toHaveURL(inquiries);

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
				const amountLabel =
					language.lang === 'de' ? 'Betrag' : 'Amount';
				if (width === 1440) {
					await expect(
						page
							.locator('.linker-account-inquiry-columns')
							.getByText(amountLabel, { exact: true })
					).toBeVisible();
				}
				const amount = row.locator('.linker-account-row-amount');
				await expect(amount).toContainText(`${amountLabel}:`);
				await expect(amount).toContainText(/[1-9]/);
				await expect(
					page.locator('.linker-account-empty'),
					'a populated list shows no empty state'
				).toHaveCount(0);
				await expectNoOverflow(page, width);
				await shot(
					page,
					`${language.lang}-${width}-inquiries-populated`
				);

				const detail = new RegExp(
					`${language.lang === 'de' ? 'anfrage' : 'inquiry'}/${owner.order}/`
				);
				const pill = row.locator('.linker-account-pill');
				await pill.evaluate((el) =>
					el.scrollIntoView({ block: 'center', behavior: 'instant' })
				);
				const status = await pill.boundingBox();
				expect(status).not.toBeNull();
				await page.mouse.click(
					status!.x + status!.width / 2,
					status!.y + status!.height / 2
				);
				await expect(page).toHaveURL(detail);

				await page.goto(inquiries);
				const number = row.locator('.linker-account-row-number');
				await number.focus();
				await expect(number).toBeFocused();
				await page.keyboard.press('Enter');
				await expect(page).toHaveURL(detail);

				await page.goto(inquiries);
				await row.locator('.linker-account-row-view').click();
				await expect(page).toHaveURL(detail);
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
				const nav = page.locator(
					width === 390
						? '.linker-account-mobile-menu'
						: '.linker-account-sidebar'
				);
				if (width === 390) {
					await nav.locator('summary').click();
				}
				await nav.locator(`a[href$="${language.details}"]`).click();
				await expect(page).toHaveURL(base() + language.details);
				if (width === 390) {
					await nav.locator('summary').click();
					await expect(
						nav.locator('a[href*="action=logout"]')
					).toBeVisible();
					await expect(
						nav.getByRole('link', {
							name:
								language.lang === 'de'
									? 'Unternehmen'
									: 'Company',
						})
					).toBeVisible();
					await nav.locator('summary').click();
				}

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
				const workspace = page.locator('.linker-account-content');
				if (width === 390) {
					await workspace
						.locator('.linker-account-mobile-menu summary')
						.click();
				}
				await workspace
					.getByRole('link', {
						name:
							language.lang === 'en' ? 'Company' : 'Unternehmen',
						exact: true,
					})
					.click();
				await expect(page).toHaveURL(base() + language.company);

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

				await page.locator('#billing_first_name').fill('Erika');
				await page.locator('#billing_last_name').fill('Mustermann');
				await page.locator('#billing_country').selectOption('DE');
				await page.locator('#billing_address_1').fill('Triftstraße 5');
				await page.locator('#billing_postcode').fill('80538');
				await page.locator('#billing_city').fill('München');
				await save.click();
				await expect(
					page.locator('.woocommerce-message').first()
				).toBeVisible();
				await page.goto(base() + language.company);
				await expect(company).toHaveValue('E2E States GmbH');
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

		test(`${tag}: the owner finds an inquiry and downloads both original account PDFs`, async ({
			browser,
		}) => {
			const { owner, other } = makeOwner(`files-${tag}`);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				isMobile: width === 390,
				hasTouch: width === 390,
				reducedMotion: 'reduce',
			});
			let later = 0;
			try {
				const files = issueOwnerFiles(owner, language.lang);
				later = files.later;
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, owner, language.account);
				const english = language.lang === 'en';
				const search = page
					.locator('.linker-account-main')
					.getByRole('search', {
						name: english ? 'Find an inquiry' : 'Anfrage finden',
					});
				await search
					.getByLabel(english ? 'Inquiry number' : 'Anfragenummer')
					.fill(`#${owner.order}`);
				await search
					.getByRole('button', {
						name: english ? 'Search' : 'Suchen',
					})
					.click();
				await expect(page).toHaveURL(
					(url) =>
						url.pathname === language.inquiries &&
						url.searchParams.get('inquiry_number') ===
							`#${owner.order}`
				);
				const exact = page.locator(
					`.linker-account-inquiry[data-inquiry="${owner.order}"]`
				);
				await expect(
					page.locator('.linker-account-inquiry[data-inquiry]')
				).toHaveCount(1);
				await expect(
					page.locator(`[data-inquiry="${later}"]`)
				).toHaveCount(0);
				await expectNoOverflow(page, width);
				await shot(page, `${tag}-inquiry-search`);
				const translated = LANGUAGES.find(
					(entry) => entry.lang !== language.lang
				)!;
				for (const entry of [translated, language]) {
					await page
						.locator(
							`header a[data-linker-language-choice="${entry.lang}"]:visible`
						)
						.first()
						.click();
					await expect(page).toHaveURL(
						(url) =>
							url.pathname === entry.inquiries &&
							url.searchParams.get('inquiry_number') ===
								`#${owner.order}`
					);
					await expect(exact).toBeVisible();
				}
				await exact.locator('.linker-account-row-view').click();
				await expect(
					page.locator('[data-action="quotation"]')
				).toBeVisible();

				await page.goto(base() + language.account);
				await page
					.locator(
						`.linker-account-content a[href$="${language.documents}"]:visible`
					)
					.first()
					.click();
				await expect(page).toHaveURL(base() + language.documents);
				const documents = page.locator('.linker-account-file-list');
				const quotation = documents
					.locator('.linker-account-doc')
					.filter({ hasText: files.number });
				const report = documents
					.locator('.linker-account-doc')
					.filter({ hasText: 'E2E saved solution' });
				await expect(quotation).toBeVisible();
				await expect(report).toBeVisible();
				await expectNoOverflow(page, width);
				await shot(page, `${tag}-owner-files`);
				await downloadPDF(
					page,
					quotation.getByRole('link'),
					files.quote_sha
				);
				await downloadPDF(
					page,
					report.getByRole('link'),
					files.report_sha
				);
			} finally {
				await context.close();
				removeOwnerFiles(owner);
				remove([owner, other], [owner.order, later]);
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

				await page.goto(
					`${base()}${language.inquiries}?inquiry_number=${owner.order}`
				);
				await expect(
					page.locator(`[data-inquiry="${owner.order}"]`)
				).toHaveCount(0);
				await expect(
					page.locator('.linker-account-empty-inquiries')
				).toContainText(
					language.lang === 'en'
						? 'No matching inquiries.'
						: 'Keine passende Anfrage gefunden.'
				);

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
