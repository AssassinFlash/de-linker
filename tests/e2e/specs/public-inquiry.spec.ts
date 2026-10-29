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

test.setTimeout(120_000);
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
							door === 'contact' ? 'contact' : 'proforma'
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
							// The contact door cannot yet know whether a
							// receipt will follow, so it shows the plain
							// sent copy; the request page names the deferred
							// no-receipt notice.
							const notice =
								language === 'de'
									? door === 'contact'
										? 'Ihre Nachricht ist beim Linker-Team eingegangen. Eine Bestätigung per E-Mail wurde nicht versendet.'
										: 'Es wurde keine Bestätigungs-E-Mail versendet.'
									: door === 'contact'
										? 'Thank you. Your message is with the Linker team.'
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
								{
									before,
									after,
									pending,
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
