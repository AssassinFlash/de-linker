/**
 * A saved Genie solution is read back by its consumer (matrix row
 * genie:consumer-saved-solution-readback, docs/specs/13-genie.md 目标).
 *
 * An approved customer asks the live Genie a product question whose answer
 * carries a product card with a server-signed proof, saves the card's
 * solution, and reads the solution back on the account's own Saved solutions
 * screen: the saved row names the product, counts it, and returns it to the
 * solution draft. The proof lives only in the live turn (history never
 * recreates one), so the save happens in the conversation that produced the
 * card.
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

/** The question whose live answer is proven to carry a product card. */
const QUESTIONS = {
	en: {
		ask: 'What does the SAJ H2-10K-T3 cost?',
		products: '/products/',
		save: 'Save solution',
		saved: 'Saved to your account.',
		account: '/my-account/saved-solutions/',
		addToDraft: 'Add to solution draft',
		notice: 'The products of the saved solution are in your solution draft.',
	},
	de: {
		ask: 'Was kostet der SAJ H2-10K-T3?',
		products: '/de/produkte/',
		save: 'L\u00f6sung speichern',
		saved: 'Im Konto gespeichert.',
		account: '/de/mein-konto/gespeicherte-loesungen/',
		addToDraft: 'Zum L\u00f6sungsentwurf hinzuf\u00fcgen',
		notice: 'Die Produkte der gespeicherten L\u00f6sung liegen jetzt in Ihrem L\u00f6sungsentwurf.',
	},
} as const;

/** The run's own account, made before and removed after. */
const email = `genie-save-e2e-${Date.now()}@example.test`;
let customerId = 0;

test.beforeAll(() => {
	customerId = Number(
		wp([
			'eval',
			`$id = wp_insert_user( array( 'user_login' => '${email}', 'user_email' => '${email}', 'user_pass' => wp_generate_password(), 'role' => 'customer' ) );` +
				`update_user_meta( $id, 'linker_approval_status', 'approved' ); echo $id;`,
		]).trim()
	);
});

test.afterAll(() => {
	if (customerId > 0) {
		wp(['user', 'delete', String(customerId), '--yes']);
	}
});

/**
 * Asks Genie through the dock loader's own event (the entry the product
 * page's ask button uses) and waits for the answer's first product card.
 *
 * @param page   The page.
 * @param launch The question to send.
 */
async function askGenie(
	page: Page,
	launch: string,
	saveLabel: string
): Promise<void> {
	await page.evaluate((message) => {
		window.dispatchEvent(
			new CustomEvent('linker-genie-ask', { detail: { message } })
		);
	}, launch);
	const card = page.locator('.linker-genie-app article.linker-card').first();
	await expect(card).toBeVisible({ timeout: 180_000 });
	// The card is complete once its model line has come in too.
	await expect(card.locator('.linker-card__model')).toBeVisible({
		timeout: 30_000,
	});
	// The save action arrives with the stream's proof at the answer's very
	// end - a slow German stream can keep it absent for minutes.
	await expect(card.getByRole('button', { name: saveLabel })).toBeVisible({
		timeout: 180_000,
	});
}

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		const words = QUESTIONS[locale];
		test(`${locale}-${width}: the solution a customer saves from Genie is on their account and returns to the draft`, async ({
			page,
			context,
		}) => {
			test.setTimeout(400_000);
			await seedConsentCookies(context);
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await page.goto(loginLink(undefined, email));

			await page.goto(instance().url + words.products);
			await askGenie(page, words.ask, words.save);
			const card = page
				.locator('.linker-genie-app article.linker-card')
				.first();

			// The save posts the live card's proof; the account store answers
			// with the saved solution's own id and address.
			const saved = page.waitForResponse(
				(response) =>
					response
						.url()
						.includes('/wp-json/linker-ai/v1/genie/solution') &&
					response.request().method() === 'POST'
			);
			await card.getByRole('button', { name: words.save }).click();
			const response = await saved;
			expect(response.status(), 'the account save is confirmed').toBe(
				201
			);
			const payload = (await response.json()) as {
				id: number;
				url: string;
			};
			expect(payload.id).toBeGreaterThan(0);
			expect(payload.url).toContain(words.account);
			await expect(card).toContainText(words.saved);

			// The consumer reads the solution back on their account screen.
			await page.goto(instance().url + words.account);
			const row = page.locator(`#linker-solution-${payload.id}`);
			await expect(row).toBeVisible();
			await expect(row).toContainText('H2-10K-T3');
			await expect(row).toContainText('1 × ');

			// And returns it to the solution draft.
			await row.getByRole('button', { name: words.addToDraft }).click();
			// The draft's own page opens: the German endpoint segment is
			// loesungsentwurf, the English one cart.
			await expect(page).toHaveURL(
				locale === 'de' ? /loesungsentwurf/ : /cart/
			);
			await expect(page.locator('.woocommerce-message')).toContainText(
				words.notice
			);
		});
	}
}
