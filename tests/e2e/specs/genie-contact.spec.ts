/**
 * "Let Linker contact me" (ticket #243; docs/specs/13-genie.md, 目标 6 and
 * "转人工", A5). In English and German, as a guest and signed in, at 1440 and
 * 390: the customer asks for a person, the contact card appears under the
 * service's sentence, the guest leaves an address (the signed-in customer is
 * not asked), the card confirms with the one-business-day promise, #246's
 * team mail and the customer's receipt land in the instance's spool, and
 * Genie answers the next question.
 *
 * The instance's outgoing mail stays in its spool (docs/local-stack.md
 * §隔离); the routing itself is asserted on the Outbox queue by
 * plugins/linker-commerce/tests/php/Integration/GenieContactTest.php.
 *
 * With LINKER_E2E_SHOTS=<dir> every state is also saved as a screenshot
 * (the acceptance record docs/acceptance/2026-10-18/243/).
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
import { instance, loginLink, wp } from '../lib/instance';
import { mark, since } from '../lib/mail';

type Lang = 'en' | 'de';
type Who = 'guest' | 'signed-in';

const ASK: Record<Lang, { page: string; person: string; next: string }> = {
	en: {
		page: '/product/saj-h2-10k-t3/',
		person: 'Can I talk to a person?',
		next: 'Which battery fits this inverter?',
	},
	de: {
		page: '/de/produkt/saj-h2-10k-t3/',
		person: 'Ich möchte mit einem Mitarbeiter sprechen',
		next: 'Welcher Speicher passt zu diesem Wechselrichter?',
	},
};
const PROMISE = /business day|Arbeitstag/;
const SENT =
	/Your request is with the Linker team|Ihre Kontaktanfrage liegt beim Linker-Team/;
const CUSTOMER = process.env.LINKER_E2E_CUSTOMER ?? '857558227@qq.com';
// A guest address of the reserved example domain: the instance's spool keeps it.
const GUEST = 'linker-e2e-243@example.test';
const VIEWPORTS = {
	1440: { width: 1440, height: 900 },
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

/** Opens the dock (below 861 px through the loader, as genie-page.spec.ts does). */
async function openDock(page: Page): Promise<void> {
	await page.evaluate(() =>
		document.querySelector<HTMLElement>('.linker-genie-open')?.click()
	);
	await expect(page.locator('.linker-genie-app__composer')).toBeVisible({
		timeout: 30_000,
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
 * The local instance's counters, cleared: the suite sends more requests in an
 * hour than one connection may (ContactRequest::LIMIT), more receipts than a
 * day allows (#246's ReceiptLimit), and more mail in a minute than the Outbox
 * sends at once (Mail\\Throttle, whose record this clears so the mail lands in
 * the spool now).
 */
function freshCounters(): void {
	wp([
		'eval',
		"global $wpdb; $wpdb->query( \"DELETE FROM {$wpdb->options} WHERE option_name LIKE 'linker\\_tools\\_limit\\_genie\\_contact%' OR option_name LIKE 'linker\\_commerce\\_limit\\_public\\_receipts%'\" ); delete_option( 'linker_commerce_mail_sends' );",
	]);
}

for (const lang of ['en', 'de'] as const) {
	for (const who of ['guest', 'signed-in'] as const satisfies Who[]) {
		for (const width of [1440, 390] as const) {
			test(`${who} asks for a person (${lang}, ${width})`, async ({
				page,
			}) => {
				test.setTimeout(300_000);
				freshCounters();
				await page.context().clearCookies();
				if ('signed-in' === who) {
					await page.goto(loginLink(undefined, CUSTOMER));
				}
				await page.setViewportSize(VIEWPORTS[width]);
				await page.goto(`${instance().url}${ASK[lang].page}`);
				await openDock(page);
				if ('signed-in' === who) {
					// A signed-in dock restores the last conversation: start anew.
					await page
						.locator(
							'.linker-genie-app__bar-actions .linker-genie-app__icon'
						)
						.first()
						.click();
				}
				await ask(page, ASK[lang].person);
				const card = page.locator('.linker-genie-contact');
				await expect(card).toBeVisible();
				await expect(card).toContainText(PROMISE);
				const field = card.locator('.linker-genie-contact__email');
				if ('signed-in' === who) {
					await expect(field).toHaveCount(0);
					await expect(card).toContainText(CUSTOMER);
				} else {
					await expect(field).toBeVisible();
				}
				await card.scrollIntoViewIfNeeded();
				await shot(page, `${lang}-${width}-${who}-offer`);

				const sentAt = mark();
				if ('guest' === who) {
					await field.fill(GUEST);
					// The consent the site's public doors ask a guest for.
					await card
						.getByLabel(/I agree|Ich bin damit einverstanden/)
						.check();
				}
				// The signed start time is three seconds old at the least.
				await page.waitForTimeout(3_000);
				await card.locator('.linker-genie-contact__send').click();
				await expect(
					card.locator('.linker-genie-contact__title')
				).toHaveText(SENT);
				await expect(card).toContainText(
					'guest' === who ? GUEST : CUSTOMER
				);
				await shot(page, `${lang}-${width}-${who}-sent`);
				// One record through #246's door: the team mail and the receipt.
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
						{
							message: 'the receipt is in the spool',
							timeout: 30_000,
						}
					)
					.toBe(1);

				if (1440 === width) {
					// The offer does not mute Genie, and the sent card stays in
					// the history on the next turn (review round 1 of #243).
					const next = await ask(page, ASK[lang].next);
					expect(next.length).toBeGreaterThan(0);
					await expect(
						page.locator('.linker-genie-contact')
					).toHaveCount(1);
					await expect(
						page.locator('.linker-genie-contact__title')
					).toHaveText(SENT);
					await shot(page, `${lang}-${width}-${who}-after`);
					// …and after a reload.
					await page.reload();
					await openDock(page);
					await expect(
						page.locator('.linker-genie-contact')
					).toHaveCount(1);
					await expect(
						page.locator('.linker-genie-contact__title')
					).toHaveText(SENT);
					await page
						.locator('.linker-genie-contact')
						.scrollIntoViewIfNeeded();
					await shot(page, `${lang}-${width}-${who}-reload`);
				}
			});
		}
	}
}

// Over #246's daily receipt cap the request still reaches the team; the card
// says no confirmation email went (review round 1 of #243).
for (const [lang, width] of [
	['en', 1440],
	['de', 390],
] as const) {
	test(`over the receipt cap the card says so (${lang}, ${width})`, async ({
		page,
	}) => {
		test.setTimeout(300_000);
		freshCounters();
		wp([
			'eval',
			"$r = new Linker\\Commerce\\Inquiry\\RateLimit( 'public_receipts', Linker\\Commerce\\Inquiry\\ReceiptLimit::DAILY_CAP, DAY_IN_SECONDS ); while ( $r->take( '' ) ) {}",
		]);
		await page.context().clearCookies();
		await page.setViewportSize(VIEWPORTS[width]);
		await page.goto(`${instance().url}${ASK[lang].page}`);
		await openDock(page);
		await ask(page, ASK[lang].person);
		const card = page.locator('.linker-genie-contact');
		await card.locator('.linker-genie-contact__email').fill(GUEST);
		await card.getByLabel(/I agree|Ich bin damit einverstanden/).check();
		await page.waitForTimeout(3_000);
		await card.locator('.linker-genie-contact__send').click();
		await expect(page.locator('.linker-genie-contact')).toContainText(
			/We have not sent a confirmation email|Es wurde keine Bestätigungs-E-Mail versendet/
		);
		await page.locator('.linker-genie-contact').scrollIntoViewIfNeeded();
		await shot(page, `${lang}-${width}-guest-no-receipt`);
		freshCounters();
	});
}
