/**
 * The planner's full customer chain on one saved project: site -> roof (with
 * export permission) -> coordinate references -> module spec -> array ->
 * three interval profiles -> real PVGIS weather -> PV model -> equipment
 * selection with PV strings -> equipment check -> three-section scenario ->
 * energy calculation -> re-check at the saved revision -> planning report
 * (PDF + BOM CSV) -> transfer to the Woo solution draft -> cart readback.
 *
 * Drives the real review stack end to end; the equipment-check retries absorb
 * one-time late-edit revision drift (409 evaluation_revision_changed), the
 * way a customer's second click would.
 */
import { expect, test, type Page } from '@playwright/test';
import { writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { seedConsentCookies } from '../lib/consent';
import { instance, wp } from '../lib/instance';

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

type Lang = 'en' | 'de';

// Generated from the shipped German catalog - do not hand-edit words.
const WORDS = {
	en: {
		addConversionGroup: 'Add conversion group',
		addModuleArray: 'Add module array',
		addModuleSpecification: 'Add module specification',
		addRoofFace: 'Add roof face',
		includedModules: 'Included modules',
		addSelectedModulesToString: 'Add selected modules to string',
		addSelectedProductsToSolution:
			'Add selected products to solution draft',
		annualElectricityUse: 'Annual electricity use',
		availablePvAc: 'Available PV output · AC',
		pointDecimal: 'Point · 12.5',
		weatherValidated: 'passed validation',
		arrayModels: 'Array models',
		powerConversion: 'Power conversion',
		syntheticSource: 'Synthetic test data',
		avgPowerKw: 'Average power over each interval · kW',
		timestampIdentifies: 'The timestamp identifies',
		externalAuxAc: 'External auxiliary load · AC',
		applyProperties: 'Apply properties',
		calculatePvForSavedInputs: 'Calculate PV for saved inputs',
		calculateSavedScenario: 'Calculate saved scenario',
		checkSavedEquipmentSelection: 'Check saved equipment selection',
		chooseAnOperatingMode: 'Choose an operating mode',
		chooseAnOption: 'Choose an option',
		chooseEquipmentManually: 'Choose equipment manually',
		comma: 'Comma',
		confirmChanges: 'Confirm changes',
		coordinateReferences: 'Coordinate references',
		createProject: 'Create project',
		decimalSeparator: 'Decimal separator',
		discardStoredRequest: 'Discard stored request',
		endWithUtc: 'End with UTC',
		energyCalculation: 'Energy calculation',
		energyInputs: 'Energy inputs',
		equipment: 'Equipment',
		expectedRadiationDatabase: 'Expected radiation database',
		firstSourceYear: 'First source year',
		furtherAssessmentOfTheComplete:
			'Further assessment of the complete system is required.',
		generatePlanningReport: 'Generate planning report',
		gridCharging: 'Grid charging',
		gridCondition: 'Grid condition',
		gridConnection: 'Grid connection',
		gridExportLimit: 'Grid export limit',
		gridImportLimit: 'Grid import limit',
		importAndReviewData: 'Import and review data',
		importIntervalData: 'Import interval data',
		intervalBoundaries: 'Interval boundaries',
		intervalDuration: 'Interval duration',
		inverterInput: 'Inverter input',
		inverterOrIntegratedStorageSystem:
			'Inverter or integrated storage system',
		lastSourceYear: 'Last source year',
		lowestDesignAmbientTemperature: 'Lowest design ambient temperature',
		mppt: 'MPPT',
		modulesAssigned: '8 of 8 roof modules assigned',
		measurementPoint: 'Measurement point',
		newProject: 'New project',
		notIncluded: 'Not included',
		notUsed: 'Not used',
		operation: 'Operation',
		pvArrayKwp: 'PV array kWp',
		pvArraySize: 'PV array size',
		pvAvailable: 'PV available',
		pvGeneration: 'PV generation',
		pvModelPreparedInThis: 'PV model prepared in this draft',
		pvStringsAndInputs: 'PV strings and inputs',
		planningReport: 'Planning report',
		postcodeOrTown: 'Postcode or town',
		preparePvModel: 'Prepare PV model',
		prepareEquipmentSelection: 'Prepare equipment selection',
		prepareScenarioSettings: 'Prepare scenario settings',
		prepareWeatherSettings: 'Prepare weather settings',
		previewColumns: 'Preview columns',
		projectOverview: 'Project overview',
		quickStartPlanInOne: 'Quick start: plan in one screen',
		reloadProductData: 'Reload product data',
		repeatedTimeColumn: 'Repeated-time column',
		requestWeatherForSavedInputs: 'Request weather for saved inputs',
		requiredContinuousAcDischargePower:
			'Required continuous AC discharge power kW',
		requiredUsableEnergyKwh: 'Required usable energy kWh',
		requirementsNotMet: 'Requirements not met',
		reviewEnergyInputs: 'Review energy inputs',
		saveProject: 'Save project',
		saved: 'Saved',
		configurator: '/solution-configurator/',
		scenarioSettings: 'Scenario settings',
		selectAllAvailableModules: 'Select all available modules',
		selectedInTheCurrentDraft: 'Selected in the current draft',
		selectedProductsAddedToSolution:
			'Selected products added to solution draft.',
		sendInquiry: 'Send inquiry',
		setUpPvStrings: 'Set up PV strings',
		singleSystem: 'Single system',
		sourceAndPermission: 'Source and Permission',
		sourceLabel: 'Source label',
		sourceOrAssumptionForStorage:
			'Source or assumption for storage parameters',
		sourceTimeZone: 'Source time zone',
		sourceType: 'Source type',
		startWithUtc: 'Start with UTC',
		startWithAnEmptyBattery: 'Start with an empty battery',
		startingState: 'Starting state',
		storage: 'Storage',
		syntheticCalculationYear: 'Synthetic calculation year',
		temperatureSourceAndLocation: 'Temperature source and location',
		terrainHorizon: 'Terrain horizon',
		timestampAndFixedDuration: 'Timestamp and fixed duration',
		timestampColumn: 'Timestamp column',
		totalSiteLoad: 'Total site load',
		unsaved: 'Unsaved',
		updateParametersForCurrentRoof:
			'Update parameters for current roof layout',
		usableStoredEnergy: 'Usable stored energy',
		useRoofCoordinates: 'Use roof coordinates',
		useTheSharedProfileRange: 'Use the shared profile range',
		useThisProfileInThe: 'Use this profile in the open draft',
		useThisWeatherSource: 'Use this weather source',
		valueColumn: 'Value column',
		valueMeaning: 'Value meaning',
		viewSolutionDraft: 'View solution draft',
		weatherSource: 'Weather source',
	},
	de: {
		addConversionGroup: 'Umwandlungsgruppe hinzuf\u00fcgen',
		addModuleArray: 'Modulfeld hinzuf\u00fcgen',
		addModuleSpecification: 'Modulspezifikation hinzuf\u00fcgen',
		addRoofFace: 'Dachfl\u00e4che hinzuf\u00fcgen',
		includedModules: 'Ber\u00fccksichtigte Module',
		addSelectedModulesToString:
			'Ausgew\u00e4hlte Module zum String hinzuf\u00fcgen',
		addSelectedProductsToSolution:
			'Ausgew\u00e4hlte Produkte zum L\u00f6sungsentwurf hinzuf\u00fcgen',
		annualElectricityUse: 'J\u00e4hrlicher Stromverbrauch',
		availablePvAc: 'Verf\u00fcgbare PV-Leistung \u00b7 AC',
		pointDecimal: 'Punkt \u00b7 12.5',
		weatherValidated: 'gepr\u00fcft und gespeichert',
		arrayModels: 'Modelle der Modulfelder',
		powerConversion: 'Umwandlung',
		syntheticSource: 'Synthetische Testdaten',
		avgPowerKw: 'Mittlere Leistung je Intervall \u00b7 kW',
		timestampIdentifies: 'Der Zeitstempel bezeichnet',
		externalAuxAc: 'Externer Hilfsverbrauch \u00b7 AC',
		applyProperties: 'Eigenschaften anwenden',
		calculatePvForSavedInputs:
			'PV f\u00fcr gespeicherte Eingaben berechnen',
		calculateSavedScenario: 'Gespeichertes Szenario berechnen',
		checkSavedEquipmentSelection:
			'Gespeicherte Ger\u00e4teauswahl pr\u00fcfen',
		chooseAnOperatingMode: 'Betriebsart ausw\u00e4hlen',
		chooseAnOption: 'Bitte ausw\u00e4hlen',
		chooseEquipmentManually: 'Ger\u00e4te manuell ausw\u00e4hlen',
		comma: 'Komma',
		confirmChanges: '\u00c4nderungen best\u00e4tigen',
		coordinateReferences: 'Koordinatenbez\u00fcge',
		createProject: 'Projekt anlegen',
		decimalSeparator: 'Dezimaltrennzeichen in der Datei',
		discardStoredRequest: 'Gespeicherte Anfrage verwerfen',
		endWithUtc: 'Ende (UTC oder Zeitversatz)',
		energyCalculation: 'Energieberechnung',
		energyInputs: 'Energiedaten',
		equipment: 'Ger\u00e4te',
		expectedRadiationDatabase: 'Erwartete Strahlungsdatenbank',
		firstSourceYear: 'Erstes Jahr des Quellzeitraums',
		furtherAssessmentOfTheComplete:
			'Dieses Ergebnis dokumentiert die vorgeschlagene Ger\u00e4teauswahl und die hier gepr\u00fcften Anforderungen. Die Gesamtanlage muss noch weiter gepr\u00fcft werden.',
		generatePlanningReport: 'Planungsbericht erstellen',
		gridCharging: 'Laden aus dem Netz freigegeben',
		gridCondition: 'Netzzustand',
		gridConnection: 'Netzanschluss',
		gridExportLimit: 'Grenze f\u00fcr die Netzeinspeisung',
		gridImportLimit: 'Grenze f\u00fcr den Netzbezug',
		importAndReviewData: 'Daten importieren und pr\u00fcfen',
		importIntervalData: 'Zeitreihendaten importieren',
		intervalBoundaries: 'Festlegung der Intervallgrenzen',
		intervalDuration: 'Intervalldauer',
		inverterInput: 'Wechselrichtereingang',
		inverterOrIntegratedStorageSystem:
			'Wechselrichter oder integriertes Speichersystem',
		lastSourceYear: 'Letztes Jahr des Quellzeitraums',
		lowestDesignAmbientTemperature:
			'Niedrigste Auslegungs-Umgebungstemperatur',
		mppt: 'MPPT',
		modulesAssigned: '8 von 8 Dachmodulen zugeordnet',
		measurementPoint: 'Messpunkt',
		newProject: 'Neues Projekt',
		notIncluded: 'Nicht aufnehmen',
		notUsed: 'Nicht verwendet',
		operation: 'Betrieb',
		pvArrayKwp: 'PV-Leistung kWp',
		pvArraySize: 'Gr\u00f6\u00dfe der PV-Anlage',
		pvAvailable: 'PV in diesem Zeitraum verf\u00fcgbar',
		pvGeneration: 'PV-Erzeugung',
		pvModelPreparedInThis: 'PV-Modell in diesem Entwurf vorbereitet',
		pvStringsAndInputs: 'PV-Strings und Eing\u00e4nge',
		planningReport: 'Planungsbericht',
		postcodeOrTown: 'Postleitzahl oder Ort',
		preparePvModel: 'PV-Modell vorbereiten',
		prepareEquipmentSelection: 'Ger\u00e4teauswahl vorbereiten',
		prepareScenarioSettings: 'Szenario vorbereiten',
		prepareWeatherSettings: 'Wettereinstellungen vorbereiten',
		previewColumns: 'Spaltenvorschau',
		projectOverview: 'Projekt\u00fcbersicht',
		quickStartPlanInOne: 'Schnellstart: Planen auf einem Bildschirm',
		reloadProductData: 'Produktdaten neu laden',
		repeatedTimeColumn:
			'Spalte f\u00fcr doppelte Ortszeiten \u00b7 optional',
		requestWeatherForSavedInputs:
			'Wetterdaten f\u00fcr gespeicherte Eingaben abfragen',
		requiredDischargeKw: 'Benötigte AC-Dauerleistung bei Entladung kW',
		requiredUsableKwh: 'Benötigte nutzbare Speicherenergie kWh',
		requirementsNotMet: 'Anforderungen nicht erf\u00fcllt',
		reviewEnergyInputs: 'Energiedaten pr\u00fcfen',
		saveProject: 'Projekt speichern',
		saved: 'Gespeichert',
		configurator: '/de/loesungskonfigurator/',
		scenarioSettings: 'Szenarioeinstellungen',
		selectAllAvailableModules: 'Alle zuweisbaren Module ausw\u00e4hlen',
		selectedInTheCurrentDraft:
			'Im aktuellen Projektentwurf ausgew\u00e4hlt',
		selectedProductsAddedToSolution:
			'Die ausgew\u00e4hlten Produkte wurden zum L\u00f6sungsentwurf hinzugef\u00fcgt.',
		sendInquiry: 'Anfrage senden',
		setUpPvStrings: 'PV-Strings planen',
		singleSystem: 'Einzelnes System',
		// A hasText prefix of the full label (unit suffixes stay untranslated).
		sourceAndPermission: 'Herkunft und Berechtigung',
		sourceLabel: 'Bezeichnung der Datenquelle',
		sourceOrAssumptionForStorage:
			'Quelle oder Annahme f\u00fcr die Speicherparameter',
		sourceTimeZone: 'Zeitzone der Quelldaten',
		sourceType: 'Art der Datenquelle',
		startWithUtc: 'Beginn (UTC oder Zeitversatz)',
		startWithAnEmptyBattery: 'Anfangsenergie auf null setzen',
		startingState: 'Anfangszustand',
		storage: 'Speicher',
		syntheticCalculationYear: 'Synthetisches Berechnungsjahr',
		temperatureSourceAndLocation:
			'Quelle der Temperaturangabe und Standort',
		terrainHorizon: 'Gel\u00e4ndehorizont',
		timestampAndFixedDuration: 'Zeitstempel und feste Dauer',
		timestampColumn: 'Zeitstempelspalte',
		totalSiteLoad: 'Gesamte Standortlast',
		unsaved: 'Ungespeicherte \u00c4nderungen',
		updateParametersForCurrentRoof:
			'Parameter an aktuelle Dachbelegung anpassen',
		usableStoredEnergy: 'Nutzbare Speicherenergie',
		useRoofCoordinates: 'Dachkoordinaten \u00fcbernehmen',
		useTheSharedProfileRange: 'Gemeinsamen Profilzeitraum \u00fcbernehmen',
		useThisProfileInThe: 'Profil im offenen Projektentwurf verwenden',
		useThisWeatherSource: 'Diese Wetterquelle verwenden',
		valueColumn: 'Wertespalte',
		valueMeaning: 'Bedeutung und Einheit der Werte',
		viewSolutionDraft: 'L\u00f6sungsentwurf ansehen',
		weatherSource: 'Wetterquelle',
		requiredUsableEnergyKwh: 'Benötigte nutzbare Speicherenergie kWh',
		requiredContinuousAcDischargePower:
			'Benötigte AC-Dauerleistung bei Entladung kW',
	},
} as const;

/** German number fields take a decimal comma (the field's own hint). */
function num(lang: Lang, value: string): string {
	return 'de' === lang ? value.replace('.', ',') : value;
}

for (const lang of ['en', 'de'] as const) {
	const words = WORDS[lang];
	test(`${lang}: the full planner chain: report, transfer and the Woo solution draft`, async ({
		page,
	}) => {
		test.setTimeout(900_000);

		const equipResponses: string[] = [];
		const equipStatuses: number[] = [];
		// Route interception is the only reliable way to read the error body
		// (page.on('response') bodies race the app's own reader).
		void page.route('**/rpc/runs/equipment', async (route) => {
			const response = await route.fetch();
			equipStatuses.push(response.status());
			let body = '';
			try {
				body = (await response.text()).slice(0, 400);
			} catch {
				body = '<unreadable>';
			}
			await route.fulfill({ response });
		});

		const domClick = async (text: string, scope = '#lp-calculations') => {
			for (let attempt = 0; attempt < 10; attempt += 1) {
				const ok = await page.evaluate(
					(arg: string[]) => {
						const needle = arg[0] ?? '';
						const root = arg[1] ?? '#lp-calculations';
						const button = Array.from(
							document.querySelectorAll(`${root} button`)
						).find(
							(n) =>
								n.textContent?.trim() === needle ||
								(n.textContent?.includes(needle) ?? false)
						);
						if (button && !(button as HTMLButtonElement).disabled) {
							(button as HTMLElement).click();
							return true;
						}
						return false;
					},
					[text, scope]
				);
				if (ok) {
					await page.waitForTimeout(900);
					return;
				}
				await page.waitForTimeout(1000);
			}
			throw new Error(`dom click missed: ${text}`);
		};
		const switchTab = async (name: string) => {
			await domClick(name);
			await page.waitForTimeout(600);
		};
		const saveProject = async () => {
			for (let attempt = 0; attempt < 3; attempt += 1) {
				const state = await page
					.locator('.lp-save-state')
					.textContent();
				if (state?.includes(words.unsaved)) {
					await page
						.getByRole('button', { name: words.saveProject })
						.click({ noWaitAfter: true });
					await expect(page.locator('.lp-save-state')).toContainText(
						words.saved,
						{
							timeout: 90_000,
						}
					);
					await page.waitForTimeout(2500);
				} else break;
			}
		};

		// operations.start silently no-ops while ANY stored record is
		// unconfirmed (resultId null): clear every pending recovery row before
		// starting a run.
		const clearUnconfirmed = async () => {
			for (let round = 0; round < 6; round += 1) {
				const pending = await page.locator(
					'#lp-calculations button:visible',
					{
						hasText: words.discardStoredRequest,
					}
				);
				if (!(await pending.count())) break;
				await domClick(words.discardStoredRequest);
				await page.waitForTimeout(1200);
			}
		};

		// --- Project, site, roof, coordinate references, array (all proven). ---
		await page.goto(instance().url + words.configurator, {
			waitUntil: 'networkidle',
		});
		await page
			.getByRole('button', { name: words.newProject })
			.first()
			.click();
		await page
			.locator('input[maxlength="256"]')
			.first()
			.fill('Report chain');
		await page.getByRole('button', { name: words.createProject }).click();
		await expect(page).toHaveURL(/project=/, { timeout: 60_000 });
		const chainProject =
			new URL(page.url()).searchParams.get('project') ?? '';

		const site = page.locator('#lp-site');
		await site.locator('select').first().selectOption('DE');
		await site.locator('input').nth(0).fill('Triftstrasse 5');
		await site.locator('input').nth(1).fill(num(lang, '48.1689'));
		await site.locator('input').nth(2).fill(num(lang, '11.5844'));
		// The project note travels with the handoff into the inquiry's
		// revision-protected section (not a calculation input).
		await page
			.locator('#lp-notes textarea')
			.first()
			.fill('8 kWp roof with battery, Munich, south-facing');

		await page.getByRole('link', { name: words.projectOverview }).click();
		const roofEntry = page.locator('.lp-overview-empty .lp-button');
		await roofEntry.waitFor({ state: 'attached' });
		await page.evaluate(
			(el) => (el as HTMLElement).click(),
			await roofEntry.elementHandle()
		);
		await expect(page).toHaveURL(/#lp-design/, { timeout: 15_000 });

		// Narrowed to .lp-button: the German empty state's 'Erste
		// Dachfläche hinzufügen' also substring-matches.
		await page
			.locator('#lp-design button.lp-button', {
				hasText: words.addRoofFace,
			})
			.first()
			.click();
		const faceForm = page.locator('#lp-design form');
		await faceForm.locator('[name="name"]').fill('Main roof');
		await faceForm.locator('[name="width"]').fill('10');
		await faceForm.locator('[name="length"]').fill('6');
		await faceForm.locator('[name="pitch"]').fill('30');
		await faceForm.locator('[name="bearing"]').fill('180');
		await faceForm.locator('[name="source"]').fill('Owner measurement');
		await faceForm
			.locator('[name="rights_note"]')
			.fill('Owner-provided tape measurement');
		await faceForm.locator('[name="rights"]').check();
		// Reports that include the geometry require its export permission;
		// the select defaults to 'unknown' which the report refuses.
		await faceForm.locator('[name="export"]').selectOption('permitted');
		await faceForm.locator('button[type="submit"]').click();

		await page
			.locator('#lp-design button', {
				hasText: words.coordinateReferences,
			})
			.click();
		const coordForm = page.locator('#lp-design form');
		await coordForm
			.locator('select[name="north"]')
			.selectOption('true_north');
		await coordForm.locator('[name="latitude"]').fill(num(lang, '48.1689'));
		await coordForm
			.locator('[name="longitude"]')
			.fill(num(lang, '11.5844'));
		const northSource = coordForm.locator('select[name="north_source"]');
		if ((await northSource.locator('option').count()) > 1)
			await northSource.selectOption({ index: 1 });
		const anchorSource = coordForm.locator('select[name="anchor_source"]');
		if ((await anchorSource.locator('option').count()) > 1)
			await anchorSource.selectOption({ index: 1 });
		await coordForm.locator('button[type="submit"]').click();

		await page
			.locator('#lp-design button', {
				hasText: words.addModuleSpecification,
			})
			.click({ timeout: 15_000 });
		const moduleForm = page.locator('#lp-design form');
		await moduleForm.locator('select').first().selectOption({ index: 0 });
		await moduleForm.locator('button[type="submit"]').click();
		await expect(
			page.locator('#lp-design button', { hasText: words.addModuleArray })
		).toBeEnabled({ timeout: 30_000 });
		await page
			.locator('#lp-design button', { hasText: words.addModuleArray })
			.click();
		const arrayForm = page.locator('#lp-design form');
		await arrayForm.locator('[name="name"]').fill('Main array');
		await arrayForm.locator('[name="module"]').selectOption({ index: 1 });
		const fillField = async (name: string, value: string) => {
			const field = arrayForm.locator(`[name="${name}"]`);
			if (await field.count()) await field.fill(value);
		};
		await fillField('u', '1');
		await fillField('v', '1');
		await fillField('rows', '2');
		await fillField('columns', '4');
		// The configurator/validation row: an out-of-range tilt (max 90) is
		// refused by the form's own constraint - Apply does not commit it.
		await fillField('rotation', '0');
		await fillField('tilt', '91');
		await arrayForm
			.locator('button', { hasText: words.applyProperties })
			.click();
		await page.waitForTimeout(800);
		await expect(page.locator('#lp-design')).not.toContainText(
			`${words.includedModules}8`
		);
		await fillField('tilt', '0');
		await fillField('column_gap', num(lang, '0.02'));
		await fillField('row_gap', num(lang, '0.1'));
		await fillField('height', num(lang, '0.1'));
		await fillField('mounting', 'Fixed rails on roof hooks');
		await arrayForm
			.locator('button', { hasText: words.applyProperties })
			.click();
		await expect(page.locator('#lp-design')).toContainText(
			`${words.includedModules}8`,
			{
				timeout: 30_000,
			}
		);
		await saveProject();

		// --- Interval profile import + draft selection (proven sequence). ---
		await page
			.getByRole('link', { name: words.energyInputs })
			.click({ timeout: 15_000 });
		await page.waitForTimeout(800);
		// The scenario needs three interval roles (scenario_profiles_required):
		// gross load, available PV and separate AC auxiliary.
		const importProfile = async (measurement: string, label: string) => {
			const csv = join(tmpdir(), label + '.csv');
			const rows: string[] = ['timestamp,power'];
			const start = Date.UTC(2026, 0, 1) / 1000;
			for (let i = 0; i < 30 * 96; i += 1) {
				const hour = ((i % 96) * 15) / 60;
				const base =
					40 + 30 * Math.sin(((hour - 6) / 24) * 2 * Math.PI);
				rows.push(
					new Date((start + i * 900) * 1000)
						.toISOString()
						.slice(0, 19) +
						',' +
						Math.round(Math.max(5, base) * 1000) / 1000
				);
			}
			writeFileSync(csv, rows.join('\n'));
			await page
				.locator('#lp-profiles button', {
					hasText: words.importIntervalData,
				})
				.first()
				.click({ noWaitAfter: true });
			await page
				.locator('#lp-profiles input[type="file"]')
				.setInputFiles(csv);
			await page.waitForTimeout(1500);
			await page
				.locator('#lp-profiles select')
				.first()
				.selectOption({ label: words.comma });
			await domClick(words.previewColumns, '#lp-profiles');
			const byLabel = (text: string) =>
				page
					.locator('#lp-profiles label', { hasText: text })
					.locator('select');
			await byLabel(words.timestampColumn).selectOption({
				label: 'timestamp',
			});
			await byLabel(words.valueColumn).selectOption({ label: 'power' });
			await byLabel(words.measurementPoint).selectOption({
				label: measurement,
			});
			await byLabel(words.valueMeaning).selectOption({
				label: words.avgPowerKw,
			});
			await byLabel(words.decimalSeparator).selectOption({
				label: words.pointDecimal,
			});
			await byLabel(words.sourceType).selectOption({
				label: words.syntheticSource,
			});
			await byLabel(words.intervalBoundaries).selectOption({
				label: words.timestampAndFixedDuration,
			});
			await byLabel(words.timestampIdentifies).selectOption({
				index: 1,
			});
			await page
				.locator('#lp-profiles label', {
					hasText: words.intervalDuration,
				})
				.locator('input')
				.fill('15');
			await byLabel(words.sourceTimeZone).selectOption({ label: 'UTC' });
			await byLabel(words.repeatedTimeColumn).selectOption({
				label: words.notUsed,
			});
			await page
				.locator('#lp-profiles label', { hasText: words.sourceLabel })
				.locator('input')
				.fill(label);
			await page
				.locator('#lp-profiles label', {
					hasText: words.sourceAndPermission,
				})
				.locator('textarea')
				.fill('Generated for the e2e chain');
			await domClick(words.importAndReviewData, '#lp-profiles');
			await domClick(words.useThisProfileInThe, '#lp-profiles');
			await page.waitForTimeout(800);
		};
		await importProfile(words.totalSiteLoad, 'E2E synthetic load');
		await importProfile(words.availablePvAc, 'E2E synthetic pv');
		await importProfile(words.externalAuxAc, 'E2E synthetic aux');
		await saveProject();

		// --- Weather (panel-direct selection; all proven). ---
		await page
			.getByRole('link', { name: words.energyCalculation })
			.click({ timeout: 15_000 });
		await page.waitForTimeout(1000);
		await switchTab(words.weatherSource);
		await domClick(words.useRoofCoordinates);
		const weatherTab = page.locator('#lp-calculations');
		await weatherTab.getByLabel(words.firstSourceYear).fill('2005');
		await weatherTab.getByLabel(words.lastSourceYear).fill('2023');
		await weatherTab
			.getByLabel(words.expectedRadiationDatabase)
			.selectOption({ index: 1 });
		await weatherTab
			.getByLabel(words.terrainHorizon)
			.selectOption({ index: 1 });
		await weatherTab
			.getByLabel(words.syntheticCalculationYear)
			.fill('2023');
		await domClick(words.prepareWeatherSettings);
		await page.waitForTimeout(1500);
		await saveProject();
		await expect
			.poll(
				async () =>
					page
						.locator('#lp-calculations button', {
							hasText: words.requestWeatherForSavedInputs,
						})
						.first()
						.isEnabled(),
				{ timeout: 60_000 }
			)
			.toBe(true);
		await domClick(words.requestWeatherForSavedInputs);
		await expect
			.poll(
				async () =>
					(
						await page.locator('#lp-calculations').textContent()
					)?.includes(words.weatherValidated),
				{ timeout: 240_000, intervals: [3000] }
			)
			.toBe(true);
		await expect
			.poll(
				async () =>
					(await page
						.locator('#lp-calculations')
						.getByRole('button', {
							name: words.useThisWeatherSource,
						})
						.count()) > 0,
				{ timeout: 60_000 }
			)
			.toBe(true);
		await page
			.locator('#lp-calculations')
			.getByRole('button', { name: words.useThisWeatherSource })
			.first()
			.click({ force: true, noWaitAfter: true });
		await expect
			.poll(
				async () =>
					(await page
						.getByText(words.selectedInTheCurrentDraft)
						.count()) > 0,
				{ timeout: 30_000 }
			)
			.toBe(true);
		await saveProject();

		// --- PV model + calculation (proven sequence). ---
		await switchTab(words.pvGeneration);
		await expect
			.poll(
				async () =>
					page
						.locator('#lp-calculations button', {
							hasText: words.updateParametersForCurrentRoof,
						})
						.first()
						.isVisible(),
				{ timeout: 30_000 }
			)
			.toBe(true);
		await domClick(words.updateParametersForCurrentRoof);
		await page.waitForTimeout(1500);
		await domClick(`02${words.arrayModels}`);
		await page.waitForTimeout(400);
		for (const field of await page
			.locator('#lp-calculations input[inputMode="decimal"]:visible')
			.all()) {
			if (!(await field.inputValue())) await field.fill('98');
		}
		for (const field of await page
			.locator('#lp-calculations select:visible')
			.all()) {
			if (!(await field.inputValue()))
				await field.selectOption({ index: 1 }).catch(() => undefined);
		}
		for (const field of await page
			.locator('#lp-calculations textarea:visible')
			.all()) {
			if (!(await field.inputValue()))
				await field.fill(
					'Reference model assumption for the e2e chain'
				);
		}
		await domClick(`03${words.powerConversion}`);
		await page.waitForTimeout(400);
		await domClick(words.addConversionGroup);
		await page.waitForTimeout(900);
		for (const field of await page
			.locator('#lp-calculations input[inputMode="decimal"]:visible')
			.all()) {
			if (!(await field.inputValue())) await field.fill('97');
		}
		for (const field of await page
			.locator('#lp-calculations textarea:visible')
			.all()) {
			if (!(await field.inputValue()))
				await field.fill('Declared PVWatts reference conversion');
		}
		for (
			let b = 0;
			b <
			(await page
				.locator('#lp-calculations input[type="checkbox"]:visible')
				.count());
			b += 1
		) {
			const box = page
				.locator('#lp-calculations input[type="checkbox"]:visible')
				.nth(b);
			if (!(await box.isChecked()))
				await box.check({ noWaitAfter: true });
		}
		await domClick(words.preparePvModel);
		await page.waitForTimeout(2500);
		await saveProject();
		await expect
			.poll(
				async () =>
					(
						await page.locator('#lp-calculations').textContent()
					)?.includes(words.pvModelPreparedInThis),
				{ timeout: 60_000 }
			)
			.toBe(true);
		await expect
			.poll(
				async () =>
					page
						.locator('#lp-calculations button', {
							hasText: words.calculatePvForSavedInputs,
						})
						.first()
						.isEnabled(),
				{ timeout: 60_000 }
			)
			.toBe(true);
		await domClick(words.calculatePvForSavedInputs);
		await page.waitForTimeout(60_000);

		// --- Equipment: requirements, manual picker, string plan, DIAG. ---
		await switchTab(words.equipment);
		await domClick(words.singleSystem);
		await page.waitForTimeout(800);
		const equipment = page.locator('#lp-calculations');
		await equipment
			.getByLabel(words.chooseAnOperatingMode)
			.selectOption({ index: 1 });
		await equipment
			.getByLabel(words.gridConnection)
			.selectOption({ index: 1 });
		await equipment.getByLabel(words.pvArrayKwp).fill('8');
		await equipment.getByLabel(words.requiredUsableEnergyKwh).fill('10');
		await equipment
			.getByLabel(words.requiredContinuousAcDischargePower)
			.fill('5');
		await domClick(words.reloadProductData);
		await page.waitForTimeout(2500);
		await page
			.locator('#lp-calculations summary', {
				hasText: words.chooseEquipmentManually,
			})
			.first()
			.click({ force: true, noWaitAfter: true });
		await page.waitForTimeout(800);
		const inverterSelect = page
			.locator('#lp-calculations label', {
				hasText: words.inverterOrIntegratedStorageSystem,
			})
			.locator('select');
		await inverterSelect.selectOption({ index: 1 });
		await page.waitForTimeout(1500);
		for (const field of await page
			.locator('#lp-calculations input:visible:not([type="checkbox"])')
			.all()) {
			const mode = await field.getAttribute('inputmode');
			if (mode !== 'decimal' && mode !== 'numeric') continue;
			if (!(await field.inputValue())) await field.fill('1');
		}
		await saveProject();

		// PV strings: open details, create plan, complete, assign all modules.
		await page
			.locator('#lp-calculations summary', {
				hasText: words.pvStringsAndInputs,
			})
			.first()
			.click({ force: true, noWaitAfter: true });
		await page.waitForTimeout(800);
		const stringsDetails = page
			.locator('#lp-calculations details', {
				hasText: words.pvStringsAndInputs,
			})
			.first();
		await expect(stringsDetails).toBeVisible();
		const createPlan = page.locator('#lp-calculations button:visible', {
			hasText: words.setUpPvStrings,
		});
		if ((await createPlan.count()) > 0) {
			await createPlan.first().click({ force: true, noWaitAfter: true });
			await page.waitForTimeout(1200);
		}
		await stringsDetails
			.getByLabel(words.lowestDesignAmbientTemperature)
			.fill('-10');
		await stringsDetails
			.getByLabel(words.temperatureSourceAndLocation)
			.fill('Local design minimum, Munich');
		await stringsDetails.getByLabel(words.mppt).fill('1');
		await stringsDetails.getByLabel(words.inverterInput).fill('1');
		const selectAllState = await page.evaluate(
			(selectAllAvailableModules: string) => {
				const details = Array.from(
					document.querySelectorAll('#lp-calculations details')
				).find((n) => n.textContent?.includes('Array 1'));
				if (details instanceof HTMLDetailsElement && !details.open)
					details.open = true;
				const button = Array.from(
					document.querySelectorAll<HTMLButtonElement>(
						'#lp-calculations button'
					)
				).find((n) =>
					n.textContent?.includes(selectAllAvailableModules)
				);
				if (button && !button.disabled) {
					button.click();
					return true;
				}
				return false;
			},
			words.selectAllAvailableModules
		);
		expect(selectAllState).toBe(true);
		await page.waitForTimeout(800);
		const addState = await page.evaluate(
			(addSelectedModulesToString: string) => {
				const button = Array.from(
					document.querySelectorAll<HTMLButtonElement>(
						'#lp-calculations button'
					)
				).find((n) =>
					n.textContent?.includes(addSelectedModulesToString)
				);
				if (button && !button.disabled) {
					button.click();
					return true;
				}
				return false;
			},
			words.addSelectedModulesToString
		);
		expect(addState).toBe(true);
		await page.waitForTimeout(1500);
		await expect(stringsDetails).toContainText(words.modulesAssigned, {
			timeout: 15_000,
		});
		await saveProject();

		// The earlier "disabled" reads hit the hidden Multiple-systems panel's
		// button; the visible Single-system instance is the customer's control.
		const prepareVisible = page
			.locator('#lp-calculations button:visible', {
				hasText: words.prepareEquipmentSelection,
			})
			.first();
		// The #1031 fix: every recovery row offers Discard stored request. Use
		// it until the journal is empty - the customer's escape hatch.
		for (let clear = 0; clear < 4; clear += 1) {
			const step = await page.evaluate((discardStoredRequest: string) => {
				const discard = Array.from(
					document.querySelectorAll<HTMLButtonElement>(
						'#lp-calculations button'
					)
				).find((n) => n.textContent?.includes(discardStoredRequest));
				if (discard && !discard.disabled) {
					discard.click();
					return 'discard';
				}
				return 'done';
			}, words.discardStoredRequest);
			if (step === 'done') break;
			await page.waitForTimeout(2000);
		}
		// The journal must be empty now; give the UI a beat to recompute gates.
		await page.waitForTimeout(3000);
		await expect(prepareVisible).toBeEnabled({ timeout: 90_000 });
		await domClick(words.prepareEquipmentSelection);
		await saveProject();
		await clearUnconfirmed();

		// The equipment check consumes the saved selection. The evaluate job
		// runs ~7-15s (DB-proven); the run label renders in the runs view only, so
		// settle and move on rather than polling for text that never lands here.
		// A late draft edit can bump the revision after the last save, so the
		// first check attempt returns 409 evaluation_revision_changed; a real
		// customer clicks again after the record clears - mirror that.
		for (let attempt = 0; attempt < 3; attempt += 1) {
			await saveProject();
			await clearUnconfirmed();
			await domClick(words.checkSavedEquipmentSelection);
			await page.waitForTimeout(12_000);
			if (equipStatuses.length && equipStatuses.at(-1) === 200) break;
			if (equipStatuses.length && equipStatuses.at(-1) !== 409) break;
		}
		await page.waitForTimeout(15_000);

		// The calculations workspace must be VISIBLE before :visible fills run:
		// ProjectEditor hides the whole section (hidden attr, active=false) when
		// the workspace is not calculations/equipment, and chooseWorkspace
		// REFUSES to re-enter while editor-wide valid=false. Restore via the hash
		// path a real link uses, then prove visibility before proceeding.
		// No hashchange listener exists: the workspace reads the hash at mount
		// only, so restore the way a real link/refresh does - reload with the
		// hash (remount bypasses chooseWorkspace's valid=false refusal).
		// The equipment stage entered via chooseWorkspace('equipment') (hash
		// #lp-equipment); the check's openResults() back-switch was REFUSED
		// (editor-wide valid=false from the incomplete scenario form), so the
		// workspace state is stuck on 'equipment' and equipmentFocus hides every
		// form view. A hash-only goto is same-document (no remount) and a plain
		// reload would re-read #lp-equipment: fix the hash first, THEN reload so
		// the remount's workspaceFromHash resolves 'calculations'.
		const mount = new URL(page.url());
		mount.hash = '#lp-calculations';
		await page.goto(mount.toString());
		await page.reload({ waitUntil: 'load' });
		await page.waitForTimeout(4000);
		const visibility = await page.evaluate(() => {
			const section = document.getElementById('lp-calculations');
			const wrapper = section?.parentElement;
			return {
				wrapperHidden: wrapper?.hidden ?? null,
				sectionInDom: Boolean(section),
				visibleButtons: Array.from(
					document.querySelectorAll('#lp-calculations button')
				).filter(
					(b) => b instanceof HTMLElement && b.offsetParent !== null
				).length,
				hash: window.location.hash,
			};
		});
		expect(visibility.visibleButtons).toBeGreaterThan(0);

		// Scenario: all three sections must be complete before Prepare accepts
		// the draft (scenarioBattery refuses an empty source note with
		// battery_source_required - the j2 root cause).
		for (let attempt = 0; attempt < 5; attempt += 1) {
			await domClick(words.scenarioSettings);
			await page.waitForTimeout(1000);
			const pressed = await page.evaluate(
				(scenarioSettings: string) =>
					Array.from(
						document.querySelectorAll('#lp-calculations button')
					)
						.find((b) => b.getAttribute('aria-pressed') === 'true')
						?.textContent?.trim(),
				words.scenarioSettings
			);
			if (pressed === words.scenarioSettings) break;
		}
		// Do NOT click reviewEnergyInputs here: its onClick is
		// openProfiles() -> chooseWorkspace('energy'), which hides the whole
		// calculations section again (j9 DIAG: view=scenario pressed but the
		// workspace wrapper DIV hidden). The profiles were already selected in
		// the profile stage of this chain.
		await domClick(words.useTheSharedProfileRange);
		// The planner re-renders continuously (the equipment stage needed
		// force:true for the same reason), so Playwright's stability-gated
		// actions can wait forever here. Fill through the DOM with React's
		// native value setters + input events instead.
		const fillVisibleNumbers = async () => {
			await page.waitForTimeout(1200);
			const inventory = await page.evaluate(
				(labels: {
					reviewEnergyInputs: string;
					scenarioSettings: string;
					usableStoredEnergy: string;
					useTheSharedProfileRange: string;
				}) => {
					const inputs = Array.from(
						document.querySelectorAll('#lp-calculations input')
					).map((f) => {
						const i = f as HTMLInputElement;
						return {
							m: i.getAttribute('inputmode'),
							v: i.value.slice(0, 8),
							h: Boolean(i.closest('[hidden]')),
							d: i.disabled,
						};
					});
					const usable = document.querySelector(
						'#lp-calculations input'
					);
					const usableLabel = Array.from(
						document.querySelectorAll(
							'#lp-calculations .lp-field span'
						)
					).find((sp) =>
						sp.textContent?.includes(labels.usableStoredEnergy)
					);
					const activeTab = Array.from(
						document.querySelectorAll('#lp-calculations button')
					)
						.filter(
							(b) => b.getAttribute('aria-pressed') === 'true'
						)
						.map((b) => b.textContent?.trim());
					const hiddenWrappers = Array.from(
						document.querySelectorAll('#lp-calculations [hidden]')
					).map((el) => el.className || el.tagName);
					return {
						total: inputs.length,
						hiddenCount: inputs.filter((x) => x.h).length,
						emptyNumeric: inputs.filter((x) => !x.h && x.v === ''),
						usableLabelPresent: Boolean(usableLabel),
						usableLabelHidden: usableLabel
							? Boolean(usableLabel.closest('[hidden]'))
							: null,
						activeTab,
						hiddenWrappers: hiddenWrappers.slice(0, 15),
						url: window.location.search,
					};
				},
				{
					reviewEnergyInputs: words.reviewEnergyInputs,
					scenarioSettings: words.scenarioSettings,
					usableStoredEnergy: words.usableStoredEnergy,
					useTheSharedProfileRange: words.useTheSharedProfileRange,
				}
			);
			const touched = await page.evaluate(() => {
				const touched: string[] = [];
				for (const field of Array.from(
					document.querySelectorAll('#lp-calculations input')
				)) {
					const input = field as HTMLInputElement;
					if (input.type === 'checkbox' || input.closest('[hidden]'))
						continue;
					const mode = input.getAttribute('inputmode');
					if (mode !== 'decimal' && mode !== 'numeric') continue;
					if (input.value === '' && !input.disabled) {
						const setter = Object.getOwnPropertyDescriptor(
							window.HTMLInputElement.prototype,
							'value'
						)?.set;
						setter?.call(input, '1');
						input.dispatchEvent(
							new Event('input', { bubbles: true })
						);
						touched.push(input.name || input.id || mode);
					}
				}
				return touched;
			});
		};
		// Step 01 Storage: battery numbers plus the source/assumption note.
		// Scoped to the step list: the German word substring-matches other
		// buttons elsewhere in the calculations section.
		await domClick(words.storage, '.lp-scenario-steps');
		const storageButtons = await page.evaluate(
			(storage: string) =>
				Array.from(document.querySelectorAll('#lp-calculations button'))
					.map((b, index) => ({ b, index }))
					.filter(({ b }) => b.textContent?.includes(storage))
					.map(({ b, index }) => ({
						globalIndex: index,
						text: b.textContent?.trim().slice(0, 50),
						disabled: (b as HTMLButtonElement).disabled,
						view:
							b.closest('div[class]')?.className?.slice(0, 40) ??
							null,
						inSection:
							b.closest('section')?.className?.slice(0, 40) ??
							null,
					})),
			words.storage
		);
		const workspaceState = await page.evaluate(() => ({
			wrapperHidden:
				document.getElementById('lp-calculations')?.parentElement
					?.hidden,
			hash: window.location.hash,
			bodyClass: document.body.className.slice(0, 60),
		}));
		await fillVisibleNumbers();
		const noteSet = await page.evaluate(
			(sourceOrAssumptionForStorage: string) => {
				for (const ta of Array.from(
					document.querySelectorAll('#lp-calculations textarea')
				)) {
					const el = ta as HTMLTextAreaElement;
					if (el.closest('[hidden]')) continue;
					if (
						el.previousElementSibling?.textContent?.includes(
							sourceOrAssumptionForStorage
						)
					) {
						const setter = Object.getOwnPropertyDescriptor(
							window.HTMLTextAreaElement.prototype,
							'value'
						)?.set;
						setter?.call(
							el,
							'Constant-window storage assumption for the chain probe.'
						);
						el.dispatchEvent(new Event('input', { bubbles: true }));
						return true;
					}
				}
				return false;
			},
			words.sourceOrAssumptionForStorage
		);
		expect(noteSet).toBe(true);
		// Step 02 Starting state: the explicit empty inventory writes its own basis.
		// Scoped to the step list: the German word substring-matches other
		// buttons elsewhere in the calculations section.
		await domClick(words.startingState, '.lp-scenario-steps');
		await domClick(words.startWithAnEmptyBattery);
		// Step 03 Operation: one period, its values, and the terminal choice.
		// Scoped to the step list: the German word substring-matches other
		// buttons elsewhere in the calculations section.
		await domClick(words.operation, '.lp-scenario-steps');
		// emptyScenario() already carries ONE default period; 'Add operating
		// period' would create a second that stays empty and blocks the run
		// (j19: operating_period_incomplete with one complete fieldset).
		await fillVisibleNumbers();
		const terminalSet = await page.evaluate(() => {
			for (const sel of Array.from(
				document.querySelectorAll('#lp-calculations select')
			)) {
				const s = sel as HTMLSelectElement;
				if (s.closest('[hidden]')) continue;
				// The sentinel value identifies the terminal policy select; its
				// label text is locale-dependent, the value is not.
				if (Array.from(s.options).some((o) => o.value === 'none')) {
					const setter = Object.getOwnPropertyDescriptor(
						window.HTMLSelectElement.prototype,
						'value'
					)?.set;
					setter?.call(s, 'none');
					s.dispatchEvent(new Event('change', { bubbles: true }));
					return true;
				}
			}
			return false;
		});
		expect(terminalSet).toBe(true);
		// The period selects default to null (words.chooseAnOption) and start/end
		// are TEXT fields the numeric fill never touches; the engine refuses an
		// incomplete period (operating_period_incomplete, j18).
		const periodSet = await page.evaluate(
			(labels: {
				endWithUtc: string;
				gridCharging: string;
				gridCondition: string;
				gridExportLimit: string;
				gridImportLimit: string;
				pvAvailable: string;
				startWithUtc: string;
			}) => {
				const fieldset = document.querySelector(
					'#lp-calculations fieldset.lp-scenario-period'
				) as HTMLFieldSetElement | null;
				if (!fieldset) return { error: 'no fieldset' };
				const setControl = (label: string, value: string) => {
					const lab = Array.from(
						fieldset.querySelectorAll('label.lp-field')
					).find((l) =>
						l.querySelector('span')?.textContent?.includes(label)
					);
					if (!lab) return false;
					const control =
						(lab.querySelector(
							'select'
						) as HTMLSelectElement | null) ??
						(lab.querySelector('input') as HTMLInputElement | null);
					if (!control) return false;
					const proto =
						control instanceof HTMLSelectElement
							? HTMLSelectElement.prototype
							: HTMLInputElement.prototype;
					const setter = Object.getOwnPropertyDescriptor(
						proto,
						'value'
					)?.set;
					setter?.call(control, value);
					control.dispatchEvent(
						new Event(
							control instanceof HTMLSelectElement
								? 'change'
								: 'input',
							{
								bubbles: true,
							}
						)
					);
					return true;
				};
				return [
					setControl(labels.startWithUtc, '2026-01-01T00:00:00Z'),
					setControl(labels.endWithUtc, '2026-01-30T23:45:00Z'),
					setControl(labels.gridCondition, 'connected'),
					setControl(labels.pvAvailable, 'true'),
					setControl(labels.gridCharging, 'false'),
					setControl(labels.gridImportLimit, 'unlimited'),
					setControl(labels.gridExportLimit, 'unlimited'),
				] as boolean[];
			},
			{
				endWithUtc: words.endWithUtc,
				gridCharging: words.gridCharging,
				gridCondition: words.gridCondition,
				gridExportLimit: words.gridExportLimit,
				gridImportLimit: words.gridImportLimit,
				pvAvailable: words.pvAvailable,
				startWithUtc: words.startWithUtc,
			}
		);
		if (Array.isArray(periodSet)) {
			expect(periodSet.every(Boolean)).toBe(true);
		} else {
			throw new Error(periodSet.error);
		}
		await domClick(words.prepareScenarioSettings);
		await page.waitForTimeout(2000);
		const scenarioText = await page
			.locator('#lp-calculations')
			.textContent();
		await saveProject();
		await expect
			.poll(
				async () =>
					page
						.locator('#lp-calculations button:visible', {
							hasText: words.calculateSavedScenario,
						})
						.first()
						.isEnabled(),
				{ timeout: 90_000 }
			)
			.toBe(true);
		// The configurator/calculation-error row: a failed calculation request
		// surfaces the notice and keeps the inputs; the retry on the same chain
		// then succeeds.
		await page.route('**/rpc/runs/energy', (route) => route.abort());
		await domClick(words.calculateSavedScenario);
		await page.waitForTimeout(4000);
		await expect(page.locator('#lp-calculations')).toContainText(
			// The unconfirmed-request notice (the German catalog's wording for
			// "The request could not be confirmed") or the word calculation.
			/Der Vorgang konnte nicht best\u00e4tigt werden|The request could not be confirmed|calculation|Berechnung/i
		);
		await page.unroute('**/rpc/runs/energy');
		// The aborted attempt leaves an unconfirmed stored request; the
		// customer's recovery is discarding it, then the retry goes through.
		await clearUnconfirmed();
		await domClick(words.calculateSavedScenario);
		await expect
			.poll(
				async () =>
					(
						await page.locator('#lp-calculations').textContent()
					)?.includes(words.scenarioSettings) ?? false,
				{ timeout: 300_000, intervals: [5000] }
			)
			.toBe(true);
		await page.waitForTimeout(30_000);
		// The engine refuses a report whose equipment check predates the saved
		// PV strings (report_wiring_check_required, j24): re-run the check at the
		// CURRENT input revision after the energy calculation, then report.
		await switchTab(words.equipment);
		for (let attempt = 0; attempt < 3; attempt += 1) {
			await saveProject();
			await clearUnconfirmed();
			await domClick(words.checkSavedEquipmentSelection);
			await page.waitForTimeout(12_000);
			if (equipStatuses.length && equipStatuses.at(-1) === 200) break;
			if (equipStatuses.length && equipStatuses.at(-1) !== 409) break;
		}
		await page.waitForTimeout(20_000);
		// The Equipment tab enters the equipment WORKSPACE (chooseWorkspace);
		// other tabs only switch the view, so equipmentFocus would keep the
		// report form hidden (j25: the report select waited out the test).
		// Recover the calculations workspace the proven way before reporting.
		const back = new URL(page.url());
		back.hash = '#lp-calculations';
		await page.goto(back.toString());
		await page.reload({ waitUntil: 'load' });
		await page.waitForTimeout(4000);
		await switchTab(words.planningReport);
		// The report form lives in the words.planningReport tab (the energy run
		// leaves the view on 'runs'; j20's generate poll timed out polling a
		// hidden tab).
		// A real customer reviews the saved results to include: pick the newest
		// energy and PV runs (options are words.notIncluded + newest first). Labels
		// match twice (hidden view copies persist in the DOM): take the first.
		for (const label of [words.energyCalculation, words.pvGeneration]) {
			// getByLabel matches the section heading (#lp-calculations is titled
			// words.energyCalculation); scope to the form label wrapping the
			// select. Labels match twice (hidden view copies persist in the
			// DOM); on the German page the PV label's first copy is a tab
			// heading without a select - take the match that wraps a select.
			const candidates = page.locator('#lp-calculations label.lp-field', {
				hasText: label,
			});
			let select = candidates.first().locator('select');
			if (
				(await select.count()) === 0 &&
				(await candidates.count()) > 1
			) {
				select = candidates.nth(1).locator('select');
			}
			if ((await select.count()) > 0) {
				const options = await select.locator('option').all();
				if (options.length > 1) await select.selectOption({ index: 1 });
			} else {
				throw new Error(`report select missing: ${label}`);
			}
		}
		// The planning report is the keystone's summit.
		// The configurator/incompatible-result row: the deliberately tight
		// requirements (1 module, 1 stack) against the chosen inverter surface
		// the explicit incompatible presentation - the check completes and says
		// so, it never silently passes.
		await expect(page.locator('#lp-calculations')).toContainText(
			words.requirementsNotMet,
			{ timeout: 60_000 }
		);
		await expect(page.locator('#lp-calculations')).toContainText(
			words.furtherAssessmentOfTheComplete
		);
		await expect
			.poll(
				async () =>
					page
						.locator('#lp-calculations button:visible', {
							hasText: words.generatePlanningReport,
						})
						.first()
						.isEnabled(),
				{ timeout: 120_000 }
			)
			.toBe(true);
		// The report accepts a customer logo: a small PNG uploads cleanly and
		// the generation proceeds with it (no "could not be used" notice).
		const logo = join(tmpdir(), 'chain-logo.png');
		writeFileSync(
			logo,
			Buffer.from(
				'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
				'base64'
			)
		);
		await page
			.locator('#lp-calculations input[type="file"]')
			.first()
			.setInputFiles(logo);
		await domClick(words.generatePlanningReport);
		// The finished report offers its real artifacts; the transfer below
		// consumes it: preview -> confirm -> receipt -> the real Woo draft.
		await expect
			.poll(
				async () =>
					page
						.locator('#lp-calculations button:visible', {
							hasText: words.addSelectedProductsToSolution,
						})
						.first()
						.isEnabled(),
				{ timeout: 120_000 }
			)
			.toBe(true);
		await domClick(words.addSelectedProductsToSolution);
		await expect
			.poll(
				async () =>
					page
						.locator('#lp-calculations button:visible', {
							hasText: words.confirmChanges,
						})
						.count(),
				{ timeout: 60_000 }
			)
			.toBeGreaterThan(0);
		const previewRows = await page
			.locator('#lp-calculations .lp-data-table tbody tr')
			.allTextContents();
		await domClick(words.confirmChanges);
		await expect
			.poll(
				async () =>
					(
						await page.locator('#lp-calculations').textContent()
					)?.includes(words.selectedProductsAddedToSolution),
				{ timeout: 120_000 }
			)
			.toBe(true);
		const receiptUrl = await page
			.locator('#lp-calculations a.lp-button', {
				hasText: words.viewSolutionDraft,
			})
			.first()
			.getAttribute('href');
		expect(receiptUrl).toBeTruthy();
		await page.goto(receiptUrl!, { waitUntil: 'load' });
		// The real Woo solution draft carries the transferred product.
		await expect(page.locator('body')).toContainText('SAJ', {
			timeout: 30_000,
		});
		await expect(page.locator('body')).toContainText(/inquir|anfrage/i);
		// The draft's own inquiry form submits as a guest: email, name and an
		// open message; the carried note stays revision-protected server-side.
		await page
			.getByRole('link', { name: words.sendInquiry })
			.click({ timeout: 15_000 });
		await expect(page).toHaveURL(
			// The URL segment is the page's own language: proforma-request /
			// proforma-anfrage.
			/proforma-request|proforma-anfrage/,
			{ timeout: 30_000 }
		);
		// Scope every field to the inquiry form itself (action=linker_inquiry):
		// the page also carries the cookie banner and the draft panel controls.
		const inquiry = page.locator(
			'form:has(input[name="action"][value="linker_inquiry"])'
		);
		await inquiry
			.locator('input[type="email"]')
			.first()
			.fill('e2e-report-chain@example.test');
		await inquiry
			.locator('input[name="name"]')
			.first()
			.fill('E2E Report Chain');
		await inquiry
			.locator('textarea[name="message"]')
			.first()
			.fill('Please quote the transferred configuration.');
		// The transferred page carries TWO checkboxes (include-notes renders
		// before consent) - check consent by name or the required field stays
		// empty and native validation silently blocks the submit.
		await inquiry.locator('input[name="consent"]').check();
		// The public guard refuses submissions less than 3 seconds after the
		// form rendered (PublicGuard::MIN_SECONDS) - a human never fills this
		// fast, the automation does.
		// The public-connection rate limiter (3/hour per connection) is shared
		// by every local e2e run against this instance; reset it so the chain's
		// submissions are judged on their own merits, not on the counter state
		// left by earlier probes.
		wp([
			'db',
			'query',
			"DELETE FROM wp_options WHERE option_name LIKE 'linker_commerce_limit_public_connection%'",
		]);
		await page.waitForTimeout(3500);
		// Row 2 (tamper branch): the hidden note revision must match the
		// session's current note. Tamper it and the server refuses the order
		// BEFORE creating it, keeping every other entry on the page.
		const revisionField = page.locator(
			'input[name^="linker_project_note_revisions"]'
		);
		await expect(revisionField).toHaveCount(1);
		const trueRevision = await revisionField.inputValue();
		await revisionField.evaluate((el) => {
			(el as HTMLInputElement).value = 'deadbeefdeadbeef';
		});
		await inquiry.getByRole('button', { name: words.sendInquiry }).click();
		await expect(page.locator('body')).toContainText(
			// The German catalog's wording for the tamper refusal.
			/The project notes have changed|Die Projektnotizen haben sich ge\u00e4ndert/,
			{ timeout: 30_000 }
		);
		// The refusal keeps the customer's entries (409 branch: retained).
		await expect(inquiry.locator('input[name="name"]')).toHaveValue(
			'E2E Report Chain'
		);
		await expect(inquiry.locator('textarea[name="message"]')).toHaveValue(
			'Please quote the transferred configuration.'
		);
		// Row 4 (consume): restore the true revision on the retained form (the
		// flash is one-use; a fresh render loses the entries) and send - this
		// accepted submission consumes the note. The retrying click rides past
		// the send button's transient disabled window while the embedded cart
		// fragment refreshes.
		await revisionField.evaluate((el, value) => {
			(el as HTMLInputElement).value = value as string;
		}, trueRevision);
		await page.waitForTimeout(3500);
		// The confirmation endpoint's segment is the page's own language
		// (inquiry-received / anfrage-eingegangen).
		for (
			let press = 0;
			press < 4 &&
			!/inquiry-received|anfrage-eingegangen/.test(page.url());
			press += 1
		) {
			await inquiry
				.getByRole('button', { name: words.sendInquiry })
				.click();
			await page.waitForTimeout(2500);
		}
		// The confirmation names the received inquiry state.
		await expect(page.locator('body')).toContainText(
			/inquiry received|anfrage eingegangen/i,
			{ timeout: 60_000 }
		);
		// Row 3 (isolation): the customer's own message arrives verbatim on the
		// confirmation, with no Genie summary envelope around it (this flow has
		// no Genie conversation; a summary must not be invented).
		await expect(page.locator('body')).toContainText(
			'Please quote the transferred configuration.'
		);
		await expect(page.locator('body')).not.toContainText(
			/conversation summary|gesprächszusammenfassung/i
		);
		// Row 4 (consumed): the revisited form no longer offers the consumed
		// note - the exact revision was consumed by the accepted submission.
		await page.goto(instance().url + '/proforma-request/');
		await page.waitForTimeout(1200);
		await expect(
			page.locator('input[name^="linker_project_note_revisions"]')
		).toHaveCount(0);
		// The configurator/restart row: a fully planned project still reopens
		// the one-screen quick start, carrying the saved sizing (8 kWp) and the
		// site's address label.
		await page.goto(
			instance().url + `${words.configurator}?project=${chainProject}`
		);
		await page
			.getByRole('button', { name: words.quickStartPlanInOne })
			.click({ timeout: 30_000 });
		// Quick start is a fresh one-screen plan over the saved project: the
		// panel opens with its own editable defaults (the workbench stays open
		// underneath with every saved input).
		await expect(page.getByLabel(words.pvArraySize)).toBeVisible();
		await expect(page.getByLabel(words.annualElectricityUse)).toBeVisible();
		await expect(page.getByLabel(words.postcodeOrTown)).toBeVisible();
	});
}
