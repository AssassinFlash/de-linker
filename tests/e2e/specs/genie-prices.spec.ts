/**
 * Prices follow the account in Genie (#242, docs/specs/13-genie.md 目标 8).
 *
 * On the SAJ H2-10K-T3's product page, an approved partner account and a guest
 * ask Genie what the product costs, in English and in German, at 1440 and 390
 * px. The card's price line must be the product page's own: the approved
 * account reads the page's net price word for word, the guest reads the page's
 * sign-in sentence and no amount. With LINKER_ACCEPTANCE_DIR set, each card is
 * photographed there (docs/acceptance/2026-10-18/242/).
 *
 * The approved account is made for the run and removed afterwards.
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
// The product page's sentence where a guest's price would be (ProductView).
const GUEST_LINE = {
	en: 'Net price after partner sign-in',
	de: 'Nettopreis nach Partner-Anmeldung',
} as const;

let approved = '';
let approvedId = 0;

test.beforeAll(() => {
	approved = `genie-prices-e2e-${Date.now()}@example.test`;
	approvedId = Number(
		wp([
			'eval',
			`$id = wp_insert_user( array( 'user_login' => '${approved}', 'user_email' => '${approved}', 'user_pass' => wp_generate_password(), 'role' => 'customer' ) );` +
				`update_user_meta( $id, 'linker_approval_status', 'approved' ); echo $id;`,
		]).trim()
	);
});

test.afterAll(() => {
	if (approvedId > 0) {
		wp(['user', 'delete', String(approvedId), '--yes']);
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
		for (const who of ['approved', 'guest'] as const) {
			test(`${who} · ${lang} · ${width}: the card's price line is the product page's`, async ({
				page,
			}) => {
				test.setTimeout(400_000);
				await page.setViewportSize({
					width,
					height: width > 500 ? 900 : 844,
				});
				if ('approved' === who) {
					// Each row starts a new conversation: the account's earlier
					// thread would otherwise be restored with its own card.
					wp([
						'eval',
						`foreach ( get_posts( array( 'post_type' => 'linker_conversation', 'author' => ${approvedId}, 'numberposts' => -1, 'post_status' => 'any', 'fields' => 'ids' ) ) as $id ) { wp_delete_post( $id, true ); }`,
					]);
					await page.goto(loginLink(undefined, approved));
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
					expect(onCard).toBe(GUEST_LINE[lang]);
					expect(onPage).toBe(GUEST_LINE[lang]);
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
