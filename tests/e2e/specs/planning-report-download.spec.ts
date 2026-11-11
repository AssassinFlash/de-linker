/**
 * The customer's planning report download: the one channel through which an
 * inquiry's report reaches the customer after they send it.
 *
 * Read off the surfaces a customer uses — the inquiry page's own link, and the
 * address that link names — rather than inferred:
 *
 * - The inquiry page offers "Download PDF" at the address the receipt emails,
 *   and the order key in it is the customer's own possession.
 * - The signed-in owner reads the file from their session as well; the key is
 *   a convenience, not the identity.
 * - Everyone else gets one answer: an anonymous visitor, a visitor holding a
 *   wrong key, and a different signed-in customer all read "not available".
 * - A report the engine no longer has is unavailable, and bytes that are not
 *   the frozen PDF are refused instead of served as a file.
 *
 * The fixture writes the stored context exactly as the planner writes it and
 * stubs only the engine's two calls; the inquiry page, the route, the Tools
 * reader and every hash comparison are the shipped code.
 */

/**
 * External dependencies
 */
import {
	expect,
	test,
	type Browser,
	type BrowserContext,
	type Page,
} from '@playwright/test';

/**
 * Internal dependencies
 */
import { seedConsentCookies } from '../lib/consent';
import { instance, REPO_ROOT, wp } from '../lib/instance';

const fixture = `${REPO_ROOT}/tests/e2e/fixtures/planning-report.php`;
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);

const PASSWORD = 'e2e-Report-Access-2026!';
/** The published inverter the fixture inquiry carries. */
const PRODUCT = 4107;

const MISSING = 'This document is not available.';

interface Inquiry {
	customer: number;
	order: number;
	handoff: string;
	key: string;
}

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

/** Signs in through the site's own form on the account page. */
async function signIn(page: Page, login: string): Promise<void> {
	await page.goto(`${instance().url}/my-account/`);
	await page.fill('#username', login);
	await page.fill('#password', PASSWORD);
	// PublicGuard's minimum fill time; every suite posting through these doors
	// waits for it before submitting.
	await page.waitForTimeout(3_300);
	await page.locator('button[name="login"]').click();
	await page.waitForLoadState('load');
	await page.waitForFunction(
		() => document.querySelectorAll('a[href*="action=logout"]').length >= 1,
		null,
		{ timeout: 30_000 }
	);
}

/** The report's address as the inquiry page prints it. */
async function reportHref(page: Page, order: number): Promise<string> {
	await page.goto(`${instance().url}/my-account/inquiry/${order}/`);
	const link = page.getByRole('link', { name: 'Download PDF' }).first();
	await expect(link, 'the inquiry offers its report').toBeVisible();
	const href = await link.getAttribute('href');
	expect(href, 'the link names a download address').toBeTruthy();
	return href!;
}

/** A fresh, signed-out browser with its own request context. */
async function signedOut(browser: Browser): Promise<BrowserContext> {
	return browser.newContext({ baseURL: instance().url });
}

