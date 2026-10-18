/**
 * The inquiry confirmation card (ticket #250; docs/specs/13-genie.md goal 5,
 * A8). In English and German, at 1440 and 390: the customer asks for a
 * product, adds it to the solution draft, asks Genie to send an inquiry, the
 * card shows the line and the one-business-day promise, the guest fills name,
 * address and consent, the send creates #246's inquiry (the record's number
 * and status come back into the conversation), the team mail and the receipt
 * land in the instance's spool, and a reload keeps the sent card.
 *
 * The instance's outgoing mail stays in its spool (docs/local-stack.md
 * §隔离) and test mode rewrites every recipient to the tester (AGENTS.md §5);
 * the routing itself is asserted on the Outbox queue by
 * plugins/linker-commerce/tests/php/Integration/GenieInquiryTest.php.
 *
 * With LINKER_E2E_SHOTS=<dir> every state is also saved as a screenshot
 * (the acceptance record docs/acceptance/2026-10-18/250/).
 */

/**
 * External dependencies
 */
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, wp } from '../lib/instance';
import { mark, since } from '../lib/mail';

type Lang = 'en' | 'de';

const ASK: Record<Lang, { page: string; product: string; inquiry: string }> = {
	en: {
		page: '/genie/',
		product: 'saj h2 10k inverter',
		inquiry: 'Please send an inquiry for this product.',
	},
	de: {
		page: '/de/genie/',
		product: 'saj h2 10k Wechselrichter',
		inquiry: 'Bitte senden Sie eine Anfrage für dieses Produkt.',
	},
};
const SENT =
	/Your inquiry is with the Linker team|Ihre Anfrage liegt beim Linker-Team/;
const PROMISE =
	/We reply within one business day\.|Wir antworten innerhalb eines Arbeitstags\./;
const TESTER = 'tester250@example.test';
const VIEWPORTS = {
	1440: { width: 1440, height: 1200 },
	390: { width: 390, height: 844 },
} as const;
const SHOTS = process.env.LINKER_E2E_SHOTS ?? '';

async function shot(page: Page, name: string): Promise<void> {
	if (!SHOTS) {
		return;
	}
	mkdirSync(SHOTS, { recursive: true });
	await page.screenshot({
		path: join(SHOTS, `${name}.png`),
		animations: 'disabled',
	});
}

/** Asks one question and waits until its answer has replaced the placeholder. */
async function ask(page: Page, question: string): Promise<string> {
	const messages = page.locator('.linker-genie-app__message');
	const before = await messages.count();
	await page.fill('#linker-genie-input', question);
	await page.locator('.linker-genie-app__send').click();
	const answered = async (): Promise<string> => {
		if ((await messages.count()) < before + 2) {
			return '';
		}
		const last = (await messages.last().innerText()).trim();
		return /Genie is thinking|Genie denkt nach/.test(last) ? '' : last;
	};
	await expect
		.poll(answered, { message: 'the answer arrives', timeout: 180_000 })
		.not.toBe('');
	return answered();
}

/**
 * The local instance's counters, cleared: the card's limiter
 * (InquiryRequest::LIMIT), #246's receipts, and the Outbox's minute record, so
 * the mail lands in the spool now.
 */
function freshCounters(): void {
	wp([
		'eval',
		"global $wpdb; $wpdb->query( \"DELETE FROM {$wpdb->options} WHERE option_name LIKE 'linker\\_tools\\_limit\\_genie\\_inquiry%' OR option_name LIKE 'linker\\_commerce\\_limit\\_public\\_receipts%'\" ); delete_option( 'linker_commerce_mail_sends' );",
	]);
}

const previous: string[] = [];

test.beforeAll(() => {
	previous.push(
		wp([
			'eval',
			"echo (string) get_option( 'linker_commerce_test_mail_to' );",
		]).trim()
	);
	wp(['option', 'update', 'linker_commerce_test_mail_to', TESTER]);
});

