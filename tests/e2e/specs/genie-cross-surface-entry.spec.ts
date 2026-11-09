/**
 * An entry question is consumed by the conversation exactly once, across
 * surfaces (matrix row genie:cross-surface-entry-question-consumed).
 *
 * A question asked through the home hero - the entry surface whose activation
 * gate defered this row to CU - becomes the conversation's first user message
 * (the composer empties), and the same conversation on the products-page dock
 * carries that question once: it is never re-offered as a pending entry, and
 * a follow-up posts the thread with the entry question still as its first
 * message - consumed, not duplicated.
 */

/**
 * External dependencies
 */
import { expect, test, type Browser, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from '../lib/instance';
import { seedConsentCookies } from '../lib/consent';

/** The question the hero entry consumes. */
const QUESTION = 'Which inverters do you offer?';

/** A page at the home hero, the row's own viewport. */
async function home(browser: Browser): Promise<Page> {
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
		reducedMotion: 'reduce',
	});
	await seedConsentCookies(context);
	const page = await context.newPage();
	await page.goto(instance().url + '/', { waitUntil: 'load' });
	await page.evaluate(() => document.fonts.ready);
	await expect(page.locator('.hero-prompt')).toBeVisible();
	await expect(
		page.locator('.hero-cinematic[data-linker-genie-hero="ready"]')
	).toHaveCount(1);
	return page;
}

test('the hero entry question is consumed once and continues across surfaces', async ({
	browser,
}) => {
	test.setTimeout(400_000);
	const page = await home(browser);

	// The entry question is consumed: sent as the conversation's own first
	// user message, the composer left empty.
	await page.fill('.hero-prompt', QUESTION);
	await page.press('.hero-prompt', 'Enter');
	await expect(
		page.locator('.hero-cinematic.linker-genie-hero--open')
	).toHaveCount(1);
	await expect(page.locator('.linker-genie-reply').last()).toBeVisible({
		timeout: 240_000,
	});
	const surface = page.locator('.linker-genie-hero__surface');
	await expect(surface).toContainText(QUESTION);
	await expect(page.locator('.hero-prompt')).toHaveValue('');

	// The same conversation on the products-page dock: the question stands
	// once, and no pending entry re-offers it.
	await page.goto(instance().url + '/products/', {
		waitUntil: 'load',
	});
	await page.locator('.linker-genie-open').first().click();
	const app = page.locator('.linker-genie-app:visible');
	await expect(app).toBeVisible({ timeout: 30_000 });
	const asked = app.getByText(QUESTION, { exact: true });
	await expect(asked.first()).toBeVisible();
	expect(
		await asked.count(),
		'the entry question stands once, never duplicated'
	).toBe(1);
	await expect(
		app.locator('[data-genie-entry-review]'),
		'the consumed entry is never re-offered'
	).toHaveCount(0);

	// A follow-up posts the thread with the entry question still first:
	// consumed into the conversation, not parked and not duplicated.
	const posted = page.waitForRequest(
		(request) =>
			request.url().includes('/genie/turn') && 'POST' === request.method()
	);
	await app
		.locator('.linker-genie-app__input')
		.fill('And which battery pairs with it?');
	await app.locator('.linker-genie-app__send').click();
	const body = (
		(await posted).postDataJSON() as {
			messages: { role: string; content: string }[];
		}
	).messages;
	expect(body[0]).toEqual({ role: 'user', content: QUESTION });
	expect(body.filter((message) => message.content === QUESTION)).toHaveLength(
		1
	);
	await page.context().close();
});
