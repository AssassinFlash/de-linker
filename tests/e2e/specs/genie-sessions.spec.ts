/**
 * Every Genie conversation is kept (ticket #235; docs/specs/13-genie.md,
 * 目标 7; acceptance A9 and A12 of
 * docs/research/2026-10-17-ai-assistants/INTL.md §8), in a real browser
 * against a real Genie:
 *
 * - a guest opens three conversations; all three are in the list and the
 *   first can be continued;
 * - a new conversation leaves the docked workspace rail open (the rail folds
 *   only where it is an overlay, under 768 px);
 * - the conversation is emailed to the guest's own address: a confirmation
 *   with a link first (nothing of the conversation in it), then, once the link
 *   is opened, the conversation (each message in the instance's spool, to that
 *   address alone);
 * - signing in through the account page puts all three under the account,
 *   and a second browser signed in as the same customer lists all three;
 * - a conversation deleted there leaves the list.
 *
 * Once per language and width: EN/DE × 1440/390. With LINKER_E2E_SHOTS=<dir>
 * every state is saved as a screenshot (docs/acceptance/2026-10-18/235/).
 */

/**
 * External dependencies
 */
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import {
	expect,
	test,
	type Browser,
	type BrowserContext,
	type Page,
} from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, wp } from '../lib/instance';
import { mark, since } from '../lib/mail';

type Lang = 'en' | 'de';

const WORKSPACE: Record<Lang, string> = { en: '/genie/', de: '/de/genie/' };
const ACCOUNT: Record<Lang, string> = {
	en: '/my-account/',
	de: '/de/mein-konto/',
};
const QUESTIONS: Record<Lang, string[]> = {
	en: [
		'Which hybrid inverters do you carry for homes?',
		'Show me the SAJ H2-10K-T3',
		'Which batteries work with the GoodWe ESA GW10K-EHA-G20?',
	],
	de: [
		'Welche Hybridwechselrichter führen Sie für Wohngebäude?',
		'Zeigen Sie mir den SAJ H2-10K-T3',
		'Welche Batterien passen zum GoodWe ESA GW10K-EHA-G20?',
	],
};
/** A page with the dock (the standing button shows from 860 px up). */
const CATEGORY: Record<Lang, string> = {
	en: '/product-category/inverters/',
	de: '/de/produkt-kategorie/wechselrichter/',
};
const CONFIRM_SUBJECT: Record<Lang, string> = {
	en: 'Conversation with Genie requested for this email address',
	de: 'Gespräch mit Genie für diese E-Mail-Adresse angefordert',
};
const SUBJECT: Record<Lang, string> = {
	en: 'Your conversation with Genie',
	de: 'Ihr Gespräch mit Genie',
};
interface Labels {
	newConversation: string;
	conversations: string;
	email: string;
	address: string;
	send: string;
	delete: string;
	deleteRow: string;
}
const LABEL: Record<Lang, Labels> = {
	en: {
		newConversation: 'New conversation',
		conversations: 'Conversations',
		email: 'Email me this conversation',
		address: 'Your email address',
		send: 'Send email',
		delete: 'Delete',
		deleteRow: 'Delete conversation:',
	},
	de: {
		newConversation: 'Neues Gespräch',
		conversations: 'Gespräche',
		email: 'Gespräch per E-Mail erhalten',
		address: 'Ihre E-Mail-Adresse',
		send: 'E-Mail senden',
		delete: 'Löschen',
		deleteRow: 'Gespräch löschen:',
	},
};
/** The one tester address of the test mail rule (AGENTS.md §5). */
const TESTER = 'tester@example.test';

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

/** One email as its reader sees it, at the 1440 run only. */
async function mailShot(
	context: BrowserContext,
	html: string,
	width: number,
	name: string
): Promise<void> {
	if (!SHOTS || width !== 1440) {
		return;
	}
	const mailPage = await context.newPage();
	await mailPage.setViewportSize({ width: 800, height: 900 });
	await mailPage.setContent(html);
	await mailPage.screenshot({
		path: join(SHOTS, `${name}.png`),
		fullPage: true,
	});
	await mailPage.close();
}

/** The rail, open: on a phone it is an overlay the bar's toggle opens. */
async function openRail(page: Page, lang: Lang): Promise<void> {
	const rail = page.locator('.linker-genie-rail');
	if (await rail.evaluate((node) => node.classList.contains('is-open'))) {
		return;
	}
	await page
		.locator('.linker-genie-app__rail-toggle')
		.filter({ hasText: LABEL[lang].conversations })
		.click();
	await expect(rail).toHaveClass(/is-open/);
}

