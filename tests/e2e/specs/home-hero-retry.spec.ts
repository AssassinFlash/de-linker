/**
 * The home hero's failed ask and its recovery (matrix row home:retry:en:1440).
 *
 * A turn whose request never leaves the browser surfaces the hero's own
 * error alert with a Try again affordance; the retry resends the original
 * question from the restored draft, the real answer arrives in place, and
 * the page never navigates. English at 1440, the row's own shape.
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

/** The home page in English. */
const HOME = instance().url + '/';

/** A page with the hero conversation reachable, in the row's own viewport. */
async function fresh(browser: Browser): Promise<Page> {
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
		reducedMotion: 'reduce',
	});
	await seedConsentCookies(context);
	const page = await context.newPage();
	await page.goto(HOME, { waitUntil: 'load' });
	await page.evaluate(() => document.fonts.ready);
	await expect(page.locator('.hero-prompt')).toBeVisible();
	// The entry is bound before a control may be trusted (controller.tsx).
	await expect(
		page.locator('.hero-cinematic[data-linker-genie-hero="ready"]')
	).toHaveCount(1);
	return page;
}

test('a failed hero ask offers Try again and the retry delivers the answer', async ({
	browser,
}) => {
	test.setTimeout(400_000);
	const page = await fresh(browser);

	// The first turn never leaves the browser; every later one passes.
	let refused = true;
	await page.route('**/wp-json/linker-ai/v1/genie/turn', (route) => {
		if (refused && 'POST' === route.request().method()) {
			refused = false;
			return route.abort();
		}
		return route.continue();
	});

	await page.fill('.hero-prompt', 'Which inverters do you offer?');
	await page.press('.hero-prompt', 'Enter');
	await expect(
		page.locator('.hero-cinematic.linker-genie-hero--open')
	).toHaveCount(1);
	await expect(page.getByRole('alert')).toContainText(
		'Genie did not answer. Please try again.'
	);
	const retry = page.getByRole('button', { name: 'Try again' });
	await expect(retry).toBeVisible();

	await retry.click();
	await expect(page.locator('.linker-genie-reply').last()).toBeVisible({
		timeout: 240_000,
	});
	expect(page.url()).toBe(HOME);
	await page.context().close();
});
