/** A guest's open form survives a second tab creating the Woo draft and session. */
import { expect, test } from '@playwright/test';
import { join } from 'node:path';
import {
	applyTurnstileProfile,
	instance,
	REPO_ROOT,
	wp,
} from '../lib/instance';
import { seedConsentCookies } from '../lib/consent';
import { challengeRequests, waitForTurnstile } from '../lib/turnstile';

const fixture = join(REPO_ROOT, 'tests/e2e/fixtures/public-inquiry.php');
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);
let restoreTurnstile: (() => void) | undefined;
test.beforeAll(() => {
	restoreTurnstile = applyTurnstileProfile();
});
test.afterAll(() => restoreTurnstile?.());

const routes = {
	en: { contact: '/contact/', inquiry: '/proforma-request/' },
	de: { contact: '/de/kontakt/', inquiry: '/de/proforma-anfrage/' },
};

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		for (const door of ['contact', 'inquiry'] as const) {
			test(`${lang} ${width} ${door}: fresh form survives a new Woo session and confirms the native order`, async ({
				context,
				page,
			}) => {
				const email = `tester246-${lang}-${width}-${door}-${Date.now()}@example.test`;
				const { product } = JSON.parse(run('setup', email)) as {
					product: number;
				};
				try {
					await seedConsentCookies(context);
					await page.setViewportSize({
						width,
						height: width === 390 ? 844 : 900,
					});
					await page.goto(instance().url + routes[lang][door]);
					const form = page.locator(
						door === 'contact'
							? 'form.linker-contact-form'
							: 'form.linker-inquiry-form'
					);
					await expect(form).toBeVisible();

					const productPage = await context.newPage();
					const challenges = challengeRequests(productPage);
					try {
						await productPage.setViewportSize(page.viewportSize()!);
						await productPage.goto(
							`${instance().url}/?p=${product}`
						);
						await productPage
							.locator('a[href*="add-to-cart="]:visible')
							.first()
							.click();
						await expect(
							productPage.locator('form.woocommerce-cart-form')
						).toBeVisible();
						expect(challenges).toEqual([]);
					} finally {
						await productPage.close();
					}
					expect(
						(await context.cookies()).some((c) =>
							c.name.startsWith('wp_woocommerce_session_')
						)
					).toBe(true);

					await form
						.locator('[name=name]')
						.fill('Solartechnik am See');
					await form.locator('[name=email]').fill(email);
					await form
						.locator('textarea[name=message]')
						.fill('Please contact me about this battery.');
					await form.locator('[name=consent]').check();
					await waitForTurnstile(form);
					await form.locator('[type=submit]').first().click();
					if (door === 'inquiry') {
						// The other tab changed the items after this form opened.
						await expect(
							page
								.getByRole('alert')
								.filter({
									hasText: /draft changed|hat sich geändert/i,
								})
								.first()
						).toBeVisible();
						await expect(form.locator('[name=email]')).toHaveValue(
							email
						);
						await form.locator('[name=consent]').check();
						await waitForTurnstile(form);
						await form.locator('[type=submit]').first().click();
					}
					const receipt =
						door === 'contact'
							? page.locator(
									'.linker-contact-receipt .linker-form-success'
								)
							: page.getByRole('region', {
									name:
										lang === 'en'
											? 'Inquiry received'
											: 'Anfrage eingegangen',
								});
					await expect(receipt).toBeVisible();
					const { orders } = JSON.parse(run('read'));
					expect(orders).toHaveLength(1);
					expect(orders[0]).toMatchObject({
						customer: 0,
						status: 'inquiry-received',
						source: door,
						items: door === 'contact' ? 0 : 1,
					});
					await expect(receipt).toContainText(
						String(orders[0].number)
					);
					run('process');
					const settled = JSON.parse(run('read')).orders[0];
					expect(settled.authorization.jobs.sort()).toEqual([
						'receipt',
						'team',
					]);
				} finally {
					run('cleanup');
				}
			});
		}
	}
}
