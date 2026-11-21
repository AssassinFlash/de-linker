import { expect } from '@playwright/test';
import { test } from '../lib/genie-transfer';
import { applyTurnstileProfile, instance } from '../lib/instance';
import { mark } from '../lib/mail';
import { challengeRequests, waitForTurnstile } from '../lib/turnstile';

const paths = {
	en: {
		product: '/product/saj-bu2-5-0-hv1/',
		cart: '/cart/',
		contact: '/contact/',
	},
	de: {
		product: '/de/produkt/saj-bu2-5-0-hv1/',
		cart: '/de/loesungsentwurf/',
		contact: '/de/kontakt/',
	},
};
for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		for (const action of ['contact', 'inquiry'] as const) {
			test(`${lang} ${width}: anonymous ${action} keeps the form and draft through verification failure`, async ({
				page,
				customer,
			}, info) => {
				const base = instance().url;
				const path = paths[lang];
				const calls = challengeRequests(page);
				await page.setViewportSize({
					width,
					height: width === 390 ? 844 : 900,
				});
				if (action === 'inquiry') {
					await page.goto(base + path.product);
					await page
						.locator('a[href*="add-to-cart="]:visible')
						.first()
						.click();
					await expect(page).toHaveURL(base + path.cart);
					const quantity = page.locator(
						'.woocommerce-cart-form input.qty'
					);
					await expect(quantity).toHaveValue('1');
					await quantity.fill('2');
					await quantity.press('Tab');
					await page.locator('button[name="update_cart"]').click();
					await expect(
						page.locator('button[name="update_cart"]')
					).toBeDisabled();
					await page.reload();
					await expect(quantity).toHaveValue('2');
					await page
						.locator('.woocommerce-cart-form a.remove')
						.click();
					await page.locator('a.restore-item').click();
					await expect(quantity).toHaveValue('2');
					expect(
						calls,
						'view product, add, edit, remove and restore'
					).toEqual([]);
					await page.locator('.wc-proceed-to-checkout a').click();
				} else {
					await page.goto(base + path.contact);
				}
				const form = page.locator(`form.linker-${action}-form`);
				const email = form.locator('[name=email]');
				const message = form.locator('[name=message]');
				const consent = form.locator('[name=consent]');
				const text =
					lang === 'de'
						? 'Bitte prüfen Sie diese Anfrage.'
						: 'Please review this inquiry.';
				await form.locator('[name=name]').fill('Local Review');
				await email.fill(customer.email);
				await message.fill(text);
				await consent.check();
				await waitForTurnstile(form);
				expect(calls.length).toBeGreaterThan(0);
				const restore = applyTurnstileProfile(undefined, 'fail');
				try {
					await form.locator('[type=submit]').click();
					await expect(
						page
							.locator(
								'.linker-form-error, .linker-inquiry-error'
							)
							.first()
					).toBeVisible();
					await expect(email).toHaveValue(customer.email);
					await expect(message).toHaveValue(text);
					await expect(consent).toBeChecked();
					if (action === 'inquiry')
						await expect(
							page.locator('.linker-inquiry-line input.qty')
						).toHaveValue('2');
					expect(customer.read()).toEqual([]);
					await info.attach('retained-form', {
						body: await page.screenshot({ animations: 'disabled' }),
						contentType: 'image/png',
					});
				} finally {
					restore();
				}
				await waitForTurnstile(form);
				const at = mark();
				await form.locator('[type=submit]').click();
				if (action === 'inquiry') {
					await expect(page).toHaveURL(
						/order-received|inquiry-received|anfrage-eingegangen|bestellung-erhalten/
					);
				} else {
					await expect(
						page.locator('.linker-form-success')
					).toBeVisible();
				}
				const orders = customer.read();
				expect(orders).toHaveLength(1);
				const order = orders[0]!;
				expect(order).toMatchObject({
					source: action,
					status: 'inquiry-received',
					message: text,
				});
				expect(order.lines.map((line) => line.quantity)).toEqual(
					action === 'inquiry' ? [2] : []
				);
				await customer.mail(order.id, at);
			});
		}
	}
}

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${lang} ${width}: keep the actual Woo draft when Genie cannot answer`, async ({
			page,
			customer,
		}) => {
			const base = instance().url;
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await page.goto(base + paths[lang].product);
			await page
				.locator('a[href*="add-to-cart="]:visible')
				.first()
				.click();
			const qty = page.locator('.woocommerce-cart-form input.qty');
			await qty.fill('2');
			await qty.press('Tab');
			await page.locator('button[name="update_cart"]').click();
			await expect(
				page.locator('button[name="update_cart"]')
			).toBeDisabled();
			await page.goto(base + (lang === 'de' ? '/de/genie/' : '/genie/'));
			const handoff = {
				type: 'handoff',
				summary:
					lang === 'de'
						? 'Ihre Anfrage konnte gerade nicht beantwortet werden.'
						: 'I could not answer this time.',
			};
			const stream =
				'event: meta\ndata: ' +
				JSON.stringify({
					grounded: false,
					fallback: true,
					attempts: 1,
					failures: ['model unavailable'],
					language: lang,
				}) +
				'\n\nevent: block\ndata: ' +
				JSON.stringify(handoff) +
				'\n\nevent: done\ndata: {"ok":true}\n\n';
			await page.route(
				'**/wp-json/linker-ai/v1/genie/turn',
				(route) => route.fulfill({ json: { stream } }),
				{ times: 1 }
			);
			await page
				.locator('#linker-genie-input:visible')
				.fill(
					lang === 'de'
						? 'Ich möchte eine Anfrage senden.'
						: 'Please send an inquiry.'
				);
			await page.locator('.linker-genie-app__send:visible').click();
			const link = page
				.locator('.linker-genie-app__prompt:visible')
				.filter({
					hasText:
						lang === 'de' ? 'Anfrage senden' : 'Send an inquiry',
				});
			await link.click();
			const form = page.locator('form.linker-inquiry-form');
			await expect(form).toBeVisible();
			await expect(page.locator('.linker-inquiry-line')).toContainText(
				'BU2-5.0-HV1'
			);
			await expect(
				page.locator('.linker-inquiry-line input.qty')
			).toHaveValue('2');
			expect(customer.read()).toEqual([]);
		});
	}
}
