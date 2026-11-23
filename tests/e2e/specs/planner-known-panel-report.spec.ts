import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { instance } from '../lib/instance';
import { launchHomepageConfigurator } from '../lib/home-configurator';
import { resumePlannerProject } from '../lib/resume-planner-project';

const labels = {
	en: {
		home: '/',
		enter: 'Enter project details',
		project: 'New project',
		title: 'Project name',
		town: 'Town or site',
		use: 'Site use',
		solar: 'Continue with solar',
		energy: 'Continue with energy use',
		phase: 'Grid connection',
		compare: 'Compare systems',
		choose: 'Use this configuration',
		review: 'Review the proposal',
		generate: 'Generate project report',
		pdf: 'Download PDF',
		preview: 'Preview report',
		close: 'Close',
		csv: 'Download bill of materials (CSV)',
		declared: 'Customer-entered panel data',
		unknown: 'Not defined for this calculation',
		generic: 'Generic PV module (reference only — not supplied by Linker)',
		question: 'How many solar panels did I enter in this saved report?',
		countAnswer: 'You entered 16 solar panels',
		unknownAnswer: 'The panel count is unknown',
		expand: 'Show full response',
		consent: 'Reject all',
	},
	de: {
		home: '/de/',
		enter: 'Projektdaten eingeben',
		project: 'Neues Projekt',
		title: 'Projektname',
		town: 'Ort oder Standort',
		use: 'Nutzung des Standorts',
		solar: 'Weiter zur PV-Anlage',
		energy: 'Weiter zum Energiebedarf',
		phase: 'Netzanschluss',
		compare: 'Systeme vergleichen',
		choose: 'Konfiguration übernehmen',
		review: 'Lösungsvorschlag prüfen',
		generate: 'Projektbericht erstellen',
		pdf: 'PDF herunterladen',
		preview: 'Berichtsvorschau',
		close: 'Schließen',
		csv: 'Stückliste herunterladen (CSV)',
		declared: 'Vom Kunden angegebene Moduldaten',
		unknown: 'Für diese Berechnung nicht definiert',
		generic:
			'Generisches PV-Modul (nur Referenz — nicht im Lieferumfang von Linker)',
		question:
			'Wie viele PV-Module habe ich in diesem gespeicherten Bericht angegeben?',
		countAnswer: 'haben Sie 16 PV-Module angegeben',
		unknownAnswer: 'Die Modulanzahl ist offen',
		expand: 'Vollständige Antwort anzeigen',
		consent: 'Alle ablehnen',
	},
};
const button = (root: Page | Locator, name: string) =>
	root.getByRole('button', { name, exact: true });
