import { expect } from '@playwright/test';
import {
	ask,
	loseAcknowledgement,
	rejected,
	test,
} from '../lib/genie-transfer';
import { instance } from '../lib/instance';
import { mark } from '../lib/mail';
import { challengeRequests } from '../lib/turnstile';
const words = {
	en: {
		page: '/genie/',
		product: 'Show me the SAJ H2-10K-T3 inverter.',
		inquiry: 'Please send an inquiry for this product.',
	},
	de: {
		page: '/de/genie/',
		product: 'Zeigen Sie mir den Wechselrichter SAJ H2-10K-T3.',
		inquiry: 'Bitte senden Sie eine Anfrage für dieses Produkt.',
	},
};
const sent =
	/Your inquiry is with the Linker team|Ihre Anfrage liegt beim Linker-Team/;

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		for (const role of ['guest', 'approved', 'pending'] as const) {
			test(`${lang} ${width}: ${role} sends the reviewed Genie equipment once`, async ({
				page,
				customer,
			}, info) => {
				const calls = challengeRequests(page);
				await page.setViewportSize({
					width,
					height: width === 390 ? 844 : 900,
				});
				if (role !== 'guest') await customer.login(role);
				await page.goto(instance().url + words[lang].page);
				await ask(page, words[lang].product);
				const add = page
					.getByRole('button', {
						name: /Add to solution draft|Zum Lösungsentwurf hinzufügen/,
					})
					.first();
				await add.click();
				await expect(
					page
						.getByText(
							/In your solution draft\.|Im Lösungsentwurf\./
						)
						.last()
				).toBeVisible();
				expect(
					calls,
					'chat, product lookup and draft addition'
				).toEqual([]);
				await ask(page, words[lang].inquiry);
				const card = page
					.locator('.linker-genie-inquiry:visible')
					.last();
				const product = card.locator(
					'.linker-genie-inquiry__product a'
				);
				await expect(product).toHaveCount(1);
				const name = (await product.innerText()).trim();
				const attach = width === 1440;
				const summary = card.locator(
					'.linker-genie-inquiry__summary input[type=checkbox]'
				);
				await summary.setChecked(attach);
				const message = card.locator('textarea');
				const note =
					lang === 'de'
						? 'Bitte bestätigen Sie diese Auswahl.'
						: 'Please confirm this selection.';
				await message.fill(note);
				if (role === 'guest') {
					const email = card.locator('input[type=email]');
					const consent = card.locator(
						'.linker-genie-inquiry__consent input'
					);
					await card
						.getByRole('textbox', { name: /^Name$/ })
						.fill('Maria Weber');
					await email.fill(customer.email);
					await consent.check();
					await rejected(page, card, 'inquiry');
					await expect(email).toHaveValue(customer.email);
					await expect(consent).toBeChecked();
					await expect(message).toHaveValue(note);
					await expect(product).toHaveText(name);
					expect(customer.read()).toEqual([]);
					expect(calls.length).toBeGreaterThan(0);
				} else {
					await expect(card.locator('input[type=email]')).toHaveCount(
						0
					);
				}
				const at = mark();
				await loseAcknowledgement(page, card, 'inquiry');
				const original = customer.read();
				expect(original).toHaveLength(1);
				const order = original[0]!;
				expect(order).toMatchObject({
					source: 'inquiry',
					transfer: 'genie_inquiry',
					summary: attach,
					status: 'inquiry-received',
					locale: lang === 'de' ? 'de_DE_formal' : 'en_US',
					lines: [{ name, quantity: 1 }],
					message: note,
				});
				await card.locator('.linker-genie-inquiry__send').click();
				const receipt = page
					.locator('.linker-genie-inquiry--sent:visible')
					.last();
				await expect(receipt).toContainText(sent);
				await expect(receipt).toContainText(String(order.id));
				expect(customer.read().map((r) => r.id)).toEqual([order.id]);
				await customer.mail(order.id, at);
				await page.reload();
				await expect(receipt).toContainText(String(order.id));
				if (role !== 'guest') expect(calls).toEqual([]);
				await info.attach('inquiry-receipt', {
					body: await page.screenshot({ animations: 'disabled' }),
					contentType: 'image/png',
				});
			});
		}
	}
}