/** Asks one question and returns once the answer has landed. */
async function ask(page: Page, question: string): Promise<void> {
	const votes = page.locator('.linker-genie-app__votes');
	const before = await votes.count();
	await page.fill('#linker-genie-input', question);
	await page.locator('.linker-genie-app__send').click();
	await expect
		.poll(async () => votes.count(), {
			message: 'the answer arrives',
			timeout: 180_000,
		})
		.toBeGreaterThan(before);
}

/** The titles the list shows, top to bottom. */
async function titles(page: Page): Promise<string[]> {
	await expect(page.locator('.linker-genie-rail__item').first()).toBeVisible({
		timeout: 20_000,
	});
	return page.locator('.linker-genie-rail__item').allInnerTexts();
}

/** A browser of its own at one width. */
async function browserAt(
	browser: Browser,
	width: number
): Promise<{ context: BrowserContext; page: Page }> {
	const context = await browser.newContext({
		viewport: { width, height: width < 768 ? 844 : 900 },
		isMobile: width < 768,
		hasTouch: width < 768,
	});
	return { context, page: await context.newPage() };
}

/** Signs in through the account page's own form, as a customer does. */
async function signIn(
	page: Page,
	lang: Lang,
	login: string,
	password: string
): Promise<void> {
	await page.goto(`${instance().url}${ACCOUNT[lang]}`);
	await page.fill('#username', login);
	await page.fill('#password', password);
	await page.locator('button[name="login"]').click();
	await expect(page.locator('#username')).toHaveCount(0, {
		timeout: 30_000,
	});
}

