import { expect, test, type Locator, type Page } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { seedConsentCookies } from '../lib/consent';
import {
	startSolarProject,
	removeSiteProject,
	type SiteLanguage,
} from '../lib/configurator-site';

const words = {
	en: {
		solar: /Solar$/,
		energy: /Energy use$/,
		purpose: 'Purpose',
		grid: 'Grid connection',
		import: 'Import CSV',
		zone: 'Time zone',
		file: 'CSV file',
		delimiter: 'Column delimiter',
		inspect: 'Read CSV columns',
		time: 'Timestamp column',
		load: 'Consumption column',
		unit: 'Values represent',
		position: 'Timestamp marks',
		interval: 'Interval length',
		decimal: 'Decimal separator',
		origin: 'Data source',
		source: 'Source name',
		rights: 'Source and permission to store privately',
		apply: 'Use CSV consumption',
		compare: 'Compare systems',
		format: 'Decimal point or comma',
	},
	de: {
		solar: /Photovoltaik$/,
		energy: /Strombedarf$/,
		purpose: 'Ziel',
		grid: 'Netzanschluss',
		import: 'CSV importieren',
		zone: 'Zeitzone',
		file: 'CSV-Datei',
		delimiter: 'Spaltentrennzeichen',
		inspect: 'CSV-Spalten einlesen',
		time: 'Zeitstempelspalte',
		load: 'Verbrauchsspalte',
		unit: 'Einheit der Messwerte',
		position: 'Zeitstempel kennzeichnet',
		interval: 'Intervalllänge',
		decimal: 'Dezimaltrennzeichen',
		origin: 'Datenquelle',
		source: 'Name der Quelle',
		rights: 'Quelle und Erlaubnis zur privaten Speicherung',
		apply: 'Verbrauchsdaten übernehmen',
		compare: 'Systeme vergleichen',
		format: 'Dezimalpunkt oder Dezimalkomma',
	},
} as const;
const file = fileURLToPath(
	new URL('../fixtures/cossmic-konstanz-load-2017-06-19.csv', import.meta.url)
);

async function importMeterReadings(
	page: Page,
	panel: Locator,
	lang: SiteLanguage
) {
	const text = words[lang];
	await panel.getByRole('button', { name: text.import, exact: true }).click();
	await panel.getByLabel(text.zone, { exact: true }).fill('UTC');
	await panel.getByLabel(text.file, { exact: true }).setInputFiles(file);
	await panel.getByLabel(text.delimiter, { exact: true }).selectOption(';');
	await panel.getByRole('button', { name: text.inspect }).click();
	await panel.getByLabel(text.time, { exact: true }).selectOption('Time');
	await panel.getByLabel(text.load, { exact: true }).selectOption('Load');
	await panel
		.getByLabel(text.unit, { exact: true })
		.selectOption('interval_energy_kwh');
	await panel
		.getByLabel(text.position, { exact: true })
		.selectOption('start');
	await panel.getByLabel(text.interval).fill('60');
	await panel.getByLabel(text.decimal, { exact: true }).selectOption('.');
	await panel
		.getByLabel(text.origin, { exact: true })
		.selectOption('measured');
	await panel
		.getByLabel(text.source, { exact: true })
		.fill('CoSSMic Konstanz');
	await panel
		.getByLabel(text.rights, { exact: true })
		.fill('Open Power System Data, Household Data 2020-04-15, CC BY 4.0.');
	const result = page.waitForResponse((r) =>
		new URL(r.url()).pathname.endsWith('/profiles/preview')
	);
	await panel.getByRole('button', { name: text.apply, exact: true }).click();
	const response = await result;
	expect(response.ok()).toBe(true);
	const preview = response.request().postDataJSON();
	await expect(panel.locator('figure svg')).toBeVisible();
	return preview.asset_id;
}

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});
for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${lang} ${width}: site coordinates can be corrected independently of an imported meter file`, async ({
			page,
		}) => {
			test.setTimeout(150_000);
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			const text = words[lang];
			const title = `Konstanz meter ${lang} ${width}`;
			const created = page.waitForResponse((r) =>
				new URL(r.url()).pathname.endsWith('/projects/create')
			);
			const workspace = await startSolarProject(page, lang, title);
			const creation = await created;
			expect(creation.ok()).toBe(true);
			const initial = creation.request().postDataJSON();
			const projectId = new URL(page.url()).searchParams.get('project');
			expect(initial.inputs.brief.site).toMatchObject({
				location_label: title,
				latitude: null,
				longitude: null,
			});
			const nav = workspace.getByRole('navigation');
			const site = workspace
				.locator('details')
				.filter({ has: page.locator('input[name="latitude"]') });
			await site.locator('summary').click();
			const latitude = site.locator('input[name="latitude"]'),
				longitude = site.locator('input[name="longitude"]');
			await expect(latitude).toHaveValue('');
			await expect(longitude).toHaveValue('');
			await longitude.fill('9,1732');
			await latitude.fill('1.234,5');
			await expect(latitude).toHaveAttribute('aria-invalid', 'true');
			await expect(latitude).toHaveAccessibleDescription(
				new RegExp(text.format)
			);
			await nav.getByRole('button', { name: text.energy }).click();
			const panel = workspace.locator('.sc-energy-demand');
			await panel
				.getByLabel(text.purpose, { exact: true })
				.selectOption('self');
			await panel
				.getByLabel(text.grid, { exact: true })
				.selectOption('3');
			const asset = await importMeterReadings(page, panel, lang);
			await expect(
				panel.getByRole('button', { name: text.compare, exact: true })
			).toBeDisabled();
			await nav.getByRole('button', { name: text.solar }).click();
			await expect(latitude).toHaveValue('1.234,5');
			await expect(longitude).toHaveValue('9,1732');
			await latitude.fill('47.6636');
			await expect(latitude).toHaveAttribute('aria-invalid', 'false');
			await nav.getByRole('button', { name: text.energy }).click();
			await expect(panel.locator('figure svg')).toBeVisible();
			await panel
				.getByRole('heading', {
					name:
						lang === 'de'
							? 'Stromverbrauch im Zeitverlauf'
							: 'Electricity use over time',
				})
				.scrollIntoViewIfNeeded();
			await page.screenshot({
				path: test.info().outputPath('meter-profile.png'),
				animations: 'disabled',
			});
			const saved = page.waitForResponse(
				(r) =>
					new URL(r.url()).pathname.endsWith(
						'/runs/find-equipment'
					) &&
					r.request().postDataJSON()?.inputs?.profile_selections
						?.selected?.gross_load === asset
			);
			await panel
				.getByRole('button', { name: text.compare, exact: true })
				.click();
			const comparison = await saved;
			expect(comparison.ok()).toBe(true);
			const project = comparison.request().postDataJSON();
			expect(project.project_id).toBe(projectId);
			expect(project.inputs.brief.site).toMatchObject({
				latitude: 47.6636,
				longitude: 9.1732,
			});
			expect(project.inputs.profile_selections.selected.gross_load).toBe(
				asset
			);
			await removeSiteProject(page, lang, title);
		});
	}
}