test.afterAll(() => {
	if (previous[0]) {
		wp(['option', 'update', 'linker_commerce_test_mail_to', previous[0]]);
	} else {
		wp(['option', 'delete', 'linker_commerce_test_mail_to']);
	}
});

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390] as const) {
		test(`the card drafts, sends and keeps the inquiry (${lang}, ${width})`, async ({
			page,
		}) => {
			test.setTimeout(300_000);
			freshCounters();
			await page.context().clearCookies();
			await page.setViewportSize(VIEWPORTS[width]);
			await page.goto(`${instance().url}${ASK[lang].page}`);
			await expect(page.locator('#linker-genie-input')).toBeVisible({
				timeout: 30_000,
			});

			// A product in the solution draft: the card sends the draft.
			await ask(page, ASK[lang].product);
			const add = page.getByRole('button', {
				name: /Add to solution draft|Zum Lösungsentwurf hinzufügen/,
			});
			await expect(add.first()).toBeVisible();
			const product = (
				await page
					.locator('.linker-genie-app__cards .linker-card__title')
					.first()
					.innerText()
			).trim();
			await add.first().click();
			await expect(
				page.getByText(/In your solution draft\.|Im Lösungsentwurf\./)
			).toBeVisible({ timeout: 30_000 });
			await page.waitForTimeout(3_000);

			// Genie drafts the inquiry; the card follows the answer.
			await ask(page, ASK[lang].inquiry);
			const card = page.locator('.linker-genie-inquiry');
			await expect(card).toBeVisible({ timeout: 60_000 });
			await expect(card).toContainText(product);
			await expect(card).toContainText(PROMISE);
			await expect(
				card.locator('.linker-genie-inquiry__edit')
			).toBeVisible();
			await card.scrollIntoViewIfNeeded();
			await shot(page, `${lang}-${width}-offer`);
			if (390 === width) {
				// The card is taller than the phone's transcript: the fields
				// and the button are the second half of the evidence.
				await page.evaluate(() => {
					const transcript = document.querySelector(
						'.linker-genie-app__transcript'
					);
					if (transcript) {
						transcript.scrollTop = transcript.scrollHeight;
					}
				});
				await shot(page, `${lang}-${width}-offer-bottom`);
			}

			await card
				.getByRole('textbox', { name: /^Name$/ })
				.fill('Maria Weber');
			await card
				.getByRole('textbox', {
					name: /Reply email|E-Mail für die Antwort/,
				})
				.fill('linker-e2e-250@example.test');
			await card
				.getByRole('textbox', {
					name: /Company \(optional\)|Unternehmen \(optional\)/,
				})
				.fill('Weber Solar');
			await card
				.getByLabel(
					/I agree that my details|Ich bin damit einverstanden/
				)
				.check();
			// The signed start time is three seconds old at the least.
			await page.waitForTimeout(3_000);
			const sentAt = mark();
			await card.locator('.linker-genie-inquiry__send').click();
			const sent = page.locator('.linker-genie-inquiry--sent');
			await expect(sent).toBeVisible({ timeout: 30_000 });
			await expect(sent).toContainText(SENT);
			await expect(sent).toContainText(
				/Inquiry #\d+ · Inquiry received|Anfrage Nr\. \d+ · Anfrage eingegangen/
			);
			await expect(page.locator('.linker-genie-inquiry')).toHaveCount(1);
			await expect(
				page.locator('.linker-genie-inquiry__send')
			).toHaveCount(0);
			await sent.scrollIntoViewIfNeeded();
			await shot(page, `${lang}-${width}-sent`);

			// One team mail and one receipt, both rewritten to the tester.
			await expect
				.poll(() => since(sentAt, /^New inquiry #/).length, {
					message: 'the team mail is in the spool',
					timeout: 30_000,
				})
				.toBe(1);
			await expect
				.poll(
					() =>
						since(sentAt, /^(Your inquiry #|Ihre Anfrage #)/)
							.length,
					{ message: 'the receipt is in the spool', timeout: 30_000 }
				)
				.toBe(1);
			for (const message of since(sentAt)) {
				expect(message.to).toEqual([TESTER]);
			}
			const team = since(sentAt, /^New inquiry #/)[0];
			expect(team?.html).toContain('Conversation with Genie');
			expect(team?.html).toContain(product);

			// The conversation keeps the sent card through a reload.
			await page.reload();
			await expect(
				page.locator('.linker-genie-inquiry--sent')
			).toHaveText(SENT, { timeout: 30_000 });
			await shot(page, `${lang}-${width}-reload`);
		});
	}
}