for (const lang of ['en', 'de'] as Lang[]) {
	for (const width of [1440, 390]) {
		test(`${lang} ${width}: a guest keeps three conversations, emails one, and signing in keeps all three on every device`, async ({
			browser,
		}) => {
			test.setTimeout(900_000);
			const tag = `${lang}-${width}`;
			const login = `e2e-genie-235-${tag}-${Date.now()}`;
			const password = `Pw-${Date.now()}-${Math.random().toString(36).slice(2)}`;
			const user = wp([
				'user',
				'create',
				login,
				`${login}@example.test`,
				'--role=customer',
				`--user_pass=${password}`,
				'--porcelain',
			]).trim();
			const label = LABEL[lang];
			const questions = QUESTIONS[lang];
			const guest = await browserAt(browser, width);
			const other = await browserAt(browser, width);
			try {
				const page = guest.page;
				await page.goto(`${instance().url}${WORKSPACE[lang]}`);
				await expect(page.locator('#linker-genie-input')).toBeVisible({
					timeout: 30_000,
				});

				// Three conversations, each opened with "New conversation".
				for (const [index, question] of questions.entries()) {
					if (index > 0) {
						await openRail(page, lang);
						await page.locator('.linker-genie-rail__new').click();
						await expect(
							page.locator('.linker-genie-app__message')
						).toHaveCount(0);
						if (width >= 768) {
							// Docked, the rail stays open (#235).
							await expect(
								page.locator('.linker-genie-rail')
							).toHaveClass(/is-open/);
							if (index === 1) {
								await shot(page, `${tag}-1-new-keeps-rail`);
							}
						}
					}
					await ask(page, question);
				}

				await openRail(page, lang);
				await expect
					.poll(() => titles(page))
					.toEqual([...questions].reverse());
				await expect(
					page.locator('.linker-genie-rail__note')
				).toBeVisible();
				await shot(page, `${tag}-2-guest-three`);

				// The first one can be continued.
				await page
					.locator('.linker-genie-rail__item', {
						hasText: questions[0],
					})
					.click();
				await expect(
					page.locator('.linker-genie-app__message--user').first()
				).toHaveText(questions[0]!);
				await shot(page, `${tag}-3-switched-back`);

				if (width >= 860) {
					// The dock on any other page lists the same three.
					await page.goto(`${instance().url}${CATEGORY[lang]}`);
					await page.locator('.linker-genie-open').first().click();
					await page
						.locator('.linker-genie-app__bar-actions')
						.getByRole('button', { name: label.conversations })
						.click();
					await expect
						.poll(() => titles(page))
						.toEqual([...questions].reverse());
					await shot(page, `${tag}-3b-dock-three`);
					await page.goto(`${instance().url}${WORKSPACE[lang]}`);
					await expect(
						page.locator('.linker-genie-app__message--user').first()
					).toHaveText(questions[0]!, { timeout: 30_000 });
				}

				// Email it to the guest's own address. First only a confirmation
				// reaches that mailbox (fixed words and a link, nothing of the
				// conversation); the conversation follows once the link is opened
				// (review round 1 of #235). The run starts with a fresh allowance:
				// the limiter rows of this instance's Genie mail are cleared
				// (RateLimit, option names linker_tools_limit_genie_mail…).
				wp([
					'eval',
					'global $wpdb; $wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", \'linker\\_tools\\_limit\\_genie\\_mail%\' ) );',
				]);
				const before = mark();
				await page.getByRole('button', { name: label.email }).click();
				await page.getByLabel(label.address).fill(TESTER);
				await page
					.locator('.linker-genie-app__email')
					.scrollIntoViewIfNeeded();
				await shot(page, `${tag}-4-email-form`);
				// A person typing an address takes longer than the guard's
				// floor (ConversationMail::MIN_SECONDS, 3 s from the page
				// load); the test waits it out instead of being a bot.
				await page.waitForTimeout(3_000);
				await page.getByRole('button', { name: label.send }).click();
				await expect(
					page.locator('.linker-genie-app__email-status')
				).toContainText(TESTER);
				await page
					.locator('.linker-genie-app__email-status')
					.scrollIntoViewIfNeeded();
				await shot(page, `${tag}-5-confirm-requested`);
				await expect
					.poll(() => since(before, CONFIRM_SUBJECT[lang]).length, {
						message: 'the confirmation reaches the spool',
						timeout: 30_000,
					})
					.toBe(1);
				const confirmation = since(before, CONFIRM_SUBJECT[lang])[0]!;
				expect(confirmation.to).toEqual([TESTER]);
				expect(confirmation.bcc).toEqual([]);
				expect(confirmation.html).not.toContain(questions[0]!);
				expect(since(before, SUBJECT[lang])).toEqual([]);
				await mailShot(
					guest.context,
					confirmation.html,
					width,
					`${tag}-6-confirm-message`
				);
				const link = /href="([^"]*linker_tools_genie_email[^"]*)"/
					.exec(confirmation.html)?.[1]
					?.replace(/&amp;/g, '&')
					.replace(/&#038;/g, '&');
				expect(link, 'the confirmation carries its link').toBeTruthy();

				// Opening the link sends the conversation and says so on
				// Genie's page.
				const opened = await guest.context.newPage();
				await opened.goto(link!);
				await expect(
					opened.locator('.linker-genie-app__notice')
				).toBeVisible({ timeout: 30_000 });
				await shot(opened, `${tag}-7-link-opened`);
				await opened.close();
				await expect
					.poll(() => since(before, SUBJECT[lang]).length, {
						message: 'the conversation reaches the spool',
						timeout: 30_000,
					})
					.toBe(1);
				const email = since(before, SUBJECT[lang])[0]!;
				expect(email.to).toEqual([TESTER]);
				expect(email.cc).toEqual([]);
				expect(email.bcc).toEqual([]);
				expect(email.html).toContain(questions[0]!);
				await mailShot(
					guest.context,
					email.html,
					width,
					`${tag}-8-conversation-message`
				);

				// Signing in through the account page: all three are the account's.
				await signIn(page, lang, login, password);
				await page.goto(`${instance().url}${WORKSPACE[lang]}`);
				await openRail(page, lang);
				await expect
					.poll(() => titles(page))
					.toEqual([...questions].reverse());
				await expect(
					page.locator('.linker-genie-rail__note')
				).toHaveCount(0);
				await shot(page, `${tag}-9-signed-in-three`);

				// Another browser, the same customer: all three are there.
				const second = other.page;
				await signIn(second, lang, login, password);
				await second.goto(`${instance().url}${WORKSPACE[lang]}`);
				await openRail(second, lang);
				await expect
					.poll(() => titles(second))
					.toEqual([...questions].reverse());
				await shot(second, `${tag}-10-other-device-three`);

				// Deleting one there: confirm in place, then it is gone.
				const row = second.locator('.linker-genie-rail__row', {
					hasText: questions[1]!,
				});
				await row.hover();
				await second
					.getByRole('button', {
						name: `${label.deleteRow} ${questions[1]}`,
					})
					.click();
				await shot(second, `${tag}-11-delete-confirm`);
				await second
					.locator('.linker-genie-rail__confirm-delete')
					.click();
				await expect(
					second.locator('.linker-genie-rail__item', {
						hasText: questions[1]!,
					})
				).toHaveCount(0);
				await expect
					.poll(() => titles(second))
					.toEqual([questions[2], questions[0]]);
				await shot(second, `${tag}-12-deleted`);
			} finally {
				await guest.context.close();
				await other.context.close();
				// The customer and every conversation they own go again.
				wp([
					'eval',
					`foreach ( get_posts( array( 'post_type' => 'linker_conversation', 'post_status' => 'any', 'author' => ${Number(user)}, 'posts_per_page' => -1, 'fields' => 'ids' ) ) as $id ) { wp_delete_post( $id, true ); }`,
				]);
				wp(['user', 'delete', user, '--yes']);
			}
		});
	}
}
