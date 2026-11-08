/**
 * Failure-injection states the state-matrix names: the protection client's
 * pending and error feedback on the add-to-draft link and the inquiry,
 * contact and draft-quantity submits, plus the notification queue the
 * successful submits must leave. Every failure is injected at the one seam
 * the client itself depends on (linker/v1/protection prepare/verify), so
 * the page shows its own real states — never a synthesized one.
 */
import { expect, test } from '@playwright/test';
import { applyTurnstileProfile, instance, wp } from '../lib/instance';
import { seedConsentCookies } from '../lib/consent';

const PROTECTION = /linker\/v1\/protection\/(prepare|verify)/;

// The protection client only intercepts in enforce mode; this suite needs it
// on (with the always-pass dummy Turnstile profile) for its whole run, and
// puts the instance's own constants back afterwards.
let restoreTurnstile: () => void = () => {};
test.beforeAll(() => {
	restoreTurnstile = applyTurnstileProfile();
});

test.afterAll(async () => {
	restoreTurnstile();
	// The successful submits must have queued their notifications; the
	// routing itself lives in the Outbox queue, asserted on the job rows
	// rather than on real mail (test mail discipline).
	const jobs = wp([
		'eval',
		`echo count(get_posts(array("post_type" => Linker\\Commerce\\Mail\\JobStore::POST_TYPE, "post_status" => "any", "posts_per_page" => 20, "fields" => "ids", "date_query" => array(array("after" => "30 minutes ago")))));`,
	]).trim();
	expect(
		Number(jobs),
		'the injected submissions queued their mail'
	).toBeGreaterThanOrEqual(2);
});

/** One route handler whose behavior a test flips, so no request is orphaned. */
function protectionSeam(page: import('@playwright/test').Page): {
	mode: () => string;
	set: (mode: 'hold' | 'abort' | 'pass') => void;
} {
	const state = { mode: 'pass', release: (() => {}) as () => void };
	page.route(PROTECTION, async (route) => {
		if (state.mode === 'hold') {
			await new Promise<void>((resolve) => {
				state.release = resolve;
			});
		}
		if (state.mode === 'abort') {
			await route.abort();
			return;
		}
		await route.continue();
	});
	return {
		mode: () => state.mode,
		set: (mode) => {
			if (state.mode === 'hold' && mode !== 'hold') state.release();
			state.mode = mode;
		},
	};
}

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

const LOCALES = {
	en: {
		request: '/proforma-request/',
		contact: '/contact/',
		product: '/product/saj-bu2-5-0-hv1/',
	},
	de: {
		request: '/de/proforma-anfrage/',
		contact: '/de/kontakt/',
		product: '/de/produkt/saj-bu2-5-0-hv1/',
	},
} as const;
const PENDING_TEXT = /verification|prüfung/i;
const REFUSED_TEXT =
	/no request has been sent|wurde noch keine anfrage gesendet/i;

