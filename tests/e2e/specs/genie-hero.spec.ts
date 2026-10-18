/**
 * The home hero's Genie conversation in a real browser (ticket #232,
 * docs/specs/13-genie.md 目标 10; owner ruling 2026-10-17, variant B):
 *
 * - every hero control opens the conversation in place and never navigates;
 * - a real Genie answer and its product cards appear inside the hero, four
 *   columns at 1440 and two at 390;
 * - closing restores the resting hero and the same conversation continues;
 * - out of sight, the way back continues the same conversation in the dock;
 * - the #236 attachment states: exact nameplate, unreadable, PDF, refused.
 *
 * English and German, 1440 and 390. With LINKER_E2E_SHOTS=<dir> every state
 * is saved as a screenshot (the acceptance record
 * docs/acceptance/2026-10-19/232/).
 */

/**
 * External dependencies
 */
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Browser, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { REPO_ROOT, instance, wp } from '../lib/instance';

type Lang = 'en' | 'de';

const TESTER = 'linker-e2e-232@example.test';

/**
 * The local instance's counters, cleared so the hero's inquiry and contact
 * sends are not refused by the hour's limiter or the mail throttle; the test
 * mail option keeps every recipient at the tester (AGENTS.md §5).
 */
function freshCounters(): void {
	wp([
		'eval',
		"global $wpdb; $wpdb->query( \"DELETE FROM {$wpdb->options} WHERE option_name LIKE 'linker\\_tools\\_limit\\_genie\\_inquiry%' OR option_name LIKE 'linker\\_tools\\_limit\\_genie\\_contact%' OR option_name LIKE 'linker\\_commerce\\_limit\\_public\\_receipts%'\" ); delete_option( 'linker_commerce_mail_sends' );",
	]);
}

let previousMail = '';
test.beforeAll(() => {
	previousMail = wp([
		'eval',
		"echo (string) get_option( 'linker_commerce_test_mail_to' );",
	]).trim();
	wp(['option', 'update', 'linker_commerce_test_mail_to', TESTER]);
});
test.afterAll(() => {
	if (previousMail) {
		wp(['option', 'update', 'linker_commerce_test_mail_to', previousMail]);
	} else {
		wp(['option', 'delete', 'linker_commerce_test_mail_to']);
	}
});

const LANGS: Lang[] = ['en', 'de'];
const VIEWPORTS = [
	{ name: '1440', width: 1440, height: 900 },
	{ name: '390', width: 390, height: 844 },
] as const;

const PHOTO_EXACT = join(
	REPO_ROOT,
	'docs/research/2026-10-17-deepseek-flash-vision/raw/nameplate-probe.png'
);
// A nameplate whose model field is deliberately blank: the service reads the
// device type, reads no model, and the card says so (the "unreadable" state).
// The real blurred photos in services/genie/eval/attachments are graded
// unreadable but the model sometimes guesses a model from them, which makes a
// screenshot state non-deterministic.
const PHOTO_UNREADABLE = join(
	REPO_ROOT,
	'tests/e2e/fixtures/hero-nameplate-unreadable.jpg'
);
const PDF = join(
	REPO_ROOT,
	'docs/research/2026-10-17-deepseek-flash-vision/raw/datasheet-probe.pdf'
);
const REFUSED = join(REPO_ROOT, 'tests/e2e/fixtures/hero-notes.txt');

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

/** A page in its own browser context: a fresh conversation cookie each. */
async function fresh(
	browser: Browser,
	lang: Lang,
	viewport: { width: number; height: number }
): Promise<Page> {
	const context = await browser.newContext({
		viewport,
		reducedMotion: 'reduce',
	});
	const page = await context.newPage();
	await page.goto(instance().url + pageBase(lang), {
		waitUntil: 'load',
	});
	await page.evaluate(() => document.fonts.ready);
	await expect(page.locator('.hero-prompt')).toBeVisible();
	// The entry is bound before a control may be trusted (controller.tsx).
	await expect(
		page.locator('.hero-cinematic[data-linker-genie-hero="ready"]')
	).toHaveCount(1);
	return page;
}

