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
						const readback = JSON.parse(run('read'));
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
						// #533: mail leaves only after the pre-send verdict, so
						// immediately after submit the queue is empty and the
						// receipt skip reason is still 'assessment_pending'.
						// The verdict→queue→delivery walk (routing data,
						// daily_cap resolution) is nondeterministic in time
						// and lives in the walk harness instead:
						// tests/e2e/specs-walk/walk2*.ts.
						const deferred = JSON.parse(run('read')) as {
							mail: { to: string[] }[];
						};
						expect(deferred.mail).toHaveLength(0);
						const queuedMail = deferred.mail;
						if (capped) {
							// #533: the cap is resolved when the deferred
							// receipt would be built, after the verdict;
							// here every order is still 'assessment_pending'.
							expect(readback.orders[0].skipped).toBe(
								'assessment_pending'
							);
							// The contact door cannot yet know whether a
							// receipt will follow, so it shows the plain
							// sent copy; the request page names the deferred
							// no-receipt notice.
							const notice =
								language === 'de'
									? door === 'contact'
										? 'Vielen Dank. Ihre Nachricht liegt beim Linker-Team.'
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
									orders: readback.orders,
									mail: queuedMail,
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
						await context.close();
						run('cleanup');
					}
				});
			}
		}
	}
}
