import { randomUUID } from 'node:crypto';
import { join } from 'node:path';
import { test, expect } from '@playwright/test';
import { instance, REPO_ROOT, wp } from '../lib/instance';
import { seedConsentCookies } from '../lib/consent';
import { challengeRequests } from '../lib/turnstile';

const fixture = join(REPO_ROOT, 'tests/e2e/fixtures/public-inquiry.php');
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);

for (const role of ['pending', 'approved']) {
	for (const lang of ['en', 'de']) {
		for (const width of [1440, 390]) {
			test(`${role} ${lang} ${width} sends contact and product inquiries in the signed-in session`, async ({
				context,
				page,
			}) => {
				const name = 'qa-native-' + randomUUID();
				const email = name + '@example.test';
				const password = randomUUID();
				const site = instance();
				const de = lang === 'de';
				const where = (en: string, german: string) =>
					site.url + (de ? german : en);
				const customer = wp([
					'user',
					'create',
					name,
					email,
					'--role=customer',
					'--user_pass=' + password,
					'--porcelain',
				]).trim();
				if (!/^\d+$/.test(customer))
					throw new Error('Test customer creation failed');
				try {
					wp([
						'user',
						'meta',
						'update',
						customer,
						'linker_approval_status',
						role,
					]);
					wp([
						'user',
						'meta',
						'update',
						customer,
						'billing_first_name',
						'Alex',
					]);
					wp([
						'user',
						'meta',
						'update',
						customer,
						'billing_last_name',
						'Example',
					]);
					run('setup', email);
					await seedConsentCookies(context);
					await page.setViewportSize({
						width,
						height: width === 390 ? 844 : 900,
					});
					const challenges = challengeRequests(page);
					await page.goto(where('/my-account/', '/de/mein-konto/'));
					await page.locator('#username').fill(email);
					await page.locator('#password').fill(password);
					await page.locator('[name=login][type=submit]').click();
					await expect(page.locator('body')).toHaveClass(
						/\blogged-in\b/
					);
					let selected = 0;
					for (const door of ['contact', 'inquiry']) {
						if (door === 'contact') {
							await page.goto(where('/contact/', '/de/kontakt/'));
						} else {
							await page.goto(
								where(
									'/product/saj-bu2-5-0-hv1/',
									'/de/produkt/saj-bu2-5-0-hv1/'
								)
							);
							const add = page
								.locator('a[href*="add-to-cart="]:visible')
								.first();
							selected = Number(
								new URL(
									(await add.getAttribute('href')) ?? '',
									page.url()
								).searchParams.get('add-to-cart')
							);
							expect(selected).toBeGreaterThan(0);
							await add.click();
							const quantity = page
								.locator(
									'form.woocommerce-cart-form input.qty:visible'
								)
								.first();
							await quantity.fill('3');
							await page
								.locator(
									'.wc-proceed-to-checkout button[name=proceed]:visible'
								)
								.first()
								.click();
						}
						const form = page.locator(
							door === 'contact'
								? 'form.linker-contact-form'
								: 'form.linker-inquiry-form'
						);
						await expect(form).toBeVisible();
						await expect(
							form.locator(
								'[data-linker-turnstile], [name="cf-turnstile-response"]'
							)
						).toHaveCount(0);
						const person = form.locator('[name=name]');
						const reply = form.locator('[name=email]');
						if (await person.isVisible())
							await person.fill('Alex Example');
						if (await reply.isVisible()) await reply.fill(email);
						await form
							.locator('textarea[name=message]')
							.fill(
								de
									? 'Bitte kontaktieren Sie mich zum Speicher.'
									: 'Please contact me about storage.'
							);
						const consent = form.locator('[name=consent]');
						if (await consent.isVisible()) await consent.check();
						await form.locator('[type=submit]').first().click();
						const receipt =
							door === 'contact'
								? page.locator('.linker-contact-receipt')
								: page.getByRole('region', {
										name: de
											? 'Anfrage eingegangen'
											: 'Inquiry received',
									});
						await expect(receipt).toBeVisible();
						const rows = JSON.parse(run('read')).orders.filter(
							(entry: { source: string }) => entry.source === door
						);
						expect(rows).toHaveLength(1);
						expect(rows[0]).toMatchObject({
							customer: Number(customer),
							status: 'inquiry-received',
							items: door === 'contact' ? 0 : 1,
						});
						await expect(receipt).toContainText(
							String(rows[0].number)
						);
						if (door === 'inquiry') {
							const qty = wp([
								'eval',
								`$order=wc_get_order(${Number(rows[0].id)});$items=array_values($order->get_items());echo wp_json_encode([ $items[0]->get_quantity(), (int)pll_get_post($items[0]->get_product_id(),'en') === (int)pll_get_post(${selected},'en') ]);`,
							]);
							expect(JSON.parse(qty)).toEqual([3, true]);
						}
					}
					expect(challenges).toEqual([]);
				} finally {
					try {
						run('cleanup');
					} finally {
						wp(['user', 'delete', customer, '--yes']);
					}
				}
			});
		}
	}
}
