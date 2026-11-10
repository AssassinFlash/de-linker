/**
 * Restored history prices follow the current customer's authority (matrix rows
 * genie:history-current-permissions-and-locale, all languages and widths).
 *
 * The same saved conversation - a card whose snapshot price is a partner's
 * net figure - is restored under an approved, a pending, a restricted account
 * and a guest: restoreArtifacts re-reads each product through the current
 * customer's own get-product ability (refreshPrices), so the card carries the
 * account's own current line and never the snapshot. When that authority read
 * itself fails, the card keeps no price at all - a failed authority clears
 * the old price instead of leaving it behind.
 *
 * The workspace surface, English and German, 1440 and 390. The
 * opposite-language history and the restored document labels are the
 * genie-history-artifacts suite's coverage.
 */

/**
 * External dependencies
 */
import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, loginLink, wp } from '../lib/instance';
import { seedConsentCookies } from '../lib/consent';

type Lang = 'en' | 'de';

/** The product whose page pins the expected lines (genie-prices' product). */
const PRODUCT = 4107;

/** The account states whose own lines the restored card must carry. */
const STATES = ['approved', 'pending', 'restricted'] as const;
type State = (typeof STATES)[number];

/** The page's own sentence where the price stands, by account and language. */
const LINES = {
	en: {
		pending: 'Account under review. Prices after approval.',
		restricted: 'Not available for your account',
		guest: 'Net price after partner sign-in',
	},
	de: {
		pending: 'Ihr Konto wird geprüft. Preise nach Freigabe.',
		restricted: 'Für Ihr Konto nicht verfügbar',
		guest: 'Nettopreis nach Partner-Anmeldung',
	},
} as const;

/** The run's own accounts, made before and removed after. */
const accounts = {} as Record<State, { email: string; id: number }>;

test.beforeAll(() => {
	for (const state of STATES) {
		const email = `genie-history-e2e-${state}-${Date.now()}@example.test`;
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

/**
 * Serves the one saved conversation: an answer whose card carries a snapshot
 * price a partner once saw. The turn route stays unanswered - restoration
 * makes no model request.
 *
 * @param page  The page.
 * @param lang  The page's language.
 */
async function serveHistory(page: Page, lang: Lang): Promise<void> {
	const stream = [
		[
			'meta',
			{
				grounded: true,
				fallback: false,
				attempts: 1,
				failures: [],
				language: lang,
			},
		],
		[
			'block',
			{
				type: 'text',
				text:
					'en' === lang
						? 'The historical answer with its product card.'
						: 'Die frühere Antwort mit ihrer Produktkarte.',
				refs: [],
			},
		],
		[
			'block',
			{
				type: 'cards',
				product_ids: [PRODUCT],
				prices: [{ product_id: PRODUCT, text: '9.999,99 €' }],
			},
		],
		['done', { ok: true }],
	]
		.map(
			([event, data]) =>
				`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
		)
		.join('');
	await page.route('**/wp-json/linker-ai/v1/genie/turn', (route) =>
		route.fulfill({
			status: 500,
			contentType: 'application/json',
			body: '{"code":"history_only"}',
		})
	);
	// The app asks /genie/conversation?locale=..; a plain glob would not
	// match the query and the real backend would answer an empty thread.
	await page.route(
		/\/wp-json\/linker-ai\/v1\/genie\/conversation\?/,
		(route) =>
			route.fulfill({
				json: {
					messages: [
						{
							role: 'user',
							content:
								'en' === lang
									? 'Which inverters do you offer?'
									: 'Welche Wechselrichter bieten Sie an?',
						},
					],
					stream,
				},
			})
	);
	await page.route('**/wp-json/linker-ai/v1/genie/conversations', (route) =>
		// The app restores the thread only when the rail reports a
		// current conversation.
		route.fulfill({
			json: { current_id: 7, conversations: [] },
		})
	);
}

/** The workspace page with the conversation restored. */
async function restored(page: Page, lang: Lang, width: number): Promise<void> {
	await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
	await page.goto(
		instance().url + ('de' === lang ? '/de/genie/' : '/genie/'),
		{ waitUntil: 'load' }
	);
	await expect(page.locator('.linker-genie-app:visible')).toBeVisible();
}

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390] as const) {
		for (const state of [...STATES, 'guest' as const]) {
			test(`${state}-${lang}-${width}: the restored card carries this account's own current line`, async ({
				page,
				context,
			}) => {
				test.setTimeout(120_000);
				await seedConsentCookies(context);
				await serveHistory(page, lang);
				if ('guest' !== state) {
					await page.goto(
						loginLink(undefined, accounts[state].email)
					);
				}
				await restored(page, lang, width);

				const card = page
					.locator('.linker-genie-app article.linker-card')
					.first();
				await expect(card).toBeVisible({ timeout: 30_000 });
				const line = card.locator('.linker-card__price');
				if ('approved' === state) {
					await expect(line).toHaveText(/1[.,]680/);
					await expect(line).toHaveClass(/--net/);
				} else {
					await expect(line).toHaveText(
						LINES[lang][state as 'pending' | 'restricted' | 'guest']
					);
					await expect(line).toHaveClass(/--note/);
				}
				// The snapshot figure a partner once saw never survives a
				// restore.
				await expect(card).not.toContainText('9.999,99');
			});
		}

		test(`${lang}-${width}: a failed authority read clears the old price instead of leaving it`, async ({
			page,
			context,
		}) => {
			test.setTimeout(120_000);
			await seedConsentCookies(context);
			await serveHistory(page, lang);
			// The ability every restored card is re-priced through never
			// answers (its URL carries a query string, so the pattern
			// anchors on the path).
			await page.route(
				/\/wp-abilities\/v1\/abilities\/linker\/get-product\/run\?/,
				(route) => route.abort()
			);
			await restored(page, lang, width);

			const card = page
				.locator('.linker-genie-app article.linker-card')
				.first();
			await expect(card).toBeVisible({ timeout: 30_000 });
			await expect(
				card.locator('.linker-card__price'),
				'no authority line and no snapshot price remain'
			).toHaveCount(0);
			await expect(card).not.toContainText('9.999,99');
		});
	}
}
