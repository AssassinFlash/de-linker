/**
 * The commercial chain, end to end (docs/specs/11-commerce.md §验收):
 * register → see prices → solution draft → inquiry → Proforma issued in the
 * back end → the customer downloads it, once in English and once in German,
 * with the captured mail checked at every step.
 *
 * The journey is driven through the pages a customer and a staff member
 * actually use; the Proforma is issued by pressing the inquiry screen's own
 * button (Proforma\AdminBox::BUTTON, in its meta box), which is the same
 * request a staff member's click sends.
 */

/**
 * External dependencies
 */
import { expect, test, type Browser, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, loginLink, wp } from '../lib/instance';
import { approveCustomer } from '../lib/approval';
import { mark, messages, type Message } from '../lib/mail';

const PASSWORD = 'local-Testpass-2026!';
const STAFF = '857558227@qq.com';
const TEAM = 'sales@de-linker.com';

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
		// The Proforma names the seller's bank account, and staff cannot issue
		// one without it (Proforma\Issuer::blocker). The production values are
		// the owner's to enter at cutover; an instance that has none gets the
		// test's, so "issue the Proforma" is a real step here.
		['linker_commerce_bank_holder', 'Linker Technology GmbH'],
		['linker_commerce_bank_name', 'E2E Testbank'],
		['linker_commerce_bank_iban', 'DE02120300000000202051'],
		['linker_commerce_bank_bic', 'BYLADEM1001'],
	];
	for (const [option, value] of settings) {
		try {
			if (wp(['option', 'get', option]).trim() !== '') {
				continue;
			}
		} catch {
			// The option does not exist yet: that is the case this fills.
		}
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
		product: '/product/saj-h2-10k-t3/',
		draft: '/cart/',
		request: '/proforma-request/',
		priceNote: /sign in for partner pricing/i,
		draftButton: /add to solution draft/i,
		inquiries: /inquiries/i,
	},
	de: {
		account: '/de/mein-konto/',
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
	await page.goto(url(PAGES[locale].account));
	await page.fill('#billing_company', `E2E ${locale} ${stamp} GmbH`);
	// The role select carries select2, so its native element cannot be
	// clicked; the value is what the form posts either way.
	await page.evaluate(() => {
		const select = document.querySelector<HTMLSelectElement>(
			'#linker_customer_role'
		);
		if (select && !select.value) {
			select.value =
				[...select.options]
					.map((option) => option.value)
					.find((value) => value !== '') ?? '';
		}
	});
	await page.fill('#billing_first_name', 'Erika');
	await page.fill('#billing_last_name', 'Mustermann');
	await page.selectOption('#billing_country', 'DE');
	await page.fill('#billing_address_1', 'Triftstraße 5');
	await page.fill('#billing_postcode', '80538');
	await page.fill('#billing_city', 'München');
	await page.fill('#reg_email', email);
	await page.fill('#reg_password', PASSWORD);
	// Submitted with the keyboard: the button is focused and Enter pressed.
	// A synthetic pointer click on this button does not run the form's
	// submission in this build (measured 2026-10-11: `elementFromPoint` at the
	// button's own centre is the button, the click event arrives, no `submit`
	// fires; the same click on the login button right above it does submit,
	// and a DOM-level `click()` does too). Real input is what the suite uses:
	// `requestSubmit` would bypass the page's own pipeline entirely, and a
	// synthetic click that silently does nothing would make this case vacuous.
	await page.locator('button[name="register"]').focus();
	await page.keyboard.press('Enter');
	await page.waitForLoadState('load');
	try {
		await expect(
			page.locator('a[href*="customer-logout"]'),
			'the customer is signed in after registering'
		).toBeVisible({ timeout: 60_000 });
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

/** The customer's inquiries screen; returns the inquiry's order id. */
async function openInquiries(page: Page, locale: Locale): Promise<number> {
	await page.goto(url(PAGES[locale].account));
	await page
		.getByRole('link', { name: PAGES[locale].inquiries })
		.first()
		.click();
	// The endpoint is Woo's view-order, which this site names "inquiry".
	const link = page
		.locator('a[href*="/inquiry/"], a[href*="view-order/"]')
		.first();
	await expect(link, 'the inquiry list links to the inquiry').toBeVisible();
	const href = await link.getAttribute('href');
	const id = /(?:inquiry|view-order)\/(\d+)/.exec(href ?? '')?.[1];
	expect(
		id,
		`the inquiry's id comes from its own link (${href})`
	).toBeTruthy();
	return Number(id);
}

/** Issues the Proforma from the inquiry screen's own button. */
async function issueProforma(
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
		const button = admin.locator('button[name="linker_issue_proforma"]');
		await expect(
			button,
			'the inquiry screen offers the Proforma button'
		).toBeVisible({
			timeout: 60_000,
		});
		await button.click();
		await admin.waitForLoadState('load');
	} finally {
		await context.close();
	}
	// The Proforma number the issuer wrote on the inquiry; the box shows it
	// and the customer's download link is built from it (Issuer::NUMBER_META).
	// Through WooCommerce, not post meta: orders are stored in HPOS here.
	return wp([
		'eval',
		`$order = wc_get_order( ${orderId} );` +
			`echo $order ? (string) $order->get_meta( '_linker_proforma_number' ) : '';`,
	]).trim();
}

/**
 * The number format the issuer writes: PREFIX-YYYY-NNNN (Sequence::format).
 * An empty prefix option is DLK-PF (Options::proforma_prefix); a saved custom
 * prefix is left as it is, so the assertion reads the option rather than a
 * hard-coded PI- from before the default changed.
 */
function proformaNumberPattern(): RegExp {
	let prefix = 'DLK-PF';
	try {
		const saved = wp([
			'option',
			'get',
			'linker_commerce_proforma_prefix',
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
	for (const locale of ['en', 'de'] as Locale[]) {
		test(`${locale}: register → price → draft → inquiry → Proforma → download`, async ({
			page,
			context,
			browser,
		}) => {
			test.setTimeout(900_000);
			ensureBccConfigured();
			const stamp = Date.now();

			// 1. Register: the customer's welcome and the company's notice.
			const before = mark();
			const email = await register(page, locale, stamp);
			await mail(
				(one) => one.writtenAt > before && one.to.includes(email),
				`to the new customer ${email}`
			);
			const company = await mail(
				(one) => one.writtenAt > before && one.to.includes(TEAM),
				'the company, about the new customer'
			);
			expect(
				company.some((one) => one.bcc.includes(BCC)),
				`the main letter carries the Bcc (${company
					.map((one) => `bcc=${one.bcc.join(',') || 'none'}`)
					.join('; ')})`
			).toBe(true);

			// 2. The account waits for the team: every registration starts
			// pending (docs/specs/11-commerce.md §2), and a pending account
			// reads the site like a guest — no price, no draft button.
			await page.goto(url(PAGES[locale].product));
			const pendingText = await page.locator('body').innerText();
			expect(
				pendingText,
				'a pending account is shown no price'
			).not.toMatch(PRICE);
			expect(
				pendingText,
				'a pending account is not offered the draft'
			).not.toMatch(PAGES[locale].draftButton);

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
			const inquiryMark = mark();
			await page.goto(url(PAGES[locale].request));
			const placeOrder = page.locator('#place_order');
			await expect(
				placeOrder,
				'the request page offers the submit button'
			).toBeVisible();
			// WooCommerce refuses the request until the terms are accepted.
			const terms = page.locator('#terms');
			if ((await terms.count()) > 0 && !(await terms.isChecked())) {
				await terms.check();
			}
			await placeOrder.click();
			await expect(
				page
					.locator('.woocommerce-order, .linker-confirmation')
					.first(),
				'the inquiry is confirmed'
			).toBeVisible({ timeout: 120_000 });
			const received = /order-received\/(\d+)/.exec(page.url())?.[1];
			const orderId = received
				? Number(received)
				: await openInquiries(page, locale);
			await mail(
				(one) => one.writtenAt > inquiryMark && one.to.includes(email),
				`to ${email} about the inquiry`
			);
			await mail(
				(one) => one.writtenAt > inquiryMark && one.to.includes(TEAM),
				'the company, about the inquiry'
			);

			// 7. The Proforma, from the inquiry screen's own button.
			const proformaMark = mark();
			const meta = await issueProforma(browser, orderId);
			expect(meta, 'the Proforma is issued').toMatch(
				proformaNumberPattern()
			);
			await mail(
				(one) =>
					one.writtenAt > proformaMark &&
					one.to.includes(email) &&
					one.subject.toLowerCase().includes('proforma'),
				`to ${email} with the Proforma`
			);

			// 8. The customer downloads it; a guest cannot.
			await openInquiries(page, locale);
			const download = page
				.locator('a[href*="linker-document=proforma"]')
				.first();
			await expect(
				download,
				'the Proforma is downloadable'
			).toBeVisible();
			const href = await download.getAttribute('href');
			const response = await context.request.get(href!);
			expect(response.status(), 'the download answers').toBe(200);
			expect(response.headers()['content-type']).toContain(
				'application/pdf'
			);
			const pdf = await response.body();
			expect(pdf.subarray(0, 5).toString('latin1')).toBe('%PDF-');

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
