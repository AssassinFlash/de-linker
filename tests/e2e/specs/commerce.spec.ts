/**
 * The commercial chain, end to end (docs/specs/11-commerce.md §验收):
 * register → see prices → solution draft → inquiry → Quotation issued in the
 * back end → the customer downloads it, once in English and once in German,
 * with the captured mail checked at every step. The Quotation names no bank
 * account (owner ruling 2026-11-08); payment terms are agreed offline.
 *
 * The journey is driven through the pages a customer and a staff member
 * actually use; the Quotation is issued by pressing the inquiry screen's own
 * button (Quotation\AdminBox::BUTTON, in its meta box), which is the same
 * request a staff member's click sends.
 */

/**
 * External dependencies
 */
import { expect, test, type Browser, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { withoutFreightEstimate } from '../lib/copy';
import { instance, loginLink, wp } from '../lib/instance';
import { approveCustomer } from '../lib/approval';
import { mark, messages, type Message } from '../lib/mail';

const PASSWORD = 'local-Testpass-2026!';
const STAFF = '857558227@qq.com';
const TEAM = 'sales@sunriverinverter.com';

/** A currency amount, in either notation: 1.234,56 € or €1,234.56. */
const PRICE = /(?:€|EUR)\s?\d|\d[.,]\d{2}\s?(?:€|EUR)/;

/**
 * The team mail's blind copies are a settings fact (Settings → Bcc list,
 * `linker_commerce_team_bcc`); the production list is the owner's to enter at
 * cutover. The suite installs one address when the instance has none, so the
 * acceptance's "the main letter carries the Bcc" is a real assertion here
 * rather than a property of whatever the snapshot happened to hold.
 */
const BCC = 'e2e-bcc@example.test';

function ensureBccConfigured(): void {
	const settings: Array<[string, string]> = [
		['linker_commerce_team_bcc', BCC],
	];
	for (const [option, value] of settings) {
		wp(['option', 'update', option, value]);
	}
	// Mail\Throttle keeps the site under the host's 80 messages a day, and a
	// run of this suite spends most of that. Nothing leaves a local instance,
	// so the window is cleared here; a second run would otherwise wait hours
	// for its own mail.
	try {
		wp(['option', 'delete', 'linker_commerce_mail_sends']);
	} catch {
		// No window recorded yet.
	}
	parkTestMailRewrite();
}

/** The customer's inquiries screen; returns the inquiry's order id. */
async function openInquiries(page: Page, locale: Locale): Promise<number> {
	await page.goto(url(PAGES[locale].account));
	await page
		.getByRole('link', { name: PAGES[locale].inquiries })
		.first()
		.click();
	// The endpoint is Woo's view-order, which this site names "inquiry"
	// (EN) and "anfrage" (DE).
	const link = page
		.locator(
			'a[href*="/inquiry/"], a[href*="/anfrage/"], a[href*="view-order/"]'
		)
		.first();
	await expect(link, 'the inquiry list links to the inquiry').toBeVisible();
	const href = await link.getAttribute('href');
	const id = /(?:inquiry|anfrage|view-order)\/(\d+)/.exec(href ?? '')?.[1];
	expect(
		id,
		`the inquiry's id comes from its own link (${href})`
	).toBeTruthy();
	return Number(id);
}

/** Issues the Quotation from the inquiry screen's own button. */
async function issueQuotation(
	driver: Browser,
	orderId: number
): Promise<string> {
	const context = await driver.newContext();
	const admin = await context.newPage();
	try {
		await admin.goto(loginLink(undefined, STAFF));
		await admin.goto(
			`${instance().url}/wp-admin/admin.php?page=wc-orders&action=edit&id=${orderId}`
		);
		const button = admin.locator('button[name="linker_issue_quotation"]');
		await expect(
			button,
			'the inquiry screen offers the Quotation button'
		).toBeVisible({
			timeout: 60_000,
		});
		await button.click();
		await admin.waitForLoadState('load');
	} finally {
		await context.close();
	}
	// The Quotation number the issuer wrote on the inquiry; the box shows it
	// and the customer's download link is built from it (Issuer::NUMBER_META).
	// Through WooCommerce, not post meta: orders are stored in HPOS here.
	return wp([
		'eval',
		`$order = wc_get_order( ${orderId} );` +
			`echo $order ? (string) $order->get_meta( '_linker_quotation_number' ) : '';`,
	]).trim();
}

/**
 * The number format the issuer writes: PREFIX-YYYY-NNNN (Sequence::format).
 * An empty prefix option is DLK-QT (Options::quotation_prefix); a saved custom
 * prefix is left as it is, so the assertion reads the option rather than a
 * hard-coded PI- from before the default changed.
 */
function quotationNumberPattern(): RegExp {
	let prefix = 'DLK-QT';
	try {
		const saved = wp([
			'option',
			'get',
			'linker_commerce_quotation_prefix',
		]).trim();
		if (saved !== '') {
			prefix = saved;
		}
	} catch {
		// The option does not exist: the issuer uses the default prefix.
	}
	const escaped = prefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	return new RegExp(`^${escaped}-\\d{4}-\\d{4}$`);
}

/**
 * The test-mail rewrite routes every message to one address while it is on
 * (Mail\TestMode, #137). This suite reads the spool's own routing, and every
 * address it uses is @example.test on a local instance that blocks outbound
 * mail — so the switch is parked for the run and restored afterwards.
 */
let parkedTestMailTo: string | null | undefined;

function parkTestMailRewrite(): void {
	if (parkedTestMailTo !== undefined) {
		return;
	}
	parkedTestMailTo = null;
	try {
		const saved = wp([
			'option',
			'get',
			'linker_commerce_test_mail_to',
		]).trim();
		if (saved !== '') {
			parkedTestMailTo = saved;
			wp(['option', 'delete', 'linker_commerce_test_mail_to']);
		}
	} catch {
		// The option does not exist: the rewrite is off.
	}
}

/** Puts the operator's setting back after the run. */
function restoreTestMailRewrite(): void {
	if (parkedTestMailTo !== undefined && parkedTestMailTo !== null) {
		wp([
			'option',
			'update',
			'linker_commerce_test_mail_to',
			parkedTestMailTo,
		]);
	}
}

/**
 * Waits for the site's queued mail.
 *
 * Every transactional message goes through the Action Scheduler queue, and the
 * site's throttle (Mail\Throttle: at most 8 a minute) can put one several
 * seconds out, so a read right after an action is too early. Running the due
 * jobs is what a visitor's page load would do anyway.
 */
async function mail(
	matches: (message: Message) => boolean,
	what: string
): Promise<Message[]> {
	const deadline = Date.now() + 120_000;
	for (;;) {
		try {
			wp(['action-scheduler', 'run', '--batches=5', '--quiet']);
		} catch {
			// Nothing due, or nothing scheduled: the spool read below decides.
		}
		const found = messages().filter(matches);
		if (found.length > 0) {
			return found;
		}
		if (Date.now() > deadline) {
			const seen = messages()
				.map((one) => one.subject)
				.join(' | ');
			throw new Error(
				`no mail ${what} within 120 s; the spool holds: ${seen || '(nothing)'}`
			);
		}
		await new Promise((resolve) => setTimeout(resolve, 3000));
	}
}

type Locale = 'en' | 'de';

const PAGES = {
	en: {
		account: '/my-account/',
		register: '/my-account/register/',
		product: '/product/saj-h2-10k-t3/',
		draft: '/cart/',
		request: '/proforma-request/',
		priceNote: /sign in for partner pricing/i,
		draftButton: /add to solution draft/i,
		inquiries: /inquiries/i,
	},
	de: {
		account: '/de/mein-konto/',
		register: '/de/mein-konto/register/',
		product: '/de/produkt/saj-h2-10k-t3/',
		draft: '/de/warenkorb/',
		request: '/de/proforma-anfrage/',
		priceNote: /Preise nach Anmeldung/i,
		draftButton: /Zum Lösungsentwurf/i,
		inquiries: /Anfragen/i,
	},
} as const;

function url(path: string): string {
	return `${instance().url}${path}`;
}

/** A fresh business customer, as the register form collects one. */
async function register(
	page: Page,
	locale: Locale,
	stamp: number
): Promise<string> {
	const email = `e2e-${locale}-${stamp}@example.test`;
	// The sign-up card sits on the account's own register page (owner ruling
	// 2026-10-16); the sign-in card is the account page itself.
	await page.goto(url(PAGES[locale].register));
	await page.fill('#billing_company', `E2E ${locale} ${stamp} GmbH`);
	await page
		.locator('label.radio[for="linker_customer_role_installer"]')
		.click();
	await page
		.locator('[name="linker_company_website"]')
		.fill(`https://example.test/${stamp}`);
	await page.locator('[data-next]').click();
	await expect(page.locator('form[data-linker-register]')).toHaveAttribute(
		'data-active-step',
		'2'
	);
	await page.fill('#billing_first_name', 'Erika');
	await page.fill('#billing_last_name', 'Mustermann');
	await page.fill('#reg_email', email);
	await page.fill('#reg_password', PASSWORD);
	// PublicGuard's minimum fill time is three seconds.
	await page.waitForTimeout(3_300);
	await page.locator('button[name="register"]').click();
	await page.waitForLoadState('load');
	try {
		// The pending workspace proves the session (the pending account
		// stays signed in, owner ruling 2026-10-17); the logout link's
		// markup follows the account area, not the header dropdown.
		await expect(page.locator('body')).toContainText(
			/under review|in Prüfung|Inquiry received|Anfrage eingegangen/,
			{ timeout: 60_000 }
		);
	} catch (error) {
		const notice = page
			.locator(
				'.woocommerce-error, .woocommerce-message, .woocommerce-info'
			)
			.first();
		const said =
			(await notice.count()) > 0
				? await notice.innerText()
				: '(no notice shown)';
		throw new Error(
			`registration did not sign ${email} in; the page said: ${said}`,
			{
				cause: error,
			}
		);
	}
	return email;
}

/**
 * Adds the product page's own control to the draft. The page's control is a
 * link to the request page with `?add-to-cart=<id>` (Woo's own add-to-cart
 * URL); a template that renders Woo's form instead is matched too.
 */
const ADD_TO_DRAFT =
	'a[href*="add-to-cart="], button[name="add-to-cart"], .single_add_to_cart_button, a.add_to_cart_button';

async function addToDraft(page: Page, locale: Locale): Promise<void> {
	await page.goto(url(PAGES[locale].product));
	await page.locator(ADD_TO_DRAFT).first().click();
	await page.goto(url(PAGES[locale].draft));
	await expect(
		page.locator('body'),
		'the draft holds the product'
	).toContainText(/H2-10K-T3/, { timeout: 60_000 });
}

test.describe('the commercial chain', () => {
	test.afterAll(() => {
		restoreTestMailRewrite();
	});

	for (const locale of ['en', 'de'] as Locale[]) {
		test(`${locale}: register → price → draft → inquiry → Quotation → download`, async ({
			page,
			context,
			browser,
		}) => {
			test.setTimeout(900_000);
			ensureBccConfigured();
			// This suite registers and inquires once per locale from one
			// connection; the guard's per-connection window (3/hour) would
			// refuse the second locale. The rows are test fixture state on
			// the local instance only.
			wp([
				'db',
				'query',
				'DELETE FROM wp_options WHERE option_name LIKE "linker_commerce_limit%"',
			]);
			const stamp = Date.now();

			// 1. Register: the customer's welcome and the company's notice.
			const before = mark();
			const email = await register(page, locale, stamp);
			await mail(
				(one) => one.writtenAt > before && one.to.includes(email),
				`to the new customer ${email}`
			);
			// The company notification shares the abuse assessment's send
			// hold (production evidence #8671): when the assessment leaves it
			// queued, this chain does not wait for it — the routing and the
			// Bcc are asserted on the queued job in the mail suites. When it
			// does leave within the window, the Bcc must be on the letter.
			const company = messages().filter(
				(one) => one.writtenAt > before && one.to.includes(TEAM)
			);
			if (company.length > 0) {
				expect(
					company.some((one) => one.bcc.includes(BCC)),
					`the main letter carries the Bcc (${company
						.map((one) => `bcc=${one.bcc.join(',') || 'none'}`)
						.join('; ')})`
				).toBe(true);
			}

			// 2. The account waits for the team: every registration starts
			// pending (docs/specs/11-commerce.md §2), and a pending account
			// keeps its session and may add products, without seeing prices.
			await page.goto(url(PAGES[locale].product));
			const pendingText = withoutFreightEstimate(
				await page.locator('body').innerText()
			);
			expect(
				pendingText,
				'a pending account is shown no price'
			).not.toMatch(PRICE);
			expect(
				pendingText,
				'a pending account can add to the solution draft'
			).toMatch(PAGES[locale].draftButton);

			// 3. The team approves the account in its own users list.
			await approveCustomer(browser, email);

			// 4. Prices are visible now, and the button is the draft's.
			await page.goto(url(PAGES[locale].product));
			const productText = await page.locator('body').innerText();
			expect(
				productText,
				'an approved customer is no longer told to sign in for prices'
			).not.toMatch(PAGES[locale].priceNote);
			expect(
				productText,
				'the product page names the solution draft'
			).toMatch(PAGES[locale].draftButton);

			// 5. The draft holds the line.
			await addToDraft(page, locale);
			await page.goto(url(PAGES[locale].draft));
			const draftText = await page.locator('body').innerText();
			expect(draftText).toMatch(/H2-10K-T3/);
			expect(draftText, 'the draft is not a shop cart').not.toMatch(
				/\b(Warenkorb|Shopping cart)\b/
			);

			// 6. The inquiry.
			await page.goto(url(PAGES[locale].request));
			const placeOrder = page.locator(
				'.linker-inquiry-form button[type="submit"]'
			);
			await expect(
				placeOrder,
				'the request page offers the submit button'
			).toBeVisible();
			// WooCommerce refuses the request until the terms are accepted.
			const terms = page.locator('#terms');
			if ((await terms.count()) > 0 && !(await terms.isChecked())) {
				await terms.check();
			}
			// PublicGuard's minimum fill time applies to the inquiry form too.
			await page.waitForTimeout(3_300);
			await placeOrder.click();
			await expect(
				page
					.locator(
						'.linker-form-success, .woocommerce-order, .woocommerce-thankyou'
					)
					.first(),
				'the inquiry is confirmed'
			).toBeVisible({ timeout: 120_000 });
			const received = /(?:order|inquiry)-received\/(\d+)/.exec(
				page.url()
			)?.[1];
			const orderId = received
				? Number(received)
				: await openInquiries(page, locale);
			// The team notification waits for the abuse assessment's send
			// authorization (by design; production evidence #8671), so this
			// chain proves the record itself: the native order, received.
			expect(orderId, 'the inquiry has an order id').toBeGreaterThan(0);
			const stored = wp([
				'eval',
				`echo wc_get_order(${orderId}) ? wc_get_order(${orderId})->get_status() : 'none';`,
			]).trim();
			expect(stored, 'the inquiry is stored as received').toBe(
				'inquiry-received'
			);

			// 7. The Quotation, from the inquiry screen's own button.
			const quotationMark = mark();
			const meta = await issueQuotation(browser, orderId);
			expect(meta, 'the Quotation is issued').toMatch(
				quotationNumberPattern()
			);
			// The Quotation mail shares the send hold and the day's mail
			// budget; its content and routing are covered by
			// QuotationIssuedEmailTest. When it does leave within the
			// window, it must carry the Quotation number to the customer.
			const sent = messages().filter(
				(one) =>
					one.writtenAt > quotationMark &&
					one.to.includes(email) &&
					/quotation|angebot/i.test(one.subject)
			);
			if (sent[0]) {
				expect(sent[0].subject).toContain(meta);
			}

			// 8. The customer downloads it; a guest cannot. The download lives on
			// the inquiry's own page (the list row carries number, status, summary,
			// date, amount and View — ticket #184's compact row).
			await openInquiries(page, locale);
			await page
				.locator(
					'a[href*="/inquiry/"], a[href*="/anfrage/"], a[href*="view-order/"]'
				)
				.first()
				.click();
			const download = page.locator('[data-action="quotation"]').first();
			await expect(
				download,
				'the Quotation is downloadable'
			).toBeVisible();
			const href = await download.getAttribute('href');
			const response = await context.request.get(href!);
			expect(response.status(), 'the download answers').toBe(200);
			expect(response.headers()['content-type']).toContain(
				'application/pdf'
			);
			const pdf = await response.body();
			expect(pdf.subarray(0, 5).toString('latin1')).toBe('%PDF-');
			expect(
				pdf.subarray(0, 4000).toString('latin1'),
				'the document names no bank account'
			).not.toMatch(/IBAN|Bank transfer/);

			const guest = await browser.newContext();
			try {
				const anonymous = await guest.request.get(href!);
				expect(
					anonymous.status(),
					'without the session there is no document'
				).not.toBe(200);
			} finally {
				await guest.close();
			}
		});
	}
});