function pageBase(lang: Lang): string {
	return 'de' === lang ? '/de/' : '/';
}

/** Waits for the conversation to unfold in the hero. */
async function unfolded(page: Page): Promise<void> {
	await expect(page.locator('.linker-genie-hero__surface')).toBeVisible({
		timeout: 15_000,
	});
	await expect(
		page.locator('.hero-cinematic.linker-genie-hero--open')
	).toHaveCount(1);
}

/** Asks one question through the page's own textarea. */
async function enter(page: Page, question: string): Promise<void> {
	await page.fill('.hero-prompt', question);
	await page.press('.hero-prompt', 'Enter');
	await unfolded(page);
}

/** Reads the hero's conversation title and AI line. */
async function header(page: Page): Promise<string> {
	return page.locator('.linker-genie-hero__bar').innerText();
}

/** Waits for a real answer. */
async function answered(page: Page): Promise<void> {
	await expect(page.locator('.linker-genie-reply').last()).toBeVisible({
		timeout: 240_000,
	});
}

/** Scrolls one attachment card into view inside the transcript. */
async function scrollAttachment(page: Page): Promise<void> {
	await page.locator('.linker-genie-attachment').scrollIntoViewIfNeeded();
	await page.waitForTimeout(200);
}

/** Puts the transcript at its end (cards live under the answer). */
async function scrollTranscript(page: Page, top: 'start' | 'end') {
	await page
		.locator('.linker-genie-hero__surface .linker-genie-app__transcript')
		.evaluate((element, where) => {
			element.scrollTop = where === 'end' ? element.scrollHeight : 0;
		}, top);
	await page.waitForTimeout(200);
}