test('the owner reads the frozen report and everyone else is refused', async ({
	browser,
	context,
}) => {
	const login = `e2e-report-${Date.now()}`;
	const inquiry = JSON.parse(
		run('setup', login, PASSWORD, login, String(PRODUCT))
	) as Inquiry;
	const other = Number(run('customer', `${login}-other`, PASSWORD).trim());
	try {
		const page = await context.newPage();
		await signIn(page, login);

		// The inquiry page offers the report at the address the receipt emails.
		const href = await reportHref(page, inquiry.order);
		expect(href, 'the link carries the order key').toContain(
			`key=${inquiry.key}`
		);
		expect(href, 'the link names this inquiry').toContain(
			`/inquiries/${inquiry.order}/planning-report/${inquiry.handoff}`
		);

		// The owner's session reads the file, with or without the key.
		const owner = await context.request.get(href);
		expect(owner.status(), 'the owner reads the report').toBe(200);
		expect(owner.headers()['content-type']).toContain('application/pdf');
		expect(owner.headers()['content-disposition']).toContain(
			`attachment; filename="linker-planning-${inquiry.order}.pdf"`
		);
		expect(owner.headers()['cache-control']).toContain('no-store');
		expect(owner.headers()['referrer-policy']).toBe('no-referrer');
		expect(owner.headers()['x-content-type-options']).toBe('nosniff');
		expect(
			(await owner.body()).subarray(0, 5).toString(),
			'the body is the PDF itself'
		).toBe('%PDF-');

		// The key is a bearer grant: whoever holds the emailed link can read the
		// report, signed in or not — that is what lets a customer download it
		// from the receipt without first signing in. It grants this frozen
		// report and nothing else (no project, no editing, no prices).
		//
		// A cookie alone is not a session here: WordPress does not authenticate
		// a REST request from a cookie without its nonce, so this owner's own
		// browser sending the cookie and no nonce is a guest — and without the
		// key a guest reads nothing. The signed-in grant is covered where a
		// real session exists (PlanningReportDownloadTest in PHP).
		const anonymous = await signedOut(browser);
		try {
			const bearer = await anonymous.request.get(href);
			expect(
				bearer.status(),
				'the keyed link works for whoever holds it'
			).toBe(200);
			expect(
				(await bearer.body()).subarray(0, 5).toString(),
				'the bearer reads the same frozen PDF'
			).toBe('%PDF-');

			const withoutKey = await anonymous.request.get(
				href.slice(0, href.indexOf('?'))
			);
			expect(
				withoutKey.status(),
				'a guest without the key reads nothing'
			).toBe(404);
			expect(await withoutKey.text()).toContain(MISSING);

			const wrong = await anonymous.request.get(
				href.replace(`key=${inquiry.key}`, `key=${'a'.repeat(32)}`)
			);
			expect(wrong.status(), 'a wrong key reads nothing').toBe(404);
			expect(await wrong.text()).toContain(MISSING);
		} finally {
			await anonymous.close();
		}

		// Another signed-in customer without the key reads nothing either, and
		// the answer never confirms that the inquiry or its report exists.
		const second = await signedOut(browser);
		try {
			const foreignPage = await second.newPage();
			await signIn(foreignPage, `${login}-other`);
			for (const address of [
				href.slice(0, href.indexOf('?')),
				`${instance().url}/wp-json/linker/v1/inquiries/${inquiry.order}/planning-report/${inquiry.handoff}?key=${'a'.repeat(32)}`,
				`${instance().url}/wp-json/linker/v1/inquiries/${inquiry.order}/planning-report/${'b'.repeat(32)}?key=${inquiry.key}`,
				`${instance().url}/wp-json/linker/v1/inquiries/999999/planning-report/${inquiry.handoff}?key=${inquiry.key}`,
			]) {
				const refused = await second.request.get(address);
				expect(refused.status(), address).toBe(404);
				expect(await refused.text(), address).toContain(MISSING);
			}
			expect(other).toBeGreaterThan(0);
		} finally {
			await second.close();
		}
	} finally {
		run(
			'cleanup',
			String(inquiry.order),
			String(inquiry.customer),
			String(other)
		);
	}
});

test('a withdrawn report and foreign bytes are refused', async ({
	context,
	page,
}) => {
	const login = `e2e-report-missing-${Date.now()}`;
	const inquiry = JSON.parse(
		run('setup', login, PASSWORD, login, String(PRODUCT))
	) as Inquiry;
	try {
		await signIn(page, login);
		const href = await reportHref(page, inquiry.order);

		run('answer', 'refuse_handoff');
		const withdrawn = await context.request.get(href);
		expect(withdrawn.status(), 'a withdrawn report is unavailable').toBe(
			404
		);

		run('answer', 'replace_content');
		const replaced = await context.request.get(href);
		expect(
			replaced.status(),
			'bytes that are not the frozen PDF are refused'
		).toBe(503);
		expect(await replaced.text()).not.toContain('%PDF-');
	} finally {
		run('cleanup', String(inquiry.order), String(inquiry.customer));
	}
});
