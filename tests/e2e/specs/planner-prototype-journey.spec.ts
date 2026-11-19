import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

const labels = {
	en: {
		path: '/solution-configurator/',
		start: 'New project',
		title: 'Project name',
		town: 'Town or site',
		use: 'Site use',
		existing: 'There is an existing system',
		existingName: 'Existing system name',
		existingPower: 'Existing inverter power (kW)',
		keep: 'Keep the existing inverter',
		solar: 'Continue with solar',
		energy: 'Continue with energy use',
		grid: 'Grid connection',
		backup: 'Backup load',
		duration: 'Required duration',
		compare: 'Compare systems',
		review: 'Review the proposal',
		report: 'Generate project report',
		preview: 'Preview report',
		download: 'Download PDF',
		navigation: 'Project navigation',
	},
	de: {
		path: '/de/loesungskonfigurator/',
		start: 'Neues Projekt',
		title: 'Projektname',
		town: 'Ort oder Standort',
		use: 'Nutzung des Standorts',
		existing: 'Eine Anlage ist bereits vorhanden',
		existingName: 'Bezeichnung der vorhandenen Anlage',
		existingPower: 'Leistung des vorhandenen Wechselrichters (kW)',
		keep: 'Vorhandenen Wechselrichter beibehalten',
		solar: 'Weiter zur PV-Anlage',
		energy: 'Weiter zum Energiebedarf',
		grid: 'Netzanschluss',
		backup: 'Ersatzstromlast',
		duration: 'Gewünschte Dauer',
		compare: 'Systeme vergleichen',
		review: 'Lösungsvorschlag prüfen',
		report: 'Projektbericht erstellen',
		preview: 'Berichtsvorschau',
		download: 'PDF herunterladen',
		navigation: 'Projektnavigation',
	},
} as const;

async function screen(page: Page, name: string) {
	await page.evaluate(() => document.fonts.ready.then(() => undefined));
	const path = test.info().outputPath(name + '.png');
	await page.screenshot({ path, animations: 'disabled' });
}

for (const lang of ['en', 'de'] as const) {
	for (const width of [390, 1440]) {
		test(`${lang} ${width}: an existing system reaches a usable report in the project workspace`, async ({
			page,
			context,
		}) => {
			test.setTimeout(300_000);
			const words = labels[lang];
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await seedConsentCookies(context);
			const title = `Berlin ${lang.toUpperCase()} ${width}`;
			await page.goto(instance().url + words.path);
			const workspace = page.locator('[data-linker-planner]');
			const start = workspace.getByRole('form', { name: words.start });
			await start.getByLabel(words.title).fill(title);
			await start.locator('select[name=country]').selectOption('DE');
			await start.getByLabel(words.town).fill('Berlin');
			await start
				.locator('select[name=system_scope]')
				.selectOption('storage_addition');
			await start.getByLabel(words.use).selectOption('residential');
			await start
				.locator('select[name=project_purpose]')
				.selectOption('backup');
			await start.getByLabel(words.existing).check();
			await start
				.getByLabel(words.existingName)
				.fill('Workshop inverter');
			await start.getByLabel(words.existingPower).fill('7.5');
			await start.getByLabel(words.keep).check();
			await screen(page, 'project-intake');

			await start.getByRole('button', { name: words.solar }).click();
			const navigation = workspace.getByRole('navigation', {
				name: words.navigation,
			});
			const next = workspace.getByRole('button', {
				name: words.energy,
				exact: true,
			});
			await expect(next).toBeVisible();
			await expect(navigation).toBeVisible();
			await expect(page).toHaveURL(/[?&]project=[a-f0-9]{32}/);
			const project = new URL(page.url()).searchParams.get('project');
			await screen(page, 'solar');

			await next.click();
			await workspace.getByLabel(words.grid).selectOption('3');
			await workspace.getByLabel(words.backup).fill('3');
			await workspace.getByLabel(words.duration).fill('2');
			await screen(page, 'energy');

			await workspace
				.getByRole('button', { name: words.compare })
				.click();
			await expect(
				workspace.getByRole('heading', { name: words.keep })
			).toBeVisible({
				timeout: 90_000,
			});
			const review = workspace.getByRole('button', {
				name: words.review,
			});
			await expect(review).toBeEnabled();
			await screen(page, 'system');

			await review.click();
			await workspace.getByRole('button', { name: words.report }).click();
			const preview = workspace.getByRole('button', {
				name: words.preview,
				exact: true,
			});
			await expect(preview).toBeVisible({ timeout: 90_000 });
			await screen(page, 'report-and-inquiry');
			await preview.click();
			await expect(workspace.getByRole('dialog')).toBeVisible();
			await screen(page, 'report-preview');
			await page.keyboard.press('Escape');

			const file = page.waitForEvent('download');
			await workspace
				.getByRole('button', { name: words.download, exact: true })
				.click();
			const path = await (await file).path();
			expect(path).toBeTruthy();
			expect(readFileSync(path!).subarray(0, 5).toString()).toBe('%PDF-');
			expect(new URL(page.url()).searchParams.get('project')).toBe(
				project
			);
			expect(
				await page.evaluate(() => document.documentElement.scrollWidth)
			).toBe(width);
		});
	}
}
