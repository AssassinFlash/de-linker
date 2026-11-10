/** Guest public doors across a Woo session-cookie transition (#246, round 2). */
import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import {
	applyTurnstileProfile,
	instance,
	REPO_ROOT,
	wp,
} from '../lib/instance';

const evidence = join(
	REPO_ROOT,
	'.scratch/e2e-shots/public-inquiry',
	process.env.LINKER_246_RUN ?? 'latest'
);
const fixture = join(REPO_ROOT, 'tests/e2e/fixtures/public-inquiry.php');
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);

// This suite answers a real browser challenge on every submit, so the instance
// must be in the local Turnstile acceptance configuration while it runs. The
// profile is applied here and put back afterwards: leaving `enforce` behind
// would refuse every other suite's public-door submissions on this instance.
let restoreTurnstile: () => void = () => {};
test.beforeAll(() => {
	restoreTurnstile = applyTurnstileProfile();
});
test.afterAll(() => {
	restoreTurnstile();
});

// The shared protection counters (contact/inquiry doors) are per-instance and
// a 32-test sweep exhausts them mid-suite - the contact door then refuses its
// own verification dispatch. Reset the two public-door counters before each
// test so every shape is judged on its own merits (the genie-hero suite's
// freshCounters discipline).
test.beforeEach(() => {
	wp([
		'eval',
		"global $wpdb; $wpdb->query( \"DELETE FROM {$wpdb->options} WHERE option_name LIKE 'linker\\_commerce\\_limit\\_public\\_connection%' OR option_name LIKE 'linker\\_commerce\\_limit\\_public\\_receipts%' OR option_name LIKE 'linker\\_tools\\_limit\\_genie\\_contact%'\" );",
	]);
});

