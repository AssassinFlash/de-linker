/**
 * The Genie shell in the page (docs/specs/13-genie.md §C): the disclosure
 * when the dock opens, the product page's chip carrying its model, the
 * signed-in customer's own inquiry, and what a reload does with the thread.
 *
 * These are the R1–R14 rows that only exist in a browser: R13's entry is the
 * chip, and R7's second half needs a session. The rest of the panel is asked
 * of the service in genie.spec.ts.
 */

/**
 * External dependencies
 */
import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, loginLink, wp } from '../lib/instance';
import { TEAM_MAIL } from '../lib/expectations';

const PRODUCT = '/product/saj-h2-10k-t3/';
const ACCOUNT = '/my-account/';
const CUSTOMER = 'e2e-catalogue@example.test';

/** The disclosure sentence the dock speaks once. */
const DISCLOSURE =
	/You're chatting with an AI system|Sie chatten mit einem KI-System/;

/**
 * Opens the dock and the app's own panel.
 *
 * Two steps, because the shell has two: the standing button reveals the mount
 * and loads the app on the first click (Entries.php), and the app opens its
 * panel with its own toggle.
 */
async function openDock(page: Page): Promise<void> {
	// The standing button, not one of the page's chips: both carry
	// `data-linker-genie-open` and a page may have several chips.
	await page.locator('.linker-genie-open').first().click();
	await ensureOpen(page);
}

/** Opens the app's own panel once it is loaded (the dock may have done it). */
async function ensureOpen(page: Page): Promise<void> {
	const toggle = page.locator('.linker-genie-app__toggle');
	await expect(toggle, 'the app is loaded').toBeAttached({ timeout: 30_000 });
	if ((await toggle.getAttribute('aria-expanded')) !== 'true') {
		// On the product page the app's closed bar hides (the resting bar
		// covered the buy box's action row, so the page's entries are the
		// standing bubble and the buy box's own ask button), and a loaded
		// toggle inside that bar carries no box to click: there the buy box's
		// ask button is what opens the panel.
		if (await toggle.isVisible()) {
			await toggle.click();
		} else {
			await page.locator('[data-pdp-ask]').first().click();
		}
	}
	await expect(page.locator('.linker-genie-app__composer')).toBeVisible({
		timeout: 30_000,
	});
}

/**
 * Asks one question in the dock and returns once the answer has landed.
 *
 * "Landed" is the vote buttons under the assistant's message: the app shows a
 * "Genie is thinking…" placeholder with the same message class while the turn
 * is in flight, and the votes only render for an answered turn. Counting
 * messages would return on the placeholder and read a page mid-turn.
 */
async function ask(page: Page, question: string): Promise<string> {
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
	return (await page.locator('.linker-genie-app__panel').innerText()).trim();
}

