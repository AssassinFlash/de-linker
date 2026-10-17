/**
 * Genie's preview card in a real browser (ticket #249; docs/specs/13-genie.md,
 * 目标 4 and "主动预览卡"; acceptance A3 of
 * docs/research/2026-10-17-ai-assistants/INTL.md §8). One test per rule, at
 * 1440 and 390, in English and German.
 *
 * Time is the page's own clock under Playwright's control (`page.clock`):
 * the card's 8-second wait and its 30-day memory run on that clock, so a
 * test fast-forwards instead of sleeping, and "30 days later" is a real
 * date the page reads.
 *
 * With LINKER_E2E_SHOTS=<dir> every state is also saved as a screenshot
 * (the acceptance record docs/acceptance/<date>/249/).
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
import { instance } from '../lib/instance';

type Lang = 'en' | 'de';
type Kind = 'home' | 'product' | 'category' | 'solution';

const PAGES: Record<Lang, Record<Kind, string>> = {
	en: {
		home: '/',
		product: '/product/saj-h2-10k-t3/',
		category: '/product-category/inverters/',
		solution: '/solution/residential-storage/',
	},
	de: {
		home: '/de/',
		product: '/de/produkt/saj-h2-10k-t3/',
		category: '/de/produkt-kategorie/wechselrichter/',
		solution: '/de/loesung/heimspeicher/',
	},
};

/** What each card's title must name: the page the visitor is on. */
const NAMED: Record<Lang, Record<Kind, RegExp>> = {
	en: {
		home: /Genie/,
		product: /SAJ H2-10K-T3/,
		category: /Inverters/,
		solution: /residential storage/,
	},
	de: {
		home: /Genie/,
		product: /SAJ H2-10K-T3/,
		category: /Wechselrichter/,
		solution: /Heimspeicher/,
	},
};

/** Pages that never carry the card (目标 4: forms, inquiry, sign-in). */
const NEVER = [
	'/cart/',
	'/proforma-request/',
	'/my-account/',
	'/contact/',
	'/solution-configurator/',
];

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const DWELL = 8_000;
const DAY = 86_400_000;
const START = new Date('2026-10-18T09:00:00Z');

const SHOTS = process.env.LINKER_E2E_SHOTS ?? '';

async function shot(page: Page, name: string): Promise<void> {
	if (!SHOTS) {
		return;
	}
	mkdirSync(SHOTS, { recursive: true });
	// The card's entrance is a CSS transition on the real clock; finish it.
	await page.screenshot({
		path: join(SHOTS, `${name}.png`),
		animations: 'disabled',
	});
}

/** Opens a page with the card's clock under the test's control. */
async function arrive(
	page: Page,
	path: string,
	time: Date = START
): Promise<void> {
	await page.clock.install({ time });
	await page.goto(`${instance().url}${path}`);
	await page.evaluate(() => document.fonts.ready);
}

/** Scrolls the anchor the card names well above the 40% line. */
async function scrollPast(page: Page): Promise<void> {
	await page.evaluate(() => {
		const card = document.querySelector<HTMLElement>(
			'[data-linker-genie-peek]'
		);
		const anchor = card?.dataset.anchor
			? document.querySelector(card.dataset.anchor)
			: null;
		const bottom = anchor
			? anchor.getBoundingClientRect().bottom + window.scrollY
			: window.innerHeight;
		window.scrollTo(0, Math.max(0, bottom - window.innerHeight * 0.3));
	});
}

const card = (page: Page) => page.locator('[data-linker-genie-peek]');
const dock = (page: Page) => page.locator('.linker-genie');