// Each step below states its own bound. This is their sum with margin — the
// cookie handshake (100 s), the submit's success notice (60 s), one explicit
// assessment run (3 × the claimed model attempt), plus page loads and evidence.
test.setTimeout(300_000);
for (const language of ['en', 'de']) {
	for (const width of [1440, 390]) {
		for (const door of ['contact', 'request']) {
			for (const capped of [false, true]) {
				test(`${language} ${width} ${door} ${capped ? 'capped' : 'receipt'}: fresh guest can submit after Woo creates its cookie`, async ({
					browser,
				}) => {
					expect(instance().url).toMatch(
						/^http:\/\/127\.0\.0\.1:\d+$/
					);
					const email = `tester246-${language}-${width}-${door}-${Date.now()}@example.test`;
					// An aborted earlier run can leave the fixture installed
					// (a setup failure bypasses this test's cleanup), and the
					// fixture refuses to install over stale state; clear it
					// first. Cleanup is a no-op on a clean instance.
					run('cleanup');
					const setup = JSON.parse(
						run('setup', email, capped ? 'capped' : 'receipt')
					);
					const context = await browser.newContext({
						viewport: { width, height: 900 },
					});
					try {
						expect(await context.cookies()).toEqual([]);
						const page = await context.newPage();
						// A fresh visitor meets the cookie-choice panel; on a
						// narrow viewport it covers the page, so a real customer
						// answers it before interacting (either answer works;
						// rejecting keeps the run to essential cookies).
						const dismissCookies = async (
							target: import('@playwright/test').Page
						) => {
							const reject = target.getByRole('button', {
								name: /reject all|alle ablehnen/i,
							});
							if (
								await reject
									.isVisible({ timeout: 2_000 })
									.catch(() => false)
							) {
								await reject.click();
							}
						};
						const path =
							door === 'contact'
								? language === 'de'
									? '/de/kontakt/'
									: '/contact/'
								: language === 'de'
									? '/de/proforma-anfrage/'
									: '/proforma-request/';
						await page.goto(`${instance().url}${path}`);
						await dismissCookies(page);
						const form = page.locator(
							door === 'contact'
								? 'form.linker-contact-form'
								: 'form.linker-inquiry-form'
						);
						await expect(form).toBeVisible();
						const before = (await context.cookies()).map(
							(c) => c.name
						);
						expect(
							before.some((name) =>
								name.startsWith('wp_woocommerce_session_')
							)
						).toBe(false);
						// A second tab adding a product can establish Woo's cookie
						// after render. The public-admission guard refuses
						// unproven cart writes (Protection\Draft::native()
						// rejects a bare GET add-to-cart), so the real customer
						// path is the product page's "Add to solution draft"
						// link: the protection client intercepts it, supplies
						// the proof, posts the add and Woo creates the session
						// cookie.
						const tab = await context.newPage();
						try {
							await tab.goto(
								`${instance().url}/?p=${setup.product}`
							);
							await dismissCookies(tab);
							// The product page renders the add link in three
							// places; on a narrow viewport only the sticky
							// bottom bar's copy is visible.
							await tab
								.locator('a[href*="add-to-cart="]:visible')
								.first()
								.click();
							// A verification that fails here leaves the link
							// unsubmitted and the cookie absent, which would
							// otherwise look like a slow Woo session. Capture
							// the protection surface's own state so a failure
							// names its cause instead of only timing out.
							const sessionReady = await expect
								.poll(
									async () =>
										(await context.cookies()).some(
											(cookie) =>
												cookie.name.startsWith(
													'wp_woocommerce_session_'
												)
										),
									{ timeout: 100_000 }
								)
								.toBe(true)
								.then(() => true)
								.catch(() => false);
							if (!sessionReady) {
								const diagnosis = await tab.evaluate(() => {
									const widget =
										document.querySelector<HTMLElement>(
											'[data-linker-verification-state]'
										);
									const status =
										document.querySelector<HTMLElement>(
											'[role="status"]'
										);
									return {
										state:
											widget?.dataset
												.linkerVerificationState ?? '',
										error:
											widget?.dataset
												.linkerVerificationError ?? '',
										message: (
											status?.textContent ?? ''
										).trim(),
									};
								});
								throw new Error(
									`the add-to-cart link never produced a Woo session cookie; protection state=${JSON.stringify(diagnosis)}`
								);
							}
						} finally {
							await tab.close();
						}
						const after = (await context.cookies()).map(
							(c) => c.name
						);
						expect(
							after.some((name) =>
								name.startsWith('wp_woocommerce_session_')
							)
						).toBe(true);
						await form
							.locator('[name="name"]')
							.fill('246 Browser Tester');
						await form.locator('[name="email"]').fill(email);
						await form
							.locator('[name="message"]')
							.fill('Please contact me about this product.');
						await form.locator('[name="consent"]').check();
						// PublicGuard's sourced minimum fill time is three seconds.
						await page.waitForTimeout(3_100);
						await form.locator('[type="submit"]').click();
						if (door === 'request') {
							// The second tab's verified add changed the draft
							// after this page rendered; the product answers
							// with its review notice and the customer sends
							// again on the refreshed draft. Each submit first
							// completes a real browser challenge, and German
							// renders soft hyphens, so compare the alerts'
							// own text with those stripped.
							await expect
								.poll(
									async () =>
										page
											.evaluate(() =>
												Array.from(
													document.querySelectorAll(
														'[role="alert"]'
													)
												).some((el) =>
													/draft changed|hat sich geändert/i.test(
														(
															el.textContent ?? ''
														).replace(/\u00AD/g, '')
													)
												)
											)
											.catch(() => false),
									{ timeout: 60_000 }
								)
								.toBe(true);
							await form.locator('[name="consent"]').check();
							await form.locator('[type="submit"]').click();
						}
						await expect(
							page.locator('.linker-form-success')
						).toBeVisible({ timeout: 60_000 });
						const pending = JSON.parse(run('read')) as {
							orders: Array<{
								status: string;
								customer: number;
								source: string;
								skipped: string;
								items: number;
								authorization: {
									status?: string;
									team_only?: boolean;
									jobs?: string[];
								};
							}>;
							mail: Array<{ to: string[]; subject: string }>;
						};
						expect(pending.orders).toHaveLength(1);
						const pendingOrder = pending.orders[0];
						if (!pendingOrder)
							throw new Error('Missing pending order');
						expect(pendingOrder.customer).toBe(0);
						expect(pendingOrder.items).toBe(
							door === 'request' ? 1 : 0
						);
						expect(pendingOrder.status).toBe('inquiry-received');
						expect(pendingOrder.source).toBe(
							door === 'contact' ? 'contact' : 'inquiry'
						);
						// The fixture blocks both the opportunistic wake and
						// Action Scheduler. This read is one consistent pending
						// snapshot, not a race against an empty post-delivery
						// Outbox.
						expect(pendingOrder.skipped).toBe('assessment_pending');
						expect(pendingOrder.authorization.status).toBe(
							'pending'
						);
						expect(pending.mail).toHaveLength(0);
						if (capped) {
							// The first page cannot fabricate a no-receipt claim
							// for the contact door: under enforce the receipt
							// budget decides at the assessment handoff, so the
							// contact door shows its plain sent copy; the
							// request page names the deferred no-receipt notice.
							// Assert the notice element itself — visible, with
							// its own rendered text normalized (soft hyphens
							// come from the browser, not the source string).
							const notice =
								language === 'de'
									? door === 'contact'
										? 'Vielen Dank. Ihre Nachricht liegt beim Linker-Team.'
										: 'Es wurde keine Bestätigungs-E-Mail versendet.'
									: door === 'contact'
										? 'Thank you. Your message is with the Linker team.'
										: 'We have not sent a confirmation email.';
							const noticeElement =
								door === 'contact'
									? page
											.locator('.linker-form-success p')
											.first()
									: page.locator('p.linker-receipt-notice');
							await expect(noticeElement).toBeVisible({
								timeout: 60_000,
							});
							const shown = (
								await noticeElement.evaluate(
									(el) => (el as HTMLElement).innerText ?? ''
								)
							)
								.replace(/\u00AD/g, '')
								.replace(/\s+/g, ' ')
								.trim();
							expect(shown).toBe(notice);
						}

						// Drive the real assessment handoff: the fixture's
						// classifier answer and deferred mail attempts make
						// SendAuthorization::process run the genuine
						// classification, so the enforce-mode ReceiptBudget
						// decides the receipt here — capped orders end at
						// daily_cap with only the team job bound; receipt
						// orders keep the receipt with both jobs bound. Queue
						// data only; no additional mail leaves the instance.
						run('process');
						const settled = JSON.parse(
							run('read')
						) as typeof pending;
						expect(settled.orders).toHaveLength(1);
						const settledOrder = settled.orders[0];
						if (!settledOrder)
							throw new Error('Missing settled order');
						if (capped) {
							expect(settledOrder.skipped).toBe('daily_cap');
							expect(settledOrder.authorization.jobs).toEqual([
								'team',
							]);
						} else {
							expect(settledOrder.skipped).toBe('');
							expect(
								[
									...(settledOrder.authorization.jobs ?? []),
								].sort()
							).toEqual(['receipt', 'team']);
						}
						expect(settledOrder.authorization.status).toBe(
							'normal'
						);

						mkdirSync(evidence, { recursive: true });
						writeFileSync(
							join(
								evidence,
								`guest-${language}-${width}-${door}-${capped ? 'capped' : 'receipt'}.json`
							),
							JSON.stringify(
								{
									before,
									after,
									pending,
									settled,
								},
								null,
								2
							)
						);
						expect(
							await page.evaluate(
								() =>
									document.documentElement.scrollWidth <=
									innerWidth
							)
						).toBe(true);
						await page.evaluate(async () => {
							await document.fonts.ready;
							await Promise.all(
								Array.from(document.images, async (image) => {
									image.loading = 'eager';
									await Promise.race([
										image.decode().catch(() => undefined),
										new Promise((resolve) =>
											setTimeout(resolve, 5_000)
										),
									]);
								})
							);
						});
						await page.screenshot({
							path: join(
								evidence,
								`guest-${language}-${width}-${door}-${capped ? 'capped' : 'receipt'}.png`
							),
							fullPage: true,
							animations: 'disabled',
						});
					} finally {
						try {
							await context.close();
						} finally {
							run('cleanup');
						}
					}
				});
			}
		}
	}
}
