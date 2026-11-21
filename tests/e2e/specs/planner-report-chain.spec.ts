/**
 * EN/DE customer chain: project and roof -> interval sources -> weather and PV
 * preparation -> equipment and strings -> current-input energy calculation ->
 * report downloads -> solution draft -> inquiry and protected project notes.
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { seedConsentCookies } from '../lib/consent';
import { instance, wp } from '../lib/instance';

test.use({ screenshot: 'only-on-failure' });

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

type Lang = 'en' | 'de';

// Labels are read from the current application and shipped German catalog.
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
		availablePvAc: 'Available PV output · AC',
		pointDecimal: 'Point · 12.5',
		arrayModels: 'Array models',
		powerConversion: 'Power conversion',
		syntheticSource: 'Synthetic test data',
		avgPowerKw: 'Average power over each interval · kW',
		timestampIdentifies: 'The timestamp identifies…',
		externalAuxAc: 'External auxiliary load · AC',
		applyProperties: 'Apply properties',
		calculatePvForSavedInputs: 'Calculate PV for saved inputs',
		checkEquipment: 'Check equipment',
		findEquipment: 'Find equipment combinations',
		searchFinished: 'Equipment search finished',
		chooseAnOperatingMode: 'Choose an operating mode',
		chooseEquipmentManually: 'Choose equipment manually',
		comma: 'Comma',
		confirmChanges: 'Confirm changes',
		coordinateReferences: 'Coordinate references',
		createProject: 'Create project',
		decimalSeparator: 'Decimal separator in the file',
		endWithUtc: 'End with UTC or offset',
		energyCalculation: 'Energy calculation',
		expectedRadiationDatabase: 'Expected radiation database',
		firstSourceYear: 'First source year',
		equipmentScope:
			'Further assessment of the complete system is required.',
		reportScope: 'It does not approve the complete installation.',
		generatePlanningReport: 'Generate planning report',
		gridCharging: 'Grid charging allowed',
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
		measurementPoint: 'Measurement point',
		newProject: 'New project',
		notUsed: 'Not used',
		pvArrayKwp: 'PV array',
		pvAvailable: 'PV available in this period',
		pvGeneration: 'PV generation',
		pvModelPreparedInThis: 'PV model prepared in this draft',
		pvStringsAndInputs: 'PV strings and inputs',
		planningReport: 'Planning report',
		preparePvModel: 'Prepare PV model',
		prepareWeatherSettings: 'Prepare weather settings',
		previewColumns: 'Preview columns',
		reloadProductData: 'Reload product data',
		repeatedTimeColumn: 'Repeated-time column · optional',
		requestWeatherForSavedInputs: 'Request weather for saved inputs',
		requiredContinuousAcDischargePower:
			'Required continuous AC discharge power',
		requiredUsableEnergyKwh: 'Required usable energy',
		requirementsNotMet: 'Requirements not met',
		saveProject: 'Save project',
		saved: 'Saved',
		scenarioSettings: 'Scenario settings',
		selectAllAvailableModules: 'Select all available modules',
		selectedInTheCurrentDraft: 'Selected in the current draft',
		selectedProductsAddedToSolution:
			'Selected products added to solution draft.',
		sendInquiry: 'Send inquiry',
		setUpPvStrings: 'Set up PV strings',
		singleSystem: 'Single system',
		sourceAndPermission:
			'Source and permission for permanent private storage',
		sourceLabel: 'Source label',
		sourceOrAssumptionForStorage:
			'Source or assumption for storage parameters',
		sourceTimeZone: 'Source time zone',
		sourceType: 'Source type',
		startWithUtc: 'Start with UTC or offset',
		startWithAnEmptyBattery: 'Start with an empty battery',
		syntheticCalculationYear: 'Synthetic calculation year',
		temperatureSourceAndLocation: 'Temperature source and location',
		terrainHorizon: 'Terrain horizon',
		timestampAndFixedDuration: 'Timestamp and fixed duration',
		timestampColumn: 'Timestamp column',
		totalSiteLoad: 'Total site load',
		updateParametersForCurrentRoof:
			'Update parameters for current roof layout',
		usableStoredEnergy: 'Usable stored energy',
		useRoofCoordinates: 'Use roof coordinates',
		useTheSharedProfileRange: 'Use the shared profile range',
		useThisProfileInThe: 'Use this profile in the open draft',
		useThisWeatherSource: 'Use this weather source',
		useThisPvProfile: 'Use this PV profile',
		valueColumn: 'Value column',
		valueMeaning: 'Value meaning and unit',
		viewSolutionDraft: 'View solution draft',
		weatherSource: 'Weather source',
		country: 'Country',
		address: 'Address or location reference',
		coordinatesAndTimeZone: 'Coordinates and time zone',
		latitude: 'Latitude',
		longitude: 'Longitude',
		sourceReady: 'Source ready',
		irradianceTransposition: 'Irradiance transposition',
		groundReflectance: 'Ground reflectance',
		ashraeCoefficient: 'ASHRAE incidence-angle coefficient b',
		skyDiffuse: 'Retained sky-diffuse irradiance',
		groundDiffuse: 'Retained ground-reflected irradiance',
		spectralFactor: 'Spectral factor',
		soilingFactor: 'Irradiance retained after soiling',
		wiringFactor: 'DC power retained after wiring losses',
		mismatchFactor: 'DC power retained after mismatch losses',
		sapmA: 'SAPM coefficient a',
		sapmB: 'SAPM coefficient b',
		cellDeltaT: 'Cell-to-module ΔT at 1000 W/m²',
		irradianceAssumptions: 'Irradiance and loss assumptions',
		temperatureModelSource:
			'Temperature-model source and mounting conditions',
		overallPvAssumptions: 'Overall PV model assumptions',
		conversionGroup: 'Conversion group 1',
		pvWattsDcPower: 'PVWatts DC reference power',
		nominalEfficiency: 'Nominal conversion efficiency',
		referenceEfficiency: 'PVWatts reference efficiency',
		conversionAssumptions: 'Conversion-model source and assumptions',
		knownPowerCapacity: 'Known power and capacity (optional)',
		equipmentCheckComplete: 'Equipment check complete',
		operatingGoal: 'Operating goal',
		storageParameters: 'Storage parameters',
		chargingPower: 'AC charging power',
		dischargingPower: 'AC discharging power',
		chargingEfficiency: 'Charging efficiency',
		dischargingEfficiency: 'Discharging efficiency',
		internalAuxiliary: 'Internal auxiliary power',
		standingLoss: 'Standing-loss coefficient',
		startingChargeAndSource: 'Starting charge and source',
		reservedStoredEnergy: 'Reserved stored energy',
		finalStoredEnergy: 'Stored energy at the end of the calculation',
		calculateEnergyFlows: 'Calculate energy flows',
		requestUnconfirmed:
			'The request could not be confirmed. Your inputs remain open here.',
		retryOriginalCalculation: 'Retry original calculation request',
		calculationComplete: 'Calculation complete',
		equipmentChecks: 'Equipment checks',
		downloadPdf: 'Download PDF',
		downloadMaterials: 'Download bill of materials (CSV)',
		dismissConfirmed: 'Dismiss confirmed request',
		newQuantity: 'New quantity',
		modulesAssigned: '8 of 8 roof modules assigned',
		configurator: '/solution-configurator/',
		inquiry: '/proforma-request/',
	},
	de: {
		addConversionGroup: 'Umwandlungsgruppe hinzufügen',
		addModuleArray: 'Modulfeld hinzufügen',
		addModuleSpecification: 'Modulspezifikation hinzufügen',
		addRoofFace: 'Dachfläche hinzufügen',
		includedModules: 'Berücksichtigte Module',
		addSelectedModulesToString: 'Ausgewählte Module zum String hinzufügen',
		addSelectedProductsToSolution:
			'Ausgewählte Produkte zum Lösungsentwurf hinzufügen',
		availablePvAc: 'Verfügbare PV-Leistung · AC',
		pointDecimal: 'Punkt · 12.5',
		arrayModels: 'Modelle der Modulfelder',
		powerConversion: 'Umwandlung',
		syntheticSource: 'Synthetische Testdaten',
		avgPowerKw: 'Mittlere Leistung je Intervall · kW',
		timestampIdentifies: 'Der Zeitstempel bezeichnet…',
		externalAuxAc: 'Externer Hilfsverbrauch · AC',
		applyProperties: 'Eigenschaften anwenden',
		calculatePvForSavedInputs: 'PV für gespeicherte Eingaben berechnen',
		checkEquipment: 'Geräte prüfen',
		findEquipment: 'Gerätekombinationen suchen',
		searchFinished: 'Gerätesuche beendet',
		chooseAnOperatingMode: 'Betriebsart auswählen',
		chooseEquipmentManually: 'Geräte manuell auswählen',
		comma: 'Komma',
		confirmChanges: 'Änderungen bestätigen',
		coordinateReferences: 'Koordinatenbezüge',
		createProject: 'Projekt anlegen',
		decimalSeparator: 'Dezimaltrennzeichen in der Datei',
		endWithUtc: 'Ende (UTC oder Zeitversatz)',
		energyCalculation: 'Energieberechnung',
		expectedRadiationDatabase: 'Erwartete Strahlungsdatenbank',
		firstSourceYear: 'Erstes Jahr des Quellzeitraums',
		equipmentScope: 'Die Gesamtanlage muss noch weiter geprüft werden.',
		reportScope: 'Der Bericht erteilt keine Freigabe für die Gesamtanlage.',
		generatePlanningReport: 'Planungsbericht erstellen',
		gridCharging: 'Laden aus dem Netz freigegeben',
		gridCondition: 'Netzzustand',
		gridConnection: 'Netzanschluss',
		gridExportLimit: 'Grenze für die Netzeinspeisung',
		gridImportLimit: 'Grenze für den Netzbezug',
		importAndReviewData: 'Daten importieren und prüfen',
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
		measurementPoint: 'Messpunkt',
		newProject: 'Neues Projekt',
		notUsed: 'Nicht verwendet',
		pvArrayKwp: 'PV-Leistung',
		pvAvailable: 'PV in diesem Zeitraum verfügbar',
		pvGeneration: 'PV-Erzeugung',
		pvModelPreparedInThis: 'PV-Modell in diesem Entwurf vorbereitet',
		pvStringsAndInputs: 'PV-Strings und Eingänge',
		planningReport: 'Planungsbericht',
		preparePvModel: 'PV-Modell vorbereiten',
		prepareWeatherSettings: 'Wettereinstellungen vorbereiten',
		previewColumns: 'Spaltenvorschau',
		reloadProductData: 'Produktdaten neu laden',
		repeatedTimeColumn: 'Spalte für doppelte Ortszeiten · optional',
		requestWeatherForSavedInputs:
			'Wetterdaten für gespeicherte Eingaben abfragen',
		requiredContinuousAcDischargePower:
			'Benötigte AC-Dauerleistung bei Entladung',
		requiredUsableEnergyKwh: 'Benötigte nutzbare Speicherenergie',
		requirementsNotMet: 'Anforderungen nicht erfüllt',
		saveProject: 'Projekt speichern',
		saved: 'Gespeichert',
		scenarioSettings: 'Szenarioeinstellungen',
		selectAllAvailableModules: 'Alle zuweisbaren Module auswählen',
		selectedInTheCurrentDraft: 'Im aktuellen Projektentwurf ausgewählt',
		selectedProductsAddedToSolution:
			'Die ausgewählten Produkte wurden zum Lösungsentwurf hinzugefügt.',
		sendInquiry: 'Anfrage senden',
		setUpPvStrings: 'PV-Strings planen',
		singleSystem: 'Einzelnes System',
		sourceAndPermission:
			'Herkunft und Berechtigung zur dauerhaften privaten Speicherung',
		sourceLabel: 'Bezeichnung der Datenquelle',
		sourceOrAssumptionForStorage:
			'Quelle oder Annahme für die Speicherparameter',
		sourceTimeZone: 'Zeitzone der Quelldaten',
		sourceType: 'Art der Datenquelle',
		startWithUtc: 'Beginn (UTC oder Zeitversatz)',
		startWithAnEmptyBattery: 'Anfangsenergie auf null setzen',
		syntheticCalculationYear: 'Synthetisches Berechnungsjahr',
		temperatureSourceAndLocation:
			'Quelle der Temperaturangabe und Standort',
		terrainHorizon: 'Geländehorizont',
		timestampAndFixedDuration: 'Zeitstempel und feste Dauer',
		timestampColumn: 'Zeitstempelspalte',
		totalSiteLoad: 'Gesamte Standortlast',
		updateParametersForCurrentRoof:
			'Parameter an aktuelle Dachbelegung anpassen',
		usableStoredEnergy: 'Nutzbare Speicherenergie',
		useRoofCoordinates: 'Dachkoordinaten übernehmen',
		useTheSharedProfileRange: 'Gemeinsamen Profilzeitraum übernehmen',
		useThisProfileInThe: 'Profil im offenen Projektentwurf verwenden',
		useThisWeatherSource: 'Diese Wetterquelle verwenden',
		useThisPvProfile: 'Dieses PV-Profil verwenden',
		valueColumn: 'Wertespalte',
		valueMeaning: 'Bedeutung und Einheit der Werte',
		viewSolutionDraft: 'Lösungsentwurf ansehen',
		weatherSource: 'Wetterquelle',
		country: 'Land',
		address: 'Adresse oder Standortbezeichnung',
		coordinatesAndTimeZone: 'Koordinaten und Zeitzone',
		latitude: 'Breitengrad',
		longitude: 'Längengrad',
		sourceReady: 'Quelle bereit',
		irradianceTransposition:
			'Umrechnung der Einstrahlung auf die Modulebene',
		groundReflectance: 'Bodenreflexionsgrad',
		ashraeCoefficient: 'ASHRAE-Koeffizient b für den Einfallswinkel',
		skyDiffuse: 'Verbleibender Anteil der Himmelsdiffusstrahlung',
		groundDiffuse: 'Verbleibende bodenreflektierte Einstrahlung',
		spectralFactor: 'Spektraler Korrekturfaktor',
		soilingFactor: 'Verbleibende Einstrahlung nach Verschmutzung',
		wiringFactor: 'Verbleibende DC-Leistung nach Leitungsverlusten',
		mismatchFactor: 'Verbleibende DC-Leistung nach Mismatch-Verlusten',
		sapmA: 'SAPM-Koeffizient a',
		sapmB: 'SAPM-Koeffizient b',
		cellDeltaT: 'Zell-Modul-Temperaturdifferenz ΔT bei 1000 W/m²',
		irradianceAssumptions: 'Annahmen zu Einstrahlung und Verlusten',
		temperatureModelSource:
			'Quelle des Temperaturmodells und Montagebedingungen',
		overallPvAssumptions: 'Übergreifende Annahmen des PV-Modells',
		conversionGroup: 'Umwandlungsgruppe 1',
		pvWattsDcPower: 'PVWatts-DC-Referenzleistung',
		nominalEfficiency: 'Nennwirkungsgrad der Umwandlung',
		referenceEfficiency: 'PVWatts-Referenzwirkungsgrad',
		conversionAssumptions: 'Quelle und Annahmen des Umwandlungsmodells',
		knownPowerCapacity: 'Bekannte Leistung und Kapazität (optional)',
		equipmentCheckComplete: 'Prüfung der Geräteauswahl abgeschlossen',
		operatingGoal: 'Betriebsziel',
		storageParameters: 'Speicherparameter',
		chargingPower: 'AC-Ladeleistung',
		dischargingPower: 'AC-Entladeleistung',
		chargingEfficiency: 'Ladewirkungsgrad',
		dischargingEfficiency: 'Entladewirkungsgrad',
		internalAuxiliary: 'Interner Hilfsverbrauch',
		standingLoss: 'Koeffizient der zeitabhängigen Speicherverluste',
		startingChargeAndSource: 'Anfangsladung und Herkunft',
		reservedStoredEnergy: 'Energiereserve im Speicher',
		finalStoredEnergy: 'Speicherenergie am Ende der Berechnung',
		calculateEnergyFlows: 'Energieflüsse berechnen',
		requestUnconfirmed:
			'Der Vorgang konnte nicht bestätigt werden. Ihre Eingaben bleiben hier geöffnet.',
		retryOriginalCalculation:
			'Ursprünglichen Berechnungsauftrag erneut senden',
		calculationComplete: 'Berechnung abgeschlossen',
		equipmentChecks: 'Prüfung der Geräteauswahl',
		downloadPdf: 'PDF herunterladen',
		downloadMaterials: 'Stückliste herunterladen (CSV)',
		dismissConfirmed: 'Bestätigten Vorgang ausblenden',
		newQuantity: 'Neue Menge',
		modulesAssigned: '8 von 8 Dachmodulen zugeordnet',
		configurator: '/de/loesungskonfigurator/',
		inquiry: '/de/proforma-anfrage/',
	},
} as const;

function num(lang: Lang, value: string): string {
	return 'de' === lang ? value.replace('.', ',') : value;
}

async function openDetails(summary: Locator): Promise<Locator> {
	const details = summary.locator('..');
	await expect(summary).toBeVisible();
	if ((await details.getAttribute('open')) === null) await summary.click();
	await expect(details).toHaveAttribute('open', '');
	return details;
}

async function downloadedBytes(page: Page, button: Locator): Promise<Buffer> {
	const pending = page.waitForEvent('download');
	await button.click();
	const download = await pending;
	expect(await download.failure()).toBeNull();
	const stream = await download.createReadStream();
	expect(stream).not.toBeNull();
	const chunks: Buffer[] = [];
	for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
	return Buffer.concat(chunks);
}

for (const lang of ['en', 'de'] as const) {
	const words = WORDS[lang];
	test(`${lang}: the full planner chain: report, transfer and the Woo solution draft`, async ({
		page,
	}) => {
		test.setTimeout(900_000);
		page.setDefaultTimeout(15_000);
		const calculation = page.locator('#lp-calculations');
		const result = calculation.locator('.lp-run-content');
		const chapter = async (
			hash:
				| 'lp-site'
				| 'lp-design'
				| 'lp-load'
				| 'lp-equipment'
				| 'lp-calculations'
		) => {
			const section = {
				'lp-site': 'site',
				'lp-design': 'design',
				'lp-load': 'energy',
				'lp-equipment': 'equipment',
				'lp-calculations': 'calculations',
			}[hash];
			const mobile = page.locator('.lp-mobile-workspace');
			if (await mobile.isVisible()) await mobile.selectOption(section);
			else
				await page
					.locator(`.lp-project-aside a[href="#${hash}"]`)
					.click();
			await expect(page.locator('.lp-project')).toHaveAttribute(
				'data-workspace',
				section
			);
		};
		const switchTab = async (name: string) => {
			const tab = calculation
				.locator('.lp-energy-switch')
				.getByRole('button', { name, exact: true });
			await tab.click();
			await expect(tab).toHaveAttribute('aria-pressed', 'true');
		};
		const saveProject = async () => {
			const save = page.getByRole('button', {
				name: words.saveProject,
				exact: true,
			});
			await expect(save).toBeEnabled();
			await save.click();
			await expect(page.locator('.lp-save-state')).toContainText(
				words.saved,
				{ timeout: 90_000 }
			);
			await expect(save).toBeDisabled();
		};

		await page.goto(instance().url + words.configurator);
		await expect(
			page.locator('.lp-index-heading button[aria-label]')
		).toBeEnabled();
		if (!(await page.locator('select[name="system_scope"]').isVisible())) {
			await page
				.getByRole('button', { name: words.newProject, exact: true })
				.click();
		}
		await page.locator('select[name="solar_entry"]').selectOption('known');
		await page.locator('input[name="project_title"]').fill('Report chain');
		await page
			.getByRole('button', { name: words.createProject, exact: true })
			.click();
		await expect(page).toHaveURL(/project=/, { timeout: 60_000 });
		const chainProject = new URL(page.url()).searchParams.get('project')!;

		await chapter('lp-site');
		const site = page.locator('#lp-site');
		await site
			.getByRole('combobox', { name: words.country, exact: true })
			.selectOption('DE');
		await site
			.getByLabel(words.address, { exact: true })
			.fill('Triftstrasse 5');
		await openDetails(
			site.getByText(words.coordinatesAndTimeZone, { exact: true })
		);
		await site.getByLabel(words.latitude).fill(num(lang, '48.1689'));
		await site.getByLabel(words.longitude).fill(num(lang, '11.5844'));
		await page
			.locator('#lp-notes textarea')
			.fill('8 kWp roof with battery, Munich, south-facing');

		await chapter('lp-design');
		await openDetails(
			page.locator('#lp-design .lp-design-imports > summary')
		);
		await page
			.locator('#lp-design button.lp-button')
			.getByText(words.addRoofFace, { exact: true })
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
		await faceForm.locator('[name="export"]').selectOption('permitted');
		await faceForm.locator('button[type="submit"]').click();
		await expect(faceForm).toBeHidden();

		await page
			.locator('#lp-design')
			.getByRole('button', {
				name: words.coordinateReferences,
				exact: true,
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
		await coordForm
			.locator('select[name="north_source"]')
			.selectOption({ index: 1 });
		await coordForm
			.locator('select[name="anchor_source"]')
			.selectOption({ index: 1 });
		await coordForm.locator('button[type="submit"]').click();

		await page
			.locator('#lp-design')
			.getByRole('button', {
				name: words.addModuleSpecification,
				exact: true,
			})
			.click();
		const moduleForm = page.locator('#lp-design form');
		await moduleForm.locator('[name="panel_length_mm"]').fill('1800');
		await moduleForm.locator('[name="panel_width_mm"]').fill('1100');
		await moduleForm.locator('[name="panel_thickness_mm"]').fill('30');
		await moduleForm.locator('[name="panel_power_w"]').fill('430');
		await moduleForm.locator('details > summary').click();
		await moduleForm
			.locator('[name="panel_temperature_coefficient"]')
			.fill('-0.3');
		await moduleForm.locator('[name="panel_voc_v"]').fill('42');
		await moduleForm.locator('[name="panel_vmpp_v"]').fill('35');
		await moduleForm.locator('[name="panel_isc_a"]').fill('13');
		await moduleForm.locator('[name="panel_impp_a"]').fill('12.3');
		await moduleForm
			.locator('[name="panel_max_system_voltage_v"]')
			.fill('1000');
		await moduleForm
			.locator('[name="panel_alpha_isc_pct_per_c"]')
			.fill('0.04');
		await moduleForm
			.locator('[name="panel_beta_voc_pct_per_c"]')
			.fill('-0.25');
		await moduleForm
			.locator('[name="panel_cell_technology"]')
			.selectOption('monocrystalline');
		await moduleForm.locator('button[type="submit"]').click();
		await page
			.locator('#lp-design')
			.getByRole('button', { name: words.addModuleArray, exact: true })
			.click();
		const arrayForm = page.locator('#lp-design form');
		await page.locator('#lp-design .lp-view-switch button').last().click();
		const position = await openDetails(
			page.locator('.lp-plan-position > summary')
		);
		await position.locator('input').nth(0).fill('1');
		await position.locator('input').nth(1).fill('1');
		await position.getByRole('button').click();
		await openDetails(arrayForm.locator('.lp-array-settings > summary'));
		await arrayForm.locator('[name="name"]').fill('Main array');
		await arrayForm.locator('[name="module"]').selectOption({ index: 0 });
		await arrayForm.locator('[name="rows"]').fill('2');
		await arrayForm.locator('[name="columns"]').fill('4');
		await arrayForm.locator('[name="rotation"]').fill('0');
		await arrayForm.locator('[name="tilt"]').fill('91');
		await arrayForm
			.getByRole('button', { name: words.applyProperties, exact: true })
			.click();
		await expect(arrayForm.locator('[name="tilt"]')).toHaveAttribute(
			'aria-invalid',
			'true'
		);
		await expect(page.locator('#lp-design')).not.toContainText(
			`${words.includedModules}8`
		);
		await arrayForm.locator('[name="tilt"]').fill('0');
		await arrayForm.locator('[name="column_gap"]').fill(num(lang, '0.02'));
		await arrayForm.locator('[name="row_gap"]').fill(num(lang, '0.1'));
		await arrayForm.locator('[name="height"]').fill(num(lang, '0.1'));
		await arrayForm
			.locator('[name="mounting"]')
			.fill('Fixed rails on roof hooks');
		await arrayForm
			.getByRole('button', { name: words.applyProperties, exact: true })
			.click();
		await expect(page.locator('#lp-design')).toContainText(
			`${words.includedModules}8`
		);
		await saveProject();

		// Import three declared synthetic sources through the real mapping and review.
		await chapter('lp-load');
		const profiles = page.locator('#lp-profiles');
		const importProfile = async (measurement: string, label: string) => {
			const rows = ['timestamp,power'];
			const start = Date.UTC(2026, 0, 1);
			for (let index = 0; index < 30 * 96; index += 1) {
				const hour = ((index % 96) * 15) / 60;
				const power =
					40 + 30 * Math.sin(((hour - 6) / 24) * 2 * Math.PI);
				rows.push(
					`${new Date(start + index * 900_000).toISOString().slice(0, 19)},${Math.round(Math.max(5, power) * 1000) / 1000}`
				);
			}
			await profiles
				.getByRole('button', {
					name: words.importIntervalData,
					exact: true,
				})
				.click();
			await profiles.locator('input[type="file"]').setInputFiles({
				name: `${label}.csv`,
				mimeType: 'text/csv',
				buffer: Buffer.from(rows.join('\n')),
			});
			await profiles
				.locator('select')
				.first()
				.selectOption({ label: words.comma });
			await profiles
				.getByRole('button', {
					name: words.previewColumns,
					exact: true,
				})
				.click();
			await profiles
				.getByRole('combobox', {
					name: words.timestampColumn,
					exact: true,
				})
				.selectOption({ label: 'timestamp' });
			await profiles
				.getByRole('combobox', { name: words.valueColumn, exact: true })
				.selectOption({ label: 'power' });
			await profiles
				.getByRole('combobox', {
					name: words.measurementPoint,
					exact: true,
				})
				.selectOption({ label: measurement });
			await profiles
				.getByRole('combobox', {
					name: words.valueMeaning,
					exact: true,
				})
				.selectOption({ label: words.avgPowerKw });
			await profiles
				.getByRole('combobox', {
					name: words.decimalSeparator,
					exact: true,
				})
				.selectOption({ label: words.pointDecimal });
			await profiles
				.getByRole('combobox', { name: words.sourceType, exact: true })
				.selectOption({ label: words.syntheticSource });
			await profiles
				.getByRole('combobox', {
					name: words.intervalBoundaries,
					exact: true,
				})
				.selectOption({ label: words.timestampAndFixedDuration });
			await profiles
				.getByRole('combobox', {
					name: words.timestampIdentifies,
					exact: true,
				})
				.selectOption('start');
			await profiles.getByLabel(words.intervalDuration).fill('15');
			await profiles
				.getByRole('combobox', {
					name: words.sourceTimeZone,
					exact: true,
				})
				.selectOption({ label: 'UTC' });
			await profiles
				.getByRole('combobox', {
					name: words.repeatedTimeColumn,
					exact: true,
				})
				.selectOption({ label: words.notUsed });
			await profiles
				.getByLabel(words.sourceLabel, { exact: true })
				.fill(label);
			await profiles
				.getByLabel(words.sourceAndPermission)
				.fill('Generated for the e2e chain');
			await profiles
				.getByRole('button', {
					name: words.importAndReviewData,
					exact: true,
				})
				.click();
			await profiles
				.getByRole('button', {
					name: words.useThisProfileInThe,
					exact: true,
				})
				.click();
			await expect(
				profiles
					.locator('.lp-selected-profile')
					.filter({ hasText: label })
			).toBeVisible();
		};
		await importProfile(words.totalSiteLoad, 'E2E synthetic load');
		await importProfile(words.availablePvAc, 'E2E synthetic pv');
		await importProfile(words.externalAuxAc, 'E2E synthetic aux');

		// Weather acquisition and source selection remain separate customer choices.
		await chapter('lp-calculations');
		await switchTab(words.weatherSource);
		await calculation
			.getByRole('button', {
				name: words.useRoofCoordinates,
				exact: true,
			})
			.click();
		await calculation.getByLabel(words.firstSourceYear).fill('2005');
		await calculation.getByLabel(words.lastSourceYear).fill('2023');
		await calculation
			.getByRole('combobox', {
				name: words.expectedRadiationDatabase,
				exact: true,
			})
			.selectOption('PVGIS-SARAH3');
		await calculation
			.getByRole('combobox', { name: words.terrainHorizon, exact: true })
			.selectOption('true');
		// Align the synthetic weather timeline with the imported 2026 load data.
		await calculation
			.getByLabel(words.syntheticCalculationYear)
			.fill('2026');
		await calculation
			.getByRole('button', {
				name: words.prepareWeatherSettings,
				exact: true,
			})
			.click();
		await saveProject();
		await calculation
			.getByRole('button', {
				name: words.requestWeatherForSavedInputs,
				exact: true,
			})
			.click();
		await expect(
			result.locator('.lp-run-heading [role="status"]')
		).toHaveText(words.sourceReady, { timeout: 240_000 });
		const useWeather = result.getByRole('button', {
			name: words.useThisWeatherSource,
			exact: true,
		});
		await expect(useWeather).toBeEnabled();
		await useWeather.click();
		await expect(result).toContainText(words.selectedInTheCurrentDraft);
		await saveProject();

		await switchTab(words.pvGeneration);
		await calculation
			.getByRole('button', {
				name: words.updateParametersForCurrentRoof,
				exact: true,
			})
			.click();
		await calculation
			.locator('.lp-scenario-steps')
			.getByRole('button', { name: words.arrayModels })
			.click();
		const arrayModel = calculation.locator('.lp-pv-parameters').filter({
			has: page.getByRole('heading', {
				name: 'Main array',
				exact: true,
			}),
		});
		await arrayModel
			.getByRole('combobox', {
				name: words.irradianceTransposition,
				exact: true,
			})
			.selectOption('isotropic');
		for (const [label, value] of [
			[words.groundReflectance, '20'],
			[words.ashraeCoefficient, '0.05'],
			[words.skyDiffuse, '98'],
			[words.groundDiffuse, '98'],
			[words.spectralFactor, '98'],
			[words.soilingFactor, '98'],
			[words.wiringFactor, '98'],
			[words.mismatchFactor, '98'],
			[words.sapmA, '-3.56'],
			[words.sapmB, '-0.075'],
			[words.cellDeltaT, '3'],
		] as const) {
			await arrayModel.getByLabel(label).fill(num(lang, value));
		}
		await arrayModel
			.getByLabel(words.irradianceAssumptions, { exact: true })
			.fill(
				'Declared unshaded reference: 20% albedo, ASHRAE b=0.05, 98% retained factors.'
			);
		await arrayModel
			.getByLabel(words.temperatureModelSource, { exact: true })
			.fill(
				'SAPM open-rack glass/polymer reference coefficients; declared test assumption.'
			);
		await calculation
			.getByLabel(words.overallPvAssumptions, { exact: true })
			.fill(
				'Synthetic engineering reference for the E2E chain; no manufacturer performance claim.'
			);
		await calculation
			.locator('.lp-scenario-steps')
			.getByRole('button', { name: words.powerConversion })
			.click();
		await calculation
			.getByRole('button', {
				name: words.addConversionGroup,
				exact: true,
			})
			.click();
		const converter = calculation.locator('.lp-pv-parameters').filter({
			has: page.getByRole('heading', {
				name: words.conversionGroup,
				exact: true,
			}),
		});
		await converter.getByLabel('Main array', { exact: true }).check();
		await converter.getByLabel(words.pvWattsDcPower).fill('5000');
		await converter.getByLabel(words.nominalEfficiency).fill('97');
		await converter.getByLabel(words.referenceEfficiency).fill('96');
		await converter
			.getByLabel(words.conversionAssumptions, { exact: true })
			.fill(
				'Declared PVWatts reference conversion for this synthetic test.'
			);
		await calculation
			.getByRole('button', { name: words.preparePvModel, exact: true })
			.click();
		await expect(calculation).toContainText(words.pvModelPreparedInThis);
		await saveProject();
		await calculation
			.getByRole('button', {
				name: words.calculatePvForSavedInputs,
				exact: true,
			})
			.click();
		await expect(
			result.locator('.lp-run-heading [role="status"]')
		).toHaveText(words.sourceReady, { timeout: 240_000 });

		// Use the generated source in the energy calculation as well as its report.
		await result
			.getByRole('button', { name: words.useThisPvProfile, exact: true })
			.click();
		await expect(
			result.getByRole('button', {
				name: words.selectedInTheCurrentDraft,
				exact: true,
			})
		).toBeDisabled();

		// Keep the fixture's first real converter and its intentionally insufficient
		// storage selection. The result must name that selection and its failed checks.
		await chapter('lp-equipment');
		const equipment = calculation.locator('#lp-equipment');
		await equipment
			.getByRole('button', { name: words.singleSystem, exact: true })
			.click();
		await equipment
			.getByRole('combobox', {
				name: words.chooseAnOperatingMode,
				exact: true,
			})
			.selectOption('grid_connected');
		await equipment
			.getByRole('combobox', { name: words.gridConnection, exact: true })
			.selectOption('1');
		await equipment.getByLabel(words.pvArrayKwp).fill('8');
		const requirements = await openDetails(
			equipment.getByText(words.knownPowerCapacity, { exact: true })
		);
		await expect(
			requirements.getByLabel(words.requiredUsableEnergyKwh)
		).toHaveValue('');
		await expect(
			requirements.getByLabel(words.requiredContinuousAcDischargePower)
		).toHaveValue('');
		const searchRequest = page.waitForRequest(
			(request) =>
				request.url().endsWith('/rpc/runs/find-equipment') &&
				request.method() === 'POST'
		);
		await equipment
			.getByRole('button', { name: words.findEquipment, exact: true })
			.click();
		const submittedSearch = (await searchRequest).postDataJSON();
		expect(
			submittedSearch.inputs.equipment_setup.required_usable_kwh
		).toBeNull();
		expect(
			submittedSearch.inputs.equipment_setup.required_discharge_ac_kw
		).toBeNull();
		await expect(result).toContainText(words.searchFinished, {
			timeout: 180_000,
		});
		await chapter('lp-equipment');
		await openDetails(
			equipment.getByText(words.knownPowerCapacity, { exact: true })
		);
		await requirements.getByLabel(words.requiredUsableEnergyKwh).fill('10');
		await requirements
			.getByLabel(words.requiredContinuousAcDischargePower)
			.fill('5');
		await equipment
			.getByRole('button', { name: words.reloadProductData, exact: true })
			.click();
		const manual = await openDetails(
			equipment.getByText(words.chooseEquipmentManually, { exact: true })
		);
		const inverterSelect = manual.getByRole('combobox', {
			name: words.inverterOrIntegratedStorageSystem,
			exact: true,
		});
		await expect(inverterSelect.locator('option')).not.toHaveCount(1, {
			timeout: 60_000,
		});
		await inverterSelect.selectOption({ index: 1 });
		const selectedInverter = (await inverterSelect
			.locator('option:checked')
			.textContent())!.trim();
		const selectedInverterId = await inverterSelect.inputValue();
		expect(selectedInverter).toContain('SAJ');
		await manual
			.locator('input[name="equipment_setup.modules_per_stack"]')
			.fill('1');
		await manual
			.locator('input[name="equipment_setup.parallel_stacks"]')
			.fill('1');

		const strings = await openDetails(
			equipment.getByText(words.pvStringsAndInputs, { exact: true })
		);
		await strings
			.getByRole('button', { name: words.setUpPvStrings, exact: true })
			.click();
		await strings
			.getByLabel(words.lowestDesignAmbientTemperature)
			.fill('-10');
		await strings
			.getByLabel(words.temperatureSourceAndLocation, { exact: true })
			.fill('Local design minimum, Munich');
		await strings.getByLabel(words.mppt, { exact: true }).fill('1');
		await strings
			.getByLabel(words.inverterInput, { exact: true })
			.fill('1');
		const arrayDetails = strings
			.locator('details')
			.filter({
				has: page.getByText(words.selectAllAvailableModules, {
					exact: true,
				}),
			})
			.first();
		await openDetails(arrayDetails.locator(':scope > summary'));
		await arrayDetails
			.getByRole('button')
			.filter({ hasText: words.selectAllAvailableModules })
			.click();
		await strings
			.getByRole('button', {
				name: words.addSelectedModulesToString,
				exact: true,
			})
			.click();
		await expect(strings).toContainText(words.modulesAssigned);
		// Check equipment submits the current draft; no preparation/save cycle.
		const equipmentRequest = page.waitForRequest(
			(request) =>
				request.url().endsWith('/rpc/runs/check-equipment') &&
				request.method() === 'POST'
		);
		await manual
			.getByRole('button', { name: words.checkEquipment, exact: true })
			.click();
		const submittedEquipment = (await equipmentRequest).postDataJSON();
		expect(
			String(
				submittedEquipment.inputs.equipment_setup.inverter_product_id
			)
		).toBe(selectedInverterId);
		await expect(result).toContainText(words.equipmentCheckComplete, {
			timeout: 120_000,
		});
		await expect(result).toContainText(selectedInverter);
		await expect(result).toContainText(words.requirementsNotMet);
		await expect(result).toContainText(words.equipmentScope);

		// The compact form authors explicit independent-AC simulation assumptions.
		await switchTab(words.scenarioSettings);
		const scenario = calculation.locator('fieldset.lp-brief-fields');
		await expect(scenario).toBeVisible();
		await scenario
			.getByRole('combobox', { name: words.operatingGoal, exact: true })
			.selectOption('self');
		const storage = await openDetails(
			scenario.getByText(words.storageParameters, { exact: true })
		);
		for (const [label, value] of [
			[words.usableStoredEnergy, '10'],
			[words.chargingPower, '5'],
			[words.dischargingPower, '5'],
			[words.chargingEfficiency, '95'],
			[words.dischargingEfficiency, '95'],
			[words.internalAuxiliary, '0'],
			[words.standingLoss, '0'],
		] as const)
			await storage
				.getByRole('textbox', {
					name: new RegExp('^' + label + '(?:\\s|$)'),
				})
				.fill(value);
		const simulationNote =
			'Declared independent-AC test simulation: 10 kWh, 5 kW each direction, 95% efficiencies, zero internal auxiliary and standing loss; not selected-product performance.';
		await storage
			.getByLabel(words.sourceOrAssumptionForStorage, { exact: true })
			.fill(simulationNote);
		const initial = await openDetails(
			scenario.getByText(words.startingChargeAndSource, { exact: true })
		);
		await initial
			.getByRole('button', {
				name: words.startWithAnEmptyBattery,
				exact: true,
			})
			.click();
		await scenario
			.getByRole('button', {
				name: words.useTheSharedProfileRange,
				exact: true,
			})
			.click();
		const period = scenario.locator('fieldset.lp-scenario-period');
		await expect(
			period.getByLabel(words.startWithUtc, { exact: true })
		).toHaveValue(/^2026-01-01T00:00:00(?:\.0+)?(?:Z|\+00:00)$/);
		await expect(
			period.getByLabel(words.endWithUtc, { exact: true })
		).toHaveValue(/^2026-01-31T00:00:00(?:\.0+)?(?:Z|\+00:00)$/);
		await period
			.getByRole('combobox', { name: words.gridCondition, exact: true })
			.selectOption('connected');
		await period.getByLabel(words.reservedStoredEnergy).fill('0');
		await period
			.getByRole('combobox', { name: words.pvAvailable, exact: true })
			.selectOption('true');
		await period
			.getByRole('combobox', { name: words.gridCharging, exact: true })
			.selectOption('false');
		await period
			.getByRole('combobox', { name: words.gridImportLimit, exact: true })
			.selectOption('unlimited');
		await period
			.getByRole('combobox', { name: words.gridExportLimit, exact: true })
			.selectOption('unlimited');
		await scenario
			.getByRole('combobox', {
				name: words.finalStoredEnergy,
				exact: true,
			})
			.selectOption('none');
		await expect(
			scenario.getByRole('textbox', {
				name: words.sourceOrAssumptionForStorage,
				exact: true,
			})
		).toHaveValue(simulationNote);

		// A failed current-input submission keeps the draft and offers the original
		// durable request for retry; no stored request is silently discarded.
		await page.route('**/rpc/runs/calculate', (route) => route.abort());
		await calculation
			.getByRole('button', {
				name: words.calculateEnergyFlows,
				exact: true,
			})
			.click();
		await expect(calculation).toContainText(words.requestUnconfirmed);
		await expect(
			scenario.getByRole('textbox', {
				name: words.sourceOrAssumptionForStorage,
				exact: true,
			})
		).toHaveValue(simulationNote);
		await page.unroute('**/rpc/runs/calculate');
		const recovery = calculation.locator('.lp-energy-recovery-row').filter({
			hasNot: page.getByRole('button', {
				name: words.dismissConfirmed,
				exact: true,
			}),
		});
		await expect(recovery).toHaveCount(1);
		await recovery
			.getByRole('button', {
				name: words.retryOriginalCalculation,
				exact: true,
			})
			.click();
		await expect(
			result.getByRole('heading', {
				name: words.calculationComplete,
				exact: true,
			})
		).toBeVisible({ timeout: 300_000 });

		// The report's wiring check must belong to the current saved inputs.
		await chapter('lp-equipment');
		await manual
			.getByRole('button', { name: words.checkEquipment, exact: true })
			.click();
		await expect(result).toContainText(words.equipmentCheckComplete, {
			timeout: 120_000,
		});
		await expect(result).toContainText(words.requirementsNotMet);
		await expect(result).toContainText(selectedInverter);
		await chapter('lp-calculations');
		await expect(page).toHaveURL(/energy_view=reports/);
		const report = calculation.locator('section.lp-scenario-block').filter({
			has: page.getByRole('heading', {
				name: words.planningReport,
				exact: true,
			}),
		});
		await expect(report).toBeVisible();
		for (const label of [
			words.energyCalculation,
			words.pvGeneration,
			words.equipmentChecks,
		]) {
			const select = report.getByRole('combobox', {
				name: label,
				exact: true,
			});
			await expect(select.locator('option')).not.toHaveCount(1, {
				timeout: 120_000,
			});
			await select.selectOption({ index: 1 });
			await expect(select).not.toHaveValue('');
		}
		await report.locator('input[type="file"]').setInputFiles({
			name: 'chain-logo.png',
			mimeType: 'image/png',
			buffer: Buffer.from(
				'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
				'base64'
			),
		});
		await report
			.getByRole('button', {
				name: words.generatePlanningReport,
				exact: true,
			})
			.click();
		await expect(
			result.getByRole('button', { name: words.downloadPdf, exact: true })
		).toBeEnabled({ timeout: 120_000 });
		await expect(result).toContainText(selectedInverter);
		await expect(result).toContainText(words.requirementsNotMet);
		await expect(result).toContainText(words.reportScope);
		const pdf = await downloadedBytes(
			page,
			result.getByRole('button', { name: words.downloadPdf, exact: true })
		);
		expect(pdf.subarray(0, 5).toString()).toBe('%PDF-');
		const materials = await downloadedBytes(
			page,
			result.getByRole('button', {
				name: words.downloadMaterials,
				exact: true,
			})
		);
		expect(materials.toString('utf8')).toContain(
			selectedInverter.replace(/^SAJ\s+/, '')
		);

		await result
			.getByRole('button', {
				name: words.addSelectedProductsToSolution,
				exact: true,
			})
			.click();
		await expect(
			result.getByRole('button', {
				name: words.confirmChanges,
				exact: true,
			})
		).toBeVisible();
		await expect(
			result.getByRole('table').filter({
				has: page.getByRole('columnheader', {
					name: words.newQuantity,
					exact: true,
				}),
			})
		).toContainText(selectedInverter);
		await result
			.getByRole('button', { name: words.confirmChanges, exact: true })
			.click();
		await expect(result).toContainText(
			words.selectedProductsAddedToSolution,
			{ timeout: 120_000 }
		);
		await result
			.getByRole('link', { name: words.viewSolutionDraft, exact: true })
			.click();
		await expect(page.locator('body')).toContainText('SAJ');
		await expect(page.locator('body')).toContainText(
			selectedInverter.replace(/^SAJ\s+/, '')
		);
		await expect(page.locator('body')).toContainText(/inquir|anfrage/i);
		await page
			.getByRole('link', { name: words.sendInquiry, exact: true })
			.click();
		await expect(page).toHaveURL(/proforma-request|proforma-anfrage/, {
			timeout: 30_000,
		});
		const inquiry = page.locator(
			'form:has(input[name="action"][value="linker_inquiry"])'
		);
		await inquiry
			.locator('input[type="email"]')
			.fill('e2e-report-chain@example.test');
		await inquiry.locator('input[name="name"]').fill('E2E Report Chain');
		await inquiry
			.locator('textarea[name="message"]')
			.fill('Please quote the transferred configuration.');
		await inquiry.locator('input[name="consent"]').check();
		// Existing fixture setup isolates the shared local public-connection limit.
		wp([
			'db',
			'query',
			"DELETE FROM wp_options WHERE option_name LIKE 'linker_commerce_limit_public_connection%'",
		]);
		const revisionField = inquiry.locator(
			'input[name^="linker_project_note_revisions"]'
		);
		await expect(revisionField).toHaveCount(1);
		const trueRevision = await revisionField.inputValue();
		// Deliberate adversarial input: this hidden-value mutation tests note
		// revision protection, rather than bypassing a customer control.
		await revisionField.evaluate((element) => {
			(element as HTMLInputElement).value = 'deadbeefdeadbeef';
		});
		await inquiry
			.getByRole('button', { name: words.sendInquiry, exact: true })
			.click();
		await expect(page.locator('body')).toContainText(
			/The project notes have changed|Die Projektnotizen haben sich geändert/,
			{ timeout: 30_000 }
		);
		await expect(inquiry.locator('input[name="name"]')).toHaveValue(
			'E2E Report Chain'
		);
		await expect(inquiry.locator('textarea[name="message"]')).toHaveValue(
			'Please quote the transferred configuration.'
		);
		await revisionField.evaluate((element, value) => {
			(element as HTMLInputElement).value = value;
		}, trueRevision);
		await page.waitForTimeout(3500);
		await inquiry
			.getByRole('button', { name: words.sendInquiry, exact: true })
			.click();
		await expect(page).toHaveURL(/inquiry-received|anfrage-eingegangen/, {
			timeout: 60_000,
		});
		await expect(page.locator('body')).toContainText(
			/inquiry received|anfrage eingegangen/i
		);
		await expect(page.locator('body')).toContainText(
			'Please quote the transferred configuration.'
		);
		await expect(page.locator('body')).not.toContainText(
			/conversation summary|gesprächszusammenfassung/i
		);
		await page.goto(instance().url + words.inquiry);
		await expect(inquiry).toBeVisible();
		await expect(
			page.locator('input[name^="linker_project_note_revisions"]')
		).toHaveCount(0);
		await page.goto(
			instance().url + `${words.configurator}?project=${chainProject}`
		);
		await expect(page.locator('.lp-project')).toBeVisible();
		await chapter('lp-equipment');
		await expect(equipment.getByLabel(words.pvArrayKwp)).toHaveValue('8');
		await expect(inverterSelect).toHaveValue(selectedInverterId);
		await chapter('lp-calculations');
		await expect(page).toHaveURL(/energy_view=reports/);
		await expect(
			report.getByRole('button', {
				name: words.generatePlanningReport,
				exact: true,
			})
		).toBeVisible();
	});
}
