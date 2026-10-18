/** Guest public doors across a Woo session-cookie transition (#246, round 2). */
import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { instance, REPO_ROOT, wp } from '../lib/instance';

const evidence = join(REPO_ROOT, 'docs/acceptance/2026-10-18/246/round-2');
const fixture = join(REPO_ROOT, 'tests/e2e/fixtures/public-inquiry.php');
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);

test.setTimeout(60_000);
for (const language of ['en', 'de']) {
	for (const width of [1440, 390]) {
		for (const door of ['contact', 'request']) {
			for (const capped of [false, true]) {
				test(`${language} ${width} ${door} ${capped ? 'capped' : 'receipt'}: fresh guest can submit after Woo creates its cookie`, async ({
					browser,
				}) => {
					expect(instance().name).toBe('c246');
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
							await expect(page.locator('body')).toContainText(
								language === 'de'
									? door === 'contact'
										? 'Eine Bestätigung per E-Mail wurde nicht versendet.'
										: 'Es wurde keine Bestätigungs-E-Mail versendet.'
									: 'We have not sent a confirmation email.'
							);
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