test.describe('the Genie dock', () => {
	test('the disclosure is spoken once when the dock opens', async ({
		page,
	}) => {
		await page.goto(`${instance().url}${PRODUCT}`);
		await openDock(page);
		const disclosure = page.locator('.linker-genie-app__disclosure');
		await expect(disclosure, 'the AI disclosure is there').toHaveCount(1);
		expect(
			await disclosure.innerText(),
			'the AI disclosure is there'
		).toMatch(DISCLOSURE);
		const panel = await page
			.locator('.linker-genie-app__panel')
			.innerText();
		expect(
			[...panel.matchAll(new RegExp(DISCLOSURE.source, 'g'))].length,
			'the disclosure is said once'
		).toBe(1);
	});

	test('the product page chip asks about its own model (R13)', async ({
		page,
	}) => {
		await page.goto(`${instance().url}${PRODUCT}`);
		const chip = page
			.locator('[data-linker-genie-chip], .linker-genie-chip, button', {
				hasText: /pairs with this model|Was passt zu diesem Modell/i,
			})
			.first();
		test.skip(
			(await chip.count()) === 0,
			"pending-main: the product template does not carry the Genie chips yet (#13 §C Entries, the template side is the main line's)"
		);
		const posted: Array<Record<string, unknown>> = [];
		page.on('request', (request) => {
			if (
				request.url().includes('/genie/turn') &&
				request.method() === 'POST'
			) {
				const body = request.postDataJSON() as {
					page?: Record<string, unknown>;
				};
				posted.push(body.page ?? {});
			}
		});
		await chip.click();
		await expect
			.poll(async () => posted.length, { timeout: 60_000 })
			.toBeGreaterThan(0);
		expect(posted[0]!.type, 'the chip asks from the product page').toBe(
			'product'
		);
		expect(posted[0]!.product_id, 'with the model it belongs to').toBe(
			4107
		);
	});

	test('a signed-in customer can ask about their own Proforma (R7)', async ({
		page,
	}) => {
		test.setTimeout(600_000);
		// A real inquiry on the suite customer's account, so the answer has
		// something of theirs to name. The customer journey that creates one
		// through the pages is commerce.spec.ts's; here it is the fixture the
		// Genie path needs.
		const inquiry = JSON.parse(
			wp([
				'eval',
				`$customer = get_user_by( 'email', '${CUSTOMER}' );` +
					`if ( ! $customer ) { echo 'null'; exit; }` +
					`$orders = wc_get_orders( array( 'customer_id' => $customer->ID, 'limit' => 1, 'orderby' => 'date', 'order' => 'DESC' ) );` +
					`if ( array() === $orders ) {` +
					`$order = wc_create_order( array( 'customer_id' => $customer->ID ) );` +
					`$product = wc_get_product( 4107 );` +
					`if ( $product ) { $order->add_product( $product, 1 ); }` +
					`$order->set_status( 'inquiry-received' );` +
					`$order->calculate_totals( false );` +
					`$order->save(); $orders = array( $order ); }` +
					`echo wp_json_encode( array( 'id' => $orders[0]->get_id(), 'number' => (string) $orders[0]->get_order_number() ) );`,
			]).trim()
		) as { id: number; number: string } | null;
		test.skip(
			inquiry === null,
			'pending-main: the suite customer of products.spec.ts does not exist on this instance yet'
		);

		await page.goto(loginLink(undefined, CUSTOMER));
		await page.goto(`${instance().url}${ACCOUNT}`);
		// The account page's own chip is the entry the protocol names for R7;
		// the dock's standing button is the fallback.
		const chip = page.locator('.linker-genie-chip', {
			hasText: /Proforma/i,
		});
		test.skip(
			(await chip.count()) === 0,
			'pending-main: the account page carries no Genie chip for the Proforma (docs/specs/13-genie.md §C Entries)'
		);
		// The chip is the protocol's entry for R7, but a click on it opens the
		// dock without asking its own question (measured 2026-10-11: the chip
		// carries no question payload and the loader only reveals the mount),
		// so the question is typed. The R7 path — the session, the service, the
		// ability — is the same either way.
		await chip.first().click();
		await ensureOpen(page);
		const answer = await ask(page, 'Where does my Proforma stand?');
		// The status label can only come from the customer's own inquiry list:
		// a guest's turn gets `login_required` and asks for a login instead.
		expect(
			answer,
			`the answer reports the inquiry's own status (inquiry ${inquiry!.number})`
		).toMatch(/Inquiry received|Anfrage eingegangen/i);
		expect(answer, 'and the account view of it').toMatch(
			/View your inquiry|Ihre Anfrage/i
		);
		expect(answer, 'and not asked to log in').not.toMatch(
			/log ?in|sign ?in/i
		);
	});

	test('a reload restores the thread instead of starting over', async ({
		page,
	}) => {
		test.setTimeout(600_000);
		await page.goto(`${instance().url}${PRODUCT}`);
		await openDock(page);
		// On the product page the panel opens through the buy box's own ask
		// button, and the app drops a send while a turn is in flight: the
		// opening turn's answer (its votes) must land before the suite's own
		// question goes out.
		await expect(
			page.locator('.linker-genie-app__votes').first()
		).toBeVisible({ timeout: 180_000 });
		const question = 'Which hybrid inverters do you carry for homes?';
		await ask(page, question);
		const before = await page
			.locator('.linker-genie-app__panel')
			.innerText();

		// What the restore asked and what it got: the message a failure needs.
		const restores: string[] = [];
		page.on('response', (response) => {
			if (response.url().includes('/genie/conversation')) {
				void response
					.text()
					.then((body) => restores.push(body.slice(0, 120)))
					.catch(() => restores.push('(unreadable)'));
			}
		});
		await page.reload();
		await openDock(page);
		// The restore is one fetch on mount, and the panel exists a moment
		// before it lands: wait for the content instead of racing it.
		const panel = page.locator('.linker-genie-app__panel');
		const state = await page.evaluate(() => ({
			apps: document.querySelectorAll('[data-linker-app="genie"]').length,
			rendered: document.querySelectorAll('.linker-genie-app').length,
			open: document.querySelectorAll('.linker-genie-app__panel').length,
			thread: document.querySelectorAll('.linker-genie-app__message')
				.length,
			threadUrl: document
				.querySelector('[data-linker-app="genie"]')
				?.getAttribute('data-thread-url'),
		}));
		await expect(
			panel,
			`the question the customer asked is still there (restores: ${restores.join(' || ') || 'none'}; state: ${JSON.stringify(state)})`
		).toContainText(question, { timeout: 20_000 });
		const opening = before
			.split('\n')
			.find((line) => line.length > 40)
			?.slice(0, 40);
		if (opening) {
			await expect(panel, 'the answer is still there').toContainText(
				opening,
				{ timeout: 20_000 }
			);
		}
	});
});
