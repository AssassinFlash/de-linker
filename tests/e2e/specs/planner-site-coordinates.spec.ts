import { expect, test } from '@playwright/test';
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';
import {
	compareProject,
	deleteOpenProject,
	fillSolarProject,
	plannerWords,
	reopenProject,
} from '../lib/planner-entry';

const words = {
	en: {
		path: '/solution-configurator/',
		address: 'Town or site',
		estimate: 'Solar generation estimate',
		latitude: 'Latitude',
		longitude: 'Longitude',
		format: 'Decimal point or comma; no thousands separators.',
	},
	de: {
		path: '/de/loesungskonfigurator/',
		address: 'Ort oder Standort',
		estimate: 'Geschätzte PV-Erzeugung',
		latitude: 'Breitengrad',
		longitude: 'Längengrad',
		format: 'Dezimalpunkt oder Dezimalkomma; keine Tausendertrennzeichen.',
	},
};

for (const lang of ['en', 'de'] as const) {
	test.describe(`${lang} site coordinates`, () => {
		test.use({ locale: lang === 'en' ? 'en-US' : 'de-DE' });
		const labels = words[lang];
		test.beforeEach(async ({ context, page }) => {
			await seedConsentCookies(context);
			await page.goto(instance().url + labels.path);
		});

		test('an address alone carries through comparison and reopening', async ({
			page,
		}) => {
			const title = `Address only ${lang} ${Date.now()}`;
			await fillSolarProject(page, lang, title);
			await page.getByLabel(labels.address).fill('Triftstrasse 5');
			await compareProject(page, lang);
			const { inputs } = await reopenProject(page, lang, title);
			expect(inputs.brief.site).toMatchObject({
				location_label: 'Triftstrasse 5',
				latitude: null,
				longitude: null,
			});
			await expect(page.getByLabel(labels.address)).toHaveValue(
				'Triftstrasse 5'
			);
			await page
				.getByText(plannerWords[lang].roof, { exact: true })
				.click();
			await page.getByText(labels.estimate, { exact: true }).click();
			await expect(
				page.getByLabel(labels.latitude, { exact: true })
			).toHaveValue('');
			await expect(
				page.getByLabel(labels.longitude, { exact: true })
			).toHaveValue('');
			await deleteOpenProject(page, lang, title);
		});

		test('point and comma coordinates retain their values and mixed separators are refused', async ({
			page,
		}) => {
			const title = `Coordinate notation ${lang} ${Date.now()}`;
			await fillSolarProject(page, lang, title);
			await page.getByLabel(labels.address).fill('Triftstrasse 5');
			await page
				.getByText(plannerWords[lang].roof, { exact: true })
				.click();
			await page.getByText(labels.estimate, { exact: true }).click();
			const latitude = page.getByLabel(labels.latitude, { exact: true });
			const longitude = page.getByLabel(labels.longitude, {
				exact: true,
			});
			await latitude.pressSequentially('48.1689');
			await longitude.pressSequentially('11,5844');
			await compareProject(page, lang);
			const { inputs } = await reopenProject(page, lang, title);
			expect(inputs.brief.site).toMatchObject({
				latitude: 48.1689,
				longitude: 11.5844,
			});
			await page
				.getByText(plannerWords[lang].roof, { exact: true })
				.click();
			await page.getByText(labels.estimate, { exact: true }).click();
			await expect(latitude).toHaveValue(
				lang === 'de' ? '48,1689' : '48.1689'
			);
			await expect(longitude).toHaveValue(
				lang === 'de' ? '11,5844' : '11.5844'
			);
			await expect(
				page.getByText(labels.format, { exact: true })
			).toHaveCount(2);
			await latitude.fill('');
			await latitude.pressSequentially('1.234,5');
			await expect(latitude).toHaveAttribute('aria-invalid', 'true');
			await expect(
				page.getByRole('button', { name: plannerWords[lang].compare })
			).toBeDisabled();
		});
	});
}
