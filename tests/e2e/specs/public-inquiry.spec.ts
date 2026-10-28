/** Guest public doors across a Woo session-cookie transition (#246, round 2). */
import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { instance, REPO_ROOT, wp } from '../lib/instance';

const evidence = join(
	REPO_ROOT,
	'.scratch/e2e-shots/public-inquiry',
	process.env.LINKER_246_RUN ?? 'latest'
);
const fixture = join(REPO_ROOT, 'tests/e2e/fixtures/public-inquiry.php');
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);

// Queue::WAIT_SECONDS is the claimed model attempt; queue delay is excluded
// (Inquiry/Assessment/Queue.php). After the success page that delay is the
// nonblocking wake-up plus the Outbox write, not the minute recovery cron.
// AsyncRunner's 0.01s fire-and-forget is not a 10ms ceiling: Requests rounds
// that dispatch to at least 1s (docs/specs/543-assessment-dispatch.md). Lock
// allows at most 1s for the DB handoff (Inquiry/Assessment/Lock.php).
// AssessmentAsyncTest budgets 12s after the customer response to observe an 8s
// attempt of this same race, so the poll allows that 4s on top of the full 10s
// attempt. expect.poll returns when the handoff is visible; this is a ceiling.
// A live unknown verdict does not hand off inside that ceiling: the first retry
// waits Outbox::RETRY_DELAYS[0] (60s). The fixture answers only this run's
// classifier call so the first SendAuthorization attempt can reach Outbox.
const MODEL_ATTEMPT_MS = 10_000;
const SCHEDULE_MARGIN_MS = 4_000;
const HANDOFF_TIMEOUT_MS = MODEL_ATTEMPT_MS + SCHEDULE_MARGIN_MS;

test.setTimeout(60_000 + HANDOFF_TIMEOUT_MS);

type InquiryReadback = {
	orders?: Array<{ skipped?: string }>;
	mail?: Array<{ to?: string[] }>;
};

function authorizationHandoff(readback: InquiryReadback, email: string) {
	const orders = readback.orders ?? [];
	const mail = readback.mail ?? [];
	return {
		orders: orders.length,
		jobs: mail.length,
		receipt: mail.filter(
			(item) => Array.isArray(item.to) && item.to.includes(email)
		).length,
		dailyCap: orders[0]?.skipped === 'daily_cap',
	};
}

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
					const setup = JSON.parse(
						run('setup', email, capped ? 'capped' : 'receipt')
					);
					const context = await browser.newContext({
						viewport: { width, height: 900 },
					});
					try {
						expect(await context.cookies()).toEqual([]);
						const page = await context.newPage();
						const path =
							door === 'contact'
								? language === 'de'
									? '/de/kontakt/'
									: '/contact/'
								: language === 'de'
									? '/de/proforma-anfrage/'
									: '/proforma-request/';
						await page.goto(`${instance().url}${path}`);
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
						// A second tab adding a product can establish Woo's cookie after render.
						await context.request.get(
							`${instance().url}/?add-to-cart=${setup.product}`
						);
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
						await expect(
							page.locator('.linker-form-success')
						).toBeVisible();
						let readback: ReturnType<typeof JSON.parse> | undefined;
						await expect
							.poll(
								() => {
									readback = JSON.parse(run('read'));
									return authorizationHandoff(
										readback,
										email
									);
								},
								{
									message:
										'SendAuthorization hands the inquiry to Outbox after the success page',
									timeout: HANDOFF_TIMEOUT_MS,
									intervals: [500, 1_000],
								}
							)
							.toEqual({
								orders: 1,
								jobs: capped ? 1 : 2,
								receipt: capped ? 0 : 1,
								dailyCap: capped,
							});
						if (readback === undefined) {
							throw new Error(
								'SendAuthorization readback was not captured.'
							);
						}
						expect(readback.orders).toHaveLength(1);
						expect(readback.orders[0].customer).toBe(0);
						expect(readback.orders[0].items).toBe(
							door === 'request' ? 1 : 0
						);
						expect(readback.orders[0].status).toBe(
							'inquiry-received'
						);
						expect(readback.orders[0].source).toBe(
							door === 'contact' ? 'contact' : 'proforma'
						);
						expect(readback.mail).toHaveLength(capped ? 1 : 2);
						expect(
							readback.mail.filter((mail: { to: string[] }) =>
								mail.to.includes(email)
							)
						).toHaveLength(capped ? 0 : 1);
						if (capped) {
							expect(readback.orders[0].skipped).toBe(
								'daily_cap'
							);
							const notice =
								language === 'de'
									? door === 'contact'
										? 'Eine Bestätigung per E-Mail wurde nicht versendet.'
										: 'Es wurde keine Bestätigungs-E-Mail versendet.'
									: 'We have not sent a confirmation email.';
							await expect(
								page.getByText(notice, { exact: false })
							).toBeVisible();
						}

						mkdirSync(evidence, { recursive: true });
						writeFileSync(
							join(
								evidence,
								`guest-${language}-${width}-${door}-${capped ? 'capped' : 'receipt'}.json`
							),
							JSON.stringify(
								{ before, after, ...readback },
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
						await context.close();
						run('cleanup');
					}
				});
			}
		}
	}
}
