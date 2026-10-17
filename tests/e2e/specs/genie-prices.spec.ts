/**
 * Prices follow the account in Genie (#242, docs/specs/13-genie.md 目标 8).
 *
 * On the SAJ H2-10K-T3's product page, an approved, a pending and a restricted
 * account and a guest ask Genie what the product costs, in English and in
 * German, at 1440 and 390 px. The card's price line must be the product page's
 * own: the approved account reads the page's net price word for word, the
 * others the page's own sentence and no amount. With LINKER_ACCEPTANCE_DIR set, each card is
 * photographed there (docs/acceptance/2026-10-18/242/).
 *
 * The three accounts are made for the run and removed afterwards.
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

const PRODUCT = 4107;
const QUESTION = {
	en: 'What does the SAJ H2-10K-T3 cost?',
	de: 'Was kostet der SAJ H2-10K-T3?',
} as const;
// The product page's sentence where the price would be (ProductView), for the
// accounts that see none.
const LINES = {
	guest: {
		en: 'Net price after partner sign-in',
		de: 'Nettopreis nach Partner-Anmeldung',
	},
	pending: { en: 'Prices after approval', de: 'Preise nach Freigabe' },
	restricted: {
		en: 'Not available for your account',
		de: 'Für Ihr Konto nicht verfügbar',
	},
} as const;
const STATES = ['approved', 'pending', 'restricted'] as const;
type Signed = (typeof STATES)[number];

// The accounts of this run, by state: made for it and removed afterwards.
const accounts = {} as Record<Signed, { email: string; id: number }>;

test.beforeAll(() => {
	for (const state of STATES) {
		const email = `genie-prices-e2e-${state}-${Date.now()}@example.test`;
		const id = Number(
			wp([
				'eval',
				`$id = wp_insert_user( array( 'user_login' => '${email}', 'user_email' => '${email}', 'user_pass' => wp_generate_password(), 'role' => 'customer' ) );` +
					`update_user_meta( $id, 'linker_approval_status', '${state}' ); echo $id;`,
			]).trim()
		);
		accounts[state] = { email, id };
	}
});

test.afterAll(() => {
	const ids = Object.values(accounts)
		.map((account) => account.id)
		.filter((id) => id > 0);
	if (ids.length > 0) {
		wp(['user', 'delete', ...ids.map(String), '--yes']);
	}
});

/** The product page's address in a language. */
function productPath(lang: 'en' | 'de'): string {
	const url = wp([
		'eval',
		`echo get_permalink( 'de' === '${lang}' ? pll_get_post( ${PRODUCT}, 'de' ) : ${PRODUCT} );`,
	]).trim();
	return new URL(url).pathname;
}

/** The page's own price line, as text. */
async function pagePrice(page: Page): Promise<string> {
	return (await page.locator('.pdp-price').first().innerText()).trim();
}

/**
 * Asks Genie through the dock loader's own event, the entry the product
 * page's ask button uses (pdp-ui.js): at 390 px the standing button is hidden
 * (docs/specs/13-genie.md §C, 860 px).
 */
async function askGenie(page: Page, question: string): Promise<void> {
	await page.evaluate((message) => {
		window.dispatchEvent(
			new CustomEvent('linker-genie-ask', { detail: { message } })
		);
	}, question);
	await expect(page.locator('.linker-genie-app__votes').first()).toBeVisible({
		timeout: 180_000,
	});
}

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		for (const who of [...STATES, 'guest'] as const) {
			test(`${who} · ${lang} · ${width}: the card's price line is the product page's`, async ({
				page,
			}) => {
				test.setTimeout(400_000);
				await page.setViewportSize({
					width,
					height: width > 500 ? 900 : 844,
				});
				if ('guest' !== who) {
					// Each row starts a new conversation: the account's earlier
					// thread would otherwise be restored with its own card.
					wp([
						'eval',
						`foreach ( get_posts( array( 'post_type' => 'linker_conversation', 'author' => ${accounts[who].id}, 'numberposts' => -1, 'post_status' => 'any', 'fields' => 'ids' ) ) as $id ) { wp_delete_post( $id, true ); }`,
					]);
					await page.goto(loginLink(undefined, accounts[who].email));
				}
				await page.goto(`${instance().url}${productPath(lang)}`);
				const onPage = await pagePrice(page);
				await askGenie(page, QUESTION[lang]);
				const card = page
					.locator('.linker-genie-app article.linker-card')
					.first();
				await expect(card).toBeVisible({ timeout: 30_000 });
				const line = card.locator('.linker-card__price');
				await expect(line).toBeVisible();
				// The card is complete once its model line has come in too.
				await expect(card.locator('.linker-card__model')).toBeVisible({
					timeout: 30_000,
				});
				const onCard = (await line.innerText()).trim();
				if ('approved' === who) {
					expect(onCard, 'the net price, as the page prints it').toBe(
						onPage
					);
					expect(onCard).toMatch(/1[.,]680/);
					await expect(line).toHaveClass(/linker-card__price--net/);
				} else {
					expect(onCard).toBe(LINES[who][lang]);
					expect(onPage).toBe(LINES[who][lang]);
					await expect(line).toHaveClass(/linker-card__price--note/);
					expect(
						await page.locator('.linker-genie-app').innerText(),
						'no amount anywhere in the conversation'
					).not.toMatch(/€|1[.,]680/);
				}
				const dir = process.env.LINKER_ACCEPTANCE_DIR;
				if (dir) {
					mkdirSync(dir, { recursive: true });
					await card.scrollIntoViewIfNeeded();
					await page.screenshot({
						path: join(dir, `card-${who}-${lang}-${width}.png`),
					});
				}
			});
		}
	}
}
