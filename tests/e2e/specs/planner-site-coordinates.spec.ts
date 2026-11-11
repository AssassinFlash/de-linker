/**
 * The project brief's site coordinates are a datum, not a local convention.
 *
 * The first save after an address was typed used to be blocked by the
 * coordinate fields: the brief reported a format error for a coordinate the
 * customer had copied, because the parser demanded the interface language's
 * own decimal mark. Every map, receiver and datasheet writes latitude and
 * longitude with a point, so a German site refused `48.1689` and an English
 * site refused `48,1689` — the same value, unreadable with the reader's
 * keyboard layout swapped. Empty coordinates were the same defect's other
 * face: the field asked for a number where the brief means "not provided".
 *
 * Asserted here, on the deployed planner:
 * - an address alone is saveable, with both coordinates left empty, in both
 *   languages (this is what blocked the first save);
 * - a coordinate pasted with the other language's mark is accepted, and the
 *   saved revision reads back as the number it denotes;
 * - the field states which marks it accepts, so the customer is not left
 *   guessing at the format.
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

type Lang = 'en' | 'de';

const WORDS = {
	en: {
		configurator: '/solution-configurator/',
		newProject: 'New project',
		createProject: 'Create project',
		saveProject: 'Save project',
		latitude: 'Latitude',
		longitude: 'Longitude',
		address: 'Address or location reference',
		format: 'Decimal point or comma; no thousands separators.',
		saved: /^Saved/i,
	},
	de: {
		configurator: '/de/loesungskonfigurator/',
		newProject: 'Neues Projekt',
		createProject: 'Projekt anlegen',
		saveProject: 'Projekt speichern',
		latitude: 'Breitengrad',
		longitude: 'Längengrad',
		address: 'Adresse oder Standortbezeichnung',
		format: 'Dezimalpunkt oder Dezimalkomma; keine Tausendertrennzeichen.',
		saved: /^Gespeichert/i,
	},
} as const;

async function openProject(
	page: import('@playwright/test').Page,
	lang: Lang,
	title: string
): Promise<void> {
	const words = WORDS[lang];
	await page.goto(instance().url + words.configurator, {
		waitUntil: 'networkidle',
	});
	await page.getByRole('button', { name: words.newProject }).first().click();
	await page.locator('input[maxlength="256"]').first().fill(title);
	await page.getByRole('button', { name: words.createProject }).click();
	await expect(page).toHaveURL(/project=/, { timeout: 60_000 });
}

for (const lang of ['en', 'de'] as const) {
	const words = WORDS[lang];

	test(`${lang}: an address alone saves, with the coordinates left empty`, async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await openProject(
			page,
			lang,
			`Coordinate notation ${lang} ${Date.now()}`
		);

		const site = page.locator('#lp-site');
		await site.getByLabel(words.address).fill('Triftstrasse 5');

		// Empty means "not provided": no error, no refused save.
		for (const label of [words.latitude, words.longitude]) {
			const field = site.getByLabel(label);
			await expect(field).toHaveValue('');
			await expect(field).toHaveAttribute('aria-invalid', 'false');
		}
		await expect(page.locator('#lp-site .lp-field-error')).toHaveCount(0);
		await expect(page.locator('.lp-save-state')).not.toContainText(
			lang === 'en' ? 'Input needs attention' : 'Eingabe prüfen'
		);

		const save = page.getByRole('button', { name: words.saveProject });
		await expect(save).toBeEnabled();
		await save.click();
		await expect(page.locator('.lp-save-state')).toContainText(
			words.saved,
			{
				timeout: 120_000,
			}
		);
	});

	test(`${lang}: a coordinate keeps its own notation whatever the interface language`, async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await openProject(page, lang, `Coordinate marks ${lang} ${Date.now()}`);

		const site = page.locator('#lp-site');
		await site.getByLabel(words.address).fill('Triftstrasse 5');

		const latitude = site.getByLabel(words.latitude);
		const longitude = site.getByLabel(words.longitude);
		// The point a map link carries, in both languages. This is the defect:
		// the German field used to refuse it as a format error and keep the
		// project unsaveable.
		await latitude.fill('48.1689');
		await longitude.fill('11.5844');
		await expect(latitude).toHaveAttribute('aria-invalid', 'false');
		await expect(page.locator('#lp-site .lp-field-error')).toHaveCount(0);

		const save = page.getByRole('button', { name: words.saveProject });
		await expect(save).toBeEnabled();
		await save.click();
		await expect(page.locator('.lp-save-state')).toContainText(
			words.saved,
			{
				timeout: 120_000,
			}
		);

		// The saved revision holds the number the mark denotes, not a shifted
		// one: reloading shows the value formatted for this interface.
		await page.reload({ waitUntil: 'networkidle' });
		await expect(site.getByLabel(words.latitude)).toHaveValue(
			lang === 'en' ? '48.1689' : '48,1689'
		);
		await expect(site.getByLabel(words.longitude)).toHaveValue(
			lang === 'en' ? '11.5844' : '11,5844'
		);

		// The field says which marks it reads, so the customer does not have to
		// discover the rule from a red message. Both coordinates carry it.
		await expect(
			page.locator('#lp-site .lp-field small', { hasText: words.format })
		).toHaveCount(2);

		// The reader's own mark reads the same value, and two marks in one value
		// stay refused rather than guessed at.
		await latitude.fill(lang === 'en' ? '48,1689' : '48.1689');
		await expect(latitude).toHaveAttribute('aria-invalid', 'false');
		await latitude.fill('1.234,5');
		await expect(latitude).toHaveAttribute('aria-invalid', 'true');
		await expect(page.locator('#lp-site .lp-field-error')).toHaveCount(1);
		await expect(
			page.getByRole('button', { name: words.saveProject })
		).toBeDisabled();
	});
}

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});
