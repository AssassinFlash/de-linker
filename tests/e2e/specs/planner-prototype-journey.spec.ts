import { resumePlannerProject } from '../lib/resume-planner-project';
import { expect, test, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

const labels = {
	en: {
		roofChoice: 'Place modules on the roof',
		openRoof: 'Open roof layout',
		measuredRoof: 'Add a measured roof face',
		addRoof: 'Add rectangular roof',
		drawing: 'Drawing source',
		roofHeight: 'Selected roof height',
		useLayout: 'Use this layout',
		knownModules: 'Use module details',
		home: '/',
		enterDetails: 'Enter project details',
		start: 'Compare project options',
		title: 'Project name',
		town: 'Town or site',
		use: 'Site use',
		existing: 'There is an existing system',
		existingName: 'Existing system name',
		existingPower: 'Existing inverter power (kW)',
		keep: 'Keep the existing inverter',
		energy: 'Continue with energy use',
		grid: 'Grid connection',
		backup: 'Backup load',
		duration: 'Required duration',
		compare: 'Compare systems',
		review: 'Review the proposal',
		report: 'Generate project report',
		preview: 'Preview report',
		download: 'Download PDF',
		materials: 'Download bill of materials (CSV)',
		removeLogo: 'Remove logo',
		updateReport: 'Update project report',
		history: 'Calculation history',
		logo: 'Your logo on the PDF (optional)',
		openPdf: 'Open report PDF',
		navigation: 'Project navigation',
		projectChapter: /^(?:1\s*)?Project$/,
		projectSection: 'What is the project?',
		solarChapter: /^(?:2\s*)?Solar$/,
	},
	de: {
		roofChoice: 'Module auf dem Dach platzieren',
		openRoof: 'Dachbelegung öffnen',
		measuredRoof: 'Dachfläche nach Aufmaß hinzufügen',
		addRoof: 'Rechteckige Dachfläche hinzufügen',
		drawing: 'Grundlage der Zeichnung',
		roofHeight: 'Höhe der gewählten Dachfläche',
		useLayout: 'Belegung übernehmen',
		knownModules: 'Moduldaten verwenden',
		home: '/de/',
		enterDetails: 'Projektdaten eingeben',
		start: 'Projektoptionen vergleichen',
		title: 'Projektname',
		town: 'Ort oder Standort',
		use: 'Nutzung des Standorts',
		existing: 'Eine Anlage ist bereits vorhanden',
		existingName: 'Bezeichnung der vorhandenen Anlage',
		existingPower: 'Leistung des vorhandenen Wechselrichters (kW)',
		keep: 'Vorhandenen Wechselrichter beibehalten',
		energy: 'Weiter zum Energiebedarf',
		grid: 'Netzanschluss',
		backup: 'Ersatzstromlast',
		duration: 'Gewünschte Dauer',
		compare: 'Systeme vergleichen',
		review: 'Lösungsvorschlag prüfen',
		report: 'Projektbericht erstellen',
		preview: 'Berichtsvorschau',
		download: 'PDF herunterladen',
		materials: 'Stückliste herunterladen (CSV)',
		removeLogo: 'Logo entfernen',
		updateReport: 'Projektbericht aktualisieren',
		history: 'Bisherige Berechnungen',
		logo: 'Ihr Logo im PDF (optional)',
		openPdf: 'Berichts-PDF öffnen',
		navigation: 'Projektnavigation',
		projectChapter: /^(?:1\s*)?Projekt$/,
		projectSection: 'Was planen Sie?',
		solarChapter: /^(?:2\s*)?Photovoltaik$/,
	},
} as const;

async function screen(page: Page, name: string) {
	await page.evaluate(() => document.fonts.ready.then(() => undefined));
	const path = test.info().outputPath(name + '.png');
	await page.screenshot({ path, animations: 'disabled' });
}

async function importLoadProfile(energy: ReturnType<Page['locator']>) {
	const intervals = Array.from({ length: 96 }, (_, index) => {
		const time = new Date(Date.UTC(2026, 0, 20, 0, index * 15));
		return `${time.toISOString()};${index === 40 ? 8 : 2}`;
	});
	await energy
		.getByRole('button', { name: 'CSV importieren', exact: true })
		.click();
	await energy.getByLabel('Zeitzone').fill('UTC');
	await energy.getByLabel('CSV-Datei').setInputFiles({
		name: 'privater-lastgang.csv',
		mimeType: 'text/csv',
		buffer: Buffer.from(['Zeit;Last', ...intervals].join('\n')),
	});
	await energy.getByLabel('Spaltentrennzeichen').selectOption(';');
	await energy.getByRole('button', { name: 'CSV-Spalten einlesen' }).click();
	await energy.getByLabel('Zeitstempelspalte').selectOption('Zeit');
	await energy.getByLabel('Verbrauchsspalte').selectOption('Last');
	await energy
		.getByLabel('Einheit der Messwerte')
		.selectOption('interval_average_kw');
	await energy.getByLabel('Zeitstempel kennzeichnet').selectOption('start');
	await energy.getByLabel('Intervalllänge').fill('15');
	await energy.getByLabel('Dezimaltrennzeichen').selectOption('.');
	await energy.getByLabel('Datenquelle').selectOption('synthetic');
	await energy
		.getByLabel('Quelle und Erlaubnis zur privaten Speicherung')
		.fill(
			'Ein synthetischer Testlastgang für den privaten Projektentwurf.'
		);
	await energy
		.getByRole('button', { name: 'Verbrauchsdaten übernehmen' })
		.click();
	await expect(energy.locator('.sc-demand-profile')).toContainText(
		'49,5 kWh'
	);
	await expect(energy.locator('figure svg')).toBeVisible();
}

async function adjustRoof(
	page: Page,
	workspace: ReturnType<Page['locator']>,
	lang: keyof typeof labels
) {
	const words = labels[lang];
	await workspace
		.getByRole('button', { name: words.roofChoice, exact: true })
		.click();
	await workspace
		.getByRole('button', { name: words.openRoof, exact: true })
		.click();
	await expect(
		workspace.locator('.sc-roof-props details[open] summary')
	).toHaveText(words.measuredRoof);
	const roof = workspace.locator('.sc-roof-props details[open]');
	const dimensions =
		lang === 'en'
			? [
					'Width',
					'Depth',
					'Pitch',
					'Azimuth',
					'Relative roof height',
					'Origin east / U',
					'Origin north / V',
				]
			: [
					'Breite',
					'Tiefe',
					'Dachneigung',
					'Azimut',
					'Relative Dachhöhe',
					'Ursprung in Ostrichtung (U)',
					'Ursprung in Nordrichtung (V)',
				];
	for (const [index, value] of [
		'8',
		'5',
		'25',
		'180',
		'3',
		'0',
		'0',
	].entries())
		await roof.getByLabel(dimensions[index]!).fill(value);
	await roof
		.getByLabel(words.drawing)
		.fill('Test drawing for the review site');
	await roof.getByRole('checkbox').check();
	await roof.getByRole('button', { name: words.addRoof }).click();
	const height = workspace.getByLabel(words.roofHeight);
	await expect(height).toHaveValue('3');
	await height.fill('4');
	await height.press('Tab');
	await expect(height).toHaveValue('4');
	await screen(page, 'roof-layout');
	await workspace.getByRole('button', { name: words.useLayout }).click();
	await workspace.getByRole('button', { name: words.openRoof }).click();
	await expect(height).toHaveValue('4');
	await workspace.getByRole('button', { name: words.useLayout }).click();
	await workspace
		.getByRole('button', { name: words.knownModules, exact: true })
		.click();
}

const testLogo = Buffer.from(
	'iVBORw0KGgoAAAANSUhEUgAAAAwAAAAICAIAAABChommAAAAFElEQVQY02NUjnRmIASYCKoY9ooA5aIAz5+XSsIAAAAASUVORK5CYII=',
	'base64'
);

for (const lang of ['en', 'de'] as const) {
	for (const width of [390, 1440]) {
		test(`${lang} ${width}: an existing system reaches a usable report in the project workspace`, async ({
			page,
			context,
		}) => {
			test.setTimeout(300_000);
			page.setDefaultTimeout(20_000);
			const words = labels[lang];
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await seedConsentCookies(context);
			const title = `Berlin ${lang.toUpperCase()} ${width}`;
			await page.goto(instance().url + words.home);
			await page
				.locator('[data-linker-planner-entry="home-hero"] a')
				.click();
			const workspace = page.locator('[data-linker-planner]');
			const details = workspace.getByRole('button', {
				name: words.enterDetails,
				exact: true,
			});
			await expect(details).toBeInViewport();
			await screen(page, 'known-project-entry');
			await details.click();
			await expect(page).toHaveURL(/#sc-project$/);
			const start = workspace.getByRole('form', { name: words.start });
			await expect(
				start.getByRole('heading', { name: words.projectSection })
			).toBeFocused();
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

			await start
				.getByRole('button', { name: words.compare, exact: true })
				.click();
			await expect(page).toHaveURL(/[?&]project=[a-f0-9]{32}/);
			const navigation = await resumePlannerProject(page, lang, title);
			await navigation
				.getByRole('button', { name: words.solarChapter })
				.click();
			const next = workspace.getByRole('button', {
				name: words.energy,
				exact: true,
			});
			await expect(next).toBeVisible();
			await expect(navigation).toBeVisible();
			await expect(page).toHaveURL(/[?&]project=[a-f0-9]{32}/);
			const project = new URL(page.url()).searchParams.get('project');
			await navigation
				.getByRole('button', { name: words.projectChapter })
				.click();
			await expect(
				workspace.getByRole('heading', { name: words.projectSection })
			).toBeVisible();
			await screen(page, 'project');
			await navigation
				.getByRole('button', { name: words.solarChapter })
				.click();
			await expect(next).toBeVisible();
			await screen(page, 'solar');

			await next.click();
			await workspace.getByLabel(words.grid).selectOption('3');
			await workspace.getByLabel(words.backup).fill('3');
			await workspace.getByLabel(words.duration).fill('2');
			if (lang === 'de' && width === 390)
				await importLoadProfile(workspace.locator('.sc-energy-demand'));
			await page.evaluate(() =>
				window.scrollTo({ top: 0, behavior: 'instant' })
			);
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
			await page.evaluate(() =>
				window.scrollTo({ top: 0, behavior: 'instant' })
			);
			await screen(page, 'system');

			await review.click();
			await workspace.getByLabel(words.logo).setInputFiles({
				name: 'test-logo.png',
				mimeType: 'image/png',
				buffer: testLogo,
			});
			await workspace.getByRole('button', { name: words.report }).click();
			const preview = workspace.getByRole('button', {
				name: words.preview,
				exact: true,
			});
			await expect(preview).toBeVisible({ timeout: 90_000 });
			await page.evaluate(() =>
				window.scrollTo({ top: 0, behavior: 'instant' })
			);
			await screen(page, 'report-and-inquiry');
			await preview.scrollIntoViewIfNeeded();
			await screen(page, 'report-files');
			await preview.click();
			const dialog = workspace.getByRole('dialog');
			await expect(dialog).toBeVisible();
			const frame = await dialog.boundingBox();
			expect(frame!.x).toBeCloseTo((width - frame!.width) / 2, 0);
			const originalPdf = dialog.getByRole('link', {
				name: words.openPdf,
			});
			await expect(originalPdf).toBeVisible();
			expect(await originalPdf.getAttribute('href')).toMatch(/^blob:/);
			const originalBytes = await originalPdf.evaluate(
				async (link: HTMLAnchorElement) =>
					Array.from(
						new Uint8Array(
							await (await fetch(link.href)).arrayBuffer()
						)
					)
			);
			await screen(page, 'report-preview');
			await page.keyboard.press('Escape');

			const file = page.waitForEvent('download');
			await workspace
				.getByRole('button', { name: words.download, exact: true })
				.click();
			const pdf = await file;
			const basename = pdf.suggestedFilename().replace(/\.pdf$/, '');
			const version = basename.match(
				new RegExp(`^linker-planning-${project}-r([0-9]+)-${lang}$`)
			);
			expect(version).toBeTruthy();
			const revision = version![1];
			const pdfPath = test.info().outputPath('report.pdf');
			await pdf.saveAs(pdfPath);
			const downloaded = readFileSync(pdfPath);
			expect(downloaded.subarray(0, 5).toString()).toBe('%PDF-');
			expect(downloaded.equals(Buffer.from(originalBytes))).toBe(true);
			const text = execFileSync('pdftotext', ['-layout', pdfPath, '-'], {
				encoding: 'utf8',
			});
			expect(text).toContain(title);
			expect(text).toContain(project);
			expect(text).toMatch(
				new RegExp(
					`(?:Input revision|Eingabeversion)\\s+${revision}\\b`
				)
			);
			const images = execFileSync('pdfimages', ['-list', pdfPath], {
				encoding: 'utf8',
			});
			expect(images).toMatch(/^\s*1\s+\d+\s+image\s+12\s+8\s+rgb\b/m);

			const materialFile = page.waitForEvent('download');
			await workspace
				.getByRole('button', { name: words.materials, exact: true })
				.click();
			const csv = await materialFile;
			expect(csv.suggestedFilename()).toBe(basename + '.csv');
			const csvPath = test.info().outputPath('materials.csv');
			await csv.saveAs(csvPath);
			const rows = readFileSync(csvPath, 'utf8')
				.trim()
				.split(/\r?\n/)
				.slice(1);
			expect(rows.length).toBeGreaterThan(0);
			for (const row of rows)
				expect(row.startsWith(`${project},${revision},`)).toBe(true);
			expect(new URL(page.url()).searchParams.get('project')).toBe(
				project
			);
			expect(
				await page.evaluate(() => document.documentElement.scrollWidth)
			).toBe(width);
			await workspace
				.getByRole('button', { name: words.removeLogo, exact: true })
				.click();
			await workspace
				.getByRole('button', { name: words.updateReport, exact: true })
				.click();
			const history = workspace.getByRole('region', {
				name: words.history,
				exact: true,
			});
			const earlier = history.getByRole('button', {
				name: new RegExp(`^(?:Revision|Version) ${revision}\\b`),
			});
			await earlier.click({ timeout: 90_000 });
			await expect(page).toHaveURL(/[?&]run=[a-f0-9]{32}/);
			await page.reload();
			const historicalFile = page.waitForEvent('download');
			await history
				.getByRole('button', { name: words.download, exact: true })
				.click();
			const historicalPdf = await historicalFile;
			expect(historicalPdf.suggestedFilename()).toBe(
				pdf.suggestedFilename()
			);
			expect(readFileSync((await historicalPdf.path())!)).toEqual(
				downloaded
			);
			await navigation
				.getByRole('button', { name: words.solarChapter })
				.click();
			await adjustRoof(page, workspace, lang);
		});
	}
}
