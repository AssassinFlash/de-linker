/**
 * The compatibility contract and the engineering overlay, as the customer
 * sees them.
 *
 * Domain 6 of the #548 matrix (docs/acceptance/2026-11-11/548-domain-gap-matrix.md)
 * had runtime evidence for the contract — 377 pairs in the production feed —
 * but no post-2026-11-05 native acceptance: nothing proved that a released
 * pairing reaches the screen with its conditions and its documents, or that a
 * pair the documents do not list fails to pass for one.
 *
 * So this spec drives the real workbench on a real instance: a project is
 * created through the interface, the equipment workspace is opened, a pair is
 * picked by hand, saved and checked, and the rendered result is compared with
 * the engine's own answer for that run (captured from `runs/read`, never
 * re-derived here). The assertions are therefore "the screen shows what the
 * contract answered", not "the screen shows what this spec expected".
 *
 * The engineering overlay is asserted at the two layers where it is real: the
 * published module record `products/current` materialises (the Trina
 * reference component with its datasheet page), and the design contract
 * `/design/residential` that uses it as its string-layout reference — with
 * the sentence that discloses it as a design assumption. The roof module the
 * customer picks in the design editor is a declared generic tier by
 * construction (`moduleTiers.ts`: "this is never a product reference"), so no
 * page-cited datasheet link is expected there and none is asserted.
 */
/**
 * External dependencies
 */