for (const lang of LANGS) {
	for (const viewport of VIEWPORTS) {
		const at = `${lang}-${viewport.name}`;

		test.describe(`home hero · ${at}`, () => {
			test('every control opens the conversation in place and never navigates', async ({
				browser,
			}) => {
				test.setTimeout(600_000);
				const path = pageBase(lang);
				const expectedUrl = instance().url + path;

				// Typing + Enter.
				let page = await fresh(browser, lang, viewport);
				await enter(page, 'saj');
				expect(page.url()).toBe(expectedUrl);
				await shot(page, `hero-${at}-enter`);
				await page.context().close();

				// The send button (an anchor on the live page: no navigation).
				page = await fresh(browser, lang, viewport);
				await page.fill('.hero-prompt', 'saj');
				await page.click('.hero-send');
				await unfolded(page);
				expect(page.url()).toBe(expectedUrl);
				await shot(page, `hero-${at}-send`);
				await page.context().close();

				// A capsule.
				page = await fresh(browser, lang, viewport);
				await page.locator('.hero-capsule').first().click();
				await unfolded(page);
				expect(page.url()).toBe(expectedUrl);
				await shot(page, `hero-${at}-capsule`);
				await page.context().close();

				// The voice button (dictation where the browser has it).
				page = await fresh(browser, lang, viewport);
				await page.click('[data-linker-assistant-open="voice"]');
				await unfolded(page);
				expect(page.url()).toBe(expectedUrl);
				await shot(page, `hero-${at}-voice`);
				await page.context().close();

				// The nameplate button opens the conversation and its picker.
				page = await fresh(browser, lang, viewport);
				await page.click('[data-linker-assistant-open="nameplate"]');
				await unfolded(page);
				expect(page.url()).toBe(expectedUrl);
				await shot(page, `hero-${at}-photo-open`);
				await page.context().close();

				// The attachment button does the same for a document.
				page = await fresh(browser, lang, viewport);
				await page.click('[data-linker-assistant-open="attach"]');
				await unfolded(page);
				expect(page.url()).toBe(expectedUrl);
				await shot(page, `hero-${at}-attach-open`);
				await page.context().close();
			});

			test('the answer and its product cards appear in the hero', async ({
				browser,
			}) => {
				test.setTimeout(600_000);
				const page = await fresh(browser, lang, viewport);
				const path = pageBase(lang);
				await enter(page, 'saj');

				// The header says who is answering and offers both exits,
				// and the hero's own words fold away (review round 1, item 7).
				const bar = await header(page);
				expect(bar).toContain(
					'de' === lang
						? 'Genie – der KI-Assistent von Linker'
						: "Genie - Linker's AI assistant"
				);
				expect(bar).toContain(
					'de' === lang
						? 'In der Seitenleiste fortsetzen'
						: 'Continue in the side panel'
				);
				await expect(
					page.getByRole('button', {
						name: 'de' === lang ? 'Schließen' : 'Close',
					})
				).toHaveCount(1);
				for (const selector of [
					'.hero-badge',
					'.hero-title',
					'.hero-subtitle',
					'.hero-capsules',
					'.hero-footnote',
				]) {
					await expect(page.locator(selector)).toBeHidden();
				}

				await answered(page);
				const cards = page.locator(
					'.linker-genie-hero__cards .linker-card'
				);
				await expect
					.poll(() => cards.count(), { timeout: 60_000 })
					.toBeGreaterThan(0);
				expect(page.url()).toBe(instance().url + path);

				// Four columns at 1440, two on a phone (owner ruling).
				const columns = await page
					.locator('.linker-genie-hero__cards')
					.evaluate(
						(element) =>
							getComputedStyle(element).gridTemplateColumns.split(
								' '
							).length
					);
				expect(columns).toBe(viewport.width > 860 ? 4 : 2);

				await scrollTranscript(page, 'start');
				await shot(page, `hero-${at}-answer`);
				await scrollTranscript(page, 'end');
				await shot(page, `hero-${at}-cards`);
				await page.context().close();
			});

			test('closing restores the hero and the same conversation continues', async ({
				browser,
			}) => {
				test.setTimeout(600_000);
				const page = await fresh(browser, lang, viewport);
				await enter(page, 'saj');
				await answered(page);

				await page.click('.linker-genie-hero__close');
				await expect(
					page.locator('.linker-genie-hero__surface')
				).toHaveCount(0);
				await expect(
					page.locator('.hero-cinematic.linker-genie-hero--open')
				).toHaveCount(0);
				await expect(page.locator('.hero-title')).toBeVisible();
				await page.evaluate(() => window.scrollTo(0, 0));
				await shot(page, `hero-${at}-restored`);

				// The next question carries the thread the first answer wrote:
				// the hero and the dock share one conversation.
				const posted = page.waitForRequest(
					(request) =>
						request.url().includes('/genie/turn') &&
						'POST' === request.method()
				);
				await enter(page, 'Which battery pairs with it?');
				const body = (await posted).postDataJSON() as {
					messages: { role: string; content: string }[];
				};
				expect(body.messages[0]).toEqual({
					role: 'user',
					content: 'saj',
				});
				expect(body.messages.length).toBeGreaterThan(2);
				await page.context().close();
			});

			test('out of sight, the way back continues the same conversation in the dock', async ({
				browser,
			}) => {
				test.setTimeout(600_000);
				const page = await fresh(browser, lang, viewport);
				await enter(page, 'saj');
				await answered(page);
				await page.click('.linker-genie-hero__close');

				await page.evaluate(() =>
					window.scrollTo(0, document.body.scrollHeight)
				);
				const pill = page.locator('.linker-genie-hero-pill');
				await expect(pill).toBeVisible({ timeout: 15_000 });
				await shot(page, `hero-${at}-continue-entry`);

				await pill.click();
				await expect(
					page.locator('.linker-genie-app__composer')
				).toBeVisible({ timeout: 30_000 });
				await expect(
					page.locator('.linker-genie-app__origin')
				).toHaveText(
					'de' === lang
						? 'Auf der Startseite begonnen'
						: 'Asked from the homepage'
				);
				await expect(
					page.locator('.linker-genie-app__panel')
				).toContainText('saj');
				await shot(page, `hero-${at}-dock-continued`);
				await page.context().close();
			});

			test('Continue in the side panel hands the same conversation to the dock', async ({
				browser,
			}) => {
				test.setTimeout(600_000);
				const page = await fresh(browser, lang, viewport);
				await enter(page, 'saj');
				await answered(page);

				await page.click('.linker-genie-hero__continue');
				await expect(
					page.locator('.linker-genie-app__composer')
				).toBeVisible({ timeout: 30_000 });
				await expect(
					page.locator('.hero-cinematic.linker-genie-hero--open')
				).toHaveCount(0);
				await expect(
					page.locator('.linker-genie-app__origin')
				).toHaveText(
					'de' === lang
						? 'Auf der Startseite begonnen'
						: 'Asked from the homepage'
				);
				await expect(
					page.locator('.linker-genie-app__panel')
				).toContainText('saj');
				await shot(page, `hero-${at}-side-panel`);
				await page.context().close();
			});

			test('the #236 attachment states render in the hero', async ({
				browser,
			}) => {
				test.setTimeout(900_000);

				// Exact nameplate: the card confirms the model in our range.
				let page = await fresh(browser, lang, viewport);
				await page.click('[data-linker-assistant-open="nameplate"]');
				await unfolded(page);
				await page
					.locator('input[type="file"]')
					.setInputFiles(PHOTO_EXACT);
				await expect(
					page.locator('.linker-genie-attachment')
				).toBeVisible({ timeout: 240_000 });
				await expect(
					page.locator('.linker-genie-attachment')
				).toContainText(
					'de' === lang ? 'In unserem Sortiment' : 'In our range'
				);
				await scrollAttachment(page);
				await shot(page, `hero-${at}-nameplate-exact`);
				await page.context().close();

				// A nameplate whose model is too blurred to read.
				page = await fresh(browser, lang, viewport);
				await page.click('[data-linker-assistant-open="nameplate"]');
				await unfolded(page);
				await page
					.locator('input[type="file"]')
					.setInputFiles(PHOTO_UNREADABLE);
				await expect(
					page.locator('.linker-genie-attachment')
				).toBeVisible({ timeout: 240_000 });
				await expect(
					page.locator('.linker-genie-attachment')
				).toContainText(
					'de' === lang
						? 'Das Modell konnte nicht gelesen werden.'
						: 'The model could not be read.'
				);
				await scrollAttachment(page);
				await shot(page, `hero-${at}-nameplate-unreadable`);
				// The manual-model exit fills the hero's own follow-up field.
				await page
					.getByRole('button', {
						name:
							'de' === lang
								? 'Modell eingeben'
								: 'Type the model',
					})
					.click();
				await expect(page.locator('.hero-prompt')).toHaveValue(
					'de' === lang
						? 'Mein Gerät ist das Modell '
						: 'My device is the '
				);
				await expect(page.locator('.hero-prompt')).toBeFocused();
				await page.context().close();

				// A PDF datasheet.
				page = await fresh(browser, lang, viewport);
				await page.click('[data-linker-assistant-open="attach"]');
				await unfolded(page);
				await page.locator('input[type="file"]').setInputFiles(PDF);
				await expect(
					page.locator('.linker-genie-attachment')
				).toBeVisible({ timeout: 240_000 });
				await expect(
					page.locator('.linker-genie-attachment')
				).toContainText('datasheet-probe.pdf');
				await scrollAttachment(page);
				await shot(page, `hero-${at}-datasheet`);
				await page.context().close();

				// A type Genie does not read: refused before any turn.
				page = await fresh(browser, lang, viewport);
				await page.click('[data-linker-assistant-open="attach"]');
				await unfolded(page);
				await page.locator('input[type="file"]').setInputFiles(REFUSED);
				await expect(
					page.locator('.linker-genie-app__attachment--refused')
				).toBeVisible({ timeout: 15_000 });
				await shot(page, `hero-${at}-refused`);
				await page.context().close();
			});

			test('the #243 contact and #250 inquiry cards send from the hero', async ({
				browser,
			}) => {
				test.setTimeout(900_000);
				freshCounters();

				// "Let Linker contact me": the guest leaves an address, the
				// card sends and confirms.
				let page = await fresh(browser, lang, viewport);
				await enter(
					page,
					'de' === lang
						? 'Ich möchte mit einem Mitarbeiter sprechen'
						: 'Can I talk to a person?'
				);
				const contact = page.locator('.linker-genie-contact');
				await expect(contact).toBeVisible({ timeout: 240_000 });
				await expect(contact).toContainText(/business day|Arbeitstag/);
				await contact
					.locator('.linker-genie-contact__email')
					.fill(TESTER);
				await contact
					.getByLabel(/I agree|Ich bin damit einverstanden/)
					.check();
				// The signed start time is three seconds old at the least.
				await page.waitForTimeout(3_000);
				await contact.locator('.linker-genie-contact__send').click();
				await expect(contact).toContainText(
					/Your request is with the Linker team|Ihre Kontaktanfrage liegt beim Linker-Team/,
					{ timeout: 30_000 }
				);
				await contact.scrollIntoViewIfNeeded();
				await shot(page, `hero-${at}-contact`);
				await page.context().close();

				// The inquiry confirmation card (#250): draft a product, ask
				// for an inquiry, confirm the card, and keep the record.
				page = await fresh(browser, lang, viewport);
				await enter(
					page,
					'de' === lang
						? 'saj h2 10k Wechselrichter'
						: 'saj h2 10k inverter'
				);
				await answered(page);
				const add = page.getByRole('button', {
					name: /Add to solution draft|Zum Lösungsentwurf hinzufügen/,
				});
				await expect(add.first()).toBeVisible({ timeout: 60_000 });
				const product = (
					await page
						.locator(
							'.linker-genie-hero__cards .linker-card__title'
						)
						.first()
						.innerText()
				).trim();
				await add.first().click();
				await expect(
					page.getByText(
						/In your solution draft\.|Im Lösungsentwurf\./
					)
				).toBeVisible({ timeout: 30_000 });
				await page.waitForTimeout(3_000);

				await enter(
					page,
					'de' === lang
						? 'Bitte senden Sie eine Anfrage für dieses Produkt.'
						: 'Please send an inquiry for this product.'
				);
				const card = page.locator('.linker-genie-inquiry');
				await expect(card).toBeVisible({ timeout: 60_000 });
				await expect(card).toContainText(product);
				await expect(card).toContainText(
					/We reply within one business day|Wir antworten innerhalb eines Arbeitstags/
				);
				await card
					.getByRole('textbox', { name: /^Name$/ })
					.fill('Maria Weber');
				await card
					.getByRole('textbox', {
						name: /Reply email|E-Mail für die Antwort/,
					})
					.fill(TESTER);
				await card
					.getByRole('textbox', {
						name: /Company \(optional\)|Unternehmen \(optional\)/,
					})
					.fill('Weber Solar');
				await card
					.getByLabel(/I agree|Ich bin damit einverstanden/)
					.check();
				await page.waitForTimeout(3_000);
				await card.locator('.linker-genie-inquiry__send').click();
				const sent = page.locator('.linker-genie-inquiry--sent');
				await expect(sent).toContainText(
					/Your inquiry is with the Linker team|Ihre Anfrage liegt beim Linker-Team/,
					{ timeout: 30_000 }
				);
				await expect(sent).toContainText(
					/Inquiry #\d+ · Inquiry received|Anfrage Nr\. \d+ · Anfrage eingegangen/
				);
				await sent.scrollIntoViewIfNeeded();
				await shot(page, `hero-${at}-inquiry`);
				await page.context().close();
			});
		});
	}
}
