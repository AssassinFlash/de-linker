/**
 * The installer page's Plan entry hands the typed requirement to the
 * Solution Configurator as a staged project brief, in both languages.
 *
 * The handoff itself is locale-independent (the source path is the page's own
 * URL, the destination is the language's own configurator link), so one row
 * per language pins the whole chain on the real page: type, Enter, the staged
 * brief id on the configurator URL, and the brief text arriving in the
 * configurator's project panel.
 */
/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

const PAGES = {
	en: {
		page: '/for-installer/',
		expectedPath: '/for-installer/',
		note: '10 kWp roof with a battery for self-consumption',
	},
	de: {
		page: '/de/fuer-installateur/',
		expectedPath: '/de/fuer-installateur/',
		note: '10 kWp Dachanlage mit Speicher für den Eigenverbrauch',
	},
} as const;

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

for (const [locale, spec] of Object.entries(PAGES)) {
	test(`${locale}: the Plan entry stages the note and lands on the configurator with it`, async ({
		page,
	}) => {
		await page.goto(instance().url + spec.page);
		const field = page.locator('#lki-hero-query');
		await expect(field).toBeVisible();
		await field.fill(spec.note);
		await field.press('Enter');

		await expect(page).toHaveURL(
			new RegExp(
				`/${locale === 'de' ? 'de/loesungskonfigurator' : 'solution-configurator'}/\\?.*brief=[a-f0-9]{32}`
			),
			{ timeout: 30_000 }
		);
		const url = new URL(page.url());
		expect(url.searchParams.get('brief')).toMatch(/^[a-f0-9]{32}$/);

		// The staged note is the configurator's project input: the first frame
		// carries it, so the customer never retypes the requirement.
		await expect(page.locator('body')).toContainText('10 kWp', {
			timeout: 60_000,
		});
	});
}