for (const lang of ['en', 'de'] as const) {
	test.describe(`the preview card (${lang})`, () => {
		test('appears only after the main content and the dwell, without taking the focus', async ({
			page,
		}) => {
			await page.setViewportSize(DESKTOP);
			await arrive(page, PAGES[lang].product);
			await page.clock.runFor(DWELL * 3);
			await expect(card(page), 'not on arrival').toBeHidden();
			await shot(page, `${lang}-1440-product-1-arrival`);

			await scrollPast(page);
			await page.clock.runFor(DWELL - 1_000);
			await expect(card(page), 'not before the dwell').toBeHidden();
			await shot(page, `${lang}-1440-product-2-scrolled-7s`);

			await page.clock.runFor(1_000);
			await expect(card(page)).toBeVisible();
			await expect(card(page)).toContainText(NAMED[lang].product);
			await page.clock.runFor(500); // the entrance
			expect(
				await page.evaluate(
					() => document.activeElement === document.body
				),
				'the focus stays where it was'
			).toBe(true);
			await shot(page, `${lang}-1440-product-3-card`);
		});

		for (const kind of ['home', 'category', 'solution'] as const) {
			test(`names the ${kind} page`, async ({ page }) => {
				await page.setViewportSize(DESKTOP);
				await arrive(page, PAGES[lang][kind]);
				await scrollPast(page);
				await page.clock.runFor(DWELL + 500);
				await expect(card(page)).toBeVisible();
				await expect(
					page.locator('.linker-genie-peek__title')
				).toContainText(NAMED[lang][kind]);
				const asks = await page
					.locator('[data-linker-genie-peek-ask]')
					.count();
				expect(asks).toBeGreaterThanOrEqual(2);
				expect(asks).toBeLessThanOrEqual(4);
				await expect(page.locator('.linker-genie-peek__ai')).toHaveText(
					lang === 'de' ? /KI/ : /AI/
				);
				await shot(page, `${lang}-1440-${kind}-card`);
			});
		}

		test('the home card waits until the hero is passed', async ({
			page,
		}) => {
			await page.setViewportSize(DESKTOP);
			await arrive(page, PAGES[lang].home);
			await page.evaluate(() => window.scrollTo(0, 200));
			await page.clock.runFor(DWELL * 2);
			await expect(card(page), 'still inside the hero').toBeHidden();
			await shot(page, `${lang}-1440-home-0-in-hero`);
		});

		test('once per visit', async ({ page }) => {
			await page.setViewportSize(DESKTOP);
			await arrive(page, PAGES[lang].product);
			await scrollPast(page);
			await page.clock.runFor(DWELL + 500);
			await expect(card(page)).toBeVisible();

			// The next page of the same visit (same tab, same session).
			await page.goto(`${instance().url}${PAGES[lang].category}`);
			await scrollPast(page);
			await page.clock.runFor(DWELL * 2);
			await expect(card(page), 'not twice in one visit').toBeHidden();
			await shot(page, `${lang}-1440-category-once-per-visit`);
		});

		test('closed: away for 30 days, back after them', async ({
			context,
			page,
		}) => {
			await page.setViewportSize(DESKTOP);
			await arrive(page, PAGES[lang].category);
			await scrollPast(page);
			await page.clock.runFor(DWELL + 500);
			await page.locator('[data-linker-genie-peek-close]').click();
			await expect(card(page)).toBeHidden();
			await shot(page, `${lang}-1440-category-closed`);

			// A new visit (a new tab has its own session) 29 days later …
			const later = await context.newPage();
			await later.setViewportSize(DESKTOP);
			await arrive(
				later,
				PAGES[lang].product,
				new Date(START.getTime() + 29 * DAY)
			);
			await scrollPast(later);
			await later.clock.runFor(DWELL * 2);
			await expect(
				card(later),
				'still closed after 29 days'
			).toBeHidden();
			await shot(later, `${lang}-1440-product-closed-29-days`);
			await later.close();

			// … and one 31 days later.
			const after = await context.newPage();
			await after.setViewportSize(DESKTOP);
			await arrive(
				after,
				PAGES[lang].product,
				new Date(START.getTime() + 31 * DAY)
			);
			await scrollPast(after);
			await after.clock.runFor(DWELL + 500);
			await expect(card(after), 'back after 30 days').toBeVisible();
			await shot(after, `${lang}-1440-product-back-after-31-days`);
			await after.close();
		});

		test('never during a conversation', async ({ page }) => {
			await page.setViewportSize(DESKTOP);
			await arrive(page, PAGES[lang].product);
			await page.locator('.linker-genie-open').click();
			await expect(
				page.locator('.linker-genie-app__composer')
			).toBeVisible({ timeout: 30_000 });
			await scrollPast(page);
			await page.clock.runFor(DWELL * 2);
			await expect(card(page), 'not while Genie is open').toBeHidden();
			await shot(page, `${lang}-1440-product-conversation-open`);
		});

		test('waits while the visitor types', async ({ page }) => {
			await page.setViewportSize(DESKTOP);
			await arrive(page, PAGES[lang].category);
			await scrollPast(page);
			await page.evaluate(() => {
				const field = document.createElement('input');
				field.id = 'e2e-field';
				field.style.cssText =
					'position:fixed;top:120px;left:20px;z-index:20000';
				document.body.appendChild(field);
			});
			await page.locator('#e2e-field').fill('SAJ');
			await page.clock.runFor(DWELL * 2);
			await expect(card(page), 'not while typing').toBeHidden();
			await expect(page.locator('#e2e-field')).toBeFocused();
			await shot(page, `${lang}-1440-category-typing`);

			await page.locator('#e2e-field').blur();
			await page.clock.runFor(100);
			await expect(card(page), 'once the field is left').toBeVisible();
		});

		test('a suggestion asks Genie through the dock', async ({ page }) => {
			test.setTimeout(240_000);
			await page.setViewportSize(DESKTOP);
			await arrive(page, PAGES[lang].product);
			await scrollPast(page);
			await page.clock.runFor(DWELL + 500);
			const first = page.locator('[data-linker-genie-peek-ask]').first();
			const question = (await first.getAttribute(
				'data-linker-genie-peek-ask'
			)) as string;
			// The real model answers in real time from here on.
			await page.clock.resume();
			await first.click();
			await expect(card(page)).toBeHidden();
			await expect(
				page.locator('.linker-genie-app__message--user').first()
			).toHaveText(question, { timeout: 30_000 });
			await expect
				.poll(
					async () =>
						page.locator('.linker-genie-app__votes').count(),
					{ message: 'Genie answers', timeout: 180_000 }
				)
				.toBeGreaterThan(0);
			await shot(page, `${lang}-1440-product-suggestion-answered`);
		});

		for (const kind of ['product', 'home'] as const) {
			test(`on a phone (${kind}): only a mark on the Genie button`, async ({
				page,
			}) => {
				await page.setViewportSize(PHONE);
				await arrive(page, PAGES[lang][kind]);
				await expect(
					page.locator('.linker-genie-open'),
					'no button at rest, as on the live page'
				).toBeHidden();
				await scrollPast(page);
				await page.clock.runFor(DWELL + 500);
				await expect(dock(page)).toHaveClass(/linker-genie--peek/);
				await expect(card(page), 'no card on a phone').toBeHidden();
				await expect(page.locator('.linker-genie-open')).toBeVisible();
				const mark = await page.evaluate(
					() =>
						getComputedStyle(
							document.querySelector(
								'.linker-genie-open'
							) as Element,
							'::after'
						).backgroundColor
				);
				expect(mark, 'the red mark').toBe('rgb(214, 54, 56)');
				expect(
					await page.evaluate(
						() => document.activeElement === document.body
					)
				).toBe(true);
				await shot(page, `${lang}-390-${kind}-mark`);

				// The mark opens Genie, and goes with it.
				await page.clock.resume();
				await page.locator('.linker-genie-open').click();
				await expect(
					page.locator('.linker-genie-app__composer')
				).toBeVisible({ timeout: 30_000 });
				await expect(dock(page)).not.toHaveClass(/linker-genie--peek/);
				await shot(page, `${lang}-390-${kind}-mark-opened`);
			});
		}
	});
}

test.describe('pages without the card', () => {
	for (const path of NEVER) {
		test(`${path} carries no card`, async ({ page }) => {
			await page.setViewportSize(DESKTOP);
			await page.goto(`${instance().url}${path}`);
			await expect(card(page)).toHaveCount(0);
		});
	}
});
