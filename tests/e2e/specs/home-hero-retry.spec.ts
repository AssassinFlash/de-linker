/**
 * The home hero's failed ask and its recovery (matrix rows home:retry, all
 * languages and widths).
 *
 * A turn whose request never leaves the browser surfaces the hero's own
 * error alert with a Try again affordance; the retry resends the original
 * question from the restored draft, the real answer arrives in place, and
 * the page never navigates. English and German, 1440 and 390.
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

type Lang = 'en' | 'de';

/** The failure alert, its retry affordance and the ask, per language. */
const WORDS = {
	en: {
		home: '/',
		alert: 'Genie did not answer. Please try again.',
		retry: 'Try again',
		question: 'Which inverters do you offer?',
	},
	de: {
		home: '/de/',
		alert: 'Genie hat nicht geantwortet. Bitte versuchen Sie es erneut.',
		retry: 'Erneut versuchen',
		question: 'Welche Wechselrichter bieten Sie an?',
	},
} as const;

/** A page with the hero conversation reachable, in one shape. */
async function fresh(
	browser: Browser,
	lang: Lang,
	viewport: { width: number; height: number }
): Promise<Page> {
	const context = await browser.newContext({
		viewport,
		reducedMotion: 'reduce',
	});
	await seedConsentCookies(context);
	const page = await context.newPage();
	await page.goto(instance().url + WORDS[lang].home, {
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

for (const lang of ['en', 'de'] as const) {
	for (const viewport of [
		{ name: '1440', width: 1440, height: 900 },
		{ name: '390', width: 390, height: 844 },
	] as const) {
		test(`${lang}-${viewport.name}: a failed hero ask offers Try again and the retry delivers the answer`, async ({
			browser,
		}) => {
			test.setTimeout(400_000);
			const home = instance().url + WORDS[lang].home;
			const page = await fresh(browser, lang, viewport);

			// The first turn never leaves the browser; every later one passes.
			let refused = true;
			await page.route('**/wp-json/linker-ai/v1/genie/turn', (route) => {
				if (refused && 'POST' === route.request().method()) {
					refused = false;
					return route.abort();
				}
				return route.continue();
			});

			await page.fill('.hero-prompt', WORDS[lang].question);
			await page.press('.hero-prompt', 'Enter');
			await expect(
				page.locator('.hero-cinematic.linker-genie-hero--open')
			).toHaveCount(1);
			await expect(page.getByRole('alert')).toContainText(
				WORDS[lang].alert
			);
			const retry = page.getByRole('button', {
				name: WORDS[lang].retry,
			});
			await expect(retry).toBeVisible();

			await retry.click();
			await expect(
				page.locator('.linker-genie-reply').last()
			).toBeVisible({
				timeout: 240_000,
			});
			expect(page.url()).toBe(home);
			await page.context().close();
		});
	}
}
