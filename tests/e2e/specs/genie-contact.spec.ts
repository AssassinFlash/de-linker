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
		chat: 'What is the weather tomorrow?',
		person: 'Can I talk to a person?',
	},
	de: {
		page: '/de/genie/',
		chat: 'Wie wird das Wetter morgen?',
		person: 'Ich möchte mit einem Mitarbeiter sprechen.',
	},
};
const sent =
	/Your request is with the Linker team|Ihre Kontaktanfrage liegt beim Linker-Team/;

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		for (const role of ['guest', 'approved', 'pending'] as const) {
			test(`${lang} ${width}: ${role} sends one contact request from Genie`, async ({
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
				await ask(page, words[lang].chat);
				expect(calls, 'ordinary chat').toEqual([]);
				await ask(page, words[lang].person);
				const card = page
					.locator('.linker-genie-contact:visible')
					.last();
				const email = card.locator('input[type=email]');
				const consent = card.getByRole('checkbox');
				if (role === 'guest') {
					await email.fill(customer.email);
					await consent.check();
					await rejected(page, card, 'contact');
					await expect(email).toHaveValue(customer.email);
					await expect(consent).toBeChecked();
					expect(customer.read()).toEqual([]);
					expect(calls.length).toBeGreaterThan(0);
				} else {
					await expect(card).toContainText(customer.email);
					await expect(email).toHaveCount(0);
				}
				const at = mark();
				await loseAcknowledgement(page, card, 'contact');
				const original = customer.read();
				expect(original).toHaveLength(1);
				const order = original[0]!;
				expect(order).toMatchObject({
					source: 'contact',
					transfer: 'genie_contact',
					status: 'inquiry-received',
					locale: lang === 'de' ? 'de_DE_formal' : 'en_US',
					lines: [],
				});
				await card.locator('.linker-genie-contact__send').click();
				await expect(card).toContainText(sent);
				await expect(card).toContainText(customer.email);
				expect(customer.read().map((r) => r.id)).toEqual([order.id]);
				await customer.mail(order.id, at);
				await page.reload();
				await expect(
					page.locator('.linker-genie-contact__title:visible').last()
				).toHaveText(sent);
				if (role !== 'guest') expect(calls).toEqual([]);
				await info.attach('contact-receipt', {
					body: await page.screenshot({ animations: 'disabled' }),
					contentType: 'image/png',
				});
			});
		}
	}
}