import { expect, test, type Locator, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { enginePost, plannerPost } from '../lib/engine';
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

type Lang = 'en' | 'de';

/** Each language's own words, from the shipped linker-tools catalog. */
const WORDS = {
	en: {
		configurator: '/solution-configurator/',
		newProject: 'New project',
		createProject: 'Create project',
		country: 'Country',
		location: 'Address or location reference',
		saveProject: 'Save project',
		saved: /^Saved/i,
		singleSystem: 'Single system',
		operatingMode: 'Choose an operating mode',
		gridConnection: 'Grid connection',
		threePhase: '3',
		pvArray: 'PV array kWp',
		usableEnergy: 'Required usable energy kWh',
		dischargePower: 'Required continuous AC discharge power kW',
		reloadProducts: 'Reload product data',
		manualPicker: 'Choose equipment manually',
		inverter: 'Inverter or integrated storage system',
		battery: 'Battery or storage system',
		modulesPerStack: 'Battery modules per stack',
		prepareSelection: 'Prepare equipment selection',
		checkSelection: 'Check saved equipment selection',
		pairing: 'Manufacturer pairing',
		conditions: 'Components and manufacturer conditions',
		met: 'Checked requirements met',
		further: 'Further checks required',
		notMet: 'Requirements not met',
		sourceDocument: 'Source document',
		page: (page: number) => `Page ${page}`,
	},
	de: {
		configurator: '/de/loesungskonfigurator/',
		newProject: 'Neues Projekt',
		createProject: 'Projekt anlegen',
		country: 'Land',
		location: 'Adresse oder Standortbezeichnung',
		saveProject: 'Projekt speichern',
		saved: /^Gespeichert/i,
		singleSystem: 'Einzelnes System',
		operatingMode: 'Betriebsart auswählen',
		gridConnection: 'Netzanschluss',
		threePhase: '3',
		pvArray: 'PV-Leistung kWp',
		usableEnergy: 'Benötigte nutzbare Speicherenergie kWh',
		dischargePower: 'Benötigte AC-Dauerleistung bei Entladung kW',
		reloadProducts: 'Produktdaten neu laden',
		manualPicker: 'Geräte manuell auswählen',
		inverter: 'Wechselrichter oder integriertes Speichersystem',
		battery: 'Batterie oder Speichersystem',
		modulesPerStack: 'Batteriemodule je Stack',
		prepareSelection: 'Geräteauswahl vorbereiten',
		checkSelection: 'Gespeicherte Geräteauswahl prüfen',
		pairing: 'Herstellerangaben zur Kombination',
		conditions: 'Komponenten und Herstellervorgaben',
		met: 'Geprüfte Anforderungen erfüllt',
		further: 'Weitere Prüfung erforderlich',
		notMet: 'Anforderungen nicht erfüllt',
		sourceDocument: 'Quelldokument',
		page: (page: number) => `Seite ${page}`,
	},
} as const;

/** Collapses the wrapping differences of two widths onto one comparable line. */
const flat = (text: string): string => text.replace(/\s+/g, ' ').trim();

/** One document reference as the engine publishes it. */
interface DocumentRef {
	url: string;
	page?: number | null;
}

/** The `manufacturer_pair` object frozen into an equipment assessment. */
interface ManufacturerPair {
	verdict:
		'released' | 'released_with_accessory' | 'not_released' | 'unknown';
	conditions: Array<{ en: string; de: string }>;
	documents: DocumentRef[];
}

interface Assessment {
	manufacturer_pair: ManufacturerPair | null;
	installation_requirements?: Array<{
		kind: string;
		conditions: Array<{ en: string; de: string }>;
		documents: DocumentRef[];
	}>;
	checks: Array<{ id: string; status: string }>;
}

/** A saved project on the equipment workspace, created through the interface. */
async function equipmentProject(page: Page, lang: Lang): Promise<void> {
	const words = WORDS[lang];
	await page.goto(instance().url + words.configurator, {
		waitUntil: 'domcontentloaded',
	});
	await page.getByRole('button', { name: words.newProject }).first().click();
	await page
		.locator('input[maxlength="256"]')
		.first()
		.fill(`Compatibility ${lang} ${Date.now()}`);
	await page.getByRole('button', { name: words.createProject }).click();
	await expect(page).toHaveURL(/project=[a-f0-9]{32}/, { timeout: 60_000 });

	// A German site is what makes the pair reachable: the country decides which
	// grid rules apply, and the address is the only declared location a
	// characterisation needs before saving.
	const site = page.locator('#lp-site');
	await site.getByLabel(words.country).selectOption('DE');
	await site.getByLabel(words.location).fill('80331 München');
	await page.getByRole('button', { name: words.saveProject }).click();
	await expect(page.locator('.lp-save-state')).toContainText(words.saved, {
		timeout: 120_000,
	});

	// The workspace is read from the hash when the app mounts, and a
	// fragment-only navigation does not remount it (the same reason
	// `planner-commercial-chain` reloads here).
	const url = new URL(page.url());
	url.hash = 'lp-equipment';
	await page.goto(url.toString());
	await page.reload({ waitUntil: 'networkidle' });
	await expect(page.locator('#lp-equipment-title')).toBeVisible({
		timeout: 120_000,
	});
}

/**
 * Picks one inverter and one battery by their published names, saves the
 * selection and runs the qualification. Returns the run's own assessment.
 */
async function checkedPair(
	page: Page,
	lang: Lang,
	pair: {
		inverter: string;
		battery: string;
		pvKwp: string;
		usableKwh: string;
		dischargeKw: string;
		/** Battery modules in one stack, when the pair's condition names a count. */
		modulesPerStack?: string;
	}
): Promise<Assessment> {
	const words = WORDS[lang];
	const calculation = page.locator('#lp-calculations');

	// One system, grid-connected, three-phase: the configuration the pairs
	// below are released for.
	await page
		.locator('#lp-calculations button', { hasText: words.singleSystem })
		.first()
		.click();
	await calculation
		.getByLabel(words.operatingMode)
		.selectOption({ index: 1 });
	await calculation
		.getByLabel(words.gridConnection)
		.selectOption(words.threePhase);
	await calculation.getByLabel(words.pvArray).fill(pair.pvKwp);
	await calculation.getByLabel(words.usableEnergy).fill(pair.usableKwh);
	await calculation.getByLabel(words.dischargePower).fill(pair.dischargeKw);
	await page
		.locator('#lp-calculations button', { hasText: words.reloadProducts })
		.first()
		.click();
	await page
		.locator('#lp-calculations summary', { hasText: words.manualPicker })
		.first()
		.click({ force: true, noWaitAfter: true });
	// The picker lists what the published product record carries. Waiting for a
	// real option is what proves the catalogue arrived; a fixed pause would
	// assert nothing and fail on a slower instance.
	const inverter = calculation.getByLabel(words.inverter);
	await expect(inverter.locator('option')).not.toHaveCount(1, {
		timeout: 120_000,
	});
	await inverter.selectOption({ label: pair.inverter });
	const battery = calculation.getByLabel(words.battery);
	await expect(battery.locator('option')).not.toHaveCount(1, {
		timeout: 60_000,
	});
	await battery.selectOption({ label: pair.battery });
	// A battery system with fixed internal modules has no stack field; the
	// count that a condition names travels in `modulesPerStack` only where the
	// product leaves it open (the picker shows the field then).
	if (pair.modulesPerStack) {
		await calculation
			.locator('label.lp-field', { hasText: words.modulesPerStack })
			.locator('input')
			.first()
			.fill(pair.modulesPerStack);
	}
	// Any numeric field the customer has not touched would keep the selection
	// unprepared; the engine's own defaults are not written for them.
	for (const field of await page
		.locator('#lp-calculations input:visible:not([type="checkbox"])')
		.all()) {
		const mode = await field.getAttribute('inputmode');
		if (mode !== 'decimal' && mode !== 'numeric') continue;
		if (!(await field.inputValue())) await field.fill('1');
	}
	await page.getByRole('button', { name: words.saveProject }).click();
	await expect(page.locator('.lp-save-state')).toContainText(words.saved, {
		timeout: 120_000,
	});

	const prepare = page
		.locator('#lp-calculations button:visible', {
			hasText: words.prepareSelection,
		})
		.first();
	await expect(prepare).toBeEnabled({ timeout: 120_000 });
	await prepare.click();
	await page.waitForTimeout(1500);
	await page.getByRole('button', { name: words.saveProject }).click();
	await expect(page.locator('.lp-save-state')).toContainText(words.saved, {
		timeout: 120_000,
	});

	// The result lands on the runs view; the run's own answer is captured from
	// the poll the screen itself makes, so the comparison below is against the
	// engine's reply for this project, not a second call that could differ.
	let assessment: Assessment | null = null;
	await page.route('**/rpc/runs/read', async (route) => {
		const response = await route.fetch();
		const body = (await response.json().catch(() => null)) as {
			result?: { assessment?: Assessment | null } | null;
		} | null;
		const found = body?.result?.assessment ?? null;
		if (found && Array.isArray(found.checks)) assessment = found;
		await route.fulfill({ response, body: JSON.stringify(body) });
	});
	await page
		.locator('#lp-calculations button:visible', {
			hasText: words.checkSelection,
		})
		.first()
		.click({ force: true });
	await expect
		.poll(() => assessment !== null, { timeout: 180_000 })
		.toBe(true);
	await page.unroute('**/rpc/runs/read');
	return assessment!;
}

/** The details block whose summary names `text`, opened. */
async function openedDetails(page: Page, text: string): Promise<Locator> {
	const details = page
		.locator('#lp-calculations details', { hasText: text })
		.last();
	await expect(details).toBeVisible({ timeout: 60_000 });
	await details.locator('summary').first().click({ force: true });
	return details;
}

for (const lang of ['en', 'de'] as const) {
	const words = WORDS[lang];

	test(`${lang}: a released pairing shows its manufacturer conditions and every cited document`, async ({
		page,
	}) => {
		test.setTimeout(480_000);
		await page.setViewportSize({ width: 1440, height: 900 });
		await equipmentProject(page, lang);

		// The GoodWe pair the production walk of 2026-11-11 released: an
		// 80 kW hybrid inverter against the 61.4 kWh battery system.
		const assessment = await checkedPair(page, lang, {
			inverter: 'GoodWe GW80K-ET-G10',
			battery: 'GoodWe GW61.4-BAT-AC-G10',
			pvKwp: '8',
			usableKwh: '10',
			dischargeKw: '5',
		});
		const pairing = assessment.manufacturer_pair!;
		expect(pairing, 'the run answers with a pairing').not.toBeNull();
		expect(pairing.verdict).toBe('released');
		expect(pairing.conditions.length).toBeGreaterThan(0);

		// The check line: the screen names the pairing and reports what the
		// contract said, not a stricter or looser verdict of its own.
		const pairingLine = page
			.locator('#lp-calculations summary', { hasText: words.pairing })
			.first();
		await expect(pairingLine).toBeVisible({ timeout: 60_000 });
		await expect(pairingLine).toContainText(words.met);
		await expect(pairingLine).not.toContainText(words.notMet);

		// Conditions and documents, in the block that exists for them.
		const block = await openedDetails(page, words.conditions);
		const shown = flat(await block.innerText());

		// Each condition the contract carries is on the screen, in the page's
		// own language. The contract's text is the source; this spec does not
		// restate it.
		for (const condition of pairing.conditions) {
			const text = lang === 'de' ? condition.de : condition.en;
			expect(
				shown,
				`condition rendered: ${text.slice(0, 60)}…`
			).toContain(flat(text));
		}

		// Every document is a real link with the contract's own address, and
		// nothing is rendered that the contract did not name.
		const expected = [
			...new Set(
				(assessment.installation_requirements ?? []).flatMap(
					(requirement) =>
						requirement.documents.map((document) => document.url)
				)
			),
			...new Set(pairing.documents.map((document) => document.url)),
		];
		const links = await block
			.locator('a')
			.evaluateAll((anchors) =>
				anchors.map((anchor) => [
					anchor.textContent?.trim() ?? '',
					anchor.getAttribute('href') ?? '',
					anchor.getAttribute('rel') ?? '',
					anchor.getAttribute('target') ?? '',
				])
			);
		expect(
			links.map((link) => link[1]),
			'the cited documents, in the contract order'
		).toEqual(expected);
		for (const [label, href, rel, target] of links) {
			expect(label).toBe(words.sourceDocument);
			expect(href).toMatch(/^https:\/\/de-linker\.com\/.+\.pdf$/);
			expect(rel).toBe('noreferrer');
			expect(target).toBe('_blank');
		}

		// Where the contract cites a page, the screen says which page. Both
		// sources of documents inside this block count: the pairing itself and
		// the installation requirements rendered beside it.
		const everyDocument = [
			...(assessment.installation_requirements ?? []).flatMap(
				(requirement) => requirement.documents
			),
			...pairing.documents,
		];
		const paged = everyDocument.filter(
			(document) => typeof document.page === 'number'
		);
		if (paged.length) {
			for (const document of paged) {
				expect(shown).toContain(words.page(document.page!));
			}
		} else {
			// No page may be invented for a document the contract leaves
			// unpaged: the GoodWe conditions carry the page inside their own
			// sentence, and a bare "Page N" would be a claim nobody made.
			expect(shown).not.toMatch(/\bPage \d+\b|\bSeite \d+\b/);
		}
	});

	test(`${lang}: a document set that does not list the pair does not pass for released`, async ({
		page,
	}) => {
		test.setTimeout(480_000);
		await page.setViewportSize({ width: 1440, height: 900 });
		await equipmentProject(page, lang);

		// The feed carries this pair as `not_released`: the cited documents do
		// not list it. The screen must therefore report a further check, and
		// must still show the honest wording behind it.
		const assessment = await checkedPair(page, lang, {
			inverter: 'GoodWe GW6K-ETA-G20',
			battery: 'SAJ B2-10.0-HV1',
			pvKwp: '6',
			usableKwh: '10',
			dischargeKw: '3',
		});
		const pairing = assessment.manufacturer_pair!;
		expect(pairing.verdict).toBe('not_released');

		const pairingLine = page
			.locator('#lp-calculations summary', { hasText: words.pairing })
			.first();
		await expect(pairingLine).toBeVisible({ timeout: 60_000 });
		await expect(
			pairingLine,
			'an unreleased pair is never reported as met'
		).toContainText(words.further);
		await expect(pairingLine).not.toContainText(words.met);

		const block = await openedDetails(page, words.conditions);
		const shown = flat(await block.innerText());
		for (const condition of pairing.conditions) {
			expect(shown).toContain(
				flat(lang === 'de' ? condition.de : condition.en)
			);
		}
	});

	// A released verdict is the documents' answer about the pair, not a
	// statement that this configuration satisfies their conditions. The SAJ
	// pair below is released and its documents name a page — and the screen
	// has to report the page and judge the module count separately.
	test(`${lang}: a released pair cites its pages and judges the module count the condition names`, async ({
		page,
	}) => {
		test.setTimeout(480_000);
		await page.setViewportSize({ width: 1440, height: 900 });
		await equipmentProject(page, lang);

		// Two modules: the smallest stack the HS2 manual documents, so the
		// pairing check is met and the pages are the only new subject.
		const assessment = await checkedPair(page, lang, {
			inverter: 'SAJ HS2-6K-T2-X',
			battery: 'SAJ BU2-5.0-HV1',
			pvKwp: '6',
			usableKwh: '10',
			dischargeKw: '3',
			modulesPerStack: '2',
		});
		const pairing = assessment.manufacturer_pair!;
		expect(pairing.verdict).toBe('released');

		const paged = pairing.documents.filter(
			(document) => typeof document.page === 'number'
		);
		expect(paged.length, 'this pair cites pages').toBeGreaterThan(0);

		const pairingLine = page
			.locator('#lp-calculations summary', { hasText: words.pairing })
			.first();
		await expect(pairingLine).toContainText(words.met);

		const block = await openedDetails(page, words.conditions);
		const shown = flat(await block.innerText());
		// Every page the contract cites is on the screen, beside its document.
		for (const document of paged) {
			expect(shown).toContain(words.page(document.page!));
		}
		// The links are the contract's, in its order.
		const expected = [
			...new Set(
				(assessment.installation_requirements ?? []).flatMap(
					(requirement) =>
						requirement.documents.map((document) => document.url)
				)
			),
			...new Set(pairing.documents.map((document) => document.url)),
		];
		await expect(block.locator('a')).toHaveCount(expected.length);
		for (const [index, href] of (
			await block
				.locator('a')
				.evaluateAll((anchors) =>
					anchors.map((anchor) => anchor.getAttribute('href') ?? '')
				)
		).entries()) {
			expect(href).toBe(expected[index]);
		}
	});

	test(`${lang}: a released pair whose condition this configuration breaks is not reported as met`, async ({
		page,
	}) => {
		test.setTimeout(480_000);
		await page.setViewportSize({ width: 1440, height: 900 });
		await equipmentProject(page, lang);

		// One module is below the two-to-five the same documents require, so
		// the pair is still released while the check must fail — the screen
		// may not repeat "released" as if it were a pass.
		const assessment = await checkedPair(page, lang, {
			inverter: 'SAJ HS2-6K-T2-X',
			battery: 'SAJ BU2-5.0-HV1',
			pvKwp: '6',
			usableKwh: '10',
			dischargeKw: '3',
			modulesPerStack: '1',
		});
		const pairing = assessment.manufacturer_pair!;
		expect(pairing.verdict, 'the documents still release the pair').toBe(
			'released'
		);

		const pairingLine = page
			.locator('#lp-calculations summary', { hasText: words.pairing })
			.first();
		await expect(pairingLine).toBeVisible({ timeout: 60_000 });
		await expect(
			pairingLine,
			'a released verdict never hides a broken condition'
		).toContainText(words.notMet);
		await expect(pairingLine).not.toContainText(words.met);
	});
}

test('the engineering overlay publishes its reference module with the datasheet page', async () => {
	// `products/current` is the published module record — the same reply the
	// workbench reads to fill its module parameters. The overlay entry of the
	// feed is what it materialises. It lives on the private planner route,
	// behind the principal the gateway sets for every project page.
	const reply = await plannerPost<{
		prepared: boolean;
		references: Array<{
			id: string;
			kind: string;
			canonical_product_id: number;
		}>;
		pv_modules: Array<{
			specification: {
				id: string;
				model: string;
				stc_power_w: number;
				length_m: number;
				width_m: number;
				source: {
					kind: string;
					url: string | null;
					page: number | null;
					document_sha256: string | null;
					woo?: {
						product_id: number;
						product_revision: string;
						reference_input_id: string;
					} | null;
				};
			};
			parameters: {
				gamma_pdc_per_c: number;
				source: { url: string | null; page: number | null };
			};
		}>;
		module_diagnostics: unknown[];
	}>(
		'products/current',
		{ schema_version: 1 },
		{
			kind: 'guest',
			subject: `compat-overlay:${Date.now()}`,
		}
	);
	expect(reply.status, 'the published product record answers').toBe(200);
	const current = reply.body;

	expect(current.prepared).toBe(true);
	expect(current.module_diagnostics).toEqual([]);
	expect(current.references).toHaveLength(1);
	const reference = current.references[0]!;
	expect(reference.kind).toBe('pv_module');
	expect(reference.id).toBe('mat_trina_solar_tsm_460neg9r_28');

	expect(current.pv_modules).toHaveLength(1);
	const module = current.pv_modules[0]!;
	// The materialised record is the overlay component, bound to its Woo
	// product and to the overlay entry itself.
	expect(module.specification.model).toBe('Trina Solar TSM-460NEG9R.28');
	expect(module.specification.source.woo).toMatchObject({
		product_id: reference.canonical_product_id,
		reference_input_id: reference.id,
	});
	// The binding pins the exact product revision it was prepared against, so a
	// later Woo edit cannot silently change the module behind the design.
	expect(module.specification.source.woo!.product_revision).toMatch(
		/^[a-f0-9]{64}$/
	);
	// The figures are the overlay's own, and their citation is the datasheet
	// page the overlay carries — the page the customer-visible module
	// parameters would cite if this module were the project's roof module.
	expect(module.specification.stc_power_w).toBe(460);
	expect(module.specification.length_m).toBeCloseTo(1.762, 3);
	expect(module.specification.width_m).toBeCloseTo(1.134, 3);
	expect(module.parameters.gamma_pdc_per_c).toBeCloseTo(-0.0029, 6);
	for (const source of [
		module.specification.source,
		module.parameters.source,
	]) {
		expect(source.page).toBe(2);
		expect(source.url).toMatch(/Vertex-S_NEG9R\.28_EN_2024_C_web\.pdf$/);
	}
	expect(module.specification.source.document_sha256).toMatch(
		/^[a-f0-9]{64}$/
	);
});

test('the design contract states the overlay component as its reference module', async () => {
	// The string layout of the residential design uses the overlay module; the
	// customer is told which module that is and that the modules installed
	// govern. This is the disclosure the 2026-11-05 acceptance read at the
	// production site, asserted here against the same contract.
	const design = await enginePost<{
		status: string;
		selected: {
			strings: {
				module: string;
				module_wp: number;
				modules_per_string: number;
			};
			lines: Array<{ label: string; basis: string[] }>;
		} | null;
		warnings?: Array<{ message?: string }>;
	}>('/design/residential', {
		locale: 'en',
		plz: '80538',
		annual_kwh: 5000,
		pv_kwp: 10,
		phase: 3,
	});
	expect(design.status).toBe('solution');
	const strings = design.selected!.strings;
	expect(strings.module).toBe('Trina Solar TSM-460NEG9R.28');
	expect(strings.module_wp).toBe(460);
	expect(strings.modules_per_string).toBeGreaterThan(0);

	const text = JSON.stringify(design);
	expect(text).toContain(
		'The string layout uses Trina Solar TSM-460NEG9R.28 as a reference module; the module you install can change it.'
	);
	// The overlay component is never sold as a product line: the bill of
	// materials names PV modules as the customer's own choice.
	expect(
		design.selected!.lines.map((line) => line.label),
		'no product line claims the reference module'
	).not.toContain('Trina Solar TSM-460NEG9R.28');
	expect(text).toContain('PV modules of your choice');
});