async function file(page: Page, control: Locator) {
	const pending = page.waitForEvent('download');
	await control.click();
	const path = await (await pending).path();
	expect(path).toBeTruthy();
	return readFileSync(path!);
}
for (const lang of ['en', 'de'] as const)
	for (const width of [1440, 390])
		for (const variant of ['count', 'power', 'both'] as const) {
			test(`${lang} ${width}: known ${variant} from homepage to report, materials CSV and Genie`, async ({
				page,
			}) => {
				const url = instance().url;
				expect(new URL(url).hostname).toBe('127.0.0.1');
				await page.setViewportSize({
					width,
					height: width === 390 ? 844 : 900,
				});
				const t = labels[lang];
				const count = variant === 'power' ? null : 16,
					watts = variant === 'count' ? null : 430;
				const panelLabel =
					watts === null
						? t.generic
						: lang === 'de'
							? `Generisches ${watts}-W-PV-Modul (nur Referenz — nicht im Lieferumfang von Linker)`
							: `Generic ${watts} W PV module (reference only — not supplied by Linker)`;
				const workspace = page.locator('[data-linker-planner]');
				await page.goto(url + t.home);
				const consent = button(page, t.consent);
				if (await consent.isVisible()) await consent.click();
				const project = await launchHomepageConfigurator(page, lang);
				await project
					.getByLabel(t.title)
					.fill('Berlin panel declaration');
				await project
					.locator('select[name=country]')
					.selectOption('DE');
				await project.getByLabel(t.town).fill('Berlin');
				await project.getByLabel(t.use).selectOption('residential');
				await project
					.locator('select[name=system_scope]')
					.selectOption('pv_only');
				await project
					.locator('select[name=project_purpose]')
					.selectOption('self');
				await button(project, t.compare).click();
				await expect(page).toHaveURL(/[?&]project=[a-f0-9]{32}/);
				await resumePlannerProject(
					page,
					lang,
					'Berlin panel declaration',
					'roof'
				);
				if (count !== null)
					await workspace
						.locator('input[name=known_panel_count]')
						.fill(String(count));
				if (watts !== null)
					await workspace
						.locator('input[name=known_panel_power_w]')
						.fill(String(watts));
				await button(workspace, t.energy).click();
				await workspace.getByLabel(t.phase).selectOption('3');
				const pending = page.waitForResponse(
					(r) =>
						r.request().method() === 'POST' &&
						new URL(r.url()).pathname.endsWith(
							'/runs/find-equipment'
						)
				);
				await button(workspace, t.compare).click();
				const response = await pending;
				expect(response.status()).toBe(200);
				const inputs = response.request().postDataJSON().inputs;
				expect(inputs.known_panel_details).toMatchObject({
					count,
					power_w: watts,
				});
				expect(inputs.geometry?.arrays ?? []).toHaveLength(0);
				await button(workspace, t.choose)
					.first()
					.click({ timeout: 120_000 });
				await button(workspace, t.review).click();
				await expect(button(workspace, t.generate)).toHaveCount(0);
				await expect(
					workspace.locator('.sc-export-strip')
				).toBeVisible();
				await expect(
					workspace.locator('form.linker-inquiry-form')
				).toBeVisible();
				const csvButton = button(workspace, t.csv);
				await expect(csvButton).toBeEnabled({ timeout: 120_000 });
				const csv = await file(page, csvButton);
				const rows = JSON.parse(
					execFileSync(
						'python3',
						[
							'-c',
							'import csv,sys,json; print(json.dumps(list(csv.reader(sys.stdin))))',
						],
						{ input: csv, encoding: 'utf8' }
					)
				) as string[][];
				expect(csv.toString('utf8')).not.toMatch(
					/Trina|TSM[-_ ]?460|Vertex[- ]?S/i
				);
				const declaredRecords = rows.filter((row) =>
					row[6]?.includes('project_declared_panel_parameters')
				);
				expect(declaredRecords).toHaveLength(1);
				expect(declaredRecords[0]!.at(-1)).toBe(t.declared);
				const panels = rows.filter((row) => row.at(-1) === t.declared);
				expect(panels).toHaveLength(1);
				expect(panels[0]!.slice(2, 6)).toEqual([
					count === null ? '' : '16',
					panelLabel,
					'',
					t.declared,
				]);
				const pdf = await file(page, button(workspace, t.pdf));
				const document = execFileSync(
					'pdftotext',
					['-layout', '-', '-'],
					{ input: pdf, encoding: 'utf8' }
				);
				expect(document).not.toMatch(
					/Trina|TSM[-_ ]?460|Vertex[- ]?S/i
				);
				const start = document.indexOf(t.declared);
				expect(start).toBeGreaterThan(-1);
				const section = document
					.slice(start, start + 550)
					.replace(/\s+/g, ' ');
				expect(section).toContain(t.declared);
				expect(section).toContain(panelLabel);
				expect(section).toContain(count === null ? t.unknown : '16');
				await button(workspace, t.preview).click();
				const dialog = page.getByRole('dialog');
				const table = dialog
					.getByRole('region', { name: t.declared, exact: true })
					.getByRole('table');
				await table.scrollIntoViewIfNeeded();
				await expect(table.getByRole('cell')).toContainText([
					new RegExp((count === null ? t.unknown : '16') + '$'),
					panelLabel,
				]);
				if (variant === 'both')
					await page.screenshot({
						path: test.info().outputPath('known-panel-report.png'),
					});
				await button(dialog, t.close).click();
				await workspace
					.locator('#sc-review [data-linker-genie-planning]')
					.click();
				const panel = page.locator('.linker-genie-app__panel');
				await panel
					.locator('.linker-genie-app__input')
					.fill(t.question);
				const votes = panel.locator('.linker-genie-app__votes');
				const previous = await votes.count();
				await panel.locator('.linker-genie-app__send').click();
				await expect
					.poll(() => votes.count(), { timeout: 120_000 })
					.toBeGreaterThan(previous);
				const expand = button(panel, t.expand);
				if (await expand.isVisible()) await expand.click();
				await expect(
					panel.locator('.linker-genie-message-body').last()
				).toContainText(
					count === null ? t.unknownAnswer : t.countAnswer
				);
				if (variant === 'both')
					await panel.screenshot({
						path: test.info().outputPath('known-panel-genie.png'),
					});
			});
		}
