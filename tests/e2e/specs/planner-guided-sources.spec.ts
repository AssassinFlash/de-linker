import {
	launchHomepageConfigurator,
	compareSavedFromHome,
} from '../lib/home-configurator';
import { resumePlannerProject } from '../lib/resume-planner-project';
import { readFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { instance, isolateMailBudgets, wp } from '../lib/instance';

const words = {
	en: {
		home: '/',
		intake: 'Compare project options',
		title: 'Project name',
		town: 'Town or site',
		use: 'Site use',
		phase: 'Grid connection',
		saved: 'Saved projects',
		compare: 'Compare systems',
		choose: 'Use this configuration',
		send: 'Send inquiry',
		received: 'Inquiry received',
		report: 'Download PDF',
		enter: 'Enter project details',
		newProject: 'New project',
		solar: 'Continue with solar',
		energy: 'Continue with energy use',
		roofChoice: 'Place modules on the roof',
		module: 'PV module',
		openRoof: 'Open roof layout',
		planView: 'Plan view',
		dimensions: [
			'Width',
			'Depth',
			'Pitch',
			'Azimuth',
			'Relative roof height',
			'Origin east / U',
			'Origin north / V',
		],
		drawing: 'Drawing source',
		addRoof: 'Add rectangular roof',
		rows: 'Rows',
		columns: 'Columns',
		gap: 'Module gap',
		place: 'Place module group',
		useLayout: 'Use this layout',
		properties: 'Source properties',
		export: 'Permission to export geometry',
		timestamp: 'Timestamp column',
		value: 'Value column',
		unit: 'Value meaning and unit',
		decimal: 'Decimal separator in the file',
		boundaries: 'Interval boundaries',
		timeRole: 'The timestamp identifies…',
		interval: 'Interval duration',
		zone: 'Source time zone',
		profile: 'Your demand profile',
		peakBeforeStorage: '7.83 kW',
		peakTarget: 'Target grid import limit',
		peakBeforeStorageLabel: 'Grid import peak without storage',
		savedRevision: /^Saved · revision (\d+)$/,
	},
	de: {
		home: '/de/',
		intake: 'Projektoptionen vergleichen',
		title: 'Projektname',
		town: 'Ort oder Standort',
		use: 'Nutzung des Standorts',
		phase: 'Netzanschluss',
		saved: 'Gespeicherte Projekte',
		compare: 'Systeme vergleichen',
		choose: 'Konfiguration übernehmen',
		send: 'Anfrage senden',
		received: 'Anfrage eingegangen',
		report: 'PDF herunterladen',
		enter: 'Projektdaten eingeben',
		newProject: 'Neues Projekt',
		solar: 'Weiter zur PV-Anlage',
		energy: 'Weiter zum Energiebedarf',
		roofChoice: 'Module auf dem Dach platzieren',
		module: 'PV-Modul',
		openRoof: 'Dachbelegung öffnen',
		planView: 'Draufsicht',
		dimensions: [
			'Breite',
			'Tiefe',
			'Dachneigung',
			'Azimut',
			'Relative Dachhöhe',
			'Ursprung in Ostrichtung (U)',
			'Ursprung in Nordrichtung (V)',
		],
		drawing: 'Grundlage der Zeichnung',
		addRoof: 'Rechteckige Dachfläche hinzufügen',
		rows: 'Reihen',
		columns: 'Spalten',
		gap: 'Modulabstand',
		place: 'Modulgruppe platzieren',
		useLayout: 'Belegung übernehmen',
		properties: 'Quelleneigenschaften',
		export: 'Berechtigung zum Export der Geometrie',
		timestamp: 'Zeitstempelspalte',
		value: 'Wertespalte',
		unit: 'Bedeutung und Einheit der Werte',
		decimal: 'Dezimaltrennzeichen in der Datei',
		boundaries: 'Festlegung der Intervallgrenzen',
		timeRole: 'Der Zeitstempel bezeichnet…',
		interval: 'Intervalldauer',
		zone: 'Zeitzone der Quelldaten',
		profile: 'Ihr Lastprofil',
		peakBeforeStorage: '7,83 kW',
		peakTarget: 'Gewünschte Netzbezugsgrenze',
		peakBeforeStorageLabel: 'Netzbezugsspitze ohne Speicher',
		savedRevision: /^Gespeichert · Version (\d+)$/,
	},
} as const;

type Text = (typeof words)[keyof typeof words];
const matrix = [
	['en', 1440],
	['en', 390],
	['de', 1440],
	['de', 390],
] as const;

const button = (owner: Page | Locator, name: string) =>
	owner.getByRole('button', { name, exact: true });

function post(page: Page, endpoint: string) {
	return page.waitForResponse(
		(reply) =>
			reply.request().method() === 'POST' &&
			new URL(reply.url()).pathname.endsWith('/' + endpoint),
		{ timeout: 120_000 }
	);
}

async function enterProject(
	form: Locator,
	text: Text,
	data: {
		title: string;
		town: string;
		country: 'DE' | 'NL';
		use: 'residential' | 'commercial';
		scope: 'storage_only' | 'pv_only';
		purpose: 'self' | 'peak';
	}
) {
	await form.getByLabel(text.title).fill(data.title);
	await form.locator('select[name=country]').selectOption(data.country);
	await form.getByLabel(text.town).fill(data.town);
	await form.getByLabel(text.use).selectOption(data.use);
	await form.locator('select[name=system_scope]').selectOption(data.scope);
	await form
		.locator('select[name=project_purpose]')
		.selectOption(data.purpose);
}

async function prepareSavedRoof(
	page: Page,
	url: string,
	text: Text,
	title: string
) {
	await page.goto(url + text.home);
	const lang = text === words.en ? 'en' : 'de';
	const workspace = page.locator('[data-linker-planner]');
	const project = await launchHomepageConfigurator(page, lang);
	await enterProject(project, text, {
		title,
		town: 'Rotterdam',
		country: 'NL',
		use: 'residential',
		scope: 'pv_only',
		purpose: 'self',
	});
	await button(project, text.compare).click();
	await expect(page).toHaveURL(/[?&]project=[a-f0-9]{32}/);
	const nav = await resumePlannerProject(page, lang, title);
	await nav
		.getByRole('button', {
			name: lang === 'en' ? /Solar$/ : /Photovoltaik$|Solar$/,
		})
		.click();
	await button(workspace, text.roofChoice).click();
	for (const [field, value] of Object.entries({
		panel_length_mm: '1800',
		panel_width_mm: '1100',
		panel_thickness_mm: '30',
		panel_power_w: '430',
	}))
		await workspace.locator('input[name="' + field + '"]').fill(value);
	await button(workspace, text.openRoof).click();
	await button(workspace, text.planView).click();
	const measured = workspace.locator('.sc-roof-props details[open]');
	for (const [index, value] of [
		'8',
		'5',
		'25',
		'180',
		'3',
		'0',
		'0',
	].entries()) {
		await measured.getByLabel(text.dimensions[index]!).fill(value);
	}
	await measured
		.getByLabel(text.drawing)
		.fill('Installer survey of the review fixture');
	await measured.getByRole('checkbox').check();
	await button(measured, text.addRoof).click();
	const controls = workspace.locator('.sc-roof-props');
	await controls.getByLabel(text.rows, { exact: true }).fill('2');
	await controls.getByLabel(text.columns, { exact: true }).fill('2');
	await controls.getByLabel(text.gap).fill('0');
	await button(controls, text.place).click();
	await expect(
		workspace.locator('.sc-roof-board .sc-panel-shape')
	).toHaveCount(4);
	await button(workspace, text.useLayout).click();
	await workspace.getByText(text.properties, { exact: true }).click();
	await workspace.getByLabel(text.export).selectOption('permitted');
	await button(workspace, text.energy).click();
	await workspace.getByLabel(text.phase).selectOption('3');
	const previous = post(page, 'runs/find-equipment');
	await button(workspace, text.compare).click();
	const reply = await previous;
	expect(reply.ok()).toBe(true);
	const request = reply.request().postDataJSON();
	const geometry = request.inputs.geometry;
	expect(geometry).toMatchObject({
		roofs: [expect.objectContaining({ id: expect.any(String) })],
		arrays: [
			expect.objectContaining({
				rows: 2,
				columns: 2,
				roof_id: geometry.roofs[0].id,
			}),
		],
	});
	await expect(button(page, text.choose).first()).toBeEnabled({
		timeout: 120_000,
	});
	const savedVersion = await workspace
		.getByText(text.savedRevision)
		.innerText();
	const revision = text.savedRevision.exec(savedVersion)?.[1];
	expect(revision).toBeDefined();
	return {
		projectId: request.project_id,
		revision: Number(revision),
		geometry,
	};
}

async function chooseAndSend(
	page: Page,
	text: Text,
	projectId: string,
	email: string,
	roof?: Awaited<ReturnType<typeof prepareSavedRoof>>
) {
	const prepared =
		await test.step('2. Choose the configuration', async () => {
			const generated = post(page, 'runs/report');
			const reply = post(page, 'inquiry/form');
			const saved = roof ? post(page, 'projects/revise') : undefined;
			await button(page, text.choose).first().click({ timeout: 120_000 });
			const [report, form] = await Promise.all([generated, reply]);
			if (saved && roof) {
				const selection = await saved;
				expect(selection.ok()).toBe(true);
				expect(selection.request().postDataJSON()).toMatchObject({
					project_id: roof.projectId,
					expected_revision: roof.revision,
					inputs: { geometry: roof.geometry },
				});
			}
			expect(report.ok()).toBe(true);
			expect(form.ok()).toBe(true);
			const request = form.request().postDataJSON();
			expect(request).toMatchObject({
				project_id: projectId,
				revision: report.request().postDataJSON().expected_revision,
				report_run_id: expect.stringMatching(/^[a-f0-9]{32}$/),
			});
			return request;
		});
	return test.step('3. Review and send the inquiry', async () => {
		const form = page.locator('form.linker-inquiry-form');
		await expect(form).toBeVisible();
		await form.locator('[name=name]').fill('Review site installer');
		await form.locator('[name=email]').fill(email);
		await form
			.locator('textarea[name=message]')
			.pressSequentially(
				'Please check the configuration and confirm whether the equipment included in the report is ready for this site.',
				{ delay: 32 }
			);
		await form.locator('[name=consent]').check();
		await button(form, text.send).click();
		await expect(
			page.getByRole('heading', { name: text.received, exact: true })
		).toBeVisible({ timeout: 90_000 });
		const order = JSON.parse(
			wp([
				'eval',
				String.raw`
			if ( ! defined('LINKER_LOCAL_MAIL_DIR') || '127.0.0.1' !== wp_parse_url(home_url(), PHP_URL_HOST) ) {
				throw new RuntimeException('A local WordPress mail sink is required.');
			}
			$orders = wc_get_orders(array('billing_email' => '${email}', 'limit' => 2));
			if ( count($orders) !== 1 ) { throw new RuntimeException('Expected one inquiry'); }
			$order = $orders[0];
			$stored = \Linker\Commerce\Planning\Context::stored($order);
			echo wp_json_encode(array('id' => $order->get_id(), 'status' => $order->get_status(),
				'reference' => count($stored) === 1 ? reset($stored)['reference'] : null));
		`,
			])
		);
		expect(order).toMatchObject({
			status: 'inquiry-received',
			reference: {
				project_id: projectId,
				revision: prepared.revision,
				report_run_id: prepared.report_run_id,
			},
		});
		const report = page.getByRole('link', {
			name: text.report,
			exact: true,
		});
		await expect(report).toHaveAttribute(
			'href',
			new RegExp(
				`/inquiries/${order.id}/planning-report/${order.reference.handoff_id}`
			)
		);
		const pdf = await page.request.get(
			new URL((await report.getAttribute('href'))!, page.url()).href
		);
		expect(pdf.ok()).toBe(true);
		const document = await pdf.body();
		expect(document.subarray(0, 5).toString()).toBe('%PDF-');
		return document;
	});
}

// Open Power System Data. 2020. Data Package Household Data. Version 2020-04-15.
// https://data.open-power-system-data.org/household_data/2020-04-15/ (CC BY 4.0).
// CoSSMic DE_KN_residential6 hourly gross site load is the interval change in
// grid import plus PV generation less grid export. Selected channels have no
// interpolation flags in these 54 intervals. The peak is 7.826 kW.
const loadFile = fileURLToPath(
	new URL('../fixtures/cossmic-konstanz-load-2017-06-19.csv', import.meta.url)
);

async function fillMeasuredLoad(form: Locator, text: Text) {
	await form.locator('input[name=load_profile]').setInputFiles(loadFile);
	await form.locator('select[name=load_profile_delimiter]').selectOption(';');
	await form
		.locator('input[name=load_profile_source]')
		.fill('Open Power System Data, CoSSMic Konstanz household 6');
	await form
		.locator('textarea[name=load_profile_rights]')
		.fill(
			'CC BY 4.0. Hourly gross load derived from the Open Power System Data Household Data release 2020-04-15.'
		);
	await form.getByLabel(text.timestamp, { exact: true }).fill('Time');
	await form.getByLabel(text.value, { exact: true }).fill('Load');
	await form
		.getByLabel(text.unit, { exact: true })
		.selectOption('interval_energy_kwh');
	await form.getByLabel(text.decimal, { exact: true }).selectOption('.');
	await form
		.getByLabel(text.boundaries, { exact: true })
		.selectOption('fixed');
	await form.getByLabel(text.timeRole, { exact: true }).selectOption('start');
	await form.getByLabel(text.interval).fill('60');
	await form.getByLabel(text.zone, { exact: true }).selectOption('UTC');
}

test.beforeAll(async ({ request }) => {
	const { url, engineUrl } = instance();
	expect(new URL(url).hostname).toBe('127.0.0.1');
	expect(
		(await request.get(engineUrl + '/health')).ok(),
		'The review Engine must be running'
	).toBe(true);
});

for (const [lang, width] of matrix) {
	test(`${lang} ${width}: a saved rooftop layout reaches Woo untouched in three actions`, async ({
		page,
		context,
	}) => {
		page.setDefaultTimeout(15_000);
		expect(await context.cookies()).toEqual([]);
		const restoreBudgets = isolateMailBudgets();
		try {
			const text = words[lang];
			const { url } = instance();
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			const tag = randomUUID();
			const title = `Saved Rotterdam roof ${tag}`;
			const previous =
				await test.step('Earlier visit creates and saves a roof with four placed modules', () =>
					prepareSavedRoof(page, url, text, title));
			await page.goto(url + text.home);
			await test.step('1. Bring the rooftop project and compare', async () => {
				await compareSavedFromHome(page, lang, previous.projectId);
				await expect(page).toHaveURL(
					new RegExp(`[?&]project=${previous.projectId}`)
				);
			});
			await chooseAndSend(
				page,
				text,
				previous.projectId,
				`e2e-roof-${tag}@example.test`,
				previous
			);
		} finally {
			restoreBudgets();
		}
	});

	test(`${lang} ${width}: a measured load and peak target reach Woo in three actions`, async ({
		page,
		context,
	}) => {
		page.setDefaultTimeout(15_000);
		expect(await context.cookies()).toEqual([]);
		const restoreBudgets = isolateMailBudgets();
		try {
			const text = words[lang];
			const { url } = instance();
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await page.goto(url + text.home);
			const tag = randomUUID();
			const projectId =
				await test.step('1. Supply site measurements and compare', async () => {
					const form = await launchHomepageConfigurator(page, lang);
					await enterProject(form, text, {
						title: `Measured Konstanz load ${tag}`,
						town: 'Konstanz',
						country: 'DE',
						use: 'residential',
						scope: 'storage_only',
						purpose: 'peak',
					});
					await form.getByLabel(text.phase).selectOption('3');
					await form.locator('input[name=peak_import_kw]').fill('5');
					await fillMeasuredLoad(form, text);
					const imported = post(page, 'profiles/csv');
					const previewed = post(page, 'profiles/preview');
					const compared = post(page, 'runs/find-equipment');
					await button(form, text.compare).click();

					const [upload, preview] = await Promise.all([
						imported,
						previewed,
					]);
					expect(upload.ok()).toBe(true);
					expect(preview.ok()).toBe(true);
					const source = preview.request().postDataJSON();
					expect(source).toMatchObject({
						project_id: upload.request().postDataJSON().project_id,
						asset_id: expect.stringMatching(/^[a-f0-9]{32}$/),
					});
					expect(
						upload.request().postDataJSON().mapping
					).toMatchObject({
						timestamp_column: 'Time',
						value_column: 'Load',
						measurement: 'gross_load',
						origin: 'measured',
						value_kind: 'interval_energy_kwh',
						interval_seconds: 3600,
						timezone: 'UTC',
					});
					const comparison = await compared;
					expect(comparison.ok()).toBe(true);
					const request = comparison.request().postDataJSON();
					expect(request).toMatchObject({
						project_id: source.project_id,
						inputs: {
							profile_selections: {
								selected: { gross_load: source.asset_id },
							},
							energy_scenario: {
								schedule: [
									expect.objectContaining({
										import_cap_kw: 5,
									}),
								],
							},
						},
					});
					const profile = page.locator('.sc-system-options');
					await expect(
						profile.getByRole('heading', {
							name: text.profile,
							exact: true,
						})
					).toBeVisible();
					await expect(
						profile.getByText(text.peakBeforeStorage, {
							exact: true,
						})
					).toBeVisible();
					return request.project_id;
				});
			const pdf = await chooseAndSend(
				page,
				text,
				projectId,
				`e2e-peak-${tag}@example.test`
			);
			const extracted = spawnSync('pdftotext', ['-layout', '-', '-'], {
				input: pdf,
				encoding: 'utf8',
			});
			expect(
				extracted.status,
				extracted.error?.message ?? extracted.stderr
			).toBe(0);
			const report = extracted.stdout;
			expect(report).toMatch(
				new RegExp(`${text.peakTarget}[^\\n]*5(?:[.,]00)? kW`)
			);
			expect(report).toMatch(
				new RegExp(`${text.peakBeforeStorageLabel}[^\\n]*7[.,]826 kW`)
			);
		} finally {
			restoreBudgets();
		}
	});
}

for (const [lang, width] of matrix) {
	test(`${lang} ${width}: the rooftop report, materials export and Genie retain the declared panels`, async ({
		page,
	}) => {
		const text = words[lang];
		await page.setViewportSize({
			width,
			height: width === 390 ? 844 : 900,
		});
		const restoreBudgets = isolateMailBudgets();
		try {
			await prepareSavedRoof(
				page,
				instance().url,
				text,
				lang === 'de' ? 'Dach in Rotterdam' : 'Rotterdam roof'
			);
			const workspace = page.locator('[data-linker-planner]');
			await button(workspace, text.choose).first().click();
			await button(
				workspace,
				lang === 'en'
					? 'Review the proposal'
					: 'Lösungsvorschlag prüfen'
			).click();
			await button(
				workspace,
				lang === 'en'
					? 'Generate project report'
					: 'Projektbericht erstellen'
			).click();
			const consent = button(
				page,
				lang === 'en' ? 'Reject all' : 'Alle ablehnen'
			);
			if (await consent.isVisible()) await consent.click();
			const materials = button(
				workspace,
				lang === 'en'
					? 'Download bill of materials (CSV)'
					: 'Stückliste herunterladen (CSV)'
			);
			await expect(materials).toBeEnabled({ timeout: 120000 });
			const retired = /Trina|TSM[-_ ]?460|Vertex[- ]?S/i;
			const layoutTitle =
				lang === 'en' ? 'Solar panel layout' : 'PV-Modulbelegung';
			await expect(
				workspace.getByRole('heading', {
					name: layoutTitle,
					exact: true,
				})
			).toBeVisible();
			const pdfButton = button(workspace, text.report);
			for (const [format, control] of [
				['pdf', pdfButton],
				['csv', materials],
			] as const) {
				const pending = page.waitForEvent('download');
				await control.click();
				const download = await pending;
				const path = await download.path();
				expect(path).toBeTruthy();
				const bytes = readFileSync(path!);
				const content =
					format === 'pdf'
						? spawnSync('pdftotext', ['-layout', '-', '-'], {
								input: bytes,
								encoding: 'utf8',
							}).stdout
						: bytes.toString('utf8');
				expect(content).toMatch(/430\s*Wp/);
				expect(content).not.toMatch(retired);
				expect(content).not.toMatch(
					/PV reference module · project quotation|PV-Referenzmodul · Projektangebot/i
				);
				if (format === 'csv') {
					const row = content
						.split(/\r?\n/)
						.find((line) => /430\s*Wp/.test(line));
					expect(row).toMatch(/[;,"]4(?:[;,"]|$)/);
					expect(row).toContain(layoutTitle);
				}
			}
			await workspace
				.locator('#sc-review [data-linker-genie-planning]')
				.click();
			const panel = page.locator('.linker-genie-app__panel');
			const input = panel.locator('.linker-genie-app__input');
			await input.fill(
				lang === 'en'
					? 'How many solar panels are on the roof in my saved report?'
					: 'Wie viele PV-Module sind laut meinem gespeicherten Bericht auf dem Dach?'
			);
			const votes = panel.locator('.linker-genie-app__votes');
			const before = await votes.count();
			await panel.locator('.linker-genie-app__send').click();
			await expect
				.poll(() => votes.count(), { timeout: 120000 })
				.toBeGreaterThan(before);
			const answer = panel.locator('.linker-genie-message-body').last();
			await expect(answer).toContainText(
				/(?:4|four|vier)\s*(?:solar\s*|PV[- ]?)?(?:panels?|modules?|Module)|(?:panel count|module count|Anzahl[^.]{0,16})\s*[:|]?\s*4\b/i
			);
			await expect(answer).not.toContainText(retired);
			await panel.screenshot({
				path: test.info().outputPath('genie-roof-report.png'),
			});
		} finally {
			restoreBudgets();
		}
	});
}