for (const [locale, paths] of Object.entries(LOCALES)) {
	test(`${locale} 1440: add-to-draft pending, error and recovery`, async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto(`${instance().url}${paths.product}/`);
		const seam = protectionSeam(page);

		const add = page.locator('a[href*="add-to-cart="]:visible').first();
		const status = page.locator('p[role="status"]');

		// Pending: the verify answer is held back, the link's own status line
		// says a verification is being checked.
		seam.set('hold');
		await add.click();
		await expect(
			status.filter({ hasText: PENDING_TEXT }).first()
		).toBeVisible({ timeout: 20_000 });

		// Error: the held answer never arrives, the client names the failure and
		// promises no request was sent — and no Woo session appears.
		seam.set('abort');
		await expect(
			status.filter({ hasText: REFUSED_TEXT }).first()
		).toBeVisible({ timeout: 20_000 });
		expect(
			(await page.context().cookies()).some((c) =>
				c.name.startsWith('wp_woocommerce_session_')
			),
			'a refused verification adds nothing'
		).toBe(false);

		// Recovery: the seam answers again and the same link adds for real.
		seam.set('pass');
		await add.click();
		await expect
			.poll(
				async () =>
					(await page.context().cookies()).some((c) =>
						c.name.startsWith('wp_woocommerce_session_')
					),
				{
					timeout: 100_000,
					message: 'the recovered link adds the product',
				}
			)
			.toBe(true);
	});

	test(`${locale} 1440: inquiry submit is held by a failed verification, then sends`, async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		const seam = protectionSeam(page);
		await page.goto(`${instance().url}${paths.request}/`);
		const form = page.locator('form.linker-inquiry-form');
		await expect(form).toBeVisible();

		await form.locator('[name="name"]').fill('Failure Injection');
		const email = form.locator('[name="email"]');
		await email.fill(`injection-${Date.now()}@example.test`);
		await form.locator('[name="message"]').fill('Injection batch.');
		await form.locator('[name="consent"]').check();
		// PublicGuard's sourced minimum fill time is three seconds.
		await page.waitForTimeout(3_100);

		// The verification seam refuses: the form must not leave the page and
		// the visitor's typing stays.
		seam.set('abort');
		await form.locator('button[type="submit"]').click();
		await expect(
			page
				.locator('p[role="status"]')
				.filter({ hasText: REFUSED_TEXT })
				.first()
		).toBeVisible({ timeout: 20_000 });
		await expect(page).toHaveURL(
			locale === 'de' ? /proforma-anfrage/ : /proforma-request/
		);
		const typed = await email.inputValue();
		expect(typed).toContain('injection-');

		// The seam answers again: the same submit goes through to the receipt.
		// PublicGuard's minimum fill time has long passed by now.
		seam.set('pass');
		await form.locator('button[type="submit"]').click();
		await expect(page, {
			message: 'the inquiry reaches its receipt',
		}).toHaveURL(/inquiry-received|anfrage-eingegangen/, {
			timeout: 120_000,
		});
	});

	test(`${locale} 1440: contact submit is held by a failed verification, then sends`, async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		const seam = protectionSeam(page);
		await page.goto(`${instance().url}${paths.contact}/`);
		const form = page.locator('form.linker-contact-form');
		await expect(form).toBeVisible();
		await form.locator('[name="name"]').fill('Failure Injection');
		await form
			.locator('[name="email"]')
			.fill(`contact-injection-${Date.now()}@example.test`);
		await form
			.locator('[name="message"]')
			.fill('Injection batch 2026-11-08.');
		await form.locator('[name="consent"]').check();
		// PublicGuard's sourced minimum fill time is three seconds.
		await page.waitForTimeout(3_100);

		seam.set('abort');
		await form.locator('button[type="submit"]').click();
		await expect(
			page
				.locator('p[role="status"]')
				.filter({ hasText: REFUSED_TEXT })
				.first()
		).toBeVisible({ timeout: 20_000 });
		await expect(page).toHaveURL(
			locale === 'de' ? /\/kontakt\// : /\/contact\//
		);

		seam.set('pass');
		await form.locator('button[type="submit"]').click();
		await expect(
			page.locator('.linker-form-success').first(),
			'the contact message is confirmed on its own page'
		).toBeVisible({ timeout: 120_000 });
	});

	test(`${locale} 1440: draft quantity update is held by a failed verification`, async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto(`${instance().url}${paths.product}/`);
		await page.locator('a[href*="add-to-cart="]:visible').first().click();
		await expect
			.poll(
				async () =>
					(await page.context().cookies()).some((c) =>
						c.name.startsWith('wp_woocommerce_session_')
					),
				{ timeout: 100_000 }
			)
			.toBe(true);

		await page.goto(`${instance().url}${paths.request}/`);
		const qty = page.locator('input.qty').first();
		await expect(qty).toBeVisible();
		const loaded = await qty.inputValue();
		await qty.fill(String(Number(loaded) + 2));

		const seam = protectionSeam(page);
		seam.set('abort');
		await page
			.locator('button[name="update_cart"], input[name="update_cart"]')
			.first()
			.click();
		await expect(
			page
				.locator('p[role="status"]')
				.filter({ hasText: REFUSED_TEXT })
				.first()
		).toBeVisible({ timeout: 20_000 });

		// The held update never reached the server: a reload carries the
		// quantity the draft still has.
		await page.reload();
		await expect(page.locator('input.qty').first()).toHaveValue(loaded);
	});
}
