/**
 * The consent surface (docs/specs/201-consent-ga4.md): the banner, the held
 * Google tag, the order-source cookies and the withdrawal path.
 *
 * What is asserted here and what is not: the instance carries the local
 * isolation layer's CSP (tools/local/mu/000-linker-local-isolation.php), which
 * has no Google origin — a request to googletagmanager.com cannot leave this
 * machine by design. The suite therefore asserts the *mechanism* the visitor's
 * browser acts on: whether Complianz holds the tag (its script type), whether
 * the two purposes' cookies are written, and whether the footer entry reopens
 * the banner. The end-to-end Basic behaviour (requests to Google before and
 * after the answer) is measured where Google can be reached
 * (docs/research/2026-10-16/consent-ga4-carrier.md, tests 1-2) and guarded on
 * production by `just cutover verify`'s consent segment.
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from '../lib/instance';

/** Complianz writes these; the two purposes' own cookies are sbjs_* and _ga*. */
const PURPOSE_COOKIES = /^(sbjs_|_ga)/;

async function cookies(
	context: import('@playwright/test').BrowserContext
): Promise<string[]> {
	const all = await context.cookies();
	return all
		.map((cookie) => cookie.name)
		.filter((name) => PURPOSE_COOKIES.test(name))
		.sort();
}

/**
 * The tag as the browser has it: `type="text/plain"` plus the real address
 * parked in `data-cmplz-src` is Complianz's blocker holding it; `src` set and
 * `class="cmplz-activated"` is the released tag (measured on the instance,
 * docs/research/2026-10-16/consent-ga4-carrier.md).
 */
async function tagState(
	page: import('@playwright/test').Page
): Promise<{ type: string | null; src: string | null } | null> {
	return page.evaluate(() => {
		const tag = document.getElementById('google_gtagjs-js');
		return tag
			? { type: tag.getAttribute('type'), src: tag.getAttribute('src') }
			: null;
	});
}

/**
 * `window.dataLayer` as the page has built it. TypeScript's DOM lib does not
 * know it (Site Kit pushes into it at runtime), so the page-side code reads it
 * through `globalThis`.
 */
type DataLayerEntry = unknown[];

/** The consent state the dataLayer carries for Google (`consent` entries only). */
async function consentUpdates(
	page: import('@playwright/test').Page
): Promise<Record<string, string>[]> {
	return page.evaluate(() => {
		const layer =
			(globalThis as { dataLayer?: DataLayerEntry[] }).dataLayer ?? [];
		return layer
			.filter((entry) => entry[0] === 'consent' && entry[1] === 'update')
			.map((entry) => entry[2] as Record<string, string>);
	});
}

for (const [language, path] of [
	['EN', '/'],
	['DE', '/de/'],
] as const) {
	test(`${language}: nothing optional runs before the visitor answers`, async ({
		browser,
	}) => {
		const context = await browser.newContext();
		const page = await context.newPage();
		await page.goto(instance().url + path, {
			waitUntil: 'domcontentloaded',
		});

		const banner = page.locator('.cmplz-cookiebanner');
		await expect(banner).toBeVisible();

		// The first layer offers both answers with equal weight, plus the step
		// to choose purposes.
		await expect(banner.locator('.cmplz-accept')).toBeVisible();
		await expect(banner.locator('.cmplz-deny')).toBeVisible();
		await expect(banner.locator('.cmplz-view-preferences')).toBeVisible();

		// Site Kit's tag is printed but held: this is the Basic contract, and
		// it is also the regression guard for Complianz's Site Kit
		// integration, whose whitelist would let the tag run.
		const held = await tagState(page);
		expect(held?.type, 'the Google tag is held before consent').toBe(
			'text/plain'
		);
		expect(
			held?.src,
			'the address does not load before consent'
		).toBeNull();

		expect(
			await cookies(context),
			'no purpose cookies before the answer'
		).toEqual([]);

		// The consent defaults reach the dataLayer before anything else and
		// deny every Google purpose.
		const defaults = await page.evaluate(() => {
			const layer =
				(globalThis as { dataLayer?: DataLayerEntry[] }).dataLayer ??
				[];
			const entry = layer.find(
				(item) => item[0] === 'consent' && item[1] === 'default'
			);
			return JSON.stringify(entry?.[2] ?? null);
		});
		expect(defaults, 'the consent defaults are in the dataLayer').not.toBe(
			'null'
		);
		expect(JSON.parse(defaults ?? '{}')).toMatchObject({
			ad_storage: 'denied',
			ad_user_data: 'denied',
			ad_personalization: 'denied',
			analytics_storage: 'denied',
		});
		expect(
			JSON.parse(defaults ?? '{}'),
			'no region carve-out'
		).not.toHaveProperty('region');

		await context.close();
	});

	test(`${language}: accepting releases the tag and lets the order source record`, async ({
		browser,
	}) => {
		const context = await browser.newContext();
		const page = await context.newPage();
		await page.goto(instance().url + path, {
			waitUntil: 'domcontentloaded',
		});
		await page.locator('.cmplz-cookiebanner .cmplz-accept').first().click();

		// The tag is released: the blocker hands the parked address over to src.
		await expect
			.poll(async () => (await tagState(page))?.src, {
				message: 'the tag is released',
			})
			.toContain('googletagmanager.com');

		// And the answer reaches Google as a consent update: statistics
		// granted, nothing advertising (the site has no Google advertising
		// tag, so the marketing answer grants Google nothing).
		await expect
			.poll(async () =>
				(await consentUpdates(page)).some(
					(u) => u.analytics_storage === 'granted'
				)
			)
			.toBe(true);
		expect(
			(await consentUpdates(page)).some(
				(u) =>
					u.ad_storage === 'granted' || u.ad_user_data === 'granted'
			),
			'no advertising signal is granted'
		).toBe(false);

		// WooCommerce's order source is the marketing purpose, gated by
		// wp_has_consent( 'marketing' ): it records now.
		await expect
			.poll(() => cookies(context), {
				message: 'the order source records',
			})
			.toEqual(expect.arrayContaining(['sbjs_current']));

		await context.close();
	});
}

test('EN: the footer entry reopens the banner, withdrawing clears the order source', async ({
	browser,
}) => {
	const context = await browser.newContext();
	const page = await context.newPage();
	await page.goto(instance().url + '/', { waitUntil: 'domcontentloaded' });
	await page.locator('.cmplz-cookiebanner .cmplz-accept').first().click();
	await expect
		.poll(() => cookies(context))
		.toEqual(expect.arrayContaining(['sbjs_current']));

	// The visitor's withdrawal path: the site's own footer entry (the LC
	// partial's button), which Complianz's delegated handler answers.
	const entry = page.locator('.tv-footer-bar-legal .cmplz-manage-consent');
	await expect(entry).toBeVisible();
	await entry.click();
	const banner = page.locator('.cmplz-cookiebanner');
	await expect(banner).toBeVisible();

	await banner.locator('.cmplz-deny').first().click();
	await expect
		.poll(async () => (await tagState(page))?.type)
		.toBe('text/plain');
	await expect
		.poll(() => cookies(context), {
			message: 'the withdrawal clears the cookies',
		})
		.toEqual([]);

	// And the answer survives a reload: the visitor is not asked twice.
	await page.reload({ waitUntil: 'domcontentloaded' });
	await expect(banner).toBeHidden();
	await expect.poll(() => cookies(context)).toEqual([]);

	await context.close();
});
